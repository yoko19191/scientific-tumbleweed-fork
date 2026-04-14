"""Tests for the modular prompt builder (deerflow.prompts)."""

from deerflow.prompts import SystemPromptBuilder, split_prompt_for_caching
from deerflow.prompts.sections import SYSTEM_PROMPT_DYNAMIC_BOUNDARY


class TestSystemPromptBuilder:
    def test_basic_build(self):
        prompt = SystemPromptBuilder(agent_name="TestAgent").build()
        assert len(prompt) > 100
        assert "TestAgent" in prompt
        assert "科学风滚草" in prompt
        assert "良渚实验室" in prompt

    def test_default_branding(self):
        prompt = SystemPromptBuilder().build()
        assert "科学风滚草" in prompt
        assert "良渚实验室" in prompt
        assert "DeerFlow 2.0" not in prompt

    def test_contains_boundary(self):
        prompt = SystemPromptBuilder().build()
        assert SYSTEM_PROMPT_DYNAMIC_BOUNDARY in prompt

    def test_static_sections_before_boundary(self):
        prompt = SystemPromptBuilder().build()
        idx = prompt.index(SYSTEM_PROMPT_DYNAMIC_BOUNDARY)
        static = prompt[:idx]
        assert "<role>" in static
        assert "<platform_persona>" in static
        assert "<conversation_craft>" in static
        assert "<collaboration_mechanics>" in static
        assert "让回答像自然发生的协作，而不是模板生成" in static
        assert "<system_rules>" in static
        assert "<task_philosophy>" in static
        assert "<git_safety>" in static
        assert "<linter_feedback>" in static

    def test_conversation_craft_reduces_generic_ai_style(self):
        prompt = SystemPromptBuilder().build()

        assert "避免机械开场" in prompt
        assert "不要夸问题、夸用户、总结需求来凑开头" in prompt
        assert "不要用“作为一个 AI”" in prompt

    def test_collaboration_mechanics_cover_third_layer(self):
        prompt = SystemPromptBuilder().build()

        assert "上下文连续" in prompt
        assert "技能路由" in prompt
        assert "文件交付" in prompt
        assert "工具判断" in prompt
        assert "研究证据" in prompt
        assert "关系边界" in prompt
        assert "严肃主题" in prompt
        assert "当前用户明确指令优先于旧记忆" in prompt
        assert "区分事实、推断、假设和建议" in prompt

    def test_dynamic_sections_after_boundary(self):
        prompt = SystemPromptBuilder().with_memory("[Memory] user prefers Chinese").with_skills("[Skills] web_search").build()
        idx = prompt.index(SYSTEM_PROMPT_DYNAMIC_BOUNDARY)
        dynamic = prompt[idx:]
        assert "[Memory]" in dynamic
        assert "[Skills]" in dynamic

    def test_environment_injection(self):
        prompt = SystemPromptBuilder().with_environment(cwd="/workspace", date_str="2026-04-01").build()
        assert "/workspace" in prompt
        assert "2026-04-01" in prompt

    def test_specialized_agents(self):
        prompt = SystemPromptBuilder().with_subagent("subagent section", enabled=True).with_specialized_agents(verification=True, explore=True, plan=True).build()
        assert "verification" in prompt
        assert "explore" in prompt

    def test_fluent_interface_returns_self(self):
        builder = SystemPromptBuilder()
        assert builder.with_memory("x") is builder
        assert builder.with_skills("y") is builder
        assert builder.with_environment() is builder

    def test_extra_sections(self):
        prompt = SystemPromptBuilder().add_static_section("<custom_static>test</custom_static>").add_dynamic_section("<custom_dynamic>test</custom_dynamic>").build()
        idx = prompt.index(SYSTEM_PROMPT_DYNAMIC_BOUNDARY)
        assert "<custom_static>" in prompt[:idx]
        assert "<custom_dynamic>" in prompt[idx:]


class TestSplitPromptForCaching:
    def test_split_at_boundary(self):
        prompt = SystemPromptBuilder().with_memory("test memory").build()
        static, dynamic = split_prompt_for_caching(prompt)
        assert len(static) > 0
        assert len(dynamic) > 0
        assert "test memory" in dynamic
        assert "<role>" in static

    def test_no_boundary(self):
        static, dynamic = split_prompt_for_caching("simple prompt without boundary")
        assert static == "simple prompt without boundary"
        assert dynamic == ""
