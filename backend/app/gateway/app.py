import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.gateway.config import get_gateway_config
from app.gateway.csrf_middleware import get_configured_cors_origins
from app.gateway.deps import langgraph_runtime
from app.gateway.routers import (
    academic_data_search,
    agents,
    apps,
    artifacts,
    assistants_compat,
    auth,
    channels,
    mcp,
    memory,
    models,
    runs,
    sandbox,
    skills,
    suggestions,
    thread_runs,
    threads,
    upload_config,
    uploads,
)
from deerflow.config.app_config import apply_logging_level, get_app_config

# Default logging; lifespan overrides from config.yaml log_level.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# Upper bound (seconds) each lifespan shutdown hook is allowed to run.
# Bounds worker exit time so uvicorn's reload supervisor does not keep
# firing signals into a worker that is stuck waiting for shutdown cleanup.
_SHUTDOWN_HOOK_TIMEOUT_SECONDS = 5.0


# Interval between tool_cache vacuum sweeps. Postgres takes care of
# concurrency; running on every pod is safe (a single DELETE is cheap).
_TOOL_CACHE_VACUUM_INTERVAL_SECONDS = 60 * 60  # 1 hour


async def _run_tool_cache_vacuum_loop() -> None:
    """Background task that periodically deletes expired ``tool_cache`` rows."""
    from deerflow.community.semantic_scholar.postgres_cache import PostgresTTLCache

    # Small initial delay so we don't collide with schema setup on first boot.
    await asyncio.sleep(30)
    while True:
        try:
            await asyncio.to_thread(PostgresTTLCache.vacuum_expired)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("tool_cache vacuum sweep failed; will retry next interval")

        try:
            await asyncio.sleep(_TOOL_CACHE_VACUUM_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            return


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""

    # Load a startup snapshot for restart-required infrastructure. Request-time
    # config access must go through deps.get_config()/get_app_config() so edits
    # to config.yaml are picked up without restarting the gateway.
    try:
        startup_config = get_app_config()
        apply_logging_level(startup_config.log_level)
        logger.info("Configuration loaded successfully")
    except Exception as e:
        error_msg = f"Failed to load configuration during gateway startup: {e}"
        logger.exception(error_msg)
        raise RuntimeError(error_msg) from e
    config = get_gateway_config()
    logger.info(f"Starting API Gateway on {config.host}:{config.port}")

    if startup_config.memory.token_counting == "char":
        logger.info("memory.token_counting='char'; skipping tiktoken warm-up")
    else:
        try:
            from deerflow.agents.memory.prompt import warm_tiktoken_cache

            warmed = await asyncio.wait_for(
                asyncio.to_thread(warm_tiktoken_cache),
                timeout=_SHUTDOWN_HOOK_TIMEOUT_SECONDS,
            )
            if warmed:
                logger.info("tiktoken encoding cache warmed successfully")
            else:
                logger.warning(
                    "tiktoken encoding cache warm-up failed; token counting will use character-based fallback until tiktoken loads successfully"
                )
        except TimeoutError:
            logger.warning(
                "tiktoken encoding cache warm-up timed out; token counting will use character-based fallback until tiktoken loads successfully"
            )
        except Exception:
            logger.warning("tiktoken warm-up skipped", exc_info=True)

    # Initialize auth subsystem
    from app.gateway.auth.config import get_auth_config
    from app.gateway.auth.local_provider import LocalAuthProvider

    auth_config = get_auth_config()

    # Initialise the shared Postgres engine + application schema.
    # The engine defaults to POSTGRES_DSN, falling back to the checkpointer DSN.
    # We always stand it up (even when auth is on SQLite) so later migrations
    # (memory/cache/channels) can share it without re-wiring.
    from deerflow.db import (
        close_engine,
        close_pool,
        close_sync_engine,
        ensure_schema,
        init_engine,
        init_pool,
        init_sync_engine,
    )

    db_engine = None
    db_pool = None
    try:
        db_engine = await init_engine()
        # Sync engine shares the same DSN; used by repositories whose public
        # interface is synchronous (memory storage, tool cache, channel store).
        init_sync_engine()
        await ensure_schema(db_engine)
        # Legacy asyncpg pool is still used by a handful of call sites that
        # need a raw ``asyncpg.Pool`` object. Standing it up alongside the
        # engine keeps those paths working during the migration.
        db_pool = await init_pool()
        app.state.db_engine = db_engine
        app.state.db_pool = db_pool
        logger.info("Postgres engine + pool + application schema ready")
    except Exception:
        logger.exception(
            "Postgres initialisation failed; the gateway cannot serve auth, "
            "memory, tool cache, or channel-store requests without a working engine"
        )

    # Production path runs on the SQLModel + SQLAlchemy engine.
    # SQLiteUserRepository is still imported by the test suite but is no
    # longer reachable from the runtime configuration.
    from app.gateway.auth.repositories.postgres import PostgresUserRepository

    user_repo = PostgresUserRepository()
    logger.info("Auth subsystem initialised (JWT + Postgres)")

    auth_provider = LocalAuthProvider(user_repo)
    app.state.auth_config = auth_config
    app.state.auth_provider = auth_provider
    app.state.user_repo = user_repo

    # Cache provider at module level for deps.get_local_provider()
    from app.gateway.deps import set_local_provider
    set_local_provider(auth_provider)

    # Periodic vacuum for tool_cache — runs every hour while the app is up.
    # Only started when the Postgres pool is available; on the sqlite
    # fallback the per-cache DELETE-on-read path already evicts expired rows.
    tool_cache_vacuum_task: asyncio.Task | None = None
    if db_pool is not None:
        tool_cache_vacuum_task = asyncio.create_task(
            _run_tool_cache_vacuum_loop(), name="tool_cache_vacuum"
        )

    app.state.tool_cache_vacuum_task = tool_cache_vacuum_task

    # Initialize LangGraph runtime components (StreamBridge, RunManager, checkpointer, store)
    async with langgraph_runtime(app, startup_config):
        logger.info("LangGraph runtime initialised")

        # Start IM channel service if any channels are configured
        try:
            from app.channels.service import start_channel_service

            channel_service = await start_channel_service()
            logger.info("Channel service started: %s", channel_service.get_status())
        except Exception:
            logger.exception("No IM channels configured or channel service failed to start")

        yield

        # Stop channel service on shutdown (bounded to prevent worker hang)
        try:
            from app.channels.service import stop_channel_service

            await asyncio.wait_for(
                stop_channel_service(),
                timeout=_SHUTDOWN_HOOK_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            logger.warning(
                "Channel service shutdown exceeded %.1fs; proceeding with worker exit.",
                _SHUTDOWN_HOOK_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.exception("Failed to stop channel service")

    # Cancel the tool_cache vacuum loop on shutdown.
    vacuum_task = getattr(app.state, "tool_cache_vacuum_task", None)
    if vacuum_task is not None and not vacuum_task.done():
        vacuum_task.cancel()
        try:
            await asyncio.wait_for(vacuum_task, timeout=_SHUTDOWN_HOOK_TIMEOUT_SECONDS)
        except (TimeoutError, asyncio.CancelledError):
            pass
        except Exception:
            logger.exception("Failed to stop tool_cache vacuum task")

    # Close the Postgres engines + asyncpg pool on shutdown.
    try:
        await asyncio.wait_for(close_pool(), timeout=_SHUTDOWN_HOOK_TIMEOUT_SECONDS)
    except TimeoutError:
        logger.warning(
            "asyncpg pool shutdown exceeded %.1fs; proceeding with worker exit.",
            _SHUTDOWN_HOOK_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception("Failed to close asyncpg pool")

    # Sync engine dispose is synchronous but cheap; wrap so a stuck close
    # cannot block worker exit past the shared deadline.
    try:
        await asyncio.wait_for(
            asyncio.to_thread(close_sync_engine),
            timeout=_SHUTDOWN_HOOK_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning(
            "SQLAlchemy sync engine shutdown exceeded %.1fs; proceeding with worker exit.",
            _SHUTDOWN_HOOK_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception("Failed to close SQLAlchemy sync engine")

    try:
        await asyncio.wait_for(close_engine(), timeout=_SHUTDOWN_HOOK_TIMEOUT_SECONDS)
    except TimeoutError:
        logger.warning(
            "SQLAlchemy async engine shutdown exceeded %.1fs; proceeding with worker exit.",
            _SHUTDOWN_HOOK_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception("Failed to close SQLAlchemy async engine")

    logger.info("Shutting down API Gateway")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    config = get_gateway_config()
    docs_url = "/docs" if config.enable_docs else None
    redoc_url = "/redoc" if config.enable_docs else None
    openapi_url = "/openapi.json" if config.enable_docs else None

    app = FastAPI(
        title="Scientific Tumbleweed API Gateway",
        description="""
## Scientific Tumbleweed API Gateway

API Gateway for Scientific Tumbleweed - A LangGraph-based AI agent backend with sandbox execution capabilities.

### Features

- **Models Management**: Query and retrieve available AI models
- **MCP Configuration**: Manage Model Context Protocol (MCP) server configurations
- **Memory Management**: Access and manage global memory data for personalized conversations
- **Skills Management**: Query and manage skills and their enabled status
- **Artifacts**: Access thread artifacts and generated files
- **Health Monitoring**: System health check endpoints

### Architecture

LangGraph-compatible requests are routed through nginx to this gateway.
This gateway provides runtime endpoints for agent runs plus custom endpoints for models, MCP configuration, skills, and artifacts.
        """,
        version="0.1.0",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        openapi_tags=[
            {
                "name": "models",
                "description": "Operations for querying available AI models and their configurations",
            },
            {
                "name": "mcp",
                "description": "Manage Model Context Protocol (MCP) server configurations",
            },
            {
                "name": "memory",
                "description": "Access and manage global memory data for personalized conversations",
            },
            {
                "name": "skills",
                "description": "Manage skills and their configurations",
            },
            {
                "name": "artifacts",
                "description": "Access and download thread artifacts and generated files",
            },
            {
                "name": "uploads",
                "description": "Upload and manage user files for threads",
            },
            {
                "name": "threads",
                "description": "Manage Scientific Tumbleweed thread-local filesystem data",
            },
            {
                "name": "agents",
                "description": "Create and manage custom agents with per-agent config and prompts",
            },
            {
                "name": "apps",
                "description": "List modular workspace app definitions and serve workspace app APIs",
            },
            {
                "name": "suggestions",
                "description": "Generate follow-up question suggestions for conversations",
            },
            {
                "name": "channels",
                "description": "Manage IM channel integrations (Feishu, Slack, Telegram)",
            },
            {
                "name": "assistants-compat",
                "description": "LangGraph Platform-compatible assistants API (stub)",
            },
            {
                "name": "runs",
                "description": "LangGraph Platform-compatible runs lifecycle (create, stream, cancel)",
            },
            {
                "name": "health",
                "description": "Health check and system status endpoints",
            },
        ],
    )

    # CORS: the unified nginx endpoint is same-origin by default. Split-origin
    # browser clients must opt in with this explicit Gateway allowlist so CORS
    # and CSRF origin checks share the same source of truth.
    from fastapi.middleware.cors import CORSMiddleware

    cors_origins = sorted(get_configured_cors_origins())
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Auth & CSRF middleware (order matters: CSRF runs after auth)
    from app.gateway.auth_middleware import AuthMiddleware
    from app.gateway.csrf_middleware import CSRFMiddleware

    app.add_middleware(CSRFMiddleware)
    app.add_middleware(AuthMiddleware)
    # Include routers
    # Auth API is mounted at /api/v1/auth
    app.include_router(auth.router)

    # Models API is mounted at /api/models
    app.include_router(models.router)

    # MCP API is mounted at /api/mcp
    app.include_router(mcp.router)

    # Memory API is mounted at /api/memory
    app.include_router(memory.router)

    # Skills API is mounted at /api/skills
    app.include_router(skills.router)

    # Artifacts API is mounted at /api/threads/{thread_id}/artifacts
    app.include_router(artifacts.router)

    # Uploads API is mounted at /api/threads/{thread_id}/uploads
    app.include_router(uploads.router)

    # Upload configuration API is mounted at /api/uploads
    app.include_router(upload_config.router)

    # Thread cleanup API is mounted at /api/threads/{thread_id}
    app.include_router(threads.router)

    # Agents API is mounted at /api/agents
    app.include_router(agents.router)

    # Apps API is mounted at /api/apps
    app.include_router(apps.router)

    # Academic data search App API is mounted at /api/apps/research-data-search
    app.include_router(academic_data_search.router)

    # Suggestions API is mounted at /api/threads/{thread_id}/suggestions
    app.include_router(suggestions.router)

    # Channels API is mounted at /api/channels
    app.include_router(channels.router)

    # Sandbox API is mounted at /api/sandbox
    app.include_router(sandbox.router)

    # Assistants compatibility API (LangGraph Platform stub)
    app.include_router(assistants_compat.router)

    # Thread Runs API (LangGraph Platform-compatible runs lifecycle)
    app.include_router(thread_runs.router)

    # Stateless Runs API (stream/wait without a pre-existing thread)
    app.include_router(runs.router)

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        """Health check endpoint.

        Returns:
            Service health status information.
        """
        return {"status": "healthy", "service": "scientific-tumbleweed-gateway"}

    return app


# Create app instance for uvicorn
app = create_app()
