"""Shared Jinja2 renderer for prompt *partials*.

This module exists separately from :mod:`deerflow.prompts.factory.build_prompt`
to avoid an import cycle: ``build_prompt`` imports the section helpers in
``deerflow.prompts.sections``, and those helpers render partials through here.
Keeping the renderer dependency-light (only Jinja2 + stdlib) means both modules
can rely on it without circular imports.

Newline contract (critical for byte-identical output across the refactor):
partial template files follow the POSIX convention of ending with a single
trailing newline. Jinja2's default ``keep_trailing_newline=False`` strips
exactly that one newline before rendering, so a pure-text partial round-trips
to the exact string the old Python ``*_section()`` functions returned (which
ended at ``</tag>`` with no trailing newline).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_PARTIALS_SUBDIR = "partials"


@lru_cache(maxsize=1)
def _partial_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        # keep_trailing_newline left at its default (False): strip exactly one
        # trailing newline so POSIX-style partial files round-trip exactly.
        cache_size=128,
    )


def render_template(name: str, /, **context: Any) -> str:
    """Render a template path relative to ``prompts/templates``.

    Args:
        name: Template path, e.g. ``"partials/git_safety.j2"`` or
            ``"agents/title.j2"``.
        **context: Jinja2 template variables.

    Returns:
        The rendered template as a string (no enforced trailing newline).
    """
    template = _partial_environment().get_template(name)
    return template.render(**context)


def render_partial(name: str, /, **context: Any) -> str:
    """Render ``templates/partials/<name>`` with the given context."""
    return render_template(f"{_PARTIALS_SUBDIR}/{name}", **context)
