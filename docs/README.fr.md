# TTL-LAMa CLI

[English](../README.md) | Français

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](../../LICENSE)
[![Typer](https://img.shields.io/badge/CLI-Typer-009688)](https://typer.tiangolo.com/)

[![Logo](./img/logo_300ppp.png)](./img/logo_300ppp.png)

`ttlama` est l’interface en ligne de commande du projet TTL-LAMa (Time-to-Live Lease Administration Manager). Elle a vocation à permettre aux utilisateurs et aux administrateurs d’interagir avec une instance TTL-LAMa via son API HTTP, sans dépendre de son interface Web.

Le paquet est autonome dans le dépôt `cli/` et peut évoluer indépendamment du serveur. TTL-LAMa gère des accès réseau temporaires sous forme de baux (*leases*) ; la CLI n’est ni un client VPN ni un outil général d’administration réseau.

## État du projet

La CLI est en développement. Les commandes disponibles permettent de configurer l’adresse du serveur, de s’authentifier avec un compte interne, de consulter et fermer la session courante, de changer le mot de passe de l’utilisateur connecté, de consulter son aperçu, ses profils, ses appareils et ses leases, et de gérer les utilisateurs et les profils. Les commandes décrites comme « prévues » dans la suite sont la cible fonctionnelle, pas des commandes déjà utilisables.

| Groupe | Commandes disponibles | Commandes prévues |
| --- | --- | --- |
| `config` | `set-server` | — |
| `auth` | `login internal`, `logout`, `password-chg`, `status` | `login external`, `login oidc` |
| `user` | `get`, `profiles list`, `profiles get`, `devices list/get/add/delete`, `leases list/get/create/revoke` | — |
| `global-config` | — | `get`, `diff`, `validate`, `apply` |
| `admin users` | `list`, `get`, `create`, `update`, `delete`, `assign`, `unassign` | — |
| `admin devices` | — | `list`, `get`, `update`, `block`, `delete` |
| `admin leases` | — | `list`, `get`, `revoke` |
| `admin profiles` | `list`, `get`, `create`, `update`, `delete` | — |

Les autres commandes prévues reprendront les ressources et opérations exposées par l’[API v1](../../src/api/v1/README.md) (voir le dépôt github.com/remiv1/TTL-LAMa). Leurs options de filtrage et leurs formats de fichiers seront définis au fur et à mesure de leur implémentation.

## Installation et utilisation

A l'avenir, le paquet sera publié sur PyPI pour une installation simplifiée via `pip install ttlama-cli`.

Prérequis : Python 3.12 ou supérieur et une instance TTL-LAMa accessible en HTTP(S). Depuis le dossier `cli/`, installez le paquet dans un environnement virtuel :

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
ttlama --help
```

Configurez l’instance à joindre. L’URL contient le schéma et l’hôte ; le port se fournit séparément :

```bash
ttlama config set-server http://localhost --port 8080
```

Connectez-vous avec un compte interne. Le mot de passe est demandé de façon masquée et n’est pas un argument de la commande :

```bash
ttlama auth login internal --user admin
```

La commande effectue l’échange CSRF requis par l’API, puis enregistre le jeton d’accès retourné par le serveur. Elle n’affiche ni le mot de passe ni le jeton.

Changez le mot de passe du compte connecté. Le mot de passe actuel et le nouveau sont demandés de façon masquée, puis le nouveau est demandé une seconde fois pour confirmation. Après le succès, toutes les sessions du compte sont révoquées, y compris le jeton CLI ; reconnectez-vous pour enregistrer un nouveau jeton.

```bash
ttlama auth password-chg
```

Consultez la session courante, avec les dates d’expiration des sessions actives, ou fermez celle utilisée par cette instance de la CLI :

```bash
ttlama auth status
ttlama auth status --json
ttlama auth status --yaml
ttlama auth status --check-connected
ttlama auth logout
```

`status` n’affiche ni jeton d’accès ni hash. Sans jeton enregistré localement, la commande indique que la session est inactive et se termine avec succès ; `--check-connected` renvoie un code non nul dans ce cas. `logout` révoque uniquement la session CLI courante. Il supprime le jeton local après succès ou si le serveur le déclare invalide ; une erreur réseau ou serveur le conserve pour permettre une nouvelle tentative. Les sorties JSON et YAML de `status` contiennent `session` (`active` ou `inactive`), `user` (`null` sans jeton local ; sinon `id`, `username`, `email` et `is_admin`), ainsi que `sessions`, une liste de dates `expires_at`.

## Configuration et identifiants

L’adresse et le port de l’instance sont enregistrés dans `config.json`, sous le répertoire de configuration utilisateur déterminé par `platformdirs` (par exemple le répertoire XDG sous Linux). L’URL doit utiliser `http` ou `https`, sans identifiants, paramètres de requête ni fragment.

Le jeton d’accès est enregistré dans le trousseau système via `keyring`, dans une entrée par instance configurée. Il n’est pas écrit dans le fichier de configuration JSON. Un changement de mot de passe révoque ce jeton côté serveur ; la prochaine connexion réussie le remplace localement.

## Organisation du code

- `src/ttlama_cli/cli.py` déclare la commande `ttlama` et ses groupes.
- `src/ttlama_cli/commands/` contient les commandes Typer, notamment `auth`, `config`, `admin` et `user`.
- `src/ttlama_cli/api_client.py` effectue les appels HTTP à l’API.
- `src/ttlama_cli/config_store.py` valide et persiste l’instance configurée.
- `src/ttlama_cli/token_store.py` encapsule l’accès au trousseau système.
- `tests/` contient les tests unitaires et les tests d’intégration.

## Tests unitaires

Installez les dépendances de test, puis lancez la suite depuis `cli/` :

```bash
python -m pip install -e '.[test]'
python -m pytest tests/
```

## Tests d’intégration

Le lanceur démarre une instance éphémère depuis `ghcr.io/remiv1/ttl-lama:latest`, puis exécute les commandes d’authentification contre le vrai serveur :

```bash
./scripts/test-integration.sh
```

Le lanceur nécessite Podman Compose et un accès à l’image GHCR. Il vérifie le succès d’une authentification interne et le rejet d’un mot de passe incorrect. Le serveur de test utilise des identifiants dédiés, le trousseau est remplacé par un stockage mémoire et aucun volume de l’hôte n’est monté. Les conteneurs du projet Compose sont arrêtés et supprimés à la fin du script.

Les tests unitaires s’exécutent localement depuis ce dossier après installation du paquet :

```bash
python -m pip install -e '.[test]'
python -m pytest tests/
```

Les tests d’intégration démarrent une instance éphémère depuis `ghcr.io/remiv1/ttl-lama:latest`, puis exécutent les commandes d’authentification contre cette instance :

```bash
./scripts/test-integration.sh
```

Le lanceur nécessite Podman Compose et l’accès à l’image GHCR. Il ne monte aucun volume de l’hôte ; les identifiants sont réservés au serveur de test et le trousseau est remplacé par un stockage mémoire.

## Arbre des commandes

Voici l’arborescence cible des commandes disponibles avec `ttlama` :

```md
ttlama
 ├── auth → **Authentification** → **_Qui suis-je ?_**
 │    ├── login
 │    │     ├── internal --user <username>
 │    │     ├── external --user <username>
 │    │     └── oidc --user <username>
 │    │
 │    ├── logout
 │    ├── password-chg
 │    └── status
 │
 ├── user → **Utilisation** → **_Qu'est-ce que j'utilise ?_**
 │    ├── get
 │    │
 │    ├── devices
 │    │     ├── list
 │    │     ├── get --id <device_id>
 │    │     ├── add --file <file_path>
 │    │     └── delete --id <device_id>
 │    │
 │    ├── leases
 │    │     ├── list
 │    │     ├── get --id <lease_id>
 │    │     ├── create --file <file_path>
 │    │     └── revoke --id <lease_id>
 │    │
 │    └── profiles
 │          ├── list
 │          └── get --id <profile_id>
 │
 ├── global-config → **Configuration** → **_Comment l'instance fonctionne ?_**
 │    ├── get [--output <file_path> | none]
 │    ├── diff --file <file_path> [--colored-diff | none]
 │    ├── validate --file <file_path>
 │    └── apply --file <file_path> [--dry-run | none]
 │
 └── admin → **Administration** → **_Qui a doit à quoi / Quel est l'état administré ?_**
      │
      ├── users
      │     ├── list [--device <device_id> &/| --lease <lease_id> &/| --profile <profile_id> | none]
      │     ├── get --user <user_id>
      │     ├── create --file <file_path>
      │     ├── update --user <user_id> --file <file_path>
      │     ├── delete --user <user_id>
      │     ├── assign --user <user_id> --profile <profile_id>
      │     └── unassign --user <user_id> --profile <profile_id>
      │
      ├── devices
      │     ├── list [--lease <lease_id> | --profile <profile_id> | none]
      │     ├── get --device <device_id>
      │     ├── update --device <device_id> --file <file_path>
      │     ├── block --device <device_id>
      │     └── delete --device <device_id>
      │
      ├── leases
      │     ├── list [
      │     │         --user <user_id>
      │     │     &/| --device <device_id>
      │     │     &/| --profile <profile_id>
      │     │     &/| --status <status>
      │     │     | none
      │     │     ]
      │     ├── get --lease <lease_id>
      │     └── revoke --lease <lease_id>
      │
      └── profiles
            ├── list [--user <user_id> &/| --device <device_id> &/| --lease <lease_id> | none]
            ├── get --profile <profile_id> [--json | --yaml | none]
            ├── create --file <file_path>
            ├── update --profile <profile_id> --file <file_path>
            └── delete --profile <profile_id>
```

### Exemples de fichiers d’entrée

Des exemples JSON et YAML prêts à l’emploi pour chaque commande `--file` sont disponibles dans [examples/](./examples/) : utilisateurs (`users/user-create`, `users/user-update`), profils (`profiles/profile-create`, `profiles/profile-update`), appareils (`devices/device-add`, `devices/device-update`) et baux (`leases/lease-create`).

### Fichiers des commandes admin users

`ttlama admin users create --file` et `update --user <user_id> --file` acceptent des objets JSON ou YAML encodés en UTF-8. La création exige `username` ; `email`, `enabled`, `is_admin` et `password` sont facultatifs. Pour une mise à jour, le fichier contient uniquement les champs à modifier ; utilisez `email: null` pour effacer l’adresse e-mail. Le mot de passe présent dans le fichier est envoyé à l’API, mais n’est jamais affiché par la CLI. Si aucun mot de passe n’est fourni et que le serveur utilise l’authentification interne, l’API en génère un et la CLI ne l’affiche que dans la réponse de création ; conservez-le immédiatement, car il ne sera plus récupérable. Sans authentification interne, aucun identifiant interne n’est créé si le mot de passe est absent.

La sortie JSON ou YAML de `ttlama admin users get <user_id> --json` ou `--yaml` est un objet plat ne contenant que les champs modifiables renvoyés par l’API ; elle peut être passée directement à `update --user <user_id> --file`. La sortie de `list` reste une collection et ne constitue pas un corps de mise à jour. Les mots de passe ne sont jamais renvoyés ; ajoutez manuellement un champ `password` pour en modifier un.

`ttlama admin users assign --user <user_id> --profile <profile_id>` rattache
un profil à un utilisateur ; répéter la commande est sans effet supplémentaire.
La commande `unassign` correspondante révoque le rattachement actif ainsi que
les baux qui lui sont associés.

### Fichiers des commandes admin profiles

`ttlama admin profiles create --file` accepte un objet JSON ou YAML UTF-8 contenant `name`, `default_duration`, `maximum_duration` et une liste non vide de réseaux CIDR sous `networks`. Les durées utilisent les unités `d`, `h`, `m` ou `s`, et la durée par défaut ne peut pas dépasser la durée maximale. Exemple :

```yaml
name: office-access
default_duration: 1h
maximum_duration: 8h
networks:
      - 10.0.0.0/24
```

`update --profile <profile_id> --file` accepte n’importe quel sous-ensemble de ces champs. Les sorties `get --profile <profile_id> --json` et `--yaml` sont un objet plat réutilisable avec `update --file`. Les filtres `--user`, `--device` et `--lease` de `list` se combinent avec AND. Pour un profil historique sans politique, `get` ne renvoie que le nom ; complétez les champs de politique avant de le modifier. La suppression demande de saisir le nom complet du profil, puis révoque celui-ci ainsi que ses rattachements et baux dépendants.
