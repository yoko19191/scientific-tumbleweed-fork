---
name: merge-from-sources
description: Plan demand-driven synchronization from DeerFlow upstream/main and AntFlow into this repository's customized main branch. Use when the user wants to decide which new DeerFlow or AntFlow features/fixes should be brought into main, compare source/deerflow or source/antflow with main, account for docs/merge history and manual ports, estimate conflict risk, or prepare a /prd prompt for Ralph Loop to implement the selected sync.
---

# Merge From Sources

Use this skill for this repository's two-source customization workflow:

- `main` is the customized product branch.
- `source/deerflow` is the clean DeerFlow source line, tracking `upstream/main` from `bytedance/deer-flow`.
- `source/antflow` is the clean AntFlow source line, tracking `antflow/main`.
- The user wants to selectively bring new DeerFlow or AntFlow features, fixes, architecture changes, or security updates into `main`.
- Ralph Loop may perform the final implementation after a PRD is prepared.

This skill is not a generic "keep my fork up to date" workflow. Its job is to help decide what to synchronize from DeerFlow and AntFlow according to the customized product's needs, then produce a precise plan or `/prd` prompt.

## Default stance

Prefer planning before merging:

- Reply in the same language the user used for the merge request, including discussion, recommendations, and the `/prd` trigger text unless the user asks otherwise.
- Inspect first, discuss second, merge later.
- Treat `source/*` as read-only source references.
- Treat `source/deerflow` and `source/antflow` as independent sources with different roles; DeerFlow is usually the primary upstream baseline, while AntFlow may be a feature or architecture source.
- Treat remote-tracking refs as the freshness authority: DeerFlow is `upstream/main`; AntFlow is `antflow/main`. Local `source/*` branches are convenient mirrors and may be stale.
- Keep `main` as the customized product line.
- Use merge commits for long-lived integration work.
- Do not rebase `main` or `source/*`.
- Do not execute the final merge unless the user explicitly asks for direct execution.
- When the user intends to use Ralph Loop, produce a clear `/prd` trigger text instead of doing the merge manually.
- Do not treat commit order, ahead/behind counts, or missing SHAs as the full truth. Manual ports can make code present in `main` even when the original source commits are absent.
- Avoid saying the customized branch is "before" or "after" a source branch. Use precise terms: "main-only commits", "source-only commits", "local source mirror is stale", "remote source has new commits", or "code behavior already exists in main".

## Global merge strategy

Default classification when deciding how to apply upstream changes into `main` (applies to DeerFlow and AntFlow unless the user overrides):

- **安全修复 / bug fix** → 直接应用（apply as-is).
- **新功能（不与 custom 冲突）** → 直接应用（apply as-is).
- **新功能（与 custom 冲突）** → 保留 custom 逻辑，叠加上游新功能（preserve local customization; integrate upstream additions without dropping custom behavior).
- **品牌 / Landing Page** → 永不修改（do not take upstream changes that alter branding or landing pages).
- **跳过** — Blog 结构 (`7dc0c7d0`)、文档站内容 (`c1366cf5`)：默认不同步这些变更（skip unless the user explicitly requests otherwise).

When recommending sync scope, align candidate commits and file paths with this strategy and call out any exception the user must confirm.

## Safety rules

Before proposing a merge plan:

1. Check repository state:
   - `git status --short --branch`
   - `git remote -v`
   - `git branch -vv`
2. If the working tree is dirty, explain the dirty files and ask whether to continue with read-only analysis or pause.
3. Identify available source branches:
   - `git branch --list 'source/*'`
   - `git branch -r`
4. Refresh or check freshness of source refs:
   - If the user asks for latest source changes, run `git fetch upstream --prune` and `git fetch antflow --prune` when network access is available.
   - If fetch cannot be run, state that analysis is based on the last fetched refs and include the latest reflog timestamp.
   - Check whether local source mirrors are stale:
     - `git rev-list --left-right --count source/deerflow...upstream/main`
     - `git rev-list --left-right --count source/antflow...antflow/main`
   - If a local source mirror is behind its remote-tracking ref, analyze against the remote-tracking ref or explicitly fast-forward the mirror only after the user agrees.
5. Read previous merge notes when present:
   - `find docs/merge -type f -print`
   - summarize relevant files instead of loading unrelated history in full.
6. Never run `git reset --hard`, force-push, or rewrite shared history unless the user explicitly requests it.

## Branch model

Expected model:

```text
main
  Customized product branch.

source/deerflow
  Clean DeerFlow source branch, usually tracking upstream/main.

source/antflow
  Clean AntFlow source branch, usually tracking antflow/main.

feature/*
  Short-lived implementation branches from main.

experiment/*
  Disposable exploration branches.

archive/*
  Historical preservation branches.
```

Adapt names if the repository already uses a clearly equivalent convention.

## Source refs

Use these refs unless the user specifies otherwise:

