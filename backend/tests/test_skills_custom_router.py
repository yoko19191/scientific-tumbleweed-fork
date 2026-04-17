import json
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.deps import get_current_user_id
from app.gateway.routers import skills as skills_router
from deerflow.skills.manager import get_skill_history_file
from deerflow.skills.types import Skill

_TEST_USER_ID = "test-user-001"


def _skill_content(name: str, description: str = "Demo skill") -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"


async def _async_scan(decision: str, reason: str):
    from deerflow.skills.security_scanner import ScanResult

    return ScanResult(decision=decision, reason=reason)


def _make_skill(name: str, *, enabled: bool) -> Skill:
    skill_dir = Path(f"/tmp/{name}")
    return Skill(
        name=name,
        description=f"Description for {name}",
        license="MIT",
        skill_dir=skill_dir,
        skill_file=skill_dir / "SKILL.md",
        relative_path=Path(name),
        category="public",
        enabled=enabled,
    )


def _setup_skills_test(monkeypatch, tmp_path, *, skill_name="demo-skill", skill_content=None):
    """Common setup for skills router tests: creates user-scoped skill dirs and patches."""
    from deerflow.config.paths import Paths

    paths_instance = Paths(base_dir=tmp_path)
    skills_root = tmp_path / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    # User-scoped custom skill directory
    user_custom_dir = paths_instance.user_skills_custom_dir(_TEST_USER_ID)
    skill_dir = user_custom_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = skill_content or _skill_content(skill_name)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("deerflow.config.get_app_config", lambda: config)
    monkeypatch.setattr("deerflow.skills.manager.get_app_config", lambda: config)
    monkeypatch.setattr("deerflow.config.paths.get_paths", lambda: paths_instance)
    return paths_instance, skills_root, skill_dir


def test_custom_skills_router_lifecycle(monkeypatch, tmp_path):
    paths_instance, skills_root, custom_dir = _setup_skills_test(monkeypatch, tmp_path)
    monkeypatch.setattr("app.gateway.routers.skills.scan_skill_content", lambda *args, **kwargs: _async_scan("allow", "ok"))
    refresh_calls = []

    async def _refresh():
        refresh_calls.append("refresh")

    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _refresh)

    app = FastAPI()
    app.include_router(skills_router.router)
    app.dependency_overrides[get_current_user_id] = lambda: _TEST_USER_ID

    with TestClient(app) as client:
        response = client.get("/api/skills/custom")
        assert response.status_code == 200
        assert response.json()["skills"][0]["name"] == "demo-skill"

        get_response = client.get("/api/skills/custom/demo-skill")
        assert get_response.status_code == 200
        assert "# demo-skill" in get_response.json()["content"]

        update_response = client.put(
            "/api/skills/custom/demo-skill",
            json={"content": _skill_content("demo-skill", "Edited skill")},
        )
        assert update_response.status_code == 200
        assert update_response.json()["description"] == "Edited skill"

        history_response = client.get("/api/skills/custom/demo-skill/history")
        assert history_response.status_code == 200
        assert history_response.json()["history"][-1]["action"] == "human_edit"

        rollback_response = client.post("/api/skills/custom/demo-skill/rollback", json={"history_index": -1})
        assert rollback_response.status_code == 200
        assert rollback_response.json()["description"] == "Demo skill"
        assert refresh_calls == ["refresh", "refresh"]


def test_custom_skill_rollback_blocked_by_scanner(monkeypatch, tmp_path):
    paths_instance, skills_root, custom_dir = _setup_skills_test(monkeypatch, tmp_path, skill_content=_skill_content("demo-skill", "Edited skill"))
    original_content = _skill_content("demo-skill")
    edited_content = _skill_content("demo-skill", "Edited skill")
    get_skill_history_file("demo-skill", user_id=_TEST_USER_ID).parent.mkdir(parents=True, exist_ok=True)
    get_skill_history_file("demo-skill", user_id=_TEST_USER_ID).write_text(
        '{"action":"human_edit","prev_content":' + json.dumps(original_content) + ',"new_content":' + json.dumps(edited_content) + "}\n",
        encoding="utf-8",
    )

    async def _refresh():
        return None

    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _refresh)

    async def _scan(*args, **kwargs):
        from deerflow.skills.security_scanner import ScanResult

        return ScanResult(decision="block", reason="unsafe rollback")

    monkeypatch.setattr("app.gateway.routers.skills.scan_skill_content", _scan)

    app = FastAPI()
    app.include_router(skills_router.router)
    app.dependency_overrides[get_current_user_id] = lambda: _TEST_USER_ID

    with TestClient(app) as client:
        rollback_response = client.post("/api/skills/custom/demo-skill/rollback", json={"history_index": -1})
        assert rollback_response.status_code == 400
        assert "unsafe rollback" in rollback_response.json()["detail"]

        history_response = client.get("/api/skills/custom/demo-skill/history")
        assert history_response.status_code == 200
        assert history_response.json()["history"][-1]["scanner"]["decision"] == "block"


def test_custom_skill_delete_preserves_history_and_allows_restore(monkeypatch, tmp_path):
    paths_instance, skills_root, custom_dir = _setup_skills_test(monkeypatch, tmp_path)
    original_content = _skill_content("demo-skill")
    monkeypatch.setattr("app.gateway.routers.skills.scan_skill_content", lambda *args, **kwargs: _async_scan("allow", "ok"))
    refresh_calls = []

    async def _refresh():
        refresh_calls.append("refresh")

    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _refresh)

    app = FastAPI()
    app.include_router(skills_router.router)
    app.dependency_overrides[get_current_user_id] = lambda: _TEST_USER_ID

    with TestClient(app) as client:
        delete_response = client.delete("/api/skills/custom/demo-skill")
        assert delete_response.status_code == 200
        assert not (custom_dir / "SKILL.md").exists()

        history_response = client.get("/api/skills/custom/demo-skill/history")
        assert history_response.status_code == 200
        assert history_response.json()["history"][-1]["action"] == "human_delete"

        rollback_response = client.post("/api/skills/custom/demo-skill/rollback", json={"history_index": -1})
        assert rollback_response.status_code == 200
        assert rollback_response.json()["description"] == "Demo skill"
        assert (custom_dir / "SKILL.md").read_text(encoding="utf-8") == original_content
        assert refresh_calls == ["refresh", "refresh"]


def test_update_skill_refreshes_prompt_cache_before_return(monkeypatch, tmp_path):
    from deerflow.config.paths import Paths

    paths_instance = Paths(base_dir=tmp_path)
    config_path = paths_instance.user_extensions_config_file(_TEST_USER_ID)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    enabled_state = {"value": True}
    refresh_calls = []

    def _load_skills(*, enabled_only: bool, user_id: str | None = None):
        skill = _make_skill("demo-skill", enabled=enabled_state["value"])
        if enabled_only and not skill.enabled:
            return []
        return [skill]

    async def _refresh():
        refresh_calls.append("refresh")
        enabled_state["value"] = False

    monkeypatch.setattr("app.gateway.routers.skills.load_skills", _load_skills)
    monkeypatch.setattr("deerflow.config.paths.get_paths", lambda: paths_instance)
    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _refresh)

    app = FastAPI()
    app.include_router(skills_router.router)
    app.dependency_overrides[get_current_user_id] = lambda: _TEST_USER_ID

    with TestClient(app) as client:
        response = client.put("/api/skills/demo-skill", json={"enabled": False})

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert refresh_calls == ["refresh"]
    assert json.loads(config_path.read_text(encoding="utf-8")) == {"skills": {"demo-skill": {"enabled": False}}}
