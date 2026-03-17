from __future__ import annotations

import base64
from datetime import UTC, datetime
from typing import Any

from app.domain.ingestion.connectors import SourceCollectRequest


class FakeTransport:
    def __init__(self) -> None:
        self.post_calls: list[dict[str, Any]] = []
        self.get_calls: list[dict[str, Any]] = []
        self.next_post_response: dict[str, Any] = {}
        self.next_get_response: dict[str, Any] = {}

    def post_form(
        self, *, url: str, headers: dict[str, str], data: dict[str, str]
    ) -> dict[str, Any]:
        self.post_calls.append({"url": url, "headers": headers, "data": data})
        return self.next_post_response

    def get_json(
        self, *, url: str, headers: dict[str, str], params: dict[str, str]
    ) -> dict[str, Any]:
        self.get_calls.append({"url": url, "headers": headers, "params": params})
        return self.next_get_response


def test_reddit_api_client_fetch_access_token_uses_basic_auth() -> None:
    from app.infrastructure.sources.reddit import RedditApiClient, RedditCredentials

    transport = FakeTransport()
    transport.next_post_response = {"access_token": "token-123"}
    credentials = RedditCredentials(
        client_id="my-client-id",
        client_secret="my-client-secret",
        user_agent="content-factory-test/0.1",
    )

    api_client = RedditApiClient(credentials=credentials, transport=transport)
    token = api_client.fetch_access_token()

    assert token == "token-123"
    assert len(transport.post_calls) == 1

    call = transport.post_calls[0]
    expected_auth = base64.b64encode(b"my-client-id:my-client-secret").decode()
    assert call["url"] == "https://www.reddit.com/api/v1/access_token"
    assert call["headers"]["Authorization"] == f"Basic {expected_auth}"
    assert call["headers"]["User-Agent"] == "content-factory-test/0.1"
    assert call["data"] == {"grant_type": "client_credentials"}


def test_reddit_api_client_search_posts_parses_children_data() -> None:
    from app.infrastructure.sources.reddit import RedditApiClient, RedditCredentials

    transport = FakeTransport()
    transport.next_get_response = {
        "data": {
            "children": [
                {"data": {"id": "p1", "title": "First"}},
                {"data": {"id": "p2", "title": "Second"}},
                {"kind": "t3"},
            ]
        }
    }
    credentials = RedditCredentials(
        client_id="id",
        client_secret="secret",
        user_agent="content-factory-test/0.1",
    )

    api_client = RedditApiClient(credentials=credentials, transport=transport)
    posts = api_client.search_posts(token="token-xyz", query="ai agents", limit=3)

    assert [post["id"] for post in posts] == ["p1", "p2"]
    assert len(transport.get_calls) == 1

    call = transport.get_calls[0]
    assert call["url"] == "https://oauth.reddit.com/search"
    assert call["headers"]["Authorization"] == "Bearer token-xyz"
    assert call["params"]["q"] == "ai agents"
    assert call["params"]["limit"] == "3"


class FakeRedditApiClient:
    def __init__(self, responses_by_query: dict[str, list[dict[str, Any]]]) -> None:
        self.responses_by_query = responses_by_query
        self.fetch_calls = 0
        self.search_calls: list[dict[str, Any]] = []

    def fetch_access_token(self) -> str:
        self.fetch_calls += 1
        return "token-123"

    def search_posts(self, *, token: str, query: str, limit: int) -> list[dict[str, Any]]:
        self.search_calls.append({"token": token, "query": query, "limit": limit})
        return self.responses_by_query.get(query, [])


def test_reddit_connector_collect_maps_and_deduplicates_posts() -> None:
    from app.infrastructure.sources.reddit import RedditSourceConnector

    api_client = FakeRedditApiClient(
        responses_by_query={
            "ai agent": [
                {
                    "id": "a1",
                    "title": "Using AI agent in a clinic",
                    "created_utc": 1710000000,
                    "permalink": "/r/startups/comments/a1/topic/",
                    "subreddit": "startups",
                    "author": "founder1",
                    "score": 12,
                    "num_comments": 3,
                    "url": "https://example.com/a1",
                }
            ],
            "automation": [
                {
                    "id": "a1",
                    "title": "Duplicate across query",
                    "created_utc": 1710000000,
                    "permalink": "/r/startups/comments/a1/topic/",
                    "subreddit": "startups",
                    "author": "founder1",
                    "score": 12,
                    "num_comments": 3,
                    "url": "https://example.com/a1",
                },
                {
                    "id": "b2",
                    "title": "Automation workflow ideas",
                    "created_utc": 1715000000,
                    "subreddit": "entrepreneur",
                    "author": "builder2",
                    "score": 44,
                    "num_comments": 9,
                    "url": "https://example.com/b2",
                },
            ],
        }
    )
    connector = RedditSourceConnector(api_client=api_client, max_posts_per_keyword=25)

    collected = connector.collect(
        SourceCollectRequest(
            keywords=["ai agent", "automation"],
            regions=["US", "CA", "EU"],
            language="en",
            limit=5,
        )
    )

    assert len(collected) == 2
    assert collected[0].source == "reddit"
    assert collected[0].source_signal_id == "a1"
    assert collected[0].published_at == datetime.fromtimestamp(1710000000, tz=UTC)
    assert collected[0].url == "https://reddit.com/r/startups/comments/a1/topic/"
    assert collected[0].metadata["query"] == "ai agent"
    assert collected[0].engagement == {"upvotes": 12, "comments": 3}

    assert collected[1].source_signal_id == "b2"
    assert collected[1].url == "https://example.com/b2"
    assert collected[1].metadata["query"] == "automation"

    assert api_client.fetch_calls == 1
    assert len(api_client.search_calls) == 2
    assert api_client.search_calls[0]["limit"] == 5


def test_reddit_connector_returns_empty_when_no_keywords() -> None:
    from app.infrastructure.sources.reddit import RedditSourceConnector

    api_client = FakeRedditApiClient(responses_by_query={})
    connector = RedditSourceConnector(api_client=api_client)

    collected = connector.collect(
        SourceCollectRequest(
            keywords=[],
            regions=["US"],
            language="en",
            limit=10,
        )
    )

    assert collected == []
    assert api_client.fetch_calls == 0
