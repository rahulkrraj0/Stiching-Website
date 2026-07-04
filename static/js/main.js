// ==========================================================
// SilaiGhar — shared frontend behaviour
// ==========================================================

document.addEventListener('DOMContentLoaded', function () {

  // ---- Ripple effect on any .ripple-surface element ----
  document.querySelectorAll('.ripple-surface').forEach(el => {
    el.addEventListener('click', function (e) {
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const ripple = document.createElement('span');
      const bg = getComputedStyle(this).backgroundColor;
      const isDarkBg = bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent';
      ripple.className = 'ripple' + (isDarkBg ? '' : ' dark');
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
      ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 620);
    });
  });

  // ---- Mobile nav toggle ----
  const navToggle = document.getElementById('navToggle');
  const navLinks = document.getElementById('navLinks');
  const navScrim = document.getElementById('navScrim');
  function closeNav() {
    navLinks && navLinks.classList.remove('open');
    navScrim && navScrim.classList.remove('open');
    navToggle && navToggle.setAttribute('aria-expanded', 'false');
  }
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
      const isOpen = navLinks.classList.toggle('open');
      navScrim && navScrim.classList.toggle('open', isOpen);
      navToggle.setAttribute('aria-expanded', String(isOpen));
    });
  }
  if (navScrim) navScrim.addEventListener('click', closeNav);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeNav(); });

  // ---- Categories dropdown: click-toggle so it works on touch, still hovers on desktop ----
  const catDropdown = document.getElementById('catDropdown');
  const catDropToggle = document.getElementById('catDropToggle');
  if (catDropdown && catDropToggle) {
    catDropToggle.addEventListener('click', (e) => {
      e.preventDefault();
      const isOpen = catDropdown.classList.toggle('open');
      catDropToggle.setAttribute('aria-expanded', String(isOpen));
    });
    document.addEventListener('click', (e) => {
      if (!catDropdown.contains(e.target)) {
        catDropdown.classList.remove('open');
        catDropToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // ---- App bar elevation on scroll ----
  const appbar = document.getElementById('appbar');
  if (appbar) {
    window.addEventListener('scroll', () => {
      appbar.classList.toggle('scrolled', window.scrollY > 8);
    });
  }

  // ---- Trending slider controls ----
  document.querySelectorAll('.slider-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.dataset.target;
      const row = document.getElementById(targetId);
      if (!row) return;
      const offset = Math.round(row.clientWidth * 0.75);
      row.scrollBy({ left: btn.classList.contains('next') ? offset : -offset, behavior: 'smooth' });
    });
  });

  // ---- Drag-to-scroll for product rows ----
  document.querySelectorAll('.product-row').forEach(row => {
    let isDown = false;
    let startX = 0;
    let scrollLeft = 0;
    let moved = false;

    const onPointerDown = (e) => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      isDown = true;
      moved = false;
      row.classList.add('dragging');
      const rect = row.getBoundingClientRect();
      startX = e.clientX - rect.left;
      scrollLeft = row.scrollLeft;
      e.preventDefault();
      row.setPointerCapture(e.pointerId);
    };

    const onPointerMove = (e) => {
      if (!isDown) return;
      e.preventDefault();
      const rect = row.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const walk = (x - startX) * 1.2;
      if (Math.abs(walk) > 5) moved = true;
      row.scrollLeft = scrollLeft - walk;
    };

    const onPointerUp = (e) => {
      if (!isDown) return;
      isDown = false;
      row.classList.remove('dragging');
      if (e.pointerId != null) row.releasePointerCapture(e.pointerId);
    };

    const onClick = (e) => {
      if (moved) {
        e.preventDefault();
        e.stopPropagation();
      }
    };

    row.addEventListener('pointerdown', onPointerDown);
    row.addEventListener('pointermove', onPointerMove);
    row.addEventListener('pointerup', onPointerUp);
    row.addEventListener('pointerleave', onPointerUp);
    row.addEventListener('pointercancel', onPointerUp);
    row.addEventListener('click', onClick, true);
  });

  // ---- FAB scrolls to the booking form ----
  const fab = document.getElementById('fabBtn');
  if (fab) {
    fab.addEventListener('click', () => {
      const order = document.getElementById('order');
      if (order) order.scrollIntoView({ behavior: 'smooth', block: 'center' });
      else window.location.href = '/#order';
    });
  }

  // ---- Snackbar helper ----
  window.showSnackbar = function (msg) {
    const bar = document.getElementById('snackbar');
    if (!bar) return;
    document.getElementById('snackbarText').textContent = msg;
    bar.classList.add('show');
    clearTimeout(window._snackTimer);
    window._snackTimer = setTimeout(() => bar.classList.remove('show'), 4200);
  };

  // ---- Booking form (present on homepage) ----
  const orderForm = document.getElementById('orderForm');
  if (orderForm) {
    orderForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const name = document.getElementById('name').value || 'there';
      const design = document.getElementById('design').value || 'not specified';
      const query = document.getElementById('address').value || 'not provided';
      const msg = `Hello SilaiGhar!%0A%0AName: ${encodeURIComponent(name)}%0ADesign: ${encodeURIComponent(design)}%0AQuery: ${encodeURIComponent(query)}%0A%0APlease send me a measurement visit confirmation.`;
      const waNumber = document.body.dataset.whatsapp || '';
      const whatsappLink = `https://wa.me/${waNumber}?text=${msg}`;
      window.open(whatsappLink, '_blank');
      window.showSnackbar('Opening WhatsApp with your request — send it to confirm your booking.');
      this.reset();
    });
  }

  // ---- "Enquire" buttons on product detail pages ----
  document.querySelectorAll('.enquire-btn').forEach(btn => {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      window.showSnackbar("Thanks! We've noted your interest — mention this design when you book your measurement visit.");
    });
  });

  // ---- Video fallback: if no video file is present, show the placeholder ----
  const video = document.getElementById('brandVideo');
  const placeholder = document.getElementById('videoPlaceholder');
  if (video && placeholder) {
    video.addEventListener('error', () => {
      video.style.display = 'none';
      placeholder.style.display = 'flex';
    }, true);
    // If metadata loads fine, hide the placeholder
    video.addEventListener('loadedmetadata', () => {
      placeholder.style.display = 'none';
    });
    // Trigger an initial check
    if (video.readyState === 0) {
      placeholder.style.display = 'flex';
    }
  }

  // ---- Ticker: ensure smooth continuous scroll ----
  const tickerTrack = document.querySelector('.ticker-track');
  if (tickerTrack) {
    // nothing extra required; CSS handles animation. If you want pause-on-hover:
    tickerTrack.addEventListener('mouseenter', () => tickerTrack.style.animationPlayState = 'paused');
    tickerTrack.addEventListener('mouseleave', () => tickerTrack.style.animationPlayState = 'running');
  }
});
