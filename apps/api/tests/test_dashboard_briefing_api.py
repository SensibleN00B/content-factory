from __future__ import annotations

import json
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import (
    ContentCandidate,
    Profile,
    Run,
    RunSource,
    TopicCluster,
    TopicLabelLink,
)
from app.infrastructure.db.seeds import ensure_default_labels
from app.infrastructure.db.session import get_db_session
from app.main import create_app
from app.services.briefing_summarizer import LlmBriefingSummarizer, LlmRetryableError
from app.services.dashboard_briefing import (
    clear_briefing_cache_for_tests,
    refresh_briefing_cache_for_latest_run,
)


def make_client() -> tuple[TestClient, sessionmaker[Session]]:
    clear_briefing_cache_for_tests()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    app = create_app()

    def override_get_db_session() -> Generator[Session, None, None]:
        db_session = testing_session_factory()
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app), testing_session_factory


def seed_dashboard_data(db_session: Session) -> int:
    profile = Profile(
        niche=["ai"],
        icp=["founders"],
        regions=["US"],
        language="en",
        seeds=["ai workflow"],
        negatives=["crypto"],
        settings_json={},
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    run_one = Run(
        profile_id=profile.id,
        status="completed",
        input_snapshot_json={"niche": ["ai"], "language": "en"},
    )
    run_two = Run(
        profile_id=profile.id,
        status="completed",
        input_snapshot_json={"niche": ["ai"], "language": "en"},
    )
    latest_run = Run(
        profile_id=profile.id,
        status="completed",
        input_snapshot_json={"niche": ["ai"], "language": "en"},
    )
    db_session.add_all([run_one, run_two, latest_run])
    db_session.commit()
    db_session.refresh(run_one)
    db_session.refresh(run_two)
    db_session.refresh(latest_run)

    db_session.add_all(
        [
            RunSource(
                run_id=latest_run.id,
                source="google_trends",
                status="success",
                fetched_count=20,
                error_text=None,
                duration_ms=110,
            ),
            RunSource(
                run_id=latest_run.id,
                source="reddit",
                status="success",
                fetched_count=15,
                error_text=None,
                duration_ms=95,
            ),
            RunSource(
                run_id=latest_run.id,
                source="hackernews",
                status="failed",
                fetched_count=0,
                error_text="API timeout",
                duration_ms=1500,
            ),
            RunSource(
                run_id=latest_run.id,
                source="youtube",
                status="timeout",
                fetched_count=0,
                error_text="Request timed out",
                duration_ms=1500,
            ),
            RunSource(
                run_id=latest_run.id,
                source="producthunt",
                status="success",
                fetched_count=10,
                error_text=None,
                duration_ms=120,
            ),
        ]
    )
    db_session.commit()

    cluster_one_run1 = TopicCluster(
        run_id=run_one.id,
        canonical_topic="AI workflow for clinics",
        cluster_hash="c1-r1",
        source_count=2,
        signal_count=3,
        evidence_urls_json=["https://example.com/r1-c1"],
    )
    cluster_one_run2 = TopicCluster(
        run_id=run_two.id,
        canonical_topic="AI workflow for clinics",
        cluster_hash="c1-r2",
        source_count=3,
        signal_count=4,
        evidence_urls_json=["https://example.com/r2-c1"],
    )
    cluster_two_run2 = TopicCluster(
        run_id=run_two.id,
        canonical_topic="Voice AI for dentists",
        cluster_hash="c2-r2",
        source_count=2,
        signal_count=2,
        evidence_urls_json=["https://example.com/r2-c2"],
    )
    latest_cluster_one = TopicCluster(
        run_id=latest_run.id,
        canonical_topic="AI workflow for clinics",
        cluster_hash="c1-r3",
        source_count=4,
        signal_count=6,
        evidence_urls_json=["https://example.com/r3-c1"],
    )
    latest_cluster_two = TopicCluster(
        run_id=latest_run.id,
        canonical_topic="Voice AI for dentists",
        cluster_hash="c2-r3",
        source_count=2,
        signal_count=3,
        evidence_urls_json=["https://example.com/r3-c2"],
    )
    latest_cluster_three = TopicCluster(
        run_id=latest_run.id,
        canonical_topic="AI hiring copilots",
        cluster_hash="c3-r3",
        source_count=3,
        signal_count=4,
        evidence_urls_json=["https://example.com/r3-c3"],
    )
    db_session.add_all(
        [
            cluster_one_run1,
            cluster_one_run2,
            cluster_two_run2,
            latest_cluster_one,
            latest_cluster_two,
            latest_cluster_three,
        ]
    )
    db_session.commit()
    db_session.refresh(cluster_one_run1)
    db_session.refresh(cluster_one_run2)
    db_session.refresh(cluster_two_run2)
    db_session.refresh(latest_cluster_one)
    db_session.refresh(latest_cluster_two)
    db_session.refresh(latest_cluster_three)

    db_session.add_all(
        [
            ContentCandidate(
                run_id=run_one.id,
                topic_cluster_id=cluster_one_run1.id,
                trend_score=45.0,
                score_breakdown_json={"velocity": 45.0},
                why_now="Early signals in clinic automation",
                angles_json=["Angle A"],
                confidence=0.45,
            ),
            ContentCandidate(
                run_id=run_two.id,
                topic_cluster_id=cluster_one_run2.id,
                trend_score=60.0,
                score_breakdown_json={"velocity": 60.0},
                why_now="More sources discussing clinic workflows",
                angles_json=["Angle B"],
                confidence=0.6,
            ),
            ContentCandidate(
                run_id=run_two.id,
                topic_cluster_id=cluster_two_run2.id,
                trend_score=55.0,
                score_breakdown_json={"velocity": 55.0},
                why_now="Dentistry use-cases appearing in community threads",
                angles_json=["Angle C"],
                confidence=0.55,
            ),
            ContentCandidate(
                run_id=latest_run.id,
                topic_cluster_id=latest_cluster_one.id,
                trend_score=78.0,
                score_breakdown_json={"velocity": 78.0},
                why_now="Strong velocity and source expansion",
                angles_json=["Angle D"],
                confidence=0.78,
            ),
            ContentCandidate(
                run_id=latest_run.id,
                topic_cluster_id=latest_cluster_two.id,
                trend_score=54.0,
                score_breakdown_json={"velocity": 54.0},
                why_now="Steady but not accelerating",
                angles_json=["Angle E"],
                confidence=0.54,
            ),
            ContentCandidate(
                run_id=latest_run.id,
                topic_cluster_id=latest_cluster_three.id,
                trend_score=67.0,
                score_breakdown_json={"velocity": 67.0},
                why_now="New hiring automation narratives",
                angles_json=["Angle F"],
                confidence=0.67,
            ),
        ]
    )
    db_session.commit()

    labels = ensure_default_labels(db_session)
    watchlist = next(label for label in labels if label.name == "watchlist")
    db_session.add(
        TopicLabelLink(topic_cluster_id=latest_cluster_one.id, label_id=watchlist.id),
    )
    db_session.commit()

    return latest_run.id


def test_dashboard_briefing_endpoint_returns_aggregated_payload() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        latest_run_id = seed_dashboard_data(db_session)

    response = client.get("/api/dashboard/briefing")

    assert response.status_code == 200
    body = response.json()

    assert "briefing_items" in body
    assert isinstance(body["briefing_items"], list)
    assert body["briefing_available"] is False
    assert isinstance(body["briefing_unavailable_reason"], str)

    assert "recent_topics" in body
    assert isinstance(body["recent_topics"], list)
    assert len(body["recent_topics"]) >= 1
    assert "candidate_id" in body["recent_topics"][0]
    assert "canonical_topic" in body["recent_topics"][0]
    assert body["recent_topics"][0]["run_id"] == latest_run_id

    assert "latest_run" in body
    assert body["latest_run"]["id"] == latest_run_id
    assert body["latest_run"]["status"] == "completed"
    assert body["latest_run"]["candidate_count"] == 3

    assert "source_health" in body
    assert body["source_health"]["total_sources"] == 5
    assert body["source_health"]["healthy_sources"] == 3
    assert body["source_health"]["failed_sources"] == 2

    assert "pipeline_metrics" in body
    stage_keys = [stage["stage_key"] for stage in body["pipeline_metrics"]["stages"]]
    assert stage_keys == [
        "collected",
        "normalized",
        "deduplicated",
        "relevance_passed",
        "clustered",
        "shortlisted",
    ]
    assert isinstance(body["pipeline_metrics"]["drop_reasons"], dict)


def test_dashboard_briefing_marks_unavailable_when_no_completed_runs() -> None:
    client, _ = make_client()

    response = client.get("/api/dashboard/briefing")

    assert response.status_code == 200
    body = response.json()
    assert body["briefing_available"] is False
    assert body["briefing_items"] == []
    assert isinstance(body["briefing_unavailable_reason"], str)


def test_dashboard_briefing_classifies_topic_movement() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        seed_dashboard_data(db_session)

    response = client.get("/api/dashboard/briefing")
    assert response.status_code == 200

    body = response.json()
    movement_by_topic = {
        item["canonical_topic"]: item["movement"] for item in body["recent_topics"]
    }
    assert movement_by_topic["AI workflow for clinics"] == "rising"
    assert movement_by_topic["Voice AI for dentists"] == "stable"
    assert movement_by_topic["AI hiring copilots"] == "new"


def test_dashboard_briefing_uses_llm_summarizer_when_configured(monkeypatch) -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        seed_dashboard_data(db_session)

    def fake_request_response(
        self: LlmBriefingSummarizer,
        *,
        prompt: str,
    ) -> dict[str, object]:
        assert "Generate 4-5 concise briefing bullets" in prompt
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "briefing_items": [
                                        {
                                            "kind": "rising",
                                            "title": "LLM momentum signal",
                                            "detail": (
                                                "Clinic workflow automation keeps accelerating."
                                            ),
                                        },
                                        {
                                            "kind": "stable",
                                            "title": "LLM stable signal",
                                            "detail": "Voice AI remains steady across sources.",
                                        },
                                        {
                                            "kind": "cooling",
                                            "title": "LLM cooling signal",
                                            "detail": "A subset of themes softened this run.",
                                        },
                                        {
                                            "kind": "new",
                                            "title": "LLM new signal",
                                            "detail": "Hiring copilots appeared as a new theme.",
                                        },
                                        {
                                            "kind": "review_first",
                                            "title": "LLM review-first signal",
                                            "detail": "Review clinic workflow automation first.",
                                        },
                                    ]
                                }
                            ),
                        }
                    ],
                }
            ]
        }

    monkeypatch.setattr(
        LlmBriefingSummarizer,
        "_request_response",
        fake_request_response,
    )

    previous_mode = settings.briefing_summarizer_mode
    previous_api_key = settings.openai_api_key
    try:
        settings.briefing_summarizer_mode = "llm"
        settings.openai_api_key = "sk-test"
        with session_factory() as db_session:
            refresh_briefing_cache_for_latest_run(db_session=db_session)
        response = client.get("/api/dashboard/briefing")
    finally:
        settings.briefing_summarizer_mode = previous_mode
        settings.openai_api_key = previous_api_key

    assert response.status_code == 200
    body = response.json()
    assert body["briefing_available"] is True
    assert body["briefing_unavailable_reason"] is None
    assert len(body["briefing_items"]) == 5
    assert body["briefing_items"][0]["title"] == "LLM momentum signal"
    assert body["briefing_items"][4]["kind"] == "review_first"


