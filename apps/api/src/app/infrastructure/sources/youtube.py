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


class YouTubeApiError(RuntimeError):
    """Raised when YouTube API returns invalid payload."""


class YouTubeQuotaExceededError(YouTubeApiError):
    """Raised when YouTube API quota is exceeded."""


class YouTubeCredentials:
    def __init__(self, *, api_key: str) -> None:
        self.api_key = api_key


@runtime_checkable
class YouTubeApiTransport(Protocol):
    def get_json(
        self, *, url: str, headers: dict[str, str], params: dict[str, str]
    ) -> dict[str, Any]: ...


class UrllibJsonTransport:
    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self._timeout_seconds = timeout_seconds

    def get_json(
        self, *, url: str, headers: dict[str, str], params: dict[str, str]
    ) -> dict[str, Any]:
        query = urlencode(params)
        request = Request(url=f"{url}?{query}", method="GET")
        for key, value in headers.items():
            request.add_header(key, value)

        with urlopen(request, timeout=self._timeout_seconds) as response:
            payload = response.read().decode("utf-8")

        decoded = json.loads(payload or "{}")
        if not isinstance(decoded, dict):
            raise YouTubeApiError("YouTube API payload has unexpected type")
        return decoded


class YouTubeApiClient:
    SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

    def __init__(
        self,
        *,
        credentials: YouTubeCredentials,
        transport: YouTubeApiTransport | None = None,
    ) -> None:
        self._credentials = credentials
        self._transport = transport or UrllibJsonTransport()

    def search_videos(
        self, *, query: str, limit: int, region: str, language: str
    ) -> list[dict[str, Any]]:
        params = {
            "key": self._credentials.api_key,
            "part": "snippet",
            "type": "video",
            "order": "date",
            "q": query,
            "maxResults": str(limit),
            "regionCode": region,
            "relevanceLanguage": language,
        }
        payload = self._transport.get_json(url=self.SEARCH_URL, headers={}, params=params)

        error = payload.get("error")
        if isinstance(error, dict):
            reasons = []
            errors = error.get("errors")
            if isinstance(errors, list):
                for item in errors:
                    if isinstance(item, dict):
                        reason = item.get("reason")
                        if isinstance(reason, str):
                            reasons.append(reason)
            if "quotaExceeded" in reasons:
                raise YouTubeQuotaExceededError("YouTube quota exceeded")
            raise YouTubeApiError("YouTube API returned an error")

        items = payload.get("items")
        if not isinstance(items, list):
            return []

        collected: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict):
                collected.append(item)
        return collected


@runtime_checkable
class YouTubeSearchClient(Protocol):
    def search_videos(
        self, *, query: str, limit: int, region: str, language: str
    ) -> list[dict[str, Any]]: ...


class YouTubeSourceConnector(SourceConnector):
    source_key = "youtube"

    def __init__(
        self, *, api_client: YouTubeSearchClient, max_videos_per_keyword: int = 25
    ) -> None:
        self._api_client = api_client
        self._max_videos_per_keyword = max_videos_per_keyword

    def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
        keywords = [keyword.strip() for keyword in request.keywords if keyword.strip()]
        if not keywords:
            return []

        region = self._normalize_region(request.regions)
        language = self._normalize_language(request.language)
        per_query_limit = max(1, min(request.limit, self._max_videos_per_keyword))

        seen_ids: set[str] = set()
        collected: list[SourceCollectedSignal] = []

        for query in keywords:
            try:
                items = self._api_client.search_videos(
                    query=query,
                    limit=per_query_limit,
                    region=region,
                    language=language,
                )
            except YouTubeQuotaExceededError:
                break
            except Exception:
                continue

            for item in items:
                mapped = self._map_item(item=item, query=query)
                if mapped is None or mapped.source_signal_id is None:
                    continue
                if mapped.source_signal_id in seen_ids:
                    continue
                seen_ids.add(mapped.source_signal_id)
                collected.append(mapped)

        return collected

    def _map_item(self, *, item: dict[str, Any], query: str) -> SourceCollectedSignal | None:
        video_id = self._extract_video_id(item)
        if video_id is None:
            return None

        snippet = item.get("snippet")
        if not isinstance(snippet, dict):
            snippet = {}

        title = self._as_str(snippet.get("title"))
        description = self._as_str(snippet.get("description"))
        published_at = self._parse_datetime(snippet.get("publishedAt"))

        return SourceCollectedSignal(
            source=self.source_key,
            source_signal_id=video_id,
            title=title,
            url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=published_at,
            raw_payload=item,
            metadata={
                "query": query,
                "channel_title": self._as_str(snippet.get("channelTitle")),
                "description": description,
            },
            engagement={"views": 0, "likes": 0, "comments": 0},
        )

    @staticmethod
    def _extract_video_id(item: dict[str, Any]) -> str | None:
        identifier = item.get("id")
        if isinstance(identifier, dict):
            video_id = identifier.get("videoId")
            if isinstance(video_id, str) and video_id.strip():
                return video_id.strip()
        if isinstance(identifier, str) and identifier.strip():
            return identifier.strip()
        return None

    @staticmethod
    def _normalize_region(regions: list[str]) -> str:
        for region in regions:
            candidate = region.strip().upper()
            if len(candidate) == 2:
                return candidate
        return "US"

    @staticmethod
    def _normalize_language(language: str) -> str:
        candidate = language.strip().lower()
        if len(candidate) >= 2:
            return candidate[:2]
        return "en"

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        normalized = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized).astimezone(UTC)
        except ValueError:
            return None

    @staticmethod
    def _as_str(value: Any) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return None
