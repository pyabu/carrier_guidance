/* ════════════════════════════════════════════════════════════════════════
   CareerPath Pro – Main JavaScript
   Handles: Autocomplete, Dark/Light Mode, Navbar, Animations, etc.
   ════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initNavbar();
    initAOS();
    initMobileMenu();
    initAutocomplete();
    initScrollProgress();
});

/* ── Dark / Light Theme Toggle ───────────────────────────────────────── */

function initTheme() {
    const toggle = document.getElementById('themeToggle');
    const saved = localStorage.getItem('theme') || 'light';
    setTheme(saved);
    toggle?.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        setTheme(next);
        localStorage.setItem('theme', next);
    });
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const icon = document.querySelector('#themeToggle i');
    if (icon) icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
}

/* ── Navbar Scroll Effect ────────────────────────────────────────────── */

function initNavbar() {
    const navbar = document.getElementById('navbar');
    let lastScroll = 0;
    window.addEventListener('scroll', () => {
        const cur = window.scrollY;
        if (cur > 50) navbar?.classList.add('scrolled');
        else navbar?.classList.remove('scrolled');
        if (cur > 300) {
            if (cur > lastScroll + 10) navbar?.classList.add('nav-hidden');
            else if (cur < lastScroll - 10) navbar?.classList.remove('nav-hidden');
        } else { navbar?.classList.remove('nav-hidden'); }
        lastScroll = cur;
    });
}

/* ── Scroll Progress Bar ─────────────────────────────────────────────── */

function initScrollProgress() {
    const bar = document.createElement('div');
    bar.className = 'scroll-progress';
    document.body.appendChild(bar);
    window.addEventListener('scroll', () => {
        const pct = document.documentElement.scrollHeight - window.innerHeight;
        bar.style.width = pct > 0 ? ((window.scrollY / pct) * 100) + '%' : '0%';
    });
}

/* ── Mobile Menu ─────────────────────────────────────────────────────── */

function initMobileMenu() {
    const toggle = document.getElementById('navToggle');
    const menu = document.getElementById('navMenu');
    toggle?.addEventListener('click', () => {
        menu?.classList.toggle('open');
        toggle.classList.toggle('active');
        if (menu?.classList.contains('open')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    });
    // Fix for mobile nav dropdowns getting stuck
    document.querySelectorAll('.nav-dropdown > .nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
                e.preventDefault();
                const parent = link.parentElement;
                
                // Close other open dropdowns first for cleaner UX
                document.querySelectorAll('.nav-dropdown').forEach(dropdown => {
                    if (dropdown !== parent) {
                        dropdown.classList.remove('open');
                    }
                });
                
                parent.classList.toggle('open');
            }
        });
    });
    
    document.querySelectorAll('.dropdown-menu a').forEach(a => {
        a.addEventListener('click', () => { 
            menu?.classList.remove('open'); 
            
            // Remove 'open' from all dropdowns on click
            document.querySelectorAll('.nav-dropdown').forEach(d => d.classList.remove('open'));
            
            // Reset hamburger icon
            if (toggle && toggle.classList.contains('active')) {
                toggle.classList.remove('active');
            }
            
            document.body.style.overflow = ''; 
        });
    });
}

/* ── AOS Init ────────────────────────────────────────────────────────── */

function initAOS() {
    if (typeof AOS !== 'undefined') {
        AOS.init({ duration: 600, easing: 'ease-out-cubic', once: true, offset: 50, disable: 'mobile' });
    }
}

/* ════════════════════════════════════════════════════════════════════════
   LOCATION AUTOCOMPLETE
   ════════════════════════════════════════════════════════════════════════ */

let acDebounce = null;

