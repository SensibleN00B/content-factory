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


@runtime_checkable
class HackerNewsApiTransport(Protocol):
    def get_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        params: dict[str, str],
    ) -> dict[str, Any]: ...


class UrllibJsonTransport:
    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self._timeout_seconds = timeout_seconds

    def get_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        params: dict[str, str],
    ) -> dict[str, Any]:
        query = urlencode(params)
        request = Request(url=f"{url}?{query}", method="GET")
        for name, value in headers.items():
            request.add_header(name, value)

        with urlopen(request, timeout=self._timeout_seconds) as response:
            payload = response.read().decode("utf-8")

        return json.loads(payload or "{}")


class HackerNewsApiClient:
    SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"

    def __init__(self, *, transport: HackerNewsApiTransport | None = None) -> None:
        self._transport = transport or UrllibJsonTransport()

    def search_posts(self, *, query: str, limit: int) -> list[dict[str, Any]]:
        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": str(limit),
        }
        payload = self._transport.get_json(url=self.SEARCH_URL, headers={}, params=params)
        hits = payload.get("hits")
        if not isinstance(hits, list):
            return []

        results: list[dict[str, Any]] = []
        for item in hits:
            if isinstance(item, dict):
                results.append(item)
        return results


@runtime_checkable
class HackerNewsSearchClient(Protocol):
    def search_posts(self, *, query: str, limit: int) -> list[dict[str, Any]]: ...


class HackerNewsSourceConnector(SourceConnector):
    source_key = "hackernews"

    def __init__(
        self,
        *,
        api_client: HackerNewsSearchClient,
        max_posts_per_keyword: int = 25,
    ) -> None:
        self._api_client = api_client
        self._max_posts_per_keyword = max_posts_per_keyword

    def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
        keywords = [keyword.strip() for keyword in request.keywords if keyword.strip()]
        if not keywords:
            return []

        per_query_limit = max(1, min(request.limit, self._max_posts_per_keyword))
        seen_keys: set[str] = set()
        collected: list[SourceCollectedSignal] = []

        for query in keywords:
            posts = self._api_client.search_posts(query=query, limit=per_query_limit)
            for post in posts:
                dedup_key = self._dedup_key(post, query)
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)
                collected.append(self._map_post(post=post, query=query))

        return collected

    def _map_post(self, *, post: dict[str, Any], query: str) -> SourceCollectedSignal:
        source_signal_id = self._as_str(post.get("objectID"))
        title = self._as_str(post.get("title")) or self._as_str(post.get("story_title"))
        url = self._as_str(post.get("url")) or self._as_str(post.get("story_url"))
        if url is None and source_signal_id is not None:
            url = f"https://news.ycombinator.com/item?id={source_signal_id}"

        return SourceCollectedSignal(
            source=self.source_key,
            source_signal_id=source_signal_id,
            title=title,
            url=url,
            published_at=self._parse_datetime(post.get("created_at")),
            raw_payload=post,
            metadata={
                "query": query,
                "author": self._as_str(post.get("author")),
                "tags": post.get("_tags"),
            },
            engagement={
                "points": self._as_int(post.get("points")),
                "comments": self._as_int(post.get("num_comments")),
            },
        )

    @staticmethod
    def _dedup_key(post: dict[str, Any], query: str) -> str:
        for key in ("objectID", "url", "story_url"):
            value = post.get(key)
            if isinstance(value, str) and value.strip():
                return f"{key}:{value.strip()}"

        title = post.get("title") or post.get("story_title")
        if isinstance(title, str) and title.strip():
            return f"title:{title.strip().lower()}"

        return f"fallback:{query}:{json.dumps(post, sort_keys=True, default=str)}"

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

    @staticmethod
    def _as_int(value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return 0
