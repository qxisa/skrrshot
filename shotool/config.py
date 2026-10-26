import json
import os

DEFAULT_HOTKEY = "<Super><Shift>s"
DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "shotool")
PATH = os.path.join(DIR, "config.json")


def load():
    try:
        with open(PATH) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def save(data):
    os.makedirs(DIR, exist_ok=True)
    with open(PATH, "w") as handle:
        json.dump(data, handle, indent=2)


def get(key, default=None):
    return load().get(key, default)


def put(**values):
    data = load()
    data.update(values)
    save(data)


def clear():
    try:
        os.remove(PATH)
    except OSError:
        pass


def hotkey():
    return get("hotkey", DEFAULT_HOTKEY)
