---
name: autozemax:model
description: Create or edit optical systems (sequential and non-sequential) — Phase 1 of pipeline
argument-hint: "[task description]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion", "Skill", "Agent"]
---

# /autozemax:model — Optical System Modeling (Phase 1)

Guide the user through creating or modifying Zemax optical systems.
This command covers sequential and non-sequential modeling workflows.
It is Phase 1 of the AutoZemax pipeline.

## When Invoked

When the user runs `/autozemax:model`, first ask what they want to do
using AskUserQuestion. Present these categories:

1. **Create new system** — Set up a new optical system from scratch
2. **Load existing system** — Open a .zos/.zmx/.zda file for editing
3. **Edit sequential surfaces** — Add/modify surfaces in the Lens Data Editor
4. **Configure NSC system** — Set up non-sequential objects, sources, detectors
5. **System parameters** — Modify aperture, fields, wavelengths

After the user chooses, load the appropriate skill:

| User Intent | Skill to Load |
|------------|---------------|
| Create new system, load file, system parameters | `system-setup` |
| Edit sequential surfaces, solves, variables, materials, tilts | `sequential-modeling` |
| NSC objects, sources, detectors | `nsc-modeling` |

## Workflow

1. Ask the user what modeling task they need using AskUserQuestion
2. Based on their choice, load the corresponding skill via the Skill tool
3. Follow the skill's workflow to generate and execute the Python script
4. Use the Python interpreter with the compact import template below
5. Report results back to user; offer to save or continue editing
6. **After completion**, run the `model-validator` agent to verify the system configuration

## Python Script Template

Every generated script must use the compact import with `set_seed(42)`:

```python
import sys, os
_PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
for _p in [
    os.path.join(_PLUGIN_ROOT, 'scripts') if _PLUGIN_ROOT else '',
    r'C:\Users\Lex\.claude\plugins\cache\AutoSim\AutoZemax\0.2.0\scripts',
    r'C:\Users\Lex\Desktop\AutoSim\AutoZemax\scripts',
]:
    if _p and os.path.isdir(_p):
        sys.path.insert(0, _p); break
from zos_utils import ZOSConnection, set_seed, ensure_zmx_dir
set_seed(42)

with ZOSConnection() as zos:
    # ... skill-specific modeling code ...
    zos.validate_system_ready()
    # save to zmx/
    zos.save(os.path.join(ensure_zmx_dir(), 'model.zmx'))
```

Execute with:
```
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" <script>.py
```

## Validation

After modeling is complete, run the `model-validator` agent:

```
Agent: model-validator
Prompt: "Validate the optical system at <path>.zmx. Check for:
  - Valid surfaces and materials
  - Correct aperture, fields, wavelengths
  - Proper NSC object configuration
  - Any errors or warnings"
```

## Notes

- Always use the `ZOSConnection` context manager for proper cleanup
- Save work frequently with `zos.save()` to avoid data loss
- Call `zos.validate_system_ready()` after system setup in every script
- Reference `zos-api-reference.md` for ZOS-API details
- The `ensure_zmx_dir()` utility ensures the `zmx/` output directory exists
