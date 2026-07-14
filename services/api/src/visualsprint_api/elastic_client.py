"""Small Elastic client for deterministic outcome write-back and lookup."""

from __future__ import annotations

import json
import logging
from urllib import error, parse, request

from visualsprint_api.config import Settings
from visualsprint_api.elastic_mapping import (
    build_elasticsearch_document_body,
    map_elastic_document_to_memory_match,
    map_indexed_outcome_to_elastic_document,
)
from visualsprint_api.elastic_models import ElasticOutcomeDocument
from visualsprint_api.models import (
    IndexedOutcomeDocument,
    MeetingDetail,
    MemoryMatch,
    SearchPriorOutcomesRequest,
)

logger = logging.getLogger("visualsprint_api.elastic")


def upsert_indexed_outcomes_to_elasticsearch(
    *,
    config: Settings,
    meeting: MeetingDetail,
    documents: list[IndexedOutcomeDocument],
) -> int | None:
    if not config.elastic_writeback_configured or not config.elastic_index_outcomes:
        return None

    upserted = 0
    for outcome in documents:
        elastic_document = map_indexed_outcome_to_elastic_document(
            meeting_title=meeting.title,
            outcome=outcome,
        )
        path = (
            f"/{parse.quote(config.elastic_index_outcomes, safe='')}/_doc/"
            f"{parse.quote(elastic_document.document_id, safe='')}"
        )
        payload = build_elasticsearch_document_body(elastic_document)
        response = _elastic_request_json(
            config=config,
            method="PUT",
            path=path,
            payload=payload,
        )
        if response is None:
            return None
        upserted += 1
    return upserted


def search_prior_outcomes_in_elasticsearch(
    *,
    config: Settings,
    meeting: MeetingDetail,
    payload: SearchPriorOutcomesRequest,
) -> list[MemoryMatch] | None:
    if not config.elastic_writeback_configured or not config.elastic_index_outcomes:
        return None

    query_text = " ".join(part for part in (payload.summary, payload.detail) if part.strip())
    body = {
        "size": 3,
        "_source": True,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"tenant_id": "default"}},
                    {"term": {"record_type": payload.recordType}},
                ],
                "should": [
                    {"match": {"summary": {"query": payload.summary, "boost": 3}}},
                    {"match": {"detail": {"query": payload.detail, "boost": 2}}},
                    {
                        "multi_match": {
                            "query": query_text,
                            "fields": ["summary^3", "detail^2", "meeting_title"],
                        }
                    },
                ],
                "minimum_should_match": 1,
            }
        },
    }
    response = _elastic_request_json(
        config=config,
        method="POST",
        path=f"/{parse.quote(config.elastic_index_outcomes, safe='')}/_search",
        payload=body,
    )
    if response is None:
        return None

    hits = response.get("hits", {}).get("hits", [])
    matches: list[MemoryMatch] = []
    for hit in hits[:3]:
        source = hit.get("_source")
        if not isinstance(source, dict):
            continue
        try:
            document = ElasticOutcomeDocument.model_validate(source)
        except ValueError:
            continue
        raw_score = hit.get("_score", 0.0)
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0
        normalized_score = max(0.0, min(score / 10.0, 1.0))
        matches.append(
            map_elastic_document_to_memory_match(
                document=document,
                score=normalized_score,
                recorded_at=meeting.createdAt,
            )
        )
    return matches


def search_outcomes_in_elasticsearch(
    *,
    config: Settings,
    query: str,
    record_type: str | None,
    limit: int,
) -> list[tuple[ElasticOutcomeDocument, float]] | None:
    """Free-text search across every indexed meeting outcome (organizational memory).

    Returns (document, normalized_score) pairs, or None when Elastic write-back is
    not configured so the caller can signal "search unavailable" rather than faking
    results.
    """
    if not config.elastic_writeback_configured or not config.elastic_index_outcomes:
        return None

    size = max(1, min(limit, 50))
    trimmed = query.strip()
    filters: list[dict] = [{"term": {"tenant_id": "default"}}]
    if record_type:
        filters.append({"term": {"record_type": record_type}})

    if trimmed:
        bool_query: dict = {
            "filter": filters,
            "should": [
                {
                    "multi_match": {
                        "query": trimmed,
                        "fields": ["summary^3", "detail^2", "meeting_title", "owner_label"],
                        "fuzziness": "AUTO",
                    }
                }
            ],
            "minimum_should_match": 1,
        }
    else:
        # No query text: browse the most recent outcomes (optionally filtered).
        bool_query = {"filter": filters}

    path = f"/{parse.quote(config.elastic_index_outcomes, safe='')}/_search"
    base_body = {"size": size, "_source": True, "query": {"bool": bool_query}}
    sort_clause = (
        ["_score", {"updated_at": {"order": "desc", "unmapped_type": "date"}}]
        if trimmed
        else [{"updated_at": {"order": "desc", "unmapped_type": "date"}}]
    )

    # Prefer recency-sorted results, but a site whose `updated_at` is mapped as
    # text would reject the sort — fall back to an unsorted query so search still
    # works rather than silently returning nothing.
    response = _elastic_request_json(
        config=config, method="POST", path=path, payload={**base_body, "sort": sort_clause}
    )
    if response is None:
        response = _elastic_request_json(
            config=config, method="POST", path=path, payload=base_body
        )
    if response is None:
        return None

    hits = response.get("hits", {}).get("hits", [])
    results: list[tuple[ElasticOutcomeDocument, float]] = []
    for hit in hits[:size]:
        source = hit.get("_source")
        if not isinstance(source, dict):
            continue
        try:
            document = ElasticOutcomeDocument.model_validate(source)
        except ValueError:
            continue
        try:
            raw_score = float(hit.get("_score") or 0.0)
        except (TypeError, ValueError):
            raw_score = 0.0
        results.append((document, max(0.0, min(raw_score / 10.0, 1.0))))
    return results


def _elastic_request_json(
    *,
    config: Settings,
    method: str,
    path: str,
    payload: dict,
) -> dict | None:
    api_key = config.elasticsearch_api_key or config.elasticsearch_api_key_secret
    if not config.elasticsearch_url or not api_key:
        return None

    base_url = config.elasticsearch_url.rstrip("/")
    url = f"{base_url}{path}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"ApiKey {api_key}",
    }
    try:
        response = request.urlopen(
            request.Request(
                url=url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method=method,
            ),
            timeout=config.service_request_timeout_seconds,
        )
        return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        logger.warning(
            "Elasticsearch %s %s returned HTTP %s: %s",
            method,
            path,
            exc.code,
            body,
        )
        return None
    except (error.URLError, TimeoutError) as exc:
        logger.warning("Elasticsearch %s %s failed: %s", method, path, exc)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("Elasticsearch %s %s returned invalid JSON: %s", method, path, exc)
        return None
