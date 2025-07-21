from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
import sqlite3
import os
import json

app = Flask(__name__)
app.secret_key = 'votre_clé_secrète_ici'  # Changez ceci en production

# Configuration de la base de données
import os
DATABASE_DIR = 'databases'
DATABASE = os.path.join(DATABASE_DIR, 'users.db')

# Créer le dossier databases s'il n'existe pas
if not os.path.exists(DATABASE_DIR):
    os.makedirs(DATABASE_DIR)

def init_db():
    """Initialise la base de données avec les tables users et forms"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Table users (formulaire par défaut)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            age INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table pour stocker les formulaires créés
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT,
            fields TEXT NOT NULL,
            database_file TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Obtient une connexion à la base de données"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def create_custom_form_database(db_path, fields):
    """Crée une base de données personnalisée pour un formulaire avec ses champs"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Construction de la requête CREATE TABLE
    sql_fields = ['id INTEGER PRIMARY KEY AUTOINCREMENT']
    
    for field in fields:
        field_name = field['name']
        field_type = field['type']
        
        # Mapping des types HTML vers SQLite
        if field_type in ['text', 'email', 'tel', 'textarea']:
            sql_type = 'TEXT'
        elif field_type == 'number':
            sql_type = 'INTEGER'
        elif field_type == 'date':
            sql_type = 'DATE'
        else:
            sql_type = 'TEXT'
        
        # Ajout du champ (avec contrainte NOT NULL si requis)
        constraint = ' NOT NULL' if field['required'] else ''
        sql_fields.append(f"{field_name} {sql_type}{constraint}")
    
    # Ajout du timestamp de création
    sql_fields.append('created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    
    # Construction et exécution de la requête
    create_table_sql = f"CREATE TABLE IF NOT EXISTS entries ({', '.join(sql_fields)})"
    cursor.execute(create_table_sql)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Base de données créée : {db_path}")
    print(f"📊 Table 'entries' avec champs : {[f['name'] for f in fields]}")

def save_form_entry(db_path, fields, form_data):
    """Sauvegarde une entrée dans la base de données du formulaire"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Construction de la requête INSERT
    field_names = [field['name'] for field in fields]
    placeholders = ', '.join(['?' for _ in field_names])
    columns = ', '.join(field_names)
    
    sql = f"INSERT INTO entries ({columns}) VALUES ({placeholders})"
    values = [form_data.get(field_name, '') for field_name in field_names]
    
    cursor.execute(sql, values)
    conn.commit()
    conn.close()
    
    print(f"✅ Données sauvegardées dans {db_path}")

def get_form_entries(db_path):
    """Récupère toutes les entrées d'un formulaire"""
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        entries = cursor.execute('SELECT * FROM entries ORDER BY created_at DESC').fetchall()
        conn.close()
        return entries
    except:
        conn.close()
        return []

def update_database_structure(db_path, old_fields, new_fields):
    """Met à jour la structure de la base de données lors de modification d'un formulaire"""
    if not os.path.exists(db_path):
        # Si la DB n'existe pas, la créer avec la nouvelle structure
        create_custom_form_database(db_path, new_fields)
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Obtenir les colonnes existantes
        cursor.execute("PRAGMA table_info(entries)")
        existing_columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        # Identifier les nouveaux champs à ajouter
        old_field_names = {field['name'] for field in old_fields}
        new_field_names = {field['name'] for field in new_fields}
        
        # Ajouter les nouvelles colonnes
        for field in new_fields:
            field_name = field['name']
            if field_name not in existing_columns:
                # Mapping des types HTML vers SQLite
                if field['type'] in ['text', 'email', 'tel', 'textarea']:
                    sql_type = 'TEXT'
                elif field['type'] == 'number':
                    sql_type = 'INTEGER'
                elif field['type'] == 'date':
                    sql_type = 'DATE'
                else:
                    sql_type = 'TEXT'
                
                # Ajouter la colonne (SQLite ne permet pas NOT NULL sur ADD COLUMN)
                alter_sql = f"ALTER TABLE entries ADD COLUMN {field_name} {sql_type}"
                cursor.execute(alter_sql)
                print(f"➕ Colonne ajoutée : {field_name} ({sql_type})")
        
        # Note: SQLite ne supporte pas DROP COLUMN facilement
        # Les anciennes colonnes restent dans la DB pour éviter la perte de données
        removed_fields = old_field_names - new_field_names
        if removed_fields:
            print(f"ℹ️ Colonnes conservées (non supprimées) : {removed_fields}")
        
        conn.commit()
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour de la DB : {str(e)}")
        raise e
    finally:
        conn.close()

@app.route('/create-form', methods=['GET', 'POST'])
def create_form():
    """Route pour créer un nouveau formulaire"""
    if request.method == 'POST':
        # Récupération des données du formulaire
        form_name = request.form.get('form_name', '').strip().lower().replace(' ', '_')
        form_title = request.form.get('form_title', '').strip()
        form_description = request.form.get('form_description', '').strip()
        
        # Récupération des champs personnalisés
        field_names = request.form.getlist('field_name[]')
        field_labels = request.form.getlist('field_label[]')
        field_types = request.form.getlist('field_type[]')
        field_required = request.form.getlist('field_required[]')
        
        # Validation
        if not form_name or not form_title:
            flash('Le nom et le titre du formulaire sont requis', 'error')
        elif not field_names or len(field_names) == 0:
            flash('Au moins un champ est requis', 'error')
        else:
            # Construction de la structure des champs
            fields = []
            for i, name in enumerate(field_names):
                if name and i < len(field_labels) and i < len(field_types):
                    fields.append({
                        'name': name.strip(),
                        'label': field_labels[i].strip(),
                        'type': field_types[i],
                        'required': str(i) in field_required
                    })
            
            if not fields:
                flash('Aucun champ valide défini', 'error')
            else:
                try:
                    # Créer le nom du fichier de base de données
                    db_filename = f"{form_name}.db"
                    db_path = os.path.join(DATABASE_DIR, db_filename)
                    
                    # Créer la table dans la nouvelle base de données
                    create_custom_form_database(db_path, fields)
                    
                    # Enregistrer le formulaire dans la base principale
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO forms (name, title, description, fields, database_file)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (form_name, form_title, form_description, json.dumps(fields), db_filename))
                    
                    conn.commit()
                    conn.close()
                    
                    flash(f'Formulaire "{form_title}" créé avec succès ! Base de données "{db_filename}" créée.', 'success')
                    return redirect(url_for('index'))
                    
                except sqlite3.IntegrityError:
                    flash('Un formulaire avec ce nom existe déjà', 'error')
                except Exception as e:
                    flash(f'Erreur lors de la création : {str(e)}', 'error')
    
    return render_template('create_form.html')

