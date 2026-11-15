---
name: git-flow
description: Branching and merge model — merge_tier picks queue or auto-merge; lanes route checks; develop integrates, main produces; atomic commits; Git Town starts and syncs branches by rebase
type: LLM Prompt
title: "Git flow"
resource: "prompt://dryvist/auto-ai-agent/instructions/agentsmd/rules/on-demand/git-flow"
tags:
  - shared-instructions
  - agent-instructions
timestamp: "2026-11-15T07:15:00Z"
status: active
consumers:
  - dryvist/nix-ai
  - dryvist/nix-claude-code
render: { engine: literal, variables: [], frontmatter: strip }
source_history:
  - repository: dryvist/ai-assistant-instructions
    path: "agentsmd/rules/on-demand/git-flow.md"
    note: Migrated from the instruction repository.
---

# Git flow

Repos use the git-flow branch model. [Git Town](https://www.git-town.com) starts, syncs and proposes branches.
It is installed and configured globally: nix-managed git config, rebase sync, `main` and `develop` perennial.

## Detect adoption first

Before any branch, PR, or release work, detect the repo's remote default branch
(`gh repo view --json defaultBranchRef --jq .defaultBranchRef.name` or `git remote show origin`).

- Default branch `develop` → the repo is on git-flow; follow this file.
- Default branch `main` → trunk flow; squash-merge into `main`. Do not create a `develop` branch yourself.
- Never infer adoption from the current local branch name.

## The model

| Branch | Role | Gets changes by |
| --- | --- | --- |
| `main` | Production. Protected; no direct pushes. | Merge commits only; squash and rebase into `main` are banned |
| `develop` | Default integration branch. Protected; no direct pushes. | Squash-merged PRs; a merge commit only for a hotfix PR |
| `<type>/*` | One change's work; `<type>` is its Conventional Commits type, never `feature` | Branched from fresh `develop` |
| `hotfix/<name>` | Urgent production fix | From `main`; PR to `main`, merge commit; then PR from the hotfix branch to `develop`, merge commit |
| `topic/<name>` | Shared work branch for several agents | Direct pushes; force pushes blocked; one thin PR lands it |
| `promote/<yyyy-mm-dd>` | Daily promotion | Cut at the head of `green`; PR to `main`, merge commit |

The Main Source Gate allows only `develop`, same-repo `hotfix/<name>`, and `promote/<yyyy-mm-dd>` into `main`.
It blocks every other source branch. A promotion head must be a commit contained in the default branch.

`main` is never merged back into `develop`. Stabilization fixes land on `develop` through ordinary PRs.
Never merge to `main` without intending a release.

## Merge tier

`merge_tier` is a custom property on the repo, set from `repos.yml` in the infrastructure code.
It is the only switch. Rulesets and workflows both read it, so they can never disagree.

| Value | Meaning |
| --- | --- |
| `hot` | Merge queue on the default branch. Heavy checks run only in the queue. |
| `standard` | No queue. Heavy checks run on the PR. Lanes and native auto-merge apply. |
| `legacy` | A rollout device only. |

Rollback is the same switch: set the repo back to `standard` and apply.
The queue ruleset goes away and heavy checks return to the PR in the same step.

The queue uses `ALLGREEN`, build 5, merge 5, minimum 1, wait 0, timeout 30 minutes.
`HEADGREEN` is forbidden: a fast entry could carry a failed heavy entry in.

## Lanes

One classifier decides the lane from the PR itself: its files, size, labels and author.
It runs on the PR and again in the queue, so a label added late is read at build time.

| Lane | Who gets it | Before merge | After merge |
| --- | --- | --- | --- |
| Tiny | 10 changed lines or fewer, every file low-risk | Fast checks | Deferred heavy checks and verdict |
| Land-first | Label `land-first`, no guarded path | Fast checks | Deferred heavy checks and verdict |
| Normal | Everything else | Fast checks, verdict, heavy checks for the changed paths | Nothing |
| Guarded | Secrets, secret-store policy, rulesets, workflow files | Fast checks, verdict, full suite | Nothing |
| Bot | Renovate, release-please, auto-revert PRs | Checks for the changed files; no verdict | Nothing |

- Fast checks take under 2 minutes: secret scan, disclosure scan, lint, PR title and policy.
  The secret and disclosure scans always run first, in every lane. A leak cannot be reverted.
- Instruction files (rules, prompts, skills, agent files) are never low-risk, even though they are markdown.
- A PR from a sandbox executor or a fork never gets the tiny or land-first lane.
  The classifier reads the author identity, not the PR text.
- Comment-only edits inside code files are not detected automatically. They use the `land-first` label.
- The gate marks a tiny or land-first PR `checks:deferred`. See `review-gate.md` for the verdict.

## Merge flow

- Hot repo, normal lane: open a ready PR. The platform arms native auto-merge.
  The PR runs fast checks and gets its verdict. GitHub then adds it to the queue.
  The queue runs the heavy checks once on the merged result and merges by squash.
- Hot repo, fast lanes: same path, but the queue run is the fast checks only.
  A fast entry still waits for the entries ahead of it, at most one heavy cycle (about 10 minutes).
- Standard repo: same lanes. Heavy checks run on the PR. Native auto-merge merges it.
- Nothing is rebased by hand. Do not run base-branch refresh commands.
- The platform arms auto-merge. Agents never disarm it. The only merge command an agent may run is
  `gh pr merge <number> --auto`, and only to re-arm a PR that lost its auto-merge.
- Open every PR ready for review. A ready PR merges by itself, so hold nothing in draft state.
- Agents answer failed checks and CHANGES verdicts. See `ci-resilience.md` and `review-gate.md`.
- `human:review` is the only hold. Agents and executors never add it.

## The green pointer

A fast-lane merge leaves two debts: its heavy checks and its review.
On every push to the default branch, one workflow settles the debts:

1. No deferred PR between `green` and the new head: fast-forward `green` at once (seconds).
2. Otherwise run the heavy checks mapped to everything changed since `green`, on the new head.
   Check that each deferred PR has a MERGE verdict.
3. All pass: fast-forward `green`.
4. Red: post at once, start the CI-fix agent, and start a 15-minute timer
   (a GitHub environment wait timer, no runner held). If the branch is still red, `gh pr revert` opens
   the revert PR and it lands through the bot lane. A CHANGES verdict skips the timer.

`green` only moves forward, and only the automation App can move it.
The converge train, the pin bumps and the daily promotion all read `green`.
A red default branch never deploys and never spreads.

## Topic branches and cross-repo work

- Several agents push to one `topic/<name>` branch. Each rebases only its own unpushed commits.
  A ruleset blocks force pushes on `topic/**`. Each push runs the fast checks.
- One thin PR lands the topic. Open no PR before the topic is complete.
- A cross-repo topic uses the same branch name in each repo. Consumer CI tests against the upstream topic
  branch through native overrides: Nix `--override-input`, an OpenTofu module source variable,
  a Galaxy requirements override. Never commit overrides.
- Upstream lands first. The consumer PR bumps its own pin to the landed commit and then lands.
- Each landing must be safe to deploy alone. Nothing makes two repos merge atomically.

## Pins

- First-party pins are commit pins on the upstream `green` branch.
- Renovate refreshes one grouped PR per consumer every 4 hours, on an odd minute,
  with native auto-merge and no release-age hold.
- A PR that needs an upstream change now bumps the pin itself.
- Release tags stay for outside users.

## Promotion and releases

Promotion is automatic, git-flow repos only. Every day, on an odd minute:

1. Stop if `main` carries content that the default branch lacks (an unported hotfix). Post at once.
2. Start the full suite on the head of `green`.
3. Green: create `promote/<yyyy-mm-dd>` at that exact commit, open the PR to `main`, merge by merge commit.
   The promotion PR runs light checks and verifies the full-suite result for its head commit.
4. Red: no promotion that day. Post at once and start the CI-fix agent.

release-please keeps one release PR open against the default branch with the version bump and CHANGELOG.
It lands through the bot lane. The push to `main` tags and releases that commit.
Later commits take the next version. The release moves this repo's `vN` tag.
A new major (`vN+1`) is human-only: see `operating-core.md`.

## Working a change

1. Create or switch to a fresh worktree based on `origin/develop`. Place it at the repo's top level as
   `.worktrees/<name>/`, beside the primary checkout, never nested inside it. Pass `git worktree add` an
   absolute destination path so the current directory cannot change where it lands, e.g.
   `git worktree add "$(dirname "$(git rev-parse --git-common-dir)")/.worktrees/<name>" origin/develop`.
   A relative `.worktrees/<name>` resolves against your cwd; from inside the `main/` checkout it nests as
   `main/.worktrees/<name>`, which is wrong. `git rev-parse --show-toplevel` does not fix this: run from
   inside `main/` it returns `main/`'s own root, not the outer repo root. `--git-common-dir` is the anchor
   that stays stable across every worktree. Create `.worktrees/` if absent; keep it gitignored.
   The repo root checkout always stays on the default branch (`develop`, or `main` on trunk repos).
   Never check a feature branch out at the root.
2. Start the feature branch there with `git town hack <name>`, or let the harness worktree create it.
   Git Town fetches first and bases the branch on the fresh tip of `git-town.main-branch` (`develop` here).
   Pass the full name, `<type>/<issue>-<sid8>-<slug>` (session id: session-coordination rule),
   e.g. `git town hack fix/123-03a3a401-inventory-loader`; the worktree dir is the part after `/`.
   Names are thus unique per session. Never invent an issue number; without one, drop that segment.
   Never commit to or push another session's branch, except a shared `topic/<name>` branch.
3. Commit atomically: one fix, one feature, or one coherent section of updates per commit, never a grab-bag.
   Follow Conventional Commits. Sign every commit. Reference the issue (`#123`) in the commit or PR;
   use closing keywords (`fixes #123`) when the change closes it.
4. Open the PR against `develop`, ready for review. The platform arms native auto-merge and merges it.
   Ordinary PRs merge by squash. A merge commit into `develop` is only for a hotfix PR.
5. Hotfix exception to PR targeting: a `hotfix/<name>` branch starts from `main` and its PR targets `main`
   (merge commit, never squash). Afterward open a PR from the hotfix branch (not `main`) to `develop`;
   it merges with a merge commit.
6. Every change to `develop` goes through a PR. The org ruleset enforces it, so a direct push is rejected
   (`GH013: Repository rule violations`). Never plan a quick direct commit to `develop`; branch and open a PR.

## Bot-owned files in rebases and merges

release-please owns `CHANGELOG.md` and its manifest files. When a rebase or merge onto `develop` conflicts
on a bot-owned file, always take the incoming `develop` side (`git checkout --theirs <file>` during rebase).
Never hand-merge bot content, and never add a `merge=ours` gitattribute for it
(that silently discards release history). Squash your own commits into one before rebasing across bot
commits to cut the conflict surface.

## CI and automation on git-flow repos

- Required checks and their events: see `ci-resilience.md`. Release, tag, and production deploy workflows
  stay on `main`.
- Renovate dependency PRs target `develop` (the default branch). Do not add a repo-level `baseBranches`
  forcing `main`.

## Git Town usage

- Start: `git town hack <name>`. Never branch from a local `main` or `develop`; the agent hooks deny
  `checkout -b`, `switch -c` and a worktree add whose start point is not `origin/…`.
- Sync: `git town sync` rebases unpushed commits onto the fresh parent. Run it only before the first push.
  A pushed PR branch is never synced: the queue tests the merged result.
  Never merge the base into a PR branch: a merge commit fails the org's Conventional Commit ruleset.
- Propose: `git town propose` opens the PR against the parent.
- Hotfix: `git worktree add --no-track -b hotfix/<name> <abs-path> origin/main`.
- Per-repo config: a git-flow repo sets `git-town.main-branch=develop` (or commits `.git-branches.toml`);
  everything else comes from the global config.
- Never force-push. Never edit a default branch directly.
- No agent runs `git town undo`. Recovery is by hand: read the status and the reflog, then fix the one ref.
