---
name: sync-upstream-fork
description: Safely synchronize a forked repository with its upstream remote while preserving local customization branches. Use when the user asks to sync upstream branches, update a fork from upstream, merge or rebase upstream changes, inspect origin/upstream remotes, or design a Git workflow for long-term secondary development on top of an upstream project.
---

# Sync Upstream Fork

Use this skill for fork-based repositories that need both:

- continuous upstream security or feature updates
- local secondary development with minimal merge pain

## Default stance

Prefer a conservative workflow:

- keep an upstream-tracking branch as clean as possible
- keep custom development on a separate long-lived branch
- prefer `merge` for long-lived branches
- use `rebase` only for short-lived private feature branches
- never use destructive Git commands unless the user explicitly asks

## Safety rules

Before proposing or running any sync command:

1. Check repository status:
   - `git status --short --branch`
   - `git remote -v`
   - `git branch -vv`
2. If the working tree is dirty, stop and ask the user how to proceed.
3. Never assume the remote names, but `origin` and `upstream` are the default expectation for a fork workflow.
4. Never run `git reset --hard`, force-push, or history-rewriting commands on shared branches unless the user explicitly requests that.
5. Do not modify Git config.

## Recommended branch model

Unless the repository already has a clearly better convention, recommend:

- `main`: upstream-tracking branch, kept close to `upstream/main`
- `custom/main` or `dev`: long-lived branch for local secondary development
- `feature/*`: short-lived implementation branches created from the custom branch

Do not insist on renaming existing stable branches if the user already has a working convention. Adapt the workflow to the current branch layout.

## Discovery workflow

When triggered, first identify the current shape of the repository:

1. Confirm remotes and infer fork topology.
2. Identify which branch tracks upstream updates.
3. Identify whether custom work is currently mixed into `main`.
4. Decide whether the user needs:
   - a one-time setup
   - a routine upstream sync
   - conflict resolution help
   - branch model redesign

Summarize the current state before suggesting commands.

## Standard workflows

### 1. One-time setup for a fork

If `upstream` does not exist, add it:

```bash
git remote add upstream <upstream-url>
git fetch upstream
```

If the project should use a dedicated custom branch:

```bash
git checkout main
git merge --ff-only upstream/main
git checkout -b custom/main
```

Only push new branches or updated refs when the user explicitly asks.

### 2. Routine upstream synchronization

First update the clean tracking branch:

```bash
git fetch upstream --prune
git checkout main
git merge --ff-only upstream/main
```

Then bring upstream changes into the custom branch:

```bash
git checkout custom/main
git merge main
```

If the repository uses another long-lived custom branch name such as `dev` or `my-main`, adapt the commands instead of forcing `custom/main`.

### 3. Feature development

Prefer this pattern:

```bash
git checkout custom/main
git checkout -b feature/<topic>
```

After work is complete:

```bash
git checkout custom/main
git merge feature/<topic>
```

### 4. Rebase policy

Recommend `rebase` only when all of these are true:

- the branch is short-lived
- it is private or not yet shared
- the user wants a cleaner linear history
- the branch is not the long-lived integration branch

Example safe use:

```bash
git checkout feature/<topic>
git rebase custom/main
```

Do not recommend rebasing `main`, `custom/main`, or another long-lived shared branch unless the user explicitly wants that tradeoff.

## Conflict handling

If upstream sync causes conflicts:

1. Identify the conflicting files.
2. Explain whether the conflict is caused by:
   - direct edits to upstream-owned code
   - overlapping changes in the same module
   - branch model drift
3. Resolve only the intended conflict.
4. Never discard unrelated local changes without explicit approval.
5. After resolution, summarize:
   - what came from upstream
   - what remained custom
   - what should be refactored later to reduce future conflicts

## Decision guidance

Use these defaults when advising the user:

- If the user wants long-term maintainability, recommend `main` plus a separate custom branch.
- If the user already committed custom logic directly on `main`, do not panic; first explain the current risk, then propose carving out a custom branch.
- If the user asks whether to use `merge` or `rebase`, recommend:
  - `merge` for long-lived branch synchronization
  - `rebase` for short-lived local cleanup

## Response checklist

When answering, keep the output practical:

1. State the current repository shape in one short paragraph.
2. Tell the user which workflow applies.
3. Give only the necessary commands, in order.
4. Call out any risk:
   - dirty worktree
   - custom code mixed into tracking branch
   - rebase on shared history
   - push requirements
5. End with the next safe action.

## Anti-patterns

Avoid recommending these as defaults:

- doing all custom development directly on `main`
- rebasing a long-lived shared branch every time upstream changes
- force-pushing synchronization branches
- hiding the distinction between upstream-owned code and custom-owned code
- giving generic Git advice without first checking remotes, branch layout, and worktree status
