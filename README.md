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
- Rien n'est envoyé sur internet : le coffre est dans `%APPDATA%\LolAccountManager\vault.bin`.
- L'appli ne touche jamais au jeu, seulement au client Riot (reste dans ce cadre pour les CGU).

## Faire un .exe (facultatif)

```
pip install pyinstaller
pyinstaller --noconsole --onefile --collect-all customtkinter main.py
```
