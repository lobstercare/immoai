/**
 * Script pour le design moderne et élégant d'Oikos
 */

document.addEventListener('DOMContentLoaded', function() {
    // Navbar scroll effect
    const navbar = document.querySelector('.navbar');
    
    if (navbar) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }
    
    // Fade-in animation for elements
    const fadeElements = document.querySelectorAll('.fade-in');
    
    function checkFade() {
        fadeElements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            const elementBottom = element.getBoundingClientRect().bottom;
            
            // Check if element is in viewport
            if (elementTop < window.innerHeight - 100 && elementBottom > 0) {
                element.classList.add('visible');
            }
        });
    }
    
    // Initial check for elements in view
    checkFade();
    
    // Check on scroll
    window.addEventListener('scroll', checkFade);
    
    // Search tabs functionality
    const searchTabs = document.querySelectorAll('.search-tab');
    
    searchTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs
            searchTabs.forEach(t => t.classList.remove('active'));
            
            // Add active class to clicked tab
            this.classList.add('active');
        });
    });
    
    // Animated counters for stats
    const counters = document.querySelectorAll('.stat-value');
    
    function animateCounters() {
        counters.forEach(counter => {
            const target = parseInt(counter.innerText);
            const count = 0;
            const speed = 50;
            
            const updateCount = () => {
                const increment = target / (2000 / speed); // Adjust for desired animation duration
                
                if (count < target) {
                    counter.innerText = Math.ceil(count + increment);
                    setTimeout(updateCount, speed);
                } else {
                    counter.innerText = target;
                }
            };
            
            updateCount();
        });
    }
    
    // Intersection Observer for counter animation
    const observerOptions = {
        threshold: 0.5
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe the stats section if it exists
    const statsSection = document.querySelector('.stat-container');
    if (statsSection) {
        observer.observe(statsSection);
    }
    
    // Property card hover effects
    const propertyCards = document.querySelectorAll('.property-card');
    
    propertyCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
            this.style.boxShadow = '0 15px 30px rgba(0, 0, 0, 0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 5px 15px rgba(0, 0, 0, 0.05)';
        });
    });
    
    // Sidebar toggle functionality
    const body = document.body;
    const sidebarToggle = document.getElementById('sidebar-toggle');
    
    if (sidebarToggle) {
        // Check if sidebar state is saved in localStorage
        const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        
        // Apply saved state on page load
        if (sidebarCollapsed) {
            body.classList.add('sidebar-collapsed');
            sidebarToggle.querySelector('i').classList.remove('fa-chevron-left');
            sidebarToggle.querySelector('i').classList.add('fa-chevron-right');
        }
        
        // Toggle sidebar on button click
        sidebarToggle.addEventListener('click', function() {
            body.classList.toggle('sidebar-collapsed');
            
            // Save state to localStorage
            const isCollapsed = body.classList.contains('sidebar-collapsed');
            localStorage.setItem('sidebarCollapsed', isCollapsed);
            
            // Update icon
            const icon = sidebarToggle.querySelector('i');
            if (isCollapsed) {
                icon.classList.remove('fa-chevron-left');
                icon.classList.add('fa-chevron-right');
            } else {
                icon.classList.remove('fa-chevron-right');
                icon.classList.add('fa-chevron-left');
            }
        });
    }
});
