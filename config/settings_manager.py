import os
import json

APP_NAME = "JBoss/WildFly Datasource Manager"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".jw_ds_manager")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "paths": [],
    "appearance_mode": "System",
    "color_theme": "blue",
    "last_target_url": "",
    "last_username": "",
    "backup_dir": "",
    "backup_limit": 5
}

class SettingsManager:
    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if not os.path.exists(CONFIG_PATH):
            self.data = DEFAULT_SETTINGS.copy()
            self.save()
        else:
            self.load()

    def load(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            self.data = DEFAULT_SETTINGS.copy()
            self.save()

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_paths(self, paths):
        orig = set(self.data["paths"])
        for p in paths:
            p = os.path.abspath(p.strip('"').strip("'"))
            if os.path.isfile(p) and p.lower().endswith(".xml"):
                orig.add(p)
        self.data["paths"] = sorted(orig)
        self.save()

    def remove_paths(self, paths):
        s = set(self.data["paths"])
        for p in paths:
            if p in s:
                s.remove(p)
        self.data["paths"] = sorted(s)
        self.save()

    def replace_path(self, old, new):
        new = os.path.abspath(new.strip('"').strip("'"))
        if not (os.path.isfile(new) and new.lower().endswith(".xml")):
            raise ValueError("Ścieżka nie wskazuje na istniejący plik XML.")
        self.data["paths"] = [new if p == old else p for p in self.data["paths"]]
        self.data["paths"] = sorted(set(self.data["paths"]))
        self.save()

    def get_effective_backup_dir(self):
        root = self.data.get("backup_dir") or os.path.join(CONFIG_DIR, "backups")
        os.makedirs(root, exist_ok=True)
        return root

    def get_backup_limit(self):
        try:
            limit = int(self.data.get("backup_limit", 5))
        except Exception:
            limit = 5
        return max(1, limit)