function initAutocomplete() {
    const inputs = document.querySelectorAll('[data-autocomplete="location"]');
    inputs.forEach(input => {
        const wrapper = document.createElement('div');
        wrapper.className = 'ac-wrapper';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const dropdown = document.createElement('div');
        dropdown.className = 'ac-dropdown';
        wrapper.appendChild(dropdown);

        input.addEventListener('input', () => {
            clearTimeout(acDebounce);
            acDebounce = setTimeout(() => fetchSuggestions(input, dropdown), 180);
        });

        input.addEventListener('focus', () => {
            if (input.value.trim().length > 0) fetchSuggestions(input, dropdown);
            else showPopularCities(dropdown, input);
        });

        document.addEventListener('click', (e) => {
            if (!wrapper.contains(e.target)) dropdown.classList.remove('show');
        });

        input.addEventListener('keydown', (e) => {
            const items = dropdown.querySelectorAll('.ac-item');
            let idx = [...items].findIndex(i => i.classList.contains('ac-active'));
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                items[idx]?.classList.remove('ac-active');
                idx = Math.min(idx + 1, items.length - 1);
                items[idx]?.classList.add('ac-active');
                items[idx]?.scrollIntoView({ block: 'nearest' });
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                items[idx]?.classList.remove('ac-active');
                idx = Math.max(idx - 1, 0);
                items[idx]?.classList.add('ac-active');
                items[idx]?.scrollIntoView({ block: 'nearest' });
            } else if (e.key === 'Enter' && idx >= 0) {
                e.preventDefault();
                items[idx]?.click();
            } else if (e.key === 'Escape') {
                dropdown.classList.remove('show');
            }
        });
    });
}

async function fetchSuggestions(input, dropdown) {
    const q = input.value.trim();
    if (q.length === 0) { showPopularCities(dropdown, input); return; }
    try {
        const res = await fetch(`/api/autocomplete/locations?q=${encodeURIComponent(q)}`);
        const suggestions = await res.json();
        renderSuggestions(dropdown, suggestions, input, q);
    } catch (e) { dropdown.classList.remove('show'); }
}

function showPopularCities(dropdown, input) {
    const popular = [
        { name: 'Bangalore', icon: 'fa-fire', tag: 'Top IT Hub' },
        { name: 'Chennai', icon: 'fa-industry', tag: 'Tamil Nadu' },
        { name: 'Mumbai', icon: 'fa-building', tag: 'Financial Capital' },
        { name: 'Delhi NCR', icon: 'fa-landmark', tag: 'NCR Region' },
        { name: 'Hyderabad', icon: 'fa-microchip', tag: 'Cyberabad' },
        { name: 'Pune', icon: 'fa-graduation-cap', tag: 'IT & Education' },
        { name: 'Coimbatore', icon: 'fa-cogs', tag: 'Tamil Nadu' },
        { name: 'Kolkata', icon: 'fa-city', tag: 'West Bengal' },
        { name: 'Madurai', icon: 'fa-gopuram', tag: 'Tamil Nadu' },
        { name: 'Pondicherry', icon: 'fa-umbrella-beach', tag: 'Puducherry' },
        { name: 'Kochi', icon: 'fa-ship', tag: 'Kerala' },
        { name: 'Remote', icon: 'fa-laptop-house', tag: 'Work from Home' },
    ];
    dropdown.innerHTML = `<div class="ac-header"><i class="fas fa-star"></i> Popular Cities in India</div>` +
        popular.map(c => `
            <div class="ac-item ac-popular" data-value="${c.name}">
                <i class="fas ${c.icon} ac-icon"></i>
                <div class="ac-text">
                    <span class="ac-name">${c.name}</span>
                    <span class="ac-tag">${c.tag}</span>
                </div>
            </div>`).join('');
    bindAcItems(dropdown, input);
    dropdown.classList.add('show');
}

function renderSuggestions(dropdown, suggestions, input, query) {
    if (!suggestions.length) {
        dropdown.innerHTML = '<div class="ac-empty"><i class="fas fa-map-marker-alt"></i> No locations found</div>';
        dropdown.classList.add('show');
        return;
    }
    dropdown.innerHTML = suggestions.map(s => {
        const idx = s.toLowerCase().indexOf(query.toLowerCase());
        let hl = s;
        if (idx >= 0) hl = s.substring(0, idx) + '<strong>' + s.substring(idx, idx + query.length) + '</strong>' + s.substring(idx + query.length);
        return `<div class="ac-item" data-value="${s}"><i class="fas fa-map-marker-alt ac-icon"></i><span class="ac-name">${hl}</span></div>`;
    }).join('');
    bindAcItems(dropdown, input);
    dropdown.classList.add('show');
}

function bindAcItems(dropdown, input) {
    dropdown.querySelectorAll('.ac-item').forEach(item => {
        item.addEventListener('click', () => {
            input.value = item.dataset.value;
            dropdown.classList.remove('show');
            if (typeof heroSearch === 'function' && input.id === 'heroLocation') heroSearch();
            if (typeof searchJobs === 'function' && input.id === 'searchLocation') searchJobs();
        });
    });
}