def test_dashboard_briefing_retries_llm_before_success(monkeypatch) -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        seed_dashboard_data(db_session)

    attempts = {"count": 0}

    def flaky_request_response(
        self: LlmBriefingSummarizer,
        *,
        prompt: str,
    ) -> dict[str, object]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise LlmRetryableError("first attempt timed out")
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "briefing_items": [
                                        {
                                            "kind": "rising",
                                            "title": "Retry recovered signal",
                                            "detail": "Second attempt succeeded.",
                                        },
                                        {
                                            "kind": "stable",
                                            "title": "Stable",
                                            "detail": "Stable detail.",
                                        },
                                        {
                                            "kind": "new",
                                            "title": "New",
                                            "detail": "New detail.",
                                        },
                                        {
                                            "kind": "review_first",
                                            "title": "Review",
                                            "detail": "Review detail.",
                                        },
                                    ]
                                }
                            ),
                        }
                    ],
                }
            ]
        }

    monkeypatch.setattr(
        LlmBriefingSummarizer,
        "_request_response",
        flaky_request_response,
    )

    previous_mode = settings.briefing_summarizer_mode
    previous_api_key = settings.openai_api_key
    try:
        settings.briefing_summarizer_mode = "llm"
        settings.openai_api_key = "sk-test"
        with session_factory() as db_session:
            refresh_briefing_cache_for_latest_run(db_session=db_session)
        response = client.get("/api/dashboard/briefing")
    finally:
        settings.briefing_summarizer_mode = previous_mode
        settings.openai_api_key = previous_api_key

    assert response.status_code == 200
    body = response.json()
    assert body["briefing_available"] is True
    assert body["briefing_items"][0]["title"] == "Retry recovered signal"
    assert attempts["count"] == 2


