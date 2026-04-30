from types import SimpleNamespace

from services.cost_tracker import LLMUsage, extract_llm_usage


def test_extract_llm_usage_from_provider_response() -> None:
    completion = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=34),
    )

    assert extract_llm_usage(completion) == LLMUsage(input_tokens=12, output_tokens=34)
