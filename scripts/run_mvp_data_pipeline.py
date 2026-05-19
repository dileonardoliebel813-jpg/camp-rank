from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def _resolve_root_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path.resolve()
    return (ROOT / path).resolve()


def _backend_arg(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BACKEND.resolve()))
    except ValueError:
        return str(path.resolve())


def _run(command: list[str], cwd: Path) -> None:
    print(f"\n[CampRank Pipeline] {cwd}> {' '.join(command)}")
    completed = subprocess.run(command, cwd=cwd)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the CampRank MVP data-to-frontend pipeline from a local JD workbook or normalized JSON."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-xlsx", help="Local JD workbook path, for example data.xlsx.")
    source.add_argument("--json", dest="json_path", help="Already normalized CampRank JSON path.")
    parser.add_argument(
        "--output-json",
        default="backend/data/real_samples/jd_tents_mvp.json",
        help="Output JSON path when --input-xlsx is used.",
    )
    parser.add_argument("--sheet", default="data", help="Workbook sheet name.")
    parser.add_argument("--platform", default="JD", help="Platform label written into pipeline reporting.")
    parser.add_argument("--price-groups", nargs="*", type=float, default=None, help="Optional fixed price groups.")
    parser.add_argument("--skip-checks", action="store_true", help="Skip scripts/check_all.py after import and scoring.")
    parser.add_argument(
        "--append",
        action="store_true",
        help="Deprecated compatibility flag. Append/update is now the default behavior.",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Back up and rebuild the SQLite database before importing. Use only when explicitly replacing the product library.",
    )
    parser.add_argument(
        "--keep-sample-data",
        action="store_true",
        help="Seed historical sample/mock data before import. Do not use for the current JD-only real-data flow.",
    )
    args = parser.parse_args()

    if args.input_xlsx:
        input_path = _resolve_root_path(args.input_xlsx)
        output_path = _resolve_root_path(args.output_json)
        build_command = [
            sys.executable,
            "scripts/build_jd_mvp_from_xlsx.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--sheet",
            args.sheet,
        ]
        if args.price_groups:
            build_command.extend(["--price-groups", *[str(value) for value in args.price_groups]])
        _run(build_command, BACKEND)
        json_path = output_path
    else:
        json_path = _resolve_root_path(args.json_path)

    import_command = [
        sys.executable,
        "scripts/run_real_data_pipeline.py",
        "--json",
        _backend_arg(json_path),
        "--platform",
        args.platform,
    ]
    if args.reset_db:
        import_command.append("--reset-db")
    if not args.keep_sample_data:
        import_command.append("--no-sample-data")
    _run(import_command, BACKEND)

    if not args.skip_checks:
        _run([sys.executable, "scripts/check_all.py"], ROOT)

    print("\n[CampRank Pipeline] Finished.")
    print(f"Normalized JSON: {json_path}")
    print("\nStart backend:")
    print("  cd backend")
    print("  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
    print("\nStart frontend:")
    print("  cd frontend")
    print("  npm run dev -- --host 127.0.0.1 --port 5173")
    print("\nOpen:")
    print("  http://127.0.0.1:5173/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
