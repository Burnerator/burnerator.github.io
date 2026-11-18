---
title: Does graphify save tokens? 280 sessions with Claude Code and Codex
date: 2026-11-18
summary: A knowledge-graph tool promises AI coding agents will read less and spend less. We used the instructions and hooks its official installer writes, ran 280 sessions with Claude Code and Codex, and every graphify setup had a higher token volume for Claude.
tags: experiment, graphify, claude-code, codex, tokens
mascot_says: I gave both apprentices a map of the forge. They read the map, then walked the corridors anyway.
---

**Short version:** we gave Claude Code and Codex [graphify](https://github.com/Graphify-Labs/graphify) with the exact instruction text its own installer writes, plus, for Claude only, graphify's hooks and its strict mode (which our harness switched on). Codex kept the installer's hook file, which does nothing. Two things we changed on purpose: Claude's hooks ran through a small logger, and in the second run a bare `graphify` command went through a safe wrapper (details below). Then we asked them to explain and review real code. **For Claude Code, every graphify setup had a higher median token volume than no graphify: +12% to +63% per session** (+6% to +55% if we compare only with the no-graphify sessions of the same day). For Codex the observed medians were roughly unchanged: −11% to +9% with the official text, depending on the baseline. Answer coverage moved by a few points in most cells. These are the volumes we observed with the design described below, not a proof of why.

## What graphify promises

graphify turns a repository into a knowledge graph (`graphify-out/graph.json` plus a report). Its installer adds instructions telling the agent to ask the graph first (`graphify query "..."`) instead of grepping and reading files. For Claude Code it can also add **hooks** that nudge the agent towards the graph when it searches (Bash, Grep) or reads (Read, Glob). A **strict mode** goes further: the first *eligible* raw `Read` or `Grep` is denied once, as a nudge, when there has been no recent graph retrieval, and reissuing it is allowed. "Recent" is a timestamp shared by the whole checkout and fresh for 30 minutes, and our harness reused each strict checkout across repetitions, so an earlier session's query could suppress a later session's denial. The block fires at most once per session. In our runs one session logged a denial; that agent then read the same file with `Read` instead of reissuing the `Grep`.

The "80% fewer tokens" headline in graphify's README is about **[Graphify Cloud](https://github.com/Graphify-Labs/graphify#graphify-cloud)**, a hosted product. We tested the **open-source package** (`graphifyy` 0.9.111). Its README benchmark measures retrieval quality ([BENCHMARKS.md](https://github.com/Graphify-Labs/graphify/blob/v8/BENCHMARKS.md)). Its docs also have a [`graphify benchmark`](https://docs.graphify.com/open-source/features/token-benchmark) command that *estimates* savings per query against reading the whole repository, and they call that ratio "a guide to scale, not a billing figure". We measured something else: what the agents actually consumed, end to end. So this article answers a narrower question: *does the open-source tool, set up the official way, lower the agents' token volume?*

## A correction first

This is our second run. In the first one, the "graph" condition used graphify's **generic** rules text, not the exact text that `graphify claude install` and `graphify codex install` write. That was a fair objection, so we did it again:

- **official texts:** the instruction files are now the installer's exact output, byte for byte;
- **hooks and strict:** added for Claude Code;
- **a code-review task:** graphify documents a [pull-request workflow](https://docs.graphify.com/open-source/features/pr-impact), so we added the review of 4 real pull requests.

The first run is kept in the data as `rules-generic`. For Claude, and for the pooled task A comparisons, its numbers point the same way as the new ones. For Codex on anvil they don't: against each day's own baseline, generic rules used 25% more tokens and official rules 11% fewer.

## How we tested it

- **Agents:**
  - Claude Code (`claude -p`, model alias `sonnet`);
  - Codex (`codex exec`, read-only sandbox, default model).
- **Codebases, pinned to exact commits:**
  - our own [anvil](https://github.com/Burnerator/anvil) (9 Python files, 1.1k lines);
  - [httpx 0.28.1](https://github.com/encode/httpx/tree/0.28.1) (60 files, 17.8k lines).
- **Task A, understand:** 8 architecture questions, for example *"Trace what happens when calling httpx.get()"*.
- **Task B, review:** "review the changes between this commit and HEAD" on 4 real merged httpx PRs:
  - [#3377](https://github.com/encode/httpx/pull/3377), lazy loading of `certifi` and `httpcore`;
  - [#2879](https://github.com/encode/httpx/pull/2879), the new `proxy` parameter;
  - [#3139](https://github.com/encode/httpx/pull/3139), zstd decoding;
  - [#3389](https://github.com/encode/httpx/pull/3389), moving helpers out of `_utils.py`.

  The graph is built on the PR's base commit, as graphify's PR guide says ("run `graphify update .` on the base branch first").
- **Conditions** (every one on identical checkouts):

  | Condition | What the agent gets |
  |---|---|
  | `base` | nothing extra |
  | `rules-official` | graph + the exact `CLAUDE.md` / `AGENTS.md` text from graphify's installer (Claude without hooks; Codex keeps the installer's no-op hook file) |
  | `hooks` (Claude) | as above + graphify's own PreToolUse and SessionStart hooks |
  | `strict` (Claude) | as above + `GRAPHIFY_HOOK_STRICT=1` |
  | `rules-generic` (first run) | graph + graphify's generic rules text |

- **Repetitions:** 3 per question × condition, except the no-graphify task A sessions of the second run: 1 per question, pooled with the 3 of the first run. Within each batch, the order of conditions alternated. In the second run, the no-graphify sessions ran as separate batches (see the limits).
- **Metrics:** tokens, tool calls and graphify commands come from each agent's own event stream; hook firings from our hook wrapper's logs; quality from the rubric applied to the final answer:
  - tokens: uncached input, cached input, cache writes and output;
  - tool calls;
  - every graphify retrieval command (`query`, `path`, `explain`, `section`), whether its shell command succeeded, and how much text it returned;
  - every firing of graphify's Claude hooks and its decision, from the logs of our hook wrapper.
- **Quality:** a rubric of 5–8 key points per question, each one checked to exist in the code. For the PR reviews, the rubric is derived mechanically from the diff, not from the graph: up to 3 changed files, up to 3 touched functions or classes, and up to 3 other files that mention the most of those names. It checks that the answer mentions them, not that it is correct.
- **Controls:** the instructions pointed the agents to an allowlist wrapper with no API keys and no LLM backend. In the second run a bare `graphify` resolved to it through the agents' `PATH`; in the first run the instructions named the wrapper explicitly and the agents kept our normal `PATH`. The real graphify binary stayed reachable by its full path, and the official installers ran in throwaway copies with a fake home directory. This is not a sandbox: both agents ran with our normal installation and global settings, which we did not change between conditions. The report lists exactly what was and wasn't enforced.

**280 sessions in total, all completed successfully.**

## Did the agents actually call graphify?

They did call it, according to the shell-level count below, which is what makes the result meaningful. That count can include a query that printed only a diagnostic (for example "No node matching"), or a pipeline whose last command succeeded.

| | Sessions with a detected graphify command that succeeded* | graphify output (median serialized characters per setup, over sessions with output†) | Hook firings per session (logged by our hook wrapper) |
|---|---|---|---|
| Claude, task A | 100% in every graphify setup | 6,700–14,500 characters | 4–6 (hooks / strict) |
| Claude, task B | 11/12 (official, hooks), 8/12 (strict) | 6,600–6,700 characters | 4–5 (hooks / strict) |
| Codex, task A | 100% | 6,600–10,000 characters | — |
| Codex, task B | 100% | 6,700 characters (5 of 12 sessions**) | — |
| Any agent, no graphify | 0 sessions | — | — |

*\* Detected heuristically by matching the shell command text; it counts as succeeded if the shell command exited 0 (Codex) or its tool result was not an error (Claude). Output is the tool result as recorded, so a `| head` pipeline is truncated. Output counts only commands that ran nothing but graphify (pipes into `head`/`tail`, `echo` separators, `which graphify` and the `if test -f graphify-out/graph.json` guard are accepted, so their few extra characters are included); commands mixed with other shell commands count as calls but not as output, which is why only 5 Codex review sessions have an output figure.\*\* The report has the per-setup table.*

*† The median counts only sessions with non-empty output from successful, graphify-only commands. Counting the other sessions as zero lowers some cells: for example, Claude strict on task B is 6,678 characters over 8 such sessions, and 3,985 over all 12.*

## Results

**Task B, reviewing real pull requests.** We followed the base-graph step of graphify's PR-review guide and used our own review prompt; graphify's `graphify prs` command was not part of the experiment. Medians over 12 sessions per cell:

| Agent | No graphify | Official rules | Hooks | Strict | Quality (mean coverage) |
|---|---|---|---|---|---|
| Claude Code | 168,940 | 230,981 (**+37%**) | 260,136 (**+54%**) | 236,453 (**+40%**) | 79% → 83–84% |
| Codex | 109,708 | 106,391 (**−3%**) | — | — | 68% → 71% |

*Total tokens per session (uncached input + cached input + cache writes + output, over all the models a session used). For Claude, the API-equivalent cost went from $0.11 to $0.14–0.15 per review. Both rows compare same-day batches; task B has no alternative-baseline check (the tool-count check below covers it).*

**Task A, explaining code**, median total tokens per session. The base pools both runs: 12 sessions on anvil, 20 on httpx.

| Agent | Codebase | No graphify | Generic rules | Official rules | Hooks | Strict |
|---|---|---|---|---|---|---|
| Claude Code | anvil | 186,602 | +19% | +33% | +23% | +22% |
| Claude Code | httpx | 204,540 | +36% | +12% | +58% | +63% |
| Codex | anvil | 67,634 | +14% | +9% | — | — |
| Codex | httpx | 64,732 | +33% | +8% | — | — |

**Sensitivity check.** If each setup is compared only with the no-graphify sessions of its own day (just 1 repetition per question in the second run), the Claude anvil numbers shrink (+16% official, +8% hooks, +7% strict), Claude httpx stays up (+6% official, +49% hooks, +55% strict), and Codex anvil with the official text flips to −11%. Differences that small are not settled by this data. Task B has a single baseline, so there is no alternative-baseline check for it.

**A second check: Claude's tool count.** Our installation exposed either 21 or 46 extra tools to Claude (anything outside the experiment's own tool set: plugins, connectors and other CLI features), and not evenly across setups. In the 21-extra-tool subset, every Claude increase keeps its sign; the review increases get bigger (+74% to +96%) and the task A ones change by −3 to +18 percentage points. Equal counts don't prove identical tools, so this narrows the doubt about the direction but doesn't remove the imbalance as a confound.

**Question by question** (the median of each question's repetitions, compared only with the same question without graphify), the graphify median was lower on **at most 1 question out of 3–5** for Claude in any setup. Taking the geometric mean of the per-question ratios, Claude used **1.16× to 1.74×** the tokens of no graphify. Codex used **1.04× to 1.21×**.

## What it means, in plain words

- **The map didn't replace the walk, as far as the traces show.** In the graphify setups, graph queries and direct searching and reading of files appear side by side, not in one fixed order (one review ran `git diff --stat` before its first query). graphify's output, thousands of characters, was part of the context. In the PR reviews, Claude's median tool output (serialized characters per session) went from 12,400 to 14,400–15,900. We did not measure which files each setup read or how much reading the graph replaced, so this does not explain the higher totals; it only describes what the traces contain.
- **The setups that push hardest had the highest Claude medians.** The hooks and strict mode, which push the agent towards the graph, had the highest observed Claude token medians on httpx and in the reviews. With the batch and tool-count caveats below, that is what we observed, not a measurement of what the hooks cause.
- **Codex barely moved.** With the official text it ran a graphify command in every session and its observed medians ended up about where they started.
- **Quality: a small plus in most cells, not all.** In the reviews, graphify setups covered slightly more expected points on average (mean coverage 79% → 83–84% for Claude, 68% → 71% for Codex). But Codex with the generic text on anvil dropped from 93% to 84%. With 9–15 sessions per graphify cell and no significance test, these are small differences, not findings.

## Honest limits

- **Small samples.** 3 repetitions per question and condition (1 for the second run's no-graphify task A sessions). Between the two days, the same no-graphify setup varied by +1% to +33% (3 repetitions per question on day one, 1 on day two, with slightly different Claude launch settings: the second run also pre-approved bare `graphify` and `git diff/log/show`). That shows such swings happen; it can't set a precise noise threshold. Differences of that size (Codex, some Claude cells) are not conclusive. The Claude increases in task B, and with hooks and strict on httpx, are larger and hold against the same-day baseline too.
- **No-graphify sessions ran in separate batches.** In the second run's main batches (excluding the pilot), the first recorded timestamp in each Claude trace falls between 08:58 and 09:21 UTC for task B's graphify sessions and between 09:22 and 09:37 for its no-graphify ones, and task A's single extra repetition ran last. One PR repetition came from a pilot run before the main batches (restarted at least once); there, the first recorded timestamps are 07:31–07:32 UTC for its Claude graphify sessions and 07:42 for its no-graphify one, so the same graphify-then-baseline order held there. A time-of-day influence is not ruled out for task B. Task A also uses the first run's no-graphify sessions. That run was two invocations into the same directory: `--reps 1` first, then `--reps 3`, which skipped the completed first repetition and ran the other two. The two setups alternated within each question and repetition.
- **Our normal installation.** Both agents ran with our usual global settings, plugins and a startup hook. They add context, let Claude run extra shell commands, and the number of tools they exposed to Claude changed during the runs, unevenly across setups (see the tool-set check above). Another setup may give different numbers.
- **Two Python codebases.** graphify's docs say savings grow with the size of the corpus; we did not test a very large one.
- **Graphify Cloud** is a different product, and nothing here says anything about it.
- **The quality rubric checks that key points are mentioned**, not that the whole explanation is correct.
- **Claude and Codex numbers can't be compared with each other** (different models, tokenizers and caching). Compare setups within one agent.
- **Token volume and API-equivalent cost only.** The runs used subscription logins; nothing was billed.

## Check it, break it, tell us

Everything is in one repository:

- the harness, the questions and rubrics, and the corpus commits (pinned, and cloned by the harness);
- the instruction files exactly as graphify's installers wrote them, and the hook settings as we instrumented them;
- **every session's trace**, and the hook log of each `hooks` / `strict` session, redacted of our local details;
- the generated report, with all the tables, the sensitivity check and the method.

Repository: [github.com/Burnerator/graphify-tokens](https://github.com/Burnerator/graphify-tokens). If you run it and get different numbers, open an issue. That is the point.
