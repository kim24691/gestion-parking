# Application Web de Gestion du Parking Public de la Ville de Bujumbura

Projet académique réalisé pour la **Faculté de Génie Logiciel** de l'**Université Internationale de Bujumbura (Bujumbura International University - BIU)**  
**Niveau :** BAC 2 &bull; **Cours :** Programmation en Python / Framework Django  
**Localisation :** Ville de Bujumbura, République du Burundi  
**Monnaie Officielle :** Franc Burundi (**BIF**)  

---

## 📌 Présentation & Objectifs du Projet

Cette application web a été développée en réponse aux exigences académiques et aux besoins réels de la Mairie de Bujumbura pour moderniser et informatiser la gestion du stationnement public urbain.

Elle permet la supervision en temps réel des places de stationnement, le calcul automatisé des droits de stationnement en **Francs Burundi (BIF)** selon des grilles tarifaires configurables, une traçabilité totale des opérations grâce à un système d'**Audit Trail**, ainsi que la génération de rapports officiels imprimables et exportables en **PDF**.

---

## 🏛️ Zones de Stationnement Pilotes (Bujumbura)

L'application intègre nativement les grandes zones de parking de la capitale économique :
- **Centre-Ville (CV)** : Avenue de l'Uprona, Boulevard Patrice Lumumba (120 places)
- **Rohero (ROH)** : Boulevard de l'Indépendance, Avenue de France (85 places)
- **Place de l'Indépendance (PLI)** : Rond-point central et abords de la Place (150 places)
- **Marché Central (MC)** : Périmètre commercial du grand marché (200 places)
- **Asian (ASI)** : Quartier Asiatique, Avenue du Commerce (60 places)

---

## ⚙️ Fonctionnalités Détaillées du Cahier des Charges

### 1. Authentification & Gestion des Rôles
- Système de connexion/déconnexion sécurisé avec contrôle d'accès basé sur les rôles (RBAC).
- **Rôles distincts :**
  - **Administrateur Municipal** : Accès complet à l'ensemble du système, gestion des utilisateurs, des tarifs, des zones, suppression définitive et statistiques globales.
  - **Agent de Parking / Contrôleur** : Enregistrement des entrées/sorties de véhicules, encaissement en BIF, consultation des tickets et impression des reçus.
- Partage des données centralisé et sécurisé en fonction des autorisations.

### 2. Traçabilité & Historique des Activités (Audit Trail)
- Modèle `ActivityLog` enregistrant automatiquement chaque opération :
  - **Qui :** Utilisateur connecté (nom, matricule, rôle).
  - **Quoi :** Nature de l'action (`CREATION`, `MODIFICATION`, `SUPPRESSION`, `DESACTIVATION`, `ENTREE_VEHICULE`, `SORTIE_PAIEMENT`, `CONNEXION`, etc.).
  - **Sur quel élément :** Modèle ciblé (`ParkingTicket`, `ParkingZone`, `Tariff`, `CustomUser`), identifiant et intitulé.
  - **Détails & Date/Heure :** Horodatage exact (fuseau `Africa/Bujumbura` - UTC+2) et adresse IP du client.

### 3. Modules CRUD & Recherche Avancée
- **Module Utilisateurs :** Ajout, modification, activation/désactivation (soft toggle), recherche par matricule ou identifiant.
- **Module Zones & Emplacements :** Calcul en temps réel des places occupées, disponibles et du taux d'occupation (`%`) avec jauges dynamiques (Vert, Jaune, Rouge).
- **Module Tarification & Véhicules :**
  - Catégories de véhicules : Voiture de tourisme, Motocyclette/Bajaj, Minibus/Bus, Camion/Poids lourd.
  - Tarifs configurables par heure entamée ou par journée en **BIF**, avec période de grâce gratuite (ex: 15 min).
- **Module Stationnements & Tickets :**
  - Enregistrement de l'entrée avec vérification en temps réel de la disponibilité dans la zone.
  - Attribution automatique d'un numéro de ticket unique (`BJM-YYYYMMDD-XXXX`).
  - Clôture de sortie avec calcul automatique de la durée et du montant dû en BIF.
  - Encaissement multi-canaux : Espèces (Cash BIF), Lumicash, EcoCash, Virement bancaire.
  - Recherche multi-critères : immatriculation, zone, statut, type véhicule, plage de dates.
  - Désactivation logique d'un ticket avec justification textuelle obligatoire.
  - Suppression physique définitive réservée à l'administrateur avec confirmation.

### 4. Rapports & Impression
- **Ticket / Reçu thermique :** Mise en page optimisée pour imprimante ticket avec style `@media print` et téléchargement au format **PDF** officiel via *ReportLab*.
- **Bilan des flux de trafic :** Entrées et sorties par jour et par semaine, comparatifs quotidiens.
- **Rapport financier des recettes :** Recettes globales en BIF, ventilées par zone, par type de véhicule et par mode de paiement. Export **PDF A4** prêt pour signature.
- **Liste des infractions & dépassements :** Détection automatique des véhicules ayant dépassé le seuil réglementaire (> 8 heures) ou stationnés la nuit.

### 5. Interface Utilisateur & Design (UI/UX)
- Interface moderne et responsive propulsée par **Bootstrap 5** et **FontAwesome 6**.
- Palette harmonieuse : Bleu Bujumbura `#1a365d` (institutionnel), Vert Émeraude `#059669` (places libres et finances en BIF), Orange et Rouge pour les alertes.
- Dashboard interactif avec indicateurs de performance clés (KPIs) en temps réel.

