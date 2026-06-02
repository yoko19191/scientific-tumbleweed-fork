from pathlib import Path
from types import SimpleNamespace

from deerflow.agents.lead_agent.prompt import get_skills_prompt_section
from deerflow.config.agents_config import AgentConfig
from deerflow.skills.tool_policy import filter_tools_by_skill_allowed_tools
from deerflow.skills.types import Skill


class NamedTool:
    def __init__(self, name: str):
        self.name = name


def _make_skill(name: str, allowed_tools: list[str] | None = None) -> Skill:
    return Skill(
        name=name,
        description=f"Description for {name}",
        license="MIT",
        skill_dir=Path(f"/tmp/{name}"),
        skill_file=Path(f"/tmp/{name}/SKILL.md"),
        relative_path=Path(name),
        category="public",
        allowed_tools=allowed_tools,
        enabled=True,
    )


def test_get_skills_prompt_section_returns_empty_when_no_skills_match(monkeypatch):
    skills = [_make_skill("skill1"), _make_skill("skill2")]
    monkeypatch.setattr("deerflow.agents.lead_agent.prompt._get_enabled_skills", lambda: skills)

    result = get_skills_prompt_section(available_skills={"non_existent_skill"})
    assert result == ""


def test_get_skills_prompt_section_returns_empty_when_available_skills_empty(monkeypatch):
    skills = [_make_skill("skill1"), _make_skill("skill2")]
    monkeypatch.setattr("deerflow.agents.lead_agent.prompt._get_enabled_skills", lambda: skills)

    result = get_skills_prompt_section(available_skills=set())
    assert result == ""


def test_get_skills_prompt_section_returns_skills(monkeypatch):
    skills = [_make_skill("skill1"), _make_skill("skill2")]
    monkeypatch.setattr("deerflow.agents.lead_agent.prompt._get_enabled_skills", lambda: skills)

    result = get_skills_prompt_section(available_skills={"skill1"})
    assert "skill1" in result
    assert "skill2" not in result
    assert "[built-in]" in result


def test_get_skills_prompt_section_returns_all_when_available_skills_is_none(monkeypatch):
    skills = [_make_skill("skill1"), _make_skill("skill2")]
    monkeypatch.setattr("deerflow.agents.lead_agent.prompt._get_enabled_skills", lambda: skills)

    result = get_skills_prompt_section(available_skills=None)
    assert "skill1" in result
    assert "skill2" in result


def test_get_skills_prompt_section_includes_self_evolution_rules(monkeypatch):
    skills = [_make_skill("skill1")]
    monkeypatch.setattr("deerflow.agents.lead_agent.prompt._get_enabled_skills", lambda: skills)
    monkeypatch.setattr(
        "deerflow.config.get_app_config",
        lambda: SimpleNamespace(
            skills=SimpleNamespace(container_path="/mnt/skills"),
            skill_evolution=SimpleNamespace(enabled=True),
        ),
    )

    result = get_skills_prompt_section(available_skills=None)
    assert "Skill Self-Evolution" in result


def test_get_skills_prompt_section_includes_self_evolution_rules_without_skills(monkeypatch):
    monkeypatch.setattr("deerflow.agents.lead_agent.prompt._get_enabled_skills", lambda: [])
    monkeypatch.setattr(
        "deerflow.config.get_app_config",
        lambda: SimpleNamespace(
            skills=SimpleNamespace(container_path="/mnt/skills"),
            skill_evolution=SimpleNamespace(enabled=True),
        ),
    )

    result = get_skills_prompt_section(available_skills=None)
    assert "Skill Self-Evolution" in result


def test_get_skills_prompt_section_cache_respects_skill_evolution_toggle(monkeypatch):
    skills = [_make_skill("skill1")]
    monkeypatch.setattr("deerflow.agents.lead_agent.prompt._get_enabled_skills", lambda: skills)
    config = SimpleNamespace(
        skills=SimpleNamespace(container_path="/mnt/skills"),
        skill_evolution=SimpleNamespace(enabled=True),
    )
    monkeypatch.setattr("deerflow.config.get_app_config", lambda: config)

    enabled_result = get_skills_prompt_section(available_skills=None)
    assert "Skill Self-Evolution" in enabled_result

    config.skill_evolution.enabled = False
    disabled_result = get_skills_prompt_section(available_skills=None)
    assert "Skill Self-Evolution" not in disabled_result


def test_make_computer_lead_agent_empty_skills_passed_correctly(monkeypatch):
    from unittest.mock import MagicMock

    from deerflow.agents.lead_agent import agent as lead_agent_module

    # Mock dependencies
    monkeypatch.setattr(lead_agent_module, "get_app_config", lambda: MagicMock())
    monkeypatch.setattr(lead_agent_module, "_resolve_model_name", lambda x=None: "default-model")
    monkeypatch.setattr(lead_agent_module, "create_chat_model", lambda **kwargs: "model")
    monkeypatch.setattr("deerflow.tools.get_available_tools", lambda **kwargs: [])
    monkeypatch.setattr(lead_agent_module, "_load_enabled_skills_for_tool_policy", lambda available_skills, *, app_config: [])
    monkeypatch.setattr(lead_agent_module, "_build_middlewares", lambda *args, **kwargs: [])
    monkeypatch.setattr(lead_agent_module, "create_agent", lambda **kwargs: kwargs)

    class MockModelConfig:
        supports_thinking = False

    mock_app_config = MagicMock()
    mock_app_config.get_model_config.return_value = MockModelConfig()
    monkeypatch.setattr(lead_agent_module, "get_app_config", lambda: mock_app_config)

    captured_skills = []

    def mock_apply_prompt_template(**kwargs):
        captured_skills.append(kwargs.get("available_skills"))
        return "mock_prompt"

    monkeypatch.setattr(lead_agent_module, "apply_prompt_template", mock_apply_prompt_template)

    # Case 1: Empty skills list
    monkeypatch.setattr(lead_agent_module, "load_agent_config", lambda x, user_id=None: AgentConfig(name="test", skills=[]))
    lead_agent_module.make_computer_lead_agent({"configurable": {"agent_name": "test"}})
    assert captured_skills[-1] == set()

    # Case 2: None skills list
    monkeypatch.setattr(lead_agent_module, "load_agent_config", lambda x, user_id=None: AgentConfig(name="test", skills=None))
    lead_agent_module.make_computer_lead_agent({"configurable": {"agent_name": "test"}})
    assert captured_skills[-1] is None

    # Case 3: Some skills list
    monkeypatch.setattr(lead_agent_module, "load_agent_config", lambda x, user_id=None: AgentConfig(name="test", skills=["skill1"]))
    lead_agent_module.make_computer_lead_agent({"configurable": {"agent_name": "test"}})
    assert captured_skills[-1] == {"skill1"}


