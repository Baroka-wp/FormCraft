# 🚀 FormCraft API REST - Guide d'utilisation

## 📖 Vue d'ensemble

L'API REST de FormCraft permet d'interagir programmatiquement avec vos formulaires dynamiques. Vous pouvez :
- **Créer, lire, modifier, supprimer** des entrées de formulaires
- **Récupérer le schéma** des formulaires
- **Lister tous les formulaires** disponibles

**Base URL :** `http://localhost:8000/api`

---

## 🔧 Endpoints disponibles

### **📋 Gestion des formulaires**

#### `GET /api/forms`
Liste tous les formulaires créés.

```bash
curl -X GET http://localhost:8000/api/forms
```

**Réponse :**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "contact",
      "title": "Formulaire de contact",
      "description": "Formulaire pour contacter l'équipe",
      "fields": [
        {"name": "nom", "label": "Nom", "type": "text", "required": true},
        {"name": "email", "label": "Email", "type": "email", "required": true}
      ],
      "created_at": "2024-01-15 10:30:00"
    }
  ],
  "count": 1
}
```

#### `GET /api/forms/{form_name}/schema`
Récupère le schéma d'un formulaire spécifique.

```bash
curl -X GET http://localhost:8000/api/forms/contact/schema
```

---

### **📝 Gestion des entrées**

#### `GET /api/forms/{form_name}/entries`
Liste toutes les entrées d'un formulaire.

```bash
curl -X GET http://localhost:8000/api/forms/contact/entries
```

**Réponse :**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "nom": "Dupont",
      "email": "dupont@example.com",
      "message": "Bonjour !",
      "created_at": "2024-01-15 14:30:00"
    }
  ],
  "count": 1,
  "form_name": "contact"
}
```

#### `GET /api/forms/{form_name}/entries/{id}`
Récupère une entrée spécifique.

```bash
curl -X GET http://localhost:8000/api/forms/contact/entries/1
```

#### `POST /api/forms/{form_name}/entries`
Crée une nouvelle entrée.

```bash
curl -X POST http://localhost:8000/api/forms/contact/entries \
  -H "Content-Type: application/json" \
  -d '{
    "nom": "Martin",
    "email": "martin@example.com",
    "message": "Demande d'\''information"
  }'
```

**Réponse :**
```json
{
  "success": true,
  "message": "Entrée créée avec succès",
  "form_name": "contact"
}
```

#### `PUT /api/forms/{form_name}/entries/{id}`
Modifie une entrée existante.

```bash
curl -X PUT http://localhost:8000/api/forms/contact/entries/1 \
  -H "Content-Type: application/json" \
  -d '{
    "nom": "Martin",
    "email": "martin.nouveau@example.com",
    "message": "Message modifié"
  }'
```

#### `DELETE /api/forms/{form_name}/entries/{id}`
Supprime une entrée.

```bash
curl -X DELETE http://localhost:8000/api/forms/contact/entries/1
```

---

## 🐍 Exemples Python

### Configuration basique
```python
import requests
import json

BASE_URL = "http://localhost:8000/api"
headers = {"Content-Type": "application/json"}
```

### Lister les formulaires
```python
response = requests.get(f"{BASE_URL}/forms")
data = response.json()

if data['success']:
    print(f"Formulaires trouvés : {data['count']}")
    for form in data['data']:
        print(f"- {form['name']}: {form['title']}")
```

### Créer une entrée
```python
form_name = "contact"
entry_data = {
    "nom": "Alice Dubois",
    "email": "alice@example.com",
    "message": "Intéressée par vos services"
}

response = requests.post(
    f"{BASE_URL}/forms/{form_name}/entries",
    headers=headers,
    data=json.dumps(entry_data)
)

result = response.json()
if result['success']:
    print("✅ Entrée créée avec succès !")
else:
    print(f"❌ Erreur : {result['error']}")
```

### Récupérer toutes les entrées
```python
form_name = "contact"
response = requests.get(f"{BASE_URL}/forms/{form_name}/entries")
data = response.json()

if data['success']:
    print(f"📊 {data['count']} entrées trouvées :")
    for entry in data['data']:
        print(f"- ID {entry['id']}: {entry['nom']} ({entry['email']})")
```

### Modifier une entrée
```python
form_name = "contact"
entry_id = 1
updated_data = {
    "nom": "Alice Martin",
    "email": "alice.martin@example.com",
    "message": "Message mis à jour"
}

response = requests.put(
    f"{BASE_URL}/forms/{form_name}/entries/{entry_id}",
    headers=headers,
    data=json.dumps(updated_data)
)

result = response.json()
print("✅ Modifié !" if result['success'] else f"❌ {result['error']}")
```

---

