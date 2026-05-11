---
description: Build, package, install, and debug vBook extensions for website-backed or repo-backed sources
---

# WORKFLOW: /vbook-extension - Build & Debug vBook Extension

Use this workflow when we need to create, rewrite, package, install, or debug a vBook extension.

## Prime Directive

1. Classify the source first.
   Pick one of:
   - website-backed: parse live site pages or APIs
   - repo-backed: read generated repo artifacts such as `home.json`, `README.md`, `toc.json`, or raw chapter files
2. Define the data contract before coding handlers.
3. Keep the extension bundle minimal and deterministic.
4. Validate locally before touching the app.
5. Treat install failures, tester failures, and runtime bugs as separate problems.

## Step 1: Inspect the source model

For website-backed extensions:
- identify category or ranking pages for `home`
- identify the canonical detail URL
- identify the canonical toc source
- identify the canonical chapter content container

For repo-backed extensions:
- prefer a generated catalog such as `home.json`
- confirm how to resolve `README.md`, `toc.json`, cover image paths, and raw chapter files
- move normalization upstream when we control the repo

## Step 2: Define the extension contract

Required root bundle layout:
- `plugin.json`
- `icon.png`
- `src/`

Required `plugin.json` metadata fields:
- `name`
- `author`
- `version`
- `source`
- `regexp`
- `description`
- `locale`
- `language`
- `type`

Rules:
- set `metadata.language` to `javascript`
- keep `script.home`, `script.detail`, `script.toc`, and `script.chap`
- use `booklist.js` for repo-backed list flows
- use `gen.js` for website-backed list flows

## Step 3: Implement in execution order

1. `config.js`
   Put shared URLs, request helpers, normalization, and fallback logic here.
2. `home.js`
   Return tabs only. Do not overstuff this script with list data if the app expects a second list handler step.
3. List handler
   Use `booklist.js` or `gen.js` depending on the source model.
4. `detail.js`
   Return clean author, intro, info, status, cover, and source links.
5. `toc.js`
   Return canonical chapter order from one source of truth.
6. `chap.js`
   Return cleaned HTML content with stable next or previous navigation where available.

## Step 4: Validate locally

Minimum checks:
- parse every `src/*.js` with Node
- confirm every script referenced by `plugin.json` exists
- confirm bundle root contains only `plugin.json`, `icon.png`, and `src/`
- smoke the flow in order:
  - `home`
  - list handler
  - `detail`
  - `toc`
  - `chap`

Recommended helper:

```powershell
python .agents\skills\vbook-extension-authoring\scripts\vbook_debug_client.py validate D:\APP\ext-dichtrung
python .agents\skills\vbook-extension-authoring\scripts\vbook_debug_client.py pack D:\APP\ext-dichtrung --output D:\Dichtrung\ext-dichtrung-fixed.zip
```

## Step 5: Install and probe the app

Check the app server first. Some builds answer `GET /` with `200 OK` and an empty body. That still counts as alive.

Proven `/install` debug payload:

```json
{
  "id": "dich-trung",
  "name": "Dich Trung",
  "source": "https://github.com/drducqy95/Dichtrung",
  "language": "javascript",
  "home": "home.js",
  "detail": "detail.js",
  "toc": "toc.js",
  "chap": "chap.js",
  "icon": "data:image/*;base64,<icon bytes>",
  "enabled": true,
  "debug": true,
  "data": "{\"home.js\":\"...\",\"config.js\":\"...\"}"
}
```

Transport rule:
- flatten `metadata` and `script` from `plugin.json`
- read `src/*.js` into a script map and JSON-stringify it into payload field `data`
- JSON-encode the full payload
- base64-encode the JSON and send it in the `data` header to `/install`

Known `/test` findings:
- `language`
- `script`
- `ip`
- `root`
- `input`

These fields were proven required during schema probing on previous app builds. Keep probing if the current build asks for more.

Recommended helper:

```powershell
python .agents\skills\vbook-extension-authoring\scripts\vbook_debug_client.py install D:\APP\ext-dichtrung --host http://172.20.10.12:8080 --id dich-trung
python .agents\skills\vbook-extension-authoring\scripts\vbook_debug_client.py request --host http://172.20.10.12:8080 --endpoint /test --payload-json "{\"language\":\"javascript\"}"
```

## Common Failure Modes

- Wrong zip root:
  The app installs only the expected root layout.
- Wrong debug install payload:
  Manual zip import uses `plugin.zip`, but `/install` debug expects flattened metadata plus script contents, not zip bytes.
- Missing `metadata.language` or non-JavaScript value:
  Tester can fail even when install succeeds.
- Missing install wrapper `id`:
  The app can throw `SQLiteConstraintException` on `tb_extension.id`.
- False negative health check:
  High-level clients can misread the app server. Retry with the raw client.
- Repo-backed runtime doing too much parsing:
  Generate `home.json` and `toc.json` upstream instead of scraping many files in-app.

## Working Rule For This Repo

- `D:\Dichtrung\Script\branch_scaffold.py` should generate repo-side catalogs such as `home.json`.
- `D:\APP\ext-dichtrung` is the reference repo-backed extension.
- `D:\APP\ext-uukanshu` is the reference website-backed extension.