---

## 🛠️ Architecture Technique & Technologies

- **Langage :** Python 3.13+
- **Framework Web :** Django 6.x
- **Génération PDF :** ReportLab
- **Frontend :** HTML5, CSS3, JavaScript, Bootstrap 5.3, FontAwesome 6.5
- **Base de données :** SQLite (embarquée par défaut) ou PostgreSQL / MariaDB
- **Fuseau Horaire :** `Africa/Bujumbura` (CAT - UTC+2)
- **Devise :** `BIF` (Franc Burundi)

---

## 🚀 Installation & Démarrage Rapide

### 1. Cloner ou ouvrir le projet
```bash
cd "gestion parking"
```

### 2. Activer l'environnement virtuel
```bash
source .venv/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Appliquer les migrations de la base de données
```bash
python manage.py migrate
```

### 5. Charger les données de démonstration de Bujumbura
```bash
python manage.py seed_parking_data
```

### 6. Lancer le serveur de développement
```bash
python manage.py runserver
```

L'application est accessible sur : **http://127.0.0.1:8000/**

---

## 🔑 Comptes de Test Pré-configurés

La commande `seed_parking_data` configure automatiquement les comptes suivants :

| Rôle | Identifiant | Mot de passe | Matricule | Zone Affectée |
| :--- | :--- | :--- | :--- | :--- |
| **Administrateur** | `admin` | `admin123` | `ADM-BJM-001` | Accès global |
| **Agent de Parking** | `agent_rohero` | `agent123` | `AGT-ROH-01` | Rohero |
| **Agent de Parking** | `agent_centre` | `agent123` | `AGT-CV-02` | Centre-Ville |
| **Contrôleur** | `controleur` | `agent123` | `CTRL-BJM-03` | Place de l'Indépendance |

> L'interface d'administration native Django est également accessible sur : **http://127.0.0.1:8000/admin/**

---

## 🧪 Exécution des Tests Automatisés

Le projet comprend une suite complète de tests unitaires et fonctionnels :
```bash
python manage.py test
```

Résultat attendu :
```text
Ran 8 tests in ...s
OK
```

---

## 📁 Structure du Projet

```text
gestion parking/
├── bujumbura_parking_project/       # Configuration du projet Django
│   ├── settings.py                  # Paramètres (Timezone Bujumbura, BIF, Auth User)
│   ├── urls.py                      # URLs racines
│   ├── wsgi.py                      # Configuration WSGI
│   └── asgi.py                      # Configuration ASGI
├── parking_app/                     # Application principale de parking
│   ├── models.py                    # CustomUser, ParkingZone, VehicleType, Tariff, ParkingTicket, ActivityLog
│   ├── views.py                     # Contrôleurs CRUD, calculs BIF, impression et rapports
│   ├── forms.py                     # Formulaires Bootstrap 5 avec validation métier
│   ├── utils.py                     # Audit Trail, décorateurs, calculs et génération PDF ReportLab
│   ├── admin.py                     # Enregistrement dans l'interface Django Admin
│   ├── context_processors.py        # Données globales injectées aux templates (BIF, places temps réel)
│   ├── urls.py                      # Routage de l'application
│   ├── tests.py                     # Suite de tests unitaires et fonctionnels
│   └── management/commands/
│       └── seed_parking_data.py     # Commande de peuplement avec données réelles de Bujumbura
├── static/                          # Fichiers statiques
│   └── css/
│       └── custom.css               # Feuilles de style personnalisées & règles @media print
├── templates/                       # Templates HTML avec Bootstrap 5 & FontAwesome
│   ├── base.html                    # Layout principal avec Sidebar et Topbar
│   └── parking_app/
│       ├── auth/                    # Connexion (login.html), Profil (profile.html)
│       ├── dashboard.html           # Tableau de bord avec KPIs temps réel et jauges
│       ├── tickets/                 # CRUD tickets, entrée, encaissement, détail, print, suppression
│       ├── zones/                   # CRUD zones et état de remplissage
│       ├── tariffs/                 # Grille tarifaire et types de véhicules
│       ├── users/                   # Gestion des comptes utilisateurs et rôles
│       ├── audit/                   # Journal d'audit et traçabilité chronologique
│       └── reports/                 # Bilan de trafic, rapport financier BIF, infractions
├── requirements.txt                 # Liste des dépendances Python
├── manage.py                        # Script d'administration Django
└── README.md                        # Documentation académique et guide utilisateur
```

---

## 🎓 Évaluation Académique

Ce projet illustre :
1. **La Programmation Orientée Objet (POO) en Python :** Héritage de modèles, méthodes personnalisées (`calculate_bill`, `get_available_spots`, etc.).
2. **L'Architecture MVT (Modèle - Vue - Template) :** Séparation stricte de la logique métier, du contrôle et de la présentation.
3. **La Sécurité Applicative :** Décorateurs de contrôle d'accès (`@admin_required`), protection contre les failles CSRF, mots de passe hashés (PBKDF2/SHA256).
4. **L'Audit Trail :** Traçabilité exhaustive de l'activité utilisateur pour répondre aux normes de gouvernance informatique.
