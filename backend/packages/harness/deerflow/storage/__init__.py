"""Object-storage abstraction backed by OpenDAL.

All persistent file IO in the gateway goes through one of the operators
returned here — :func:`get_operator` (sync) or :func:`get_async_operator`
(async). Backends are selected by :mod:`deerflow.config.storage_config`
and default to a local-filesystem store so development works without
extra setup.

Callers should prefer the key builders in :mod:`deerflow.storage.paths`
over hand-formatted strings so future layout changes (tenant prefixes,
alternative namespaces) stay local to one file.
"""

from deerflow.storage.factory import (
    describe_operator,
    get_async_operator,
    get_operator,
    reset_operators,
)
from deerflow.storage.paths import (
    GLOBAL_SCOPE,
    outputs_key,
    outputs_prefix,
    uploads_key,
    uploads_prefix,
    user_agent_config_key,
    user_agent_prefix,
    user_agent_soul_key,
    user_agents_prefix,
    user_extensions_override_key,
    user_profile_key,
    workspace_key,
    workspace_prefix,
)

__all__ = [
    "GLOBAL_SCOPE",
    "describe_operator",
    "get_async_operator",
    "get_operator",
    "outputs_key",
    "outputs_prefix",
    "reset_operators",
    "uploads_key",
    "uploads_prefix",
    "user_agent_config_key",
    "user_agent_prefix",
    "user_agent_soul_key",
    "user_agents_prefix",
    "user_extensions_override_key",
    "user_profile_key",
    "workspace_key",
    "workspace_prefix",
]
