from faultpilot.ingestion.parsers.fanuc import extract_fanuc_chunks_from_lines


def test_extract_fanuc_chunks_reads_equipment_and_alarm_code() -> None:
    lines = [
        "Alarm List for A06B-6059-Hxxx",
        "Alarm # Meaning",
        "AL-09 Overheat of radiator",
    ]

    chunks = extract_fanuc_chunks_from_lines(lines, page_number=2)

    assert len(chunks) == 1
    assert chunks[0].equipment == "A06B-6059-Hxxx"
    assert chunks[0].alarm_code == "AL-09"
    assert "Overheat of radiator" in chunks[0].content


def test_extract_fanuc_chunks_handles_legacy_numeric_alarm_rows() -> None:
    lines = [
        "Alarm List for A06B-6044-Hxxx",
        "1 o Motor Overheat",
        "2 o Speed deviates from commanded speed",
    ]

    chunks = extract_fanuc_chunks_from_lines(lines, page_number=1)

    assert [chunk.alarm_code for chunk in chunks] == ["AL-01", "AL-02"]
