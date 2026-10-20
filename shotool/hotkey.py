import ast
import re
import subprocess

SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
LEGACY_PATH = "/" + SCHEMA.replace(".", "/") + "/custom-keybindings/shotool/"
LEGACY_ITEM = f"{SCHEMA}.custom-keybinding:{LEGACY_PATH}"
CANDIDATES = ["<Super><Shift>s", "<Primary><Super>s", "<Primary><Alt><Shift>s"]
MODIFIER_ORDER = ["ctrl", "super", "alt", "shift"]
ALIASES = {"primary": "ctrl", "control": "ctrl", "ctrl": "ctrl"}


def gsettings(*args):
    result = subprocess.run(["gsettings", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def custom_paths():
    try:
        raw = gsettings("get", SCHEMA, "custom-keybindings")
        return ast.literal_eval(raw.removeprefix("@as "))
    except (OSError, subprocess.CalledProcessError, ValueError, SyntaxError):
        return []


def normalize(accel):
    mods = {ALIASES.get(m.lower(), m.lower()) for m in re.findall(r"<(\w+)>", accel)}
    return frozenset(mods), re.sub(r"<\w+>", "", accel).lower()


def pretty(accel):
    mods, key = normalize(accel)
    parts = [m.capitalize() for m in MODIFIER_ORDER if m in mods]
    return "+".join(parts + [key.upper()])


def taken():
    used = {}
    try:
        listing = subprocess.run(["gsettings", "list-recursively"], capture_output=True, text=True)
    except OSError:
        return used
    for line in listing.stdout.splitlines():
        schema, _, rest = line.partition(" ")
        key, _, value = rest.partition(" ")
        for accel in re.findall(r"'([^']*<[^']*)'", value):
            used.setdefault(normalize(accel), f"{schema} {key}")
    for path in custom_paths():
        if path == LEGACY_PATH:
            continue
        try:
            binding = gsettings("get", f"{SCHEMA}.custom-keybinding:{path}", "binding").strip("'")
        except (OSError, subprocess.CalledProcessError):
            continue
        if binding:
            used.setdefault(normalize(binding), f"custom shortcut {path}")
    return used


def choose(binding=None):
    used = taken()
    if binding:
        return binding, used.get(normalize(binding))
    for candidate in CANDIDATES:
        if normalize(candidate) not in used:
            return candidate, None
    return CANDIDATES[0], used.get(normalize(CANDIDATES[0]))


def remove_legacy():
    paths = custom_paths()
    if LEGACY_PATH not in paths:
        return
    try:
        gsettings("set", SCHEMA, "custom-keybindings", str([p for p in paths if p != LEGACY_PATH]))
        for key in ("name", "command", "binding"):
            gsettings("reset", LEGACY_ITEM, key)
    except (OSError, subprocess.CalledProcessError):
        pass
