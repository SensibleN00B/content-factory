from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.ingestion.connectors import SourceCollectRequest


class FakeTransport:
    def __init__(self) -> None:
        self.get_calls: list[dict[str, Any]] = []
        self.next_response: dict[str, Any] = {}

    def get_json(
        self, *, url: str, headers: dict[str, str], params: dict[str, str]
    ) -> dict[str, Any]:
        self.get_calls.append({"url": url, "headers": headers, "params": params})
        return self.next_response


def test_youtube_api_client_search_videos_parses_items_and_params() -> None:
    from app.infrastructure.sources.youtube import YouTubeApiClient, YouTubeCredentials

    transport = FakeTransport()
    transport.next_response = {
        "items": [
            {"id": {"videoId": "v1"}, "snippet": {"title": "First"}},
            {"id": {"videoId": "v2"}, "snippet": {"title": "Second"}},
        ]
    }
    credentials = YouTubeCredentials(api_key="yt-api-key")

    api_client = YouTubeApiClient(credentials=credentials, transport=transport)
    items = api_client.search_videos(
        query="ai automation",
        limit=3,
        region="US",
        language="en",
    )

    assert len(items) == 2
    assert items[0]["id"]["videoId"] == "v1"
    assert len(transport.get_calls) == 1

    call = transport.get_calls[0]
    assert call["url"] == "https://www.googleapis.com/youtube/v3/search"
    assert call["params"]["key"] == "yt-api-key"
    assert call["params"]["q"] == "ai automation"
    assert call["params"]["maxResults"] == "3"
    assert call["params"]["regionCode"] == "US"
    assert call["params"]["relevanceLanguage"] == "en"


class FakeYouTubeApiClient:
    def __init__(
        self,
        responses_by_query: dict[str, list[dict[str, Any]]],
        quota_failure_query: str | None = None,
    ) -> None:
        self.responses_by_query = responses_by_query
        self.quota_failure_query = quota_failure_query
        self.search_calls: list[dict[str, Any]] = []

    def search_videos(
        self, *, query: str, limit: int, region: str, language: str
    ) -> list[dict[str, Any]]:
        self.search_calls.append(
            {"query": query, "limit": limit, "region": region, "language": language}
        )
        if self.quota_failure_query is not None and query == self.quota_failure_query:
            from app.infrastructure.sources.youtube import YouTubeQuotaExceededError

            raise YouTubeQuotaExceededError("quota exceeded")
        return self.responses_by_query.get(query, [])


def test_youtube_connector_collect_maps_and_deduplicates_videos() -> None:
    from app.infrastructure.sources.youtube import YouTubeSourceConnector

    api_client = FakeYouTubeApiClient(
        responses_by_query={
            "ai": [
                {
                    "id": {"videoId": "v1"},
                    "snippet": {
                        "title": "AI automation ideas for founders",
                        "description": "Practical AI workflow setup",
                        "publishedAt": "2026-03-17T10:00:00Z",
                        "channelTitle": "Builder Channel",
                    },
                }
            ],
            "automation": [
                {
                    "id": {"videoId": "v1"},
                    "snippet": {
                        "title": "Duplicate video",
                        "description": "Duplicate",
                        "publishedAt": "2026-03-17T10:00:00Z",
                        "channelTitle": "Builder Channel",
                    },
                },
                {
                    "id": {"videoId": "v2"},
                    "snippet": {
                        "title": "Automation workflows for SMB teams",
                        "description": "No-code automation stack",
                        "publishedAt": "2026-03-17T11:30:00Z",
                        "channelTitle": "Ops Lab",
                    },
                },
            ],
        }
    )
    connector = YouTubeSourceConnector(api_client=api_client, max_videos_per_keyword=20)

    collected = connector.collect(
        SourceCollectRequest(
            keywords=["ai", "automation"],
            regions=["US", "CA", "EU"],
            language="en",
            limit=5,
        )
    )

    assert len(collected) == 2
    assert collected[0].source == "youtube"
    assert collected[0].source_signal_id == "v1"
    assert collected[0].title == "AI automation ideas for founders"
    assert collected[0].url == "https://www.youtube.com/watch?v=v1"
    assert collected[0].published_at == datetime(2026, 3, 17, 10, 0, tzinfo=UTC)
    assert collected[0].metadata["query"] == "ai"
    assert collected[0].metadata["channel_title"] == "Builder Channel"
    assert collected[0].engagement == {"views": 0, "likes": 0, "comments": 0}

    assert collected[1].source_signal_id == "v2"
    assert collected[1].metadata["query"] == "automation"

    assert len(api_client.search_calls) == 2
    assert api_client.search_calls[0]["limit"] == 5
    assert api_client.search_calls[0]["region"] == "US"


def test_youtube_connector_stops_on_quota_exceeded() -> None:
    from app.infrastructure.sources.youtube import YouTubeSourceConnector

    api_client = FakeYouTubeApiClient(
        responses_by_query={
            "ai": [
                {
                    "id": {"videoId": "v1"},
                    "snippet": {
                        "title": "AI ops",
                        "description": "AI",
                        "publishedAt": "2026-03-17T10:00:00Z",
                        "channelTitle": "Builder",
                    },
                }
            ]
        },
        quota_failure_query="automation",
    )
    connector = YouTubeSourceConnector(api_client=api_client)

    collected = connector.collect(
        SourceCollectRequest(
            keywords=["ai", "automation", "agent"],
            regions=["US"],
            language="en",
            limit=10,
        )
    )

    assert len(collected) == 1
    assert collected[0].source_signal_id == "v1"
    assert [call["query"] for call in api_client.search_calls] == ["ai", "automation"]


def test_youtube_connector_returns_empty_when_no_keywords() -> None:
    from app.infrastructure.sources.youtube import YouTubeSourceConnector

    api_client = FakeYouTubeApiClient(responses_by_query={})
    connector = YouTubeSourceConnector(api_client=api_client)

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
