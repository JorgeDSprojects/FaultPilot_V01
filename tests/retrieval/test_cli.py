from faultpilot.retrieval.cli import main


def test_cli_search_dry_run_returns_zero_exit_code() -> None:
    code = main(["search", "--query", "AL-09", "--dry-run"])

    assert code == 0


def test_cli_index_dry_run_returns_zero_exit_code() -> None:
    code = main(["index", "--dry-run"])

    assert code == 0