```text
DeerFlow source branch: source/deerflow
DeerFlow freshness ref: upstream/main

AntFlow source branch: source/antflow
AntFlow freshness ref: antflow/main
```

When the local source branch and freshness ref differ, prefer the freshness ref for analysis:

```bash
git rev-list --left-right --count source/deerflow...upstream/main
git rev-list --left-right --count source/antflow...antflow/main
```

Interpret the two numbers as:

```text
<local-source-only-count> <remote-source-only-count>
```

If the second number is greater than zero, the local `source/*` mirror is stale. Do not say `main` is ahead of upstream just because `source/*` lacks those commits.

## Workflow

### 1. Select the current source ref

Before discovery, decide which ref represents the source:

- Use `upstream/main` for latest DeerFlow analysis.
- Use `antflow/main` for latest AntFlow analysis.
- Use `source/deerflow` or `source/antflow` only when they are confirmed equal to the remote-tracking ref or when the user explicitly wants the local mirror state.

Name this ref in the response as `source ref`.

### 2. Discover source candidates as hints

For each relevant source ref, inspect commits that are present in the source ref but not in `main`:

```bash
git log --oneline --decorate main..<source-ref>
git diff --stat main..<source-ref>
git diff --name-only main..<source-ref>
git cherry -v main <source-ref>
```

If the list is large, group commits by subsystem or theme. Do not assume all commits should be merged. Do not assume a commit is missing only because its SHA is absent from `main`.

Also inspect whether `main` has customized commits that are absent from the source branch:

```bash
git log --oneline <source-ref>..main
```

This helps distinguish source changes from local product changes.

### 3. Read historical merge context

Review `docs/merge/*` before making a recommendation. This is mandatory because prior sync work may have been done by manual porting, cherry-pick, or partial implementation instead of a clean merge commit.

Look for:

- source branches previously merged
- commit ranges or features already manually ported
- files or subsystems already reconciled
- repeated conflict areas
- customization decisions that should be preserved
- files that have historically required manual reconciliation
- incomplete or risky prior merges

Summarize only the history relevant to the current source branch or touched files.

### 4. Compare actual code implementation

Before saying a source feature is missing, compare the actual implementation in `main` with the source branch.

Use source candidate commits and `docs/merge/*` notes to identify affected files, then inspect code-level differences:

```bash
git diff --stat main..<source-ref>
git diff --name-only main..<source-ref>
git diff main..<source-ref> -- <path>
git log --all --oneline -- <path>
```

For likely manual ports, inspect whether the behavior already exists in `main` even if the source commit does not:

```bash
git grep -n "<symbol-or-keyword>" main -- <path>
git grep -n "<symbol-or-keyword>" <source-ref> -- <path>
git show <source-ref>:<path>
git show main:<path>
```

Classify each candidate feature using three evidence channels:

- History evidence: source commits, patch-equivalent commits from `git cherry`, and local commits.
- Merge-note evidence: relevant `docs/merge/*.md` decisions, manual ports, conflicts, and follow-ups.
- Code evidence: current implementation differences between `main` and `source/*`.

Use one of these statuses:

- Already integrated: code behavior is present in `main`, even if the original source commit is absent.
- Partially integrated: some files or behaviors exist, but source branch has additional behavior or cleanup.
- Missing: the behavior is not present in `main`.
- Conflicting: both branches implement related behavior differently.
- Unclear: more inspection or user context is needed.

### 5. Discuss what to sync

Before conflict analysis becomes too detailed, present a concise choice set:

- source branch candidates
- source ref freshness, including whether `source/*` is stale relative to its remote-tracking ref
- notable ahead commits or feature groups
- whether each group appears already integrated, partially integrated, missing, conflicting, or unclear
- files or subsystems affected
- likely value of each group
- obvious risks or overlap with customized code

Ask the user which feature group, commit range, or source branch they want to integrate.

### 6. Estimate merge conflict risk

After the user chooses a target source/range, estimate conflicts without changing the worktree.

Useful commands:

```bash
git merge-base main <source-ref>
git diff --name-only $(git merge-base main <source-ref>)..main
git diff --name-only $(git merge-base main <source-ref>)..<source-ref>
git merge-tree $(git merge-base main <source-ref>) main <source-ref>
```

If command substitution is inconvenient, run `git merge-base` first and paste the SHA into the later commands.

Classify risk:

- Low: mostly additive changes; little or no overlap with customized files.
- Medium: overlapping files, but changes are in different functions or modules.
- High: same files and same logic areas changed, migration/config/auth/runtime behavior touched, or previous `docs/merge` notes flagged the area.

When overlaps exist, show the relevant files and summarize the nature of overlap. Compare code behavior, not only commit history. Avoid dumping huge diffs; use focused hunks only when needed.

### 7. Recommend an integration strategy

Recommend one of:

- Merge the source branch/range into a temporary feature branch from `main`.
- Cherry-pick specific commits when the desired work is isolated.
- Recreate the behavior manually when source history is noisy or conflicts are high.
- Mark as already integrated when code and merge notes show the behavior is already present.
- Only port the missing delta when a feature is partially integrated.
- Defer the merge when the value is unclear or conflicts are likely to interrupt current work.

