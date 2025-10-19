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

        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        header.columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="Zbiorcza konfiguracja źródeł danych", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )

        self.bulk_mode_var = tk.BooleanVar(value=True)
        self.bulk_mode_checkbox = ctk.CTkCheckBox(
            header,
            text="Zbiorcza konfiguracja źródeł danych",
            variable=self.bulk_mode_var,
            command=self.toggle_mode
        )
        self.bulk_mode_checkbox.grid(row=0, column=1, sticky="e", padx=6)

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

        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.files_list = tk.Listbox(list_frame, height=10)

        if ctk.get_appearance_mode() == "Dark":
            self.files_list.configure(
                bg="#333333",
                fg="#FFFFFF",
                selectbackground="#555555",
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
        self.files_list.bind("<<ListboxSelect>>", lambda _e: self._update_buttons_state())

        btns = ctk.CTkFrame(self)
        btns.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        self.btn_refresh = ctk.CTkButton(btns, text="Odśwież listę URL / użytkowników", command=self.refresh_sources)
        self.btn_refresh.pack(side="left", padx=6)

        self.btn_apply_selected = ctk.CTkButton(btns, text="Zastosuj do wybranego", command=self.apply_to_selected)
        self.btn_apply_selected.pack(side="left", padx=6)

        self.btn_apply_all = ctk.CTkButton(btns, text="Zastosuj do wszystkich plików", command=self.apply_to_all,
                                           fg_color="#0b6e4f", hover_color="#0c7d59")
        self.btn_apply_all.pack(side="left", padx=6)

        self.btn_preview = ctk.CTkButton(btns, text="Podgląd (1 plik)…", command=self.preview_one)
        self.btn_preview.pack(side="left", padx=6)



        self.reload_files()
        self.refresh_sources()

        self.toggle_mode()
        self._update_buttons_state()

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

        if not target_url and not target_user:
            messagebox.showwarning(APP_NAME, "Wybierz przynajmniej URL lub użytkownika.")
            return

        paths = list(self.settings.data["paths"])
        files_with_url = []
        files_with_user = []
        files_without_url = []
        files_without_user = []

        for p in paths:
            has_url, has_user = self._file_contains(p, target_url, target_user)
            if target_url:
                (files_with_url if has_url else files_without_url).append(p)
            if target_user:
                (files_with_user if has_user else files_without_user).append(p)

        warn_needed = False
        lines = []
        if target_url and files_without_url:
            warn_needed = True
            lines.append("Brak wybranego URL w plikach:")
            lines += [f" - {os.path.basename(x)}" for x in files_without_url]
        if target_user and files_without_user:
            warn_needed = True
            if lines:
                lines.append("")
            lines.append("Brak wybranego użytkownika w plikach:")
            lines += [f" - {os.path.basename(x)}" for x in files_without_user]

        if warn_needed:
            resp = messagebox.askyesno(
                APP_NAME,
                "Uwaga: Nie wszystkie pliki zawierają wybraną konfigurację.\n"
                "Zmiany zostaną zastosowane tylko tam, gdzie to możliwe.\n\n" +
                "\n".join(lines) +
                "\n\nCzy chcesz kontynuować?"
            )
            if not resp:
                return

        backups = []
        changed_full = []
        changed_url_only = []
        changed_user_only = []
        unchanged = []

        for p in paths:
            has_url, has_user = self._file_contains(p, target_url, target_user)
            if (target_url and not has_url) and (target_user and not has_user):
                unchanged.append(p)
                continue

            try:
                bkp = self.processor.apply_changes_to_file(p, target_url, target_user)
                backups.append((p, bkp))
                if (target_url and has_url) and (target_user and has_user):
                    changed_full.append(p)
                elif (target_url and has_url) and (not target_user or not has_user):
                    changed_url_only.append(p)
                elif (target_user and has_user) and (not target_url or not has_url):
                    changed_user_only.append(p)
                else:
                    unchanged.append(p)
            except Exception as e:
                unchanged.append(p)

        self.settings.data["last_target_url"] = target_url
        self.settings.data["last_username"] = target_user
        self.settings.save()

        msg = []
        if changed_full:
            msg.append("Zmieniono (URL + użytkownik):")
            msg += [f" ✅ {os.path.basename(x)}" for x in changed_full]
            msg.append("")
        if changed_url_only:
            msg.append("Zmieniono tylko URL:")
            msg += [f" ✅ {os.path.basename(x)}" for x in changed_url_only]
            msg.append("")
        if changed_user_only:
            msg.append("Zmieniono tylko użytkownika:")
            msg += [f" ✅ {os.path.basename(x)}" for x in changed_user_only]
            msg.append("")
        if unchanged:
            msg.append("Pominięto (brak wybranego URL i/lub użytkownika):")
            msg += [f" ⚠ {os.path.basename(x)}" for x in unchanged]
            msg.append("")

        if backups:
            msg.append("Utworzono kopie:")
            msg += [f" • {os.path.basename(p)} → {os.path.basename(b)}" for p, b in backups]

        messagebox.showinfo(APP_NAME, "\n".join([line for line in msg if line is not None]) or "Brak zmian.")

    def apply_to_selected(self):
        bulk = self.bulk_mode_var.get()
        if bulk:
            return

        sel = self.files_list.curselection()
        if len(sel) != 1:
            messagebox.showwarning(APP_NAME, "Wybierz dokładnie jeden plik na liście.")
            return

        path = self.files_list.get(sel[0])
        target_url = self.url_var.get().strip()
        target_user = self.user_var.get().strip()

        if not target_url and not target_user:
            messagebox.showwarning(APP_NAME, "Wybierz przynajmniej URL lub użytkownika.")
            return

        has_url, has_user = self._file_contains(path, target_url, target_user)

        if (target_url and not has_url) and (target_user and not has_user):
            messagebox.showinfo(APP_NAME,
                                "Nie da się zmienić konfiguracji w wybranym pliku (zmodyfikuj plik samodzielnie).")
            return

        try:
            bkp = self.processor.apply_changes_to_file(path, target_url, target_user)
            parts = []
            if target_url and has_url:
                parts.append("URL")
            if target_user and has_user:
                parts.append("użytkownika")
            info = " i ".join(parts) if parts else "konfigurację"
            messagebox.showinfo(APP_NAME,
                                f"Zmieniono {info} w pliku:\n{os.path.basename(path)}\n\nKopia: {os.path.basename(bkp)}")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Błąd zapisu: {e}")


    def preview_one(self):
        sel = self.files_list.curselection()
        if not sel:
            messagebox.showinfo(APP_NAME, "Zaznacz plik na liście.")
            return
        path = self.files_list.get(sel[0])

        try:
            target_url = self.url_var.get().strip()
            target_user = self.user_var.get().strip()

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

    def toggle_mode(self):
        bulk = self.bulk_mode_var.get()
        self.files_list.configure(state=("disabled" if bulk else "normal"))
        self._update_buttons_state()

    def _update_buttons_state(self):
        bulk = self.bulk_mode_var.get()
        if bulk:
            self.btn_apply_all.configure(state="normal")
            self.btn_apply_selected.configure(state="disabled")
        else:
            sel = self.files_list.curselection()
            self.btn_apply_all.configure(state="disabled")
            self.btn_apply_selected.configure(state=("normal" if len(sel) == 1 else "disabled"))

    def _file_contains(self, path, url, user):
        try:
            urls, users = self.processor.collect_urls_and_users(path)
            has_url = (url.strip() in urls) if url.strip() else False
            has_user = (user.strip() in users) if user.strip() else False
            return has_url, has_user
        except Exception:
            return False, False