def test_dashboard_briefing_marks_unavailable_when_llm_mode_is_requested_without_key() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        seed_dashboard_data(db_session)

    previous_mode = settings.briefing_summarizer_mode
    previous_api_key = settings.openai_api_key
    try:
        settings.briefing_summarizer_mode = "llm"
        settings.openai_api_key = ""
        response = client.get("/api/dashboard/briefing")
    finally:
        settings.briefing_summarizer_mode = previous_mode
        settings.openai_api_key = previous_api_key

    assert response.status_code == 200
    body = response.json()
    assert body["briefing_available"] is False
    assert body["briefing_items"] == []
    assert isinstance(body["briefing_unavailable_reason"], str)


def test_dashboard_briefing_read_path_uses_cached_items_without_new_llm_call(monkeypatch) -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        seed_dashboard_data(db_session)

    def fake_request_response(
        self: LlmBriefingSummarizer,
        *,
        prompt: str,
    ) -> dict[str, object]:
        assert "Generate 4-5 concise briefing bullets" in prompt
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "briefing_items": [
                                        {
                                            "kind": "rising",
                                            "title": "Cached LLM briefing",
                                            "detail": "Should be served from cache on read.",
                                        },
                                        {
                                            "kind": "stable",
                                            "title": "Stable",
                                            "detail": "Stable detail.",
                                        },
                                        {
                                            "kind": "new",
                                            "title": "New",
                                            "detail": "New detail.",
                                        },
                                        {
                                            "kind": "review_first",
                                            "title": "Review",
                                            "detail": "Review detail.",
                                        },
                                    ]
                                }
                            ),
                        }
                    ],
                }
            ]
        }

    monkeypatch.setattr(
        LlmBriefingSummarizer,
        "_request_response",
        fake_request_response,
    )

    previous_mode = settings.briefing_summarizer_mode
    previous_api_key = settings.openai_api_key
    try:
        settings.briefing_summarizer_mode = "llm"
        settings.openai_api_key = "sk-test"
        with session_factory() as db_session:
            refresh_briefing_cache_for_latest_run(db_session=db_session)
    finally:
        settings.briefing_summarizer_mode = previous_mode
        settings.openai_api_key = previous_api_key

    def unexpected_request(
        self: LlmBriefingSummarizer,
        *,
        prompt: str,
    ) -> dict[str, object]:
        raise AssertionError("LLM should not be called during dashboard read path.")

    monkeypatch.setattr(
        LlmBriefingSummarizer,
        "_request_response",
        unexpected_request,
    )

    previous_mode = settings.briefing_summarizer_mode
    previous_api_key = settings.openai_api_key
    try:
        settings.briefing_summarizer_mode = "llm"
        settings.openai_api_key = "sk-test"
        response = client.get("/api/dashboard/briefing")
    finally:
        settings.briefing_summarizer_mode = previous_mode
        settings.openai_api_key = previous_api_key

    assert response.status_code == 200
    body = response.json()
    assert body["briefing_available"] is True
    assert body["briefing_items"][0]["title"] == "Cached LLM briefing"
