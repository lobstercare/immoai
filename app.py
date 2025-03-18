from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os
import json
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from PIL import Image
import folium
import io
import base64
import requests
from dotenv import load_dotenv
import openai
from flask import send_file
import pdfkit
from jinja2 import Environment, FileSystemLoader
import re
from geopy.geocoders import Nominatim

# Charger les variables d'environnement
load_dotenv()

# Configuration de l'API OpenAI
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("ATTENTION: Clé API OpenAI non trouvée dans le fichier .env")
else:
    openai.api_key = openai_api_key

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_key_for_testing")
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# Créer le dossier d'uploads s'il n'existe pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'dpe'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'properties'), exist_ok=True)

# Base de données simulée (dans un vrai projet, utilisez une base de données)
DATABASE_FILE = 'database.json'

def get_database():
    if not os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'w') as f:
            json.dump({"users": {}, "properties": {}}, f)
    
    with open(DATABASE_FILE, 'r') as f:
        return json.load(f)

def save_database(data):
    with open(DATABASE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

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
        property_id = str(uuid.uuid4())
        property_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'properties', property_id)
        os.makedirs(property_folder, exist_ok=True)
        
        # Traiter les images
        images = []
        try:
            if 'images' in request.files:
                files = request.files.getlist('images')
                for i, file in enumerate(files):
                    if file and file.filename and allowed_file(file.filename):
                        try:
                            filename = secure_filename(f"{i}_{file.filename}")
                            filepath = os.path.join(property_folder, filename)
                            file.save(filepath)
                            images.append(os.path.join('uploads', 'properties', property_id, filename))
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
                    filename = secure_filename(f"dpe_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'dpe', filename)
                    file.save(filepath)
                    dpe_file = os.path.join('uploads', 'dpe', filename)
        except Exception as e:
            print(f"Erreur lors du traitement du DPE: {str(e)}")
            # Continuer sans DPE si nécessaire
        
        # Créer l'entrée dans la base de données
        try:
            # Analyser les images et générer une description améliorée si possible
            enhanced_description = description
            try:
                if images:
                    enhanced_description = generate_enhanced_description(description, images, property_type, area, rooms, city)
            except Exception as e:
                print(f"Erreur lors de la génération de la description améliorée: {str(e)}")
                # Utiliser la description originale en cas d'erreur
            
            db = get_database()
            db['properties'][property_id] = {
                'title': title,
                'description': description,
                'enhanced_description': enhanced_description,
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
            }
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
    if property_id not in db['properties']:
        flash('Propriété non trouvée', 'danger')
        return redirect(url_for('dashboard'))
    
    property_data = db['properties'][property_id]
    
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
    if property_id not in db['properties'] or db['properties'][property_id]['owner'] != session['user']:
        flash('Vous n\'avez pas accès à cette propriété', 'danger')
        return redirect(url_for('dashboard'))
    
    property_data = db['properties'][property_id]
    
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
            property_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'properties', property_id)
            os.makedirs(property_folder, exist_ok=True)
            
            # Déterminer le prochain numéro d'image
            next_image_num = 0
            for img_path in property_data['images']:
                img_name = os.path.basename(img_path)
                if img_name.split('_')[0].isdigit():
                    num = int(img_name.split('_')[0])
                    next_image_num = max(next_image_num, num + 1)
            
            # Ajouter les nouvelles images
            for file in files:
                if file and allowed_file(file.filename) and file.filename:
                    filename = secure_filename(f"{next_image_num}_{file.filename}")
                    filepath = os.path.join(property_folder, filename)
                    file.save(filepath)
                    property_data['images'].append(os.path.join('uploads', 'properties', property_id, filename))
                    next_image_num += 1
        
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
                
                filename = secure_filename(f"dpe_{property_id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'dpe', filename)
                file.save(filepath)
                property_data['dpe_file'] = os.path.join('uploads', 'dpe', filename)
        
        # Mettre à jour la description améliorée si la description a changé
        if request.form.get('regenerate_description', 'off') == 'on' or not property_data.get('enhanced_description'):
            enhanced_description = generate_enhanced_description(
                property_data['description'], 
                property_data['images'], 
                property_data['property_type'], 
                property_data['area'], 
                property_data['rooms'], 
                property_data['city']
            )
            property_data['enhanced_description'] = enhanced_description
        
        # Mettre à jour la date de modification
        property_data['updated_at'] = datetime.now().isoformat()
        
        # Sauvegarder les modifications
        db['properties'][property_id] = property_data
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
    if property_id not in db['properties']:
        flash('Propriété non trouvée', 'danger')
        return redirect(url_for('dashboard'))
        
    if db['properties'][property_id]['owner'] != session['user']:
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
        if 'dpe_file' in db['properties'][property_id] and db['properties'][property_id]['dpe_file']:
            dpe_path = os.path.join('static', db['properties'][property_id]['dpe_file'])
            if os.path.exists(dpe_path):
                os.remove(dpe_path)
        
        # Supprimer de la base de données
        del db['properties'][property_id]
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
    if property_id not in db['properties']:
        flash('Propriété non trouvée', 'danger')
        return redirect(url_for('dashboard'))
    
    property_data = db['properties'][property_id]
    
    # Vérifier que l'utilisateur est le propriétaire de l'annonce
    if property_data['owner'] != session['user']:
        flash('Vous n\'avez pas accès à cette propriété', 'danger')
        return redirect(url_for('dashboard'))
    
    # Générer la carte
    map_html = generate_map(property_data['address'], property_data['city'], property_data['postal_code'])
    
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
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400
    
    if file and allowed_file(file.filename):
        # Sauvegarder temporairement l'image
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_' + filename)
        file.save(temp_path)
        
        # Analyser l'image avec une méthode simplifiée
        try:
            # Lire l'image pour l'analyse de base
            image = cv2.imread(temp_path)
            if image is None:
                os.remove(temp_path)
                return jsonify({'error': 'Impossible de lire l\'image'}), 500
                
            height, width, _ = image.shape
            
            # Analyse basique de l'image pour les caractéristiques visuelles
            avg_brightness = np.mean(image)
            std_dev = np.std(image)
            
            # Détection basique d'extérieur vs intérieur
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            # Plage de vert en HSV
            lower_green = np.array([35, 50, 50])
            upper_green = np.array([90, 255, 255])
            # Créer un masque pour le vert
            mask = cv2.inRange(hsv, lower_green, upper_green)
            # Calculer le pourcentage de pixels verts
            green_ratio = np.count_nonzero(mask) / (height * width)
            
            # Déterminer le type d'espace
            if green_ratio > 0.15:  # Si plus de 15% de l'image est verte
                room_type = 'espace extérieur'
            else:
                # Analyse basique des couleurs pour déterminer le type de pièce
                avg_color = np.mean(image, axis=(0, 1))
                b, g, r = avg_color
                
                # Logique simple pour déterminer le type de pièce
                if r > 100 and g > 100 and b > 100 and std_dev < 50:
                    room_type = 'salon'  # Pièces claires et uniformes
                elif r < 100 and g < 100 and b < 100 and std_dev < 50:
                    room_type = 'chambre'  # Pièces sombres et uniformes
                elif std_dev > 60:
                    room_type = 'cuisine'  # Pièces avec beaucoup de détails
                else:
                    room_type = 'pièce'  # Par défaut
            
            # Déterminer les caractéristiques
            features = []
            
            # Luminosité
            if avg_brightness > 150:
                features.append('lumineux')
            elif avg_brightness < 80:
                features.append('intime')
            
            # Contraste/Décoration
            if std_dev > 60:
                features.append('bien aménagé')
                
            # Taille
            if width * height > 600000:
                features.append('spacieux')
            
            # Générer une description textuelle
            if room_type in ['espace extérieur', 'jardin', 'parc']:
                description = f"Cette photo montre un {room_type}"
            else:
                description = f"Cette photo montre une {room_type}"
                
            if features:
                description += f" {', '.join(features)}."
            else:
                description += "."
            
            # Nettoyer le fichier temporaire
            os.remove(temp_path)
            
            # Résultats
            return jsonify({
                'room_type': room_type,
                'features': features,
                'description': description,
                'brightness': float(avg_brightness),
                'std_dev': float(std_dev)
            })
            
        except Exception as e:
            # Nettoyer le fichier temporaire en cas d'erreur
            if os.path.exists(temp_path):
                os.remove(temp_path)
            print(f"Erreur lors de l'analyse de l'image: {str(e)}")
            return jsonify({
                'room_type': 'pièce',
                'features': ['non analysé'],
                'description': "Cette photo montre une pièce de la propriété.",
                'error': str(e)
            })
    
    return jsonify({'error': 'Invalid file type'}), 400

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
    
    # Construire le prompt pour l'API OpenAI
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
    
    La description doit être détaillée, mettre en valeur les points forts du bien et inciter les acheteurs potentiels à visiter.
    Utilise un style professionnel mais chaleureux, avec des phrases variées et un vocabulaire riche.
    La description doit faire environ 150-200 mots.
    """
    
    try:
        response = openai.ChatCompletion.create(
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
        response = openai.ChatCompletion.create(
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
        
        # Obtenir les coordonnées de l'adresse
        geolocator = Nominatim(user_agent="immoai-app")
        location = geolocator.geocode(full_address)
        
        if not location:
            return jsonify({'error': 'Adresse introuvable'}), 404
        
        latitude, longitude = location.latitude, location.longitude
        
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
        print(f"Erreur lors de la recherche des points d'intérêt: {str(e)}")
        return jsonify({'error': str(e)}), 500

def analyze_property_image(image_path):
    """
    Analyser une image de propriété pour en extraire des caractéristiques en utilisant l'API OpenAI Vision
    """
    try:
        # Vérifier si l'image existe
        if not os.path.exists(image_path):
            return {"error": "Image introuvable"}
        
        # Lire l'image pour l'analyse de base
        image = cv2.imread(image_path)
        if image is None:
            return {"error": "Impossible de lire l'image"}
            
        height, width, _ = image.shape
        
        # Analyse basique de l'image pour les caractéristiques visuelles
        avg_brightness = np.mean(image)
        std_dev = np.std(image)
        
        # Convertir l'image en base64 pour l'API OpenAI
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Utiliser l'API OpenAI Vision pour analyser l'image
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un expert en immobilier spécialisé dans l'analyse d'images de propriétés. Tu dois identifier avec précision le type d'espace montré dans l'image, y compris les espaces extérieurs comme les jardins, parcs, vues extérieures, terrasses, balcons, etc."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyse cette image de propriété immobilière. Identifie précisément le type d'espace (salon, cuisine, chambre, salle de bain, jardin, parc, vue extérieure, terrasse, balcon, entrée, etc.) et décris ses caractéristiques principales (luminosité, verdure, espace, aménagement, etc.). Réponds au format JSON avec les clés 'room_type' et 'features' (liste de 3 caractéristiques maximum)."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            # Extraire la réponse
            analysis_text = response.choices[0].message.content.strip()
            
            # Tenter de parser la réponse JSON
            try:
                # Essayer de trouver un objet JSON dans la réponse
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', analysis_text, re.DOTALL)
                if json_match:
                    analysis_json = json.loads(json_match.group(1))
                else:
                    # Essayer de parser directement
                    analysis_json = json.loads(analysis_text)
                
                room_type = analysis_json.get('room_type', 'indéterminé').lower()
                features = analysis_json.get('features', [])
                
            except Exception as json_error:
                print(f"Erreur lors du parsing JSON: {str(json_error)}")
                # Fallback: extraire manuellement les informations
                room_type = 'indéterminé'
                features = []
                
                # Recherche du type de pièce avec une liste étendue incluant les espaces extérieurs
                room_types = [
                    'salon', 'cuisine', 'chambre', 'salle de bain', 'balcon', 'terrasse', 
                    'entrée', 'jardin', 'parc', 'extérieur', 'vue', 'paysage', 'cour', 
                    'piscine', 'espace vert'
                ]
                
                for rt in room_types:
                    if rt in analysis_text.lower():
                        room_type = rt
                        break
                
                # Si aucun type spécifique n'est trouvé mais qu'il s'agit clairement d'un extérieur
                if room_type == 'indéterminé' and any(ext in analysis_text.lower() for ext in ['arbre', 'verdure', 'herbe', 'plante', 'ciel', 'nature']):
                    room_type = 'espace extérieur'
                
                # Recherche des caractéristiques
                feature_keywords = [
                    'lumineux', 'spacieux', 'moderne', 'décoré', 'rénové', 'équipé',
                    'verdoyant', 'arboré', 'aménagé', 'ensoleillé', 'ombragé', 'fleuri'
                ]
                
                for kw in feature_keywords:
                    if kw in analysis_text.lower() and len(features) < 3:
                        features.append(kw)
        
        except Exception as api_error:
            print(f"Erreur lors de l'appel à l'API OpenAI: {str(api_error)}")
            # Fallback: utiliser l'analyse basique
            
            # Détection basique d'extérieur vs intérieur
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            # Plage de vert en HSV
            lower_green = np.array([35, 50, 50])
            upper_green = np.array([90, 255, 255])
            # Créer un masque pour le vert
            mask = cv2.inRange(hsv, lower_green, upper_green)
            # Calculer le pourcentage de pixels verts
            green_ratio = np.count_nonzero(mask) / (height * width)
            
            # Déterminer si c'est un espace extérieur basé sur la quantité de vert
            if green_ratio > 0.15:  # Si plus de 15% de l'image est verte
                room_type = 'espace extérieur'
            else:
                room_type = 'indéterminé'
            
            features = []
            
            # Luminosité
            if avg_brightness > 150:
                features.append('lumineux')
            
            # Contraste/Décoration
            if std_dev > 60:
                features.append('bien aménagé')
                
            # Taille
            if width * height > 600000:
                features.append('spacieux')
        
        # Générer une description textuelle
        if room_type in ['jardin', 'parc', 'espace extérieur', 'extérieur', 'vue', 'paysage', 'cour']:
            description = f"Cette photo montre un {room_type} {', '.join(features)}."
        else:
            description = f"Cette photo montre une {room_type} {', '.join(features)}."
        
        # Résultats
        return {
            'room_type': room_type,
            'features': features,
            'description': description,
            'brightness': avg_brightness,
            'std_dev': std_dev
        }
    except Exception as e:
        print(f"Erreur lors de l'analyse de l'image: {str(e)}")
        return {
            'room_type': 'indéterminé',
            'features': ['non analysé'],
            'description': "Impossible d'analyser cette image.",
            'error': str(e)
        }

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
        response = openai.ChatCompletion.create(
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

def generate_map(address, city, postal_code):
    """
    Générer une carte interactive pour une adresse donnée
    """
    # Construire l'adresse complète
    full_address = f"{address}, {postal_code} {city}, France"
    
    try:
        # Utiliser l'API de géocodage (dans un projet réel, utilisez une clé API)
        response = requests.get(
            f"https://nominatim.openstreetmap.org/search",
            params={
                "q": full_address,
                "format": "json",
                "limit": 1
            },
            headers={"User-Agent": "PropertyListingApp/1.0"}
        )
        
        data = response.json()
        
        if data and len(data) > 0:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            
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
        else:
            return "<p>Carte non disponible pour cette adresse</p>"
    
    except Exception as e:
        print(f"Erreur lors de la génération de la carte: {str(e)}")
        return "<p>Erreur lors de la génération de la carte</p>"

if __name__ == '__main__':
    app.run(debug=True)
