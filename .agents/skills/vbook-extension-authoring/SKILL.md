---
name: vbook-extension-authoring
description: Author, rewrite, package, install, and debug vBook JavaScript extensions. Use when building or fixing `plugin.json` plus `src/*.js` handlers for vBook, especially for `home/detail/toc/chap` flows, repo-backed catalogs such as `home.json`, website-backed list/detail parsers, zip packaging, or app-side `/install` and `/test` debugging.
---

# VBook Extension Authoring

Build vBook extensions as small, testable bundles. Treat app installation, runtime script execution, and upstream data shape as separate failure surfaces.

## Workflow

1. Inspect the target source first.
   For website-backed extensions, inspect real list/detail/chapter HTML or APIs.
   For repo-backed extensions, inspect the metadata source first. Prefer a normalized catalog such as `home.json` over parsing many raw files inside the extension.

2. Choose the extension shape before coding.
   Use the website-backed pattern when the source site already exposes categories or ranking pages. Typical files: `home.js`, `gen.js`, `detail.js`, `toc.js`, `chap.js`.
   Use the repo-backed pattern when the source is a Git repo or generated artifact set. Typical files: `home.js`, `booklist.js`, `detail.js`, `toc.js`, `chap.js`, with shared helpers in `config.js`.

3. Keep `plugin.json` minimal but complete.
   Always include `metadata.language: "javascript"`.
   Ensure `script.home`, `script.detail`, `script.toc`, and `script.chap` exist and point to real files.
   Keep the zip root exactly as `plugin.json`, `icon.png`, and `src/`.

4. Validate locally before talking to the app.
   Parse every JS file with Node before packing.
   Smoke the handler flow locally in order: `home` -> list handler -> `detail` -> `toc` -> `chap`.
   Validate bundle layout and `plugin.json` with `scripts/vbook_debug_client.py`.

5. Separate install debugging from runtime debugging.
   If install fails, debug the app wrapper payload and zip structure first.
   If install succeeds but the extension fails in app, debug `/test` contract and then the script runtime.

## Decision Rules

- Prefer backend normalization over frontend scraping inside the extension when the source is your own repo.
- Prefer one shared `config.js` for URL builders, normalization, fallback logic, and common parsing helpers.
- Keep app-specific transport quirks out of handler scripts. Put them in tooling or docs.
- When the app debug server returns odd HTTP behavior, fall back to raw socket or a thin custom client instead of assuming the app is dead.

## Local Validation

Use `references/process.md` for the full checklist.

Minimum local checks:

- Parse `src/*.js` with Node.
- Validate `plugin.json` required fields.
- Pack a fresh zip and inspect root entries.
- If the extension depends on remote data, simulate that data locally or map raw URLs to workspace files for smoke testing.

## App Debugging

Read `references/app-debug-contract.md` before using the app debug server.

Use `scripts/vbook_debug_client.py` for:

- `validate`: verify `plugin.json` and file layout
- `pack`: build a clean plugin zip
- `install`: send the proven `/install` debug payload with flattened metadata and script contents
- `request`: probe `/test` or other app endpoints with arbitrary JSON payloads wrapped in the required base64 header

## References

- Read [../../workflows/vbook-extension.md](../../workflows/vbook-extension.md) for the operator-facing workflow used in this repo.
- Read [references/process.md](references/process.md) for the full authoring workflow and failure checklist.
- Read [references/app-debug-contract.md](references/app-debug-contract.md) when install or tester behavior is unclear.
