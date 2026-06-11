from faultpilot.retrieval.bm25_index import build_bm25_index
from faultpilot.retrieval.schemas import RetrievedChunk, RetrievalFilters


def _sample_chunks() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id="1",
            content="AL-09 Overheat of radiator",
            alarm_code="AL-09",
            equipment="A06B-6059-Hxxx",
            manufacturer="Fanuc",
            source_doc="ac_spindle_alarm_list.pdf",
            page=2,
        ),
        RetrievedChunk(
            chunk_id="2",
            content="2641 NO PANEL TRANSFER",
            alarm_code="2641",
            equipment="CC220/320",
            manufacturer="Bosch",
            source_doc="Error_messages_CC_220107007331804.pdf",
            page=140,
        ),
    ]


def test_bm25_search_returns_exact_alarm_first() -> None:
    index = build_bm25_index(_sample_chunks())

    hits = index.search("AL-09", top_k=2)

    assert hits[0].alarm_code == "AL-09"


def test_bm25_respects_manufacturer_filter() -> None:
    index = build_bm25_index(_sample_chunks())

    hits = index.search(
        "panel transfer",
        top_k=2,
        filters=RetrievalFilters(manufacturer="Bosch"),
    )

    assert len(hits) == 1
    assert hits[0].manufacturer == "Bosch"
