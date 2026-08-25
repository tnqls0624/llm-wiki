# Vault — core operating rules

Auto-loaded every session. Compact, imperative rule set for the AI hot path. The root `CLAUDE.md` (human-owned narrative rationale, Korean) holds the top-level **change-sync duty** (what-changed → what-docs-to-update) and **wins on conflict** — flag the mismatch instead of silently diverging.

## Structure (mechanism vs content)
- Content lives in **topic directories**, each `<Topic>/` holding notes + a `<Topic>/<Topic>.md` MOC hub. Current topics: `80 Tooling/` (Claude Code official-docs KB 30 notes + the absorbed vault self-diagnosis note + `31 하네스 엔지니어링`, the one externally-curated note) · `20 Architecture/` (CS/Linux/kernel fundamentals, 10) · `30 AI Infrastructure/` (backend→AI-infra learning, 8). 53 `.md` = **50 notes + 3 MOC hubs** — when quoting ratios, state which denominator you used; kb-lint counts 53 (it does not subtract MOCs). This is **content (data)**.
- `.claude/` — the **portable framework package** (rules, runtime, hooks, scripts, tests, commands, agents, skills). Copyable to another vault as-is.
- `blog/` — blog drafts + their collected images (`blog/<slug>/` = `<slug>.md` draft + `N. name.png` numbered images + `SOURCES.md` provenance, produced by soobeen-voice + `blog-collect.py`). Git-tracked but **neither KB content nor mechanism** — a publishing workspace, so kb-lint excludes it (like `Projects/`).
- Keep the split when adding files: mechanism → `.claude/`; knowledge → a topic dir; blog output → `blog/`. Adding a new topic → follow the checklist in root `CLAUDE.md`'s change-sync table.

## Note format
Frontmatter, **11 fields** — the metaprompt's §12 schema, adopted whole by user decision 2026-08-22 (canonical list in `.claude/kb-required-fields.txt`; do not re-spec it here or in commands):
- `id` — stable identifier, `<folder-prefix>-<nn>` (e.g. `tooling-07`, `arch-00`, `aiinfra-04`, `meta-00`). Survives file moves; nothing resolves links by it (wikilinks resolve by basename), so treat it as a label, not a key.
- `title` — note title. Not required to match the filename; MOC hubs keep their descriptive title (e.g. `80 Tooling/80 Tooling.md` is titled "Claude Code 사용법").
- `type` — closed enum, canonical values in `.claude/kb-allowed-types.txt`: `evergreen` · `concept` · `architecture` · `comparison` · `playbook` · `career`. kb-lint blocks any value outside it. Migration mapping from the retired enum: reference/how-to→`playbook`, explanation→`concept`, tutorial→`career`, moc→`evergreen`. `architecture`/`comparison` are unused slots for new notes.
- `status` — `seed` | `growing` | `evergreen` | `deprecated`. Maturity. Currently `evergreen` for the finished official-docs KB, `growing` for the two learning KBs.
- `created` — `YYYY-MM-DD`, first commit date. Set from git history at migration time, not invented.
- `updated` — `YYYY-MM-DD`. The note's last **content** revision (a pure schema migration does not bump it — freshness signal stays meaningful).
- `area` — the owning Area (`개발자 학습` · `AI 인프라 역량` · …). Mirrors the Notion Area vocabulary.
- `tags` — inline list, max 5. Currently one machine-derived topic tag per note; human curation is still outstanding.
- `source_urls` — array of official-doc slugs/URLs the note synthesizes (MOC hubs use `[]`). **Renamed from `sources`** in the §12 adoption. Block-style YAML lists (`source_urls:` then `  - …`) and inline (`[a, b]`) both parse. Caveat inherited from the rename: for `80 Tooling/` notes the values are official-doc **slugs**, not URLs, because `--online` slug-diff and `kb-source-hashes.py` compare them against `llms.txt`.
- `notion_url` — the counterpart Notion page. Currently `""` on every note: no per-note mapping exists.
- `confidentiality` — `personal` | `public` | `company-sensitive`. **Label only — there is no mechanical gate**, and this vault auto-pushes to a public remote, so the label must not be treated as protection (see automation-safety: a prompt-level instruction is not enforcement).

