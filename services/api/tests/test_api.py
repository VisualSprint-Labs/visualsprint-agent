from __future__ import annotations

from fastapi.testclient import TestClient

from visualsprint_api.config import build_settings
from visualsprint_api.models import MemoryMatch


def _create_live_browser_meeting(client: TestClient) -> str:
    create_response = client.post(
        "/api/meetings",
        json={
            "title": "Integration planning sync",
            "participantCount": 4,
            "sourceConnector": "browser_live_capture",
            "notes": "Track blockers, owners, and repeated risks.",
        },
    )
    assert create_response.status_code == 201
    meeting_id = create_response.json()["meeting"]["id"]

    start_response = client.post(f"/api/meetings/{meeting_id}/start")
    assert start_response.status_code == 200
    return meeting_id


def _start_capture_session(client: TestClient, meeting_id: str) -> dict:
    response = client.post(
        f"/api/meetings/{meeting_id}/capture-sessions/start",
        json={
            "recorderMimeType": "video/webm;codecs=vp9,opus",
            "hasDisplayVideo": True,
            "hasDisplayAudio": True,
            "hasMicrophoneAudio": True,
        },
    )
    assert response.status_code == 201
    return response.json()["captureSession"]


def _register_chunk(client: TestClient, meeting_id: str, client_chunk_id: str, sequence: int = 1):
    return client.post(
        f"/api/meetings/{meeting_id}/capture-sessions/chunk",
        json={
            "clientChunkId": client_chunk_id,
            "sequence": sequence,
            "durationMs": 4000,
            "byteSize": 64000,
            "mimeType": "video/webm",
        },
    )


def _process_chunk(client: TestClient, meeting_id: str, client_chunk_id: str) -> None:
    upload_response = client.post(
        f"/api/meetings/{meeting_id}/capture-sessions/chunk/upload-complete",
        json={"clientChunkId": client_chunk_id},
    )
    assert upload_response.status_code == 200
    reasoning_response = client.post(
        f"/api/meetings/{meeting_id}/capture-sessions/chunks/{client_chunk_id}/reasoning/run"
    )
    assert reasoning_response.status_code == 200


def test_upload_completion_only_assembles_chunk_context(client: TestClient):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    register_response = _register_chunk(client, meeting_id, "client-chunk-0901", sequence=1)
    assert register_response.status_code == 200

    upload_response = client.post(
        f"/api/meetings/{meeting_id}/capture-sessions/chunk/upload-complete",
        json={"clientChunkId": "client-chunk-0901"},
    )
    assert upload_response.status_code == 200
    upload_payload = upload_response.json()
    assert upload_payload["chunk"]["processingStatus"] == "processing"
    assert upload_payload["chunk"]["lifecycleStatus"] == "processing"
    assert upload_payload["chunk"]["signalCount"] == 0

    context_response = client.get(
        f"/api/meetings/{meeting_id}/capture-sessions/chunks/client-chunk-0901/context"
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()["chunkContext"]
    assert len(context_payload["transcriptSegments"]) == 2
    assert len(context_payload["screenEvents"]) >= 1
    assert context_payload["chunk"]["processingStatus"] == "processing"

    reasoning_response = client.post(
        f"/api/meetings/{meeting_id}/capture-sessions/chunks/client-chunk-0901/reasoning/run"
    )
    assert reasoning_response.status_code == 200
    reasoning_payload = reasoning_response.json()
    assert reasoning_payload["chunk"]["processingStatus"] == "processed"
    assert reasoning_payload["chunk"]["signalCount"] >= 1


def test_capture_chunk_registration_is_idempotent_and_sequence_safe(client: TestClient):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)

    first_response = _register_chunk(client, meeting_id, "client-chunk-0001", sequence=1)
    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload["chunk"]["uploadStatus"] == "ready"
    assert first_payload["meeting"]["metrics"]["captureChunksCount"] == 1

    duplicate_response = _register_chunk(client, meeting_id, "client-chunk-0001", sequence=1)
    assert duplicate_response.status_code == 200
    duplicate_payload = duplicate_response.json()
    assert duplicate_payload["chunk"]["id"] == first_payload["chunk"]["id"]
    assert duplicate_payload["meeting"]["metrics"]["captureChunksCount"] == 1

    conflict_response = _register_chunk(client, meeting_id, "client-chunk-0002", sequence=1)
    assert conflict_response.status_code == 409
    assert "Chunk sequence already exists" in conflict_response.text


