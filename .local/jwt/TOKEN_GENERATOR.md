# Générer un Bearer JWT pour l'authentification locale

> Créer un token JWT de test signé avec une clé privée RSA et exposer la clé publique correspondante dans la config/mock
> OIDC, afin que l'application puisse valider le token **sans modifier le code applicatif**.

---

## Prérequis

Assurez-vous que les outils suivants sont disponibles sur votre machine :

| Outil     | Vérification        |
|-----------|---------------------|
| `openssl` | `openssl version`   |
| `python3` | `python3 --version` |
| `pip3`    | `pip3 --version`    |

---

## Étape 1 — Générer une paire de clés RSA 2048 bits

### 1.1 · Créer le dossier de travail

Depuis la **racine du projet** :

```bash
mkdir -p .local/jwt
cd .local/jwt
```

### 1.2 · Générer la paire de clés RSA

**Clé privée (PEM) :**

```bash
openssl genpkey -algorithm RSA -out oidc-private-key.pem -pkeyopt rsa_keygen_bits:2048
```

**Clé publique (PEM) :**

```bash
openssl rsa -pubout -in oidc-private-key.pem -out oidc-public-key.pem
```

### 1.3 · Exporter la clé publique au format attendu par le mock

Le service attend généralement la clé publique en **Base64 DER** (sans en-têtes PEM).

Exporter en DER :

```bash
openssl rsa -pubout -in oidc-private-key.pem -outform DER -out oidc-public-key.der
```

Encoder en Base64 sur une seule ligne :

```bash
base64 -w 0 oidc-public-key.der > oidc-public-key.base64
```

Vérifier le résultat :

```bash
cat oidc-public-key.base64
```

Le contenu obtenu ressemble à :

```
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQE...
```

---

## Étape 2 — Générer le Bearer JWT

### 2.1 · Installer les dépendances Python

```bash
pip3 install pyjwt cryptography
```

> **⚠️ Erreur PEP 668 ?**
> Si `pip3` retourne une erreur du type `hint: See PEP 668 for the detailed specification.`,
> utilisez un environnement virtuel :
>
> ```bash
> python3 -m venv venv
> source venv/bin/activate
> pip install --upgrade pip
> pip install pyjwt cryptography
> ```

### 2.2 · Générer le token

Assurez-vous que le script `generate_token.py` est présent dans le dossier, puis exécutez :

```bash
python3 generate_token.py > access-token.txt
```

Afficher le token brut :

```bash
cat access-token.txt
```

Afficher le header HTTP prêt à l'emploi :

```bash
echo "Bearer $(cat access-token.txt)"
```

---

## Étape 3 — Configurer le service pour accepter le token JWT

### Variables d'environnement requises

| Variable          | Description                                                                              |
|-------------------|------------------------------------------------------------------------------------------|
| `JWT_SIGNING_KEY` | clef publique: "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhki...\n-----END PUBLIC KEY----- |
| `JWT_ALGORITHMS`  | RS256                                                                                    |

*Dans votre fichier d'environnement local (`.env` ou équivalent)