/* ── Toast Notifications ─────────────────────────────────────────────── */

function showToast(message, type = 'success') {
    document.querySelector('.toast')?.remove();
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = { success: 'check-circle', error: 'exclamation-circle', info: 'info-circle', warning: 'exclamation-triangle' };
    toast.innerHTML = `<i class="fas fa-${icons[type] || icons.success}"></i><span>${message}</span><button class="toast-close" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>`;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => { toast.classList.remove('show'); setTimeout(() => toast.remove(), 300); }, 4000);
}

/* ── Save/Bookmark Jobs ──────────────────────────────────────────────── */

function toggleSave(btn) {
    const icon = btn.querySelector('i');
    const isSaved = icon.classList.contains('fas');
    if (isSaved) {
        icon.classList.replace('fas', 'far');
        btn.classList.remove('saved');
        showToast('Job removed from saved list', 'error');
    } else {
        icon.classList.replace('far', 'fas');
        btn.classList.add('saved');
        showToast('Job saved successfully!', 'success');
    }
}

/* ── Smooth Scroll ───────────────────────────────────────────────────── */

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        const target = document.querySelector(this.getAttribute('href'));
        if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
});

/* ── Counter Animation ───────────────────────────────────────────────── */

function animateCounters() {
    document.querySelectorAll('.stat-number').forEach(counter => {
        if (counter.dataset.animated) return;
        counter.dataset.animated = '1';
        const text = counter.textContent;
        const match = text.match(/(\d[\d,]*)/);
        if (!match) return;
        const target = parseInt(match[1].replace(/,/g, ''));
        const suffix = text.replace(match[0], '');
        const duration = 1200;
        const start = performance.now();
        function step(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.round(target * eased);
            counter.textContent = current.toLocaleString() + suffix;
            if (progress < 1) requestAnimationFrame(step);
            else counter.textContent = text;
        }
        requestAnimationFrame(step);
    });
}

const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => { if (entry.isIntersecting) animateCounters(); });
}, { threshold: 0.3 });
const statsEl = document.querySelector('.hero-stats');
if (statsEl) statsObserver.observe(statsEl);

/* ── Keyboard shortcuts ──────────────────────────────────────────────── */

document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const search = document.getElementById('heroKeyword') || document.getElementById('searchKeyword');
        search?.focus();
    }
    if (e.key === 'Escape') {
        document.getElementById('navMenu')?.classList.remove('open');
        document.querySelectorAll('.ac-dropdown').forEach(d => d.classList.remove('show'));
        document.body.style.overflow = '';
    }
});

/* ── Back to Top Button ──────────────────────────────────────────────── */

(function() {
    const btn = document.createElement('button');
    btn.className = 'back-to-top';
    btn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    btn.title = 'Back to top';
    document.body.appendChild(btn);
    btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    window.addEventListener('scroll', () => btn.classList.toggle('visible', window.scrollY > 500));
})();

/* ── Last Update Time ────────────────────────────────────────────────── */

async function fetchLastUpdate() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        const el = document.getElementById('lastUpdate');
        if (el && data.last_updated) el.textContent = `Jobs last updated: ${data.last_updated}`;
        const totalEl = document.getElementById('totalJobs');
        if (totalEl && data.total_jobs) totalEl.textContent = data.total_jobs.toLocaleString() + '+';
    } catch (e) { /* silent */ }
}
fetchLastUpdate();

/* ── Typed Text Effect removed (caused layout jumping) ──────────────── */

/* ── Card Tilt Effect ────────────────────────────────────────────────── */

if (window.matchMedia('(hover: hover)').matches) {
    document.querySelectorAll('.ai-feature-card, .category-card').forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width - 0.5) * 4;
            const y = ((e.clientY - rect.top) / rect.height - 0.5) * -4;
            card.style.transform = `perspective(800px) rotateX(${y}deg) rotateY(${x}deg)`;
        });
        card.addEventListener('mouseleave', () => {
            card.style.transition = 'transform 0.4s ease';
            card.style.transform = '';
            setTimeout(() => { card.style.transition = ''; }, 400);
        });
    });
}