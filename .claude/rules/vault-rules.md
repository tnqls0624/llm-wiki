# Vault — core operating rules

Auto-loaded every session. Compact, imperative rule set for the AI hot path. A root `CLAUDE.md` (human-owned narrative rationale, Korean) does not currently exist — when the vault is reorganized that is its slot; on conflict it wins, so flag the mismatch instead of silently diverging.

## Structure (mechanism vs content)
- `Claude/` — Claude Code official-docs KB: 26 Korean notes (`01 시작하기` … `26 변경 이력과 용어집`) + `Claude/Claude.md` MOC hub. This is **content (data)**.
- Future topics follow the same pattern: a `<Topic>/` directory holding notes plus a `<Topic>/<Topic>.md` MOC hub.
- `.claude/` — the **portable framework package** (rules, runtime, hooks, scripts, tests, commands, agents, skills). Copyable to another vault as-is.
- Keep the split when adding files: mechanism → `.claude/`; knowledge → a topic dir.

## Note format
Frontmatter, three fields only:
- `title` — note title.
- `updated` — `YYYY-MM-DD`.
- `sources` — array of official-doc slugs the note synthesizes (MOC hubs use `[]`).

Body is Korean prose. Commands, flags, config keys, env vars, and code stay **English** (verbatim from the docs). Use `[[wikilinks]]` **only to notes that already exist**. End each note with a `## 원본 문서` section listing the source URLs.

## Update duty (CANONICAL — 3 steps)
Single source of truth for the update obligation. Commands and agents **reference this; they don't re-spec it.** Any action that creates or changes a note must do all three, in order:
1. Bump `updated` in the note's frontmatter.
2. Reflect the change in that directory's MOC (`Claude/Claude.md` for the KB) — a new note gets a link + one-line summary.
3. Add one **English** line to `.claude/runtime/hot.md`; keep it rolling at ~500 words.

(The old four-step duty that touched `index.md` / `log.md` is retired — do not reference it.)

## Navigation order (context layering)
L1 `.claude/runtime/hot.md` (auto-injected by the `session-context` hook) → L2 the relevant MOC (`Claude/Claude.md`) → L3 individual notes. Read the cheapest layer that answers the question first.

## macOS caveat — keep the MOC lean
On case-insensitive APFS, `Claude/Claude.md` collides with the `CLAUDE.md` memory filename, so it is **auto-injected as context** whenever you work under `Claude/`. Keep the MOC hub lean — it is paid for on every such session.

## Maintenance (lint)
- Machine lint: `python3 .claude/kb-lint.py` — checks frontmatter fields, date format, and `[[wikilink]]` targets across the vault. Add `--online` to diff the `sources` slugs against the official `llms.txt` index.
- The `kb-lint-check` PostToolUse hook gives the same checks per-edit, on a single file, as you save it.

## claude-radar (daily ecosystem radar)
A daily launchd cron runs `/claude-radar collect` headless: `radar-collect.py` scrapes ~8 public sources (HN · GitHub · GeekNews · Anthropic release-notes · dev.to · npm) → dedups via `runtime/radar-seen.json` → the session appends recommendations to `runtime/radar-queue.md`. **Safety invariant: the unattended collect step writes ONLY the queue + ledger — it MUST never create skills/agents/commands/rules or ingest KB notes.** Generation happens only in `/claude-radar review` (interactive) after explicit user consent, using official tools (skill-creator for skills; `.claude/{agents,commands,rules}/*.md` for the rest; `/kb-ingest` for KB). Pending queue items surface at SessionStart via the `session-context` hook. The collect↔review split is what keeps "ask before adding" true — do not collapse it.

## Contradictions
Never delete conflicting claims — mark them:
```
> [!warning] 모순
> [[A]]는 X라 하지만 [[B]](2026-05)는 Y라고 함. 출처 확인 필요.
```
