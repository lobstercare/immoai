// Animation 3D d'un bâtiment immobilier
// Utilise Three.js chargé via CDN

// Initialisation de la scène
function init3DBuilding(containerId) {
    // Créer la scène, la caméra et le renderer
    const container = document.getElementById(containerId);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8f9fa);
    
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(15, 10, 15);
    
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);
    
    // Ajouter des contrôles pour permettre la rotation
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.screenSpacePanning = false;
    controls.minDistance = 10;
    controls.maxDistance = 30;
    controls.maxPolarAngle = Math.PI / 2;
    
    // Ajouter un éclairage
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 20, 10);
    directionalLight.castShadow = true;
    scene.add(directionalLight);
    
    // Créer un sol
    const groundGeometry = new THREE.PlaneGeometry(50, 50);
    const groundMaterial = new THREE.MeshStandardMaterial({ 
        color: 0x8bc34a,
        roughness: 0.8,
    });
    const ground = new THREE.Mesh(groundGeometry, groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);
    
    // Créer plusieurs bâtiments
    createBuildings(scene);
    
    // Animation
    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }
    
    // Gérer le redimensionnement de la fenêtre
    window.addEventListener('resize', () => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });
    
    // Lancer l'animation
    animate();
}

// Fonction pour créer plusieurs bâtiments
function createBuildings(scene) {
    // Couleurs pour les bâtiments
    const buildingColors = [
        0x4fc3f7, // bleu clair
        0xec407a, // rose
        0xffb74d, // orange
        0x9575cd, // violet
        0x4db6ac, // turquoise
        0xf06292, // rose clair
        0x7986cb  // bleu-violet
    ];
    
    // Créer un groupe pour tous les bâtiments
    const buildingsGroup = new THREE.Group();
    
    // Créer plusieurs bâtiments de différentes tailles et positions
    for (let i = 0; i < 15; i++) {
        // Position aléatoire dans une grille
        const x = (Math.random() - 0.5) * 30;
        const z = (Math.random() - 0.5) * 30;
        
        // Taille aléatoire
        const width = 1 + Math.random() * 3;
        const height = 2 + Math.random() * 8;
        const depth = 1 + Math.random() * 3;
        
        // Créer le bâtiment
        const building = createBuilding(
            width, height, depth,
            buildingColors[Math.floor(Math.random() * buildingColors.length)]
        );
        
        // Positionner le bâtiment
        building.position.set(x, height / 2, z);
        
        // Ajouter au groupe
        buildingsGroup.add(building);
    }
    
    // Ajouter un bâtiment principal plus grand au centre
    const mainBuilding = createBuilding(5, 10, 5, 0x4fc3f7);
    mainBuilding.position.set(0, 5, 0);
    buildingsGroup.add(mainBuilding);
    
    // Ajouter le groupe à la scène
    scene.add(buildingsGroup);
    
    // Animation du groupe de bâtiments
    function animateBuildings() {
        buildingsGroup.rotation.y += 0.002;
        requestAnimationFrame(animateBuildings);
    }
    
    animateBuildings();
}

// Fonction pour créer un bâtiment
function createBuilding(width, height, depth, color) {
    // Créer le corps du bâtiment
    const geometry = new THREE.BoxGeometry(width, height, depth);
    const material = new THREE.MeshStandardMaterial({ 
        color: color,
        roughness: 0.5,
        metalness: 0.2
    });
    
    const building = new THREE.Mesh(geometry, material);
    building.castShadow = true;
    building.receiveShadow = true;
    
    // Ajouter des fenêtres
    addWindows(building, width, height, depth);
    
    return building;
}

// Fonction pour ajouter des fenêtres à un bâtiment
function addWindows(building, width, height, depth) {
    const windowGeometry = new THREE.PlaneGeometry(0.3, 0.5);
    const windowMaterial = new THREE.MeshStandardMaterial({ 
        color: 0xffff99,
        emissive: 0xffff00,
        emissiveIntensity: 0.3,
        side: THREE.DoubleSide
    });
    
    // Nombre de fenêtres par étage et nombre d'étages
    const floorsCount = Math.floor(height / 1.2);
    const windowsPerFloor = Math.floor(width / 0.7);
    
    // Créer les fenêtres pour les 4 côtés du bâtiment
    for (let side = 0; side < 4; side++) {
        for (let floor = 0; floor < floorsCount; floor++) {
            for (let w = 0; w < windowsPerFloor; w++) {
                const window = new THREE.Mesh(windowGeometry, windowMaterial);
                
                // Positionner la fenêtre selon le côté du bâtiment
                if (side === 0) {
                    window.position.set(
                        (w - windowsPerFloor / 2 + 0.5) * 0.7,
                        floor * 1.2 - height / 2 + 1,
                        depth / 2 + 0.01
                    );
                } else if (side === 1) {
                    window.position.set(
                        width / 2 + 0.01,
                        floor * 1.2 - height / 2 + 1,
                        (w - windowsPerFloor / 2 + 0.5) * 0.7
                    );
                    window.rotation.y = Math.PI / 2;
                } else if (side === 2) {
                    window.position.set(
                        (w - windowsPerFloor / 2 + 0.5) * 0.7,
                        floor * 1.2 - height / 2 + 1,
                        -depth / 2 - 0.01
                    );
                    window.rotation.y = Math.PI;
                } else {
                    window.position.set(
                        -width / 2 - 0.01,
                        floor * 1.2 - height / 2 + 1,
                        (w - windowsPerFloor / 2 + 0.5) * 0.7
                    );
                    window.rotation.y = -Math.PI / 2;
                }
                
                building.add(window);
            }
        }
    }
    
    // Ajouter un toit
    const roofGeometry = new THREE.ConeGeometry(Math.max(width, depth) / 1.5, height / 5, 4);
    const roofMaterial = new THREE.MeshStandardMaterial({ 
        color: 0xd32f2f,
        roughness: 0.7
    });
    
    const roof = new THREE.Mesh(roofGeometry, roofMaterial);
    roof.position.y = height / 2 + height / 10;
    roof.rotation.y = Math.PI / 4;
    roof.castShadow = true;
    
    building.add(roof);
    
    return building;
}

// Exporter la fonction d'initialisation
export { init3DBuilding };
