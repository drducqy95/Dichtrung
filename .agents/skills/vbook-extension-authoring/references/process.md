# VBook Extension Authoring Process

## 1. Identify the source model

Decide which of these two extension shapes you are building:

- Website-backed source:
  Site already has category, detail, toc, and chapter pages. Build a parser-oriented extension.
- Repo-backed source:
  Data lives in generated artifacts, markdown, JSON, or a Git repo. Build a catalog-oriented extension.

Use the repo-backed shape whenever you control the upstream data, because it lets you move complexity out of the app and into build-time artifacts.

## 2. Design the data contract first

For repo-backed sources, prefer a generated catalog file such as `home.json` with:

- top-level `tabs`
- top-level `books`
- per-book fields for `branch`, `title`, `author`, `summary`, `backdrop`, `status`, `completed_chapters`, `total_chapters`, `categories`, `cover_candidates`, `cover_slots`, `readme_path`, `toc_path`

This avoids teaching the extension to scrape many repo files on every screen.

For website-backed sources, define:

- how `home.js` returns tabs
- which list handler script each tab uses
- the canonical detail URL
- the canonical toc source
- the canonical chapter content source

## 3. Build the extension skeleton

Required files at zip root:

- `plugin.json`
- `icon.png`
- `src/`

Required `plugin.json` metadata fields that have proven necessary in practice:

- `name`
- `author`
- `version`
- `source`
- `regexp`
- `description`
- `locale`
- `language`
- `type`

Required `script` fields:

- `home`
- `detail`
- `toc`
- `chap`

Typical repo-backed file set:

- `src/config.js`
- `src/home.js`
- `src/booklist.js`
- `src/detail.js`
- `src/toc.js`
- `src/chap.js`

Typical website-backed file set:

- `src/config.js`
- `src/home.js`
- `src/gen.js`
- `src/detail.js`
- `src/toc.js`
- `src/chap.js`

## 4. Write shared helpers before handlers

Put these concerns in `config.js`:

- repo or site base URLs
- raw/API URL builders
- request wrappers
- line-break normalization
- title and chapter ordering helpers
- catalog loading and fallback logic
- HTML escaping

Do not duplicate these helpers across handler scripts.

## 5. Implement handlers in execution order

Implement and validate in this order:

1. `home.js`
2. list handler (`booklist.js` or `gen.js`)
3. `detail.js`
4. `toc.js`
5. `chap.js`

This keeps the debugging path aligned with how the app actually reaches content.

## 6. Local validation checklist

Before packaging:

- Parse every `src/*.js` with Node using `new Function(...)`.
- Confirm every script path referenced by `plugin.json` exists.
- For repo-backed sources, validate `home.json` shape.
- For repo-backed toc, confirm chapter URLs resolve to real raw files.
- For chapter rendering, verify markdown transforms produce valid HTML snippets.

Recommended smoke flow:

1. Run `home.js`
2. Take the first returned tab and run the list handler
3. Take the first returned book and run `detail.js`
4. Run `toc.js` on that same book
5. Run `chap.js` on the first chapter URL

## 7. Package cleanly

Always rebuild the zip from scratch.

The zip root should contain only:

- `plugin.json`
- `icon.png`
- `src/...`

Do not leave stale files at zip root.

## 8. App-side debugging order

Debug in this order:

1. Connectivity:
   Confirm the app debug server is listening.
2. Install contract:
   Prove `/install` accepts the wrapper payload and returns `status:0`.
3. Tester contract:
   Probe `/test` until the payload schema is complete.
4. Runtime:
   Only after `/test` reaches script execution should you debug handler code.

## 9. Known high-value pitfalls

- Missing `metadata.language` causes tester failure even when the bundle looks correct.
- The app may require a wrapper JSON with an explicit `id` when installing.
- The app debug server may return unusual HTTP behavior; standard clients can report protocol violations even when the server is alive.
- A repo-backed extension that reads many source files at runtime becomes fragile. Normalize upstream data instead.
- Empty or missing cover assets should still have a deterministic cover slot path in metadata.
