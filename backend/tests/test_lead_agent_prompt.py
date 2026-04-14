import threading
from pathlib import Path
from types import SimpleNamespace

import anyio

from deerflow.agents.lead_agent import prompt as prompt_module
from deerflow.prompts.sections import SYSTEM_PROMPT_DYNAMIC_BOUNDARY
from deerflow.skills.types import Skill


def test_build_custom_mounts_section_returns_empty_when_no_mounts(monkeypatch):
    config = SimpleNamespace(sandbox=SimpleNamespace(mounts=[]))
    monkeypatch.setattr("deerflow.config.get_app_config", lambda: config)

    assert prompt_module._build_custom_mounts_section() == ""


def _patch_prompt_dependencies(monkeypatch, *, skills=None, memory="", soul=""):
    config = SimpleNamespace(
        sandbox=SimpleNamespace(mounts=[]),
        skills=SimpleNamespace(container_path="/mnt/skills"),
        skill_evolution=SimpleNamespace(enabled=False),
    )
    monkeypatch.setattr("deerflow.config.get_app_config", lambda: config)
    monkeypatch.setattr(prompt_module, "_get_enabled_skills", lambda: skills or [])
    monkeypatch.setattr(prompt_module, "get_deferred_tools_prompt_section", lambda: "")
    monkeypatch.setattr(prompt_module, "_build_acp_section", lambda: "")
    monkeypatch.setattr(prompt_module, "_get_memory_context", lambda user_id=None: memory)
    monkeypatch.setattr(prompt_module, "get_agent_soul", lambda agent_name=None, user_id=None: soul)


def test_apply_prompt_template_uses_scientific_tumbleweed_brand(monkeypatch):
    _patch_prompt_dependencies(monkeypatch)

    prompt = prompt_module.apply_prompt_template()

    assert "科学风滚草" in prompt
    assert "良渚实验室" in prompt
    assert "DeerFlow 2.0" not in prompt
    assert SYSTEM_PROMPT_DYNAMIC_BOUNDARY in prompt


def test_apply_prompt_template_custom_agent_keeps_name_and_platform_style(monkeypatch):
    _patch_prompt_dependencies(monkeypatch)

    prompt = prompt_module.apply_prompt_template(agent_name="lab-agent")

    assert "你是 lab-agent" in prompt
    assert "科学风滚草" in prompt
    assert "良渚实验室" in prompt
    assert "<conversation_craft>" in prompt
    assert "<collaboration_mechanics>" in prompt
    assert "让回答像自然发生的协作，而不是模板生成" in prompt


def test_apply_prompt_template_subagent_section_still_feature_gated(monkeypatch):
    _patch_prompt_dependencies(monkeypatch)

    disabled_prompt = prompt_module.apply_prompt_template(subagent_enabled=False)
    enabled_prompt = prompt_module.apply_prompt_template(subagent_enabled=True, max_concurrent_subagents=2)

    assert "<subagent_system>" not in disabled_prompt
    assert "<subagent_system>" in enabled_prompt
    assert "MAXIMUM 2 `task` CALLS PER RESPONSE" in enabled_prompt


def test_dynamic_sections_remain_after_cache_boundary(monkeypatch):
    skill = Skill(
        name="science-skill",
        description="Description for science-skill",
        license="MIT",
        skill_dir=Path("/tmp/science-skill"),
        skill_file=Path("/tmp/science-skill/SKILL.md"),
        relative_path=Path("science-skill"),
        category="public",
        enabled=True,
    )
    _patch_prompt_dependencies(monkeypatch, skills=[skill], memory="<memory>\nUser prefers concise research notes.\n</memory>")

    prompt = prompt_module.apply_prompt_template()
    idx = prompt.index(SYSTEM_PROMPT_DYNAMIC_BOUNDARY)

    assert "<platform_persona>" in prompt[:idx]
    assert "<conversation_craft>" in prompt[:idx]
    assert "<collaboration_mechanics>" in prompt[:idx]
    assert "<memory>" in prompt[idx:]
    assert "<skill_system>" in prompt[idx:]


def test_apply_prompt_template_includes_anti_template_conversation_rules(monkeypatch):
    _patch_prompt_dependencies(monkeypatch)

    prompt = prompt_module.apply_prompt_template()

    assert "避免机械开场" in prompt
    assert "不要夸问题、夸用户、总结需求来凑开头" in prompt
    assert "作为一个 AI" in prompt


def test_apply_prompt_template_includes_collaboration_mechanics(monkeypatch):
    _patch_prompt_dependencies(monkeypatch)

    prompt = prompt_module.apply_prompt_template()

    assert "上下文连续" in prompt
    assert "技能路由" in prompt
    assert "文件交付" in prompt
    assert "研究证据" in prompt
    assert "关系边界" in prompt
    assert "当前用户明确指令优先于旧记忆" in prompt


def test_build_custom_mounts_section_lists_configured_mounts(monkeypatch):
    mounts = [
        SimpleNamespace(container_path="/home/user/shared", read_only=False),
        SimpleNamespace(container_path="/mnt/reference", read_only=True),
    ]
    config = SimpleNamespace(sandbox=SimpleNamespace(mounts=mounts))
    monkeypatch.setattr("deerflow.config.get_app_config", lambda: config)

    section = prompt_module._build_custom_mounts_section()

    assert "**Custom Mounted Directories:**" in section
    assert "`/home/user/shared`" in section
    assert "read-write" in section
    assert "`/mnt/reference`" in section
    assert "read-only" in section


