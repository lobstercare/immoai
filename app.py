from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file
import os
import json
import uuid
import re
from datetime import datetime
import base64
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
import folium
import pdfkit
import io
import requests
from flask import send_from_directory
import time

# Load environment variables
load_dotenv()

# Set up OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Test API key validity without blocking app startup
def test_openai_connection():
    try:
        # Just a simple API call to test connectivity
        client.models.list()
        return True
    except Exception as e:
        print(f"Warning: OpenAI API connection issue: {str(e)}")
        return False

# Check connection but don't block startup
api_connected = test_openai_connection()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_key_for_testing")

# Upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
DOCUMENTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'documents')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'xlsx', 'xls', 'csv'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOCUMENTS_FOLDER'] = DOCUMENTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOCUMENTS_FOLDER, exist_ok=True)

# Route to serve uploaded files
@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Route to serve documents
@app.route('/documents/<path:filename>')
def serve_documents(filename):
    """
    Servir les fichiers de documents
    """
    return send_from_directory(app.config['DOCUMENTS_FOLDER'], filename)

# Database functions
def get_database():
    """Load the database from the JSON file or create a new one if it doesn't exist."""
    db_path = os.path.join(os.path.dirname(__file__), 'database.json')
    if os.path.exists(db_path):
        with open(db_path, 'r') as f:
            db = json.load(f)
            # Ensure next_property_id exists
            if 'next_property_id' not in db:
                db['next_property_id'] = 1
                # If there are existing properties, set next_property_id to max id + 1
                if 'properties' in db and db['properties']:
                    # Filter out properties that are not dictionaries
                    valid_properties = [prop for prop in db['properties'] if isinstance(prop, dict)]
                    if valid_properties:
                        max_id = max([int(prop.get('id', 0)) for prop in valid_properties if prop.get('id', '').isdigit()])
                        db['next_property_id'] = max_id + 1
            return db
    else:
        # Create a new database structure
        return {
            'users': {},
            'properties': [],
            'next_property_id': 1
        }

def save_database(db):
    """Save the database to the JSON file."""
    db_path = os.path.join(os.path.dirname(__file__), 'database.json')
    with open(db_path, 'w') as f:
        json.dump(db, f, indent=4)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_document_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOCUMENT_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        db = get_database()
        if email in db['users'] and db['users'][email]['password'] == password:
            session['user'] = email
            session['agency_name'] = db['users'][email].get('agency_name', '')
            flash('Connexion réussie!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou mot de passe incorrect', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        agency_name = request.form.get('agency_name')
        
        db = get_database()
        if email in db['users']:
            flash('Cet email est déjà utilisé', 'danger')
        else:
            db['users'][email] = {
                'password': password,
                'agency_name': agency_name,
                'created_at': datetime.now().isoformat()
            }
            save_database(db)
            flash('Inscription réussie! Veuillez vous connecter', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('agency_name', None)
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Veuillez vous connecter pour accéder à cette page', 'warning')
        return redirect(url_for('login'))
    
    db = get_database()
    user_properties = []
    
    # Vérifier si properties est une liste (nouveau format) ou un dictionnaire (ancien format)
    if isinstance(db['properties'], list):
        # Format liste
        for prop in db['properties']:
            if prop.get('owner') == session['user']:
                # S'assurer que chaque propriété a un attribut id
                if 'id' not in prop:
                    prop['id'] = prop.get('property_id', 0)
                user_properties.append(prop)
    else:
        # Format dictionnaire (pour compatibilité avec ancienne version)
        for prop_id, prop in db['properties'].items():
            if prop.get('owner') == session['user']:
                user_properties.append({
                    'id': prop_id,
                    **prop
                })
    
    return render_template('dashboard.html', properties=user_properties)

@app.route('/new-property', methods=['GET', 'POST'])
def new_property():
    if 'user' not in session:
        flash('Veuillez vous connecter pour accéder à cette page', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        property_type = request.form.get('property_type')
        transaction_type = request.form.get('transaction_type')
        price = request.form.get('price')
        area = request.form.get('area')
        rooms = request.form.get('rooms')
        address = request.form.get('address')
        city = request.form.get('city')
        postal_code = request.form.get('postal_code')
        
        # Validation basique
        if not all([title, property_type, transaction_type, price, area, address, city, postal_code]):
            flash('Veuillez remplir tous les champs obligatoires', 'danger')
            return redirect(url_for('new_property'))
        
        # Générer un ID unique pour la propriété
        db = get_database()
        property_id = db['next_property_id']
        db['next_property_id'] += 1
        
        # Créer les dossiers nécessaires s'ils n'existent pas
        property_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'properties', str(property_id))
        os.makedirs(property_folder, exist_ok=True)
        dpe_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'dpe')
        os.makedirs(dpe_folder, exist_ok=True)
        
        # Traiter les images
        images = []
        try:
            if 'images' in request.files:
                files = request.files.getlist('images')
                for i, file in enumerate(files):
                    if file and file.filename and allowed_file(file.filename):
                        try:
                            filename = secure_filename(f"{property_id}_image_{i}_{file.filename}")
                            filepath = os.path.join(property_folder, filename)
                            file.save(filepath)
                            # Utiliser des chemins avec des slashes avant pour le stockage
                            relative_path = os.path.join('properties', str(property_id), filename).replace('\\', '/')
                            
                            # Créer un objet image avec chemin et description
                            image_obj = {
                                'path': relative_path,
                                'description': f"Image {i+1} de la propriété"  # Description par défaut
                            }
                            images.append(image_obj)
                            
                            print(f"Image saved: {filepath}")
                            print(f"Image path stored: {relative_path}")
                        except Exception as e:
                            print(f"Erreur lors du traitement de l'image {file.filename}: {str(e)}")
                            # Continuer avec les autres images
        except Exception as e:
            print(f"Erreur lors du traitement des images: {str(e)}")
            # Continuer sans images si nécessaire
        
        # Traiter le DPE
        dpe_file = None
        try:
            if 'dpe' in request.files and request.files['dpe'].filename:
                file = request.files['dpe']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"dpe_{property_id}_{file.filename}")
                    filepath = os.path.join(dpe_folder, filename)
                    file.save(filepath)
                    # Utiliser des chemins avec des slashes avant pour le stockage
                    dpe_file = os.path.join('dpe', filename).replace('\\', '/')
                    print(f"DPE saved: {filepath}")
                    print(f"DPE path stored: {dpe_file}")
        except Exception as e:
            print(f"Erreur lors du traitement du DPE: {str(e)}")
            # Continuer sans DPE si nécessaire
        
        # Créer l'entrée dans la base de données
        try:
            # Ensure properties is a list
            if 'properties' not in db:
                db['properties'] = []
            elif not isinstance(db['properties'], list):
                db['properties'] = []
                
            db['properties'].append({
                'id': property_id,
                'title': title,
                'description': description,
                'property_type': property_type,
                'transaction_type': transaction_type,
                'price': price,
                'area': area,
                'rooms': rooms,
                'address': address,
                'city': city,
                'postal_code': postal_code,
                'images': images,
                'dpe_file': dpe_file,
                'owner': session['user'],
                'agency_name': session.get('agency_name', ''),
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            })
            save_database(db)
            
            flash('Annonce créée avec succès!', 'success')
            return redirect(url_for('property_preview', property_id=property_id))
        except Exception as e:
            print(f"Erreur lors de la création de l'annonce: {str(e)}")
            flash('Une erreur est survenue lors de la création de l\'annonce. Veuillez réessayer.', 'danger')
            return redirect(url_for('new_property'))
    
    return render_template('new_property.html')