@app.route('/form/<form_name>', methods=['GET', 'POST'])
def dynamic_form(form_name):
    """Route pour afficher et traiter un formulaire dynamique"""
    # Récupérer les informations du formulaire
    conn = get_db_connection()
    form_info = conn.execute(
        'SELECT * FROM forms WHERE name = ?', (form_name,)
    ).fetchone()
    
    if not form_info:
        flash('Formulaire non trouvé', 'error')
        return redirect(url_for('index'))
    
    # Parser les champs du formulaire
    try:
        fields = json.loads(form_info['fields'])
    except:
        flash('Erreur dans la configuration du formulaire', 'error')
        return redirect(url_for('index'))
    
    # Construire le chemin de la base de données du formulaire
    form_db_path = os.path.join(DATABASE_DIR, form_info['database_file'])
    
    if request.method == 'POST':
        # Traitement de l'enregistrement
        form_data = {}
        errors = []
        
        # Validation et récupération des données
        for field in fields:
            field_name = field['name']
            field_value = request.form.get(field_name, '').strip()
            
            # Validation des champs requis
            if field['required'] and not field_value:
                errors.append(f"Le champ '{field['label']}' est requis")
                continue
            
            # Validation spécifique par type
            if field_value:  # Seulement si la valeur n'est pas vide
                if field['type'] == 'email' and '@' not in field_value:
                    errors.append(f"'{field['label']}' doit être un email valide")
                elif field['type'] == 'number':
                    try:
                        field_value = int(field_value)
                    except ValueError:
                        errors.append(f"'{field['label']}' doit être un nombre")
            
            form_data[field_name] = field_value
        
        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            # Enregistrement en base de données
            try:
                save_form_entry(form_db_path, fields, form_data)
                flash(f'Données enregistrées avec succès dans "{form_info["title"]}" !', 'success')
                return redirect(url_for('dynamic_form', form_name=form_name))
            except Exception as e:
                flash(f'Erreur lors de l\'enregistrement : {str(e)}', 'error')
    
    # Récupération des entrées existantes pour affichage
    try:
        entries = get_form_entries(form_db_path)
    except:
        entries = []
    
    # Récupération de tous les formulaires pour la sidebar
    all_forms = conn.execute('SELECT * FROM forms ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('dynamic_form.html', 
                         form_info=form_info, 
                         fields=fields, 
                         entries=entries,
                         forms=all_forms,
                         current_form=form_name)

@app.route('/delete-form/<form_name>', methods=['POST'])
def delete_form(form_name):
    """Route pour supprimer un formulaire et sa base de données"""
    try:
        # Récupérer les informations du formulaire
        conn = get_db_connection()
        form_info = conn.execute(
            'SELECT * FROM forms WHERE name = ?', (form_name,)
        ).fetchone()
        
        if not form_info:
            flash('Formulaire non trouvé', 'error')
            return redirect(url_for('index'))
        
        # Supprimer le fichier de base de données
        db_path = os.path.join(DATABASE_DIR, form_info['database_file'])
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"🗑️ Fichier supprimé : {db_path}")
        
        # Supprimer l'entrée de la table forms
        cursor = conn.cursor()
        cursor.execute('DELETE FROM forms WHERE name = ?', (form_name,))
        conn.commit()
        conn.close()
        
        flash(f'Formulaire "{form_info["title"]}" supprimé avec succès !', 'success')
        print(f"🗑️ Formulaire '{form_name}' supprimé")
        
    except Exception as e:
        flash(f'Erreur lors de la suppression : {str(e)}', 'error')
        print(f"❌ Erreur suppression : {str(e)}")
    
    return redirect(url_for('index'))

