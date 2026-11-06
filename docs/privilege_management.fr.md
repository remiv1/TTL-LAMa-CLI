# Gestion des privilèges des backends

TTL-LAMa est conçu pour fonctionner sans accès privilégié direct à l'infrastructure réseau de l'hôte.

Les opérations nécessitant des privilèges système sont exécutées sur le serveur hébergeant le backend VPN au travers d'une connexion SSH dédiée.

Cette séparation permet de conserver le conteneur TTL-LAMa non privilégié tout en donnant au backend les permissions strictement nécessaires à la matérialisation et à la révocation des baux.

## Architecture

Le modèle général est le suivant :

```text
Conteneur TTL-LAMa
│
├── API
├── scheduler
└── backend
     │
     │ SSH
     ▼
Serveur VPN
│
├── utilisateur système dédié : <ssh_config.user>
│
├── CLI TTL-LAMa
│    │
│    └── `ttlama backend <backend>` ...
│
└── élévation contrôlée
     │
     ▼
gestionnaire VPN
```

Dans le cas de WireGuard :

```text
TTL-LAMa
   │
   │ SSH
   ▼
utilisateur ttlama
   │
   ▼
sudo -n ttlama backend wg leases ...
   │
   ▼
WireGuardDriver
   │
   ▼
   wg
   │
   ▼
   wg0
```

La connexion SSH constitue la frontière entre l'application TTL-LAMa et le serveur VPN.

## Installation de la CLI sur le serveur VPN

La CLI `ttlama` doit être installée globalement sur le serveur VPN et être administrée par l'opérateur.

L'exécutable ainsi que le code Python correspondant ne doivent pas être modificables par l'utilisateur SSH dédié.

L'installation doit fournir une commande stable, par exemple :

```bash
/usr/local/bin/ttlama backend <backend> ...
```

L'utilisateur dédié doit pouvoir exécuter normalement `ttlama --help` sans disposer pour autant de privilèges administratifs.

Depuis le dossier `cli/` d'une copie du dépôt :

```bash
cd /path/to/TTL-LAMa/cli
sudo python3 -m venv /opt/ttlama-cli
sudo /opt/ttlama-cli/bin/python -m pip install --upgrade pip
sudo /opt/ttlama-cli/bin/python -m pip install .
sudo ln -sfn /opt/ttlama-cli/bin/ttlama /usr/local/bin/ttlama
/usr/local/bin/ttlama --help
```

Cette procédure installe les sources du dépôt dans un environnement virtuel appartenant à root. Depuis une copie mise à jour, exécutez `sudo /opt/ttlama-cli/bin/python -m pip install --force-reinstall .` pour réinstaller la CLI ; n'installez pas le paquet globalement avec `sudo pip`.

## Utilisateur système dédié

Un utilisateur système dédié doit être créé sur le serveur hébergeant le backend VPN.

```bash
sudo useradd \
  --system \
  --create-home \
  --home-dir /var/lib/ttlama \
  --shell /bin/bash \
  <ssh_config.user>
```

Cet utilisateur :

- N'est pas root
- Est réservé aux opérations effectuées par TTL-LAMa
- Possède une clé SSH dédiée
- Ne doit pas disposer de privilèges administratifs généraux
- Ne reçoit que les autorisations nécessaires au backend configuré.

Son répertoire personnel peut notamment contenir :

```texte
/var/lib/ttlama/
└── .ssh/
    └── authorized_keys
```

## Gestion des privilèges avec `sudo`

Certaines opérations des drivers nécessitent des privilèges système. WireGuard nécessite notamment que les opérations modifiant l'état de l'interface soient exécutées avec les permissions appropriées.

Deux modes d'utilisation sont distingués.

### Administration manuelle

Un administrateur peut lancer explicitement la CLI avec `sudo`:

```bash
sudo ttlama backend wg leases ...
```

Ce mode est principalement destiné au diagnostic, aux tests et aux opérations administratives ponctuelles.

### Exécution automatisée

Pour les appels provenant de l'application TTL-LAMa, l'utilisateur défini dans le fichier de configuration reste non privilégié. Seules les commandes `ttlama backend` nécessaires au backend configuré doivent pouvoir bénéficier d'une élévation contrôlée.

