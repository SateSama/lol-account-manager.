"""LoL Account Manager : interface principale."""
from __future__ import annotations

import queue
import threading
import tkinter
import tkinter.messagebox as messagebox

import customtkinter as ctk

import remember
import riot
import startup
import stats
import theme
from vault import Account, Vault, WrongPassword

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ---------------------------------------------------------------- petits widgets stylés
def primary_button(parent, text: str, command, width: int = 96, **kwargs) -> ctk.CTkButton:
    """Bouton doré (action principale)."""
    return ctk.CTkButton(parent, text=text, command=command, width=width, corner_radius=8,
                         fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                         text_color=theme.ON_ACCENT, font=ctk.CTkFont(weight="bold"), **kwargs)


def ghost_button(parent, text: str, command, width: int = 100, **kwargs) -> ctk.CTkButton:
    """Bouton discret avec bordure (action secondaire)."""
    return ctk.CTkButton(parent, text=text, command=command, width=width, corner_radius=8,
                         fg_color="transparent", hover_color=theme.CARD_HOVER,
                         border_width=1, border_color=theme.BORDER, text_color=theme.TEXT, **kwargs)


def icon_button(parent, text: str, command, hover: str = theme.CARD_HOVER) -> ctk.CTkButton:
    return ctk.CTkButton(parent, text=text, command=command, width=34, corner_radius=8,
                         fg_color="transparent", hover_color=hover, text_color=theme.MUTED)


def entry(parent, **kwargs) -> ctk.CTkEntry:
    return ctk.CTkEntry(parent, fg_color=theme.FIELD, border_color=theme.BORDER,
                        text_color=theme.TEXT, placeholder_text_color=theme.MUTED,
                        corner_radius=8, height=36, **kwargs)


def switch(parent, text: str, command) -> ctk.CTkSwitch:
    return ctk.CTkSwitch(parent, text=text, command=command, text_color=theme.MUTED,
                         progress_color=theme.ACCENT, button_color=theme.TEXT,
                         button_hover_color=theme.ACCENT_HOVER, fg_color=theme.BORDER)


class AccountDialog(ctk.CTkToplevel):
    """Fenêtre d'ajout / modification d'un compte."""

    def __init__(self, parent: ctk.CTk, account: Account | None, on_save) -> None:
        super().__init__(parent, fg_color=theme.BG)
        self.title("Modifier le compte" if account else "Nouveau compte")
        self.geometry("360x600")
        self.resizable(False, False)
        self.transient(parent)
        self.after(150, self.grab_set)

        self._account = account
        self._on_save = on_save

        self.label = self._field("Nom affiché (ex : Main, Smurf)", account.label if account else "")
        self.username = self._field("Identifiant Riot", account.username if account else "")
        self.password = self._field("Mot de passe", account.password if account else "", secret=True)
        self.note = self._field("Note (facultatif)", account.note if account else "")
        self.riot_id = self._field("Riot ID pour le rang (Nom#TAG, facultatif)", account.riot_id if account else "")

        ctk.CTkLabel(self, text="Serveur", anchor="w", text_color=theme.MUTED).pack(fill="x", padx=24, pady=(14, 2))
        self.region = ctk.CTkOptionMenu(
            self, values=list(stats.REGIONS), fg_color=theme.FIELD, button_color=theme.BORDER,
            button_hover_color=theme.CARD_HOVER, text_color=theme.TEXT, dropdown_fg_color=theme.CARD,
            dropdown_text_color=theme.TEXT, dropdown_hover_color=theme.CARD_HOVER, corner_radius=8, height=36)
        self.region.set(account.region if account and account.region in stats.REGIONS else stats.DEFAULT_REGION)
        self.region.pack(fill="x", padx=24)

        primary_button(self, "Enregistrer", self._save, width=200, height=38).pack(pady=20)
        self.bind("<Return>", lambda _e: self._save())

    def _field(self, title: str, value: str, secret: bool = False) -> ctk.CTkEntry:
        ctk.CTkLabel(self, text=title, anchor="w", text_color=theme.MUTED).pack(fill="x", padx=24, pady=(14, 2))
        field = entry(self, show="•" if secret else "")
        field.pack(fill="x", padx=24)
        field.insert(0, value)
        return field

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
        account.riot_id = self.riot_id.get().strip()
        account.region = self.region.get()
        self._on_save(account)
        self.destroy()


