# Vault — core operating rules

Auto-loaded every session. Compact, imperative rule set for the AI hot path. The root `CLAUDE.md` (human-owned narrative rationale, Korean) holds the top-level **change-sync duty** (what-changed → what-docs-to-update) and **wins on conflict** — flag the mismatch instead of silently diverging.

## Structure (mechanism vs content)
- Content lives in **topic directories**, each `<Topic>/` holding notes + a `<Topic>/<Topic>.md` MOC hub. Current topics: `Claude/` (Claude Code official-docs KB, 26 notes) · `AI-Infra/` (backend→AI-infra learning, 6 notes) · `Infra/` (CS/Linux/kernel fundamentals, 10 notes) · `Meta/` (vault's own architecture self-diagnosis). This is **content (data)**.
- `.claude/` — the **portable framework package** (rules, runtime, hooks, scripts, tests, commands, agents, skills). Copyable to another vault as-is.
- Keep the split when adding files: mechanism → `.claude/`; knowledge → a topic dir. Adding a new topic → follow the checklist in root `CLAUDE.md`'s change-sync table.

## Note format
Frontmatter, four fields (canonical list in `.claude/kb-required-fields.txt`):
- `title` — note title.
- `updated` — `YYYY-MM-DD`. The note's last **content** revision (a pure schema migration like adding `type` does not bump it — freshness signal stays meaningful).
- `sources` — array of official-doc slugs/URLs the note synthesizes (MOC hubs use `[]`). Block-style YAML lists (`sources:` then `  - …`) and inline (`[a, b]`) both parse — kb-lint reads both.
- `type` — closed enum, canonical values in `.claude/kb-allowed-types.txt`: `reference` (look-up facts/API/options) · `explanation` (concept/why) · `how-to` (goal-oriented procedure) · `tutorial` (learning path/roadmap) · `moc` (Map of Content hub; exempt from `sources`). This is OKF v0.1's one required field + Diátaxis's axis; kb-lint blocks any value outside the enum. Don't split a note just to fit one type — heading hierarchy carries atomic sub-concepts (a deliberately-synthesized reference note may span many doc pages by design).

Body is Korean prose. Commands, flags, config keys, env vars, and code stay **English** (verbatim from the docs). Use `[[wikilinks]]` **only to notes that already exist**. End each note with a `## 원본 문서` section listing the source URLs.

## Update duty (CANONICAL — 3 steps)
Single source of truth for the update obligation. Commands and agents **reference this; they don't re-spec it.** Any action that creates or changes a note must do all three, in order:
1. Bump `updated` in the note's frontmatter.
2. Reflect the change in that directory's MOC (`Claude/Claude.md` for the KB) — a new note gets a link + one-line summary.
3. Add one **English** line to `.claude/runtime/hot.md`; keep it rolling at ~500 words.

(The old four-step duty that touched `index.md` / `log.md` is retired — do not reference it.)

## Navigation order (context layering, multi-topic)
L1 `.claude/runtime/hot.md` (auto-injected by `session-context`) → **L1.5 topic router** (hot.md's `Content` line already lists every topic + one-line description — use it to pick which topic the query falls under) → L2 that topic's `<Topic>/<Topic>.md` MOC → L3 individual notes. Read the cheapest layer that answers the question first. (Do not hardcode `Claude/Claude.md` — there are multiple topics; route via L1.5.)

## macOS caveat — keep the MOC lean
On case-insensitive APFS, `Claude/Claude.md` collides with the `CLAUDE.md` memory filename, so it is **auto-injected as context** whenever you work under `Claude/`. Keep the MOC hub lean — it is paid for on every such session.

## Maintenance (lint)
- Machine lint: `python3 .claude/kb-lint.py` — checks frontmatter fields, date format, and `[[wikilink]]` targets across the vault. Add `--online` to diff the `sources` slugs against the official `llms.txt` index.
- The `kb-lint-check` PostToolUse hook gives the same checks per-edit, on a single file, as you save it.

## claude-radar (daily ecosystem radar)
A daily launchd cron runs `/claude-radar collect` headless: `radar-collect.py` scrapes public sources across two topics — **Claude Code** (HN · GitHub · GeekNews · Anthropic release-notes · dev.to · npm) and **AI-Infra learning** (vLLM/KServe/Karpenter releases.atom · HN AI-infra keywords, `AI-infra:`-tagged) → dedups via `runtime/radar-seen.json` → the session appends recommendations to `runtime/radar-queue.md`. **Safety invariant: the unattended collect step writes ONLY the queue + ledger — it MUST never create skills/agents/commands/rules or ingest KB notes.** Generation happens only in `/claude-radar review` (interactive) after explicit user consent, using official tools (skill-creator for skills; `.claude/{agents,commands,rules}/*.md` for the rest; `/kb-ingest` for KB — `AI-infra:` items → `AI-Infra/`, else `Claude/`). Pending queue items surface at SessionStart via the `session-context` hook. The collect↔review split is what keeps "ask before adding" true — do not collapse it.

## study-coach (daily AI-Infra learning loop)
A daily launchd cron (09:30) runs `/study-coach review` headless: it `git pull --ff-only`s the vault, then an LLM reviews yesterday's work in the **separate `ai-infra-lab` repo (READ-ONLY — `git log`/`diff`/Read only, never commit/edit it)**, grades it against the completion criteria, checks off finished items (`- [ ]`→`- [x]`) and appends a dated review log in `runtime/study-state.md`, then runs `study-brief.py` (0-LLM) to write today's `runtime/study-today.md` + a macOS notification. **Safety invariant: the unattended step writes ONLY `.claude/runtime/` (study-state.md, study-today.md) — it MUST never touch the `ai-infra-lab` repo, `.claude/` mechanisms, or KB notes.** Backed mechanically by `stray-guard.sh runtime` (reverts any out-of-scope vault change before the commit boundary; `ai-infra-lab` is a different repo so it's outside the vault working tree entirely). **Multi-machine:** progress lives in `study-state.md` (git-tracked → shared across the two Macs); `last_brief_date` is a 2nd idempotency key so two Macs don't double-review the same day; the anacron stamp (`runtime/study-last-run`) and `runtime/study-local.conf` (per-machine `repo_path` override) are gitignored. Install per studying Mac via `install-study-coach-cron.sh`; skip it on a Mac where unattended review isn't wanted and run `/study-coach review` manually instead. Per automation-safety: unattended tier = sonnet, allowlist scoped (study-brief.py + git + runtime writes).

## Contradictions
Never delete conflicting claims — mark them:
```
> [!warning] 모순
> [[A]]는 X라 하지만 [[B]](2026-05)는 Y라고 함. 출처 확인 필요.
```

## Explicit non-goals (do NOT add these without a real trigger)
The vault's strength is partly in what it deliberately does **not** build. At ~45 notes with a hand-curated MOC + wikilink graph (already a GraphRAG community-summary equivalent), the cold-start cost of these exceeds their value. Recording the decision here stops it being re-litigated every `/claude-radar review`.
- **Embeddings / vector search / RAG index** — MOC + `[[wikilink]]` navigation covers global/relational queries at zero token cost. Reconsider only if "find a concept by meaning when its name is unknown" queries become frequent AND the vault grows past ~100 notes; then add a local opt-in `SQLite FTS5 (BM25) + multilingual ONNX embedding + RRF` as an **L2.5 fallback** (MOC-first stays primary), read-only, never per-query.
- **RDF / JSON-LD / OWL ontology** — the semantic-web lesson is that the operational cost (hand annotation, ontology consensus) sinks it. Markdown + frontmatter + wikilink is the right altitude.
- **Typed relation frontmatter** (`related` / `up` / `part-of`) — body `[[wikilink]]` already carries relations (Claude/ averages ~37/note); a relation field would be double-entry that kb-lint must then dangling-check too. `type` is the only frontmatter axis we add.
- **OKF export script / AGENTS.md** — deferred until external publishing or other-agent (Cursor/Codex) interop is a real need. See `.claude/EXTENSIBILITY.md`. The vault stays source-of-truth; wikilink→standard-md-link is an export-boundary concern, not an internal conversion.
