---
name: autozemax:model
description: Zemax optical system modeling — create, edit, and configure lens systems
argument-hint: "[task description]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion", "Skill"]
---

# /autozemax:model — Optical System Modeling

Guide the user through creating or modifying Zemax optical systems.
This command covers sequential and non-sequential modeling workflows.

## When Invoked

When the user runs `/autozemax:model`, first ask what they want to do
using AskUserQuestion. Present these categories:

1. **Create new system** — Set up a new optical system from scratch
2. **Load existing system** — Open a .zos file for editing
3. **Edit sequential surfaces** — Add/modify surfaces in the Lens Data Editor
4. **Configure NSC system** — Set up non-sequential objects and detectors
5. **System parameters** — Modify aperture, fields, wavelengths

After the user chooses, load the appropriate skill and execute:

| User Intent | Skill to Load |
|------------|---------------|
| Create new system, load file, system parameters | `system-setup` |
| Edit sequential surfaces, solves, variables | `sequential-modeling` |
| NSC objects, detectors, sources | `non-sequential-modeling` |

## Workflow

1. Ask the user what modeling task they need using AskUserQuestion
2. Based on their choice, load the corresponding skill via the Skill tool
3. Follow the skill's workflow to generate and execute the Python script
4. Use the Python interpreter documented in `references/environment.md`
5. Scripts import from `${CLAUDE_PLUGIN_ROOT}/scripts/zos_utils.py`
   (Claude Code sets `CLAUDE_PLUGIN_ROOT` at runtime; use `os.environ.get()` in Python)
6. Report results back to user; offer to save or continue editing

## Python Script Template

Every generated script should start with:

```python
import sys, os
# Use CLAUDE_PLUGIN_ROOT set by Claude Code at runtime
_plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
if _plugin_root:
    sys.path.insert(0, os.path.join(_plugin_root, 'scripts'))
from zos_utils import ZOSConnection
# ... skill-specific code ...
```

## Notes

- Always use the ZOSConnection context manager for proper cleanup
- Save work frequently to avoid data loss
- Reference `zos-api-reference.md` for API details
- Reference `environment.md` for Python path and package info
