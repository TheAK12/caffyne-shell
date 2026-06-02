import os
import subprocess
from typing import Optional
from fabric.core.service import Service, Property
from gi.repository import GLib
from loguru import logger
from fabric.utils import get_relative_path


def _get_screen_commands() -> tuple[str, str]:
    """Return (screen_off_cmd, screen_on_cmd) for the running WM."""
    if os.getenv("NIRI_SOCKET"):
        return (
            "niri msg action power-off-monitors",
            "niri msg action power-on-monitors",
        )
    elif os.getenv("HYPRLAND_INSTANCE_SIGNATURE"):
        return (
            "hyprctl dispatch dpms off",
            "hyprctl dispatch dpms on",
        )
    elif os.getenv("MANGO_INSTANCE_SIGNATURE"):
        return (
            "mango msg dpms off",
            "mango msg dpms on",
        )
    else:
        # Generic Wayland fallback via wlopm if available
        return (
            "wlopm --off '*'",
            "wlopm --on '*'",
        )


LOCK_CMD = f"python3 {get_relative_path('../lockscreen.py')} &"
SUSPEND_CMD = "loginctl suspend"


def _build_rule_commands() -> dict[str, tuple[str, Optional[str]]]:
    screen_off, screen_on = _get_screen_commands()
    return {
        "screen-off": (screen_off, screen_on),
        "lock":       (LOCK_CMD,   None),
        "suspend":    (SUSPEND_CMD, None),
    }


class SwayidleService(Service):

    @Property(bool, "readable", default_value=False)
    def active(self) -> bool:
        return self._active

    @Property(bool, "readable", default_value=False)
    def on_battery(self) -> bool:
        return self._on_battery

    def __init__(self, rules: list[dict], **kwargs):
        self._rules: list[dict] = list(rules)
        self._process: Optional[subprocess.Popen] = None
        self._active = False
        self._on_battery = False
        self._upower = None

        super().__init__(**kwargs)

        self._setup_upower()

    def start(self):
        if self._active:
            return
        logger.info("[SwayidleService] Starting...")
        self._active = True
        self.notify("active")
        self._spawn()

    def stop(self):
        if not self._active:
            return
        logger.info("[SwayidleService] Stopping...")
        self._active = False
        self.notify("active")
        self._kill()

    def update_rules(self, rules: list[dict]):
        logger.info("[SwayidleService] Rules updated, respawning...")
        self._rules = list(rules)
        if self._active:
            self._respawn()

    def _setup_upower(self):
        try:
            from services.singletons import battery
            self._upower = battery
            self._on_battery = self._check_battery()
            self._upower.connect("changed", self._on_power_changed)
            logger.info("[SwayidleService] Battery service connected")
        except Exception as e:
            logger.warning(f"[SwayidleService] Battery service unavailable: {e}")

    def _check_battery(self) -> bool:
        if not self._upower:
            return False
        try:
            return self._upower.discharging
        except Exception:
            return False

    def _on_power_changed(self, *_):
        now_battery = self._check_battery()
        if now_battery == self._on_battery:
            return
        self._on_battery = now_battery
        self.notify("on-battery")
        state = "battery" if now_battery else "AC"
        logger.info(f"[SwayidleService] Power state → {state}, respawning...")
        if self._active:
            GLib.timeout_add(1000, self._respawn_once)

    def _respawn_once(self):
        self._respawn()
        return False

    def _build_args(self) -> list[str]:
        args = ["swayidle", "-w"]
        rule_commands = _build_rule_commands()

        for rule in self._rules:
            if not rule.get("enabled", True):
                continue
            name = rule["name"]
            if name not in rule_commands:
                logger.warning(f"[SwayidleService] Unknown rule name: {name!r}, skipping")
                continue

            on_idle, on_resume = rule_commands[name]
            timeout_min = rule["timeout_bat"] if self._on_battery else rule["timeout_ac"]
            timeout_sec = int(timeout_min * 60)

            args += ["timeout", str(timeout_sec), on_idle]
            if on_resume:
                args += ["resume", on_resume]

        logger.debug(f"[SwayidleService] Args: {' '.join(args)}")
        return args

    def _spawn(self):
        args = self._build_args()
        if len(args) <= 2:
            logger.info("[SwayidleService] No enabled rules, not spawning")
            return
        try:
            self._process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"[SwayidleService] Spawned (pid {self._process.pid})")
        except FileNotFoundError:
            logger.error("[SwayidleService] swayidle not found — is it installed?")
        except Exception as e:
            logger.error(f"[SwayidleService] Failed to spawn: {e}")

    def _kill(self):
        if self._process is None:
            return
        try:
            self._process.terminate()
            self._process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        except Exception as e:
            logger.warning(f"[SwayidleService] Error killing process: {e}")
        finally:
            self._process = None

    def _respawn(self):
        self._kill()
        self._spawn()