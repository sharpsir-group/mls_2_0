# Contributing to Sharp Matrix Platform KB

## How to Add a New Document

1. Create the markdown file in the appropriate `docs/` subdirectory
2. Add the file to the chapter `index.md`
3. Add the file to `docs/INDEX.md`
4. Add the file to `AGENTS.md` (tree structure + task navigation table if applicable)
5. Add cross-references to related documents

## Naming Conventions

- File names: `kebab-case.md`
- Directory names: `kebab-case/`
- Use descriptive names that indicate content

## Document Structure

Every document should include:

1. An H1 title
2. A `> Source:` callout with the source repo/file
3. A `> **For Lovable**:` callout explaining relevance to app building
4. A `## Cross-Reference` section at the bottom linking to related docs

## Breaking Changes

Changes that may affect Lovable's ability to consume the KB:

- Renaming files referenced in `AGENTS.md`
- Changing table/column names in data model docs
- Altering auth flow patterns in `app-template.md`
- Modifying RLS patterns in `security-model.md`

These changes require an ADR in `docs/architecture/decisions/`.
