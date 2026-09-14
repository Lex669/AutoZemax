"""
AutoZemax Session Helper — inspect and start OpticStudio, never more.

This helper answers the two questions the AutoZemax skills need before running
a script:

    1. Is an OpticStudio GUI window already open? (do we need to launch one)
    2. Is the running OpticStudio a headless standalone server left behind by a
       previous API run? (diagnostics only)

It deliberately performs NO API connection. Connecting to the Interactive
Extension consumes the "Waiting for connection..." session, so the probe must
happen exactly once — inside the real AutoZemax script, not here.

It also performs no process termination. Residual headless instances are a
manual diagnostic step documented in the `interactive-session` skill.

Usage:
    python zemax_session.py status [--json]
    python zemax_session.py wait [--timeout 90] [--interval 3]
    python zemax_session.py launch [--wait] [--executable <path>]

Exit codes:
    0  success / condition satisfied
    1  timeout or OpticStudio not found
    2  usage error
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import time

# Candidate install locations, checked in order when no process is running.
_EXE_GLOBS = (
    r"C:\Program Files\ANSYS Inc\v*\Zemax OpticStudio\OpticStudio.exe",
    r"C:\Program Files\Zemax OpticStudio\OpticStudio.exe",
    r"C:\Apps\ANSYS Inc\v*\Zemax OpticStudio\OpticStudio.exe",
    r"C:\Zemax\OpticStudio\OpticStudio.exe",
)

_EXE_ENV_VAR = "AUTOZEMAX_OPTICSTUDIO_EXE"


# ------------------------------------------------------------------
# Process inspection
# ------------------------------------------------------------------

def _powershell(script):
    """Run a PowerShell snippet and return stdout (empty string on failure).

    Output is forced to UTF-8 and decoded defensively: window titles may hold
    characters outside the console code page (e.g. Chinese filenames), which
    would otherwise blow up text-mode subprocess decoding.
    """
    wrapped = ("[Console]::OutputEncoding = "
               "[System.Text.Encoding]::UTF8; " + script)
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", wrapped],
            capture_output=True, timeout=60,
        )
    except Exception:
        return ""
    return (proc.stdout or b"").decode("utf-8", errors="replace").strip()


def _ps_rows(script):
    """Run a PowerShell snippet whose output is a JSON array/object."""
    raw = _powershell(script)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    if isinstance(data, dict):
        return [data]
    return data if isinstance(data, list) else []


def list_instances():
    """Return one dict per running OpticStudio.exe process.

    Each dict has: pid, title, command_line, visible, kind
    ("gui", "headless_server" or "unknown").
    """
    procs = _ps_rows(
        "Get-Process -Name OpticStudio -ErrorAction SilentlyContinue | "
        "Select-Object Id,MainWindowHandle,MainWindowTitle | "
        "ConvertTo-Json -Compress"
    )
    cmds = _ps_rows(
        "Get-CimInstance Win32_Process -Filter \"Name='OpticStudio.exe'\" | "
        "ForEach-Object { [pscustomobject]@{ ProcessId = $_.ProcessId; "
        "CommandLine = $_.CommandLine } } | ConvertTo-Json -Compress"
    )
    cmd_by_pid = {int(r["ProcessId"]): r.get("CommandLine") or ""
                  for r in cmds if r.get("ProcessId") is not None}

    instances = []
    for row in procs:
        pid = row.get("Id")
        if pid is None:
            continue
        pid = int(pid)
        cmd = cmd_by_pid.get(pid, "")
        handle = int(row.get("MainWindowHandle") or 0)
        visible = handle != 0
        # A hidden instance launched by CreateNewApplication() looks like:
        #   OpticStudio.exe -server -pid="<client pid>"
        headless = (not visible) and ("-server" in cmd.lower())
        instances.append({
            "pid": pid,
            "title": row.get("MainWindowTitle") or None,
            "command_line": cmd or None,
            "visible": visible,
            "kind": ("headless_server" if headless
                     else ("gui" if visible else "unknown")),
        })
    instances.sort(key=lambda i: i["pid"])
    return instances


def find_executable():
    """Locate OpticStudio.exe without initializing the ZOS-API.

    Order: env override -> running process -> common install locations.
    """
    override = os.environ.get(_EXE_ENV_VAR)
    if override and os.path.isfile(override):
        return override

    for inst in list_instances():
        cmd = inst.get("command_line") or ""
        if cmd.startswith('"'):
            end = cmd.find('"', 1)
            exe = cmd[1:end] if end > 1 else ""
        else:
            exe = cmd.split(" ")[0]
        if exe.lower().endswith("opticstudio.exe") and os.path.isfile(exe):
            return exe

    for pattern in _EXE_GLOBS:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]  # highest version wins
    return None


def snapshot():
    """Current OpticStudio state, suitable for status reporting."""
    instances = list_instances()
    return {
        "running": bool(instances),
        "visible_gui": any(i["visible"] for i in instances),
        "headless_server": any(i["kind"] == "headless_server"
                               for i in instances),
        "instances": instances,
        "executable": find_executable(),
    }


# ------------------------------------------------------------------
# Reporting
# ------------------------------------------------------------------

def print_status(state):
    """Human-readable status report."""
    if not state["running"]:
        print("OpticStudio: not running")
    else:
        print(f"OpticStudio: {len(state['instances'])} process(es)")
        for inst in state["instances"]:
            title = inst["title"] or "(no window)"
            print(f"  pid {inst['pid']}  [{inst['kind']}]  {title}")
    if state["visible_gui"]:
        print("GUI window: present (interactive mode is possible)")
    else:
        print("GUI window: none - interactive mode needs a visible "
              "OpticStudio window")
    if state["headless_server"]:
        print("Note: a headless -server instance is running. It is unrelated "
              "to the Interactive Extension and can be left alone.")
    print(f"Executable: {state['executable'] or 'not found'}")
    print("Next step: to use interactive mode, click Programming -> "
          "Interactive Extension in OpticStudio so it shows "
          "'Waiting for connection...', then run the AutoZemax script with "
          "mode='interactive'.")


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------

def cmd_status(args):
    state = snapshot()
    if args.json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print_status(state)
    return 0


def cmd_wait(args):
    """Poll until a visible OpticStudio GUI window exists."""
    start = time.time()
    deadline = start + args.timeout
    while True:
        state = snapshot()
        if state["visible_gui"]:
            print(f"OpticStudio GUI is up after {time.time() - start:.0f}s")
            return 0
        if time.time() >= deadline:
            print(f"TIMEOUT: no OpticStudio GUI window after {args.timeout}s",
                  file=sys.stderr)
            print("Check for a licence or login prompt in OpticStudio and "
                  "retry.", file=sys.stderr)
            return 1
        time.sleep(args.interval)


def cmd_launch(args):
    """Start OpticStudio (no UI automation, no licence changes)."""
    state = snapshot()
    if state["visible_gui"]:
        print("OpticStudio GUI already running — nothing to launch.")
        return 0

    exe = args.executable or state["executable"]
    if not exe or not os.path.isfile(exe):
        print("ERROR: OpticStudio.exe not found. Pass --executable <path> or "
              f"set {_EXE_ENV_VAR}.", file=sys.stderr)
        return 1

    print(f"Launching: {exe}")
    subprocess.Popen([exe], close_fds=True)

    if args.wait:
        return cmd_wait(argparse.Namespace(timeout=args.timeout, interval=3))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="zemax_session.py",
        description="Inspect and start OpticStudio for AutoZemax "
                    "(never connects, never kills).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="report OpticStudio processes")
    p_status.add_argument("--json", action="store_true",
                          help="machine-readable output")
    p_status.set_defaults(func=cmd_status)

    p_wait = sub.add_parser("wait", help="wait for a visible GUI window")
    p_wait.add_argument("--timeout", type=float, default=90.0)
    p_wait.add_argument("--interval", type=float, default=3.0)
    p_wait.set_defaults(func=cmd_wait)

    p_launch = sub.add_parser("launch", help="start OpticStudio if not running")
    p_launch.add_argument("--wait", action="store_true",
                          help="wait for the window to appear")
    p_launch.add_argument("--timeout", type=float, default=90.0,
                          help="window wait timeout (with --wait)")
    p_launch.add_argument("--executable", default=None,
                          help="explicit OpticStudio.exe path")
    p_launch.set_defaults(func=cmd_launch)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
