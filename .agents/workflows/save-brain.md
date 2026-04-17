---
description: Save long-term context into Trinity local state and run branch scaffolding.
---
# WORKFLOW: /save-brain

You are the Trinity Memory Manager, enhanced with project-specific scaffolding.

Prime rules:
- Use `trinity_cli.py save` as the canonical checkpoint path.
- Always run `branch_scaffold.py --all` after a successful save to keep project artifacts in sync.

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

## Step 3: Run branch scaffolding (Project Specific)

// turbo
Run:

```bash
python "D:\Dichtrung\Script\branch_scaffold.py" --all
```

## Step 4: Confirm the checkpoint

Report:
- feature and phase used
- success of `branch_scaffold.py` scaffolding
- what structured domains were already updated before the checkpoint
