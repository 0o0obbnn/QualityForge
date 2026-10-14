# QualityForge Requirements Documentation Reorganization Plan

> **For agentic workers:** Execute inline in the current session. This project is not a Git repository; do not use Git or worktrees.

**Goal:** Reorganize QualityForge requirement and design artifacts into responsibility-based directories while preserving filenames, content, cross-document navigation, audit priority, and executable prototype paths.

**Architecture:** Keep `AGENTS.md` at the workspace root. Move active documents under `docs/` by product, PRD, governance, and architecture responsibility; move current and historical reviews under `docs/05-audits/`; move executable/sample artifacts under `prototypes/`. Rewrite local Markdown and `file://` links mechanically after moves, then validate every resolvable local link.

**Tech Stack:** Markdown, YAML, JSON, filesystem paths, shell link verification.

## Global Constraints

- The workspace is not a Git repository; do not run Git commands.
- Preserve every existing filename and file content except mechanically necessary path references and the path catalog in `AGENTS.md`.
- Historical reports `40-52` may be relocated by the user's explicit request, but their analytical content must not be edited.
- Keep `skills/` and `e2e-validation/` contents unchanged while relocating their parent paths.
- Do not delete any project artifact.
- Validate local links and inventory counts after relocation.

---

### Task 1: Freeze the inventory and link baseline

**Files:**
- Read: workspace root, `audit-v2/`, `skills/`, `e2e-validation/`, `archive/`, `wireframes/`

- [ ] Record file counts and SHA-256 hashes before moving.
- [ ] Inventory Markdown links and absolute `file://` references.
- [ ] Confirm destination collisions do not exist.

### Task 2: Create the responsibility-based directories

**Files:**
- Create directories under `docs/` and `prototypes/`.

- [ ] Create `docs/00-navigation/`.
- [ ] Create `docs/01-product/`.
- [ ] Create `docs/02-prd/`.
- [ ] Create `docs/03-governance/`.
- [ ] Create `docs/04-architecture/`.
- [ ] Create `docs/05-audits/current/` and `docs/05-audits/historical/`.
- [ ] Create `docs/06-wireframes/` and `docs/99-archive/`.
- [ ] Create `prototypes/skills/` and `prototypes/e2e-validation/` through directory relocation.

### Task 3: Relocate files without changing filenames

**Files:**
- Move top-level numbered documents into the matching destination.
- Move `audit-v2/*` into `docs/05-audits/current/`.
- Move historical reports into `docs/05-audits/historical/`.
- Move `skills/` and `e2e-validation/` into `prototypes/`.
- Move `wireframes/` and `archive/` under `docs/`.

- [ ] Move navigation documents `53-54`.
- [ ] Move product documents `01-04`.
- [ ] Move module PRDs `10-19` while separating same-numbered reports by filename.
- [ ] Move governance documents `20-22`.
- [ ] Move architecture documents `30-37`.
- [ ] Move current and historical audits.
- [ ] Move prototype, wireframe, and archive directories.

### Task 4: Rewrite path references and workspace instructions

**Files:**
- Modify: Markdown/YAML/JSON path references across the workspace.
- Modify: `AGENTS.md` project path catalog.

- [ ] Replace old absolute `file://` targets with their new absolute locations.
- [ ] Rebase relative Markdown links from each moved file to its target.
- [ ] Update plain authoritative path references in `AGENTS.md` and navigation documents.
- [ ] Preserve URLs, anchors, and internal OpenAPI references.

### Task 5: Verify the reorganization

**Files:**
- Read all relocated artifacts.

- [ ] Compare pre/post file counts.
- [ ] Compare SHA-256 after normalizing path-reference-only changes where practical.
- [ ] Confirm every expected destination file exists and no old duplicate regular file remains.
- [ ] Validate every relative local Markdown link.
- [ ] Validate every absolute `file://` link under the workspace.
- [ ] Parse `32-API规范.yaml` and `audit-v2/概念权威基线.json` from their new locations.
- [ ] Confirm all 29 Skill entrypoints and all 13 E2E files remain present.
- [ ] Confirm historical report bodies changed only where a local path reference required rebasing.
