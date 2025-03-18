/**
 * ImmoAI - Main JavaScript File
 * Contient les fonctions principales pour l'application ImmoAI
 */

document.addEventListener('DOMContentLoaded', function() {
    // Activer tous les tooltips Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Activer tous les popovers Bootstrap
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Gestion des alertes flash
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Gestion de la prévisualisation des images lors du téléchargement
    const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    
    imageInputs.forEach(input => {
        input.addEventListener('change', function() {
            const previewContainer = this.closest('.mb-3').querySelector('.image-preview-container');
            
            if (previewContainer) {
                previewContainer.innerHTML = '';
                
                if (this.files) {
                    const maxPreviews = this.multiple ? 6 : 1;
                    const filesToPreview = Array.from(this.files).slice(0, maxPreviews);
                    
                    filesToPreview.forEach(file => {
                        const reader = new FileReader();
                        
                        reader.onload = function(e) {
                            const previewDiv = document.createElement('div');
                            previewDiv.className = 'col-md-4 mb-3';
                            
                            const previewCard = document.createElement('div');
                            previewCard.className = 'card h-100';
                            
                            const previewImg = document.createElement('img');
                            previewImg.src = e.target.result;
                            previewImg.className = 'card-img-top image-preview';
                            
                            const cardBody = document.createElement('div');
                            cardBody.className = 'card-body p-2';
                            
                            const fileName = document.createElement('p');
                            fileName.className = 'card-text small text-truncate mb-0';
                            fileName.textContent = file.name;
                            
                            cardBody.appendChild(fileName);
                            previewCard.appendChild(previewImg);
                            previewCard.appendChild(cardBody);
                            previewDiv.appendChild(previewCard);
                            previewContainer.appendChild(previewDiv);
                        };
                        
                        reader.readAsDataURL(file);
                    });
                    
                    if (this.files.length > maxPreviews) {
                        const moreText = document.createElement('div');
                        moreText.className = 'col-md-4 mb-3 d-flex align-items-center justify-content-center';
                        moreText.innerHTML = `<div class="text-center text-muted">+${this.files.length - maxPreviews} fichiers supplémentaires</div>`;
                        previewContainer.appendChild(moreText);
                    }
                }
            }
        });
    });

    // Gestion du formulaire de création/modification d'annonce
    const propertyForm = document.getElementById('propertyForm');
    
    if (propertyForm) {
        // Validation du formulaire avant soumission
        propertyForm.addEventListener('submit', function(event) {
            if (!validatePropertyForm()) {
                event.preventDefault();
            }
        });
        
        // Génération de description avec l'IA
        const generateBtn = document.getElementById('generate-description');
        
        if (generateBtn) {
            generateBtn.addEventListener('click', generateAIDescription);
        }
        
        // Analyse d'images avec l'IA
        const imageInput = document.getElementById('images');
        
        if (imageInput) {
            imageInput.addEventListener('change', function() {
                if (this.files && this.files.length > 0) {
                    analyzeImages(this.files);
                }
            });
        }
    }

    // Gestion de la carte sur la page de prévisualisation
    initializeMap();
});

/**
 * Valide le formulaire de création/modification d'annonce
 * @returns {boolean} True si le formulaire est valide, false sinon
 */
function validatePropertyForm() {
    const form = document.getElementById('propertyForm');
    
    if (!form) return true;
    
    let isValid = true;
    
    // Vérifier les champs requis
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
            
            // Créer un message d'erreur si nécessaire
            let errorMessage = field.nextElementSibling;
            
            if (!errorMessage || !errorMessage.classList.contains('invalid-feedback')) {
                errorMessage = document.createElement('div');
                errorMessage.className = 'invalid-feedback';
                errorMessage.textContent = 'Ce champ est requis';
                field.parentNode.insertBefore(errorMessage, field.nextSibling);
            }
        } else {
            field.classList.remove('is-invalid');
            
            // Supprimer le message d'erreur si nécessaire
            const errorMessage = field.nextElementSibling;
            
            if (errorMessage && errorMessage.classList.contains('invalid-feedback')) {
                errorMessage.remove();
            }
        }
    });
    
    // Vérifier les formats spécifiques (email, numéros, etc.)
    // ...
    
    return isValid;
}

/**
 * Génère une description améliorée avec l'IA
 */
function generateAIDescription() {
    const descriptionInput = document.getElementById('description');
    const propertyType = document.getElementById('property_type');
    const area = document.getElementById('area');
    const rooms = document.getElementById('rooms');
    const city = document.getElementById('city');
    const aiPreview = document.getElementById('ai-description-preview');
    const aiContent = document.getElementById('ai-description-content');
    
    if (!descriptionInput || !aiPreview || !aiContent) return;
    
    if (!descriptionInput.value.trim()) {
        alert('Veuillez d\'abord saisir une description de base');
        return;
    }
    
    // Afficher un état de chargement
    aiContent.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm text-primary" role="status"></div> Génération en cours...</div>';
    aiPreview.style.display = 'block';
    
    // Appel à l'API pour générer la description
    fetch('/api/generate-description', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            basic_info: descriptionInput.value,
            property_type: propertyType ? propertyType.value : '',
            area: area ? area.value : '',
            rooms: rooms ? rooms.value : '',
            city: city ? city.value : ''
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.enhanced_description) {
            aiContent.innerHTML = data.enhanced_description.replace(/\n/g, '<br>');
        } else {
            aiContent.innerHTML = '<div class="text-danger">Erreur lors de la génération de la description</div>';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        aiContent.innerHTML = '<div class="text-danger">Erreur lors de la génération de la description</div>';
    });
}

