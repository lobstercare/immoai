/**
 * Animation pour l'image de la maison parisienne
 * Ajoute des effets interactifs et des animations supplémentaires
 */

// Fonction principale d'initialisation
function initParishouseAnimation(selector) {
    console.log("Initialisation de l'animation de la maison parisienne...");
    
    const parishouseImage = document.querySelector(selector);
    if (!parishouseImage) {
        console.error("L'élément sélectionné n'existe pas:", selector);
        return;
    }
    
    console.log("Image trouvée, configuration des animations...");
    
    // Effet de parallaxe au mouvement de la souris
    const container = parishouseImage.closest('.parishouse-container');
    
    if (container) {
        // S'assurer que les styles de particules sont ajoutés
        addParticleStyles();
        
        // Animation autonome plus prononcée - démarrer immédiatement
        animateHouseAutonomously(parishouseImage);
        
        // Puis continuer périodiquement
        setInterval(() => {
            animateHouseAutonomously(parishouseImage);
        }, 3000);
        
        // Démarrer l'animation autonome des particules
        startAutonomousParticles(container);
        
        // Effet de parallaxe au mouvement de la souris (plus subtil)
        container.addEventListener('mousemove', (e) => {
            const xAxis = (window.innerWidth / 2 - e.pageX) / 35;
            const yAxis = (window.innerHeight / 2 - e.pageY) / 35;
            
            // Appliquer une légère rotation à l'image en fonction de la position de la souris
            parishouseImage.style.transform = `rotateY(${xAxis}deg) rotateX(${yAxis}deg) scale(1.05)`;
        });
        
        // Réinitialiser la rotation quand la souris quitte le conteneur
        container.addEventListener('mouseleave', () => {
            parishouseImage.style.transform = '';
        });
        
        // Animation au survol
        container.addEventListener('mouseenter', () => {
            // Ajouter une classe pour une animation spéciale au survol
            parishouseImage.classList.add('hover-effect');
            
            // Créer des éléments décoratifs animés
            addDecorativeElements(container);
        });
        
        container.addEventListener('mouseleave', () => {
            // Retirer la classe d'effet au survol
            parishouseImage.classList.remove('hover-effect');
        });
        
        console.log("Animation de la maison parisienne initialisée avec succès!");
    } else {
        console.error("Conteneur parent non trouvé pour l'image");
    }
}

// Animation autonome de la maison
function animateHouseAutonomously(element) {
    console.log("Animation autonome déclenchée");
    
    // Générer une animation aléatoire
    const animations = [
        { transform: 'translateY(-40px) rotate(3deg) scale(1.03)', filter: 'drop-shadow(0 20px 30px rgba(255, 193, 7, 0.7)) sepia(40%) saturate(200%)' },
        { transform: 'translateY(-30px) rotate(-2deg) scale(1.02)', filter: 'drop-shadow(0 15px 25px rgba(255, 193, 7, 0.6)) sepia(35%) saturate(180%)' },
        { transform: 'translateY(-35px) rotate(1deg) scale(1.04)', filter: 'drop-shadow(0 18px 28px rgba(255, 193, 7, 0.65)) sepia(38%) saturate(190%)' }
    ];
    
    const randomAnimation = animations[Math.floor(Math.random() * animations.length)];
    
    // Appliquer l'animation avec transition
    element.style.transition = 'transform 1.5s ease-in-out, filter 1.5s ease-in-out';
    element.style.transform = randomAnimation.transform;
    element.style.filter = randomAnimation.filter;
    
    // Revenir à l'état normal après un délai
    setTimeout(() => {
        element.style.transition = 'transform 2s ease-in-out, filter 2s ease-in-out';
        element.style.transform = '';
        element.style.filter = '';
    }, 1500);
}

