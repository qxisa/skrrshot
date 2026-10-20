import os
import subprocess
import sys
import time

from . import __version__

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
USAGE = """usage: shotool [command]

  capture          start a capture (default)
  daemon           run in the background and wait for the shortcut
  reload           re-read the shortcut from the settings
  quit             stop the background process
  update           pull the latest version and restart
  hotkey [ACCEL]   set the shortcut, default is the first free one of
                   Super+Shift+S, Ctrl+Super+S, Ctrl+Alt+Shift+S
  hotkey --remove  remove the shortcut settings
  version
"""


def launcher():
    return os.path.abspath(sys.argv[0])


def check_session():
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        sys.exit("shotool supports X11 only for now. Choose 'Ubuntu on Xorg' on the login screen.")


def start_daemon():
    subprocess.Popen([launcher(), "daemon"], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def update():
    if not os.path.isdir(os.path.join(ROOT, ".git")):
        print("This copy was not installed from git. Download the new release instead.")
        return 1
    subprocess.run(["git", "-C", ROOT, "pull", "--ff-only"], check=True)
    subprocess.run([launcher(), "quit"])
    time.sleep(0.6)
    start_daemon()
    return 0


def hotkey(args):
    from . import config, hotkey as keys

    if args and args[0] == "--remove":
        keys.remove_legacy()
        config.clear()
        return 0
    accel, clash = keys.choose(args[0] if args else None)
    keys.remove_legacy()
    config.save({**config.load(), "hotkey": accel})
    start_daemon()
    time.sleep(0.8)
    if subprocess.run([launcher(), "reload"]).returncode != 0:
        print(f"Could not use {keys.pretty(accel)}, another program holds it.")
        print("Try another one, for example: shotool hotkey '<Primary><Alt>p'")
        return 1
    print(f"Shortcut set to {keys.pretty(accel)}")
    if clash:
        print(f"Note: it was also listed in {clash}")
    return 0


def main():
    args = sys.argv[1:]
    command = args[0].lstrip("-") if args else "capture"
    if command in ("version", "v"):
        print(__version__)
        return 0
    if command == "update":
        return update()
    if command == "hotkey":
        return hotkey(args[1:])
    if command in ("capture", "daemon", "reload", "quit"):
        check_session()
        try:
            from .app import run
        except (ImportError, ValueError):
            print("GTK bindings for the system Python are missing. Run:\n"
                  "  sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0", file=sys.stderr)
            return 1

        return run([sys.argv[0], f"--{command}"] if command != "capture" else [sys.argv[0]])
    print(USAGE)
    return 0 if command in ("h", "help") else 1
