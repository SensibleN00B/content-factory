from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.domain.ingestion.connectors import (
    SourceCollectedSignal,
    SourceCollectRequest,
    SourceConnector,
)


class GoogleTrendsApiError(RuntimeError):
    """Raised when Google Trends API response is invalid."""


@runtime_checkable
class GoogleTrendsApiTransport(Protocol):
    def get_text(self, *, url: str, headers: dict[str, str], params: dict[str, str]) -> str: ...


class UrllibTextTransport:
    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self._timeout_seconds = timeout_seconds

    def get_text(self, *, url: str, headers: dict[str, str], params: dict[str, str]) -> str:
        query = urlencode(params)
        request = Request(url=f"{url}?{query}", method="GET")
        for key, value in headers.items():
            request.add_header(key, value)

        with urlopen(request, timeout=self._timeout_seconds) as response:
            return response.read().decode("utf-8")


class GoogleTrendsApiClient:
    DAILY_TRENDS_URL = "https://trends.google.com/trends/api/dailytrends"

    def __init__(self, *, transport: GoogleTrendsApiTransport | None = None) -> None:
        self._transport = transport or UrllibTextTransport()

    def fetch_daily_trends(self, *, region: str, language: str, limit: int) -> list[dict[str, Any]]:
        normalized_region = region.strip().upper()
        normalized_language = language.strip().lower()

        hl = self._build_hl(language=normalized_language, region=normalized_region)
        params = {
            "hl": hl,
            "geo": normalized_region,
            "tz": "0",
            "ns": "15",
        }
        raw_text = self._transport.get_text(url=self.DAILY_TRENDS_URL, headers={}, params=params)
        payload = self._decode_payload(raw_text)

        default_data = payload.get("default")
        if not isinstance(default_data, dict):
            return []

        days = default_data.get("trendingSearchesDays")
        if not isinstance(days, list):
            return []

        trends: list[dict[str, Any]] = []
        for day in days:
            if not isinstance(day, dict):
                continue
            date_value = day.get("date")
            day_trends = day.get("trendingSearches")
            if not isinstance(day_trends, list):
                continue

            for trend in day_trends:
                if not isinstance(trend, dict):
                    continue
                trend_copy = dict(trend)
                if (
                    isinstance(date_value, str)
                    and date_value.strip()
                    and "__date" not in trend_copy
                ):
                    trend_copy["__date"] = date_value.strip()
                trends.append(trend_copy)

        return trends[: max(limit, 0)]

    @staticmethod
    def _build_hl(*, language: str, region: str) -> str:
        if len(language) == 2 and len(region) == 2:
            return f"{language}-{region}"
        return language or "en-US"

    @staticmethod
    def _decode_payload(raw_text: str) -> dict[str, Any]:
        normalized = raw_text.lstrip()
        if normalized.startswith(")]}'"):
            normalized = normalized.split("\n", maxsplit=1)[1] if "\n" in normalized else "{}"

        try:
            decoded = json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise GoogleTrendsApiError("Failed to parse Google Trends payload") from exc

        if not isinstance(decoded, dict):
            raise GoogleTrendsApiError("Google Trends payload has unexpected type")
        return decoded


@runtime_checkable
class GoogleTrendsSearchClient(Protocol):
    def fetch_daily_trends(
        self, *, region: str, language: str, limit: int
    ) -> list[dict[str, Any]]: ...


