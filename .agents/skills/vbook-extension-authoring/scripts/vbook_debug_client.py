#!/usr/bin/env python3
"""Validate, pack, and talk to the vBook app debug server."""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
import zipfile


REQUIRED_METADATA_KEYS = (
    "name",
    "author",
    "version",
    "source",
    "regexp",
    "description",
    "locale",
    "language",
    "type",
)
REQUIRED_SCRIPT_KEYS = ("home", "detail", "toc", "chap")


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def warn(message: str) -> None:
    print(f"WARN: {message}")


def parse_host(raw_host: str) -> tuple[str, int]:
    value = raw_host if "://" in raw_host else f"http://{raw_host}"
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if not host:
        raise ValueError(f"invalid host: {raw_host}")
    port = parsed.port or 80
    return host, port


def load_plugin(ext_dir: Path) -> dict[str, Any]:
    plugin_path = ext_dir / "plugin.json"
    if not plugin_path.exists():
        raise FileNotFoundError(f"missing {plugin_path}")
    return json.loads(plugin_path.read_text(encoding="utf-8"))


def resolve_script_path(ext_dir: Path, script_name: str) -> Path:
    candidate = ext_dir / "src" / script_name
    if candidate.exists():
        return candidate
    candidate = ext_dir / script_name
    return candidate


