import pytest

from faultpilot.ingestion.contracts import ChunkRecord, normalize_alarm_code


def test_normalize_alarm_code_strips_and_uppercases() -> None:
    assert normalize_alarm_code(" al-09 ") == "AL-09"


def test_chunk_record_requires_manufacturer() -> None:
    with pytest.raises(ValueError, match="manufacturer"):
        ChunkRecord(
            content="motor overheating",
            alarm_code="AL-09",
            equipment="A06B-6055-Hxxx",
            manufacturer="",
            source_doc="ac_spindle_alarm_list.pdf",
            page=1,
        )


def test_chunk_record_allows_null_alarm_code() -> None:
    chunk = ChunkRecord(
        content="General troubleshooting guidance",
        alarm_code=None,
        equipment="CC220",
        manufacturer="Bosch",
        source_doc="Error_messages_CC_220107007331804.pdf",
        page=12,
    )

    data = chunk.to_dict()

    assert data["alarm_code"] is None
    assert data["manufacturer"] == "Bosch"
    assert data["page"] == 12
