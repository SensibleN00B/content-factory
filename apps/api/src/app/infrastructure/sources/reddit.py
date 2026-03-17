from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.domain.ingestion.connectors import (
    SourceCollectedSignal,
    SourceCollectRequest,
    SourceConnector,
)


@dataclass(frozen=True)
class RedditCredentials:
    client_id: str
    client_secret: str
    user_agent: str = "content-factory/0.1"


class RedditApiError(RuntimeError):
    """Raised when Reddit API returns invalid or unexpected payload."""


@runtime_checkable
class RedditApiTransport(Protocol):
    def post_form(
        self,
        *,
        url: str,
        headers: dict[str, str],
        data: dict[str, str],
    ) -> dict[str, Any]: ...

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

    def post_form(
        self,
        *,
        url: str,
        headers: dict[str, str],
        data: dict[str, str],
    ) -> dict[str, Any]:
        body = urlencode(data).encode("utf-8")
        request = Request(url=url, data=body, method="POST")
        for name, value in headers.items():
            request.add_header(name, value)
        request.add_header("Content-Type", "application/x-www-form-urlencoded")

        with urlopen(request, timeout=self._timeout_seconds) as response:
            payload = response.read().decode("utf-8")

        return json.loads(payload or "{}")

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


class RedditApiClient:
    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    SEARCH_URL = "https://oauth.reddit.com/search"

    def __init__(
        self,
        *,
        credentials: RedditCredentials,
        transport: RedditApiTransport | None = None,
    ) -> None:
        self._credentials = credentials
        self._transport = transport or UrllibJsonTransport()

    def fetch_access_token(self) -> str:
        raw_credentials = (
            f"{self._credentials.client_id}:{self._credentials.client_secret}".encode()
        )
        encoded_credentials = base64.b64encode(raw_credentials).decode("utf-8")

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "User-Agent": self._credentials.user_agent,
        }
        payload = self._transport.post_form(
            url=self.TOKEN_URL,
            headers=headers,
            data={"grant_type": "client_credentials"},
        )

        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise RedditApiError("Missing access token in Reddit auth response")
        return access_token

    def search_posts(self, *, token: str, query: str, limit: int) -> list[dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": self._credentials.user_agent,
        }
        params = {
            "q": query,
            "limit": str(limit),
            "sort": "new",
            "type": "link",
            "restrict_sr": "false",
        }
        payload = self._transport.get_json(url=self.SEARCH_URL, headers=headers, params=params)
        data = payload.get("data")
        if not isinstance(data, dict):
            return []

        children = data.get("children")
        if not isinstance(children, list):
            return []

        posts: list[dict[str, Any]] = []
        for child in children:
            if not isinstance(child, dict):
                continue
            post_data = child.get("data")
            if isinstance(post_data, dict):
                posts.append(post_data)
        return posts


@runtime_checkable
class RedditSearchClient(Protocol):
    def fetch_access_token(self) -> str: ...

    def search_posts(self, *, token: str, query: str, limit: int) -> list[dict[str, Any]]: ...


class RedditSourceConnector(SourceConnector):
    source_key = "reddit"

    def __init__(self, *, api_client: RedditSearchClient, max_posts_per_keyword: int = 25) -> None:
        self._api_client = api_client
        self._max_posts_per_keyword = max_posts_per_keyword

    def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
        keywords = [keyword.strip() for keyword in request.keywords if keyword.strip()]
        if not keywords:
            return []

        token = self._api_client.fetch_access_token()
        per_query_limit = max(1, min(request.limit, self._max_posts_per_keyword))

        collected: list[SourceCollectedSignal] = []
        seen_keys: set[str] = set()

        for query in keywords:
            posts = self._api_client.search_posts(token=token, query=query, limit=per_query_limit)
            for post in posts:
                dedup_key = self._dedup_key(post, query)
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)
                collected.append(self._map_post(post=post, query=query))

        return collected

    def _map_post(self, *, post: dict[str, Any], query: str) -> SourceCollectedSignal:
        permalink = self._as_str(post.get("permalink"))
        post_url = self._build_post_url(permalink) or self._as_str(post.get("url"))

        return SourceCollectedSignal(
            source=self.source_key,
            source_signal_id=self._as_str(post.get("id")),
            title=self._as_str(post.get("title")),
            url=post_url,
            published_at=self._parse_timestamp(post.get("created_utc")),
            raw_payload=post,
            metadata={
                "query": query,
                "subreddit": self._as_str(post.get("subreddit")),
                "author": self._as_str(post.get("author")),
                "permalink": permalink,
                "over_18": bool(post.get("over_18", False)),
            },
            engagement={
                "upvotes": self._as_int(post.get("score")),
                "comments": self._as_int(post.get("num_comments")),
            },
        )

    @staticmethod
    def _dedup_key(post: dict[str, Any], query: str) -> str:
        for key in ("id", "name", "permalink", "url"):
            value = post.get(key)
            if isinstance(value, str) and value.strip():
                return f"{key}:{value.strip()}"

        title = post.get("title")
        if isinstance(title, str) and title.strip():
            return f"title:{title.strip().lower()}"

        return f"fallback:{query}:{json.dumps(post, sort_keys=True, default=str)}"

    @staticmethod
    def _build_post_url(permalink: str | None) -> str | None:
        if permalink is None:
            return None
        if permalink.startswith("http://") or permalink.startswith("https://"):
            return permalink
        if permalink.startswith("/"):
            return f"https://reddit.com{permalink}"
        return f"https://reddit.com/{permalink}"

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=UTC)
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
