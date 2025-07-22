from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import os
import json
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'votre_clé_secrète_ici'  # Changez ceci en production

# Configuration Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'info'

# Classe User pour Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email, created_at):
        self.id = id
        self.username = username
        self.email = email
        self.created_at = created_at

@login_manager.user_loader
def load_user(user_id):
    """Charge un utilisateur à partir de son ID"""
    try:
        conn = get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['email'], user_data['created_at'])
        return None
    except sqlite3.OperationalError:
        # La table n'existe pas encore (premier démarrage)
        return None

# ===== ROUTES D'AUTHENTIFICATION =====

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Route d'inscription"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validation des données
        errors = []
        if not username or len(username) < 3:
            errors.append('Le nom d\'utilisateur doit contenir au moins 3 caractères')
        if not email or '@' not in email:
            errors.append('Veuillez saisir un email valide')
        if not password or len(password) < 6:
            errors.append('Le mot de passe doit contenir au moins 6 caractères')
        if password != confirm_password:
            errors.append('Les mots de passe ne correspondent pas')
        
        if not errors:
            try:
                # Vérifier si l'utilisateur existe déjà
                conn = get_db_connection()
                existing_user = conn.execute(
                    'SELECT id FROM users WHERE username = ? OR email = ?', 
                    (username, email)
                ).fetchone()
                
                if existing_user:
                    flash('Ce nom d\'utilisateur ou email est déjà utilisé', 'error')
                else:
                    # Créer le nouvel utilisateur
                    password_hash = generate_password_hash(password)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO users (username, email, password_hash)
                        VALUES (?, ?, ?)
                    ''', (username, email, password_hash))
                    
                    user_id = cursor.lastrowid
                    conn.commit()
                    
                    # Connecter automatiquement l'utilisateur
                    user = User(user_id, username, email, None)
                    login_user(user)
                    
                    flash(f'Compte créé avec succès ! Bienvenue {username} !', 'success')
                    return redirect(url_for('index'))
                    
                conn.close()
                
            except Exception as e:
                flash(f'Erreur lors de la création du compte : {str(e)}', 'error')
        else:
            for error in errors:
                flash(error, 'error')
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Route de connexion"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = bool(request.form.get('remember'))
        
        if not username or not password:
            flash('Veuillez saisir votre nom d\'utilisateur et mot de passe', 'error')
        else:
            # Rechercher l'utilisateur
            conn = get_db_connection()
            user_data = conn.execute(
                'SELECT * FROM users WHERE username = ? OR email = ?', 
                (username, username)
            ).fetchone()
            conn.close()
            
            if user_data and check_password_hash(user_data['password_hash'], password):
                user = User(user_data['id'], user_data['username'], user_data['email'], user_data['created_at'])
                login_user(user, remember=remember)
                flash(f'Connexion réussie ! Bonjour {user.username} !', 'success')
                
                # Rediriger vers la page demandée ou l'accueil
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                flash('Nom d\'utilisateur ou mot de passe incorrect', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    """Route de déconnexion"""
    username = current_user.username
    logout_user()
    flash(f'Déconnexion réussie ! À bientôt {username} !', 'success')
    return redirect(url_for('login'))

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
    
    # Table pour stocker les utilisateurs (authentification)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table pour stocker les formulaires créés (maintenant liés aux utilisateurs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            fields TEXT NOT NULL,
            database_file TEXT NOT NULL,
            public_token TEXT UNIQUE,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(name, user_id)
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
        if field_type in ['text', 'email', 'tel', 'textarea', 'textarea_rich', 'select', 'radio']:
            sql_type = 'TEXT'
        elif field_type == 'number':
            sql_type = 'INTEGER'
        elif field_type == 'date':
            sql_type = 'DATE'
        elif field_type in ['multiselect', 'checkbox']:
            sql_type = 'TEXT'  # Stocké en JSON pour les sélections multiples
        elif field_type == 'file':
            sql_type = 'TEXT'  # Stocké le chemin/nom du fichier
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

def get_single_entry(db_path, entry_id):
    """Récupère une entrée spécifique par son ID"""
    if not os.path.exists(db_path):
        return None
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        entry = cursor.execute('SELECT * FROM entries WHERE id = ?', (entry_id,)).fetchone()
        conn.close()
        return entry
    except:
        conn.close()
        return None

def update_form_entry(db_path, fields, form_data, entry_id):
    """Met à jour une entrée existante dans la base de données"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Construction de la requête UPDATE
    field_names = [field['name'] for field in fields]
    set_clause = ', '.join([f"{field_name} = ?" for field_name in field_names])
    
    sql = f"UPDATE entries SET {set_clause} WHERE id = ?"
    values = [form_data.get(field_name, '') for field_name in field_names]
    values.append(entry_id)
    
    cursor.execute(sql, values)
    conn.commit()
    conn.close()
    
    print(f"✅ Entrée {entry_id} mise à jour dans {db_path}")

def delete_form_entry(db_path, entry_id):
    """Supprime une entrée de la base de données"""
    if not os.path.exists(db_path):
        raise Exception("Base de données non trouvée")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM entries WHERE id = ?', (entry_id,))
        if cursor.rowcount == 0:
            raise Exception("Entrée non trouvée")
        
        conn.commit()
        conn.close()
        print(f"🗑️ Entrée {entry_id} supprimée de {db_path}")
        
    except Exception as e:
        conn.close()
        raise e

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
@login_required
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
        field_options = request.form.getlist('field_options[]')
        
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
                    field_data = {
                        'name': name.strip(),
                        'label': field_labels[i].strip(),
                        'type': field_types[i],
                        'required': str(i) in field_required
                    }
                    
                    # Ajouter les options pour les types qui en ont besoin
                    if field_types[i] in ['select', 'multiselect', 'radio', 'checkbox'] and i < len(field_options):
                        options_text = field_options[i].strip()
                        if options_text:
                            # Diviser les options par ligne et nettoyer
                            options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]
                            field_data['options'] = options
                        else:
                            field_data['options'] = []
                    
                    fields.append(field_data)
            
            if not fields:
                flash('Aucun champ valide défini', 'error')
            else:
                try:
                    # Créer le nom du fichier de base de données
                    db_filename = f"{form_name}.db"
                    db_path = os.path.join(DATABASE_DIR, db_filename)
                    
                    # Créer la table dans la nouvelle base de données
                    create_custom_form_database(db_path, fields)
                    
                    # Générer un token unique pour l'accès public
                    public_token = secrets.token_urlsafe(32)
                    
                    # Enregistrer le formulaire dans la base principale
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO forms (name, title, description, fields, database_file, public_token, user_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (form_name, form_title, form_description, json.dumps(fields), db_filename, public_token, current_user.id))
                    
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
@login_required
def dynamic_form(form_name):
    """Route pour afficher et traiter un formulaire dynamique de l'utilisateur connecté"""
    # Récupérer les informations du formulaire (uniquement ceux de l'utilisateur connecté)
    conn = get_db_connection()
    form_info = conn.execute(
        'SELECT * FROM forms WHERE name = ? AND user_id = ?', (form_name, current_user.id)
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
    
    # Récupération des formulaires de l'utilisateur connecté pour la sidebar
    all_forms = conn.execute(
        'SELECT * FROM forms WHERE user_id = ? ORDER BY created_at DESC', 
        (current_user.id,)
    ).fetchall()
    conn.close()
    
    return render_template('dynamic_form.html', 
                         form_info=form_info, 
                         fields=fields, 
                         entries=entries,
                         forms=all_forms,
                         current_form=form_name)

@app.route('/delete-form/<form_name>', methods=['POST'])
@login_required
def delete_form(form_name):
    """Route pour supprimer un formulaire et sa base de données (uniquement le propriétaire)"""
    try:
        # Récupérer les informations du formulaire (vérifier la propriété)
        conn = get_db_connection()
        form_info = conn.execute(
            'SELECT * FROM forms WHERE name = ? AND user_id = ?', (form_name, current_user.id)
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
@login_required
def edit_form(form_name):
    """Route pour modifier un formulaire existant (uniquement le propriétaire)"""
    # Récupérer les informations du formulaire (vérifier la propriété)
    conn = get_db_connection()
    form_info = conn.execute(
        'SELECT * FROM forms WHERE name = ? AND user_id = ?', (form_name, current_user.id)
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

@app.route('/edit-entry/<form_name>/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def edit_entry(form_name, entry_id):
    """Route pour modifier une entrée spécifique (uniquement le propriétaire du formulaire)"""
    # Récupérer les informations du formulaire (vérifier la propriété)
    conn = get_db_connection()
    form_info = conn.execute(
        'SELECT * FROM forms WHERE name = ? AND user_id = ?', (form_name, current_user.id)
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
    
    # Construire le chemin de la base de données
    form_db_path = os.path.join(DATABASE_DIR, form_info['database_file'])
    
    # Récupérer l'entrée à modifier
    try:
        entry = get_single_entry(form_db_path, entry_id)
        if not entry:
            flash('Entrée non trouvée', 'error')
            return redirect(url_for('dynamic_form', form_name=form_name))
    except:
        flash('Erreur lors de la récupération de l\'entrée', 'error')
        return redirect(url_for('dynamic_form', form_name=form_name))
    
    if request.method == 'POST':
        # Traitement de la modification
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
            if field_value:
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
            # Mise à jour en base de données
            try:
                update_form_entry(form_db_path, fields, form_data, entry_id)
                flash('Entrée modifiée avec succès !', 'success')
                return redirect(url_for('dynamic_form', form_name=form_name))
            except Exception as e:
                flash(f'Erreur lors de la modification : {str(e)}', 'error')
    
    conn.close()
    return render_template('edit_entry.html', 
                         form_info=form_info, 
                         fields=fields, 
                         entry=entry,
                         form_name=form_name,
                         entry_id=entry_id)

@app.route('/delete-entry/<form_name>/<int:entry_id>', methods=['POST'])
@login_required
def delete_entry(form_name, entry_id):
    try:
        # Vérifier que l'utilisateur est propriétaire du formulaire
        conn = get_db_connection()
        form_info = conn.execute(
            'SELECT * FROM forms WHERE name = ? AND user_id = ?', (form_name, current_user.id)
        ).fetchone()
        conn.close()
        
        if not form_info:
            flash('Formulaire non trouvé ou accès refusé', 'error')
            return redirect(url_for('index'))
        
        db_path = os.path.join(DATABASE_DIR, f'{form_name}.db')
        delete_form_entry(db_path, entry_id)
        flash('Entrée supprimée avec succès!', 'success')
    except Exception as e:
        flash(f'Erreur lors de la suppression: {str(e)}', 'error')
    
    return redirect(f'/form/{form_name}')

# ===== API REST ENDPOINTS =====

@app.route('/api/forms', methods=['GET'])
def api_get_forms():
    """GET /api/forms - Liste de tous les formulaires"""
    try:
        conn = get_db_connection()
        forms = conn.execute('SELECT * FROM forms ORDER BY created_at DESC').fetchall()
        conn.close()
        
        forms_list = []
        for form in forms:
            forms_list.append({
                'id': form['id'],
                'name': form['name'],
                'title': form['title'],
                'description': form['description'],
                'fields': json.loads(form['fields']),
                'database_file': form['database_file'],
                'created_at': form['created_at']
            })
        
        return jsonify({
            'success': True,
            'data': forms_list,
            'count': len(forms_list)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/forms/<form_name>/schema', methods=['GET'])
def api_get_form_schema(form_name):
    """GET /api/forms/{form_name}/schema - Schéma d'un formulaire"""
    try:
        conn = get_db_connection()
        form = conn.execute('SELECT * FROM forms WHERE name = ?', (form_name,)).fetchone()
        conn.close()
        
        if not form:
            return jsonify({
                'success': False,
                'error': 'Formulaire non trouvé'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'name': form['name'],
                'title': form['title'],
                'description': form['description'],
                'fields': json.loads(form['fields']),
                'created_at': form['created_at']
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/forms/<form_name>/entries', methods=['GET'])
def api_get_entries(form_name):
    """GET /api/forms/{form_name}/entries - Liste des entrées d'un formulaire"""
    try:
        # Vérifier que le formulaire existe
        conn = get_db_connection()
        form = conn.execute('SELECT * FROM forms WHERE name = ?', (form_name,)).fetchone()
        conn.close()
        
        if not form:
            return jsonify({
                'success': False,
                'error': 'Formulaire non trouvé'
            }), 404
        
        # Récupérer les entrées
        db_path = os.path.join(DATABASE_DIR, f'{form_name}.db')
        entries = get_form_entries(db_path)
        
        # Convertir en liste de dictionnaires
        entries_list = []
        for entry in entries:
            entry_dict = dict(entry)
            entries_list.append(entry_dict)
        
        return jsonify({
            'success': True,
            'data': entries_list,
            'count': len(entries_list),
            'form_name': form_name
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/forms/<form_name>/entries/<int:entry_id>', methods=['GET'])
def api_get_entry(form_name, entry_id):
    """GET /api/forms/{form_name}/entries/{id} - Récupérer une entrée spécifique"""
    try:
        # Vérifier que le formulaire existe
        conn = get_db_connection()
        form = conn.execute('SELECT * FROM forms WHERE name = ?', (form_name,)).fetchone()
        conn.close()
        
        if not form:
            return jsonify({
                'success': False,
                'error': 'Formulaire non trouvé'
            }), 404
        
        # Récupérer l'entrée
        db_path = os.path.join(DATABASE_DIR, f'{form_name}.db')
        entry = get_single_entry(db_path, entry_id)
        
        if not entry:
            return jsonify({
                'success': False,
                'error': 'Entrée non trouvée'
            }), 404
        
        return jsonify({
            'success': True,
            'data': dict(entry),
            'form_name': form_name
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/forms/<form_name>/entries', methods=['POST'])
def api_create_entry(form_name):
    """POST /api/forms/{form_name}/entries - Créer une nouvelle entrée"""
    try:
        # Vérifier que le formulaire existe et récupérer le schéma
        conn = get_db_connection()
        form = conn.execute('SELECT * FROM forms WHERE name = ?', (form_name,)).fetchone()
        conn.close()
        
        if not form:
            return jsonify({
                'success': False,
                'error': 'Formulaire non trouvé'
            }), 404
        
        fields = json.loads(form['fields'])
        
        # Récupérer les données JSON de la requête
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type doit être application/json'
            }), 400
        
        data = request.get_json()
        
        # Valider les champs requis
        errors = []
        for field in fields:
            if field['required'] and (field['name'] not in data or not data[field['name']]):
                errors.append(f"Le champ '{field['label']}' est requis")
        
        if errors:
            return jsonify({
                'success': False,
                'error': 'Données invalides',
                'details': errors
            }), 400
        
        # Sauvegarder l'entrée
        db_path = os.path.join(DATABASE_DIR, f'{form_name}.db')
        save_form_entry(db_path, fields, data)
        
        return jsonify({
            'success': True,
            'message': 'Entrée créée avec succès',
            'form_name': form_name
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/forms/<form_name>/entries/<int:entry_id>', methods=['PUT'])
def api_update_entry(form_name, entry_id):
    """PUT /api/forms/{form_name}/entries/{id} - Modifier une entrée"""
    try:
        # Vérifier que le formulaire existe et récupérer le schéma
        conn = get_db_connection()
        form = conn.execute('SELECT * FROM forms WHERE name = ?', (form_name,)).fetchone()
        conn.close()
        
        if not form:
            return jsonify({
                'success': False,
                'error': 'Formulaire non trouvé'
            }), 404
        
        fields = json.loads(form['fields'])
        
        # Vérifier que l'entrée existe
        db_path = os.path.join(DATABASE_DIR, f'{form_name}.db')
        existing_entry = get_single_entry(db_path, entry_id)
        
        if not existing_entry:
            return jsonify({
                'success': False,
                'error': 'Entrée non trouvée'
            }), 404
        
        # Récupérer les données JSON de la requête
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type doit être application/json'
            }), 400
        
        data = request.get_json()
        
        # Valider les champs requis
        errors = []
        for field in fields:
            if field['required'] and (field['name'] not in data or not data[field['name']]):
                errors.append(f"Le champ '{field['label']}' est requis")
        
        if errors:
            return jsonify({
                'success': False,
                'error': 'Données invalides',
                'details': errors
            }), 400
        
        # Mettre à jour l'entrée
        update_form_entry(db_path, fields, data, entry_id)
        
        return jsonify({
            'success': True,
            'message': 'Entrée modifiée avec succès',
            'form_name': form_name,
            'entry_id': entry_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/forms/<form_name>/entries/<int:entry_id>', methods=['DELETE'])
def api_delete_entry(form_name, entry_id):
    """DELETE /api/forms/{form_name}/entries/{id} - Supprimer une entrée"""
    try:
        # Vérifier que le formulaire existe
        conn = get_db_connection()
        form = conn.execute('SELECT * FROM forms WHERE name = ?', (form_name,)).fetchone()
        conn.close()
        
        if not form:
            return jsonify({
                'success': False,
                'error': 'Formulaire non trouvé'
            }), 404
        
        # Vérifier que l'entrée existe et la supprimer
        db_path = os.path.join(DATABASE_DIR, f'{form_name}.db')
        existing_entry = get_single_entry(db_path, entry_id)
        
        if not existing_entry:
            return jsonify({
                'success': False,
                'error': 'Entrée non trouvée'
            }), 404
        
        delete_form_entry(db_path, entry_id)
        
        return jsonify({
            'success': True,
            'message': 'Entrée supprimée avec succès',
            'form_name': form_name,
            'entry_id': entry_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== API DOCUMENTATION ENDPOINT =====

@app.route('/form/<form_name>/integration', methods=['GET'])
@login_required
def form_integration(form_name):
    """Page d'intégration API spécifique à un formulaire (uniquement le propriétaire)"""
    # Récupérer les informations du formulaire (vérifier la propriété)
    conn = get_db_connection()
    form_info = conn.execute(
        'SELECT * FROM forms WHERE name = ? AND user_id = ?', (form_name, current_user.id)
    ).fetchone()
    
    if not form_info:
        flash('Formulaire non trouvé', 'error')
        return redirect(url_for('index'))
    
    # Parser les champs
    try:
        fields = json.loads(form_info['fields'])
    except:
        flash('Erreur dans la configuration du formulaire', 'error')
        return redirect(url_for('index'))
    
    # Récupération des formulaires de l'utilisateur connecté pour la sidebar
    all_forms = conn.execute(
        'SELECT * FROM forms WHERE user_id = ? ORDER BY created_at DESC', 
        (current_user.id,)
    ).fetchall()
    conn.close()
    
    # Générer un exemple de données pour ce formulaire
    example_data = {}
    for field in fields:
        if field['type'] == 'text':
            example_data[field['name']] = f"Exemple {field['label'].lower()}"
        elif field['type'] == 'email':
            example_data[field['name']] = "exemple@domain.com"
        elif field['type'] == 'number':
            example_data[field['name']] = 25
        elif field['type'] == 'date':
            example_data[field['name']] = "2024-01-15"
        elif field['type'] == 'textarea':
            example_data[field['name']] = f"Contenu exemple pour {field['label'].lower()}"
        else:
            example_data[field['name']] = f"Valeur {field['label'].lower()}"
    
    return render_template('integration.html', 
                         form_info=form_info, 
                         fields=fields,
                         forms=all_forms,
                         current_form=form_name,
                         example_data=example_data,
                         base_url=request.host_url.rstrip('/'))

@app.route('/public/<token>', methods=['GET', 'POST'])
def public_form(token):
    """Formulaire public accessible via un token unique"""
    # Récupérer le formulaire par son token
    conn = get_db_connection()
    form_info = conn.execute(
        'SELECT * FROM forms WHERE public_token = ?', (token,)
    ).fetchone()
    
    if not form_info:
        return render_template('public_error.html'), 404
    
    # Parser les champs
    try:
        fields = json.loads(form_info['fields'])
    except:
        return render_template('public_error.html'), 500
    
    if request.method == 'POST':
        # Traitement de la soumission du formulaire public
        form_data = {}
        errors = []
        
        # Validation des champs
        for field in fields:
            field_name = field['name']
            field_value = request.form.get(field_name, '').strip()
            
            # Vérification des champs requis
            if field['required'] and not field_value:
                errors.append(f"Le champ '{field['label']}' est requis")
                continue
            
            # Validation selon le type
            if field['type'] == 'email' and field_value:
                if '@' not in field_value:
                    errors.append(f"'{field['label']}' doit être un email valide")
            elif field['type'] == 'number' and field_value:
                try:
                    field_value = int(field_value)
                except:
                    errors.append(f"'{field['label']}' doit être un nombre")
            
            form_data[field_name] = field_value
        
        if errors:
            conn.close()
            return render_template('public_form.html', 
                                 form_info=form_info, 
                                 fields=fields,
                                 errors=errors,
                                 form_data=form_data)
        else:
            # Enregistrement en base de données
            try:
                form_db_path = os.path.join(DATABASE_DIR, form_info['database_file'])
                save_form_entry(form_db_path, fields, form_data)
                conn.close()
                return render_template('public_success.html', form_info=form_info)
            except Exception as e:
                conn.close()
                return render_template('public_form.html', 
                                     form_info=form_info, 
                                     fields=fields,
                                     errors=[f'Erreur lors de l\'enregistrement : {str(e)}'],
                                     form_data=form_data)
    
    conn.close()
    return render_template('public_form.html', 
                         form_info=form_info, 
                         fields=fields,
                         errors=[],
                         form_data={})

@app.route('/api/docs', methods=['GET'])
def api_documentation():
    """Documentation de l'API REST"""
    docs = {
        'title': 'FormCraft API REST',
        'version': '1.0.0',
        'description': 'API REST pour gérer les formulaires dynamiques et leurs données',
        'base_url': request.host_url + 'api',
        'endpoints': {
            'forms': {
                'GET /api/forms': {
                    'description': 'Liste de tous les formulaires',
                    'response': 'JSON avec liste des formulaires'
                },
                'GET /api/forms/{form_name}/schema': {
                    'description': 'Schéma d\'un formulaire spécifique',
                    'response': 'JSON avec définition des champs'
                }
            },
            'entries': {
                'GET /api/forms/{form_name}/entries': {
                    'description': 'Liste des entrées d\'un formulaire',
                    'response': 'JSON avec liste des entrées'
                },
                'POST /api/forms/{form_name}/entries': {
                    'description': 'Créer une nouvelle entrée',
                    'content_type': 'application/json',
                    'response': 'JSON avec confirmation'
                },
                'GET /api/forms/{form_name}/entries/{id}': {
                    'description': 'Récupérer une entrée spécifique',
                    'response': 'JSON avec les données de l\'entrée'
                },
                'PUT /api/forms/{form_name}/entries/{id}': {
                    'description': 'Modifier une entrée existante',
                    'content_type': 'application/json',
                    'response': 'JSON avec confirmation'
                },
                'DELETE /api/forms/{form_name}/entries/{id}': {
                    'description': 'Supprimer une entrée',
                    'response': 'JSON avec confirmation'
                }
            }
        },
        'examples': {
            'create_entry': {
                'url': '/api/forms/contact/entries',
                'method': 'POST',
                'headers': {'Content-Type': 'application/json'},
                'body': {
                    'nom': 'Dupont',
                    'email': 'dupont@example.com',
                    'message': 'Bonjour, j\'aimerais plus d\'informations'
                }
            },
            'get_entries': {
                'url': '/api/forms/contact/entries',
                'method': 'GET',
                'response_example': {
                    'success': True,
                    'data': [
                        {
                            'id': 1,
                            'nom': 'Dupont',
                            'email': 'dupont@example.com',
                            'created_at': '2024-01-15 10:30:00'
                        }
                    ],
                    'count': 1
                }
            }
        }
    }
    
    return jsonify(docs)

@app.route('/', methods=['GET'])
@login_required
def index():
    """Route principale pour afficher le dashboard des formulaires de l'utilisateur connecté"""
    # Récupération des formulaires de l'utilisateur connecté uniquement
    conn = get_db_connection()
    forms = conn.execute(
        'SELECT * FROM forms WHERE user_id = ? ORDER BY created_at DESC', 
        (current_user.id,)
    ).fetchall()
    conn.close()
    
    return render_template('index.html', forms=forms)



if __name__ == '__main__':
    # Initialisation de la base de données au démarrage
    init_db()
    print("🚀 Serveur Flask démarré sur http://localhost:8000")
    print("📊 Base de données SQLite initialisée")
    app.run(debug=True, host='0.0.0.0', port=8000) 