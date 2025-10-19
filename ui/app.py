import customtkinter as ctk
from config.settings_manager import SettingsManager, APP_NAME
from core.processor import XMLProcessor
from .main_view import MainView
from .settings_view import SettingsView


class App(ctk.CTk):
    """
    Główne okno aplikacji, nawigacja pomiędzy widokami:
    - Główny (zbiorcza zmiana URL / user)
    - Ustawienia (zarządzanie ścieżkami, motywem)
    """
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1000x700")

        # Konfiguracja motywu i koloru z ustawień
        self.settings = SettingsManager()
        ctk.set_appearance_mode(self.settings.data.get("appearance_mode", "System"))
        ctk.set_default_color_theme(self.settings.data.get("color_theme", "blue"))

        self.processor = XMLProcessor()

        # Pasek nawigacji (Segmented Button)
        self.nav = ctk.CTkSegmentedButton(self, values=["Główny", "Ustawienia"], command=self._switch_view)
        self.nav.pack(fill="x", padx=10, pady=10)
        self.nav.set("Główny")

        # Kontener widoków
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        # Inicjalizacja widoków
        self.main_view = MainView(self.container, self.settings, self.processor)
        self.settings_view = SettingsView(
            self.container,
            settings=self.settings,
            on_paths_changed=self._on_paths_changed,
            on_theme_changed=self._on_theme_changed
        )

        # Start
        self.current = None
        self._switch_view("Główny")

    def _switch_view(self, name):
        if self.current is not None:
            self.current.grid_forget()
        if name == "Główny":
            self.current = self.main_view
        else:
            self.current = self.settings_view
        self.current.grid(row=0, column=0, sticky="nsew")

    def _on_paths_changed(self):
        # Gdy zmienią się ścieżki w Ustawieniach – odśwież widok główny
        self.main_view.reload_files()

    def _on_theme_changed(self):
        # Miejsce na dodatkowe reakcje po zmianie motywu
        pass
