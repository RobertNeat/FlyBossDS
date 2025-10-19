import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, settings, on_paths_changed, on_theme_changed):
        super().__init__(master)
        self.settings = settings
        self.on_paths_changed = on_paths_changed
        self.on_theme_changed = on_theme_changed

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Ustawienia", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 0)
        )

        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.paths_list = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=12)
        self.paths_list.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        btns = ctk.CTkFrame(list_frame)
        btns.grid(row=0, column=1, sticky="ns", padx=(5, 10), pady=10)

        ctk.CTkButton(btns, text="Dodaj pliki…", command=self._add_files).pack(fill="x", pady=4)
        ctk.CTkButton(btns, text="Dodaj folder…", command=self._add_folder).pack(fill="x", pady=4)
        ctk.CTkButton(btns, text="Edytuj zaznaczony…", command=self._edit_selected).pack(fill="x", pady=4)
        ctk.CTkButton(btns, text="Usuń zaznaczone", fg_color="#8b0000", hover_color="#a40000",
                      command=self._remove_selected).pack(fill="x", pady=8)

        paste_frame = ctk.CTkFrame(self)
        paste_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        paste_frame.columnconfigure(1, weight=1)
        ctk.CTkLabel(paste_frame, text="Wklej ścieżkę:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.path_entry = ctk.CTkEntry(paste_frame, placeholder_text=r"C:\folder\plik.xml lub /home/u/plik.xml")
        self.path_entry.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="ew")
        ctk.CTkButton(paste_frame, text="Dodaj", command=self._add_from_entry).grid(row=0, column=2, padx=10, pady=10)

        self._setup_optional_dnd()

        theme_frame = ctk.CTkFrame(self)
        theme_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        ctk.CTkLabel(theme_frame, text="Motyw:", width=80).pack(side="left", padx=10, pady=10)

        self.appearance_var = tk.StringVar(value=self.settings.data.get("appearance_mode", "System"))
        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["System", "Dark", "Light"],
            variable=self.appearance_var,
            command=self._change_appearance
        )
        self.theme_menu.pack(side="left", padx=6, pady=10)

        ctk.CTkLabel(theme_frame, text="Schemat kolorów:").pack(side="left", padx=(20, 6))
        self.color_theme_var = tk.StringVar(value=self.settings.data.get("color_theme", "blue"))
        self.color_theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["blue"],
            variable=self.color_theme_var,
            command=self._change_color_theme
        )
        self.color_theme_menu.pack(side="left", padx=6, pady=10)

        ctk.CTkLabel(self, text="Domyślnie: System + blue (ciemne tło w trybie system-dark).",
                     font=ctk.CTkFont(size=11, slant="italic")).grid(row=4, column=0, sticky="w", padx=12, pady=(0, 10))

        self._reload_paths()

    def _setup_optional_dnd(self):
        try:
            import tkinterdnd2  # noqa: F401
            self.tk.call('package', 'require', 'tkdnd')
            self.paths_list.drop_target_register('DND_Files')
            self.paths_list.dnd_bind('<<Drop>>', self._on_drop)
            tip = "Możesz przeciągnąć tu pliki *.xml."
        except Exception:
            tip = "Drag&Drop wymaga pakietu tkinterdnd2 (opcjonalne)."
        ctk.CTkLabel(self, text=tip, font=ctk.CTkFont(size=11, slant="italic")).grid(row=5, column=0, sticky="w", padx=12, pady=(0, 10))

    def _on_drop(self, event):
        data = event.data
        items = []
        token = ""
        in_brace = False
        for ch in data:
            if ch == "{":
                in_brace = True
                token = ""
            elif ch == "}":
                in_brace = False
                items.append(token)
                token = ""
            elif ch == " " and not in_brace:
                if token:
                    items.append(token)
                    token = ""
            else:
                token += ch
        if token:
            items.append(token)
        self.settings.add_paths(items)
        self._reload_paths()
        self.on_paths_changed()

    def _reload_paths(self):
        self.paths_list.delete(0, tk.END)
        for p in self.settings.data["paths"]:
            self.paths_list.insert(tk.END, p)

    def _add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("XML files", "*.xml")])
        if files:
            self.settings.add_paths(files)
            self._reload_paths()
            self.on_paths_changed()

    def _add_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        found = []
        for root, _dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(".xml"):
                    found.append(os.path.join(root, f))
        self.settings.add_paths(found)
        self._reload_paths()
        self.on_paths_changed()

    def _remove_selected(self):
        sel = [self.paths_list.get(i) for i in self.paths_list.curselection()]
        if not sel:
            return
        self.settings.remove_paths(sel)
        self._reload_paths()
        self.on_paths_changed()

    def _edit_selected(self):
        sel = self.paths_list.curselection()
        if not sel:
            return
        from_path = self.paths_list.get(sel[0])
        to_path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")], initialdir=os.path.dirname(from_path))
        if to_path:
            try:
                self.settings.replace_path(from_path, to_path)
                self._reload_paths()
                self.on_paths_changed()
            except Exception as e:
                messagebox.showerror("Błąd", str(e))

    def _add_from_entry(self):
        p = self.path_entry.get().strip()
        if p:
            self.settings.add_paths([p])
            self._reload_paths()
            self.path_entry.delete(0, tk.END)
            self.on_paths_changed()

    def _change_appearance(self, _value):
        import customtkinter as ctk
        mode = self.appearance_var.get()
        self.settings.data["appearance_mode"] = mode
        self.settings.save()
        ctk.set_appearance_mode(mode)
        self.on_theme_changed()

    def _change_color_theme(self, _value):
        import customtkinter as ctk
        theme = self.color_theme_var.get()
        self.settings.data["color_theme"] = theme
        self.settings.save()
        # pełna zmiana koloru w CTk działa najlepiej po restarcie aplikacji
        messagebox.showinfo("Informacja", "Zmiana schematu kolorów zadziała w pełni po ponownym uruchomieniu.")
        ctk.set_default_color_theme(theme)
        self.on_theme_changed()
