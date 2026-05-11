# VBook App Debug Contract Notes

These notes capture the behaviors proven during direct interaction with the vBook app debug server.

## 1. Health checks

Observed behavior:

- `GET /` can return `HTTP/1.1 200 OK` with `Content-Length: 0`.
- Some standard HTTP clients can report protocol issues even though the server is alive.

Practical rule:

- If a high-level client fails with a protocol violation, retry with a raw socket or the bundled debug client before assuming the app is down.

## 2. `/install` contract

The debug `/install` endpoint expects the unpacked extension payload used by `vbook-extension-maker`, not a plugin zip.

Payload shape:

```json
{
  "id": "debug-<metadata.source>",
  "name": "<metadata.name>",
  "author": "<metadata.author>",
  "version": 1,
  "source": "<metadata.source>",
  "regexp": "<metadata.regexp>",
  "description": "<metadata.description>",
  "locale": "<metadata.locale>",
  "language": "javascript",
  "type": "novel",
  "home": "home.js",
  "detail": "detail.js",
  "toc": "toc.js",
  "chap": "chap.js",
  "icon": "data:image/*;base64,<icon bytes>",
  "enabled": true,
  "debug": true,
  "data": "{\"home.js\":\"...\",\"detail.js\":\"...\"}"
}
```

Transport detail:

- Flatten `metadata` and `script` from `plugin.json`.
- Read every `src/*.js` file into the nested `data` object.
- JSON-stringify that nested script map.
- UTF-8 JSON encode the whole payload, then base64-encode it.
- Send the encoded payload in the request header named `data`.

Observed failure mode:

- If `id` is missing, the app can fail with `SQLiteConstraintException: NOT NULL constraint failed: tb_extension.id`.
- Sending a zip base64 inside `data` can return `{"status":0}` but still leave an invalid extension record that crashes the extension screen when the app reads it.

Observed success condition:

- With `id` present, `/install` returned `{"status":0}`.

## 3. `/test` contract discovery

The tester endpoint is stricter than install.

During schema probing, omitting these fields caused immediate JSON exceptions:

- `language`
- `script`
- `ip`
- `root`
- `input`

Practical implication:

- A tester payload must carry more than the install payload.
- Treat `/test` as a separate contract. Do not assume install success implies test success.

At minimum, the bundle metadata should also include:

```json
"language": "javascript"
```

Without it, the tester can fail even when install succeeds.

## 4. Suggested debugging sequence

1. Confirm app server liveness.
2. Prove `/install` with a minimal wrapper using `id` and `data`.
3. Probe `/test` incrementally until all required fields are known for that app version.
4. Only then debug handler runtime.

## 5. Recommended tooling usage

Use `scripts/vbook_debug_client.py` for:

- packing and validating the bundle
- sending the proven install wrapper
- probing `/test` with arbitrary JSON payloads

This keeps transport quirks out of the extension code itself.
