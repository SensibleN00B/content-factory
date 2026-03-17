from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.ingestion.connectors import SourceCollectRequest


class FakeTransport:
    def __init__(self) -> None:
        self.post_calls: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any]] = []

    def post_json(
        self, *, url: str, headers: dict[str, str], body: dict[str, Any]
    ) -> dict[str, Any]:
        self.post_calls.append({"url": url, "headers": headers, "body": body})
        if not self.responses:
            return {}
        return self.responses.pop(0)


def test_producthunt_api_client_fetch_access_token_uses_client_credentials() -> None:
    from app.infrastructure.sources.producthunt import ProductHuntApiClient, ProductHuntCredentials

    transport = FakeTransport()
    transport.responses = [{"access_token": "ph-token-123"}]
    credentials = ProductHuntCredentials(
        client_id="ph-client-id",
        client_secret="ph-client-secret",
    )

    api_client = ProductHuntApiClient(credentials=credentials, transport=transport)
    token = api_client.fetch_access_token()

    assert token == "ph-token-123"
    assert len(transport.post_calls) == 1

    call = transport.post_calls[0]
    assert call["url"] == "https://api.producthunt.com/v2/oauth/token"
    assert call["body"]["client_id"] == "ph-client-id"
    assert call["body"]["client_secret"] == "ph-client-secret"
    assert call["body"]["grant_type"] == "client_credentials"


def test_producthunt_api_client_fetch_posts_parses_graphql_edges() -> None:
    from app.infrastructure.sources.producthunt import ProductHuntApiClient, ProductHuntCredentials

    transport = FakeTransport()
    transport.responses = [
        {
            "data": {
                "posts": {
                    "edges": [
                        {"node": {"id": "p1", "name": "First Product"}},
                        {"node": {"id": "p2", "name": "Second Product"}},
                        {"cursor": "x"},
                    ]
                }
            }
        }
    ]
    credentials = ProductHuntCredentials(client_id="id", client_secret="secret")

    api_client = ProductHuntApiClient(credentials=credentials, transport=transport)
    posts = api_client.fetch_posts(token="ph-token", limit=2)

    assert [post["id"] for post in posts] == ["p1", "p2"]
    assert len(transport.post_calls) == 1

    call = transport.post_calls[0]
    assert call["url"] == "https://api.producthunt.com/v2/api/graphql"
    assert call["headers"]["Authorization"] == "Bearer ph-token"
    assert call["body"]["variables"]["first"] == 2
    assert "posts" in call["body"]["query"]


class FakeProductHuntApiClient:
    def __init__(self, posts: list[dict[str, Any]]) -> None:
        self.posts = posts
        self.fetch_token_calls = 0
        self.fetch_posts_calls: list[dict[str, Any]] = []

    def fetch_access_token(self) -> str:
        self.fetch_token_calls += 1
        return "ph-token"

    def fetch_posts(self, *, token: str, limit: int) -> list[dict[str, Any]]:
        self.fetch_posts_calls.append({"token": token, "limit": limit})
        return self.posts


def test_producthunt_connector_collect_maps_and_filters_posts() -> None:
    from app.infrastructure.sources.producthunt import ProductHuntSourceConnector

    api_client = FakeProductHuntApiClient(
        posts=[
            {
                "id": "p1",
                "name": "Voice AI Receptionist",
                "tagline": "AI receptionist for clinics",
                "description": "Automate inbound clinic calls",
                "url": "https://www.producthunt.com/posts/voice-ai-receptionist",
                "website": "https://example.com/p1",
                "createdAt": "2026-03-17T09:15:00Z",
                "votesCount": 212,
                "commentsCount": 17,
                "topics": {"edges": [{"node": {"name": "Artificial Intelligence"}}]},
            },
            {
                "id": "p1",
                "name": "Duplicate",
                "tagline": "Duplicate item",
                "description": "Duplicate",
                "url": "https://www.producthunt.com/posts/voice-ai-receptionist",
                "createdAt": "2026-03-17T09:15:00Z",
                "votesCount": 212,
                "commentsCount": 17,
                "topics": {"edges": []},
            },
            {
                "id": "p2",
                "name": "Automation Ops Toolkit",
                "tagline": "Workflow automation for founders",
                "description": "Automation recipes for SMB teams",
                "url": "https://www.producthunt.com/posts/automation-ops-toolkit",
                "createdAt": "2026-03-17T10:00:00Z",
                "votesCount": 98,
                "commentsCount": 8,
                "topics": {"edges": [{"node": {"name": "Productivity"}}]},
            },
            {
                "id": "p3",
                "name": "Gaming Skin Tracker",
                "tagline": "Track skin prices",
                "description": "For gamers",
                "url": "https://www.producthunt.com/posts/gaming-skin-tracker",
                "createdAt": "2026-03-17T11:00:00Z",
                "votesCount": 120,
                "commentsCount": 10,
                "topics": {"edges": [{"node": {"name": "Gaming"}}]},
            },
        ]
    )
    connector = ProductHuntSourceConnector(api_client=api_client, max_posts=30)

    collected = connector.collect(
        SourceCollectRequest(
            keywords=["ai", "automation"],
            regions=["US", "CA", "EU"],
            language="en",
            limit=5,
        )
    )

    assert len(collected) == 2
    assert collected[0].source == "producthunt"
    assert collected[0].source_signal_id == "p1"
    assert collected[0].published_at == datetime(2026, 3, 17, 9, 15, tzinfo=UTC)
    assert collected[0].metadata["query_match"] == "ai"
    assert collected[0].engagement == {"votes": 212, "comments": 17}
    assert "Artificial Intelligence" in collected[0].metadata["topics"]

    assert collected[1].source_signal_id == "p2"
    assert collected[1].metadata["query_match"] == "automation"

    assert api_client.fetch_token_calls == 1
    assert len(api_client.fetch_posts_calls) == 1
    assert api_client.fetch_posts_calls[0]["limit"] == 5


def test_producthunt_connector_returns_empty_when_no_keywords() -> None:
    from app.infrastructure.sources.producthunt import ProductHuntSourceConnector

    api_client = FakeProductHuntApiClient(posts=[])
    connector = ProductHuntSourceConnector(api_client=api_client)

    collected = connector.collect(
        SourceCollectRequest(
            keywords=[],
            regions=["US"],
            language="en",
            limit=10,
        )
    )

    assert collected == []
    assert api_client.fetch_token_calls == 0