def test_make_computer_lead_agent_filters_tools_from_available_skills(monkeypatch):
    from unittest.mock import MagicMock

    from deerflow.agents.lead_agent import agent as lead_agent_module

    monkeypatch.setattr(lead_agent_module, "_resolve_model_name", lambda x=None, **kwargs: "default-model")
    monkeypatch.setattr(lead_agent_module, "create_chat_model", lambda **kwargs: "model")
    monkeypatch.setattr(lead_agent_module, "_build_middlewares", lambda *args, **kwargs: [])
    monkeypatch.setattr(lead_agent_module, "apply_prompt_template", lambda **kwargs: "mock_prompt")
    monkeypatch.setattr(lead_agent_module, "create_agent", lambda **kwargs: kwargs)
    monkeypatch.setattr(lead_agent_module, "load_agent_config", lambda x: AgentConfig(name="test", skills=["restricted", "legacy"]))
    monkeypatch.setattr(lead_agent_module, "_load_enabled_skills_for_tool_policy", lambda available_skills, *, app_config: [_make_skill("restricted", ["read_file"]), _make_skill("legacy", None)])
    monkeypatch.setattr("deerflow.tools.get_available_tools", lambda **kwargs: [NamedTool("bash"), NamedTool("read_file"), NamedTool("web_search")])

    mock_app_config = MagicMock()
    mock_app_config.get_model_config.return_value = SimpleNamespace(supports_thinking=False, supports_vision=False)
    monkeypatch.setattr(lead_agent_module, "get_app_config", lambda: mock_app_config)

    agent_kwargs = lead_agent_module.make_computer_lead_agent({"configurable": {"agent_name": "test"}})

    assert [tool.name for tool in agent_kwargs["tools"]] == ["read_file"]


def test_make_computer_lead_agent_all_legacy_skills_preserve_all_tools(monkeypatch):
    from unittest.mock import MagicMock

    from deerflow.agents.lead_agent import agent as lead_agent_module

    monkeypatch.setattr(lead_agent_module, "_resolve_model_name", lambda x=None, **kwargs: "default-model")
    monkeypatch.setattr(lead_agent_module, "create_chat_model", lambda **kwargs: "model")
    monkeypatch.setattr(lead_agent_module, "_build_middlewares", lambda *args, **kwargs: [])
    monkeypatch.setattr(lead_agent_module, "apply_prompt_template", lambda **kwargs: "mock_prompt")
    monkeypatch.setattr(lead_agent_module, "create_agent", lambda **kwargs: kwargs)
    monkeypatch.setattr(lead_agent_module, "load_agent_config", lambda x: AgentConfig(name="test", skills=None))
    monkeypatch.setattr(lead_agent_module, "_load_enabled_skills_for_tool_policy", lambda available_skills, *, app_config: [_make_skill("legacy", None)])
    monkeypatch.setattr("deerflow.tools.get_available_tools", lambda **kwargs: [NamedTool("bash"), NamedTool("read_file")])

    mock_app_config = MagicMock()
    mock_app_config.get_model_config.return_value = SimpleNamespace(supports_thinking=False, supports_vision=False)
    monkeypatch.setattr(lead_agent_module, "get_app_config", lambda: mock_app_config)

    agent_kwargs = lead_agent_module.make_computer_lead_agent({"configurable": {"agent_name": "test"}})

    assert [tool.name for tool in agent_kwargs["tools"]] == ["bash", "read_file", "update_agent"]


def test_skill_allowed_tools_all_unknown_falls_back_to_allow_all(caplog):
    tools = [NamedTool("web_search"), NamedTool("read_file")]
    skills = [_make_skill("humanizer", ["Read", "Edit"])]

    with caplog.at_level("WARNING"):
        filtered = filter_tools_by_skill_allowed_tools(tools, skills)

    assert filtered == tools
    assert "matches no available tool" in caplog.text
    assert "humanizer" in caplog.text


def test_skill_allowed_tools_partial_unknown_keeps_matching_tools(caplog):
    tools = [NamedTool("web_search"), NamedTool("read_file"), NamedTool("bash")]
    skills = [_make_skill("humanizer", ["web_search", "Read"])]

    with caplog.at_level("WARNING"):
        filtered = filter_tools_by_skill_allowed_tools(tools, skills)

    assert [tool.name for tool in filtered] == ["web_search"]
    assert "unknown tool name" in caplog.text
    assert "Read" in caplog.text
