import os
import sys
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from lxml import etree

from config.settings_manager import APP_NAME
from core.processor import XMLProcessor
from core.utils import deep_clone_tree


class MainView(ctk.CTkFrame):
    def __init__(self, master, settings, processor: XMLProcessor):
        super().__init__(master)
        self.settings = settings
        self.processor = processor

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Tytuł
        ctk.CTkLabel(self, text="Zbiorcza konfiguracja źródeł danych", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 0)
        )

        # Forma wyboru
        form = ctk.CTkFrame(self)
        form.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        form.columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Docelowy URL bazy:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.url_var = tk.StringVar(value=self.settings.data.get("last_target_url", ""))
        self.url_combo = ctk.CTkComboBox(form, values=[], variable=self.url_var)
        self.url_combo.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(form, text="Użytkownik (blok <security>):").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.user_var = tk.StringVar(value=self.settings.data.get("last_username", ""))
        self.user_combo = ctk.CTkComboBox(form, values=[], variable=self.user_var)
        self.user_combo.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Lista plików (readonly)
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.files_list = tk.Listbox(list_frame, height=10)

        # Po utworzeniu self.paths_list (lub self.files_list):
        if ctk.get_appearance_mode() == "Dark":
            self.files_list.configure(
                bg="#333333",
                fg="#FFFFFF",
                selectbackground="#555555",  # lub np. "#1f6aa5" aby pasował do CTk
                selectforeground="#FFFFFF",
                highlightthickness=0,
                borderwidth=0,
            )
        else:
            self.files_list.configure(
                bg="#FFFFFF",
                fg="#000000",
                selectbackground="#E5E5E5",
                selectforeground="#000000",
                highlightthickness=0,
                borderwidth=0,
            )


        self.files_list.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Przyciski
        btns = ctk.CTkFrame(self)
        btns.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        ctk.CTkButton(btns, text="Odśwież listę URL / użytkowników", command=self.refresh_sources).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Zastosuj do wszystkich plików", command=self.apply_to_all, fg_color="#0b6e4f", hover_color="#0c7d59").pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Podgląd (1 plik)…", command=self.preview_one).pack(side="left", padx=6)

        self.reload_files()
        self.refresh_sources()

    def reload_files(self):
        self.files_list.delete(0, tk.END)
        for p in self.settings.data["paths"]:
            self.files_list.insert(tk.END, p)

    def refresh_sources(self):
        all_urls = set()
        all_users = set()
        for p in self.settings.data["paths"]:
            try:
                urls, users = self.processor.collect_urls_and_users(p)
                all_urls.update(urls)
                all_users.update(users)
            except Exception as e:
                print(f"[WARN] {p}: {e}", file=sys.stderr)

        urls_sorted = sorted(all_urls)
        users_sorted = sorted(all_users)
        self.url_combo.configure(values=urls_sorted)
        self.user_combo.configure(values=users_sorted)

        if urls_sorted and not self.url_var.get():
            self.url_var.set(urls_sorted[0])
        if users_sorted and not self.user_var.get():
            self.user_var.set(users_sorted[0])

    def apply_to_all(self):
        target_url = self.url_var.get().strip()
        target_user = self.user_var.get().strip()

        if not target_url:
            messagebox.showwarning(APP_NAME, "Podaj docelowy URL bazy.")
            return

        backups = []
        errors = []
        for p in self.settings.data["paths"]:
            try:
                bkp = self.processor.apply_changes_to_file(p, target_url, target_user)
                backups.append((p, bkp))
            except Exception as e:
                errors.append((p, str(e)))

        self.settings.data["last_target_url"] = target_url
        self.settings.data["last_username"] = target_user
        self.settings.save()

        msg_lines = []
        if backups:
            msg_lines.append("Zapisano zmiany (utworzono kopie):")
            for p, b in backups:
                msg_lines.append(f"• {os.path.basename(p)} → {os.path.basename(b)}")
        if errors:
            msg_lines.append("\nBłędy:")
            for p, err in errors:
                msg_lines.append(f"• {p}: {err}")

        messagebox.showinfo(APP_NAME, "\n".join(msg_lines) if msg_lines else "Brak zmian.")

    def preview_one(self):
        sel = self.files_list.curselection()
        if not sel:
            messagebox.showinfo(APP_NAME, "Zaznacz plik na liście.")
            return
        path = self.files_list.get(sel[0])

        try:
            target_url = self.url_var.get().strip()
            target_user = self.user_var.get().strip()

            # Podgląd: pracujemy na klonie drzewa
            from core.utils import read_xml
            tree = read_xml(path)
            tree_copy = deep_clone_tree(tree)

            self.processor.activate_connection_url(tree_copy, target_url)
            if target_user:
                self.processor.activate_user(tree_copy, target_user)

            xml_text = etree.tostring(
                tree_copy, pretty_print=True, xml_declaration=True, encoding="utf-8"
            ).decode("utf-8")

            win = ctk.CTkToplevel(self)
            win.title(f"Podgląd: {os.path.basename(path)}")
            win.geometry("900x600")
            txt = tk.Text(win, wrap="none")
            txt.pack(fill="both", expand=True, padx=10, pady=10)
            txt.insert("1.0", xml_text)
            txt.configure(state="disabled")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Błąd podglądu: {e}")

    def update_listbox_style(self):
        if ctk.get_appearance_mode() == "Dark":
            self.files_list.configure(bg="#333333", fg="#FFFFFF", selectbackground="#555555", selectforeground="#FFFFFF")
        else:
            self.files_list.configure(bg="#FFFFFF", fg="#000000", selectbackground="#E5E5E5", selectforeground="#000000")
