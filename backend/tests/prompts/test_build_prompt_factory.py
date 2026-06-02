from deerflow.prompts import SYSTEM_PROMPT_DYNAMIC_BOUNDARY, PromptContext, build_prompt, split_prompt_for_caching


def test_build_prompt_renders_lead_prompt_with_ground_truth_and_boundary():
    prompt = build_prompt(
        "computer_lead",
        PromptContext(
            agent_name="lab-agent",
            subagent_enabled=True,
            subagent_section="<subagent_system>enabled</subagent_system>",
            skills_section="<skill_system>skills</skill_system>",
            clarification_section="<clarification_system>clarify</clarification_system>",
            working_directory_section="<working_directory>wd</working_directory>",
            citations_section="<citations>cite</citations>",
            has_verification=True,
            has_explore=True,
            has_plan=True,
        ),
    )

    assert "<ground_truth>" in prompt
    assert "Scientific Tumbleweed" in prompt
    assert "你是 lab-agent" in prompt
    assert SYSTEM_PROMPT_DYNAMIC_BOUNDARY in prompt

    static_prefix, dynamic_suffix = split_prompt_for_caching(prompt)
    assert "<platform_persona>" in static_prefix
    assert "<skill_system>skills</skill_system>" in dynamic_suffix
    assert "<subagent_system>enabled</subagent_system>" in dynamic_suffix


def test_build_prompt_renders_builtin_subagents_with_ground_truth():
    for agent_key in ("general-purpose", "bash", "explore", "plan", "verification"):
        prompt = build_prompt(agent_key, PromptContext(skill_messages="<skill name='x'>body</skill>"))
        assert "<ground_truth>" in prompt
        assert "<skill name='x'>body</skill>" in prompt
        assert len(prompt) > 200