## 🌐 Exemples JavaScript (Node.js)

### Configuration
```javascript
const axios = require('axios');

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {'Content-Type': 'application/json'}
});
```

### Créer une entrée
```javascript
async function createEntry(formName, data) {
  try {
    const response = await api.post(`/forms/${formName}/entries`, data);
    console.log('✅ Entrée créée :', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ Erreur :', error.response.data);
  }
}

// Utilisation
createEntry('contact', {
  nom: 'Jean Dupuis',
  email: 'jean@example.com',
  message: 'Demande de rendez-vous'
});
```

### Récupérer des entrées avec filtrage
```javascript
async function getEntriesWithFilter(formName) {
  try {
    const response = await api.get(`/forms/${formName}/entries`);
    const entries = response.data.data;
    
    // Filtrer par email contenant 'gmail'
    const gmailUsers = entries.filter(entry => 
      entry.email && entry.email.includes('gmail')
    );
    
    console.log(`📧 ${gmailUsers.length} utilisateurs Gmail trouvés`);
    return gmailUsers;
  } catch (error) {
    console.error('❌ Erreur :', error.response.data);
  }
}
```

---

## 📱 Exemples d'intégration

### **1. Site web avec formulaire AJAX**
```html
<form id="contactForm">
  <input name="nom" placeholder="Votre nom" required>
  <input name="email" type="email" placeholder="Email" required>
  <textarea name="message" placeholder="Message"></textarea>
  <button type="submit">Envoyer</button>
</form>

<script>
document.getElementById('contactForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const formData = new FormData(e.target);
  const data = Object.fromEntries(formData.entries());
  
  try {
    const response = await fetch('/api/forms/contact/entries', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (result.success) {
      alert('✅ Message envoyé avec succès !');
      e.target.reset();
    } else {
      alert('❌ Erreur : ' + result.error);
    }
  } catch (error) {
    alert('❌ Erreur de connexion');
  }
});
</script>
```

### **2. Application mobile (React Native)**
```javascript
import React, {useState} from 'react';

const ContactForm = () => {
  const [form, setForm] = useState({nom: '', email: '', message: ''});
  
  const submitForm = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/forms/contact/entries', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(form)
      });
      
      const result = await response.json();
      
      if (result.success) {
        Alert.alert('Succès', 'Message envoyé !');
        setForm({nom: '', email: '', message: ''});
      }
    } catch (error) {
      Alert.alert('Erreur', 'Connexion impossible');
    }
  };

  return (
    // ... Interface React Native
  );
};
```

### **3. Webhook / Intégration Zapier**
```python
# Script pour synchroniser avec un service externe
import requests
import schedule
import time

def sync_new_entries():
    """Synchronise les nouvelles entrées avec un service externe"""
    
    # Récupérer les entrées du formulaire contact
    response = requests.get("http://localhost:8000/api/forms/contact/entries")
    entries = response.json()['data']
    
    # Envoyer à Slack, email, CRM, etc.
    for entry in entries:
        # Logique de synchronisation
        send_to_slack(entry)
        add_to_crm(entry)

# Exécuter toutes les 5 minutes
schedule.every(5).minutes.do(sync_new_entries)

while True:
    schedule.run_pending()
    time.sleep(1)
```

---

## ⚠️ Gestion d'erreurs

### Codes de statut HTTP
- **200** : Succès
- **201** : Créé avec succès
- **400** : Données invalides
- **404** : Formulaire ou entrée non trouvé(e)
- **500** : Erreur serveur

### Format des erreurs
```json
{
  "success": false,
  "error": "Message d'erreur",
  "details": ["Détails spécifiques", "si disponibles"]
}
```

---

## 🔐 Sécurité & Bonnes pratiques

### **Pour la production :**
1. **Ajouter une authentification** (JWT, API Key)
2. **Implémenter des limites de taux** (rate limiting)
3. **Valider strictement** les données d'entrée
4. **Utiliser HTTPS** pour toutes les communications
5. **Logger** les accès API pour audit

### **Exemple d'authentification simple :**
```python
# Ajouter dans app.py
from functools import wraps

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != 'your-secret-api-key':
            return jsonify({'error': 'API Key requise'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Utiliser sur les endpoints
@app.route('/api/forms', methods=['GET'])
@require_api_key
def api_get_forms():
    # ... code existant
```

---

## 📚 Documentation interactive

Accédez à la documentation interactive en temps réel :
**👉 [http://localhost:8000/api/docs](http://localhost:8000/api/docs)**

Cette page contient :
- ✅ Liste complète des endpoints
- ✅ Exemples de requêtes/réponses
- ✅ Schémas des formulaires en temps réel
- ✅ Testeur d'API intégré 