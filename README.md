# 📋 Gestion des Utilisateurs - Flask

Une application web simple et élégante pour enregistrer et afficher des utilisateurs dans une base de données SQLite.

## ✨ Caractéristiques

- **Interface moderne** : Design inspiré d'Apple avec glassmorphisme et animations fluides
- **Base de données SQLite** : Stockage simple et efficace des utilisateurs
- **Validation des données** : Vérification côté serveur des informations saisies
- **Design responsive** : Interface adaptée à tous les écrans
- **API REST** : Endpoint JSON pour récupérer les utilisateurs

## 🛠 Installation

1. **Cloner ou télécharger le projet**

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **Lancer l'application**
   ```bash
   python app.py
   ```

4. **Ouvrir dans le navigateur**
   ```
   http://localhost:8000
   ```

## 📊 Structure de la base de données

Base de données SQLite stockée dans `databases/users.db` :
- `id` : Identifiant unique (auto-incrémenté)
- `nom` : Nom de famille (requis)
- `prenom` : Prénom (requis)
- `age` : Âge entre 0 et 150 ans (requis)
- `created_at` : Date et heure de création (automatique)

## 🎯 Fonctionnalités

### Interface Web (Layout 3 colonnes)
- **Sidebar** : Menu de navigation et compteur d'utilisateurs
- **Formulaire central** : Ajouter un nouvel utilisateur
- **Tableau utilisateurs** : Liste avec avatars et informations
- **Messages de feedback** : Confirmation et erreurs en temps réel
- **Design responsive** : Adaptable mobile/desktop

### API REST
- `GET /api/users` : Récupère tous les utilisateurs en format JSON

## 🎨 Design

L'interface suit les principes de design d'Apple :
- **Simplicité** : Interface épurée et intuitive
- **Élégance** : Couleurs neutres et typographie moderne
- **Glassmorphisme** : Effets de transparence et de flou
- **Animations fluides** : Transitions et micro-interactions

## 📱 Responsive

L'application s'adapte automatiquement à différentes tailles d'écran :
- **Desktop** : Mise en page optimisée pour grand écran
- **Tablette** : Adaptation des espacements et tailles
- **Mobile** : Interface simplifiée et tactile

## 🔧 Technologies utilisées

- **Flask** : Framework web Python
- **SQLite** : Base de données légère
- **HTML5/CSS3** : Interface utilisateur moderne
- **Jinja2** : Moteur de templates Flask

## 📝 Utilisation

1. Remplissez le formulaire avec les informations de l'utilisateur
2. Cliquez sur "Enregistrer l'utilisateur"
3. L'utilisateur apparaît instantanément dans la liste
4. Les données sont automatiquement sauvegardées dans `databases/users.db`

## 🔒 Sécurité

- Validation des données côté serveur
- Protection contre les injections SQL (requêtes préparées)
- Nettoyage automatique des données saisies
- Messages d'erreur informatifs

## 🚀 Déploiement

Pour un déploiement en production :
1. Modifiez la `secret_key` dans `app.py`
2. Configurez une base de données plus robuste si nécessaire
3. Ajoutez HTTPS et autres mesures de sécurité
4. Utilisez un serveur WSGI comme Gunicorn

---

*Projet créé avec ❤️ en suivant les principes de simplicité et d'élégance* 