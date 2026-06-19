from faultpilot.rag.generator import RagAnswerGenerator
from faultpilot.rag.schemas import Citation


class _CaptureClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "ok"


def test_generate_strict_includes_explicit_citation_tokens() -> None:
    client = _CaptureClient()
    generator = RagAnswerGenerator(client=client)
    citations = [Citation(source_doc="ac_spindle_alarm_list.pdf", page=1)]

    _ = generator.generate(
        query="AL-09",
        intent="alarm_lookup",
        context="context block",
        citations=citations,
        strict=True,
    )

    assert len(client.prompts) == 1
    prompt = client.prompts[0]
    assert "Use one of these exact citation tokens" in prompt
    assert "[ac_spindle_alarm_list.pdf:p.1]" in prompt
    assert "[ac_spindle_alarm_list.pdf:1]" in prompt
