/**
 * Animation SVG pour la page d'accueil
 * Ajoute des effets interactifs à l'illustration du bâtiment
 */

function initSVGAnimation(selector) {
    const svgElement = document.querySelector(selector);
    
    if (!svgElement) {
        console.error("Élément SVG non trouvé");
        return;
    }
    
    // Ajouter une légère rotation au survol
    svgElement.addEventListener('mousemove', function(e) {
        const rect = svgElement.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Calculer la rotation en fonction de la position de la souris
        const rotateX = (y - rect.height / 2) / 20;
        const rotateY = (rect.width / 2 - x) / 20;
        
        // Appliquer la transformation
        svgElement.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
    });
    
    // Remettre à zéro quand la souris quitte l'élément
    svgElement.addEventListener('mouseleave', function() {
        svgElement.style.transform = 'perspective(1000px) rotateX(0) rotateY(0)';
    });
    
    // Ajouter une transition pour un effet plus fluide
    svgElement.style.transition = 'transform 0.2s ease-out';
}

// Exporter la fonction
window.initSVGAnimation = initSVGAnimation;
