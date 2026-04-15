// Hero Carousel
function initHeroCarousel() {
    const carousels = document.querySelectorAll('.hero-carousel');
    
    carousels.forEach(carousel => {
        const slides = carousel.querySelectorAll('.carousel-slide');
        const dots = carousel.querySelectorAll('.dot');
        const prevBtn = carousel.querySelector('.carousel-prev');
        const nextBtn = carousel.querySelector('.carousel-next');
        
        if (!slides.length) return;
        
        let currentIndex = 0;
        
        function showSlide(index) {
            slides.forEach((slide, i) => {
                slide.classList.toggle('active', i === index);
            });
            dots.forEach((dot, i) => {
                dot.classList.toggle('active', i === index);
            });
        }
        
        function nextSlide() {
            currentIndex = (currentIndex + 1) % slides.length;
            showSlide(currentIndex);
        }
        
        function prevSlide() {
            currentIndex = (currentIndex - 1 + slides.length) % slides.length;
            showSlide(currentIndex);
        }
        
        if (prevBtn) prevBtn.addEventListener('click', prevSlide);
        if (nextBtn) nextBtn.addEventListener('click', nextSlide);
        
        dots.forEach((dot, i) => {
            dot.addEventListener('click', () => {
                currentIndex = i;
                showSlide(currentIndex);
            });
        });
        
        // Auto-play (opsiyonel)
        setInterval(nextSlide, 5000);
    });
}

// Countdown Timer
function initHeroCountdown() {
    const countdowns = document.querySelectorAll('.hero-countdown');
    
    countdowns.forEach(countdown => {
        const targetDate = countdown.dataset.target;
        if (!targetDate) return;
        
        const timerEl = countdown.querySelector('.countdown-timer');
        if (!timerEl) return;
        
        function updateCountdown() {
            const now = new Date().getTime();
            const target = new Date(targetDate).getTime();
            const diff = target - now;
            
            if (diff <= 0) {
                timerEl.textContent = "00:00:00:00";
                return;
            }
            
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (86400000)) / (3600000));
            const minutes = Math.floor((diff % (3600000)) / (60000));
            const seconds = Math.floor((diff % (60000)) / 1000);
            
            timerEl.textContent = `${days}d ${hours}h ${minutes}m ${seconds}s`;
        }
        
        updateCountdown();
        setInterval(updateCountdown, 1000);
    });
}

// Initialize all hero components
document.addEventListener('DOMContentLoaded', () => {
    initHeroCarousel();
    initHeroCountdown();
});
