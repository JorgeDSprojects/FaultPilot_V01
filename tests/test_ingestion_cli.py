from pathlib import Path

from faultpilot.ingestion.cli import build_parser, main


def test_cli_defaults_to_bosch_and_fanuc() -> None:
    parser = build_parser()
    args = parser.parse_args([])

    assert args.documents == ["bosch", "fanuc"]


def test_main_dry_run_succeeds_with_empty_raw_dir(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()

    exit_code = main(
        [
            "--raw-dir",
            str(raw_dir),
            "--processed-dir",
            str(processed_dir),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert processed_dir.exists()