// Fonction pour ajouter des éléments décoratifs animés
function addDecorativeElements(container) {
    // Vérifier si les éléments existent déjà pour éviter les doublons
    const existingElements = container.querySelectorAll('.decoration-particle');
    if (existingElements.length > 10) return;
    
    console.log("Ajout d'éléments décoratifs");
    
    // Créer quelques particules décoratives
    for (let i = 0; i < 8; i++) {
        const particle = document.createElement('div');
        particle.classList.add('decoration-particle');
        
        // Positionner aléatoirement
        particle.style.left = `${Math.random() * 100}%`;
        particle.style.top = `${Math.random() * 100}%`;
        
        // Taille aléatoire
        const size = 8 + Math.random() * 15;
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;
        
        // Ajouter au conteneur
        container.appendChild(particle);
        
        // Supprimer après l'animation
        setTimeout(() => {
            if (particle.parentNode === container) {
                container.removeChild(particle);
            }
        }, 3000);
    }
}

// Fonction pour démarrer l'animation autonome des particules
function startAutonomousParticles(container) {
    console.log("Démarrage de l'animation autonome des particules");
    
    // Ajouter immédiatement quelques particules
    addDecorativeElements(container);
    
    // Puis continuer périodiquement
    setInterval(() => {
        // Ne pas ajouter trop de particules
        if (container.querySelectorAll('.decoration-particle').length < 5) {
            const particle = document.createElement('div');
            particle.classList.add('decoration-particle', 'autonomous-particle');
            
            // Positionner aléatoirement
            particle.style.left = `${Math.random() * 100}%`;
            particle.style.top = `${Math.random() * 100}%`;
            
            // Taille aléatoire
            const size = 5 + Math.random() * 10;
            particle.style.width = `${size}px`;
            particle.style.height = `${size}px`;
            
            // Ajouter au conteneur
            container.appendChild(particle);
            
            // Supprimer après l'animation
            setTimeout(() => {
                if (particle.parentNode === container) {
                    container.removeChild(particle);
                }
            }, 4000);
        }
    }, 800);
}

// Ajouter des styles CSS pour les particules
function addParticleStyles() {
    if (document.getElementById('particle-styles')) return;
    
    console.log("Ajout des styles CSS pour les particules");
    
    const styleElement = document.createElement('style');
    styleElement.id = 'particle-styles';
    styleElement.textContent = `
        .decoration-particle {
            position: absolute;
            background-color: rgba(255, 193, 7, 0.7);
            border-radius: 50%;
            pointer-events: none;
            animation: float-particle 3s ease-out forwards;
            box-shadow: 0 0 10px rgba(255, 193, 7, 0.5);
        }
        
        .autonomous-particle {
            animation: float-autonomous-particle 4s ease-out forwards;
        }
        
        @keyframes float-particle {
            0% {
                transform: translateY(0) scale(0);
                opacity: 0;
            }
            20% {
                opacity: 1;
            }
            100% {
                transform: translateY(-120px) scale(1.8);
                opacity: 0;
            }
        }
        
        @keyframes float-autonomous-particle {
            0% {
                transform: translateY(0) scale(0);
                opacity: 0;
            }
            20% {
                opacity: 0.8;
            }
            100% {
                transform: translateY(-150px) rotate(45deg) scale(2);
                opacity: 0;
            }
        }
        
        .hover-effect {
            animation: none !important;
            transition: transform 0.3s ease-out, filter 0.3s ease-out;
            filter: drop-shadow(0 20px 30px rgba(255, 193, 7, 0.8)) sepia(40%) saturate(200%) !important;
            transform: scale(1.05) !important;
        }
    `;
    
    document.head.appendChild(styleElement);
}

// Initialiser les styles de particules et l'animation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM chargé, initialisation des styles de particules");
    addParticleStyles();
    
    // Initialiser automatiquement l'animation si l'élément existe
    const parishouseImage = document.querySelector('.parishouse-image');
    if (parishouseImage) {
        console.log("Image trouvée automatiquement, initialisation de l'animation");
        initParishouseAnimation('.parishouse-image');
    } else {
        console.log("Image non trouvée automatiquement, attente de l'appel manuel");
    }
});