For Ralph Loop workflows, prefer a temporary implementation branch:

```text
feature/merge-<source>-<topic>
```

The final merge target remains `main`.

### 8. Produce a /prd trigger text

After the user confirms the desired sync scope, produce a copy-ready `/prd` prompt.

The prompt must include:

- goal
- source branch
- target branch
- selected commits or feature groups
- integration status from history, merge notes, and code evidence
- files/subsystems likely affected
- conflict risk and expected manual decisions
- constraints to preserve local customization
- references to relevant `docs/merge/*` history
- acceptance criteria
- required merge documentation under `docs/merge/`

Template:

```text
/prd
Create a merge plan and implementation task for integrating selected changes from <source-branch> into main.

Goal:
- <what the user wants to bring into the customized product branch>

Source:
- Branch: <source-branch>
- Source ref used for analysis: <upstream/main | antflow/main | source/...>
- Source freshness: <whether source/* matched or lagged behind its remote-tracking ref>
- Commit range or selected commits: <range-or-list>
- Feature groups: <groups>

Evidence reviewed:
- Commit/patch history: <what commits or patch-equivalent changes were inspected>
- Merge history docs: <docs/merge paths and relevant decisions>
- Code comparison: <paths/symbols inspected and current integration status>

Target:
- Branch: main
- Implementation branch: feature/merge-<source>-<topic>

Context:
- main is the customized product branch.
- source/* branches are read-only source references.
- Commit history is not the only source of truth because prior work may have been manually ported.
- Preserve existing local customizations unless explicitly called out below.
- Review these merge history notes before implementing: <docs/merge paths>.

Expected conflict areas:
- <files/subsystems and risk level>

Implementation requirements:
- Merge, cherry-pick, or manually port only the confirmed scope.
- Do not re-implement behavior already present in main.
- For partially integrated features, port only the missing delta.
- Keep unrelated source changes out of the implementation.
- Preserve local behavior for <custom features>.
- Update tests or add focused tests for affected behavior.
- After completion, write docs/merge/YYYY-MM-DD_<source>_into_main.md with commit range, conflicts, resolution decisions, and follow-up notes.

Acceptance criteria:
- <observable behavior>
- Existing customized flows still work.
- Relevant tests pass.
- Merge documentation is complete.
```

## Merge documentation

When an actual merge, cherry-pick series, or manual port from `source/*` into `main` completes, create a document under `docs/merge/`.

File naming:

```text
docs/merge/YYYY-MM-DD_<source-branch>_into_main.md
```

Use `source-deerflow` or `source-antflow` in filenames instead of slashes.

Required content:

```markdown
# Merge: <source> into main

**Date**: YYYY-MM-DD HH:MM local time
**Source branch**: <source branch>
**Target branch**: main
**Implementation branch**: <branch or "none">
**Commit range**: <from>..<to> or selected commits
**Merge method**: merge / cherry-pick / manual port
**Merge commit**: <sha or "none">

## Commits or features integrated

| SHA | Author | Message | Included |
|-----|--------|---------|----------|

## Changes summary

## Customization decisions

## Conflicts encountered

## Tests run

## Follow-up notes
```

If the merge is deferred, aborted, or handed to Ralph Loop, document that status in the PRD prompt or final response. Do not create a merge document unless an actual integration attempt happened.

## Response checklist

When using this skill:

1. State the current branch model in one short paragraph.
2. Use the user's language for the whole interaction unless they ask otherwise.
3. State source ref freshness: fetched or stale, local source mirror versus remote-tracking ref.
4. Summarize source-only commits or feature groups as candidates, not facts of missing work.
5. Summarize relevant `docs/merge/*` history.
6. Summarize actual code comparison and classify already integrated / partially integrated / missing / conflicting / unclear.
7. Ask or confirm what the user wants to sync.
8. Provide conflict-risk judgment and recommendation.
9. Provide the copy-ready `/prd` trigger text.
10. End with the next safe action.
11. Align recommendations with **Global merge strategy** (security/bug, non-conflicting features, conflicting features + preserve custom, brand/landing, skip list).

## Anti-patterns

Avoid:

- directly merging all of `source/*` into `main` without selection
- treating `source/*` as development branches
- rebasing long-lived source or product branches
- deciding sync scope only from commit SHAs, ahead counts, or chronological order
- analyzing latest upstream changes from stale local `source/*` branches when `upstream/main` or `antflow/main` has moved
- using "before" or "after" language for divergent histories
- ignoring `docs/merge/*` history
- missing manually ported code that already exists in `main`
- generating a vague PRD prompt that leaves Ralph Loop to rediscover obvious constraints
- deleting or overwriting local customization to make a source merge easier
- ignoring **Global merge strategy** (for example merging brand/Landing Page changes, or Blog/docs skip areas, without explicit user approval)
