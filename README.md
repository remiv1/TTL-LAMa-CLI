# TTL-LAMa CLI

![Python](https://img.shields.io/badge/python-3.12+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

[![Logo](./docs/img/logo_300ppp.png)](./docs/img/logo_300ppp.png)

`ttlama` est l’interface en ligne de commande du projet TTL-LAMa (Time-to-Live Lease Administration Manager). Elle a vocation à permettre aux utilisateurs et aux administrateurs d’interagir avec une instance TTL-LAMa via son API HTTP, sans dépendre de son interface Web.

Le paquet est autonome dans le dépôt `cli/` et peut évoluer indépendamment du serveur. TTL-LAMa gère des accès réseau temporaires sous forme de baux (*leases*) ; la CLI n’est ni un client VPN ni un outil général d’administration réseau.

## État du projet

La CLI est en développement. À ce jour, les commandes disponibles permettent de configurer l’adresse du serveur et de s’authentifier avec un compte interne. Les commandes décrites comme « prévues » dans la suite sont la cible fonctionnelle, pas des commandes déjà utilisables.

| Groupe | Commandes disponibles | Commandes prévues |
| --- | --- | --- |
| `config` | `set-server` | — |
| `auth` | `login internal` | `login external`, `login oidc`, `logout`, `status` |
| `user` | — | consultation de l’utilisateur, des appareils, des baux et des profils qui lui sont accessibles |
| `global-config` | — | `get`, `diff`, `validate`, `apply` |
| `admin users` | — | `list`, `get`, `create`, `update`, `delete`, `assign`, `unassign` |
| `admin devices` | — | `list`, `get`, `update`, `block`, `delete` |
| `admin leases` | — | `list`, `get`, `revoke` |
| `admin profiles` | — | `list`, `get`, `create`, `update`, `delete` |

Les commandes prévues reprendront les ressources et opérations exposées par l’[API v1](../src/api/v1/README.md). Leurs options de filtrage et leurs formats de fichiers seront définis au fur et à mesure de leur implémentation.

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

## Configuration et identifiants

L’adresse et le port de l’instance sont enregistrés dans `config.json`, sous le répertoire de configuration utilisateur déterminé par `platformdirs` (par exemple le répertoire XDG sous Linux). L’URL doit utiliser `http` ou `https`, sans identifiants, paramètres de requête ni fragment.

Le jeton d’accès est enregistré dans le trousseau système via `keyring`. Son entrée est associée à l’instance et au nom d’utilisateur. Il n’est donc pas écrit dans le fichier de configuration JSON.

## Organisation du code

- `src/ttlama_cli/cli.py` déclare la commande `ttlama` et ses groupes.
- `src/ttlama_cli/commands/` contient les commandes Typer, notamment `auth` et `config`.
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