La configuration `sudoers` doit respecter le principe du moindre privilège. Elle ne doit notamment pas donner à l'utilisateur configuré une autorisation générale telle que :

```texte
Cmnd_Alias TTLAMA_BACKEND = /usr/local/bin/ttlama backend *
ttlama ALL=(root) NOPASSWD: TTLAMA_BACKEND
```

Les permissions doivent être limitées aux opérations nécessaires au backend. Une configuration dédiée peut être placée dans `/etc/sudoers.d/ttlama`. Cette configuration doit être validée avec :

```bash
sudo visudo -cf /etc/sudoers.d/ttlama
```

L'application distante invoque la CLI backend avec sudo -n. L'élévation concerne la commande ttlama backend ... ; le driver sélectionné par la CLI s'exécute ensuite dans ce contexte et n'appelle pas lui-même sudo. Toute demande de mot de passe doit être considérée comme une erreur de configuration du backend.

## Configuration SSH

Les paramètres permettant à TTL-LAMa de joindre le serveur VPN sont stockés dans un fichier de configuration dédié dans `/etc/ttl-lama/ssh_config.yml`.

Exemple de configuration :

```yaml
ssh_config:
  host: host.containers.internal # ou vpn.example.com
  port: 22
  user: ttlama

  identity_file: /run/secrets/ttlama_ssh_key
  known_hosts_file: /etc/ttl-lama/ssh_known_hosts

  connection_timeout: 10
```

Le fichier décrit le transport SSH. Il ne contient pas la clé privée elle-même.
Le scheduler le lit à l’ouverture d’une connexion SSH ; les paramètres de connexion ne sont pas conservés dans la configuration de l’application.

La configuration du backend reste indépendante dans `/etc/ttl-lama/backend_config.yml` :

```yaml
backend:
  wireguard:
    interfaces:
      - name: wg0
        description: Interface WireGuard principale
        networks:
          - 10.0.0.1/24
        public_key: your_public_key_here
        default_duration: 8h
        maximum_duration: 24h
```

Cette séparation distingue :

- `ssh_config.yml` : **_Comment contacter l'hôte ?_**
- `backend_config.yml` : **_Quelles infrastructures administrer ?_**
  
### Clé SSH dédiée

TTL-LAMa utilise une paire de clés SSH dédiée à la communication entre l'application et le serveur VPN.

La paire ne doit pas être réutilisée pour l'administration humaine du serveur. Elle peut être générée avec :

```bash
ssh-keygen \
  -t ed25519 \
  -f ttlama_backend \
  -C "TTL-LAMa backend"
```

Deux fichiers sont générés :

- `ttlama_backend` : La clé privée utilisée par TTL-LAMa pour se connecter au serveur VPN.
- `ttlama_backend.pub` : La clé publique correspondante à ajouter sur le serveur VPN.

#### Clé privée

La clé privée appartient au côté application TTL-LAMa. Elle ne doit jamais :

- être intégrée dans l'image du conteneur
- être intégrée dans le dépôt Git
- être copiée sur le serveur VPN
- apparaître dans les logs

Elle doit être injectée au déploiement au moyen du mécanisme de gestion des secrets utilisé par l'opérateur. Le fichier configuré dans `ssh_config.yml` désigne son emplacement:

```yaml
ssh_config:
  identity_file: /run/secrets/ttlama_ssh_key
```

#### Clé publique

La clé publique est installée sur le serveur VPN dans le compte dédié : `/var/lib/ttlama/.ssh/authorized_keys`.

Elle peut être associée à des restrictions SSH destinées à réduire les possibilités offertes à la connexion automatisée. La connexion utilisée par TTL-LAMa ne doit notamment pas devenir un moyen général d'administration du serveur.

### Vérification de l'identité du serveur

TTL-LAMa doit vérifier l'identité SSH du serveur distant.

La configuration référence pour cela un fichier `known_hosts` :

```yaml
ssh_config:
  known_hosts_file: /etc/ttl-lama/ssh_known_hosts
```

L'application ne doit pas désactiver la vérification de l'identité du serveur pour faciliter le déploiement. La clé d'hôte attendue doit être provisionnée par l'opérateur.

### Séparation des secrets et de la configuration

