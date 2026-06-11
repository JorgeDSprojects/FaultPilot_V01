import json
from pathlib import Path

from faultpilot.retrieval.loaders import build_chunk_id, load_chunks


def test_build_chunk_id_is_stable() -> None:
    value1 = build_chunk_id(
        "ac_spindle_alarm_list.pdf",
        2,
        "A06B-6059-Hxxx",
        "AL-09",
        "Overheat",
    )
    value2 = build_chunk_id(
        "ac_spindle_alarm_list.pdf",
        2,
        "A06B-6059-Hxxx",
        "AL-09",
        "Overheat",
    )

    assert value1 == value2


def test_load_chunks_from_jsonl_directory(tmp_path: Path) -> None:
    row = {
        "content": "AL-09 Overheat of radiator",
        "alarm_code": "AL-09",
        "equipment": "A06B-6059-Hxxx",
        "manufacturer": "Fanuc",
        "source_doc": "ac_spindle_alarm_list.pdf",
        "page": 2,
        "category": "alarm",
        "description": "Overheat of radiator",
        "language": "en",
        "raw_table_ref": "page_2",
    }
    out = tmp_path / "fanuc_ac_spindle_chunks.jsonl"
    out.write_text(json.dumps(row) + "\n", encoding="utf-8")

    chunks = load_chunks(tmp_path)

    assert len(chunks) == 1
    assert chunks[0].alarm_code == "AL-09"
    assert chunks[0].manufacturer == "Fanuc"
