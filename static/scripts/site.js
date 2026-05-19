/* Planet Python — minimal site script.
 *
 * Two responsibilities:
 *   1. Drive the reading-progress bar at the top of the viewport.
 *   2. Toggle the visibility of the back-to-top button after 400px of scroll.
 *
 * Plain DOM, no dependencies. ~600 bytes uncompressed.
 */
(function () {
  'use strict';

  var bar = document.getElementById('reading-progress');
  var btn = document.getElementById('back-to-top');

  function update() {
    var h = document.documentElement;
    var scrolled = h.scrollTop || document.body.scrollTop;
    var max = h.scrollHeight - h.clientHeight;
    if (bar && max > 0) {
      bar.style.width = (scrolled / max * 100) + '%';
    }
    if (btn) {
      btn.classList.toggle('visible', scrolled > 400);
    }
  }

  // requestAnimationFrame coalesces scroll events so we never run more than
  // once per frame, which keeps things smooth even on long pages.
  var ticking = false;
  window.addEventListener('scroll', function () {
    if (!ticking) {
      window.requestAnimationFrame(function () {
        update();
        ticking = false;
      });
      ticking = true;
    }
  }, { passive: true });

  update();
})();