/**
 * Analyse les images téléchargées avec l'IA
 * @param {FileList} files Liste des fichiers à analyser
 */
function analyzeImages(files) {
    if (!files || files.length === 0) return;
    
    // Limiter le nombre d'images à analyser pour des raisons de performance
    const maxImagesToAnalyze = 5;
    const imagesToAnalyze = Array.from(files).slice(0, maxImagesToAnalyze);
    
    imagesToAnalyze.forEach((file, index) => {
        // Créer un FormData pour l'envoi du fichier
        const formData = new FormData();
        formData.append('image', file);
        
        // Simuler un délai pour éviter de surcharger le serveur
        setTimeout(() => {
            // Appel à l'API pour analyser l'image
            fetch('/api/analyze-image', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Trouver la carte correspondant à l'image
                const imagePreviewContainer = document.getElementById('image-preview-container');
                
                if (imagePreviewContainer) {
                    const cards = imagePreviewContainer.querySelectorAll('.card');
                    
                    if (cards && cards[index]) {
                        // Ajouter un badge avec le résultat de l'analyse
                        if (data.room_type) {
                            const badge = document.createElement('div');
                            badge.className = 'position-absolute top-0 start-0 m-2 badge bg-primary';
                            badge.textContent = data.room_type;
                            cards[index].appendChild(badge);
                        }
                        
                        // Ajouter d'autres informations si disponibles
                        if (data.features && data.features.length > 0) {
                            const featuresList = document.createElement('div');
                            featuresList.className = 'position-absolute bottom-0 start-0 m-2';
                            
                            data.features.forEach(feature => {
                                const featureBadge = document.createElement('span');
                                featureBadge.className = 'badge bg-info me-1 mb-1';
                                featureBadge.textContent = feature;
                                featuresList.appendChild(featureBadge);
                            });
                            
                            cards[index].appendChild(featuresList);
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error analyzing image:', error);
            });
        }, 1000 * index); // Délai progressif pour éviter les requêtes simultanées
    });
}

/**
 * Initialise la carte interactive sur la page de prévisualisation
 */
function initializeMap() {
    // Cette fonction est un placeholder, car la carte est générée côté serveur avec Folium
    // et injectée directement dans le HTML
}

/**
 * Partage une annonce sur les réseaux sociaux
 * @param {string} propertyId ID de la propriété à partager
 * @param {string} platform Plateforme de partage (facebook, twitter, linkedin, etc.)
 */
function shareProperty(propertyId, platform) {
    if (!propertyId || !platform) return;
    
    const propertyUrl = window.location.origin + '/property/' + propertyId;
    let shareUrl = '';
    
    switch (platform) {
        case 'facebook':
            shareUrl = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(propertyUrl);
            break;
        case 'twitter':
            shareUrl = 'https://twitter.com/intent/tweet?url=' + encodeURIComponent(propertyUrl) + '&text=' + encodeURIComponent('Découvrez cette annonce immobilière sur ImmoAI');
            break;
        case 'linkedin':
            shareUrl = 'https://www.linkedin.com/shareArticle?mini=true&url=' + encodeURIComponent(propertyUrl);
            break;
        case 'whatsapp':
            shareUrl = 'https://api.whatsapp.com/send?text=' + encodeURIComponent('Découvrez cette annonce immobilière sur ImmoAI: ' + propertyUrl);
            break;
        default:
            return;
    }
    
    // Ouvrir une nouvelle fenêtre pour le partage
    window.open(shareUrl, '_blank', 'width=600,height=400');
}

/**
 * Exporte une annonce au format PDF
 * @param {string} propertyId ID de la propriété à exporter
 */
function exportPropertyToPDF(propertyId) {
    if (!propertyId) return;
    
    // Rediriger vers l'endpoint d'export PDF
    window.location.href = '/export-pdf/' + propertyId;
}

/**
 * Affiche ou masque les champs supplémentaires en fonction du type de bien
 */
function toggleAdditionalFields() {
    const propertyType = document.getElementById('property_type');
    
    if (!propertyType) return;
    
    const additionalFieldsContainer = document.getElementById('additional-fields');
    
    if (!additionalFieldsContainer) return;
    
    // Afficher ou masquer les champs supplémentaires en fonction du type de bien
    switch (propertyType.value) {
        case 'Appartement':
        case 'Maison':
        case 'Studio':
        case 'Loft':
        case 'Duplex':
            additionalFieldsContainer.style.display = 'block';
            break;
        default:
            additionalFieldsContainer.style.display = 'none';
            break;
    }
}
