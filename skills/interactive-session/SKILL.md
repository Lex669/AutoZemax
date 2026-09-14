---
name: interactive-session
description: This skill should be used when the user asks to "use interactive mode", "interactive 模式", "交互模式", "连接模式", "switch connection mode", "Interactive Extension", "watch it run", "实时查看", "看着跑", "跑给我看", "use the model I have open", "用当前打开的模型", "在 Zemax 里实时显示", "auto mode", "standalone vs interactive", or when a Zemax task should be visible in the OpticStudio GUI instead of running headless.
version: 0.3.0
---

# Interactive Session — Choosing and Establishing the Connection Mode

AutoZemax can drive OpticStudio in two ways. Pick the mode deliberately, and
know how to arm/repair an interactive session.

| | `standalone` (default) | `interactive` |
|---|---|---|
| How | hidden instance launched by the API | attaches to a running OpticStudio GUI whose Interactive Extension is armed |
| Speed | fast (no UI sync) | slower (every change repaints the GUI) |
| Parallel | several instances allowed | one instance, one connection |
| Setup | none | one click on **Programming → Interactive Extension** |
| Visible to user | no | yes, live |
| Best for | batch optimization, tolerance Monte Carlo, bulk analysis, unattended pipelines | modeling/tuning you want to watch, reusing the user's open design, debugging step by step, demos |
| On finish | `CloseApplication()` shuts the instance down | only disconnects — the user's OpticStudio stays open |

## Standard import block

```python
import sys, os
_PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
for _p in [
    os.path.join(_PLUGIN_ROOT, 'scripts') if _PLUGIN_ROOT else '',
    r'C:\Users\Lex\.claude\plugins\cache\AutoSim\AutoZemax\0.3.0\scripts',
    r'C:\Users\Lex\.codex\plugins\cache\AutoSim\AutoZemax\0.3.0\scripts',
    r'C:\Users\Lex\Desktop\AutoSim\AutoZemax\scripts',
]:
    if _p and os.path.isdir(_p):
        sys.path.insert(0, _p); break
from zos_utils import ZOSConnection, set_seed, ensure_zmx_dir
set_seed(42)
```

## Python API

```python
with ZOSConnection(mode="interactive") as zos:
    print(zos.mode, zos.instance, zos.is_interactive)   # 'interactive' 1 True
    copy = zos.save_interactive_copy()                  # edit a copy, not the user's file
    zos.set_ui_updates(False)                           # optional: bulk edits without repaint
    # ... modeling / analysis code ...
    zos.set_ui_updates(True)                            # optional: replay the result live
```

| Item | Behaviour |
|------|-----------|
| `mode=` | `"standalone"` (default) · `"interactive"` · `"auto"` |
| `AUTOZEMAX_MODE` | env var used when `mode` is not passed |
| `instance=` | pin the extension instance number; default probes 1–8 and takes the first that answers |
| `show_changes_in_ui=` | interactive only, default `True` |
| `zos.mode` / `zos.is_interactive` / `zos.instance` | actual mode after connecting |
| `zos.save_interactive_copy(path=None)` | interactive: `SaveAs` the live system to `zmx/<stem>_interactive.zos` and keep editing the copy; standalone: no-op |
| `zos.set_ui_updates(True/False)` | interactive: toggles `ShowChangesInUI`; standalone: no-op returning `False` |
| `ZOSConnection.InteractiveNotAvailable` | raised by `mode="interactive"` when nothing is waiting |

Mode resolution order: explicit `mode=` → `AUTOZEMAX_MODE` → `standalone`.
`"auto"` reuses a waiting interactive session when one exists, otherwise runs
standalone.

## Bootstrap: arming the Interactive Extension (agent + computer use)

OpticStudio cannot be put into interactive mode programmatically — the session
must be armed in the GUI. The flow below is the measured recipe on OpticStudio
2025 R2.

1. **Check what is already running** (never connects, so it cannot consume a
   waiting session):

   ```
   & "<python>" "<plugin>/scripts/zemax_session.py" status
   ```

2. **No visible GUI window?** Launch and wait:

   ```
   & "<python>" "<plugin>/scripts/zemax_session.py" launch --wait --timeout 90
   ```

   With computer use, `sky.launch_app({app: "<...>\\OpticStudio.exe"})` plus
   `sky.list_windows()` polling works too — a window appears ~15–20 s later
   because of licence checkout.

3. **Arm the extension** with computer use:

   - `sky.get_window({id, app})` → `sky.activate_window` → `sky.get_window_state({include_screenshot: true})`.
   - The accessibility tree of OpticStudio is **empty** — you must work from
     screenshots and window-relative coordinates, and re-observe before every
     single action (dialog positions shift between captures).
   - Click the **Programming** ribbon tab (in Chinese UI: 「编程」). If a
     floating pane (typically **Lens Data**) covers the tab row, first drag the
     pane's title bar out of the way, then re-screenshot.
   - Click the **Interactive Extension** button in the *ZOS API.NET
     Applications* group. There is **no separate Connect button** — this click
     arms the session.
   - Confirm the dialog shows `Instance Number: <n>` and
     `Status: Waiting for connection...`. If it already shows that, skip this
     step entirely.

4. **Run the real script** with `mode="interactive"`. Do not run a separate
   "probe" script first: connecting consumes the session, and the dialog closes
   as soon as the client disconnects. Expect:

   ```
   [AutoZemax] connected / interactive mode (instance 1, live UI updates: True)
   ```

## Working-copy policy

Interactive mode acts on whatever the user has open, so call
`zos.save_interactive_copy()` before modifying anything. It `SaveAs`-es the
live system into `zmx/<stem>_interactive.zos`, which repoints the OpticStudio
window at the copy and leaves the user's original file untouched on disk.
Always report both paths to the user.

A `.ZDA` companion file is written next to the `.zos` by OpticStudio; that is
expected.

## Failure modes and recovery

| Symptom | Cause | Action |
|---------|-------|--------|
| `InteractiveNotAvailable` (< 1 s) | nothing armed, or OpticStudio closed | arm the extension as above, then re-run; if it still fails, fall back to standalone |
| `ArgumentException: This application was not launched by Optic Studio` | `ConnectToApplication()` was used from an external script | use `connect()` with `mode="interactive"` — it calls `ConnectAsExtension(n)` |
| Dialog gone after a run | the extension closes on disconnect | click Interactive Extension again before the next script |
| "Autosave Recovery Notification" on startup | OpticStudio was killed while a document was dirty | click **Close**; do **not** delete recovered files without asking the user |
| "Save changes in ...?" prompt | the document is dirty (connecting can mark it modified) | cannot be driven by computer use — ask the user to answer it |
| Long scripts feel slow | `ShowChangesInUI` repaints every change | `zos.set_ui_updates(False)` during bulk edits |

## Fallback policy

If interactive cannot be established (desktop locked, user away, UI drift,
extension refused), rerun the same task with `mode="standalone"` and tell the
user explicitly:

> 未能建立 interactive 会话（原因），本次已自动改用 standalone 模式完成，结果如下。

Never leave the task unfinished just because the GUI session is unavailable.

## Do / Don't

- **Do** keep the user's original file untouched — always `save_interactive_copy()` first.
- **Do** re-screenshot before every click; never reuse coordinates across observations.
- **Do** report which mode produced the results.
- **Don't** call `CloseApplication()` in interactive mode — the library already handles this, and `close()` only disconnects.
- **Don't** kill OpticStudio.exe or terminate the user's session; if an instance must go away, ask the user.
- **Don't** use `ConnectToApplication()` from a script — it only works for plug-ins OpticStudio launched itself.
