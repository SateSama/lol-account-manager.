"""LoL Account Manager : interface principale."""
from __future__ import annotations

import queue
import threading
import tkinter
import tkinter.messagebox as messagebox

import customtkinter as ctk

import lcu
import remember
import riot
import startup
import stats
import theme
from vault import Account, Vault, WrongPassword

AUTO_REFRESH_MS = 30 * 60 * 1000  # actualisation automatique des rangs : toutes les 30 minutes

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
try:  # police native de Windows pour tous les widgets (sinon customtkinter utilise Roboto)
    ctk.ThemeManager.theme["CTkFont"]["Windows"]["family"] = theme.FONT
except (KeyError, AttributeError, TypeError):
    pass


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(size=size, weight=weight)


# ---------------------------------------------------------------- petits widgets stylés
def primary_button(parent, text: str, command, width: int = 96, **kwargs) -> ctk.CTkButton:
    """Bouton clair (action principale)."""
    kwargs.setdefault("height", 34)
    return ctk.CTkButton(parent, text=text, command=command, width=width, corner_radius=8,
                         fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                         text_color=theme.ON_ACCENT, font=font(13, "bold"), **kwargs)


def ghost_button(parent, text: str, command, width: int = 100, **kwargs) -> ctk.CTkButton:
    """Bouton discret avec bordure (action secondaire)."""
    kwargs.setdefault("height", 34)
    return ctk.CTkButton(parent, text=text, command=command, width=width, corner_radius=8,
                         fg_color="transparent", hover_color=theme.CARD_HOVER,
                         border_width=1, border_color=theme.BORDER, text_color=theme.TEXT, **kwargs)


