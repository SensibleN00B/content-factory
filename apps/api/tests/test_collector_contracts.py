from __future__ import annotations

from datetime import UTC, datetime

from app.domain.ingestion.connectors import SourceCollectedSignal, SourceCollectRequest
from app.infrastructure.sources.google_trends import GoogleTrendsSourceConnector
from app.infrastructure.sources.hackernews import HackerNewsSourceConnector
from app.infrastructure.sources.producthunt import ProductHuntSourceConnector
from app.infrastructure.sources.reddit import RedditSourceConnector
from app.infrastructure.sources.youtube import YouTubeSourceConnector


def make_request() -> SourceCollectRequest:
    return SourceCollectRequest(
        keywords=["ai"],
        regions=["US"],
        language="en",
        limit=5,
    )


def assert_contract(signal: SourceCollectedSignal, *, expected_source: str) -> None:
    assert signal.source == expected_source
    assert isinstance(signal.raw_payload, dict)
    assert isinstance(signal.metadata, dict)
    assert isinstance(signal.engagement, dict)
    if signal.url is not None:
        assert isinstance(signal.url, str)
    if signal.title is not None:
        assert isinstance(signal.title, str)
    if signal.published_at is not None:
        assert isinstance(signal.published_at, datetime)


def test_reddit_connector_contract() -> None:
    class StubRedditClient:
        def fetch_access_token(self) -> str:
            return "token"

        def search_posts(self, *, token: str, query: str, limit: int) -> list[dict]:
            return [
                {
                    "id": "r1",
                    "title": "AI receptionist for clinics",
                    "url": "https://example.com/r1",
                    "created_utc": 1_710_000_000,
                    "author": "founder",
                    "subreddit": "startups",
                    "score": 10,
                    "num_comments": 2,
                }
            ]

    connector = RedditSourceConnector(api_client=StubRedditClient())
    signals = connector.collect(make_request())

    assert len(signals) == 1
    assert_contract(signals[0], expected_source="reddit")


def test_hackernews_connector_contract() -> None:
    class StubHNClient:
        def search_posts(self, *, query: str, limit: int) -> list[dict]:
            return [
                {
                    "objectID": "h1",
                    "title": "AI workflow for clinics",
                    "url": "https://example.com/h1",
                    "created_at": "2026-03-17T10:00:00Z",
                    "author": "founder",
                    "points": 20,
                    "num_comments": 5,
                }
            ]

    connector = HackerNewsSourceConnector(api_client=StubHNClient())
    signals = connector.collect(make_request())

    assert len(signals) == 1
    assert_contract(signals[0], expected_source="hackernews")


def test_google_trends_connector_contract() -> None:
    class StubGoogleClient:
        def fetch_daily_trends(self, *, region: str, language: str, limit: int) -> list[dict]:
            return [
                {
                    "__date": "20260317",
                    "title": {"query": "AI clinic workflow"},
                    "formattedTraffic": "12K+",
                    "relatedQueries": [{"query": "AI automation"}],
                    "articles": [{"url": "https://example.com/g1"}],
                }
            ]

    connector = GoogleTrendsSourceConnector(api_client=StubGoogleClient())
    signals = connector.collect(make_request())

    assert len(signals) == 1
    assert_contract(signals[0], expected_source="google_trends")


def test_producthunt_connector_contract() -> None:
    class StubProductHuntClient:
        def fetch_access_token(self) -> str:
            return "token"

        def fetch_posts(self, *, token: str, limit: int) -> list[dict]:
            return [
                {
                    "id": "p1",
                    "name": "AgentFlow",
                    "tagline": "AI automation for clinic workflows",
                    "description": "AI tool for clinic operations",
                    "url": "https://example.com/p1",
                    "createdAt": "2026-03-17T08:00:00Z",
                    "votesCount": 50,
                    "commentsCount": 8,
                    "topics": {"edges": [{"node": {"name": "Artificial Intelligence"}}]},
                }
            ]

    connector = ProductHuntSourceConnector(api_client=StubProductHuntClient())
    signals = connector.collect(make_request())

    assert len(signals) == 1
    assert_contract(signals[0], expected_source="producthunt")


def test_youtube_connector_contract() -> None:
    class StubYouTubeClient:
        def search_videos(
            self, *, query: str, limit: int, region: str, language: str
        ) -> list[dict]:
            return [
                {
                    "id": {"videoId": "y1"},
                    "snippet": {
                        "title": "AI clinic automation walkthrough",
                        "description": "How clinics adopt AI workflows",
                        "publishedAt": datetime(2026, 3, 17, 9, 0, 0, tzinfo=UTC).isoformat(),
                        "channelTitle": "Founder Ops",
                    },
                }
            ]

    connector = YouTubeSourceConnector(api_client=StubYouTubeClient())
    signals = connector.collect(make_request())

    assert len(signals) == 1
    assert_contract(signals[0], expected_source="youtube")