**MOC detection is path-based**, not type-based: a note is a MOC iff its filename equals its parent directory name. The §12 enum has no `moc` value, so the basis moved to the path — the same basis the MOC-backlink check already used, which collapses two rules into one.

Body is Korean prose. Commands, flags, config keys, env vars, and code stay **English** (verbatim from the docs). Use `[[wikilinks]]` **only to notes that already exist**. End each note with a `## 원본 문서` section listing the source URLs.

## Update duty (CANONICAL — 3 steps)
Single source of truth for the update obligation. Commands and agents **reference this; they don't re-spec it.** Any action that creates or changes a note must do all three, in order:
1. Bump `updated` in the note's frontmatter.
2. Reflect the change in that directory's MOC (`<dir>/<dir>.md` — e.g. `80 Tooling/80 Tooling.md`) — a new note gets a link + one-line summary.
3. Add one **English** line to `.claude/runtime/hot.md`. **Interactive sessions** may Edit it directly; **unattended runs MUST use `python3 .claude/hot-append.py --line "<English one-liner>"`** — the harness classifies that path as sensitive and denies unattended Edit/Write (the 2026-08-24 kb-sync run finished its KB work but failed duty-③ twice for exactly this reason, and still exited 0). The script inserts at the top of `## Recent sessions`, auto-numbers a second same-day entry, refuses header/control-char injection, leaves the `INJECT` block untouched, and writes `runtime/hot-last-append.json` — the receipt the kb-sync wrapper checks to decide whether duty-③ actually completed. Rolling size is a **mechanical cap (25 entries, `--prune`)**, replacing the old "~500 words" hand contract that had drifted to 7,100 words unnoticed.

(The old four-step duty that touched `index.md` / `log.md` is retired — do not reference it.)

