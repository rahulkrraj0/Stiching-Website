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
    const appbarEl = document.getElementById('appbar');
    if (appbarEl) appbarEl.classList.remove('nav-open');
  }
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
      const isOpen = navLinks.classList.toggle('open');
      navScrim && navScrim.classList.toggle('open', isOpen);
      navToggle.setAttribute('aria-expanded', String(isOpen));
      const appbarEl = document.getElementById('appbar');
      if (appbarEl) appbarEl.classList.toggle('nav-open', isOpen);
    });
    // Close the mobile nav when any nav link is clicked (ensures navigation works)
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        closeNav();
      });
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
  // Custom smooth scroller (shorter duration = faster slide)
  function animateScrollTo(container, target, duration = 250) {
    const start = container.scrollLeft;
    const change = target - start;
    const startTime = performance.now();
    const easeInOut = (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    function step(now) {
      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / duration);
      container.scrollLeft = Math.round(start + change * easeInOut(t));
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  document.querySelectorAll('.slider-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.dataset.target;
      const row = document.getElementById(targetId);
      if (!row) return;
      const offset = Math.round(row.clientWidth * 0.75);
      const target = btn.classList.contains('next') ? row.scrollLeft + offset : row.scrollLeft - offset;
      animateScrollTo(row, Math.max(0, target), 250);
    });
  });

  // ---- Enhanced Trending slider: dots, autoplay, update on scroll ----
  (function initTrendingSlider() {
    const row = document.getElementById('trending-row');
    if (!row) return;
    const slides = Array.from(row.children);
    if (slides.length === 0) return;
    const gap = 20; // must match CSS .product-row gap

    // create dots container
    const dotsWrap = document.createElement('div');
    dotsWrap.className = 'carousel-dots';
    slides.forEach((s, i) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'dot'; b.dataset.index = i;
      b.setAttribute('aria-label', 'Go to slide ' + (i + 1));
      dotsWrap.appendChild(b);
      b.addEventListener('click', () => {
        const rect = slides[0].getBoundingClientRect();
        const slideWidth = Math.round(rect.width) + gap;
        animateScrollTo(row, i * slideWidth, 250);
      });
    });
    row.parentNode.appendChild(dotsWrap);

    // update active dot based on scroll
    let ticking = false;
    const updateActive = () => {
      const rect = slides[0].getBoundingClientRect();
      const slideWidth = Math.round(rect.width) + gap;
      const idx = Math.round(row.scrollLeft / slideWidth);
      dotsWrap.querySelectorAll('.dot').forEach((d, i) => d.classList.toggle('active', i === idx));
      ticking = false;
    };
    row.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(updateActive);
        ticking = true;
      }
    });
    // init active
    updateActive();

    // autoplay
    let autoTimer = null;
    const startAutoplay = () => {
      if (autoTimer) return;
      autoTimer = setInterval(() => {
        const rect = slides[0].getBoundingClientRect();
        const slideWidth = Math.round(rect.width) + gap;
        const maxScroll = Math.max(0, row.scrollWidth - row.clientWidth);
        if (row.scrollLeft + slideWidth >= maxScroll - 2) {
          animateScrollTo(row, 0, 250);
        } else {
          animateScrollTo(row, row.scrollLeft + slideWidth, 250);
        }
      }, 3500);
    };
    const stopAutoplay = () => { if (autoTimer) { clearInterval(autoTimer); autoTimer = null; } };
    row.addEventListener('mouseenter', stopAutoplay);
    row.addEventListener('mouseleave', startAutoplay);
    row.addEventListener('touchstart', stopAutoplay, { passive: true });
    row.addEventListener('touchend', startAutoplay);
    startAutoplay();
  })();

  // ---- Drag-to-scroll for product rows ----
  const isCoarsePointer = window.matchMedia && window.matchMedia('(pointer:coarse)').matches;
  if (!isCoarsePointer) {
    document.querySelectorAll('.product-row').forEach(row => {
    let isDown = false;
    let startX = 0;
    let scrollLeft = 0;
    let moved = false;
    let movedDistance = 0;
      let pointerCaptured = false;
      let activePointerId = null;

    const onPointerDown = (e) => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      isDown = true;
      moved = false;
      row.classList.add('dragging');
      const rect = row.getBoundingClientRect();
      startX = e.clientX - rect.left;
      scrollLeft = row.scrollLeft;
        // don't capture pointer immediately; capture only if user actually drags
    };

    const onPointerMove = (e) => {
      if (!isDown) return;
      const rect = row.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const walk = (x - startX) * 1.2;
      movedDistance = Math.abs(walk);
      if (movedDistance > 12) moved = true;
        // start capturing the pointer only when drag threshold exceeded
        if (moved && !pointerCaptured) {
          try {
            row.setPointerCapture(e.pointerId);
            pointerCaptured = true;
            activePointerId = e.pointerId;
          } catch (err) {
            // ignore if not supported
          }
        }
      row.scrollLeft = scrollLeft - walk;
    };

    const onPointerUp = (e) => {
      if (!isDown) return;
      isDown = false;
      row.classList.remove('dragging');
        if (pointerCaptured && activePointerId != null) {
          try { row.releasePointerCapture(activePointerId); } catch (err) {}
          pointerCaptured = false;
          activePointerId = null;
        }
    };

    const onClick = (e) => {
      if (moved && movedDistance > 12) {
        e.preventDefault();
        e.stopPropagation();
      }
    };

      row.addEventListener('pointerdown', onPointerDown);
      row.addEventListener('pointermove', onPointerMove);
      row.addEventListener('pointerup', onPointerUp);
      row.addEventListener('pointerleave', onPointerUp);
      row.addEventListener('pointercancel', onPointerUp);
      row.addEventListener('click', onClick, false);
    });
  }

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