@app.route('/property/<property_id>')
def property_preview(property_id):
    if 'user' not in session:
        flash('Veuillez vous connecter pour accéder à cette page', 'warning')
        return redirect(url_for('login'))
    
    db = get_database()
    for prop in db['properties']:
        if prop['id'] == int(property_id):
            property_data = prop
            break
    else:
        flash('Propriété non trouvée', 'danger')
        return redirect(url_for('dashboard'))
    
    # Vérifier si l'utilisateur est le propriétaire
    is_owner = property_data['owner'] == session['user']
    
    # S'assurer que les champs numériques sont bien des nombres
    try:
        property_data['rooms'] = int(property_data['rooms']) if property_data.get('rooms') else 0
        property_data['area'] = float(property_data['area']) if property_data.get('area') else 0
        property_data['price'] = float(property_data['price']) if property_data.get('price') else 0
    except (ValueError, TypeError):
        # En cas d'erreur de conversion, on laisse les valeurs telles quelles
        pass
    
    # Générer la carte
    try:
        map_html = generate_map(property_data['address'], property_data['city'], property_data['postal_code'])
    except Exception as e:
        print(f"Erreur lors de la génération de la carte: {str(e)}")
        map_html = "<div class='alert alert-warning'>Impossible de générer la carte</div>"
    
    return render_template('property_preview.html', property=property_data, property_id=property_id, map_html=map_html, is_owner=is_owner)

@app.route('/edit-property/<property_id>', methods=['GET', 'POST'])
def edit_property(property_id):
    if 'user' not in session:
        flash('Veuillez vous connecter pour accéder à cette page', 'warning')
        return redirect(url_for('login'))
    
    db = get_database()
    for prop in db['properties']:
        if prop['id'] == int(property_id):
            property_data = prop
            break
    else:
        flash('Vous n\'avez pas accès à cette propriété', 'danger')
        return redirect(url_for('dashboard'))
    
    if property_data['owner'] != session['user']:
        flash('Vous n\'avez pas accès à cette propriété', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Mettre à jour les données de la propriété
        property_data['title'] = request.form.get('title')
        property_data['description'] = request.form.get('description')
        property_data['property_type'] = request.form.get('property_type')
        property_data['transaction_type'] = request.form.get('transaction_type')
        property_data['price'] = request.form.get('price')
        property_data['area'] = request.form.get('area')
        property_data['rooms'] = request.form.get('rooms')
        property_data['address'] = request.form.get('address')
        property_data['city'] = request.form.get('city')
        property_data['postal_code'] = request.form.get('postal_code')
        
        # Gérer les nouvelles images
        if 'images' in request.files:
            files = request.files.getlist('images')
            property_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'properties', str(property_id))
            os.makedirs(property_folder, exist_ok=True)
            
            # Ajouter de nouvelles images
            next_image_num = len(property_data['images'])
            for file in files:
                if file and file.filename and allowed_file(file.filename):
                    try:
                        filename = secure_filename(f"{property_id}_image_{next_image_num}_{file.filename}")
                        filepath = os.path.join(property_folder, filename)
                        file.save(filepath)
                        # Utiliser des chemins avec des slashes avant pour le stockage
                        relative_path = os.path.join('properties', str(property_id), filename).replace('\\', '/')
                        property_data['images'].append({
                            'path': relative_path,
                            'description': f"Image {next_image_num+1} de la propriété"  # Description par défaut
                        })
                        next_image_num += 1
                    except Exception as e:
                        print(f"Erreur lors du traitement de l'image {file.filename}: {str(e)}")
        
        # Gérer le DPE
        if 'dpe' in request.files and request.files['dpe'].filename:
            file = request.files['dpe']
            if file and allowed_file(file.filename):
                # Supprimer l'ancien DPE s'il existe
                if property_data['dpe_file'] and os.path.exists(os.path.join('static', property_data['dpe_file'])):
                    try:
                        os.remove(os.path.join('static', property_data['dpe_file']))
                    except:
                        pass
                
                # Créer le dossier DPE s'il n'existe pas
                dpe_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'dpe')
                os.makedirs(dpe_folder, exist_ok=True)
                
                filename = secure_filename(f"dpe_{property_id}_{file.filename}")
                filepath = os.path.join(dpe_folder, filename)
                file.save(filepath)
                # Utiliser des chemins avec des slashes avant pour le stockage
                property_data['dpe_file'] = os.path.join('dpe', filename).replace('\\', '/')
        
        # Mettre à jour la date de modification
        property_data['updated_at'] = datetime.now().isoformat()
        
        # Sauvegarder les modifications
        for i, prop in enumerate(db['properties']):
            if prop['id'] == int(property_id):
                db['properties'][i] = property_data
                break
        save_database(db)
        
        flash('Annonce mise à jour avec succès!', 'success')
        return redirect(url_for('property_preview', property_id=property_id))
    
    return render_template('edit_property.html', property=property_data, property_id=property_id)

