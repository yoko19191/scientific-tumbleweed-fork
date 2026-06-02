"""Shared helpers for agent module assembly."""


def call_with_optional_app_config(func, *args, app_config=None, **kwargs):
    if app_config is None:
        return func(*args, **kwargs)
    try:
        return func(*args, app_config=app_config, **kwargs)
    except TypeError as exc:
        if "app_config" not in str(exc):
            raise
        return func(*args, **kwargs)
