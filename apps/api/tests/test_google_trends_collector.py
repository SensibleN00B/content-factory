from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.domain.ingestion.connectors import SourceCollectRequest


class FakeTextTransport:
    def __init__(self) -> None:
        self.get_calls: list[dict[str, Any]] = []
        self.next_text_response: str = "{}"

    def get_text(self, *, url: str, headers: dict[str, str], params: dict[str, str]) -> str:
        self.get_calls.append({"url": url, "headers": headers, "params": params})
        return self.next_text_response


def test_google_trends_api_client_fetch_daily_trends_parses_xssi_payload() -> None:
    from app.infrastructure.sources.google_trends import GoogleTrendsApiClient

    payload = {
        "default": {
            "trendingSearchesDays": [
                {
                    "date": "20260317",
                    "trendingSearches": [
                        {"title": {"query": "AI agent tools"}},
                        {"title": {"query": "Automation for SMB"}},
                    ],
                }
            ]
        }
    }
    transport = FakeTextTransport()
    transport.next_text_response = ")]}',\n" + json.dumps(payload)

    client = GoogleTrendsApiClient(transport=transport)
    trends = client.fetch_daily_trends(region="US", language="en", limit=1)

    assert len(trends) == 1
    assert trends[0]["title"]["query"] == "AI agent tools"
    assert trends[0]["__date"] == "20260317"
    assert len(transport.get_calls) == 1

    call = transport.get_calls[0]
    assert call["url"] == "https://trends.google.com/trends/api/dailytrends"
    assert call["params"]["geo"] == "US"
    assert call["params"]["hl"] == "en-US"
    assert call["params"]["tz"] == "0"


class FakeGoogleTrendsApiClient:
    def __init__(
        self,
        responses_by_region: dict[str, list[dict[str, Any]]],
        failing_regions: set[str] | None = None,
    ) -> None:
        self.responses_by_region = responses_by_region
        self.failing_regions = failing_regions or set()
        self.calls: list[dict[str, Any]] = []

    def fetch_daily_trends(self, *, region: str, language: str, limit: int) -> list[dict[str, Any]]:
        self.calls.append({"region": region, "language": language, "limit": limit})
        if region in self.failing_regions:
            raise RuntimeError(f"region failure: {region}")
        return self.responses_by_region.get(region, [])


def test_google_trends_connector_collect_maps_and_deduplicates() -> None:
    from app.infrastructure.sources.google_trends import GoogleTrendsSourceConnector

    api_client = FakeGoogleTrendsApiClient(
        responses_by_region={
            "US": [
                {
                    "__date": "20260317",
                    "title": {"query": "AI agent tools for clinics"},
                    "formattedTraffic": "200K+",
                    "articles": [{"url": "https://example.com/a1"}],
                    "relatedQueries": [{"query": "voice ai agent"}],
                },
                {
                    "__date": "20260317",
                    "title": {"query": "Sports highlights"},
                    "formattedTraffic": "50K+",
                    "articles": [{"url": "https://example.com/sports"}],
                    "relatedQueries": [],
                },
            ],
            "CA": [
                {
                    "__date": "20260317",
                    "title": {"query": "AI agent tools for clinics"},
                    "formattedTraffic": "150K+",
                    "articles": [{"url": "https://example.com/a1"}],
                    "relatedQueries": [{"query": "ai call assistant"}],
                },
                {
                    "__date": "20260317",
                    "title": {"query": "Automation workflow templates"},
                    "formattedTraffic": "80K+",
                    "articles": [],
                    "relatedQueries": [{"query": "automation"}],
                },
            ],
        }
    )
    connector = GoogleTrendsSourceConnector(api_client=api_client, max_trends_per_region=20)

    collected = connector.collect(
        SourceCollectRequest(
            keywords=["ai agent", "automation"],
            regions=["US", "CA"],
            language="en",
            limit=5,
        )
    )

    assert len(collected) == 2
    assert collected[0].source == "google_trends"
    assert collected[0].title == "AI agent tools for clinics"
    assert collected[0].url == "https://example.com/a1"
    assert collected[0].published_at == datetime(2026, 3, 17, tzinfo=UTC)
    assert collected[0].metadata["region"] == "US"
    assert collected[0].metadata["query_match"] == "ai agent"
    assert collected[0].engagement["search_traffic"] == 200000

    assert collected[1].title == "Automation workflow templates"
    assert collected[1].metadata["region"] == "CA"
    assert collected[1].metadata["query_match"] == "automation"
    assert collected[1].url is None

    assert len(api_client.calls) == 2
    assert api_client.calls[0]["limit"] == 5


def test_google_trends_connector_handles_region_failures() -> None:
    from app.infrastructure.sources.google_trends import GoogleTrendsSourceConnector

    api_client = FakeGoogleTrendsApiClient(
        responses_by_region={
            "US": [
                {
                    "__date": "20260317",
                    "title": {"query": "Automation for customer support"},
                    "formattedTraffic": "90K+",
                    "articles": [{"url": "https://example.com/us"}],
                    "relatedQueries": [{"query": "automation"}],
                }
            ]
        },
        failing_regions={"CA"},
    )
    connector = GoogleTrendsSourceConnector(api_client=api_client)

    collected = connector.collect(
        SourceCollectRequest(
            keywords=["automation"],
            regions=["CA", "US"],
            language="en",
            limit=10,
        )
    )

    assert len(collected) == 1
    assert collected[0].title == "Automation for customer support"
    assert [call["region"] for call in api_client.calls] == ["CA", "US"]


def test_google_trends_connector_returns_empty_when_no_keywords() -> None:
    from app.infrastructure.sources.google_trends import GoogleTrendsSourceConnector

    api_client = FakeGoogleTrendsApiClient(responses_by_region={"US": []})
    connector = GoogleTrendsSourceConnector(api_client=api_client)

    collected = connector.collect(
        SourceCollectRequest(
            keywords=[],
            regions=["US"],
            language="en",
            limit=10,
        )
    )

    assert collected == []
    assert api_client.calls == []
