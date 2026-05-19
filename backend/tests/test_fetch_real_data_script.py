from pathlib import Path
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _env(tmp_path):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{tmp_path / 'script_fetch_test.db'}"
    env["SMZDM_API_ENABLED"] = "false"
    return env


def test_fetch_real_data_script_local_input_succeeds(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/fetch_real_data.py",
            "--source",
            "smzdm",
            "--keyword",
            "帐篷",
            "--limit",
            "20",
            "--input",
            "data/real_samples/smzdm_tents_sample.json",
        ],
        cwd=ROOT,
        env=_env(tmp_path),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert '"source": "smzdm"' in result.stdout
    assert "analyze_comments.py" in result.stdout


def test_fetch_real_data_script_requires_live_or_input(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/fetch_real_data.py", "--source", "smzdm", "--keyword", "帐篷"],
        cwd=ROOT,
        env=_env(tmp_path),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "--input is required" in result.stderr


def test_fetch_real_data_script_live_missing_config_fails_clearly(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/fetch_real_data.py",
            "--source",
            "smzdm",
            "--keyword",
            "帐篷",
            "--live",
        ],
        cwd=ROOT,
        env=_env(tmp_path),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "SMZDM_API_ENABLED=false" in result.stdout
