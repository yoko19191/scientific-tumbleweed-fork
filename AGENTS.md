# Repository Guidelines

## Project Structure & Module Organization

Scientific Tumbleweed is a full-stack agent harness. Root `Makefile` targets coordinate the app. Backend code lives in `backend/`: `app/` contains the FastAPI gateway and channel integrations, `packages/harness/deerflow/` contains the reusable LangGraph agent framework, and `tests/` contains pytest coverage. Frontend code lives in `frontend/src/`: `app/` for Next.js routes, `components/` for UI, `core/` for domain logic, plus `hooks/`, `lib/`, and `styles/`. Agent skills are committed under `skills/public/`; local custom skills belong in `skills/custom/`. Docker and nginx assets live under `docker/`; broader docs and plans live under `docs/`.

## Build, Test, and Development Commands

- `make setup`: run the setup wizard and generate local config.
- `make doctor`: validate configuration and required services.
- `make install`: install backend dependencies with `uv` and frontend dependencies with `pnpm`.
- `make dev`: start LangGraph, Gateway, Frontend, and nginx for local development.
- `make docker-start`: start the Docker development stack on `localhost:2026`.
- `cd backend && make test`: run backend pytest tests.
- `cd frontend && pnpm check`: run frontend linting and TypeScript checks.
- `cd frontend && BETTER_AUTH_SECRET=local-dev-secret pnpm build`: verify the production frontend build.

## Coding Style & Naming Conventions

Backend Python targets Python 3.12, uses `ruff`, double quotes, space indentation, and first-party imports from `deerflow` or `app`. Preserve the harness/app boundary: `app.*` may import `deerflow.*`, but `deerflow.*` must not import `app.*`. Frontend TypeScript uses ESLint, Prettier, and the Tailwind Prettier plugin. Prefer PascalCase for React components, camelCase for functions, and domain modules under `frontend/src/core/<domain>/`.

## Testing Guidelines

Backend tests are pytest files named `test_*.py` under `backend/tests/`; add focused regression tests for changed behavior and run specific files with `PYTHONPATH=. uv run pytest tests/test_<feature>.py -v`. Frontend tests under `frontend/tests/` follow Vitest-style `*.test.ts` naming; run `pnpm check` and a production build before submitting UI changes.

## Commit & Pull Request Guidelines

Recent history follows Conventional Commit prefixes such as `feat(scope): ...`, `fix(scope): ...`, `test(scope): ...`, and `refactor(scope): ...`. Keep commits scoped and include tests or docs when behavior changes. PRs should explain what changed, why it changed, how it was implemented, and how it was tested; include screenshots for visible UI changes and link related issues when available.

## Agent-Specific Instructions

Read scoped guides before editing: `backend/AGENTS.md` delegates backend architecture rules to `backend/CLAUDE.md`, and `frontend/AGENTS.md` documents frontend agent architecture. Do not commit generated local state such as `.env`, `config.yaml`, `backend/.deer-flow/`, `.next/`, `node_modules/`, or local agent files.