def test_processed_chunk_exposes_context_insight_and_memory_surfaces(client: TestClient):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    register_response = _register_chunk(client, meeting_id, "client-chunk-1001", sequence=1)
    assert register_response.status_code == 200

    _process_chunk(client, meeting_id, "client-chunk-1001")

    context_response = client.get(
        f"/api/meetings/{meeting_id}/capture-sessions/chunks/client-chunk-1001/context"
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert len(context_payload["chunkContext"]["transcriptSegments"]) == 2
    assert len(context_payload["chunkContext"]["screenEvents"]) >= 1
    assert context_payload["chunkContext"]["chunk"]["transcriptSource"] == "local_fallback"
    assert context_payload["chunkContext"]["chunk"]["mediaSource"] == "local_fallback"
    assert context_payload["chunkContext"]["chunk"]["reasoningSource"] == "local_fallback"
    assert context_payload["meetingState"]["latestChunkClientId"] == "client-chunk-1001"

    insight_response = client.get(f"/api/meetings/{meeting_id}/insights/chunks/client-chunk-1001")
    assert insight_response.status_code == 200
    insight_payload = insight_response.json()["insight"]
    assert insight_payload["clientChunkId"] == "client-chunk-1001"
    assert len(insight_payload["focusAreas"]) >= 2
    assert len(insight_payload["memoryQueries"]) >= 1
    assert context_payload["meetingState"]["openDecisions"][0]["evidence"][0]["clientChunkId"] == "client-chunk-1001"


def test_chunk_insight_injects_backend_memory_matches_before_agent_calls(
    client: TestClient,
    monkeypatch,
):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    register_response = _register_chunk(client, meeting_id, "client-chunk-1101", sequence=1)
    assert register_response.status_code == 200

    _process_chunk(client, meeting_id, "client-chunk-1101")

    monkeypatch.setattr(
        "visualsprint_api.repository.settings",
        build_settings(
            {
                "ELASTICSEARCH_URL": "https://elastic.example",
                "ELASTICSEARCH_API_KEY_SECRET": "elastic-api-key",
                "ELASTIC_INDEX_OUTCOMES": "visualsprint-outcomes",
            }
        ),
    )
    monkeypatch.setattr(
        "visualsprint_api.repository.search_prior_outcomes_in_elasticsearch",
        lambda **kwargs: [
            MemoryMatch(
                id="mem_elastic_injected_001",
                sourceMeetingId="mtg_hist_injected_001",
                summary="A similar blocker was found in Elastic.",
                sourceMeetingTitle="Incident review",
                strength="critical",
                relation="recurring",
                score=0.91,
                snippet="Elastic search returned a closely related blocker document.",
                recordedAt="2026-06-08T10:00:00Z",
            )
        ],
    )

    insight_response = client.get(
        f"/api/meetings/{meeting_id}/insights/chunks/client-chunk-1101"
    )
    assert insight_response.status_code == 200
    insight_payload = insight_response.json()["insight"]
    assert len(insight_payload["memoryMatches"]) == 1
    assert insight_payload["memoryMatches"][0]["sourceMeetingId"] == "mtg_hist_injected_001"
    assert insight_payload["memoryMatches"][0]["relation"] == "recurring"


def test_summary_packet_output_registration_and_final_report_flow(client: TestClient):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    register_response = _register_chunk(client, meeting_id, "client-chunk-2001", sequence=1)
    assert register_response.status_code == 200
    _process_chunk(client, meeting_id, "client-chunk-2001")

    outputs_response = client.post(
        f"/api/meetings/{meeting_id}/outputs/register",
        json={
            "clientChunkId": "client-chunk-2001",
            "decisions": [
                {
                    "title": "Publish the rollback plan before the next deploy",
                    "rationale": "The team wants a durable handoff artifact before resuming release work.",
                    "speakerLabel": "Jordan",
                }
            ],
            "commitments": [
                {
                    "ownerLabel": "Mina",
                    "action": "Attach the rollout verification checklist to the ticket",
                    "dueHint": "Today",
                }
            ],
            "blockers": [],
            "openQuestions": [
                {
                    "question": "Who signs off on rollback readiness once staging is green?",
                    "speakerLabel": "Avery",
                }
            ],
            "memoryMatches": [
                {
                    "sourceMeetingId": "mtg_hist_auth_01",
                    "summary": "Rollback readiness was also a concern in the prior release review.",
                    "sourceMeetingTitle": "Sprint 21 release review",
                    "strength": "related",
                    "relation": "recurring",
                    "score": 0.77,
                    "snippet": "Rollback readiness had to be confirmed before the release freeze was lifted.",
                }
            ],
        },
    )
    assert outputs_response.status_code == 200
    state_after_outputs = outputs_response.json()["meetingState"]
    assert len(state_after_outputs["openQuestions"]) >= 1

    summary_response = client.get(f"/api/meetings/{meeting_id}/summary-packet")
    assert summary_response.status_code == 200
    summary_packet = summary_response.json()["summaryPacket"]
    assert summary_packet["meetingStatus"] == "live"
    assert len(summary_packet["reportChecklist"]) >= 4
    assert len(summary_packet["timelineHighlights"]) >= 1
    assert len(summary_packet["decisions"]) >= 2
    assert len(summary_packet["decisions"][0]["evidence"]) >= 1
    assert summary_packet["decisions"][0]["evidence"][0]["clientChunkId"] == "client-chunk-2001"

    index_documents_response = client.get(f"/api/meetings/{meeting_id}/memory/index-documents")
    assert index_documents_response.status_code == 200
    index_documents = index_documents_response.json()["documents"]
    assert len(index_documents) >= 4
    assert any(document["recordType"] == "decision" for document in index_documents)

    end_response = client.post(f"/api/meetings/{meeting_id}/end")
    assert end_response.status_code == 200

    finalize_response = client.post(f"/api/meetings/{meeting_id}/final-report")
    assert finalize_response.status_code == 200
    final_report = finalize_response.json()["report"]
    assert final_report["meetingId"] == meeting_id
    assert final_report["summarySource"] == "local_fallback"
    assert len(final_report["decisions"]) >= 2
    assert len(final_report["openQuestions"]) >= 1
    assert len(final_report["decisions"][0]["evidence"]) >= 1
    assert final_report["decisions"][0]["evidence"][0]["transcriptRef"] is not None

    ended_summary_response = client.get(f"/api/meetings/{meeting_id}/summary-packet")
    assert ended_summary_response.status_code == 200
    assert ended_summary_response.json()["summaryPacket"]["meetingStatus"] == "ended"


def test_register_outputs_can_upsert_indexed_documents_to_elasticsearch(
    client: TestClient,
    monkeypatch,
):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    register_response = _register_chunk(client, meeting_id, "client-chunk-elastic-001", sequence=1)
    assert register_response.status_code == 200
    _process_chunk(client, meeting_id, "client-chunk-elastic-001")

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "visualsprint_api.repository.settings",
        build_settings(
            {
                "ELASTICSEARCH_URL": "https://elastic.example",
                "ELASTICSEARCH_API_KEY_SECRET": "elastic-api-key",
                "ELASTIC_INDEX_OUTCOMES": "visualsprint-outcomes",
            }
        ),
    )

    def fake_upsert(*, config, meeting, documents):
        captured["index"] = config.elastic_index_outcomes
        captured["meeting_id"] = meeting.id
        captured["document_count"] = len(documents)
        captured["record_types"] = sorted({document.recordType for document in documents})
        return len(documents)

    monkeypatch.setattr(
        "visualsprint_api.repository.upsert_indexed_outcomes_to_elasticsearch",
        fake_upsert,
    )

    outputs_response = client.post(
        f"/api/meetings/{meeting_id}/outputs/register",
        json={
            "clientChunkId": "client-chunk-elastic-001",
            "decisions": [
                {
                    "title": "Publish the rollback plan before the next deploy",
                    "rationale": "The team wants a durable handoff artifact before resuming release work.",
                    "speakerLabel": "Jordan",
                }
            ],
            "commitments": [],
            "blockers": [],
            "openQuestions": [],
            "memoryMatches": [],
        },
    )

    assert outputs_response.status_code == 200
    assert captured["index"] == "visualsprint-outcomes"
    assert captured["meeting_id"] == meeting_id
    assert captured["document_count"] >= 2
    assert "decision" in captured["record_types"]