def check_node_parse(script_paths: list[Path]) -> list[str]:
    try:
        subprocess.run(
            ["node", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        warn("Node was not found. Skipping JS parse check.")
        return []

    errors: list[str] = []
    for script_path in script_paths:
        command = [
            "node",
            "-e",
            (
                "const fs=require('fs');"
                "new Function(fs.readFileSync(process.argv[1],'utf8'));"
            ),
            str(script_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "parse failed"
            errors.append(f"{script_path}: {detail}")
    return errors


def validate_ext_dir(ext_dir: Path) -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not ext_dir.exists():
        return fail(f"extension directory does not exist: {ext_dir}")

    plugin_path = ext_dir / "plugin.json"
    icon_path = ext_dir / "icon.png"
    src_dir = ext_dir / "src"

    if not plugin_path.exists():
        errors.append(f"missing {plugin_path}")
    if not icon_path.exists():
        errors.append(f"missing {icon_path}")
    if not src_dir.is_dir():
        errors.append(f"missing {src_dir}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    try:
        plugin = load_plugin(ext_dir)
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"failed to read plugin.json: {exc}")

    metadata = plugin.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("plugin.json is missing object field metadata")
        metadata = {}
    script = plugin.get("script")
    if not isinstance(script, dict):
        errors.append("plugin.json is missing object field script")
        script = {}

    for key in REQUIRED_METADATA_KEYS:
        value = metadata.get(key)
        if value in (None, ""):
            errors.append(f"metadata.{key} is required")

    if metadata.get("language") != "javascript":
        errors.append('metadata.language must be "javascript"')

    script_paths: list[Path] = []
    for key in REQUIRED_SCRIPT_KEYS:
        value = script.get(key)
        if value in (None, ""):
            errors.append(f"script.{key} is required")
            continue
        resolved = resolve_script_path(ext_dir, str(value))
        if not resolved.exists():
            errors.append(f"script.{key} points to missing file: {value}")
        else:
            script_paths.append(resolved)

    root_entries = {path.name for path in ext_dir.iterdir()}
    expected_root = {"plugin.json", "icon.png", "src"}
    extra_roots = sorted(root_entries - expected_root)
    if extra_roots:
        warnings.append(
            "extra root entries will be excluded from packed zip: "
            + ", ".join(extra_roots)
        )

    parse_errors = check_node_parse(script_paths)
    errors.extend(parse_errors)

    for message in warnings:
        warn(message)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"OK: validated {ext_dir}")
    return 0


def pack_ext_dir(ext_dir: Path, output_path: Path) -> int:
    code = validate_ext_dir(ext_dir)
    if code != 0:
        return code

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(ext_dir / "plugin.json", "plugin.json")
        archive.write(ext_dir / "icon.png", "icon.png")
        for path in sorted((ext_dir / "src").rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(ext_dir).as_posix())

    with zipfile.ZipFile(output_path, "r") as archive:
        names = archive.namelist()
    print(f"OK: packed {output_path}")
    print("ZIP_ROOT:")
    for name in names:
        print(f"  {name}")
    return 0


def build_install_payload(ext_dir: Path, extension_id: str | None = None) -> dict[str, Any]:
    plugin = load_plugin(ext_dir)
    metadata = plugin.get("metadata") or {}
    script = plugin.get("script") or {}
    if not isinstance(metadata, dict) or not isinstance(script, dict):
        raise ValueError("plugin.json must contain metadata and script objects")

    payload: dict[str, Any] = {}
    payload.update(metadata)
    payload.update(script)
    payload["id"] = extension_id or ("debug-" + str(metadata.get("source") or "unknown"))
    payload["icon"] = "data:image/*;base64," + base64.b64encode(
        (ext_dir / "icon.png").read_bytes()
    ).decode("ascii")
    payload["enabled"] = True
    payload["debug"] = True

    script_data: dict[str, str] = {}
    for script_path in sorted((ext_dir / "src").glob("*.js")):
        script_data[script_path.name] = script_path.read_text(encoding="utf-8")
    payload["data"] = json.dumps(
        script_data,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return payload


def raw_http_request(
    host: str,
    port: int,
    path: str,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    body: bytes = b"",
    timeout: float = 10.0,
) -> tuple[str, bytes]:
    request_headers = {
        "Host": f"{host}:{port}",
        "Connection": "close",
    }
    if headers:
        request_headers.update(headers)
    if body:
        request_headers["Content-Length"] = str(len(body))

    header_lines = [f"{method} {path} HTTP/1.1"]
    header_lines.extend(f"{key}: {value}" for key, value in request_headers.items())
    request_bytes = ("\r\n".join(header_lines) + "\r\n\r\n").encode("utf-8") + body

    chunks: list[bytes] = []
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(request_bytes)
        while True:
            data = sock.recv(65536)
            if not data:
                break
            chunks.append(data)

    response = b"".join(chunks)
    if b"\r\n\r\n" in response:
        head, body_bytes = response.split(b"\r\n\r\n", 1)
    elif b"\n\n" in response:
        head, body_bytes = response.split(b"\n\n", 1)
    else:
        head, body_bytes = response, b""
    return head.decode("iso-8859-1", errors="replace"), body_bytes


def print_response(head: str, body: bytes) -> None:
    lines = [line for line in head.splitlines() if line.strip()]
    if lines:
        print(lines[0])
    else:
        print("<no status line>")
    if body:
        text = body.decode("utf-8", errors="replace").strip()
        if text:
            print(text)


def command_health(args: argparse.Namespace) -> int:
    host, port = parse_host(args.host)
    try:
        head, body = raw_http_request(host, port, "/", timeout=args.timeout)
    except OSError as exc:
        return fail(f"health request failed: {exc}")
    print_response(head, body)
    return 0


def command_install(args: argparse.Namespace) -> int:
    host, port = parse_host(args.host)
    ext_dir = Path(args.ext_dir).resolve()
    code = validate_ext_dir(ext_dir)
    if code != 0:
        return code

    try:
        payload = build_install_payload(ext_dir, args.id)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return fail(f"failed to prepare install payload: {exc}")

    encoded_payload = base64.b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    try:
        head, body = raw_http_request(
            host,
            port,
            "/install",
            headers={"data": encoded_payload},
            timeout=args.timeout,
        )
    except OSError as exc:
        return fail(f"install request failed: {exc}")
    print_response(head, body)
    return 0


def load_json_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.payload_json:
        return json.loads(args.payload_json)
    if args.payload_file:
        return json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    raise ValueError("one of --payload-json or --payload-file is required")


def command_request(args: argparse.Namespace) -> int:
    host, port = parse_host(args.host)
    try:
        payload = load_json_payload(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return fail(f"invalid payload: {exc}")

    encoded_payload = base64.b64encode(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    try:
        head, body = raw_http_request(
            host,
            port,
            args.endpoint,
            headers={"data": encoded_payload},
            method=args.method.upper(),
            timeout=args.timeout,
        )
    except OSError as exc:
        return fail(f"request failed: {exc}")
    print_response(head, body)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate, pack, and debug vBook extension bundles."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate an extension directory")
    validate_parser.add_argument("ext_dir", help="Path to the unpacked extension directory")
    validate_parser.set_defaults(func=lambda args: validate_ext_dir(Path(args.ext_dir).resolve()))

    pack_parser = subparsers.add_parser("pack", help="Pack an extension directory into plugin.zip")
    pack_parser.add_argument("ext_dir", help="Path to the unpacked extension directory")
    pack_parser.add_argument(
        "--output",
        default=None,
        help="Output zip path. Defaults to <ext_dir>\\plugin.zip",
    )
    pack_parser.set_defaults(
        func=lambda args: pack_ext_dir(
            Path(args.ext_dir).resolve(),
            Path(args.output).resolve()
            if args.output
            else Path(args.ext_dir).resolve() / "plugin.zip",
        )
    )

    health_parser = subparsers.add_parser("health", help="Check whether the app debug server responds")
    health_parser.add_argument("--host", required=True, help="Host or URL, for example 172.20.10.12:8080")
    health_parser.add_argument("--timeout", type=float, default=10.0, help="Socket timeout in seconds")
    health_parser.set_defaults(func=command_health)

    install_parser = subparsers.add_parser("install", help="Install an unpacked extension directory into the app")
    install_parser.add_argument("ext_dir", help="Path to the unpacked extension directory")
    install_parser.add_argument("--host", required=True, help="Host or URL, for example 172.20.10.12:8080")
    install_parser.add_argument(
        "--id",
        default=None,
        help="Extension id. Defaults to debug-<metadata.source>, matching vbook-extension-maker.",
    )
    install_parser.add_argument("--timeout", type=float, default=10.0, help="Socket timeout in seconds")
    install_parser.set_defaults(func=command_install)

    request_parser = subparsers.add_parser("request", help="Send a base64 JSON payload to an app endpoint")
    request_parser.add_argument("--host", required=True, help="Host or URL, for example 172.20.10.12:8080")
    request_parser.add_argument("--endpoint", required=True, help="Endpoint path, for example /test")
    request_parser.add_argument("--payload-json", help="Inline JSON payload")
    request_parser.add_argument("--payload-file", help="Path to a JSON file payload")
    request_parser.add_argument("--method", default="GET", help="HTTP method. Default: GET")
    request_parser.add_argument("--timeout", type=float, default=10.0, help="Socket timeout in seconds")
    request_parser.set_defaults(func=command_request)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
