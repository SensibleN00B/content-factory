from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from urllib.request import Request, urlopen

from app.domain.ingestion.connectors import (
    SourceCollectedSignal,
    SourceCollectRequest,
    SourceConnector,
)


@dataclass(frozen=True)
class ProductHuntCredentials:
    client_id: str
    client_secret: str


class ProductHuntApiError(RuntimeError):
    """Raised when Product Hunt API returns invalid payload."""


@runtime_checkable
class ProductHuntApiTransport(Protocol):
    def post_json(
        self, *, url: str, headers: dict[str, str], body: dict[str, Any]
    ) -> dict[str, Any]: ...


class UrllibJsonTransport:
    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self._timeout_seconds = timeout_seconds

    def post_json(
        self, *, url: str, headers: dict[str, str], body: dict[str, Any]
    ) -> dict[str, Any]:
        request_body = json.dumps(body).encode("utf-8")
        request = Request(url=url, data=request_body, method="POST")
        for key, value in headers.items():
            request.add_header(key, value)
        if "Content-Type" not in request.headers:
            request.add_header("Content-Type", "application/json")

        with urlopen(request, timeout=self._timeout_seconds) as response:
            payload = response.read().decode("utf-8")

        decoded = json.loads(payload or "{}")
        if not isinstance(decoded, dict):
            raise ProductHuntApiError("Product Hunt response has unexpected format")
        return decoded


class ProductHuntApiClient:
    TOKEN_URL = "https://api.producthunt.com/v2/oauth/token"
    GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

    def __init__(
        self,
        *,
        credentials: ProductHuntCredentials,
        transport: ProductHuntApiTransport | None = None,
    ) -> None:
        self._credentials = credentials
        self._transport = transport or UrllibJsonTransport()

    def fetch_access_token(self) -> str:
        response = self._transport.post_json(
            url=self.TOKEN_URL,
            headers={"Content-Type": "application/json"},
            body={
                "client_id": self._credentials.client_id,
                "client_secret": self._credentials.client_secret,
                "grant_type": "client_credentials",
            },
        )

        access_token = response.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ProductHuntApiError("Missing Product Hunt access token")
        return access_token

    def fetch_posts(self, *, token: str, limit: int) -> list[dict[str, Any]]:
        query = """
        query GetPosts($first: Int!) {
          posts(first: $first) {
            edges {
              node {
                id
                name
                tagline
                description
                url
                website
                createdAt
                votesCount
                commentsCount
                topics {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """
        response = self._transport.post_json(
            url=self.GRAPHQL_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            body={
                "query": query,
                "variables": {"first": limit},
            },
        )

        data = response.get("data")
        if not isinstance(data, dict):
            return []
        posts = data.get("posts")
        if not isinstance(posts, dict):
            return []
        edges = posts.get("edges")
        if not isinstance(edges, list):
            return []

        collected: list[dict[str, Any]] = []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            node = edge.get("node")
            if isinstance(node, dict):
                collected.append(node)

        return collected


@runtime_checkable
class ProductHuntSearchClient(Protocol):
    def fetch_access_token(self) -> str: ...

    def fetch_posts(self, *, token: str, limit: int) -> list[dict[str, Any]]: ...


class ProductHuntSourceConnector(SourceConnector):
    source_key = "producthunt"

    def __init__(self, *, api_client: ProductHuntSearchClient, max_posts: int = 25) -> None:
        self._api_client = api_client
        self._max_posts = max_posts

    def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
        keywords = [keyword.strip().lower() for keyword in request.keywords if keyword.strip()]
        if not keywords:
            return []

        token = self._api_client.fetch_access_token()
        fetch_limit = max(1, min(request.limit, self._max_posts))
        posts = self._api_client.fetch_posts(token=token, limit=fetch_limit)

        seen_keys: set[str] = set()
        collected: list[SourceCollectedSignal] = []

        for post in posts:
            query_match = self._find_query_match(post=post, keywords=keywords)
            if query_match is None:
                continue

            dedup_key = self._dedup_key(post)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            collected.append(self._map_post(post=post, query_match=query_match))

        return collected

    def _map_post(self, *, post: dict[str, Any], query_match: str) -> SourceCollectedSignal:
        topics = self._extract_topics(post)

        return SourceCollectedSignal(
            source=self.source_key,
            source_signal_id=self._as_str(post.get("id")),
            title=self._as_str(post.get("name")),
            url=self._as_str(post.get("url")) or self._as_str(post.get("website")),
            published_at=self._parse_datetime(post.get("createdAt")),
            raw_payload=post,
            metadata={
                "query_match": query_match,
                "topics": topics,
                "tagline": self._as_str(post.get("tagline")),
            },
            engagement={
                "votes": self._as_int(post.get("votesCount")),
                "comments": self._as_int(post.get("commentsCount")),
            },
        )

    def _find_query_match(self, *, post: dict[str, Any], keywords: list[str]) -> str | None:
        parts: list[str] = []
        for key in ("name", "tagline", "description"):
            value = post.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        parts.extend(self._extract_topics(post))

        haystack = " ".join(parts).lower()
        for keyword in keywords:
            if keyword in haystack:
                return keyword
        return None

    @staticmethod
    def _extract_topics(post: dict[str, Any]) -> list[str]:
        topics = post.get("topics")
        if not isinstance(topics, dict):
            return []

        edges = topics.get("edges")
        if not isinstance(edges, list):
            return []

        values: list[str] = []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            node = edge.get("node")
            if not isinstance(node, dict):
                continue
            name = node.get("name")
            if isinstance(name, str) and name.strip():
                values.append(name.strip())
        return values

    def _dedup_key(self, post: dict[str, Any]) -> str:
        for key in ("id", "url", "name"):
            value = post.get(key)
            if isinstance(value, str) and value.strip():
                return f"{key}:{value.strip().lower()}"
        return f"fallback:{json.dumps(post, sort_keys=True, default=str)}"

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
