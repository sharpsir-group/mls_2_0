# KB Methodology — Design Principles, Versioning, and Contribution

> This document explains how the Sharp Matrix Knowledge Base itself is designed,
> maintained, and versioned. It serves as both a competitive advantage and an
> operational guide for contributors.

---

## Design Principles

| Principle | Implementation |
|-----------|----------------|
| **LLM-first** | Structured for AI agent consumption, not just human reading |
| **Progressive disclosure** | AGENTS.md → INDEX.md → chapter indexes → individual docs |
| **Task-based navigation** | "If you need to…" table in [AGENTS.md](../../AGENTS.md) |
| **Explicit reading order** | Numbered steps for Lovable in "For Lovable — Start Here" |
| **Self-contained chapters** | Each chapter works independently with cross-references |

## Why This Matters

No PropTech leader (Zillow, Compass, Redfin, CoStar) has published an LLM-readable KB designed as an executable specification for AI-powered app builders. This is a genuine competitive advantage.

## Semantic Versioning for the KB

| Version | When to Bump |
|---------|--------------|
| **Major** | Breaking structure changes (renaming AGENTS.md, reorganizing chapters) |
| **Minor** | New files (adding a new doc) |
| **Patch** | Content updates (fixing, expanding existing docs) |

Changelog maintained in repo; tag releases when shipping major/minor bumps.

## Breaking Change Detection

Checklist for changes that could affect Lovable:

- [ ] Renaming files referenced in AGENTS.md
- [ ] Changing table/column names in data model docs
- [ ] Altering auth flow patterns in app-template.md
- [ ] Modifying RLS patterns in security-model.md
- [ ] Changing Supabase project IDs or Edge Function names

## Contribution Guidelines

**Adding a new doc:**

1. Create file (kebab-case.md)
2. Add to chapter index (e.g. `docs/product-specs/index.md`)
3. Add to AGENTS.md tree
4. Add to INDEX.md table
5. Add task nav entry in AGENTS.md if applicable

**Naming**: Use kebab-case for all doc filenames. **Cross-references**: Every new doc must link to related docs at the bottom.

## Validation Process

Periodic check that KB references match codebase:

- Table names in data model docs vs Supabase schema
- File paths in AGENTS.md vs actual files
- Supabase project IDs (SSO: `xgubaguglsnokjyudgvc`, etc.)
- Edge Function names vs deployed functions

Run validation when: adding new data model docs, changing AGENTS.md structure, or before major Lovable builds.

## Document Conventions

- **Tables over prose**: Prefer structured tables for specifications; easier for LLM parsing.
- **Cross-reference section**: Every doc ends with a "Cross-Reference" table linking to related docs.
- **For Lovable callouts**: Use blockquote `> **For Lovable**:` when content directly affects app-building.
- **Source attribution**: When a doc derives from external sources (PDFs, Mermaid diagrams), cite them at the top.

## Cross-Reference

| For | See |
|-----|-----|
| Master navigation | [AGENTS.md](../../AGENTS.md) |
| Chapter index and summaries | [INDEX.md](../INDEX.md) |
| App template (Lovable entry point) | [app-template.md](app-template.md) |
| Platform chapter index | [platform/index.md](index.md) |
