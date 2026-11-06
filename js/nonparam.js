/* AsliPedas - Halaman Non-Parametrik: dropzone upload, tab data, tile uji, copy narasi */
(function () {
  /* ---------- Dropzone & Upload ---------- */
  var dz = document.getElementById('dropzone');
  var input = document.getElementById('file-input');
  var form = document.getElementById('upload-form');
  var prog = document.getElementById('upload-progress');
  var bar = document.getElementById('upload-bar');
  var errBox = document.getElementById('upload-error');

  function setBar(p) { if (bar) bar.style.width = p + '%'; }
  function startProgress() {
    if (errBox) errBox.innerHTML = '';
    if (prog) prog.classList.add('active');
    setBar(6);
  }
  function stopProgress() {
    if (prog) prog.classList.remove('active');
    setBar(0);
    try { input.value = ''; } catch (e) {}
  }

  if (dz && input && form) {
    function submitUpload() {
      if (!input.files || !input.files.length) return;
      startProgress();
      htmx.trigger(form, 'submit');
    }
    dz.addEventListener('click', function () { input.click(); });
    ['dragenter', 'dragover'].forEach(function (ev) {
      dz.addEventListener(ev, function (e) {
        e.preventDefault();
        dz.classList.add('dragging');
      });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      dz.addEventListener(ev, function (e) {
        e.preventDefault();
        dz.classList.remove('dragging');
      });
    });
    dz.addEventListener('drop', function (e) {
      var f = e.dataTransfer && e.dataTransfer.files;
      if (f && f.length) {
        try { input.files = f; } catch (err) {}
        submitUpload();
      }
    });
    input.addEventListener('change', function () { submitUpload(); });
    form.addEventListener('htmx:xhr:progress', function (evt) {
      var d = evt.detail || {};
      if (d.lengthComputable) setBar(Math.max(10, Math.round((d.loaded / d.total) * 100)));
      else setBar(55);
    });
    form.addEventListener('htmx:afterRequest', function () { stopProgress(); });
    form.addEventListener('htmx:responseError', function () {
      stopProgress();
      if (errBox) errBox.innerHTML = '<div class="inline-error">Server menolak permintaan. Periksa format file lalu coba lagi.</div>';
    });
    form.addEventListener('htmx:sendError', function () {
      stopProgress();
      if (errBox) errBox.innerHTML = '<div class="inline-error">Koneksi ke server terputus. Periksa jaringan lalu coba lagi.</div>';
    });
  }

  /* ---------- Delegasi Klik: Tab & Tile Uji ---------- */
  document.addEventListener('click', function (e) {
    var tb = e.target.closest('.tab-btn');
    if (tb) {
      var card = tb.closest('.tabs-card');
      if (card) {
        card.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.remove('active'); });
        tb.classList.add('active');
        var key = tb.getAttribute('data-tab');
        card.querySelectorAll('.tab-panel').forEach(function (p) {
          p.classList.toggle('active', p.getAttribute('data-panel') === key);
        });
      }
      return;
    }
    var tile = e.target.closest('.a-tile');
    if (tile) {
      if (tile.parentElement) {
        tile.parentElement.querySelectorAll('.a-tile').forEach(function (t) {
          t.classList.remove('active');
        });
      }
      tile.classList.add('active');
    }
  });

  /* ---------- Slider: perbarui nilai output ---------- */
  document.addEventListener('input', function (e) {
    var t = e.target;
    if (t && t.classList && t.classList.contains('rng')) {
      var out = t.nextElementSibling;
      if (out) out.value = t.value;
    }
  });

  /* ---------- Scroll halus setelah swap HTMX ---------- */
  document.body.addEventListener('htmx:afterSwap', function (e) {
    var id = e.detail && e.detail.target ? e.detail.target.id : '';
    if (id === 'workspace' || id === 'np-params' || id === 'np-results') {
      var el = document.getElementById(id);
      if (el) {
        var y = el.getBoundingClientRect().top + window.scrollY - 86;
        window.scrollTo({ top: y, behavior: 'smooth' });
      }
    }
  });

  /* ---------- Salin Narasi Analisis ---------- */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-copy-narasi]');
    if (!btn) return;
    var box = btn.closest('.narasi-card');
    if (!box) return;
    var paras = box.querySelectorAll('.narasi-p');
    var teks = [];
    paras.forEach(function (p) { teks.push(p.textContent.trim()); });
    function tandai() {
      var asli = btn.innerHTML;
      btn.innerHTML = '✓ Tersalin';
      btn.classList.add('copied');
      setTimeout(function () {
        btn.innerHTML = asli;
        btn.classList.remove('copied');
      }, 1800);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(teks.join('\n\n')).then(tandai).catch(function () {});
    }
  });
})();
