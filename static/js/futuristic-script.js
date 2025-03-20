// Futuristic Modern Script for Oikos

document.addEventListener('DOMContentLoaded', function() {
    // Navbar scroll effect
    const navbar = document.querySelector('.navbar');
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // Initialize scroll animations
    initScrollAnimations();
    
    // Initialize number counters
    initCounters();
    
    // Initialize hover effects
    initHoverEffects();
    
    // Initialize particle effects
    initParticleEffects();
});

// Scroll animations for elements
function initScrollAnimations() {
    const fadeElements = document.querySelectorAll('.fade-in');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                // Unobserve after animation
                if (entry.target.classList.contains('counter-value')) {
                    return;
                }
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });
    
    fadeElements.forEach(element => {
        observer.observe(element);
    });
}

// Number counter animation
function initCounters() {
    const counterElements = document.querySelectorAll('.counter-value');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = parseInt(entry.target.getAttribute('data-target'));
                const duration = 2000; // 2 seconds
                const step = Math.ceil(target / (duration / 16)); // 60fps
                
                let current = 0;
                const timer = setInterval(() => {
                    current += step;
                    if (current >= target) {
                        entry.target.textContent = target.toLocaleString();
                        clearInterval(timer);
                    } else {
                        entry.target.textContent = current.toLocaleString();
                    }
                }, 16);
                
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.5
    });
    
    counterElements.forEach(element => {
        observer.observe(element);
    });
}

// Hover effects for interactive elements
function initHoverEffects() {
    // Property cards hover effect
    const propertyCards = document.querySelectorAll('.property-card');
    
    propertyCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
            this.style.boxShadow = '0 15px 35px rgba(0, 0, 0, 0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.08)';
        });
    });
    
    // Location cards hover effect
    const locationCards = document.querySelectorAll('.location-card');
    
    locationCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            const image = this.querySelector('.location-image');
            const overlay = this.querySelector('.location-overlay');
            const button = this.querySelector('.location-button');
            
            image.style.transform = 'scale(1.05)';
            overlay.style.background = 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.4) 50%, rgba(0,0,0,0.1) 100%)';
            button.style.backgroundColor = 'var(--primary-color)';
        });
        
        card.addEventListener('mouseleave', function() {
            const image = this.querySelector('.location-image');
            const overlay = this.querySelector('.location-overlay');
            const button = this.querySelector('.location-button');
            
            image.style.transform = 'scale(1)';
            overlay.style.background = 'linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.2) 50%, rgba(0,0,0,0) 100%)';
            button.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
        });
    });
}

// Particle effects for hero section
function initParticleEffects() {
    const heroSection = document.querySelector('.hero-section');
    
    if (!heroSection) return;
    
    // Create particle container
    const particleContainer = document.createElement('div');
    particleContainer.classList.add('particle-container');
    particleContainer.style.position = 'absolute';
    particleContainer.style.top = '0';
    particleContainer.style.left = '0';
    particleContainer.style.width = '100%';
    particleContainer.style.height = '100%';
    particleContainer.style.overflow = 'hidden';
    particleContainer.style.zIndex = '0';
    
    heroSection.appendChild(particleContainer);
    
    // Create particles
    const particleCount = 20;
    
    for (let i = 0; i < particleCount; i++) {
        createParticle(particleContainer);
    }
}

function createParticle(container) {
    const particle = document.createElement('div');
    
    // Random size between 5px and 15px
    const size = Math.random() * 10 + 5;
    
    // Random position
    const posX = Math.random() * 100;
    const posY = Math.random() * 100;
    
    // Random opacity
    const opacity = Math.random() * 0.5 + 0.1;
    
    // Set styles
    particle.style.position = 'absolute';
    particle.style.width = `${size}px`;
    particle.style.height = `${size}px`;
    particle.style.borderRadius = '50%';
    particle.style.backgroundColor = 'var(--primary-color)';
    particle.style.opacity = opacity;
    particle.style.left = `${posX}%`;
    particle.style.top = `${posY}%`;
    particle.style.transform = 'translateZ(0)';
    
    // Add animation
    const duration = Math.random() * 20 + 10; // 10-30s
    const delay = Math.random() * 5; // 0-5s
    
    particle.style.animation = `float-particle ${duration}s ease-in-out ${delay}s infinite`;
    
    // Add to container
    container.appendChild(particle);
    
    // Define animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes float-particle {
            0%, 100% {
                transform: translate(0, 0);
            }
            25% {
                transform: translate(${Math.random() * 50 - 25}px, ${Math.random() * 50 - 25}px);
            }
            50% {
                transform: translate(${Math.random() * 100 - 50}px, ${Math.random() * 100 - 50}px);
            }
            75% {
                transform: translate(${Math.random() * 50 - 25}px, ${Math.random() * 50 - 25}px);
            }
        }
    `;
    
    document.head.appendChild(style);
}

// 3D tilt effect for cards
document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.property-card, .feature-card');
    
    cards.forEach(card => {
        card.addEventListener('mousemove', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left; // x position within the element
            const y = e.clientY - rect.top; // y position within the element
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const deltaX = (x - centerX) / centerX * 10; // max 10 degrees
            const deltaY = (y - centerY) / centerY * 10; // max 10 degrees
            
            this.style.transform = `perspective(1000px) rotateX(${-deltaY}deg) rotateY(${deltaX}deg) scale3d(1.02, 1.02, 1.02)`;
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale3d(1, 1, 1)';
        });
    });
});

// Animated search box
document.addEventListener('DOMContentLoaded', function() {
    const searchBox = document.querySelector('.search-box input');
    
    if (!searchBox) return;
    
    searchBox.addEventListener('focus', function() {
        this.parentElement.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.15)';
        this.parentElement.style.transform = 'translateY(-3px)';
    });
    
    searchBox.addEventListener('blur', function() {
        this.parentElement.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.08)';
        this.parentElement.style.transform = 'translateY(0)';
    });
});