def test_search_prior_outcomes_can_use_elasticsearch_when_configured(
    client: TestClient,
    monkeypatch,
):
    meeting_id = _create_live_browser_meeting(client)

    monkeypatch.setattr(
        "visualsprint_api.repository.settings",
        build_settings(
            {
                "ELASTICSEARCH_URL": "https://elastic.example",
                "ELASTICSEARCH_API_KEY_SECRET": "elastic-api-key",
                "ELASTIC_INDEX_OUTCOMES": "visualsprint-outcomes",
            }
        ),
    )
    monkeypatch.setattr(
        "visualsprint_api.repository.search_prior_outcomes_in_elasticsearch",
        lambda **kwargs: [
            MemoryMatch(
                id="mem_elastic_001",
                sourceMeetingId="mtg_hist_elastic_001",
                summary="A similar blocker was found in Elastic.",
                sourceMeetingTitle="Incident review",
                strength="recurring",
                relation="recurring",
                score=0.88,
                snippet="Elastic search returned a closely related blocker document.",
                recordedAt="2026-06-08T10:00:00Z",
            )
        ],
    )

    response = client.post(
        f"/api/meetings/{meeting_id}/memory/search-prior-outcomes",
        json={
            "recordType": "blocker",
            "summary": "Authentication release blocker is still active",
            "detail": "The auth configuration drift is blocking the release and needs a historical comparison.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["matches"][0]["sourceMeetingId"] == "mtg_hist_elastic_001"
    assert payload["matches"][0]["relation"] == "recurring"


def test_knowledge_search_falls_back_to_local_outcomes_when_elastic_unconfigured(
    client: TestClient,
):
    """Knowledge search must return local in-memory results, not available=False."""

    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    _register_chunk(client, meeting_id, "client-chunk-knowledge-001", sequence=1)
    _process_chunk(client, meeting_id, "client-chunk-knowledge-001")

    response = client.get("/api/knowledge/search", params={"q": "release"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["total"] > 0
    assert any("release" in r["summary"].lower() for r in payload["results"])


def test_knowledge_search_local_fallback_filters_by_record_type(client: TestClient):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    _register_chunk(client, meeting_id, "client-chunk-filter-001", sequence=1)
    _process_chunk(client, meeting_id, "client-chunk-filter-001")

    response = client.get(
        "/api/knowledge/search",
        params={"q": "", "recordType": "decision"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["total"] > 0
    assert all(r["recordType"] == "decision" for r in payload["results"])


def test_search_prior_outcomes_uses_local_cross_meeting_data_when_elastic_unconfigured(
    client: TestClient,
):
    """Memory search must return real cross-meeting outcomes, not hardcoded templates."""

    meeting_a = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_a)
    _register_chunk(client, meeting_a, "client-chunk-prior-a1", sequence=1)
    _process_chunk(client, meeting_a, "client-chunk-prior-a1")

    meeting_b = _create_live_browser_meeting(client)

    response = client.post(
        f"/api/meetings/{meeting_b}/memory/search-prior-outcomes",
        json={
            "recordType": "blocker",
            "summary": "Auth configuration drift is still blocking the release candidate",
            "detail": "The auth configuration drift is blocking the release.",
        },
    )

    assert response.status_code == 200
    matches = response.json()["matches"]
    assert len(matches) > 0
    assert matches[0]["sourceMeetingId"] == meeting_a
    assert matches[0]["sourceMeetingId"] != "mtg_hist_auth_01"


def test_search_prior_outcomes_returns_new_when_no_cross_meeting_data(
    client: TestClient,
):
    """With no prior meetings, memory search should honestly report 'new'."""

    meeting_id = _create_live_browser_meeting(client)

    response = client.post(
        f"/api/meetings/{meeting_id}/memory/search-prior-outcomes",
        json={
            "recordType": "blocker",
            "summary": "A completely novel deployment issue",
            "detail": "Something entirely unprecedented happened.",
        },
    )

    assert response.status_code == 200
    matches = response.json()["matches"]
    assert len(matches) == 1
    assert matches[0]["relation"] == "new"


def test_repeated_agent_outputs_update_existing_records_instead_of_duplicating(client: TestClient):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    register_response = _register_chunk(client, meeting_id, "client-chunk-3001", sequence=1)
    assert register_response.status_code == 200
    _process_chunk(client, meeting_id, "client-chunk-3001")

    payload = {
        "clientChunkId": "client-chunk-3001",
        "decisions": [
            {
                "title": "Publish the rollback plan before the next deploy",
                "rationale": "The team wants the deployment handoff documented before release work continues.",
                "speakerLabel": "Jordan",
            }
        ],
        "commitments": [],
        "blockers": [],
        "openQuestions": [],
        "memoryMatches": [],
        "resolvedDecisionIds": [],
        "resolvedCommitmentIds": [],
        "resolvedBlockerIds": [],
        "resolvedOpenQuestionIds": [],
    }

    first_response = client.post(f"/api/meetings/{meeting_id}/outputs/register", json=payload)
    assert first_response.status_code == 200
    first_meeting = first_response.json()["meeting"]
    first_decision = next(
        decision
        for decision in first_meeting["recentDecisions"]
        if decision["title"] == "Publish the rollback plan before the next deploy"
    )
    first_decision_id = first_decision["id"]
    first_decisions_count = first_meeting["metrics"]["decisionsCount"]
    assert first_decision["status"] == "open"

    second_response = client.post(f"/api/meetings/{meeting_id}/outputs/register", json=payload)
    assert second_response.status_code == 200
    second_meeting = second_response.json()["meeting"]
    second_decision = next(
        decision
        for decision in second_meeting["recentDecisions"]
        if decision["title"] == "Publish the rollback plan before the next deploy"
    )
    assert second_decision["id"] == first_decision_id
    assert second_decision["status"] == "updated"
    assert second_decision["firstSeenChunkId"] == "client-chunk-3001"
    assert second_decision["lastUpdatedChunkId"] == "client-chunk-3001"
    assert second_meeting["metrics"]["decisionsCount"] == first_decisions_count


def test_resolved_records_leave_open_state_and_can_reopen(client: TestClient):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    register_response = _register_chunk(client, meeting_id, "client-chunk-4001", sequence=1)
    assert register_response.status_code == 200
    _process_chunk(client, meeting_id, "client-chunk-4001")

    initial_meeting = client.get(f"/api/meetings/{meeting_id}").json()["meeting"]
    target_decision = initial_meeting["recentDecisions"][0]

    resolve_response = client.post(
        f"/api/meetings/{meeting_id}/outputs/register",
        json={
            "clientChunkId": "client-chunk-4001",
            "decisions": [],
            "commitments": [],
            "blockers": [],
            "openQuestions": [],
            "memoryMatches": [],
            "resolvedDecisionIds": [target_decision["id"]],
            "resolvedCommitmentIds": [],
            "resolvedBlockerIds": [],
            "resolvedOpenQuestionIds": [],
        },
    )
    assert resolve_response.status_code == 200
    resolved_meeting = resolve_response.json()["meeting"]
    resolved_decision = next(
        decision for decision in resolved_meeting["recentDecisions"] if decision["id"] == target_decision["id"]
    )
    assert resolved_decision["status"] == "resolved"
    assert all(
        decision["id"] != target_decision["id"]
        for decision in resolve_response.json()["meetingState"]["openDecisions"]
    )
    resolved_index_documents = client.get(f"/api/meetings/{meeting_id}/memory/index-documents").json()["documents"]
    resolved_document = next(
        document for document in resolved_index_documents if document["id"] == target_decision["id"]
    )
    assert resolved_document["status"] == "resolved"

    reopen_response = client.post(
        f"/api/meetings/{meeting_id}/outputs/register",
        json={
            "clientChunkId": "client-chunk-4001",
            "decisions": [
                {
                    "title": target_decision["title"],
                    "rationale": target_decision["rationale"],
                    "speakerLabel": target_decision["speakerLabel"],
                }
            ],
            "commitments": [],
            "blockers": [],
            "openQuestions": [],
            "memoryMatches": [],
            "resolvedDecisionIds": [],
            "resolvedCommitmentIds": [],
            "resolvedBlockerIds": [],
            "resolvedOpenQuestionIds": [],
        },
    )
    assert reopen_response.status_code == 200
    reopened_decision = next(
        decision
        for decision in reopen_response.json()["meeting"]["recentDecisions"]
        if decision["id"] == target_decision["id"]
    )
    assert reopened_decision["status"] == "reopened"
    assert any(
        decision["id"] == target_decision["id"]
        for decision in reopen_response.json()["meetingState"]["openDecisions"]
    )
    reopened_index_documents = client.get(f"/api/meetings/{meeting_id}/memory/index-documents").json()["documents"]
    reopened_document = next(
        document for document in reopened_index_documents if document["id"] == target_decision["id"]
    )
    assert reopened_document["status"] == "reopened"


def test_chunk_processing_can_use_service_boundary_processors(client: TestClient, monkeypatch):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    register_response = _register_chunk(client, meeting_id, "client-chunk-5001", sequence=2)
    assert register_response.status_code == 200

    from visualsprint_api.models import ScreenEvent, TranscriptSegment

    def fake_transcript_processor(chunk):
        return [
            TranscriptSegment(
                id="trn_service_001",
                speakerLabel="ServiceAvery",
                startedAt=chunk.recordedAt,
                endedAt=chunk.recordedAt,
                text="Service boundary transcript processor supplied this segment.",
            ),
            TranscriptSegment(
                id="trn_service_002",
                speakerLabel="ServiceJordan",
                startedAt=chunk.recordedAt,
                endedAt=chunk.recordedAt,
                text="A second transcript segment arrived from the ingest service surface.",
            ),
        ], "downstream_service"

    def fake_media_processor(chunk):
        return (
            7,
            [
                ScreenEvent(
                    id="scr_service_001",
                    kind="terminal",
                    summary="Service boundary media processor supplied this visual event.",
                    frameTimestampMs=1200,
                    recordedAt=chunk.recordedAt,
                )
            ],
            "downstream_service",
        )

    monkeypatch.setattr(
        "visualsprint_api.repository.process_transcript_chunk_with_source",
        fake_transcript_processor,
    )
    monkeypatch.setattr(
        "visualsprint_api.repository.process_media_chunk_with_source",
        fake_media_processor,
    )

    _process_chunk(client, meeting_id, "client-chunk-5001")

    context_response = client.get(
        f"/api/meetings/{meeting_id}/capture-sessions/chunks/client-chunk-5001/context"
    )
    assert context_response.status_code == 200
    payload = context_response.json()["chunkContext"]
    assert payload["transcriptSegments"][0]["speakerLabel"] == "ServiceAvery"
    assert payload["screenEvents"][0]["summary"] == "Service boundary media processor supplied this visual event."
    assert payload["chunk"]["transcriptSource"] == "downstream_service"
    assert payload["chunk"]["mediaSource"] == "downstream_service"


def test_chunk_registration_can_use_ingest_upload_reservation(client: TestClient, monkeypatch):
    meeting_id = _create_live_browser_meeting(client)
    capture_session = _start_capture_session(client, meeting_id)

    def fake_upload_target_reservation(**kwargs):
        from visualsprint_api.models import CaptureChunkUploadTarget

        return CaptureChunkUploadTarget(
            objectPath=(
                f"reserved/{kwargs['meeting_id']}/{kwargs['capture_session_id']}/"
                f"{kwargs['client_chunk_id']}.webm"
            ),
            requiredHeaders={
                "Content-Type": kwargs["mime_type"],
                "X-VisualSprint-Reservation": "service",
            },
        )

    monkeypatch.setattr(
        "visualsprint_api.repository.reserve_chunk_upload_target",
        fake_upload_target_reservation,
    )

    register_response = _register_chunk(client, meeting_id, "client-chunk-5101", sequence=1)
    assert register_response.status_code == 200
    payload = register_response.json()["chunk"]
    assert payload["storageObjectPath"].startswith("reserved/")
    assert payload["storageObjectPath"].endswith("client-chunk-5101.webm")
    assert payload["uploadTarget"]["requiredHeaders"]["X-VisualSprint-Reservation"] == "service"
    assert capture_session["id"] in payload["storageObjectPath"]


def test_meta_reports_downstream_service_status(client: TestClient, monkeypatch):
    fallback_meta_response = client.get("/api/meta")
    assert fallback_meta_response.status_code == 200
    fallback_payload = fallback_meta_response.json()
    fallback_services = fallback_payload["downstreamServices"]
    agents_status = next(service for service in fallback_services if service["kind"] == "agents")
    ingest_status = next(service for service in fallback_services if service["kind"] == "ingest")
    media_status = next(service for service in fallback_services if service["kind"] == "media")
    assert agents_status["status"] == "not_configured"
    assert ingest_status["status"] == "not_configured"
    assert media_status["status"] == "not_configured"
    assert fallback_payload["memoryIntegration"]["provider"] == "elastic"
    assert fallback_payload["memoryIntegration"]["writebackConfigured"] is False
    assert fallback_payload["memoryIntegration"]["mcpServerConfigured"] is False

    from visualsprint_api.models import DownstreamServiceStatus

    monkeypatch.setattr(
        "visualsprint_api.routes.meta.get_downstream_service_statuses",
        lambda: [
            DownstreamServiceStatus(
                service="visualsprint-api",
                kind="control_plane",
                configured=True,
                reachable=True,
                mode="local",
                baseUrl=None,
                status="ok",
                version="0.1.0",
                track="elastic",
                note="Control plane is healthy.",
            ),
            DownstreamServiceStatus(
                service="visualsprint-agents",
                kind="agents",
                configured=True,
                reachable=True,
                mode="remote",
                baseUrl="http://127.0.0.1:8300",
                status="ok",
                version="0.1.0",
                track="elastic",
                note="Agents service responded successfully.",
            ),
            DownstreamServiceStatus(
                service="visualsprint-ingest",
                kind="ingest",
                configured=True,
                reachable=True,
                mode="remote",
                baseUrl="http://127.0.0.1:8100",
                status="ok",
                version="0.1.0",
                track="elastic",
                note="Ingest service responded successfully.",
            ),
            DownstreamServiceStatus(
                service="visualsprint-media",
                kind="media",
                configured=True,
                reachable=False,
                mode="fallback",
                baseUrl="http://127.0.0.1:8200",
                status="unreachable",
                version=None,
                track=None,
                note="Media service is unreachable; local fallback remains active.",
            ),
        ],
    )

    patched_meta_response = client.get("/api/meta")
    assert patched_meta_response.status_code == 200
    patched_payload = patched_meta_response.json()
    patched_services = patched_payload["downstreamServices"]
    assert next(service for service in patched_services if service["kind"] == "agents")["status"] == "ok"
    assert next(service for service in patched_services if service["kind"] == "ingest")["status"] == "ok"
    assert next(service for service in patched_services if service["kind"] == "media")["status"] == "unreachable"
    assert patched_payload["memoryIntegration"]["provider"] == "elastic"


def test_agents_invocation_audit_proxy_reports_fallback_when_unavailable(client: TestClient):
    response = client.get("/api/meta/agents/invocations")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["available"] is False
    assert payload["summary"]["source"] == "local_unavailable"
    assert payload["summary"]["total"] == 0
    assert payload["invocations"] == []


def test_agents_invocation_audit_proxy_can_surface_service_data(client: TestClient, monkeypatch):
    from visualsprint_api.models import AgentInvocationAuditResponse

    monkeypatch.setattr(
        "visualsprint_api.routes.agents.get_agents_invocation_audit",
        lambda: AgentInvocationAuditResponse.model_validate(
            {
                "summary": {
                    "available": True,
                    "source": "agents_service",
                    "total": 2,
                    "reasoningRuns": 1,
                    "summaryRuns": 1,
                    "bridgeRuns": 1,
                    "bridgeFallbackRuns": 1,
                    "mockRuns": 0,
                    "note": "The standalone agents service provided recent invocation audit data.",
                },
                "invocations": [
                    {
                        "invokedAt": "2026-06-08T09:00:00Z",
                        "agentKind": "summary",
                        "executionMode": "bridge_fallback",
                        "status": "fallback",
                        "targetAgentId": "summary-agent",
                        "requestKey": "mtg_001",
                        "detail": "Configured bridge was unavailable, so deterministic summary fallback was used.",
                    },
                    {
                        "invokedAt": "2026-06-08T08:59:00Z",
                        "agentKind": "reasoning",
                        "executionMode": "bridge",
                        "status": "success",
                        "targetAgentId": "reasoning-agent",
                        "requestKey": "chunk_001",
                        "detail": "Configured bridge produced the reasoning response.",
                    },
                ],
            }
        ),
    )

    response = client.get("/api/meta/agents/invocations")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["available"] is True
    assert payload["summary"]["bridgeRuns"] == 1
    assert payload["summary"]["bridgeFallbackRuns"] == 1
    assert payload["invocations"][0]["agentKind"] == "summary"
    assert payload["invocations"][1]["executionMode"] == "bridge"


def test_agent_smoke_uses_processed_chunk_and_summary_packet(client: TestClient, monkeypatch):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    register_response = _register_chunk(client, meeting_id, "client-chunk-7001", sequence=1)
    assert register_response.status_code == 200
    _process_chunk(client, meeting_id, "client-chunk-7001")

    from visualsprint_api.models import FinalReport, RegisterAgentOutputsRequest

    monkeypatch.setattr(
        "visualsprint_api.routes.agents.run_chunk_reasoning_with_source",
        lambda insight: (
            RegisterAgentOutputsRequest(
                clientChunkId=insight.clientChunkId,
                decisions=[
                    {
                        "title": "Smoke decision",
                        "rationale": "Smoke route exercised the reasoning adapter seam.",
                        "speakerLabel": "SmokeAgent",
                    }
                ],
                commitments=[],
                blockers=[],
                openQuestions=[],
                memoryMatches=[],
                resolvedDecisionIds=[],
                resolvedCommitmentIds=[],
                resolvedBlockerIds=[],
                resolvedOpenQuestionIds=[],
            ),
            "downstream_service",
        ),
    )
    monkeypatch.setattr(
        "visualsprint_api.routes.agents.run_summary_agent_with_source",
        lambda packet: (
            FinalReport(
                meetingId=packet.meetingId,
                generatedAt="2026-06-08T10:00:00Z",
                executiveSummary="Smoke summary output.",
                summarySource="downstream_service",
                decisions=packet.decisions,
                commitments=packet.commitments,
                blockers=packet.blockers,
                openQuestions=packet.openQuestions,
                memoryHighlights=packet.memoryHighlights,
            ),
            "downstream_service",
        ),
    )

    response = client.post(f"/api/meetings/{meeting_id}/agents/smoke")
    assert response.status_code == 200
    payload = response.json()
    assert payload["meetingId"] == meeting_id
    assert payload["reasoning"]["attempted"] is True
    assert payload["reasoning"]["selectedChunkId"] == "client-chunk-7001"
    assert payload["reasoning"]["source"] == "downstream_service"
    assert payload["reasoning"]["producedOutput"] is True
    assert payload["reasoning"]["decisionCount"] == 1
    assert payload["summary"]["attempted"] is True
    assert payload["summary"]["source"] == "downstream_service"
    assert payload["summary"]["producedOutput"] is True
    assert payload["summary"]["executiveSummaryLength"] > 0


def test_agent_smoke_handles_meeting_without_processed_chunk(client: TestClient):
    meeting_id = _create_live_browser_meeting(client)

    response = client.post(f"/api/meetings/{meeting_id}/agents/smoke")
    assert response.status_code == 200
    payload = response.json()
    assert payload["reasoning"]["attempted"] is False
    assert payload["reasoning"]["selectedChunkId"] is None
    assert payload["summary"]["attempted"] is True
    assert payload["summary"]["source"] == "local_fallback"


def test_chunk_processing_can_use_agents_reasoning_service(client: TestClient, monkeypatch):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    register_response = _register_chunk(client, meeting_id, "client-chunk-6001", sequence=1)
    assert register_response.status_code == 200

    from visualsprint_api.models import RegisterAgentOutputsRequest

    monkeypatch.setattr(
        "visualsprint_api.repository.run_chunk_reasoning_with_source",
        lambda insight: (
            RegisterAgentOutputsRequest(
                clientChunkId=insight.clientChunkId,
                decisions=[
                    {
                        "title": "Service-generated decision",
                        "rationale": "The agents service produced this reasoning output.",
                        "speakerLabel": "AgentsService",
                    }
                ],
                commitments=[],
                blockers=[],
                openQuestions=[],
                memoryMatches=[],
                resolvedDecisionIds=[],
                resolvedCommitmentIds=[],
                resolvedBlockerIds=[],
                resolvedOpenQuestionIds=[],
            ),
            "downstream_service",
        ),
    )

    _process_chunk(client, meeting_id, "client-chunk-6001")

    meeting_response = client.get(f"/api/meetings/{meeting_id}")
    assert meeting_response.status_code == 200
    meeting_payload = meeting_response.json()["meeting"]
    decisions = meeting_payload["recentDecisions"]
    assert any(decision["title"] == "Service-generated decision" for decision in decisions)
    assert meeting_payload["recentCaptureChunks"][0]["reasoningSource"] == "downstream_service"


def test_finalize_report_can_use_agents_summary_service(client: TestClient, monkeypatch):
    meeting_id = _create_live_browser_meeting(client)
    _start_capture_session(client, meeting_id)
    register_response = _register_chunk(client, meeting_id, "client-chunk-6101", sequence=1)
    assert register_response.status_code == 200
    _process_chunk(client, meeting_id, "client-chunk-6101")
    end_response = client.post(f"/api/meetings/{meeting_id}/end")
    assert end_response.status_code == 200

    from visualsprint_api.models import FinalReport

    monkeypatch.setattr(
        "visualsprint_api.repository.run_summary_agent_with_source",
        lambda packet: (
            FinalReport(
                meetingId=packet.meetingId,
                generatedAt="2026-06-07T10:00:00Z",
                executiveSummary="Agents service generated this final summary.",
                summarySource="downstream_service",
                decisions=packet.decisions,
                commitments=packet.commitments,
                blockers=packet.blockers,
                openQuestions=packet.openQuestions,
                memoryHighlights=packet.memoryHighlights,
            ),
            "downstream_service",
        ),
    )

    finalize_response = client.post(f"/api/meetings/{meeting_id}/final-report")
    assert finalize_response.status_code == 200
    assert finalize_response.json()["report"]["executiveSummary"] == "Agents service generated this final summary."
    assert finalize_response.json()["report"]["summarySource"] == "downstream_service"


def test_build_settings_supports_elastic_configuration():
    settings = build_settings(
        {
            "VISUALSPRINT_ENV": "production",
            "VISUALSPRINT_TRACK": "elastic",
            "VISUALSPRINT_AGENTS_SERVICE_URL": "https://agents.example",
            "VISUALSPRINT_INGEST_SERVICE_URL": "https://ingest.example",
            "VISUALSPRINT_MEDIA_SERVICE_URL": "https://media.example",
            "ELASTICSEARCH_URL": "https://elastic.example",
            "ELASTICSEARCH_API_KEY_SECRET": "projects/demo/secrets/elastic-api-key",
            "ELASTIC_INDEX_OUTCOMES": "visualsprint-outcomes",
            "ELASTIC_MCP_SERVER_URL": "https://elastic.example/mcp",
        }
    )

    assert settings.environment == "production"
    assert settings.elasticsearch_url_configured is True
    assert settings.elasticsearch_api_key_configured is True
    assert settings.elastic_mcp_server_configured is True
    assert settings.elastic_writeback_configured is True
    assert settings.elastic_index_outcomes == "visualsprint-outcomes"


def test_demo_seed_creates_populated_meeting(client: TestClient):
    response = client.post("/api/dev/demo-seed")
    assert response.status_code == 201
    payload = response.json()
    assert payload["meeting"]["title"] == "Release readiness sync"
    assert payload["meeting"]["status"] == "ended"
    assert payload["meeting"]["metrics"]["decisionsCount"] > 0
    assert payload["meeting"]["metrics"]["commitmentsCount"] > 0
    assert payload["meeting"]["metrics"]["blockersCount"] > 0
    assert payload["meeting"]["metrics"]["actionRecommendationsCount"] > 0


def test_demo_seed_not_available_when_disabled(client: TestClient, monkeypatch):
    import visualsprint_api.routes.dev as dev_module
    from visualsprint_api.config import build_settings

    monkeypatch.setattr(
        dev_module, "settings", build_settings({"VISUALSPRINT_ENV": "production"})
    )
    response = client.post("/api/dev/demo-seed")
    assert response.status_code == 403
