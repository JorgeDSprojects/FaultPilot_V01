from faultpilot.ingestion.parsers.bosch import parse_bosch_error_row


def test_parse_bosch_error_row_extracts_code_and_remedy() -> None:
    row = [
        "2641 NO PANEL TRANSFER\nNo connection between CP and panel.",
        "* Check connection between CP and panel.",
    ]

    chunk = parse_bosch_error_row(row=row, page_number=140, row_index=1)

    assert chunk is not None
    assert chunk.alarm_code == "2641"
    assert chunk.manufacturer == "Bosch"
    assert "NO PANEL TRANSFER" in chunk.content
    assert "Check connection" in chunk.content


def test_parse_bosch_error_row_supports_rows_without_numeric_code() -> None:
    row = [
        "> PANEL TRANSMITTER LINE FAULTY!",
        "* Check transmitter line and connections.",
    ]

    chunk = parse_bosch_error_row(row=row, page_number=142, row_index=4)

    assert chunk is not None
    assert chunk.alarm_code is None
    assert chunk.raw_table_ref == "row_4"
