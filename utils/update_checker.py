import subprocess
from pathlib import Path
import gi
gi.require_version("Notify", "0.7")
from gi.repository import GLib, Notify
from loguru import logger

Notify.init("caffyne-shell")

REPO_PATH = Path(__file__).parent.parent


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_PATH)


def check_for_updates() -> None:
    try:
        _run(["git", "fetch"])
        result = _run(["git", "rev-list", "HEAD..@{u}", "--count"])
        behind = int(result.stdout.strip())
    except Exception as e:
        logger.warning(f"[UpdateChecker] failed to check for updates: {e}")
        return

    if behind > 0:
        GLib.Thread.new(None, _notify_update_available, behind)


def _notify_update_available(commits_behind: int) -> None:
    n = Notify.Notification.new(
        "Shell update available",
        f"{commits_behind} new commit{'s' if commits_behind > 1 else ''} on origin",
        None
    )
    n.add_action("update", "Pull update", lambda *_: _do_pull(), None)
    n.show()

def _do_pull() -> None:
    result = _run(["git", "pull"])
    if result.returncode == 0:
        _notify_restart_prompt()
    else:
        subprocess.run([
            "notify-send",
            "--app-name=caffyne-shell",
            "--urgency=critical",
            "Shell update failed",
            result.stderr.strip() or "git pull returned an error",
        ])


def _notify_restart_prompt() -> None:
    n = Notify.Notification.new(
        "Shell updated!",
        "Restart to apply changes",
        None
    )
    n.add_action("restart", "Restart now", lambda *_: _restart_shell(), None)
    n.add_action("later", "Later", lambda *_: None, None)
    n.show()

def _restart_shell() -> None:
    import os, sys
    os.execv(sys.executable, [sys.executable] + sys.argv)