def test_apply_prompt_template_includes_custom_mounts(monkeypatch):
    mounts = [SimpleNamespace(container_path="/home/user/shared", read_only=False)]
    config = SimpleNamespace(
        sandbox=SimpleNamespace(mounts=mounts),
        skills=SimpleNamespace(container_path="/mnt/skills"),
    )
    monkeypatch.setattr("deerflow.config.get_app_config", lambda: config)
    monkeypatch.setattr(prompt_module, "_get_enabled_skills", lambda: [])
    monkeypatch.setattr(prompt_module, "get_deferred_tools_prompt_section", lambda: "")
    monkeypatch.setattr(prompt_module, "_build_acp_section", lambda: "")
    monkeypatch.setattr(prompt_module, "_get_memory_context", lambda user_id=None: "")
    monkeypatch.setattr(prompt_module, "get_agent_soul", lambda agent_name=None, user_id=None: "")

    prompt = prompt_module.apply_prompt_template()

    assert "`/home/user/shared`" in prompt
    assert "Custom Mounted Directories" in prompt


def test_apply_prompt_template_includes_relative_path_guidance(monkeypatch):
    config = SimpleNamespace(
        sandbox=SimpleNamespace(mounts=[]),
        skills=SimpleNamespace(container_path="/mnt/skills"),
    )
    monkeypatch.setattr("deerflow.config.get_app_config", lambda: config)
    monkeypatch.setattr(prompt_module, "_get_enabled_skills", lambda: [])
    monkeypatch.setattr(prompt_module, "get_deferred_tools_prompt_section", lambda: "")
    monkeypatch.setattr(prompt_module, "_build_acp_section", lambda: "")
    monkeypatch.setattr(prompt_module, "_get_memory_context", lambda agent_name=None: "")
    monkeypatch.setattr(prompt_module, "get_agent_soul", lambda agent_name=None, user_id=None: "")

    prompt = prompt_module.apply_prompt_template()

    assert "Treat `/mnt/user-data/workspace` as your default current working directory" in prompt
    assert "`hello.txt`, `../uploads/data.csv`, and `../outputs/report.md`" in prompt


def test_refresh_skills_system_prompt_cache_async_reloads_immediately(monkeypatch, tmp_path):
    def make_skill(name: str) -> Skill:
        skill_dir = tmp_path / name
        return Skill(
            name=name,
            description=f"Description for {name}",
            license="MIT",
            skill_dir=skill_dir,
            skill_file=skill_dir / "SKILL.md",
            relative_path=skill_dir.relative_to(tmp_path),
            category="custom",
            enabled=True,
        )

    state = {"skills": [make_skill("first-skill")]}
    monkeypatch.setattr(prompt_module, "load_skills", lambda enabled_only=True: list(state["skills"]))
    prompt_module._reset_skills_system_prompt_cache_state()

    try:
        prompt_module.warm_enabled_skills_cache()
        assert [skill.name for skill in prompt_module._get_enabled_skills()] == ["first-skill"]

        state["skills"] = [make_skill("second-skill")]
        anyio.run(prompt_module.refresh_skills_system_prompt_cache_async)

        assert [skill.name for skill in prompt_module._get_enabled_skills()] == ["second-skill"]
    finally:
        prompt_module._reset_skills_system_prompt_cache_state()


def test_clear_cache_does_not_spawn_parallel_refresh_workers(monkeypatch, tmp_path):
    started = threading.Event()
    release = threading.Event()
    active_loads = 0
    max_active_loads = 0
    call_count = 0
    lock = threading.Lock()

    def make_skill(name: str) -> Skill:
        skill_dir = tmp_path / name
        return Skill(
            name=name,
            description=f"Description for {name}",
            license="MIT",
            skill_dir=skill_dir,
            skill_file=skill_dir / "SKILL.md",
            relative_path=skill_dir.relative_to(tmp_path),
            category="custom",
            enabled=True,
        )

    def fake_load_skills(enabled_only=True):
        nonlocal active_loads, max_active_loads, call_count
        with lock:
            active_loads += 1
            max_active_loads = max(max_active_loads, active_loads)
            call_count += 1
            current_call = call_count

        started.set()
        if current_call == 1:
            release.wait(timeout=5)

        with lock:
            active_loads -= 1

        return [make_skill(f"skill-{current_call}")]

    monkeypatch.setattr(prompt_module, "load_skills", fake_load_skills)
    prompt_module._reset_skills_system_prompt_cache_state()

    try:
        prompt_module.clear_skills_system_prompt_cache()
        assert started.wait(timeout=5)

        prompt_module.clear_skills_system_prompt_cache()
        release.set()
        prompt_module.warm_enabled_skills_cache()

        assert max_active_loads == 1
        assert [skill.name for skill in prompt_module._get_enabled_skills()] == ["skill-2"]
    finally:
        release.set()
        prompt_module._reset_skills_system_prompt_cache_state()


def test_warm_enabled_skills_cache_logs_on_timeout(monkeypatch, caplog):
    event = threading.Event()
    monkeypatch.setattr(prompt_module, "_ensure_enabled_skills_cache", lambda: event)

    with caplog.at_level("WARNING"):
        warmed = prompt_module.warm_enabled_skills_cache(timeout_seconds=0.01)

    assert warmed is False
    assert "Timed out waiting" in caplog.text
