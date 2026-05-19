from deerflow.config.sandbox_config import SandboxConfig


def test_sandbox_config_accepts_resource_aliases():
    config = SandboxConfig(
        use="deerflow.community.aio_sandbox:AioSandboxProvider",
        resources={
            "requests": {
                "cpu": "100m",
                "memory": "256Mi",
                "ephemeral-storage": "500Mi",
            },
            "limits": {
                "cpu": "2",
                "memory": "4Gi",
                "ephemeral-storage": "10Gi",
            },
        },
    )

    assert config.resources is not None
    assert config.resources.requests is not None
    assert config.resources.requests.ephemeral_storage == "500Mi"
    assert config.resources.limits is not None
    assert config.resources.limits.ephemeral_storage == "10Gi"
    assert config.resources.model_dump(by_alias=True, exclude_none=True) == {
        "requests": {
            "cpu": "100m",
            "memory": "256Mi",
            "ephemeral-storage": "500Mi",
        },
        "limits": {
            "cpu": "2",
            "memory": "4Gi",
            "ephemeral-storage": "10Gi",
        },
    }
