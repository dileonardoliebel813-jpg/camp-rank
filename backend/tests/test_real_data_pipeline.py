from pathlib import Path
import os
import sqlite3
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _env(tmp_path):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{tmp_path / 'pipeline_test.db'}"
    env["JD_API_ENABLED"] = "false"
    return env


def test_run_real_data_pipeline_handles_local_json(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_real_data_pipeline.py",
            "--json",
            "data/real_samples/tents_real_sample.json",
            "--platform",
            "JD",
        ],
        cwd=ROOT,
        env=_env(tmp_path),
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert "ImportReport:" in result.stdout
    assert "Pipeline final stats:" in result.stdout
    assert "field_completeness" in result.stdout


def test_run_real_data_pipeline_updates_analysis_and_scores(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_real_data_pipeline.py",
            "--adapter",
            "jd",
            "--input",
            "data/real_samples/jd_tents_sample.json",
            "--platform",
            "JD",
        ],
        cwd=ROOT,
        env=_env(tmp_path),
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert '"analyzed_comments"' in result.stdout
    assert '"updated_scores"' in result.stdout
    assert '"warnings"' in result.stdout
    assert '"field_completeness"' in result.stdout


def test_run_real_data_pipeline_can_skip_sample_data_and_reset_db(tmp_path):
    db_path = tmp_path / "pipeline_clean_import.db"
    env = _env(tmp_path)
    env["DATABASE_URL"] = f"sqlite:///{db_path}"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_real_data_pipeline.py",
            "--json",
            "data/real_samples/tents_real_sample.json",
            "--platform",
            "JD",
            "--reset-db",
            "--no-sample-data",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert result.returncode == 0
    assert "Sample data seeding skipped" in result.stdout
    with sqlite3.connect(db_path) as connection:
        canonical_count = connection.execute("select count(*) from canonical_products").fetchone()[0]
    assert canonical_count == 3
