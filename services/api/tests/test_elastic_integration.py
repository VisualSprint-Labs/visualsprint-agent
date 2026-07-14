from __future__ import annotations

from datetime import datetime, timezone

from visualsprint_api.config import build_settings
from visualsprint_api.elastic_mapping import (
    build_elasticsearch_document_body,
    map_elastic_document_to_memory_match,
    map_indexed_outcome_to_elastic_document,
)
from visualsprint_api.models import EvidenceReference, IndexedOutcomeDocument, MemoryMatch


def test_indexed_outcome_mapping_builds_elastic_document():
    outcome = IndexedOutcomeDocument(
        id="dec_123",
        meetingId="mtg_123",
        recordType="decision",
        summary="Freeze the release path",
        detail="The team agreed to pause net-new work until auth stabilizes.",
        status="updated",
        ownerLabel=None,
        speakerLabel="Jordan",
        dueHint=None,
        severity=None,
        firstSeenChunkId="client-chunk-1234",
        lastUpdatedChunkId="client-chunk-1234",
        createdAt=datetime(2026, 6, 8, 10, 0, tzinfo=timezone.utc),
        updatedAt=datetime(2026, 6, 8, 10, 5, tzinfo=timezone.utc),
        evidence=[
            EvidenceReference(
                chunkId="chk_123",
                clientChunkId="client-chunk-1234",
                tStartMs=0,
                tEndMs=900,
                transcriptRef="trn_123",
                frameRef=None,
                note="Jordan: Freeze the release path until the auth issue is fixed.",
            )
        ],
    )

    document = map_indexed_outcome_to_elastic_document(
        meeting_title="Release planning",
        outcome=outcome,
    )
    body = build_elasticsearch_document_body(document)

    assert document.document_id == "default:mtg_123:dec_123"
    assert body["meeting_title"] == "Release planning"
    assert body["record_type"] == "decision"
    assert body["speaker_label"] == "Jordan"
    assert body["evidence"][0]["transcriptRef"] == "trn_123"


def test_elastic_document_mapping_can_build_memory_match():
    document = map_indexed_outcome_to_elastic_document(
        meeting_title="Release planning",
        outcome=IndexedOutcomeDocument(
            id="blk_123",
            meetingId="mtg_123",
            recordType="blocker",
            summary="Auth config drift is still blocking release",
            detail="Severity high; owner Avery.",
            status="resolved",
            ownerLabel="Avery",
            speakerLabel=None,
            dueHint=None,
            severity="high",
            firstSeenChunkId="client-chunk-1234",
            lastUpdatedChunkId="client-chunk-1235",
            createdAt=datetime(2026, 6, 8, 10, 0, tzinfo=timezone.utc),
            updatedAt=datetime(2026, 6, 8, 10, 5, tzinfo=timezone.utc),
            evidence=[],
        ),
    )

    match = map_elastic_document_to_memory_match(
        document=document,
        score=0.84,
        recorded_at=datetime(2026, 6, 8, 10, 10, tzinfo=timezone.utc),
    )

    assert isinstance(match, MemoryMatch)
    assert match.sourceMeetingId == "mtg_123"
    assert match.sourceMeetingTitle == "Release planning"
    assert match.relation == "resolved_previously"
    assert match.strength == "recurring"


def test_elastic_client_uses_resolved_api_key_for_authorization(monkeypatch):
    """The ApiKey header must use the resolved key value, not the secret name."""

    from urllib import request as urllib_request

    from visualsprint_api.elastic_client import _elastic_request_json

    config = build_settings(
        {
            "ELASTICSEARCH_URL": "https://elastic.example",
            "ELASTICSEARCH_API_KEY": "resolved-key-value",
            "ELASTICSEARCH_API_KEY_SECRET": "secret-name-placeholder",
            "ELASTIC_INDEX_OUTCOMES": "test-index",
        }
    )

    captured: dict = {}

    class FakeResponse:
        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(req, **kwargs):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["method"] = req.get_method()
        return FakeResponse()

    monkeypatch.setattr(urllib_request, "urlopen", fake_urlopen)

    result = _elastic_request_json(
        config=config,
        method="POST",
        path="/test-index/_search",
        payload={"query": {"match_all": {}}},
    )

    assert result == {"ok": True}
    auth_header = captured["headers"].get("Authorization", "")
    assert auth_header == "ApiKey resolved-key-value"
    assert "secret-name-placeholder" not in auth_header