## Navigation order (context layering, multi-topic)
L1 `.claude/runtime/hot.md` (auto-injected by `session-context`) → **L1.5 topic router** (hot.md's `Content` line already lists every topic + one-line description — use it to pick which topic the query falls under) → L2 that topic's `<Topic>/<Topic>.md` MOC → L3 individual notes. Read the cheapest layer that answers the question first. (Do not hardcode `80 Tooling/80 Tooling.md` — there are multiple topics; route via L1.5.)

## macOS caveat — resolved 2026-08-22 (keep the MOC lean anyway)
The old `Claude/Claude.md` collided with the `CLAUDE.md` memory filename on case-insensitive APFS, so it was auto-injected as context on every session touching that directory. The §11 rename to `80 Tooling/80 Tooling.md` **removed that collision** as a side effect — no topic MOC shares a name with `CLAUDE.md` now. Keep MOC hubs lean regardless: they are the L2 layer every navigation pays for.

## Maintenance (lint)
- Machine lint: `python3 .claude/kb-lint.py` — checks frontmatter fields, date format, and `[[wikilink]]` targets across the vault. Add `--online` to diff the `source_urls` slugs against the official `llms.txt` index.
- The `kb-lint-check` PostToolUse hook gives the same checks per-edit, on a single file, as you save it.

## claude-radar (daily ecosystem radar)
A **weekly** launchd cron (Wed 09:33; daily→weekly 2026-08-23 — processing, not collection, is the bottleneck, and the 26-day silent failure proved daily was over-collection) runs `/claude-radar collect` headless: `radar-collect.py` scrapes public sources across two topics — **Claude Code** (HN · GitHub · GeekNews · Anthropic release-notes · dev.to · npm) and **AI-Infra learning** (vLLM/KServe/Karpenter releases.atom · HN AI-infra keywords, `AI-infra:`-tagged) → dedups via `runtime/radar-seen.json` → the session writes recommendations to a `/tmp` fragment and **`radar-collect.py --append-queue` validates and appends them to `runtime/radar-queue.md`** (the harness classifies that path as sensitive and denies unattended Edit/Write — the 26-day silent failure of 2026-07-28~08-22; the allowlisted script is the only unattended write path, per automation-safety "deterministic code for unattended durable changes"). Pending items **expire to `[expired]` after 30 days** (status flip, never deletion — an unprocessed queue must stay finite or it kills the loop, as the Notion briefing DB proved). **Safety invariant: the unattended collect step writes ONLY the queue + ledger — it MUST never create skills/agents/commands/rules or ingest KB notes.** Generation happens only in `/claude-radar review` (interactive) after explicit user consent, using official tools (skill-creator for skills; `.claude/{agents,commands,rules}/*.md` for the rest; `/kb-ingest` for KB — `AI-infra:` items → `30 AI Infrastructure/`, else `80 Tooling/`). Pending queue items surface at SessionStart via the `session-context` hook. The collect↔review split is what keeps "ask before adding" true — do not collapse it.

## study-coach (daily AI-Infra learning loop)
A daily launchd cron (09:30) runs the wrapper, which `git pull --ff-only`s the vault **and then the `ai-infra-lab` repo, and applies a commit gate (2026-08-23): if there are no new `ai-infra-lab` commits since the last review-log date, the LLM review is skipped entirely — no tokens, no notification (a no-commit day is the normal state of a burst rhythm; loop-death is watched separately by the session-context dead-man banner). A failed pull is loud: review is skipped (grading a stale checkout would be fail-silent), rc=1 keeps the anacron stamp unbumped for retry, and a warning notification fires.** On commit days an LLM reviews yesterday's work in the **separate `ai-infra-lab` repo (READ-ONLY — `git log`/`diff`/Read only, never commit/edit it)**, grades it against the completion criteria, checks off finished items (`- [ ]`→`- [x]`) and appends a dated review log in `runtime/study-state.md`, then runs `study-brief.py` (0-LLM) to write today's `runtime/study-today.md` + a macOS notification. **Safety invariant: the unattended step writes ONLY `.claude/runtime/` (study-state.md, study-today.md) — it MUST never touch the `ai-infra-lab` repo, `.claude/` mechanisms, or KB notes.** Backed mechanically by `stray-guard.sh runtime` (reverts any out-of-scope vault change before the commit boundary; `ai-infra-lab` is a different repo so it's outside the vault working tree entirely). **Multi-machine:** progress lives in `study-state.md` (git-tracked → shared across the two Macs); `last_brief_date` is a 2nd idempotency key so two Macs don't double-review the same day; the anacron stamp (`runtime/study-last-run`) and `runtime/study-local.conf` (per-machine `repo_path` override) are gitignored. Install per studying Mac via `install-study-coach-cron.sh`; skip it on a Mac where unattended review isn't wanted and run `/study-coach review` manually instead. Per automation-safety: unattended tier = sonnet, allowlist scoped (study-brief.py + git + runtime writes).

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
- **Typed relation frontmatter** (`related` / `up` / `part-of`) — still a non-goal. Body `[[wikilink]]` already carries relations (`80 Tooling/` averages ~44/note); a relation field would be double-entry that kb-lint must then dangling-check too.
  > [!warning] 결정 변경 (2026-08-22)
  > "`type` is the only frontmatter axis we add" no longer holds. The user adopted the metaprompt's §12 schema whole, which added `id`/`status`/`created`/`area`/`tags`/`notion_url`/`confidentiality`. The concerns recorded before that decision — `area`/`tags` duplicate the directory axis, `notion_url` is the typed-relation pattern pointing outward, `confidentiality` is a label with no mechanical gate — were reported and the decision was reaffirmed. They are open debts, not settled design. Typed *internal* relation fields remain rejected.
- **OKF export script / AGENTS.md** — deferred until external publishing or other-agent (Cursor/Codex) interop is a real need. See `.claude/EXTENSIBILITY.md`. The vault stays source-of-truth; wikilink→standard-md-link is an export-boundary concern, not an internal conversion.
