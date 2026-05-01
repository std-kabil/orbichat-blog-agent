from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


class PromptNotFoundError(FileNotFoundError):
    pass


@lru_cache(maxsize=128)
def load_prompt(relative_path: str) -> str:
    prompt_path = _resolve_prompt_path(relative_path)
    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise PromptNotFoundError(f"Prompt file not found: {relative_path}") from exc


def render_prompt(relative_path: str, **values: object) -> str:
    return load_prompt(relative_path).format(**values)


def _resolve_prompt_path(relative_path: str) -> Path:
    raw_path = Path(relative_path)
    if not relative_path or raw_path.is_absolute() or ".." in raw_path.parts:
        raise ValueError(f"Invalid prompt path: {relative_path}")

    prompt_path = (PROMPTS_DIR / raw_path).resolve()
    prompt_path.relative_to(PROMPTS_DIR.resolve())
    return prompt_path
