# LoL Account Manager

Gestionnaire local de comptes League of Legends (Windows). Un clic sur un compte
ferme le Riot Client, le relance et saisit l'identifiant et le mot de passe.

## Installation

```
pip install -r requirements.txt
python main.py
```

Au premier lancement, crée un mot de passe maître. Il chiffre tout (AES + scrypt)
et **ne peut pas être récupéré** : si tu l'oublies, il faut recréer le coffre.

## Ne plus retaper le mot de passe maître

À l'ouverture, la case **« Se souvenir sur ce PC »** (cochée par défaut) mémorise le mot de passe maître,
protégé par Windows (DPAPI). Aux lancements suivants, le coffre s'ouvre tout seul.

- Le souvenir n'est lisible que par ton compte Windows, sur ce PC (fichier `%APPDATA%\LolAccountManager\remember.bin`).
- Compromis : quiconque ouvre ta session Windows peut ouvrir l'appli. Pour t'en protéger : bouton **Verrouiller**
  (oublie le souvenir, le mot de passe sera redemandé) ou l'interrupteur « Ne pas redemander le mot de passe sur ce PC ».
- Si le mot de passe mémorisé ne marche plus (coffre recréé, autre session Windows), il est oublié et l'écran de saisie réapparaît.

## Rang et winrate

Chaque carte affiche le rang (Solo/Duo, sinon Flex), les LP et le winrate du compte, avec l'ancienneté de l'information quand elle date.

**Automatique, sans clé API.** Quand tu cliques sur « Connexion » et que le client LoL s'ouvre, l'appli lit dans le client (API locale du client, lecture seule, uniquement sur ton PC) le Riot ID et le rang du compte connecté, puis les enregistre dans le coffre chiffré. Tu n'as rien à saisir. Le rang d'un compte est donc mis à jour à chaque connexion avec lui, et le dernier rang connu reste affiché ensuite.
- Le bouton **Actualiser** lit aussi le client s'il est déjà ouvert, si son Riot ID correspond à un de tes comptes.
- Si le client n'est pas ouvert, il n'y a rien à lire : le dernier rang connu reste affiché.

**Facultatif : clé API Riot.** Pour actualiser tous les rangs sans te connecter, colle une clé de développement gratuite dans **Réglages → Clé API Riot** (sur [developer.riotgames.com](https://developer.riotgames.com), elle commence par `RGAPI-` et expire au bout de 24 h). Il faut alors le **Riot ID** (`Nom#TAG`) et le serveur du compte, qui se remplissent tout seuls à la première connexion. Avec une clé, les rangs se rechargent à l'ouverture, puis toutes les 30 minutes, et avec **Actualiser**.
- Seuls le Riot ID et la clé API sont envoyés à Riot (API officielle). L'identifiant de connexion et le mot de passe ne quittent jamais le PC.
- La clé est enregistrée en clair dans `%APPDATA%\LolAccountManager\settings.json`.

## Utilisation

1. **+ Ajouter** pour enregistrer un compte (nom affiché, identifiant, mot de passe, note).
2. **Connexion** : l'appli ferme le client, le relance et se connecte, puis vérifie que League of Legends s'ouvre (et le relance une fois sinon). Elle ouvre le client LoL, pas une partie : la partie ne démarre que quand tu lances une file.
3. Ne touche ni au clavier ni à la souris pendant la saisie (3 à 5 secondes).

## Réglages si la saisie rate

Dans `riot.py`, fonction `login` :
- `render_delay` (3 s par défaut) : augmente-le si le texte part avant l'affichage du formulaire.
- `key_pause` (0,4 s) : augmente-le sur un PC lent.

Si la saisie se fait au mauvais endroit, c'est que le champ identifiant n'avait pas le focus.
Dans ce cas, dis-le et on ajoutera un clic sur le champ.

## À savoir

- La session « Rester connecté » est supprimée à chaque connexion, sinon le client se
  reconnecterait tout seul au dernier compte. Tu seras donc déconnecté du client à chaque switch.
- La connexion est refusée si une partie est en cours.
- Si un compte a la double authentification, il faudra saisir le code à la main.
- Le presse-papiers est vidé juste après la saisie.
- Le coffre est dans `%APPDATA%\LolAccountManager\vault.bin`. Les identifiants et mots de passe ne sont jamais envoyés sur internet (seul le Riot ID l'est, pour afficher le rang).
- L'appli ne touche jamais au jeu, seulement au client Riot (reste dans ce cadre pour les CGU).

## Faire un .exe (facultatif)

```
pip install pyinstaller
pyinstaller --noconsole --onefile --collect-all customtkinter main.py
```
