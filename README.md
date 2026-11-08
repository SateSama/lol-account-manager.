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
- Compromis : quiconque ouvre ta session Windows peut ouvrir l'appli. Pour t'en protéger : bouton **🔒 Verrouiller**
  (oublie le souvenir, le mot de passe sera redemandé) ou l'interrupteur « Ne pas redemander le mot de passe sur ce PC ».
- Si le mot de passe mémorisé ne marche plus (coffre recréé, autre session Windows), il est oublié et l'écran de saisie réapparaît.

## Rang et winrate

Chaque compte peut afficher son rang (Solo/Duo, sinon Flex), ses LP et son winrate.

1. Clique sur **🔑 Clé API Riot** et colle ta clé de développement (gratuite sur [developer.riotgames.com](https://developer.riotgames.com), elle commence par `RGAPI-`). Elle expire au bout de 24 h : recolle-la quand l'appli affiche « Clé API refusée ou expirée ».
2. Dans **+ Ajouter** ou **✎**, remplis **Riot ID** (`Nom#TAG`) et choisis le **serveur**. Ce n'est pas l'identifiant de connexion.
3. Les rangs se chargent à l'ouverture. Le bouton **↻** les actualise.

Seuls le Riot ID et la clé API sont envoyés à Riot (API officielle). L'identifiant de connexion et le mot de passe ne quittent jamais le PC.
La clé est enregistrée en clair dans `%APPDATA%\LolAccountManager\settings.json`.

## Utilisation

1. **+ Ajouter** pour enregistrer un compte (nom affiché, identifiant, mot de passe, note).
2. **Connexion** : l'appli ferme le client, le relance et se connecte.
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
