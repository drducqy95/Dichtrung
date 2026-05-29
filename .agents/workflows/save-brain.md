---
description: Save long-term context into Trinity local state and run branch scaffolding.
---
# WORKFLOW: /save-brain

You are the Trinity Memory Manager, enhanced with project-specific scaffolding.

Prime rules:
- Use `trinity_cli.py save` as the canonical checkpoint path.
- Always run `branch_scaffold.py --all` after a successful save to keep project artifacts in sync.
- Always run `sync_state.py` after scaffolding to sync glossary & characters to Global State.

## Step 1: Ensure Trinity exists

Run:

```bash
python "C:\Users\vanki\.gemini\antigravity\scripts\trinity_cli.py" init
```

## Step 2: Canonical save

Run:

```bash
python "C:\Users\vanki\.gemini\antigravity\scripts\trinity_cli.py" save --feature "[FEATURE]" --phase "[PHASE]" --notes "[NOTES]"
```

## Step 3: Run branch scaffolding (README + TOC + schema_migrate + character_manifest + home.json)

// turbo
Run:

```bash
python "D:\Dichtrung\Script\branch_scaffold.py" --all
```

> Tự động bao gồm: `schema_migrate.py` (Gold Schema enforcement) + `build_character_prompts.py`
> Để chạy migration riêng lẻ: `python "D:\Dichtrung\Script\schema_migrate.py" --all`

## Step 4: Sync glossary & characters to Global State

// turbo
Run:

```bash
python "D:\Dichtrung\Script\sync_state.py"
```

## Step 5: Confirm the checkpoint

Report:
- feature and phase used
- success of `branch_scaffold.py` scaffolding (all branch READMEs + TOCs + home.json updated)
- success of `sync_state.py` sync (X terms + Y characters merged to Global State)
- what structured domains were already updated before the checkpoint