La configuration et les secrets ont des cycles de vie différents. La disposition recommandée est conceptuellement :

```text
/etc/ttl-lama/
├── config.yml
├── ssh_config.yml
└── ssh_known_hosts

/run/secrets/
└── ttlama_ssh_key
```

Le premier ensemble contient la configuration provisionnée par l'opérateur. Le second contient des secrets injectés lors du déploiement.

### Permissions recommandées

Les données sensibles doivent avoir des permissions restrictives.

```text
/run/secrets/ttlama_ssh_key
    lecture : utilisateur TTL-LAMa uniquement

/etc/ttl-lama/ssh_known_hosts
    lecture : TTL-LAMa
    écriture : administrateur uniquement

/var/lib/ttlama/.ssh/authorized_keys
    lecture/écriture : compte serveur correctement restreint
```

Les permissions exactes doivent être adaptées au mode de déploiement et au mécanisme de secrets utilisé par l'opérateur.

## Modèle de sécurité

La chaîne de privilèges recherchée est :

```text
Application TTL-LAMa non privilégiée
          │
          │ clé SSH dédiée
          ▼
Compte ttlama non privilégié
          │
          │ sudo limité
          ▼
ttlama backend <backend> ...
          │
          ▼
      Driver VPN
          │
          ▼
Infrastructure VPN
```

Une compromission d'un niveau ne doit donc pas donner automatiquement accès à l'ensemble du niveau suivant, en particulier :

- Le conteneur TTL-LAMa ne reçoit pas de privilège réseau sur l'hôte
- la clé SSH n'est pas une clé d'administration humaine
- l'utilisateur SSH n'est pas `root`
- `sudo` n'autorise pas des commandes administratives générales
- le driver VPN ne construit jamais une commande passée à un shell
- seuls les paramètres strictement nécessaires au backend sont acceptés.
- l'exécutable `ttlama` et le code qu'il charge lors d'une élévation ne sont pas modifiables par l'utilisateur SSH dédié ;

## WireGuard

Pour WireGuard, la CLI locale expose les opérations TTL-LAMa :

```bash
sudo -n ttlama backend wg leases ...
```

La commande privilégiée est la CLI TTL-LAMa elle-même. Le `WireGuardDriver` n'effectue pas de nouvelle élévation de privilèges et exécute directement les primitives WireGuard nécessaires.

L'application transmet le document du bail sur l'entrée standard SSH avec `--lease -`; le contenu JSON/YAML n'est pas ajouté à la commande distante. Le document complet comprend l'interface ciblée, l'identifiant du bail, l'identifiant de l'appareil, la clé publique et les réseaux autorisés. Exemple d'appel depuis un client disposant déjà du document en mémoire :

```bash
printf '%s' "$lease_json" | ssh -T vpn-admin@vpn-host \
  'sudo -n ttlama backend wg leases apply --lease -'
```

`get` renvoie l'état JSON/YAML du peer; `--check` permet de distinguer un peer absent avec le code de sortie. `apply` et `delete` renvoient un statut JSON. Les erreurs sont émises sur stderr et produisent un code de sortie non nul.

Le driver traduit ensuite les opérations sur les leases vers les primitives WireGuard correspondantes, par exemple :

```text
TTL-LAMa lease
      │
      ▼
WireGuardDriver
      │
      ▼
WireGuard peer
```

La CLI et le driver ne doivent pas manipuler la clé privée de l'interface WireGuard. La lecture de l'état nécessaire à la réconciliation doit se limiter aux informations nécessaires à TTL-LAMa, notamment l'identité des peers et leurs réseaux autorisés.

## Extension à d'autres backends VPN

La gestion des privilèges est volontairement séparée du backend VPN. Le même modèle peut être utilisé avec d'autres drivers :

```text
Application
    │
    └── SSH
         │
         ▼
utilisateur dédié
         │
         ▼
sudo -n ttlama backend <backend> leases ...
         │
         ▼
VPNDriver
         │
         ├── WireGuardDriver
         ├── OpenVPNDriver
         └── futur driver
```

Chaque driver définit les opérations locales nécessaires à son gestionnaire VPN, tandis que le transport SSH et son modèle de privilèges restent communs.
