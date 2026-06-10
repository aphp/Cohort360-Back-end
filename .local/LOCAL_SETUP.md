# Guide de Configuration Technique - Environnement de Développement Local

## 1. Résumé

Ce document constitue le guide de référence technique pour l'installation, la configuration et l'exécution de l'environnement de développement du backend de la plateforme Cohort360 sur un système Linux. Il détaille les étapes nécessaires pour configurer les services tiers, installer les dépendances et lancer l'application avec l'ensemble de ses composants (API, WebSockets, Tâches asynchrones).

## 2. Table des Matières

1. [Résumé](#1-résumé)
2. [Table des Matières](#2-table-des-matières)
3. [Architecture Technique](#3-architecture-technique)
4. [Prérequis Système](#4-prérequis-système)
5. [Configuration des Services Socles](#5-configuration-des-services-socles)
    * [5.1. Serveur Redis](#51-serveur-redis)
    * [5.2. Base de Données PostgreSQL](#52-base-de-données-postgresql)
6. [Installation et Configuration du Projet](#6-installation-et-configuration-du-projet)
    * [6.1.Environnement Virtuel](#61-environnement-virtuel)
    * [6.2. Variables d'Environnement](#62-variables-denvironnement)
7. [Procédures de Lancement](#7-procédures-de-lancement)
    * [7.1. Initialisation de la Base de Données](#71-initialisation-de-la-base-de-données)
    * [7.2. Serveur API (Django)](#72-serveur-api-django)
    * [7.3. Serveur WebSocket (Daphne)](#73-serveur-websocket-daphne)
    * [7.4. Gestion des Tâches Asynchrones (Celery)](#74-gestion-des-tâches-asynchrones-celery)
8. [Gestion des Utilisateurs et Données de Test](#8-gestion-des-utilisateurs-et-données-de-test)
    * [8.1. Comptes Administrateurs](#81-comptes-administrateurs)
    * [8.2. Génération d'Utilisateurs Fictifs](#82-génération-dutilisateurs-fictifs)
9. [Assurance Qualité et Tests](#9-assurance-qualité-et-tests)
10. [Dépannage et Astuces](#10-dépannage-et-astuces)

---

## 3. Architecture Technique

Le fonctionnement complet de l'application repose sur l'interaction de plusieurs services :

- **Django** : Serveur d'API principal gérant les requêtes HTTP.
- **PostgreSQL** : Système de gestion de base de données relationnelle.
- **Redis** : Broker pour Celery, cache applicatif et gestionnaire de canaux pour les WebSockets.
- **Celery** : Moteur d'exécution de tâches asynchrones (Worker) et planifiées (Beat).
- **Daphne** : Serveur ASGI dédié à la gestion des connexions temps réel (WebSockets).

---

## 4. Prérequis Système

L'environnement de développement est optimisé pour les distributions Linux (Ubuntu/Debian).

### 4.1. Dépendances Logicielles

Assurez-vous que les paquets suivants sont installés :

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv postgresql redis-server libpq-dev curl libkrb5-dev
```

### 4.2. Gestionnaire de Paquets (uv)

L'utilisation de `uv` est recommandée pour sa rapidité de gestion des environnements et des dépendances.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
*Note : Il peut être nécessaire de redémarrer le terminal après l'installation.*

---

## 5. Configuration des Services Socles

### 5.1. Serveur Redis

Redis doit être actif pour assurer le fonctionnement du cache et des files d'attente de tâches.

```bash
# Démarrage du service
sudo systemctl start redis

# Vérification de la disponibilité
redis-cli ping
# Résultat attendu : PONG
```

### 5.2. Base de Données PostgreSQL

Configurez l'utilisateur et la base de données via l'interface `psql` :

```bash
sudo -u postgres psql
```

Exécutez les instructions SQL suivantes :

```sql
CREATE DATABASE cohort_db;
CREATE USER cohort_dev WITH PASSWORD 'cohort_dev_pwd';
GRANT ALL PRIVILEGES ON DATABASE cohort_db TO cohort_dev;
ALTER DATABASE cohort_db OWNER TO cohort_dev;
\q
```

---

## 6. Installation et Configuration du Projet

### 6.1. Environnement Virtuel

**Création de l'environnement virtuel et installation :**

   Option 1 : Via `uv` (recommandé)
   ```bash
   uv venv --python 3.12
   source .venv/bin/activate
   uv sync
   ```

   Option 2 : Via `venv` et `pip`
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   pip install .
   ```

### 6.2. Variables d'Environnement

Initialisez votre configuration locale en copiant le template fourni :

```bash
cp .local/loca-env.template .env
```
*Le fichier `.env` à la racine est automatiquement chargé par le framework.*

---

## 7. Procédures de Lancement

### 7.1. Initialisation de la Base de Données

Appliquez les schémas de base de données :

```bash
python manage.py migrate
```

### 7.2. Serveur API (Django)

Lancement du serveur de développement HTTP :

```bash
python manage.py runserver
```
*L'interface est accessible à l'adresse `http://localhost:8000/`.*

### 7.3. Serveur WebSocket (Daphne)

Lancement du serveur ASGI pour le temps réel :

```bash
daphne -p 8001 admin_cohort.asgi:application
```
*Les points d'entrée WebSocket sont accessibles sur `ws://localhost:8001/ws`.*

### 7.4. Gestion des Tâches Asynchrones (Celery)

Celery est requis pour les traitements lourds (calculs de cohortes).

**Exécution du Worker :**
```bash
celery -A admin_cohort worker --loglevel=info
```

**Exécution du Scheduler (Beat) :**
```bash
celery -A admin_cohort beat --loglevel=info
```

---

## 8. Gestion des Utilisateurs et Données de Test

### 8.1. Comptes Administrateurs

1. **Super-utilisateur standard :**
   ```bash
   python manage.py createsuperuser
   ```

2. **Utilisateur de test avec rôle spécifique (mode local) :**
   ```bash
   python manage.py create_user_admin --username {identifiant} --password {mot_de_passe}
   ```

### 8.2. Génération d'Utilisateurs Fictifs

Outil de peuplement pour simuler une charge ou tester l'interface :

```bash
# Génération par défaut (12 utilisateurs)
python manage.py generate_fictive_users

# Génération paramétrée (ex: 50 utilisateurs)
python manage.py generate_fictive_users --count 50

# Paramétrage avancé (Périmètre et Rôle spécifiques)
python manage.py generate_fictive_users --count 3 --perimeter_id 1234567890 --role_id 4
```

---

## 9. Assurance Qualité et Tests

Exécutez la suite de tests complète avec `pytest` pour valider l'intégrité de l'installation :

```bash
pytest
```

---

## 10. Dépannage et Astuces

- **MailHog** : Recommandé pour tester l'interception et l'envoi d'emails en local sans serveur SMTP réel.
- **Variables FHIR** : Pour les modules de cohortes, vérifiez que `FHIR_URL` et `QUERY_EXECUTOR_URL` dans le fichier `.env` pointent vers des instances fonctionnelles.
- **Erreurs Kerberos** : Si l'installation des dépendances échoue sur `gssapi` ou `kerberos`, assurez-vous que les bibliothèques de développement sont présentes :
  ```bash
  sudo apt update && sudo apt install libkrb5-dev
  ```