class KeyDialog(ctk.CTkToplevel):
    """Fenêtre pour coller sa clé API Riot (nécessaire au rang et au winrate)."""

    def __init__(self, parent: ctk.CTk, on_save) -> None:
        super().__init__(parent, fg_color=theme.BG)
        self.title("Clé API Riot")
        self.geometry("420x290")
        self.resizable(False, False)
        self.transient(parent)
        self.after(150, self.grab_set)
        self._on_save = on_save

        ctk.CTkLabel(
            self, justify="left", anchor="w", text_color=theme.MUTED, wraplength=370,
            text="Pour afficher le rang et le winrate, il faut une clé API Riot gratuite :\n"
                 "1. Va sur developer.riotgames.com et connecte-toi avec ton compte Riot.\n"
                 "2. Copie la « Development API Key » (commence par RGAPI-).\n"
                 "Elle expire au bout de 24 h : recolle-la quand l'appli le demande.",
        ).pack(fill="x", padx=24, pady=(20, 10))
        self.key = entry(self, show="•")
        self.key.pack(fill="x", padx=24)
        self.key.insert(0, stats.load_key())
        primary_button(self, "Enregistrer", self._save, width=200, height=38).pack(pady=20)
        self.bind("<Return>", lambda _e: self._save())

    def _save(self) -> None:
        key = self.key.get().strip()
        if not key:
            messagebox.showwarning("Clé manquante", "Colle ta clé API Riot.", parent=self)
            return
        try:
            stats.save_key(key)
        except OSError as exc:
            messagebox.showerror("Erreur", f"Impossible d'enregistrer la clé : {exc}", parent=self)
            return
        self._on_save()
        self.destroy()


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__(fg_color=theme.BG)
        self.title("LoL Account Manager")
        self.geometry("520x640")
        self.minsize(460, 420)
        self.vault = Vault()
        self._master = ""
        self._busy = False
        self._refreshing = False
        self._ranks: dict[str, tuple[str, str]] = {}   # id du compte -> (texte, couleur) du rang
        self._rank_labels: dict[str, ctk.CTkLabel] = {}
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
        box = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=16,
                           border_width=1, border_color=theme.BORDER)
        box.place(relx=0.5, rely=0.45, anchor="center")
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(padx=36, pady=30)

        ctk.CTkLabel(inner, text="LoL Account Manager", text_color=theme.ACCENT,
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(0, 6))
        ctk.CTkLabel(
            inner,
            text="Crée ton mot de passe maître.\nIl chiffre tous tes comptes et ne peut pas être récupéré."
            if creating else "Entre ton mot de passe maître.",
            text_color=theme.MUTED,
        ).pack(pady=(0, 18))

        pw = entry(inner, placeholder_text="Mot de passe maître", show="•", width=260)
        pw.pack(pady=4)
        pw.focus()
        confirm = None
        if creating:
            confirm = entry(inner, placeholder_text="Confirmer", show="•", width=260)
            confirm.pack(pady=4)

        remember_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(inner, text="Se souvenir sur ce PC", variable=remember_var,
                        text_color=theme.MUTED, fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                        checkmark_color=theme.ON_ACCENT, border_color=theme.BORDER).pack(pady=(8, 0))

        error = ctk.CTkLabel(inner, text="", text_color=theme.DANGER)
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

        primary_button(inner, "Créer le coffre" if creating else "Déverrouiller", submit,
                       width=260, height=38).pack(pady=6)
        self.bind("<Return>", submit)

    # ------------------------------------------------------------ écran principal
    def _show_main(self) -> None:
        self._clear()
        self.unbind("<Return>")

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(18, 10))
        ctk.CTkLabel(header, text="Mes comptes", text_color=theme.TEXT,
                     font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        primary_button(header, "+ Ajouter", self._add, width=90).pack(side="right")
        ghost_button(header, "🔒 Verrouiller", self._lock).pack(side="right", padx=(0, 8))
        ghost_button(header, "↻", self._refresh_ranks, width=36).pack(side="right", padx=(0, 8))

        ctk.CTkFrame(self, height=1, fg_color=theme.BORDER).pack(fill="x", padx=18)

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                                 scrollbar_button_color=theme.BORDER,
                                                 scrollbar_button_hover_color=theme.MUTED)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=8)

        self.autostart = switch(self, "Lancer au démarrage de Windows", self._toggle_autostart)
        self.autostart.pack(anchor="w", padx=18, pady=(6, 6))
        if startup.is_enabled():
            self.autostart.select()

        self.remember_switch = switch(self, "Ne pas redemander le mot de passe sur ce PC", self._toggle_remember)
        self.remember_switch.pack(anchor="w", padx=18, pady=(0, 6))
        if remember.is_enabled():
            self.remember_switch.select()

        ghost_button(self, "🔑 Clé API Riot (rang et winrate)", self._ask_key, width=230, height=28).pack(
            anchor="w", padx=18, pady=(2, 6))

        self.status = ctk.CTkLabel(self, text="", text_color=theme.MUTED, anchor="w")
        self.status.pack(fill="x", padx=18, pady=(0, 14))
        self._render()
        if stats.load_key():
            self._refresh_ranks()

    def _render(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._rank_labels = {}

        if not self.vault.accounts:
            ctk.CTkLabel(self.list_frame, text="Aucun compte pour l'instant.\nClique sur « + Ajouter ».",
                         text_color=theme.MUTED).pack(pady=40)
            return

        for account in self.vault.accounts:
            row = ctk.CTkFrame(self.list_frame, fg_color=theme.CARD, corner_radius=12,
                               border_width=1, border_color=theme.BORDER)
            row.pack(fill="x", padx=4, pady=5)

            # pastille ronde avec l'initiale du compte
            avatar = ctk.CTkFrame(row, width=42, height=42, corner_radius=21,
                                  fg_color=theme.avatar_color(account.id))
            avatar.pack(side="left", padx=(12, 0), pady=10)
            avatar.pack_propagate(False)
            ctk.CTkLabel(avatar, text=theme.initial(account.label), text_color="white",
                         font=ctk.CTkFont(size=18, weight="bold")).place(relx=0.5, rely=0.5, anchor="center")

            # les boutons sont placés avant le texte : si le rang est long, c'est le texte qui est rogné, pas les boutons
            icon_button(row, "🗑", lambda a=account: self._delete(a), hover=theme.DANGER_HOVER).pack(side="right", padx=(0, 8))
            icon_button(row, "✎", lambda a=account: self._edit(a)).pack(side="right")
            primary_button(row, "Connexion", lambda a=account: self._connect(a), width=96).pack(side="right", padx=8)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=12, pady=8)
            ctk.CTkLabel(info, text=account.label, text_color=theme.TEXT,
                         font=ctk.CTkFont(size=15, weight="bold"), anchor="w").pack(fill="x")
            sub = account.username + (f"  ·  {account.note}" if account.note else "")
            ctk.CTkLabel(info, text=sub, text_color=theme.MUTED, anchor="w").pack(fill="x")
            rank_label = ctk.CTkLabel(info, text="", anchor="w", justify="left", wraplength=230,
                                       font=ctk.CTkFont(size=12, weight="bold"))
            rank_label.pack(fill="x")
            self._rank_labels[account.id] = rank_label
            self._apply_rank(account)


    # ------------------------------------------------------------ actions
    def _show_status(self, text: str) -> None:
        """Affiche un message d'état : rouge pour une erreur (⚠), vert pour un succès (✔), gris sinon."""
        if text.startswith("⚠"):
            color = theme.DANGER
        elif "✔" in text:
            color = theme.OK
        else:
            color = theme.MUTED
        self.status.configure(text=text, text_color=color)

    def _apply_rank(self, account: Account) -> None:
        """Écrit le rang du compte dans sa carte (texte mis en cache, couleur du palier)."""
        label = self._rank_labels.get(account.id)
        if label is None:
            return
        if not account.riot_id:
            text, color = "Ajoute le Riot ID (✎) pour voir le rang", theme.MUTED
        else:
            text, color = self._ranks.get(account.id, ("Rang : clique sur ↻ pour actualiser", theme.MUTED))
        try:
            label.configure(text=text, text_color=color)
        except (tkinter.TclError, AttributeError):
            pass  # la carte a été recréée entre-temps

    def _ask_key(self) -> None:
        KeyDialog(self, self._refresh_ranks)

    def _refresh_ranks(self) -> None:
        """Récupère le rang et le winrate de chaque compte qui a un Riot ID (en arrière-plan)."""
        key = stats.load_key()
        if not key:
            self._show_status("⚠ Ajoute ta clé API Riot (bouton 🔑) pour voir le rang")
            return
        accounts = [a for a in self.vault.accounts if a.riot_id]
        if self._refreshing or not accounts:
            return
        self._refreshing = True
        for account in accounts:
            self._ranks[account.id] = ("Chargement du rang…", theme.MUTED)
            self._apply_rank(account)

        results: queue.Queue = queue.Queue()  # le thread de fond n'appelle jamais Tk : il dépose ici

        def work() -> None:
            fatal = ""  # erreur qui rend inutile d'interroger les comptes suivants (clé refusée, limite...)
            try:
                for account in accounts:
                    if fatal:
                        result = (f"⚠ {fatal}", theme.DANGER)
                    else:
                        try:
                            info = stats.fetch_rank(account.riot_id, account.region, key)
                        except stats.StatsError as exc:
                            result = (f"⚠ {exc}", theme.DANGER)
                            if exc.fatal:
                                fatal = str(exc)
                        except Exception as exc:  # erreur inattendue : on l'affiche plutôt que de planter
                            result = (f"⚠ Erreur : {exc}", theme.DANGER)
                        else:
                            if info is None:
                                result = ("Non classé", theme.MUTED)
                            else:
                                result = (f"{info.rank_text()}\n{info.winrate_text()}",
                                          theme.TIER_COLORS.get(info.tier, theme.TEXT))
                    results.put((account, result))
            finally:
                results.put(None)  # fin du travail

        def poll() -> None:
            """Côté fenêtre : affiche les rangs au fur et à mesure qu'ils arrivent."""
            while True:
                try:
                    item = results.get_nowait()
                except queue.Empty:
                    self.after(100, poll)
                    return
                if item is None:
                    self._refreshing = False
                    return
                account, result = item
                self._ranks[account.id] = result
                self._apply_rank(account)

        threading.Thread(target=work, daemon=True).start()
        poll()

    def _toggle_autostart(self) -> None:
        enabled = bool(self.autostart.get())
        try:
            startup.set_enabled(enabled)
            self._show_status("Lancement au démarrage activé ✔" if enabled
                              else "Lancement au démarrage désactivé")
        except OSError as exc:
            self._show_status(f"⚠ Impossible de modifier le démarrage : {exc}")

    def _toggle_remember(self) -> None:
        try:
            if self.remember_switch.get():
                remember.save(self._master)
                self._show_status("Mot de passe mémorisé sur ce PC ✔")
            else:
                remember.forget()
                self._show_status("Le mot de passe sera redemandé au prochain lancement")
        except OSError as exc:
            self.remember_switch.deselect()
            self._show_status(f"⚠ Impossible de modifier la mémorisation : {exc}")

    def _lock(self) -> None:
        """Verrouille le coffre et oublie le mot de passe mémorisé : il sera redemandé."""
        remember.forget()
        self.vault = Vault()
        self._master = ""
        self._ranks = {}
        self._show_unlock(auto=False)

    def _add(self) -> None:
        AccountDialog(self, None, self._saved)

    def _edit(self, account: Account) -> None:
        AccountDialog(self, account, self._saved)

    def _saved(self, account: Account) -> None:
        self.vault.upsert(account)
        self._ranks.pop(account.id, None)  # le Riot ID a peut-être changé : on recharge
        self._render()
        if stats.load_key():
            self._refresh_ranks()

    def _delete(self, account: Account) -> None:
        if messagebox.askyesno("Supprimer", f"Supprimer le compte « {account.label} » ?"):
            self.vault.delete(account.id)
            self._render()

    def _set_status(self, text: str) -> None:
        self.after(0, lambda: self._show_status(text))

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
