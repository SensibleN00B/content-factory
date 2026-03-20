from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_ALLOWED_BRIEFING_KINDS = {"rising", "stable", "cooling", "new", "review_first"}
_BRIEFING_SCHEMA = {
    "type": "object",
    "properties": {
        "briefing_items": {
            "type": "array",
            "minItems": 4,
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": sorted(_ALLOWED_BRIEFING_KINDS),
                    },
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                },
                "required": ["kind", "title", "detail"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["briefing_items"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class BriefingTopic:
    canonical_topic: str
    movement: str
    trend_score: float
    source_count: int
    signal_count: int


@dataclass(frozen=True)
class BriefingContext:
    topics: list[BriefingTopic]
    latest_run_id: int
    latest_candidate_count: int
    total_sources: int
    healthy_sources: int
    failed_sources: int


@dataclass(frozen=True)
class BriefingItem:
    kind: str
    title: str
    detail: str


class BriefingSummarizer(Protocol):
    def summarize(self, *, context: BriefingContext) -> list[BriefingItem]: ...


class LlmSummarizerError(RuntimeError):
    pass


class LlmRetryableError(LlmSummarizerError):
    pass


class RuleBasedBriefingSummarizer:
    def summarize(self, *, context: BriefingContext) -> list[BriefingItem]:
        topics = context.topics
        rising_topics = [topic for topic in topics if topic.movement == "rising"]
        stable_topics = [topic for topic in topics if topic.movement == "stable"]
        cooling_topics = [topic for topic in topics if topic.movement == "cooling"]
        new_topics = [topic for topic in topics if topic.movement == "new"]
        top_topic = max(topics, key=lambda topic: topic.trend_score, default=None)

        items: list[BriefingItem] = []
        if rising_topics:
            leader = max(rising_topics, key=lambda topic: topic.trend_score)
            items.append(
                BriefingItem(
                    kind="rising",
                    title=f"{len(rising_topics)} topic(s) are gaining momentum",
                    detail=(
                        f"{leader.canonical_topic} is leading with score "
                        f"{round(leader.trend_score, 2)}."
                    ),
                )
            )
        else:
            items.append(
                BriefingItem(
                    kind="stable",
                    title="Momentum is currently steady",
                    detail="No topic shows a sharp acceleration in the latest run.",
                )
            )

        if cooling_topics:
            leader = max(cooling_topics, key=lambda topic: topic.trend_score)
            items.append(
                BriefingItem(
                    kind="cooling",
                    title=f"{len(cooling_topics)} topic(s) are cooling",
                    detail=f"{leader.canonical_topic} softened versus prior runs.",
                )
            )
        else:
            items.append(
                BriefingItem(
                    kind="stable",
                    title=f"{len(stable_topics)} topic(s) are stable",
                    detail="Stable topics are consistent but do not yet accelerate.",
                )
            )

        if new_topics:
            sample = ", ".join(topic.canonical_topic for topic in new_topics[:2])
            items.append(
                BriefingItem(
                    kind="new",
                    title=f"{len(new_topics)} new topic(s) appeared",
                    detail=f"New entrants: {sample}.",
                )
            )
        else:
            items.append(
                BriefingItem(
                    kind="new",
                    title="No new topics in the latest run",
                    detail="The latest shortlist is formed from known recurring themes.",
                )
            )

        items.append(
            BriefingItem(
                kind="stable",
                title="Source collection health snapshot",
                detail=(
                    f"{context.healthy_sources}/{context.total_sources} sources healthy; "
                    f"{context.failed_sources} failed."
                ),
            )
        )

        if top_topic is not None:
            items.append(
                BriefingItem(
                    kind="review_first",
                    title="Review-first candidate",
                    detail=(
                        f"{top_topic.canonical_topic} is the top priority at "
                        f"{round(top_topic.trend_score, 2)}."
                    ),
                )
            )

        return items[:5]


class LlmBriefingSummarizer:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
        retry_backoff_seconds: float,
    ) -> None:
        self._api_key = api_key.strip()
        self._model = model.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max(0, int(max_retries))
        self._retry_backoff_seconds = max(float(retry_backoff_seconds), 0.1)

    def summarize(self, *, context: BriefingContext) -> list[BriefingItem]:
        if not self._api_key:
            raise RuntimeError("LLM summarizer is enabled but OPENAI_API_KEY is missing.")
        if not self._model:
            raise RuntimeError("LLM summarizer is enabled but no model is configured.")

        prompt = _build_prompt(context=context)
        max_attempts = self._max_retries + 1
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                response_payload = self._request_response(prompt=prompt)
                response_text = _extract_output_text(response_payload=response_payload)
                if not response_text:
                    raise LlmRetryableError("LLM response did not contain output text.")

                items = _parse_briefing_items(response_text=response_text)
                return items[:5]
            except LlmRetryableError as error:
                last_error = error
                if attempt >= max_attempts:
                    break
                backoff_seconds = self._retry_backoff_seconds * (2 ** (attempt - 1))
                time.sleep(backoff_seconds)
            except LlmSummarizerError as error:
                raise RuntimeError(str(error)) from error

        message = "LLM briefing request failed after retries."
        if last_error is not None:
            message = f"{message} {last_error}"
        raise RuntimeError(message)

    def _request_response(self, *, prompt: str) -> dict[str, Any]:
        payload = {
            "model": self._model,
            "instructions": (
                "You are generating concise dashboard briefing bullets. "
                "Return only valid JSON that matches the provided schema."
            ),
            "input": prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "dashboard_briefing_items",
                    "schema": _BRIEFING_SCHEMA,
                }
            },
        }

        request = Request(
            url=f"{self._base_url}/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            status_code = int(exc.code)
            if status_code == 429 or 500 <= status_code < 600:
                raise LlmRetryableError(
                    f"OpenAI responses request failed with status {status_code}: {error_body}"
                ) from exc
            raise LlmSummarizerError(
                f"OpenAI responses request failed with status {status_code}: {error_body}"
            ) from exc
        except URLError as exc:
            raise LlmRetryableError(f"OpenAI responses request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LlmRetryableError("OpenAI responses request timed out.") from exc

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise LlmRetryableError("OpenAI responses request returned invalid JSON.") from exc


def resolve_briefing_summarizer(
    *,
    mode: str,
    api_key: str,
    model: str,
    base_url: str = "https://api.openai.com/v1",
    timeout_seconds: float = 45.0,
    max_retries: int = 2,
    retry_backoff_seconds: float = 1.0,
) -> BriefingSummarizer:
    if mode.strip().lower() == "llm":
        return LlmBriefingSummarizer(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )
    return RuleBasedBriefingSummarizer()


def _build_prompt(*, context: BriefingContext) -> str:
    payload = {
        "latest_run_id": context.latest_run_id,
        "latest_candidate_count": context.latest_candidate_count,
        "source_health": {
            "total_sources": context.total_sources,
            "healthy_sources": context.healthy_sources,
            "failed_sources": context.failed_sources,
        },
        "topics": [
            {
                "canonical_topic": topic.canonical_topic,
                "movement": topic.movement,
                "trend_score": round(topic.trend_score, 2),
                "source_count": topic.source_count,
                "signal_count": topic.signal_count,
            }
            for topic in context.topics
        ],
    }
    return (
        "Generate 4-5 concise briefing bullets for a trend dashboard.\n"
        "Use kind values from: rising, stable, cooling, new, review_first.\n"
        "Use factual language only from context and keep detail actionable.\n"
        f"Context:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def _extract_output_text(*, response_payload: dict[str, Any]) -> str:
    direct_output = response_payload.get("output_text")
    if isinstance(direct_output, str) and direct_output.strip():
        return direct_output.strip()

    chunks: list[str] = []
    output_items = response_payload.get("output")
    if not isinstance(output_items, list):
        return ""

    for item in output_items:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        content_items = item.get("content")
        if not isinstance(content_items, list):
            continue
        for content in content_items:
            if not isinstance(content, dict):
                continue
            if content.get("type") != "output_text":
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
    return "\n".join(chunks).strip()


def _parse_briefing_items(*, response_text: str) -> list[BriefingItem]:
    text = _strip_markdown_fence(response_text)
    payload = json.loads(text)
    items_raw = payload.get("briefing_items") if isinstance(payload, dict) else None
    if not isinstance(items_raw, list):
        raise RuntimeError("LLM response JSON does not contain briefing_items list.")
    if not 4 <= len(items_raw) <= 5:
        raise RuntimeError("LLM response must contain 4-5 briefing items.")

    items: list[BriefingItem] = []
    for item in items_raw:
        if not isinstance(item, dict):
            raise RuntimeError("LLM briefing item must be an object.")
        kind = str(item.get("kind", "")).strip().lower()
        title = str(item.get("title", "")).strip()
        detail = str(item.get("detail", "")).strip()
        if kind not in _ALLOWED_BRIEFING_KINDS:
            raise RuntimeError(f"Unsupported briefing kind from LLM: {kind}")
        if not title or not detail:
            raise RuntimeError("LLM briefing item must contain title and detail.")
        items.append(BriefingItem(kind=kind, title=title, detail=detail))

    return items


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped
