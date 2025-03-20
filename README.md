# Maja - Générateur d'Annonces Immobilières avec IA

ImmoAI est une plateforme web qui permet aux agences immobilières françaises de générer des annonces professionnelles à partir d'images et d'informations de base sur les biens immobiliers. L'application utilise l'intelligence artificielle pour analyser les images, générer des descriptions attrayantes et créer des annonces complètes incluant des cartes interactives.

## Fonctionnalités

- **Génération de descriptions par IA** : Transforme les descriptions basiques en textes professionnels et attrayants
- **Analyse d'images** : Détecte automatiquement les pièces et caractéristiques des biens à partir des photos
- **Intégration de cartes** : Affiche la localisation du bien avec les commodités à proximité
- **Gestion des DPE** : Intègre les diagnostics de performance énergétique aux annonces
- **Interface utilisateur intuitive** : Création d'annonces en quelques clics
- **Tableau de bord complet** : Gestion centralisée de toutes les annonces
- **Prévisualisation des annonces** : Aperçu professionnel avant publication

## Installation

### Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- Un compte OpenAI pour l'API (pour la génération de descriptions)

### Étapes d'installation

1. Clonez ce dépôt :
   ```
   git clone https://github.com/votre-utilisateur/immoai.git
   cd immoai
   ```

2. Créez un environnement virtuel et activez-le :
   ```
   python -m venv venv
   
   # Sur Windows
   venv\Scripts\activate
   
   # Sur macOS/Linux
   source venv/bin/activate
   ```

3. Installez les dépendances :
   ```
   pip install -r requirements.txt
   ```

4. Créez un fichier `.env` à la racine du projet avec les variables suivantes :
   ```
   OPENAI_API_KEY=votre_clé_api_openai
   SECRET_KEY=une_clé_secrète_pour_flask
   ```

5. Créez les dossiers nécessaires pour les uploads :
   ```
   mkdir -p static/uploads/properties static/uploads/dpe static/img
   ```

6. Lancez l'application :
   ```
   python app.py
   ```

7. Accédez à l'application dans votre navigateur à l'adresse `http://localhost:5000`

## Structure du projet

```
immoai/
├── app.py                  # Application principale Flask
├── requirements.txt        # Dépendances Python
├── .env                    # Variables d'environnement (à créer)
├── database.json           # Base de données simulée
├── static/                 # Fichiers statiques
│   ├── css/                # Feuilles de style
│   │   └── style.css       # Styles personnalisés
│   ├── js/                 # Scripts JavaScript
│   │   └── main.js         # Script principal
│   ├── img/                # Images du site
│   └── uploads/            # Fichiers téléchargés
│       ├── properties/     # Photos des biens
│       └── dpe/            # Documents DPE
└── templates/              # Templates HTML
    ├── base.html           # Template de base
    ├── index.html          # Page d'accueil
    ├── login.html          # Page de connexion
    ├── register.html       # Page d'inscription
    ├── dashboard.html      # Tableau de bord
    ├── new_property.html   # Création d'annonce
    ├── edit_property.html  # Modification d'annonce
    └── property_preview.html # Prévisualisation d'annonce
```

## Utilisation

### Inscription et connexion

1. Créez un compte en fournissant le nom de votre agence, votre email et un mot de passe
2. Connectez-vous avec vos identifiants

### Création d'une annonce

1. Cliquez sur "Nouvelle annonce" dans le tableau de bord
2. Remplissez les informations de base sur le bien (type, prix, surface, etc.)
3. Ajoutez une description simple du bien
4. Téléchargez des photos du bien et le document DPE si disponible
5. Cliquez sur "Générer une description avec l'IA" pour améliorer votre texte
6. Validez la création de l'annonce

### Gestion des annonces

- Visualisez toutes vos annonces dans le tableau de bord
- Modifiez ou supprimez une annonce existante
- Prévisualisez l'annonce telle qu'elle apparaîtra aux clients

## Personnalisation

### Modification des styles

Vous pouvez personnaliser l'apparence de l'application en modifiant le fichier `static/css/style.css`.

### Ajout de fonctionnalités

Pour ajouter de nouvelles fonctionnalités, modifiez le fichier `app.py` et créez les templates correspondants dans le dossier `templates/`.

## Intégration avec d'autres plateformes

ImmoAI peut être facilement intégré avec d'autres plateformes immobilières via des API. Pour cela, vous devrez développer des connecteurs spécifiques selon les plateformes cibles.

## Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

## Contact

Pour toute question ou suggestion, veuillez contacter :
- Email : contact@immoai.fr
- Site web : www.immoai.fr

---

Développé avec ❤️ pour les agences immobilières françaises
