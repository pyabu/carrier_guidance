/* ════════════════════════════════════════════════════════════════════════
   CareerPath Pro – Main JavaScript
   Handles: Dark/Light Mode, Navbar, Animations, Toast, Search, etc.
   ════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initNavbar();
    initAOS();
    initMobileMenu();
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
    if (icon) {
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

/* ── Navbar Scroll Effect ────────────────────────────────────────────── */

function initNavbar() {
    const navbar = document.getElementById('navbar');
    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const currentScroll = window.scrollY;
        if (currentScroll > 50) {
            navbar?.classList.add('scrolled');
        } else {
            navbar?.classList.remove('scrolled');
        }
        lastScroll = currentScroll;
    });
}

/* ── Mobile Menu ─────────────────────────────────────────────────────── */

function initMobileMenu() {
    const toggle = document.getElementById('navToggle');
    const menu = document.getElementById('navMenu');

    toggle?.addEventListener('click', () => {
        menu?.classList.toggle('open');
        toggle.classList.toggle('active');

        // Animate hamburger
        const spans = toggle.querySelectorAll('span');
        if (menu?.classList.contains('open')) {
            spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
            spans[1].style.opacity = '0';
            spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
        } else {
            spans[0].style.transform = 'none';
            spans[1].style.opacity = '1';
            spans[2].style.transform = 'none';
        }
    });

    // Mobile dropdown toggle
    document.querySelectorAll('.nav-dropdown > .nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
                e.preventDefault();
                link.parentElement.classList.toggle('open');
            }
        });
    });

    // Close menu on link click
    document.querySelectorAll('.dropdown-menu a').forEach(a => {
        a.addEventListener('click', () => {
            menu?.classList.remove('open');
        });
    });
}

/* ── AOS (Animate On Scroll) Init ────────────────────────────────────── */

function initAOS() {
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 600,
            easing: 'ease-out-cubic',
            once: true,
            offset: 50,
        });
    }
}

/* ── Toast Notifications ─────────────────────────────────────────────── */

function showToast(message, type = 'success') {
    // Remove existing toast
    document.querySelector('.toast')?.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}" 
           style="color:var(--${type === 'success' ? 'success' : 'danger'});font-size:1.2rem;"></i>
        <span>${message}</span>
    `;
    document.body.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // Auto-remove
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
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

/* ── Smooth Scroll for Anchor Links ──────────────────────────────────── */

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

/* ── Counter Animation (for stats) ───────────────────────────────────── */

function animateCounters() {
    const counters = document.querySelectorAll('.stat-number');
    counters.forEach(counter => {
        const text = counter.textContent;
        const match = text.match(/(\d[\d,]*)/);
        if (!match) return;
        
        const target = parseInt(match[1].replace(/,/g, ''));
        const suffix = text.replace(match[0], '');
        let current = 0;
        const increment = Math.ceil(target / 60);
        const duration = 1500;
        const stepTime = duration / (target / increment);

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                counter.textContent = text;
                clearInterval(timer);
            } else {
                counter.textContent = current.toLocaleString() + suffix;
            }
        }, stepTime);
    });
}

// Trigger counter animation when visible
const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            animateCounters();
            statsObserver.disconnect();
        }
    });
});

const statsEl = document.querySelector('.hero-stats');
if (statsEl) statsObserver.observe(statsEl);

/* ── Keyboard shortcuts ──────────────────────────────────────────────── */

document.addEventListener('keydown', (e) => {
    // Ctrl+K or Cmd+K → Focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const search = document.getElementById('heroKeyword') || document.getElementById('searchKeyword');
        search?.focus();
    }

    // Escape → Close mobile menu
    if (e.key === 'Escape') {
        document.getElementById('navMenu')?.classList.remove('open');
        document.getElementById('postJobModal')?.style.setProperty('display', 'none');
    }
});

/* ── Last Update Time ────────────────────────────────────────────────── */

async function fetchLastUpdate() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        const el = document.getElementById('lastUpdate');
        if (el && data.last_updated) {
            el.textContent = `Jobs last updated: ${data.last_updated}`;
        }
    } catch (e) { /* silent */ }
}
fetchLastUpdate();
