#!/usr/bin/env python3
"""
AI Translation Node — Calls mimo-v2.5-pro via OpenAI-compatible gateway
to generate translation_result.json from a context_pack.

Features:
- Automatic retry with error feedback until success
- JSON response validation and auto-fix
- Cost tracking per chapter
- Dry-run mode for testing
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openai import OpenAI  # noqa: E402
import httpx  # noqa: E402
from utils.io import (  # noqa: E402
    get_logger,
    load_json,
    save_json_atomic,
    resolve_branch_dir,
    now_iso,
    ensure_dir,
)
from prompts.translation_system import (  # noqa: E402
    build_system_prompt,
    build_user_prompt,
    build_retry_prompt,
)
from validate_ai_response import validate_ai_response  # noqa: E402

LOGGER = get_logger("ai_translate")
CONFIG_PATH = ROOT / "ai_config.json"


def load_ai_config() -> dict[str, Any]:
    """Load AI configuration."""
    config = load_json(CONFIG_PATH)
    if not config:
        raise FileNotFoundError(f"AI config not found: {CONFIG_PATH}")
    return config


def create_client(config: dict[str, Any]) -> OpenAI:
    """Create OpenAI client with gateway settings.
    
    Uses a custom httpx client with Accept-Encoding: identity to bypass
    broken gzip encoding from the OpenGateway proxy.
    """
    return OpenAI(
        base_url=config["base_url"],
        api_key=config["api_key"],
        timeout=config.get("timeout_seconds", 600),
        http_client=httpx.Client(
            verify=False,
            headers={"Accept-Encoding": "identity"},
        ),
    )


def log_cost(
    config: dict[str, Any],
    branch_name: str,
    chapter: int,
    attempt: int,
    usage: dict[str, Any],
    success: bool,
) -> None:
    """Append cost entry to the cost log file."""
    if not config.get("cost_tracking"):
        return

    log_path = resolve_branch_dir(branch_name) / "runtime" / config.get(
        "cost_log_file", "ai_cost_log.jsonl"
    )
    ensure_dir(log_path.parent)

    entry = {
        "timestamp": now_iso(),
        "branch": branch_name,
        "chapter": chapter,
        "attempt": attempt,
        "model": config.get("model", "unknown"),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "cost": usage.get("cost", 0),
        "success": success,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def call_api(
    client: OpenAI,
    config: dict[str, Any],
    messages: list[dict[str, str]],
) -> tuple[str, dict[str, Any]]:
    """
    Call the AI API and return (response_text, usage_dict).
    """
    response = client.chat.completions.create(
        model=config["model"],
        messages=messages,
        max_tokens=config.get("max_tokens", 16384),
        temperature=config.get("temperature", 0.3),
    )

    # Extract response text
    choice = response.choices[0]
    content = choice.message.content or ""

    # If model uses reasoning, the content may be in reasoning field
    if not content and hasattr(choice.message, "reasoning"):
        # For reasoning models, the actual answer is in content
        # reasoning is the chain-of-thought
        pass

    # Extract usage
    usage = {}
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        # Try to get cost from response model extras
        raw_usage = response.usage.model_extra or {}
        if "cost" in raw_usage:
            usage["cost"] = raw_usage["cost"]

    return content, usage


def run_ai_translation(
    branch_name: str,
    chapter: int,
    dry_run: bool = False,
) -> dict[str, Any] | None:
    """
    Execute AI translation for a single chapter.
    Retries until success or max retries reached.
    Returns the validated translation result dict, or None on failure.
    """
    config = load_ai_config()
    client = create_client(config)
    max_retries = config.get("max_retries", 10)
    retry_delay = config.get("retry_delay_seconds", 5)

    # Load context pack
    branch_dir = resolve_branch_dir(branch_name)
    pack_path = (
        branch_dir / "runtime" / "context_packs"
        / f"chapter_{chapter:04d}.context_pack.json"
    )
    context_pack = load_json(pack_path)
    if not context_pack:
        LOGGER.error("Context pack not found: %s", pack_path)
        return None

    # Build initial prompts
    system_prompt = build_system_prompt(context_pack)
    user_prompt = build_user_prompt(context_pack)

    LOGGER.info(
        "Starting AI translation for chapter %d (model=%s)",
        chapter,
        config["model"],
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0}

    for attempt in range(1, max_retries + 1):
        LOGGER.info("Attempt %d/%d...", attempt, max_retries)

        try:
            raw_response, usage = call_api(client, config, messages)
        except Exception as e:
            LOGGER.error("API call failed (attempt %d): %s", attempt, e)
            log_cost(config, branch_name, chapter, attempt, {}, False)
            if attempt < max_retries:
                LOGGER.info("Retrying in %ds...", retry_delay)
                time.sleep(retry_delay)
                continue
            else:
                LOGGER.error("All retries exhausted due to API errors.")
                return None

        # Accumulate usage
        for k in ("prompt_tokens", "completion_tokens", "total_tokens", "cost"):
            total_usage[k] = total_usage.get(k, 0) + usage.get(k, 0)

        LOGGER.info(
            "Response received: %d tokens (prompt=%d, completion=%d)",
            usage.get("total_tokens", 0),
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
        )

        # Validate response
        data, errors, warnings = validate_ai_response(raw_response, context_pack)

        for w in warnings:
            LOGGER.warning("  %s", w)

        if not errors and data is not None:
            LOGGER.info("✓ Validation passed on attempt %d", attempt)
            log_cost(config, branch_name, chapter, attempt, total_usage, True)

            if dry_run:
                LOGGER.info("[DRY RUN] Would save translation_result.json")
                print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
                return data

            # Save result
            result_path = (
                branch_dir / "runtime"
                / f"chapter_{chapter:04d}.translation_result.json"
            )
            save_json_atomic(result_path, data)
            LOGGER.info("Saved: %s", result_path)
            LOGGER.info(
                "Total cost: prompt=%d, completion=%d, total=%d tokens",
                total_usage["prompt_tokens"],
                total_usage["completion_tokens"],
                total_usage["total_tokens"],
            )
            return data

        # Errors found — log them and retry
        LOGGER.warning("Validation failed (attempt %d) with %d errors:", attempt, len(errors))
        for e in errors:
            LOGGER.warning("  ✗ %s", e)

        log_cost(config, branch_name, chapter, attempt, usage, False)

        if attempt < max_retries:
            LOGGER.info("Building retry prompt with error feedback...")
            # Build retry message
            retry_msg = build_retry_prompt(errors, raw_response, context_pack)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": raw_response[:4000]},
                {"role": "user", "content": retry_msg},
            ]
            time.sleep(retry_delay)
        else:
            LOGGER.error("All %d retries exhausted. Last errors:", max_retries)
            for e in errors:
                LOGGER.error("  ✗ %s", e)

            # Save the best attempt even if it has errors (for manual fix)
            if data is not None:
                result_path = (
                    branch_dir / "runtime"
                    / f"chapter_{chapter:04d}.translation_result.DRAFT.json"
                )
                save_json_atomic(result_path, data)
                LOGGER.warning("Saved draft (with errors) to: %s", result_path)

            return None

    return None


def test_connection() -> bool:
    """Test API connectivity."""
    config = load_ai_config()
    client = create_client(config)
    LOGGER.info("Testing connection to %s with model %s...", config["base_url"], config["model"])
    try:
        response = client.chat.completions.create(
            model=config["model"],
            messages=[{"role": "user", "content": "Reply with exactly: CONNECTION_OK"}],
            max_tokens=20,
        )
        content = response.choices[0].message.content or ""
        LOGGER.info("Response: %s", content.strip())
        LOGGER.info("✓ Connection successful!")
        return True
    except Exception as e:
        LOGGER.error("✗ Connection failed: %s", e)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Translation Node")
    sub = parser.add_subparsers(dest="command")

    # Test connection
    sub.add_parser("test", help="Test API connection")

    # Translate single chapter
    tr = sub.add_parser("translate", help="Translate a chapter")
    tr.add_argument("--branch", required=True)
    tr.add_argument("--chapter", required=True, type=int)
    tr.add_argument("--dry-run", action="store_true")

    # Batch translate
    bt = sub.add_parser("batch", help="Batch translate chapters")
    bt.add_argument("--branch", required=True)
    bt.add_argument("--from-chapter", required=True, type=int, dest="from_ch")
    bt.add_argument("--to-chapter", required=True, type=int, dest="to_ch")

    args = parser.parse_args()

    if args.command == "test":
        return 0 if test_connection() else 1

    elif args.command == "translate":
        result = run_ai_translation(args.branch, args.chapter, args.dry_run)
        return 0 if result else 1

    elif args.command == "batch":
        failed = []
        for ch in range(args.from_ch, args.to_ch + 1):
            LOGGER.info("=" * 60)
            LOGGER.info("BATCH: Chapter %d", ch)
            result = run_ai_translation(args.branch, ch)
            if not result:
                failed.append(ch)
                LOGGER.error("BATCH: Chapter %d FAILED", ch)
        if failed:
            LOGGER.error("BATCH COMPLETE with failures: %s", failed)
            return 1
        LOGGER.info("BATCH COMPLETE: all chapters translated successfully")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
