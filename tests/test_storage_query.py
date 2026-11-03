import sqlite3
from datetime import datetime

from mi_fitness_mcp.models import (
    BodyMeasurement,
    DailyActivity,
    HeartRateSample,
    SleepSession,
    SleepStage,
)
from mi_fitness_mcp.services.query_service import QueryService
from mi_fitness_mcp.storage import Database


def _hrv_sleep() -> SleepSession:
    return SleepSession(
        id="s1",
        provider="mi_fitness",
        source_type="cloud_session",
        user_id="u1",
        sleep_id="s1",
        start_at=datetime(2026, 10, 28, 0, 35),
        end_at=datetime(2026, 10, 28, 8, 44),
        duration_minutes=489,
        time_asleep_minutes=460,
        time_awake_minutes=29,
        sleep_score=85,
        stages=[SleepStage(stage="deep", minutes=100)],
        avg_hrv_ms=76,
        min_hrv_ms=39,
        max_hrv_ms=107,
        hrv_median_ms=75,
        hrv_std_ms=0,
        hrv_lower_quantile_ms=52,
        hrv_upper_quantile_ms=102,
        hrv_base_min_ms=34,
        hrv_base_max_ms=76,
        hrv_analysis_at=datetime(2026, 10, 28, 8, 0),
    )


def test_storage_and_query_roundtrip(tmp_path):
    db = Database(tmp_path / "test.db")

    activity = DailyActivity(
        id="a1",
        provider="mi_fitness",
        source_type="cloud_session",
        user_id="u1",
        date="2025-04-01",
        steps=1000,
        distance_m=800,
        active_kcal=50,
    )
    hr = HeartRateSample(
        id="hr1",
        provider="mi_fitness",
        source_type="cloud_session",
        user_id="u1",
        timestamp=datetime(2025, 4, 1, 12, 0, 0),
        bpm=70,
        sample_type="passive",
    )
    body = BodyMeasurement(
        id="w1",
        provider="mi_fitness",
        source_type="cloud_session",
        user_id="u1",
        timestamp=datetime(2025, 4, 1, 7, 0, 0),
        weight_kg=101.5,
        bmi=28.0,
    )

    db.insert_daily_activity(activity)
    db.insert_heart_rate_sample(hr)
    db.insert_body_measurement(body)

    query = QueryService(db, "u1")
    assert len(query.get_daily_summaries("2025-04-01", "2025-04-01")) == 1
    assert len(query.get_heart_rate_samples("2025-04-01", "2025-04-01")) == 1
    assert len(query.get_body_measurements("2025-04-01", "2025-04-01")) == 1


def test_sleep_hrv_roundtrip(tmp_path):
    db = Database(tmp_path / "test.db")
    db.insert_sleep_session(_hrv_sleep())

    rows = QueryService(db, "u1").get_sleep_sessions("2026-10-28", "2026-10-28")

    assert len(rows) == 1
    row = rows[0]
    assert row["avg_hrv_ms"] == 76
    assert row["min_hrv_ms"] == 39
    assert row["max_hrv_ms"] == 107
    assert row["hrv_median_ms"] == 75
    assert row["hrv_std_ms"] == 0
    assert row["hrv_lower_quantile_ms"] == 52
    assert row["hrv_upper_quantile_ms"] == 102
    assert row["hrv_base_min_ms"] == 34
    assert row["hrv_base_max_ms"] == 76
    assert row["hrv_analysis_at"].startswith("2026-10-28T08:00:00")
    assert row["stages"] == [{"stage": "deep", "minutes": 100}]


def test_sleep_hrv_migration_from_legacy_schema(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE sleep_sessions (
            id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_record_id TEXT,
            user_id TEXT NOT NULL,
            device_id TEXT,
            timezone TEXT DEFAULT 'UTC',
            collected_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sleep_id TEXT NOT NULL,
            start_at TIMESTAMP NOT NULL,
            end_at TIMESTAMP NOT NULL,
            duration_minutes INTEGER NOT NULL,
            time_asleep_minutes INTEGER NOT NULL,
            time_awake_minutes INTEGER NOT NULL,
            sleep_score INTEGER,
            is_nap BOOLEAN DEFAULT FALSE,
            stages TEXT,
            UNIQUE(user_id, sleep_id)
        )
    """)
    conn.commit()
    conn.close()

    db = Database(path)
    conn = sqlite3.connect(path)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(sleep_sessions)")}
    conn.close()
    assert {
        "avg_hrv_ms",
        "min_hrv_ms",
        "max_hrv_ms",
        "hrv_median_ms",
        "hrv_std_ms",
        "hrv_lower_quantile_ms",
        "hrv_upper_quantile_ms",
        "hrv_base_min_ms",
        "hrv_base_max_ms",
        "hrv_analysis_at",
    } <= columns

    db.insert_sleep_session(_hrv_sleep())
    rows = QueryService(db, "u1").get_sleep_sessions("2026-10-28", "2026-10-28")
    assert rows[0]["avg_hrv_ms"] == 76
    assert rows[0]["hrv_analysis_at"].startswith("2026-10-28T08:00:00")
