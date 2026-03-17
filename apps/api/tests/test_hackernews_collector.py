from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.ingestion.connectors import SourceCollectRequest


class FakeTransport:
    def __init__(self) -> None:
        self.get_calls: list[dict[str, Any]] = []
        self.next_get_response: dict[str, Any] = {}

    def get_json(
        self, *, url: str, headers: dict[str, str], params: dict[str, str]
    ) -> dict[str, Any]:
        self.get_calls.append({"url": url, "headers": headers, "params": params})
        return self.next_get_response


def test_hn_api_client_search_posts_parses_hits() -> None:
    from app.infrastructure.sources.hackernews import HackerNewsApiClient

    transport = FakeTransport()
    transport.next_get_response = {
        "hits": [
            {"objectID": "1", "title": "First"},
            {"objectID": "2", "title": "Second"},
        ]
    }

    api_client = HackerNewsApiClient(transport=transport)
    posts = api_client.search_posts(query="ai agents", limit=3)

    assert [post["objectID"] for post in posts] == ["1", "2"]
    assert len(transport.get_calls) == 1
    call = transport.get_calls[0]
    assert call["url"] == "https://hn.algolia.com/api/v1/search_by_date"
    assert call["params"]["query"] == "ai agents"
    assert call["params"]["hitsPerPage"] == "3"
    assert call["params"]["tags"] == "story"


class FakeHnApiClient:
    def __init__(self, responses_by_query: dict[str, list[dict[str, Any]]]) -> None:
        self.responses_by_query = responses_by_query
        self.search_calls: list[dict[str, Any]] = []

    def search_posts(self, *, query: str, limit: int) -> list[dict[str, Any]]:
        self.search_calls.append({"query": query, "limit": limit})
        return self.responses_by_query.get(query, [])


def test_hn_connector_collect_maps_and_deduplicates_posts() -> None:
    from app.infrastructure.sources.hackernews import HackerNewsSourceConnector

    api_client = FakeHnApiClient(
        responses_by_query={
            "ai agent": [
                {
                    "objectID": "a1",
                    "title": "AI agents in SaaS",
                    "url": "https://example.com/a1",
                    "created_at": "2026-03-17T08:00:00Z",
                    "author": "founder1",
                    "points": 42,
                    "num_comments": 11,
                }
            ],
            "automation": [
                {
                    "objectID": "a1",
                    "title": "Duplicate",
                    "url": "https://example.com/a1",
                    "created_at": "2026-03-17T08:00:00Z",
                    "author": "founder1",
                    "points": 42,
                    "num_comments": 11,
                },
                {
                    "objectID": "b2",
                    "title": "Automating support operations",
                    "created_at": "2026-03-17T09:30:00Z",
                    "author": "builder2",
                    "points": 18,
                    "num_comments": 4,
                },
            ],
        }
    )
    connector = HackerNewsSourceConnector(api_client=api_client, max_posts_per_keyword=30)

    collected = connector.collect(
        SourceCollectRequest(
            keywords=["ai agent", "automation"],
            regions=["US", "CA", "EU"],
            language="en",
            limit=5,
        )
    )

    assert len(collected) == 2
    assert collected[0].source == "hackernews"
    assert collected[0].source_signal_id == "a1"
    assert collected[0].published_at == datetime(2026, 3, 17, 8, 0, tzinfo=UTC)
    assert collected[0].url == "https://example.com/a1"
    assert collected[0].metadata["query"] == "ai agent"
    assert collected[0].engagement == {"points": 42, "comments": 11}

    assert collected[1].source_signal_id == "b2"
    assert collected[1].url == "https://news.ycombinator.com/item?id=b2"
    assert collected[1].metadata["query"] == "automation"

    assert len(api_client.search_calls) == 2
    assert api_client.search_calls[0]["limit"] == 5


def test_hn_connector_returns_empty_when_no_keywords() -> None:
    from app.infrastructure.sources.hackernews import HackerNewsSourceConnector

    api_client = FakeHnApiClient(responses_by_query={})
    connector = HackerNewsSourceConnector(api_client=api_client)

    collected = connector.collect(
        SourceCollectRequest(
            keywords=[],
            regions=["US"],
            language="en",
            limit=10,
        )
    )

    assert collected == []
    assert api_client.search_calls == []
