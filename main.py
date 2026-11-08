"""LoL Account Manager : interface principale."""
from __future__ import annotations

import threading
import tkinter.messagebox as messagebox

import customtkinter as ctk

import remember
import riot
import startup
from vault import Account, Vault, WrongPassword

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AccountDialog(ctk.CTkToplevel):
    """Fenêtre d'ajout / modification d'un compte."""

    def __init__(self, parent: ctk.CTk, account: Account | None, on_save) -> None:
        super().__init__(parent)
        self.title("Modifier le compte" if account else "Nouveau compte")
        self.geometry("360x400")
        self.resizable(False, False)
        self.transient(parent)
        self.after(150, self.grab_set)

        self._account = account
        self._on_save = on_save

        self.label = self._field("Nom affiché (ex : Main, Smurf)", account.label if account else "")
        self.username = self._field("Identifiant Riot", account.username if account else "")
        self.password = self._field("Mot de passe", account.password if account else "", secret=True)
        self.note = self._field("Note (facultatif)", account.note if account else "")

        ctk.CTkButton(self, text="Enregistrer", command=self._save).pack(pady=18)
        self.bind("<Return>", lambda _e: self._save())

    def _field(self, title: str, value: str, secret: bool = False) -> ctk.CTkEntry:
        ctk.CTkLabel(self, text=title, anchor="w").pack(fill="x", padx=24, pady=(14, 2))
        entry = ctk.CTkEntry(self, show="•" if secret else "")
        entry.pack(fill="x", padx=24)
        entry.insert(0, value)
        return entry

    def _save(self) -> None:
        label, username, password = (
            self.label.get().strip(), self.username.get().strip(), self.password.get(),
        )
        if not (label and username and password):
            messagebox.showwarning("Champs manquants", "Nom, identifiant et mot de passe sont obligatoires.", parent=self)
            return
        account = self._account or Account(label, username, password)
        account.label, account.username, account.password = label, username, password
        account.note = self.note.get().strip()
        self._on_save(account)
        self.destroy()


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("LoL Account Manager")
        self.geometry("520x620")
        self.minsize(460, 400)
        self.vault = Vault()
        self._master = ""
        self._busy = False
        self._show_unlock()

    # ------------------------------------------------------------ déverrouillage
    def _clear(self) -> None:
        for child in self.winfo_children():
            child.destroy()

    def _try_auto_unlock(self) -> bool:
        """Déverrouille sans rien demander si le mot de passe a été mémorisé sur ce PC."""
        if not (Vault.exists() and remember.is_enabled()):
            return False
        master = remember.load()
        if not master:
            remember.forget()  # fichier illisible (autre session Windows...) : on repart propre
            return False
        try:
            self.vault.unlock(master)
        except (WrongPassword, OSError, ValueError):
            remember.forget()  # coffre recréé ou mot de passe obsolète
            return False
        self._master = master
        return True

    def _show_unlock(self, auto: bool = True) -> None:
        if auto and self._try_auto_unlock():
            self._show_main()
            return
        self._clear()
        creating = not Vault.exists()
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(box, text="LoL Account Manager", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(0, 6))
        ctk.CTkLabel(
            box,
            text="Crée ton mot de passe maître.\nIl chiffre tous tes comptes et ne peut pas être récupéré."
            if creating else "Entre ton mot de passe maître.",
            text_color="gray70",
        ).pack(pady=(0, 18))

        pw = ctk.CTkEntry(box, placeholder_text="Mot de passe maître", show="•", width=260)
        pw.pack(pady=4)
        pw.focus()
        confirm = None
        if creating:
            confirm = ctk.CTkEntry(box, placeholder_text="Confirmer", show="•", width=260)
            confirm.pack(pady=4)

        remember_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(box, text="Se souvenir sur ce PC", variable=remember_var).pack(pady=(6, 0))

        error = ctk.CTkLabel(box, text="", text_color="#ff6b6b")
        error.pack(pady=4)

        def finish(master: str) -> None:
            self._master = master
            try:
                if remember_var.get():
                    remember.save(master)
                else:
                    remember.forget()
            except OSError:
                pass  # la mémorisation est facultative : on ne bloque pas l'ouverture du coffre
            self._show_main()

        def submit(_event=None) -> None:
            master = pw.get()
            if creating:
                if len(master) < 8:
                    error.configure(text="8 caractères minimum.")
                elif master != confirm.get():
                    error.configure(text="Les deux mots de passe ne correspondent pas.")
                else:
                    self.vault.create(master)
                    finish(master)
                return
            try:
                self.vault.unlock(master)
            except WrongPassword:
                error.configure(text="Mot de passe incorrect.")
                return
            finish(master)

        ctk.CTkButton(box, text="Créer le coffre" if creating else "Déverrouiller", command=submit, width=260).pack(pady=6)
        self.bind("<Return>", submit)

    # ------------------------------------------------------------ écran principal
    def _show_main(self) -> None:
        self._clear()
        self.unbind("<Return>")

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 6))
        ctk.CTkLabel(header, text="Mes comptes", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="+ Ajouter", width=90, command=self._add).pack(side="right")
        ctk.CTkButton(header, text="🔒 Verrouiller", width=100, fg_color="transparent", border_width=1,
                      command=self._lock).pack(side="right", padx=(0, 8))

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=14, pady=6)

        self.autostart = ctk.CTkSwitch(self, text="Lancer au démarrage de Windows",
                                       command=self._toggle_autostart)
        self.autostart.pack(anchor="w", padx=18, pady=(6, 4))
        if startup.is_enabled():
            self.autostart.select()

        self.remember_switch = ctk.CTkSwitch(self, text="Ne pas redemander le mot de passe sur ce PC",
                                             command=self._toggle_remember)
        self.remember_switch.pack(anchor="w", padx=18, pady=(0, 4))
        if remember.is_enabled():
            self.remember_switch.select()

        self.status = ctk.CTkLabel(self, text="", text_color="gray70", anchor="w")
        self.status.pack(fill="x", padx=18, pady=(0, 12))
        self._render()

    def _render(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()

        if not self.vault.accounts:
            ctk.CTkLabel(self.list_frame, text="Aucun compte pour l'instant.\nClique sur « + Ajouter ».",
                         text_color="gray60").pack(pady=40)
            return

        for account in self.vault.accounts:
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x", pady=5)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=12, pady=8)
            ctk.CTkLabel(info, text=account.label, font=ctk.CTkFont(size=15, weight="bold"), anchor="w").pack(fill="x")
            sub = account.username + (f"  ·  {account.note}" if account.note else "")
            ctk.CTkLabel(info, text=sub, text_color="gray65", anchor="w").pack(fill="x")

            ctk.CTkButton(row, text="🗑", width=34, fg_color="transparent", hover_color="#5a2a2a",
                          command=lambda a=account: self._delete(a)).pack(side="right", padx=(0, 8))
            ctk.CTkButton(row, text="✎", width=34, fg_color="transparent",
                          command=lambda a=account: self._edit(a)).pack(side="right")
            ctk.CTkButton(row, text="Connexion", width=96,
                          command=lambda a=account: self._connect(a)).pack(side="right", padx=8)

    # ------------------------------------------------------------ actions
    def _toggle_autostart(self) -> None:
        enabled = bool(self.autostart.get())
        try:
            startup.set_enabled(enabled)
            self.status.configure(text="Lancement au démarrage activé ✔" if enabled
                                  else "Lancement au démarrage désactivé")
        except OSError as exc:
            self.status.configure(text=f"⚠ Impossible de modifier le démarrage : {exc}")

    def _toggle_remember(self) -> None:
        try:
            if self.remember_switch.get():
                remember.save(self._master)
                self.status.configure(text="Mot de passe mémorisé sur ce PC ✔")
            else:
                remember.forget()
                self.status.configure(text="Le mot de passe sera redemandé au prochain lancement")
        except OSError as exc:
            self.remember_switch.deselect()
            self.status.configure(text=f"⚠ Impossible de modifier la mémorisation : {exc}")

    def _lock(self) -> None:
        """Verrouille le coffre et oublie le mot de passe mémorisé : il sera redemandé."""
        remember.forget()
        self.vault = Vault()
        self._master = ""
        self._show_unlock(auto=False)

    def _add(self) -> None:
        AccountDialog(self, None, self._saved)

    def _edit(self, account: Account) -> None:
        AccountDialog(self, account, self._saved)

    def _saved(self, account: Account) -> None:
        self.vault.upsert(account)
        self._render()

    def _delete(self, account: Account) -> None:
        if messagebox.askyesno("Supprimer", f"Supprimer le compte « {account.label} » ?"):
            self.vault.delete(account.id)
            self._render()

    def _set_status(self, text: str) -> None:
        self.after(0, lambda: self.status.configure(text=text))

    def _connect(self, account: Account) -> None:
        if self._busy:
            return
        self._busy = True

        def work() -> None:
            try:
                riot.login(account.username, account.password, self._set_status)
                self._set_status(f"Connexion envoyée pour « {account.label} » ✔")
            except riot.RiotError as exc:
                self._set_status(f"⚠ {exc}")
            except Exception as exc:  # erreur inattendue : on l'affiche plutôt que de planter
                self._set_status(f"⚠ Erreur : {exc}")
            finally:
                self._busy = False

        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