class GoogleTrendsSourceConnector(SourceConnector):
    source_key = "google_trends"

    def __init__(
        self,
        *,
        api_client: GoogleTrendsSearchClient,
        max_trends_per_region: int = 25,
    ) -> None:
        self._api_client = api_client
        self._max_trends_per_region = max_trends_per_region

    def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
        keywords = [keyword.strip().lower() for keyword in request.keywords if keyword.strip()]
        if not keywords:
            return []

        regions = [region.strip().upper() for region in request.regions if region.strip()] or ["US"]
        per_region_limit = max(1, min(request.limit, self._max_trends_per_region))

        seen_keys: set[str] = set()
        collected: list[SourceCollectedSignal] = []

        for region in regions:
            try:
                trends = self._api_client.fetch_daily_trends(
                    region=region,
                    language=request.language,
                    limit=per_region_limit,
                )
            except Exception:
                continue

            for trend in trends:
                match_keyword = self._find_keyword_match(trend=trend, keywords=keywords)
                if match_keyword is None:
                    continue

                dedup_key = self._dedup_key(trend)
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)

                collected.append(
                    self._map_trend(
                        trend=trend,
                        region=region,
                        match_keyword=match_keyword,
                    )
                )

        return collected

    def _map_trend(
        self,
        *,
        trend: dict[str, Any],
        region: str,
        match_keyword: str,
    ) -> SourceCollectedSignal:
        title = self._extract_title(trend)
        article_url = self._extract_article_url(trend)
        published_at = self._parse_date(trend.get("__date"))

        return SourceCollectedSignal(
            source=self.source_key,
            source_signal_id=self._build_signal_id(region=region, trend=trend),
            title=title,
            url=article_url,
            published_at=published_at,
            raw_payload=trend,
            metadata={
                "region": region,
                "query_match": match_keyword,
                "related_queries": self._extract_related_queries(trend),
            },
            engagement={
                "search_traffic": self._parse_search_traffic(trend.get("formattedTraffic")),
            },
        )

    @staticmethod
    def _extract_title(trend: dict[str, Any]) -> str | None:
        title_value = trend.get("title")
        if isinstance(title_value, dict):
            query = title_value.get("query")
            if isinstance(query, str) and query.strip():
                return query.strip()
        if isinstance(title_value, str) and title_value.strip():
            return title_value.strip()
        return None

    @staticmethod
    def _extract_related_queries(trend: dict[str, Any]) -> list[str]:
        related = trend.get("relatedQueries")
        if not isinstance(related, list):
            return []

        values: list[str] = []
        for item in related:
            if not isinstance(item, dict):
                continue
            query = item.get("query")
            if isinstance(query, str) and query.strip():
                values.append(query.strip())
        return values

    def _find_keyword_match(self, *, trend: dict[str, Any], keywords: list[str]) -> str | None:
        title = self._extract_title(trend)
        related_queries = self._extract_related_queries(trend)
        haystack = " ".join([title or "", *related_queries]).lower()

        for keyword in keywords:
            if keyword in haystack:
                return keyword
        return None

    @staticmethod
    def _extract_article_url(trend: dict[str, Any]) -> str | None:
        articles = trend.get("articles")
        if not isinstance(articles, list):
            return None

        for article in articles:
            if not isinstance(article, dict):
                continue
            url = article.get("url")
            if isinstance(url, str) and url.strip():
                return url.strip()
        return None

    @staticmethod
    def _parse_date(value: Any) -> datetime | None:
        if not isinstance(value, str):
            return None
        text = value.strip()
        if len(text) != 8 or not text.isdigit():
            return None

        try:
            return datetime.strptime(text, "%Y%m%d").replace(tzinfo=UTC)
        except ValueError:
            return None

    @staticmethod
    def _parse_search_traffic(value: Any) -> int:
        if isinstance(value, int):
            return value
        if not isinstance(value, str) or not value.strip():
            return 0

        text = value.strip().upper().replace(",", "")
        multiplier = 1
        if text.endswith("K+"):
            multiplier = 1_000
            text = text[:-2]
        elif text.endswith("M+"):
            multiplier = 1_000_000
            text = text[:-2]
        elif text.endswith("+"):
            text = text[:-1]

        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits:
            return 0
        return int(digits) * multiplier

    def _dedup_key(self, trend: dict[str, Any]) -> str:
        article_url = self._extract_article_url(trend)
        if article_url:
            return f"url:{article_url}"

        title = self._extract_title(trend)
        if title:
            return f"title:{title.lower()}"

        return f"fallback:{json.dumps(trend, sort_keys=True, default=str)}"

    def _build_signal_id(self, *, region: str, trend: dict[str, Any]) -> str:
        date = trend.get("__date") if isinstance(trend.get("__date"), str) else "na"
        title = (self._extract_title(trend) or "untitled").lower().replace(" ", "-")
        return f"{region}:{date}:{title}"