@app.route('/delete-property/<property_id>', methods=['POST'])
def delete_property(property_id):
    if 'user' not in session:
        flash('Veuillez vous connecter pour accéder à cette page', 'warning')
        return redirect(url_for('login'))
    
    db = get_database()
    for prop in db['properties']:
        if prop['id'] == int(property_id):
            property_data = prop
            break
    else:
        flash('Propriété non trouvée', 'danger')
        return redirect(url_for('dashboard'))
        
    if property_data['owner'] != session['user']:
        flash('Vous n\'avez pas accès à cette propriété', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Supprimer les fichiers associés
        property_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'properties', property_id)
        if os.path.exists(property_folder):
            for file in os.listdir(property_folder):
                file_path = os.path.join(property_folder, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(property_folder)
        
        # Supprimer le DPE s'il existe
        if 'dpe_file' in property_data and property_data['dpe_file']:
            dpe_path = os.path.join('static', property_data['dpe_file'])
            if os.path.exists(dpe_path):
                os.remove(dpe_path)
        
        # Supprimer de la base de données
        for i, prop in enumerate(db['properties']):
            if prop['id'] == int(property_id):
                del db['properties'][i]
                break
        save_database(db)
        
        flash('Annonce supprimée avec succès', 'success')
    except Exception as e:
        print(f"Erreur lors de la suppression: {str(e)}")
        flash('Erreur lors de la suppression de l\'annonce', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/export-pdf/<property_id>')
def export_pdf(property_id):
    if 'user' not in session:
        flash('Veuillez vous connecter pour accéder à cette page', 'warning')
        return redirect(url_for('login'))
    
    db = get_database()
    for prop in db['properties']:
        if prop['id'] == int(property_id):
            property_data = prop
            break
    else:
        flash('Propriété non trouvée', 'danger')
        return redirect(url_for('dashboard'))
    
    # Vérifier que l'utilisateur est le propriétaire de l'annonce
    if property_data['owner'] != session['user']:
        flash('Vous n\'avez pas accès à cette propriété', 'danger')
        return redirect(url_for('dashboard'))
    
    # Générer la carte
    try:
        map_html = generate_map(property_data['address'], property_data['city'], property_data['postal_code'])
    except Exception as e:
        print(f"Erreur lors de la génération de la carte: {str(e)}")
        map_html = "<div class='alert alert-warning'>Impossible de générer la carte</div>"
    
    # Créer un environnement Jinja2 pour le template PDF
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('pdf_template.html')
    
    # Rendre le template avec les données de la propriété
    html_content = template.render(
        property=property_data,
        property_id=property_id,
        map_html=map_html,
        agency_name=session.get('agency_name', 'Votre Agence'),
        export_date=datetime.now().strftime('%d/%m/%Y')
    )
    
    # Générer le PDF à partir du HTML
    pdf_options = {
        'page-size': 'A4',
        'margin-top': '1cm',
        'margin-right': '1cm',
        'margin-bottom': '1cm',
        'margin-left': '1cm',
        'encoding': 'UTF-8',
        'no-outline': None,
        'enable-local-file-access': None
    }
    
    pdf = pdfkit.from_string(html_content, False, options=pdf_options)
    
    # Créer un fichier temporaire pour le PDF
    pdf_io = io.BytesIO(pdf)
    pdf_io.seek(0)
    
    # Générer un nom de fichier pour le téléchargement
    filename = f"annonce_{property_data['property_type']}_{property_data['city']}_{property_id[:8]}.pdf"
    
    # Envoyer le fichier PDF au client
    return send_file(
        pdf_io,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/analyze-image', methods=['POST'])
def analyze_image():
    """
    Endpoint pour analyser une image avec l'API OpenAI Vision
    """
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'File type not allowed'}), 400
    
    try:
        # Generate a unique ID for this upload
        upload_id = request.form.get('upload_id', 'no-id')
        
        # Create a unique filename to avoid collisions
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S%f")
        filename = f"image_{timestamp}_{upload_id}.png"
        
        # Save the file temporarily
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        print(f"File saved temporarily at: {file_path}")
        print(f"Form data: {request.form}")
        
        # Convert the image to base64
        with open(file_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        print(f"Processing upload with ID: {upload_id}")
        print(f"Calling OpenAI Vision API for upload ID: {upload_id}")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Décrivez cette image de bien immobilier en détail, en français. Concentrez-vous sur les aspects importants pour une annonce immobilière comme: le type de pièce, la luminosité, l'aménagement, l'état général, les équipements visibles, etc."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300,  # Increased token limit for more detailed descriptions
        )

        # Get the description from OpenAI
        description = response.choices[0].message.content
        print(f"Got description from OpenAI for upload ID {upload_id}: {description[:100]}...")

        # Generate URL for the saved image
        image_url = url_for('static', filename=f'uploads/{filename}')
        
        # We'll keep the file for now (no deletion)
        
        return jsonify({
            'success': True,
            'description': description,
            'filename': filename,
            'url': image_url,
            'uploadId': upload_id,
            'room_type': 'Pièce',  # Default room type
            'features': []  # Empty features array
        })

    except Exception as api_error:
        print(f"Error analyzing image: {str(api_error)}")
        return jsonify({
            'success': False, 
            'error': f"Error analyzing image: {str(api_error)}"
        }), 500

@app.route('/api/generate-description', methods=['POST'])
def api_generate_description():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    property_type = data.get('property_type', '')
    transaction_type = data.get('transaction_type', '')
    price = data.get('price', '')
    area = data.get('area', '')
    rooms = data.get('rooms', '')
    bedrooms = data.get('bedrooms', '')
    location = data.get('location', '')
    user_description = data.get('user_description', '')
    
    # Construire le prompt pour l'IA
    prompt = f"""
    Génère une description professionnelle et attrayante pour une annonce immobilière avec les caractéristiques suivantes:
    - Type de bien: {property_type}
    - Type de transaction: {transaction_type}
    - Prix: {price}€
    - Surface: {area} m²
    - Nombre de pièces: {rooms}
    - Nombre de chambres: {bedrooms}
    - Localisation: {location}
    
    Description de base fournie par l'utilisateur:
    {user_description}
    
    La description doit être détaillée, mettre en valeur les points forts du bien, et utiliser un langage professionnel adapté au secteur immobilier français.
    Structurez la description en paragraphes avec une introduction, une description des pièces principales, et une conclusion sur l'environnement.
    Assurez-vous d'inclure et de mentionner explicitement toutes les informations fournies (surface, nombre de pièces, localisation, prix si disponible).
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un agent immobilier expérimenté, spécialisé dans la rédaction de descriptions immobilières attrayantes."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # Extraire la description de la réponse
        description = response.choices[0].message.content.strip()
        
        # Si l'API n'est pas disponible, on utilise une description par défaut
        if not description:
            raise Exception("Pas de réponse de l'API")
            
        return jsonify({'description': description})
    
    except Exception as e:
        print(f"Erreur lors de la génération de la description: {str(e)}")
        return jsonify({"error": "Erreur lors de la génération de la description"}), 500

@app.route('/api/generate-title-suggestions', methods=['POST'])
def api_generate_title_suggestions():
    """
    Générer des suggestions de titres pour une annonce immobilière
    """
    if 'user' not in session:
        return jsonify({"error": "Utilisateur non connecté"}), 401
    
    data = request.json
    property_type = data.get('property_type', '')
    transaction_type = data.get('transaction_type', '')
    price = data.get('price', '')
    area = data.get('area', '')
    rooms = data.get('rooms', '')
    bedrooms = data.get('bedrooms', '')
    location = data.get('location', '')
    description = data.get('description', '')
    features = data.get('features', [])
    
    # Construire le prompt pour l'API OpenAI
    prompt = f"""
    Génère 5 titres accrocheurs et professionnels pour une annonce immobilière avec les caractéristiques suivantes:
    - Type de bien: {property_type}
    - Type de transaction: {transaction_type}
    - Prix: {price}€
    - Surface: {area} m²
    - Nombre de pièces: {rooms}
    - Nombre de chambres: {bedrooms}
    - Localisation: {location}
    - Caractéristiques: {', '.join(features) if features else 'Non spécifié'}
    
    Description du bien:
    {description}
    
    Les titres doivent être concis (maximum 70 caractères), attractifs et mettre en valeur les points forts du bien.
    Chaque titre doit être différent en style et en approche.
    Retourne uniquement la liste des 5 titres, un par ligne.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en marketing immobilier spécialisé dans la création de titres d'annonces accrocheurs."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        # Extraire les titres de la réponse
        titles_text = response.choices[0].message.content.strip()
        titles = [title.strip() for title in titles_text.split('\n') if title.strip()]
        
        # Nettoyer les titres (supprimer les numéros au début)
        cleaned_titles = []
        for title in titles:
            # Supprimer les formats comme "1. ", "2- ", etc.
            cleaned_title = re.sub(r'^\d+[\.\)\-\s]+\s*', '', title)
            cleaned_titles.append(cleaned_title)
        
        return jsonify({"titles": cleaned_titles})
    
    except Exception as e:
        print(f"Erreur lors de la génération des titres: {str(e)}")
        return jsonify({"error": "Erreur lors de la génération des titres"}), 500

@app.route('/api/nearby-places', methods=['POST'])
def nearby_places():
    """API pour rechercher les points d'intérêt à proximité d'une adresse"""
    data = request.json
    address = data.get('address')
    city = data.get('city')
    postal_code = data.get('postal_code')
    place_type = data.get('type', 'transport')  # transport, commerce, ecole
    
    if not all([address, city, postal_code]):
        return jsonify({'error': 'Adresse incomplète'}), 400
    
    try:
        # Construire l'adresse complète
        full_address = f"{address}, {postal_code} {city}, France"
        
        # Méthode 1: Utiliser directement l'API Nominatim avec un timeout plus élevé
        try:
            response = requests.get(
                f"https://nominatim.openstreetmap.org/search",
                params={
                    "q": full_address,
                    "format": "json",
                    "limit": 1
                },
                headers={"User-Agent": "immoai-app/1.0"},
                timeout=10  # Augmenter le timeout à 10 secondes
            )
            
            data = response.json()
            
            if data and len(data) > 0:
                latitude = float(data[0]["lat"])
                longitude = float(data[0]["lon"])
            else:
                # Fallback: Utiliser des coordonnées par défaut pour Paris
                print(f"Adresse non trouvée: {full_address}, utilisation des coordonnées par défaut")
                latitude, longitude = 48.8566, 2.3522  # Paris
            
            # Définir le type de recherche en fonction du paramètre
            search_types = {
                'transport': ['subway_station', 'train_station', 'bus_station', 'transit_station'],
                'commerce': ['supermarket', 'shopping_mall', 'store', 'bakery', 'grocery_or_supermarket'],
                'ecole': ['school', 'university', 'primary_school', 'secondary_school']
            }
            
            # Simuler des résultats pour éviter de dépendre d'une API externe
            # Dans une version réelle, vous utiliseriez l'API Google Places ou similaire
            results = []
            
            if place_type == 'transport':
                results = [
                    {
                        'name': 'Station de métro Mairie',
                        'type': 'subway_station',
                        'distance': '350m',
                        'icon': 'subway'
                    },
                    {
                        'name': 'Arrêt de bus Centre-Ville',
                        'type': 'bus_station',
                        'distance': '200m',
                        'icon': 'bus'
                    },
                    {
                        'name': 'Gare SNCF',
                        'type': 'train_station',
                        'distance': '1.2km',
                        'icon': 'train'
                    }
                ]
            elif place_type == 'commerce':
                results = [
                    {
                        'name': 'Supermarché Express',
                        'type': 'supermarket',
                        'distance': '450m',
                        'icon': 'shopping-cart'
                    },
                    {
                        'name': 'Boulangerie du Coin',
                        'type': 'bakery',
                        'distance': '150m',
                        'icon': 'bread-slice'
                    },
                    {
                        'name': 'Centre Commercial',
                        'type': 'shopping_mall',
                        'distance': '1.5km',
                        'icon': 'shopping-bag'
                    }
                ]
            elif place_type == 'ecole':
                results = [
                    {
                        'name': 'École Primaire Jean Moulin',
                        'type': 'primary_school',
                        'distance': '550m',
                        'icon': 'school'
                    },
                    {
                        'name': 'Collège Victor Hugo',
                        'type': 'secondary_school',
                        'distance': '800m',
                        'icon': 'graduation-cap'
                    },
                    {
                        'name': 'Lycée Pasteur',
                        'type': 'secondary_school',
                        'distance': '1.1km',
                        'icon': 'graduation-cap'
                    }
                ]
            
            return jsonify({
                'results': results,
                'coordinates': {
                    'lat': latitude,
                    'lng': longitude
                }
            })
            
        except Exception as e:
            print(f"Erreur lors de la géolocalisation via API directe: {str(e)}")
            # Fallback: Utiliser des coordonnées par défaut pour Paris
            latitude, longitude = 48.8566, 2.3522  # Paris
            
    except Exception as e:
        print(f"Erreur lors de la recherche des points d'intérêt: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-image', methods=['POST'])
def delete_image():
    data = request.json
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'success': False, 'error': 'No filename provided'}), 400
    
    try:
        # Construct the full path to the image
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Check if the file exists
        if os.path.exists(file_path):
            # Delete the file
            os.remove(file_path)
            print(f"Deleted image: {filename}")
            return jsonify({'success': True, 'message': 'Image deleted successfully'})
        else:
            print(f"Image not found: {filename}")
            return jsonify({'success': False, 'error': 'Image not found'}), 404
    
    except Exception as e:
        print(f"Error deleting image {filename}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/image-description', methods=['POST'])
def api_image_description():
    """
    API pour récupérer la description d'une image
    """
    if 'user' not in session:
        return jsonify({"error": "Utilisateur non connecté"}), 401
    
    data = request.json
    property_id = data.get('property_id')
    image_index = data.get('image_index', 0)
    
    if not property_id:
        return jsonify({"error": "ID de propriété manquant"}), 400
    
    try:
        property_id = int(property_id)
    except ValueError:
        return jsonify({"error": "ID de propriété invalide"}), 400
    
    db = get_database()
    property_data = None
    
    # Trouver la propriété
    for prop in db['properties']:
        if isinstance(prop, dict) and prop.get('id') == property_id:
            property_data = prop
            break
    
    if not property_data:
        return jsonify({"error": "Propriété non trouvée"}), 404
    
    # Vérifier si des images existent
    if not property_data.get('images') or len(property_data['images']) <= image_index:
        return jsonify({"error": "Image non trouvée"}), 404
    
    # Récupérer l'image
    image_path = property_data['images'][image_index]['path']
    
    # Vérifier si une description existe déjà
    image_descriptions = property_data.get('image_descriptions', {})
    description = image_descriptions.get(str(image_index))
    
    # Si aucune description n'existe, générer une description avec l'API Vision
    if not description and api_connected:
        try:
            # Chemin complet de l'image
            full_image_path = os.path.join(os.path.dirname(__file__), image_path)
            
            # Vérifier si le fichier existe
            if os.path.exists(full_image_path):
                # Lire l'image et l'encoder en base64
                with open(full_image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
                # Appeler l'API Vision pour analyser l'image
                response = client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": "Tu es un expert immobilier spécialisé dans la description d'images de biens immobiliers."
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Décris cette image de bien immobilier en détail. Concentre-toi sur les éléments architecturaux, l'aménagement, la décoration, la luminosité et l'atmosphère générale. Sois précis et concis (maximum 100 mots)."},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=300
                )
                
                # Extraire la description générée
                description = response.choices[0].message.content.strip()
                
                # Sauvegarder la description dans la base de données
                if 'image_descriptions' not in property_data:
                    property_data['image_descriptions'] = {}
                
                property_data['image_descriptions'][str(image_index)] = description
                save_database(db)
        except Exception as e:
            print(f"Erreur lors de la génération de la description de l'image: {str(e)}")
            # En cas d'erreur, utiliser une description par défaut
            description = "Aucune description disponible pour cette image."
    
    return jsonify({"description": description})

@app.route('/api/update-description', methods=['POST'])
def update_image_description():
    """API pour mettre à jour la description d'une image"""
    if 'user' not in session:
        return jsonify({"error": "Non autorisé"}), 401
    
    data = request.json
    property_id = data.get('property_id')
    image_index = data.get('image_index')
    description = data.get('description')
    
    if not all([property_id, image_index is not None, description]):
        return jsonify({"error": "Données manquantes"}), 400
    
    db = get_database()
    
    # Trouver la propriété
    property_found = False
    for prop in db['properties']:
        if prop.get('id') == property_id:
            property_data = prop
            property_found = True
            break
    
    if not property_found:
        return jsonify({"error": "Propriété non trouvée"}), 404
    
    # Vérifier que l'utilisateur est le propriétaire
    if property_data.get('owner') != session['user']:
        return jsonify({"error": "Non autorisé"}), 403
    
    # Vérifier que l'image existe
    if not property_data.get('images') or image_index >= len(property_data['images']):
        return jsonify({"error": "Image non trouvée"}), 404
    
    # Mettre à jour la description
    try:
        # Si l'image est déjà un objet avec path et description
        if isinstance(property_data['images'][image_index], dict):
            property_data['images'][image_index]['description'] = description
        else:
            # Si l'image est juste un chemin, convertir en objet
            image_path = property_data['images'][image_index]
            property_data['images'][image_index] = {
                'path': image_path,
                'description': description
            }
        
        # Sauvegarder les modifications
        save_database(db)
        return jsonify({"success": True, "message": "Description mise à jour avec succès"})
    except Exception as e:
        print(f"Erreur lors de la mise à jour de la description: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/document-chat')
def document_chat():
    """
    Page pour le chat avec documents
    """
    # Vérifier si l'utilisateur est connecté
    if 'user' not in session:
        flash('Veuillez vous connecter pour accéder à cette page', 'warning')
        return redirect(url_for('login'))
    
    # Récupérer les documents de l'utilisateur
    db = get_database()
    user_documents = []
    
    # Vérifier si la section documents existe pour l'utilisateur
    if 'documents' in db and session['user'] in db['documents']:
        user_documents = db['documents'][session['user']]
    
    return render_template('document_chat.html', documents=user_documents)

@app.route('/api/delete-document', methods=['POST'])
def delete_document():
    data = request.json
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'success': False, 'error': 'No filename provided'}), 400
    
    try:
        # Construct the full path to the document
        file_path = os.path.join(app.config['DOCUMENTS_FOLDER'], filename)
        
        # Check if the file exists
        if os.path.exists(file_path):
            # Delete the file
            os.remove(file_path)
            print(f"Deleted document: {filename}")
            return jsonify({'success': True, 'message': 'Document deleted successfully'})
        else:
            print(f"Document not found: {filename}")
            return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    except Exception as e:
        print(f"Error deleting document {filename}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/documents')
def get_documents_api():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Non autorisé'}), 401
    
    # Créer le dossier de documents s'il n'existe pas
    user_docs_dir = os.path.join(app.config['UPLOAD_FOLDER'], session['user'])
    os.makedirs(user_docs_dir, exist_ok=True)
    
    documents = []
    for filename in os.listdir(user_docs_dir):
        file_path = os.path.join(user_docs_dir, filename)
        if os.path.isfile(file_path):
            file_type = filename.split('.')[-1].lower()
            original_name = filename  # Dans un système réel, vous stockeriez le nom original dans une base de données
            
            documents.append({
                'id': filename,
                'filename': filename,
                'original_name': original_name,
                'file_type': file_type
            })
    
    return jsonify({'success': True, 'documents': documents})

@app.route('/api/upload-documents', methods=['POST'])
def upload_documents_api():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Non autorisé'}), 401
    
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier trouvé'}), 400
    
    files = request.files.getlist('files')
    
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': 'Aucun fichier sélectionné'}), 400
    
    uploaded_files = []
    
    for file in files:
        if file and allowed_document_file(file.filename):
            # Sécuriser le nom du fichier
            filename = secure_filename(file.filename)
            
            # Créer le dossier de l'utilisateur s'il n'existe pas
            user_docs_dir = os.path.join(app.config['UPLOAD_FOLDER'], session['user'])
            os.makedirs(user_docs_dir, exist_ok=True)
            
            # Chemin complet du fichier
            file_path = os.path.join(user_docs_dir, filename)
            
            # Sauvegarder le fichier
            file.save(file_path)
            
            # Obtenir le type de fichier
            file_type = filename.split('.')[-1].lower()
            
            uploaded_files.append({
                'id': filename,
                'filename': filename,
                'original_name': filename,
                'file_type': file_type
            })
    
    if uploaded_files:
        return jsonify({'success': True, 'documents': uploaded_files})
    else:
        return jsonify({'success': False, 'message': 'Type de fichier non autorisé'}), 400

@app.route('/api/documents/<doc_id>', methods=['DELETE'])
def delete_document_api(doc_id):
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Non autorisé'}), 401
    
    # Vérifier que le nom de fichier est sécurisé
    if not doc_id or '..' in doc_id:
        return jsonify({'success': False, 'message': 'Nom de fichier invalide'}), 400
    
    user_docs_dir = os.path.join(app.config['UPLOAD_FOLDER'], session['user'])
    file_path = os.path.join(user_docs_dir, doc_id)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            os.remove(file_path)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    else:
        return jsonify({'success': False, 'message': 'Fichier non trouvé'}), 404

@app.route('/api/chat', methods=['POST'])
def chat_with_documents_api():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Non autorisé'}), 401
    
    data = request.json
    
    if not data or 'message' not in data:
        return jsonify({'success': False, 'message': 'Message requis'}), 400
    
    message = data.get('message', '')
    document_ids = data.get('document_ids', [])
    model = data.get('model', 'gpt-3.5-turbo')
    history = data.get('history', [])
    
    # Vérifier si des documents ont été sélectionnés
    if not document_ids:
        return jsonify({
            'success': True,
            'response': "Veuillez sélectionner au moins un document dans la barre latérale pour que je puisse vous aider avec votre question."
        })
    
    # Dans un système réel, vous utiliseriez ici une API comme OpenAI, Claude, etc.
    # Pour cet exemple, nous simulons une réponse
    
    # Simuler un délai de traitement
    time.sleep(1)
    
    # Réponse simulée basée sur le modèle et le message
    if 'prix' in message.lower() or 'cout' in message.lower() or 'coût' in message.lower():
        response = "Selon les documents que vous avez partagés, les prix de l'immobilier dans cette zone varient entre 3000€ et 5000€ par mètre carré, selon l'emplacement et les caractéristiques du bien."
    elif 'surface' in message.lower() or 'taille' in message.lower() or 'mètre' in message.lower():
        response = "D'après les documents fournis, la propriété fait environ 120m² avec un terrain de 450m². Elle comprend 4 chambres et 2 salles de bain."
    elif 'localisation' in message.lower() or 'quartier' in message.lower() or 'emplacement' in message.lower():
        response = "La propriété est située dans un quartier résidentiel calme, à proximité des transports en commun (ligne de bus 42 à 200m) et des commerces. L'école primaire est à 5 minutes à pied et le collège à 10 minutes."
    elif 'diagnostic' in message.lower() or 'dpe' in message.lower() or 'énergie' in message.lower():
        response = "Le diagnostic de performance énergétique (DPE) indique une classe C avec une consommation de 125 kWh/m²/an. Le diagnostic des émissions de gaz à effet de serre est classé B."
    else:
        response = "Après analyse des documents sélectionnés, je peux vous dire que cette propriété présente un bon potentiel d'investissement. Elle est bien située, en bon état général et correspond aux tendances actuelles du marché immobilier local. N'hésitez pas à me poser des questions plus spécifiques sur certains aspects qui vous intéressent."
    
    return jsonify({'success': True, 'response': response})

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_document_file(filename):
    ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'xls', 'xlsx', 'csv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOCUMENT_EXTENSIONS

def generate_map(address, city, postal_code):
    """
    Générer une carte interactive pour une adresse donnée
    """
    # Construire l'adresse complète
    full_address = f"{address}, {postal_code} {city}, France"
    
    try:
        # Utiliser l'API de géocodage avec un timeout plus élevé
        response = requests.get(
            f"https://nominatim.openstreetmap.org/search",
            params={
                "q": full_address,
                "format": "json",
                "limit": 1
            },
            headers={"User-Agent": "immoai-app/1.0"},
            timeout=10  # Augmenter le timeout à 10 secondes
        )
        
        data = response.json()
        
        if data and len(data) > 0:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
        else:
            # Fallback: Utiliser des coordonnées par défaut pour Paris
            print(f"Adresse non trouvée pour la carte: {full_address}, utilisation des coordonnées par défaut")
            lat, lon = 48.8566, 2.3522  # Paris
            
        # Créer la carte
        m = folium.Map(location=[lat, lon], zoom_start=15)
        folium.Marker(
            [lat, lon],
            popup=f"<b>{address}</b><br>{postal_code} {city}",
            icon=folium.Icon(color="red", icon="home")
        ).add_to(m)
        
        # Ajouter des cercles pour montrer les commodités à proximité
        folium.Circle(
            radius=500,
            location=[lat, lon],
            popup="5 minutes à pied",
            color="green",
            fill=True
        ).add_to(m)
        
        # Convertir la carte en HTML
        map_html = m._repr_html_()
        return map_html
    
    except Exception as e:
        print(f"Erreur lors de la génération de la carte: {str(e)}")
        # Créer une carte de secours centrée sur Paris
        try:
            m = folium.Map(location=[48.8566, 2.3522], zoom_start=12)
            map_html = m._repr_html_()
            return map_html
        except:
            return "<p>Erreur lors de la génération de la carte</p>"

def generate_enhanced_description(basic_description, images, property_type, area, rooms, city):
    """
    Générer une description améliorée en utilisant l'IA
    """
    # Dans un projet réel, cette fonction appellerait l'API OpenAI ou un autre modèle de langage
    
    try:
        # Construction du prompt pour l'IA
        prompt = f"""
        Générez une description professionnelle et attrayante pour une annonce immobilière avec les informations suivantes:
        
        Type de bien: {property_type}
        Surface: {area} m²
        Nombre de pièces: {rooms}
        Ville: {city}
        
        Description de base fournie par le propriétaire:
        {basic_description}
        
        La description doit être engageante, mettre en valeur les points forts du bien, et utiliser un langage professionnel adapté au secteur immobilier français.
        Structurez la description en paragraphes avec une introduction, une description des pièces principales, et une conclusion sur l'environnement.
        Assurez-vous d'inclure et de mentionner explicitement toutes les informations fournies (surface, nombre de pièces, localisation, prix si disponible).
        """
        
        # Appel à l'API OpenAI avec le nouveau format ChatCompletion
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Vous êtes un expert en immobilier spécialisé dans la rédaction de descriptions professionnelles pour des annonces immobilières."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        enhanced_description = response.choices[0].message.content.strip()
        
        # Si l'API n'est pas disponible, on utilise une description par défaut
        if not enhanced_description:
            raise Exception("Pas de réponse de l'API")
            
        return enhanced_description
        
    except Exception as e:
        print(f"Erreur lors de la génération de la description: {str(e)}")
        
        # Description par défaut en cas d'erreur
        return f"""
        {property_type.capitalize()} de {area} m² situé à {city}.
        
        Ce bien dispose de {rooms} pièces et offre un cadre de vie agréable.
        
        {basic_description}
        
        Idéalement situé, proche des commerces et transports.
        """

@app.route('/api/upload-document', methods=['POST'])
def upload_document():
    """
    API pour télécharger un document
    """
    # Vérifier si l'utilisateur est connecté
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Utilisateur non connecté'}), 401
    
    # Vérifier si le fichier est présent dans la requête
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier envoyé'}), 400
    
    file = request.files['file']
    
    # Vérifier si le fichier a un nom
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nom de fichier vide'}), 400
    
    # Vérifier si le fichier est d'un type autorisé
    if not allowed_document_file(file.filename):
        return jsonify({'success': False, 'error': 'Type de fichier non autorisé'}), 400
    
    try:
        # Sécuriser le nom du fichier
        filename = secure_filename(file.filename)
        
        # Générer un nom unique pour éviter les conflits
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Chemin complet du fichier
        file_path = os.path.join(app.config['DOCUMENTS_FOLDER'], unique_filename)
        
        # Sauvegarder le fichier
        file.save(file_path)
        
        # Mettre à jour la base de données
        db = get_database()
        
        # Créer la section documents si elle n'existe pas
        if 'documents' not in db:
            db['documents'] = {}
        
        # Créer la liste de documents pour l'utilisateur si elle n'existe pas
        if session['user'] not in db['documents']:
            db['documents'][session['user']] = []
        
        # Ajouter le document à la liste de l'utilisateur
        document_info = {
            'id': str(uuid.uuid4()),
            'filename': unique_filename,
            'original_name': filename,
            'upload_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'file_type': filename.rsplit('.', 1)[1].lower(),
            'file_size': os.path.getsize(file_path)
        }
        
        db['documents'][session['user']].append(document_info)
        save_database(db)
        
        return jsonify({
            'success': True, 
            'document': document_info,
            'message': 'Document téléchargé avec succès'
        })
        
    except Exception as e:
        print(f"Erreur lors du téléchargement du document: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-documents', methods=['GET'])
def get_documents():
    """
    API pour récupérer la liste des documents de l'utilisateur
    """
    # Vérifier si l'utilisateur est connecté
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Utilisateur non connecté'}), 401
    
    try:
        # Récupérer la base de données
        db = get_database()
        
        # Récupérer les documents de l'utilisateur
        user_documents = []
        if 'documents' in db and session['user'] in db['documents']:
            user_documents = db['documents'][session['user']]
        
        return jsonify({
            'success': True,
            'documents': user_documents
        })
        
    except Exception as e:
        print(f"Erreur lors de la récupération des documents: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat-with-documents', methods=['POST'])
def chat_with_documents():
    """
    API pour chatter avec les documents en utilisant l'IA
    """
    # Vérifier si l'utilisateur est connecté
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Utilisateur non connecté'}), 401
    
    # Vérifier si l'API OpenAI est connectée
    if not api_connected:
        return jsonify({'success': False, 'error': 'Service IA non disponible'}), 503
    
    data = request.json
    message = data.get('message')
    document_ids = data.get('document_ids', [])
    model = data.get('model', 'gpt-3.5-turbo')
    
    if not message:
        return jsonify({'success': False, 'error': 'Message vide'}), 400
    
    try:
        # Récupérer la base de données
        db = get_database()
        
        # Récupérer les documents sélectionnés
        selected_documents = []
        if 'documents' in db and session['user'] in db['documents']:
            all_user_documents = db['documents'][session['user']]
            selected_documents = [doc for doc in all_user_documents if doc['id'] in document_ids]
        
        # Construire le contexte pour l'IA en fonction des documents sélectionnés
        context = "Voici ma question concernant les documents immobiliers suivants:\n\n"
        
        if selected_documents:
            for doc in selected_documents:
                context += f"Document: {doc['original_name']}\n"
                # Dans une version plus avancée, on pourrait extraire le contenu des documents
                # et l'inclure dans le contexte
        else:
            context += "Aucun document spécifique n'a été sélectionné.\n"
        
        context += f"\nMa question est: {message}"
        
        # Simuler une réponse pour le moment (dans une version réelle, on utiliserait l'API OpenAI)
        # Dans une implémentation complète, vous utiliseriez une approche RAG (Retrieval Augmented Generation)
        
        if model == 'gpt-4':
            response_text = f"Analyse basée sur GPT-4: J'ai analysé votre question concernant les documents immobiliers. Voici ce que je peux vous dire..."
        elif model == 'claude-3':
            response_text = f"Analyse basée sur Claude 3: En examinant votre question sur les documents immobiliers, je constate que..."
        else:  # gpt-3.5-turbo par défaut
            response_text = f"J'ai examiné votre question concernant les documents immobiliers. Voici ce que je peux vous dire..."
        
        # Ajouter une mention sur les documents sélectionnés
        if selected_documents:
            response_text += f"\n\nCette analyse est basée sur les {len(selected_documents)} document(s) que vous avez sélectionné(s)."
        else:
            response_text += "\n\nAucun document spécifique n'a été sélectionné pour cette analyse. Pour une réponse plus précise, veuillez sélectionner les documents pertinents."
        
        return jsonify({
            'success': True,
            'response': response_text
        })
        
    except Exception as e:
        print(f"Erreur lors du chat avec documents: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
