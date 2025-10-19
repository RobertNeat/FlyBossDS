import os
import json

APP_NAME = "JBoss/WildFly Datasource Manager"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".jw_ds_manager")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "paths": [],
    "appearance_mode": "System",   # "System" | "Dark" | "Light"
    "color_theme": "blue",         # "blue" (domyślnie niebieski schemat CTk)
    "last_target_url": "",
    "last_username": "",
}


class SettingsManager:
    """
    Zarządza odczytem i zapisem ustawień aplikacji:
    - lista ścieżek do plików XML
    - motyw (System/Dark/Light) i schemat kolorów (blue)
    - ostatnio użyty URL i użytkownik
    """
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

    # ===== Operacje na ścieżkach =====

    def add_paths(self, paths):
        """Dodaje nowe ścieżki (tylko istniejące pliki .xml)."""
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
        """Podmienia jedną ścieżkę na inną (walidacja, że XML istnieje)."""
        new = os.path.abspath(new.strip('"').strip("'"))
        if not (os.path.isfile(new) and new.lower().endswith(".xml")):
            raise ValueError("Ścieżka nie wskazuje na istniejący plik XML.")
        self.data["paths"] = [new if p == old else p for p in self.data["paths"]]
        # deduplikacja + sort
        self.data["paths"] = sorted(set(self.data["paths"]))
        self.save()
