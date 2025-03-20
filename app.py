from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os
import json
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import base64
from openai import OpenAI
from dotenv import load_dotenv

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
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database functions
def get_database():
    """Load the database from the JSON file or create a new one if it doesn't exist."""
    db_path = os.path.join(os.path.dirname(__file__), 'database.json')
    if os.path.exists(db_path):
        with open(db_path, 'r') as f:
            return json.load(f)
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
        db = get_database()
        property_id = db['next_property_id']
        db['next_property_id'] += 1
        property_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'properties', str(property_id))
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
                            images.append(os.path.join('uploads', 'properties', str(property_id), filename))
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
                if file and file.filename and allowed_file(file.filename):
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