@app.route('/edit-form/<form_name>', methods=['GET', 'POST'])
def edit_form(form_name):
    """Route pour modifier un formulaire existant"""
    # Récupérer les informations du formulaire
    conn = get_db_connection()
    form_info = conn.execute(
        'SELECT * FROM forms WHERE name = ?', (form_name,)
    ).fetchone()
    
    if not form_info:
        flash('Formulaire non trouvé', 'error')
        return redirect(url_for('index'))
    
    # Parser les champs actuels
    try:
        current_fields = json.loads(form_info['fields'])
    except:
        flash('Erreur dans la configuration du formulaire', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Récupération des nouvelles données
        new_form_title = request.form.get('form_title', '').strip()
        new_form_description = request.form.get('form_description', '').strip()
        
        # Récupération des champs modifiés
        field_names = request.form.getlist('field_name[]')
        field_labels = request.form.getlist('field_label[]')
        field_types = request.form.getlist('field_type[]')
        field_required = request.form.getlist('field_required[]')
        
        # Validation
        if not new_form_title:
            flash('Le titre du formulaire est requis', 'error')
        elif not field_names or len(field_names) == 0:
            flash('Au moins un champ est requis', 'error')
        else:
            # Construction de la nouvelle structure des champs
            new_fields = []
            for i, name in enumerate(field_names):
                if name and i < len(field_labels) and i < len(field_types):
                    new_fields.append({
                        'name': name.strip(),
                        'label': field_labels[i].strip(),
                        'type': field_types[i],
                        'required': str(i) in field_required
                    })
            
            if not new_fields:
                flash('Aucun champ valide défini', 'error')
            else:
                try:
                    # Modifier la structure de la base de données si nécessaire
                    db_path = os.path.join(DATABASE_DIR, form_info['database_file'])
                    update_database_structure(db_path, current_fields, new_fields)
                    
                    # Mettre à jour les informations du formulaire
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE forms 
                        SET title = ?, description = ?, fields = ?
                        WHERE name = ?
                    ''', (new_form_title, new_form_description, json.dumps(new_fields), form_name))
                    
                    conn.commit()
                    
                    flash(f'Formulaire "{new_form_title}" modifié avec succès !', 'success')
                    return redirect(url_for('dynamic_form', form_name=form_name))
                    
                except Exception as e:
                    flash(f'Erreur lors de la modification : {str(e)}', 'error')
    
    conn.close()
    return render_template('edit_form.html', 
                         form_info=form_info, 
                         fields=current_fields,
                         form_name=form_name)

@app.route('/', methods=['GET', 'POST'])
def index():
    """Route principale pour afficher le formulaire et traiter l'enregistrement"""
    if request.method == 'POST':
        # Récupération des données du formulaire
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        age = request.form.get('age', '').strip()
        
        # Validation des données
        errors = []
        if not nom:
            errors.append('Le nom est requis')
        if not prenom:
            errors.append('Le prénom est requis')
        if not age:
            errors.append('L\'âge est requis')
        else:
            try:
                age = int(age)
                if age < 0 or age > 150:
                    errors.append('L\'âge doit être entre 0 et 150 ans')
            except ValueError:
                errors.append('L\'âge doit être un nombre valide')
        
        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            # Enregistrement en base de données
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO users (nom, prenom, age) VALUES (?, ?, ?)',
                    (nom, prenom, age)
                )
                conn.commit()
                conn.close()
                flash(f'Utilisateur {prenom} {nom} enregistré avec succès !', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'Erreur lors de l\'enregistrement : {str(e)}', 'error')
    
    # Récupération de tous les utilisateurs pour affichage
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    
    # Récupération de tous les formulaires pour la sidebar
    forms = conn.execute('SELECT * FROM forms ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('index.html', users=users, forms=forms)

@app.route('/api/users', methods=['GET'])
def api_users():
    """API pour récupérer la liste des utilisateurs en JSON"""
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    
    users_list = []
    for user in users:
        users_list.append({
            'id': user['id'],
            'nom': user['nom'],
            'prenom': user['prenom'],
            'age': user['age'],
            'created_at': user['created_at']
        })
    
    return jsonify(users_list)

if __name__ == '__main__':
    # Initialisation de la base de données au démarrage
    init_db()
    print("🚀 Serveur Flask démarré sur http://localhost:8000")
    print("📊 Base de données SQLite initialisée")
    app.run(debug=True, host='0.0.0.0', port=8000) 