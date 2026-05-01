import json

import pytest

from agents.topic_scorer import _topic_scoring_messages
from schemas.trend import TopicCandidateInput
from services.prompts import PromptNotFoundError, load_prompt, render_prompt


def test_load_prompt_reads_prompt_directory_file() -> None:
    prompt = load_prompt("blog_generation/article_draft.system.md")

    assert "OrbiChat.ai" in prompt
    assert "Return only JSON" in prompt


def test_load_prompt_rejects_paths_outside_prompt_directory() -> None:
    with pytest.raises(ValueError):
        load_prompt("../pyproject.toml")


def test_load_prompt_raises_clear_error_for_missing_file() -> None:
    with pytest.raises(PromptNotFoundError, match="missing.system.md"):
        load_prompt("blog_generation/missing.system.md")


def test_render_prompt_injects_schema_instruction_values() -> None:
    prompt = render_prompt(
        "llm_router/json_retry.user.md",
        model_name="ExampleOutput",
        parse_error="field required",
    )

    assert "ExampleOutput" in prompt
    assert "field required" in prompt


def test_topic_scoring_messages_use_prompt_files() -> None:
    topic_input = TopicCandidateInput(
        seed_query="AI chat apps",
        candidate_titles=["Best AI chat apps"],
        source_urls=["https://example.com"],
        snippets=["Useful source"],
    )

    messages = _topic_scoring_messages(topic_input)

    assert messages[0]["content"] == load_prompt("topic_scorer/score_candidate.system.md")
    assert load_prompt("topic_scorer/score_candidate.user.md") in messages[1]["content"]
    assert json.loads(messages[1]["content"].split("Trend cluster input:\n", 1)[1])["seed_query"] == (
        "AI chat apps"
    )