def icon_button(parent, text: str, command, hover: str = theme.CARD_HOVER) -> ctk.CTkButton:
    return ctk.CTkButton(parent, text=text, command=command, width=32, height=32, corner_radius=8,
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
        self.riot_id = self._field("Riot ID (Nom#TAG) : rempli tout seul à la 1re connexion", account.riot_id if account else "")

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
        self.geometry("420x330")
        self.resizable(False, False)
        self.transient(parent)
        self.after(150, self.grab_set)
        self._on_save = on_save

        ctk.CTkLabel(
            self, justify="left", anchor="w", text_color=theme.MUTED, wraplength=370,
            text="Facultatif. Le rang d'un compte est déjà lu automatiquement dans le client LoL quand tu "
                 "te connectes avec lui. Avec une clé API Riot gratuite, l'appli peut aussi actualiser "
                 "tous les rangs sans que tu te connectes :\n"
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


class SettingsDialog(ctk.CTkToplevel):
    """Réglages : démarrage avec Windows, mot de passe mémorisé, clé API Riot."""

    def __init__(self, app: "App") -> None:
        super().__init__(app, fg_color=theme.BG)
        self.title("Réglages")
        self.geometry("440x380")
        self.resizable(False, False)
        self.transient(app)
        self.after(150, self.grab_set)

        ctk.CTkLabel(self, text="Réglages", text_color=theme.TEXT, font=font(18, "bold"),
                     anchor="w").pack(fill="x", padx=24, pady=(22, 12))

        # les interrupteurs sont gardés sur l'appli : ses méthodes _toggle_* les lisent
        app.autostart = switch(self, "Lancer au démarrage de Windows", app._toggle_autostart)
        app.autostart.pack(anchor="w", padx=24, pady=6)
        if startup.is_enabled():
            app.autostart.select()
        app.remember_switch = switch(self, "Ne pas redemander le mot de passe sur ce PC", app._toggle_remember)
        app.remember_switch.pack(anchor="w", padx=24, pady=6)
        if remember.is_enabled():
            app.remember_switch.select()

        ctk.CTkFrame(self, height=1, fg_color=theme.BORDER).pack(fill="x", padx=24, pady=(16, 14))
        ctk.CTkLabel(self, text="Rang et winrate", text_color=theme.TEXT, font=font(14, "bold"),
                     anchor="w").pack(fill="x", padx=24)
        ctk.CTkLabel(
            self, justify="left", anchor="w", text_color=theme.MUTED, wraplength=390, font=font(12),
            text="Le rang est lu automatiquement dans le client LoL quand tu te connectes avec un compte. "
                 "Une clé API Riot (facultatif) permet d'actualiser tous les rangs sans te connecter.",
        ).pack(fill="x", padx=24, pady=(4, 10))
        ghost_button(self, "Clé API Riot…", app._ask_key, width=140).pack(anchor="w", padx=24)

        primary_button(self, "Fermer", self.destroy, width=110).pack(side="bottom", anchor="e", padx=24, pady=20)


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__(fg_color=theme.BG)
        self.title("LoL Account Manager")
        self.geometry("580x660")
        self.minsize(540, 440)
        self.vault = Vault()
        self._master = ""
        self._busy = False
        self._refreshing = False
        self._events: queue.Queue = queue.Queue()  # messages des threads de fond (ils n'appellent jamais Tk)
        self._lcu_gen = 0    # numéro de la lecture du client LoL en cours (pour annuler les anciennes)
        self._auto_gen = 0   # idem pour l'actualisation automatique
        self._ranks: dict[str, tuple[str, str]] = {}   # id du compte -> (texte, couleur) du rang
        self._rank_labels: dict[str, ctk.CTkLabel] = {}
        self.after(150, self._pump)
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
        box = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=14,
                           border_width=1, border_color=theme.BORDER)
        box.place(relx=0.5, rely=0.45, anchor="center")
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(padx=36, pady=30)

        ctk.CTkLabel(inner, text="LoL Account Manager", text_color=theme.TEXT,
                     font=font(22, "bold")).pack(pady=(0, 6))
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
        ctk.CTkLabel(header, text="Comptes", text_color=theme.TEXT,
                     font=font(20, "bold")).pack(side="left")
        primary_button(header, "+ Ajouter", self._add, width=86).pack(side="right")
        ghost_button(header, "Verrouiller", self._lock, width=92).pack(side="right", padx=(0, 8))
        ghost_button(header, "Réglages", self._open_settings, width=84).pack(side="right", padx=(0, 8))
        ghost_button(header, "Actualiser", self._refresh_ranks, width=84).pack(side="right", padx=(0, 8))

        ctk.CTkFrame(self, height=1, fg_color=theme.BORDER).pack(fill="x", padx=18)

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                                 scrollbar_button_color=theme.BORDER,
                                                 scrollbar_button_hover_color=theme.MUTED)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=8)

        self.status = ctk.CTkLabel(self, text="", text_color=theme.MUTED, anchor="w", justify="left", wraplength=480, font=font(12))
        self.status.pack(fill="x", padx=20, pady=(0, 14))
        self._render()
        self._refresh_ranks(manual=False)
        self._schedule_auto_refresh()

    def _render(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._rank_labels = {}

        if not self.vault.accounts:
            ctk.CTkLabel(self.list_frame, text="Aucun compte pour l'instant.\nClique sur « + Ajouter ».",
                         text_color=theme.MUTED).pack(pady=40)
            return

        for account in self.vault.accounts:
            row = ctk.CTkFrame(self.list_frame, fg_color=theme.CARD, corner_radius=10,
                               border_width=1, border_color=theme.BORDER)
            row.pack(fill="x", padx=4, pady=5)

            # pastille discrète avec l'initiale du compte
            avatar = ctk.CTkFrame(row, width=40, height=40, corner_radius=10, fg_color=theme.AVATAR)
            avatar.pack(side="left", padx=(14, 0), pady=12)
            avatar.pack_propagate(False)
            ctk.CTkLabel(avatar, text=theme.initial(account.label), text_color=theme.MUTED,
                         font=font(16, "bold")).place(relx=0.5, rely=0.5, anchor="center")

            # les boutons sont placés avant le texte : si le rang est long, c'est le texte qui est rogné, pas les boutons
            icon_button(row, "✕", lambda a=account: self._delete(a), hover=theme.DANGER_HOVER).pack(side="right", padx=(0, 10))
            icon_button(row, "✎", lambda a=account: self._edit(a)).pack(side="right")
            primary_button(row, "Connexion", lambda a=account: self._connect(a), width=92, height=32).pack(side="right", padx=8)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=12, pady=8)
            ctk.CTkLabel(info, text=account.label, text_color=theme.TEXT,
                         font=font(14, "bold"), anchor="w").pack(fill="x")
            sub = account.username + (f"  ·  {account.note}" if account.note else "")
            ctk.CTkLabel(info, text=sub, text_color=theme.MUTED, anchor="w", font=font(12)).pack(fill="x")
            rank_label = ctk.CTkLabel(info, text="", anchor="w", justify="left", wraplength=120,
                                       font=font(12, "bold"))
            rank_label.pack(fill="x", pady=(2, 0))
            # le texte passe à la ligne selon la place disponible : il ne pousse jamais les boutons hors de la carte
            info.bind("<Configure>", lambda e, lbl=rank_label: lbl.configure(wraplength=max(e.width - 8, 80)), add="+")
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
        try:
            self.status.configure(text=text, text_color=color)
        except (tkinter.TclError, AttributeError):
            pass  # l'écran a changé (coffre verrouillé) : le message n'a plus de place où s'afficher

    def _rank_display(self, account: Account) -> tuple[str, str]:
        """Texte et couleur du rang d'une carte : état en cours, sinon dernier rang connu."""
        session = self._ranks.get(account.id)
        if session and not (session[0].startswith("⚠") and account.rank):
            return session  # chargement, « Non classé »... (une erreur ne cache pas le dernier rang connu)
        if account.rank:
            try:
                info = stats.RankInfo.from_dict(account.rank)
            except (KeyError, ValueError, TypeError):
                info = None
            if info is not None:
                age = stats.age_text(account.rank.get("updated"))
                text = f"{info.rank_text()}\n{info.winrate_text()}" + (f" · {age}" if age else "")
                return text, theme.TIER_COLORS.get(info.tier, theme.TEXT)
        if account.riot_id:
            return "Rang : clique sur Actualiser ou connecte-toi avec ce compte", theme.MUTED
        return "Rang : connecte-toi une fois avec ce compte", theme.MUTED

    def _apply_rank(self, account: Account) -> None:
        """Écrit le rang du compte dans sa carte."""
        label = self._rank_labels.get(account.id)
        if label is None:
            return
        text, color = self._rank_display(account)
        try:
            label.configure(text=text, text_color=color)
        except (tkinter.TclError, AttributeError):
            pass  # la carte a été recréée entre-temps

    def _find_account(self, account_id: str) -> Account | None:
        return next((a for a in self.vault.accounts if a.id == account_id), None)

    def _refresh_card(self, account_id: str) -> None:
        account = self._find_account(account_id)
        if account is not None:
            self._apply_rank(account)

    def _store_rank(self, account_id: str, info: stats.RankInfo | None, riot_id: str = "") -> None:
        """Enregistre dans le coffre le dernier rang connu (et le Riot ID s'il vient d'être lu)."""
        account = self._find_account(account_id)
        if account is None:
            return  # coffre verrouillé ou compte supprimé entre-temps
        if riot_id:
            account.riot_id = riot_id
        if info is not None:
            account.rank = info.to_dict()
            self._ranks.pop(account_id, None)
        else:
            account.rank = {}
            self._ranks[account_id] = ("Non classé", theme.MUTED)
        try:
            self.vault.save()
        except OSError as exc:
            self._show_status(f"⚠ Impossible d'enregistrer le rang : {exc}")
        self._apply_rank(account)

    # ------------------------------------------------------------ threads de fond
    def _put(self, *event) -> None:
        """Dépose un message depuis un thread de fond ; la fenêtre le traite dans _pump."""
        self._events.put(event)

    def _pump(self) -> None:
        """Côté fenêtre : traite ce que les threads de fond ont déposé."""
        try:
            while True:
                try:
                    event = self._events.get_nowait()
                except queue.Empty:
                    break
                try:
                    self._handle(event)
                except Exception as exc:  # un message mal formé ne doit pas bloquer les suivants
                    self._show_status(f"⚠ Erreur : {exc}")
        finally:
            self.after(150, self._pump)

    def _handle(self, event: tuple) -> None:
        kind = event[0]
        if kind == "status":
            self._show_status(event[1])
        elif kind == "done":
            self._refreshing = False
        elif kind == "rank":  # chargement, erreur : ("rank", id, texte, couleur)
            _kind, account_id, text, color = event
            self._ranks[account_id] = (text, color)
            self._refresh_card(account_id)
        elif kind == "known":  # rang reçu de l'API Riot : ("known", id, rang ou None)
            self._store_rank(event[1], event[2])
        elif kind == "lcu":  # compte lu dans le client juste après une connexion : ("lcu", id, riot_id, rang)
            self._store_rank(event[1], event[3], riot_id=event[2])
            self._show_status("Riot ID et rang lus dans le client LoL ✔")
        elif kind == "client":  # client déjà ouvert : ("client", riot_id, rang, manuel)
            _kind, riot_id, info, manual = event
            match = next((a for a in self.vault.accounts if a.riot_id.casefold() == riot_id.casefold()), None)
            if match is not None:
                self._store_rank(match.id, info)
                if manual:
                    self._show_status(f"Rang de « {match.label} » lu dans le client LoL ✔")
            elif manual:
                self._show_status(f"Le client LoL est connecté avec {riot_id}, un compte que je ne connais pas "
                                  "encore : connecte-toi avec l'appli ou ajoute ce Riot ID en modifiant un compte.")

    def _read_client_once(self, manual: bool) -> None:
        """Si le client LoL est ouvert, lit son compte et son rang (sans clé API)."""
        conn = lcu.find_connection()
        if conn is None:
            if manual:
                self._put("status", "Client LoL fermé : le rang se lit quand tu te connectes avec l'appli.")
            return
        try:
            riot_id = lcu.read_riot_id(conn)
            info = lcu.read_rank(conn)
        except lcu.LcuError:
            if manual:
                self._put("status", "Le client LoL n'est pas encore connecté.")
            return
        self._put("client", riot_id, info, manual)

    def _watch_client(self, account_id: str, before: lcu.Connection | None, gen: int) -> None:
        """Après une connexion : attend que le client LoL s'ouvre, puis lit le compte et son rang."""
        found = lcu.wait_for_account(before, cancel=lambda: gen != self._lcu_gen)
        if found is not None and gen == self._lcu_gen:
            self._put("lcu", account_id, found[0], found[1])

    def _fetch_all(self, accounts: list[Account], key: str) -> None:
        fatal = ""  # erreur qui rend inutile d'interroger les comptes suivants (clé refusée, limite...)
        try:
            for account in accounts:
                if fatal:
                    self._put("rank", account.id, f"⚠ {fatal}", theme.DANGER)
                    continue
                try:
                    info = stats.fetch_rank(account.riot_id, account.region, key)
                except stats.StatsError as exc:
                    self._put("rank", account.id, f"⚠ {exc}", theme.DANGER)
                    if exc.fatal:
                        fatal = str(exc)
                except Exception as exc:  # erreur inattendue : on l'affiche plutôt que de planter
                    self._put("rank", account.id, f"⚠ Erreur : {exc}", theme.DANGER)
                else:
                    self._put("known", account.id, info)
            if fatal:  # message d'aide en bas de la fenêtre, avec la marche à suivre
                hint = ("régénère-la sur developer.riotgames.com puis colle-la dans Réglages → Clé API Riot"
                        if "Clé API" in fatal else "réessaie dans une minute avec Actualiser")
                self._put("status", f"⚠ {fatal} : {hint}")
        finally:
            self._put("done")

    # ------------------------------------------------------------ rangs
    def _open_settings(self) -> None:
        SettingsDialog(self)

    def _ask_key(self) -> None:
        KeyDialog(self, self._refresh_ranks)

    def _refresh_ranks(self, manual: bool = True) -> None:
        """Met les rangs à jour : lecture du client LoL s'il est ouvert, puis API Riot si une clé est enregistrée."""
        threading.Thread(target=self._read_client_once, args=(manual,), daemon=True).start()
        key = stats.load_key()
        if not key:
            if manual:
                self._show_status("Pas de clé API : le rang se met à jour à chaque connexion depuis l'appli.")
            return
        accounts = [a for a in self.vault.accounts if a.riot_id]
        if self._refreshing or not accounts:
            return
        self._refreshing = True
        for account in accounts:
            if not account.rank:  # sinon le dernier rang connu reste affiché pendant le chargement
                self._ranks[account.id] = ("Chargement du rang…", theme.MUTED)
            self._apply_rank(account)
        threading.Thread(target=self._fetch_all, args=(accounts, key), daemon=True).start()

    def _schedule_auto_refresh(self) -> None:
        """Actualise les rangs toutes les 30 minutes tant que l'écran des comptes est ouvert."""
        self._auto_gen += 1
        gen = self._auto_gen

        def tick() -> None:
            if gen != self._auto_gen:
                return  # coffre verrouillé ou écran rechargé : cette boucle est périmée
            self._refresh_ranks(manual=False)
            self.after(AUTO_REFRESH_MS, tick)

        self.after(AUTO_REFRESH_MS, tick)

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
        self._lcu_gen += 1   # annule une lecture du client LoL en attente
        self._auto_gen += 1  # arrête l'actualisation automatique
        self._show_unlock(auto=False)

    def _add(self) -> None:
        AccountDialog(self, None, self._saved)

    def _edit(self, account: Account) -> None:
        AccountDialog(self, account, self._saved)

    def _saved(self, account: Account) -> None:
        self.vault.upsert(account)
        self._ranks.pop(account.id, None)  # le Riot ID a peut-être changé : on recharge
        self._render()
        self._refresh_ranks(manual=False)

    def _delete(self, account: Account) -> None:
        if messagebox.askyesno("Supprimer", f"Supprimer le compte « {account.label} » ?"):
            self.vault.delete(account.id)
            self._render()

    def _set_status(self, text: str) -> None:
        self._put("status", text)  # appelé depuis un thread de fond

    def _connect(self, account: Account) -> None:
        if self._busy:
            return
        self._busy = True
        self._lcu_gen += 1  # une nouvelle connexion annule la lecture du compte précédent
        gen = self._lcu_gen

        def work() -> None:
            logged_in = False
            before = None
            try:
                before = lcu.find_connection()  # client LoL ouvert avant le changement : on l'ignorera ensuite
                riot.login(account.username, account.password, self._set_status)
                self._set_status(f"Connexion envoyée pour « {account.label} » ✔")
                logged_in = True
                if riot.ensure_league_launched(self._set_status):
                    self._set_status(f"League of Legends lancé avec « {account.label} » ✔")
                else:
                    self._set_status("⚠ Le client LoL ne s'est pas ouvert : vérifie le code de double authentification, "
                                     "ou lance-le depuis le Riot Client.")
            except riot.RiotError as exc:
                self._set_status(f"⚠ {exc}")
            except Exception as exc:  # erreur inattendue : on l'affiche plutôt que de planter
                self._set_status(f"⚠ Erreur : {exc}")
            finally:
                self._busy = False
            if logged_in:  # lit le Riot ID et le rang quand le client LoL est ouvert (jusqu'à 5 minutes d'attente)
                self._watch_client(account.id, before, gen)

        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
