/* AseliPedas - Halaman Perbandingan File Data:
   dua dropzone unggah, tab hasil SAMA/BEDA, salin narasi, scroll halus */
(function () {
  /* ---------- Dua Dropzone & Upload (slot 1 dan 2) ---------- */
  ["1", "2"].forEach(function (no) {
    var dz = document.getElementById('dropzone-' + no);
    var input = document.getElementById('file-input-' + no);
    var form = document.getElementById('upload-form-' + no);
    var prog = document.getElementById('upload-progress-' + no);
    var bar = document.getElementById('upload-bar-' + no);
    var errBox = document.getElementById('upload-error-' + no);
    if (!dz || !input || !form) return;

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
  });

  /* ---------- Delegasi Klik: Tab hasil SAMA/BEDA ---------- */
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
    }
  });

  /* ---------- Scroll halus setelah swap HTMX ---------- */
  document.body.addEventListener('htmx:afterSwap', function (e) {
    var id = e.detail && e.detail.target ? e.detail.target.id : '';
    if (id === 'komparasi-workspace' || id === 'komparasi-hasil') {
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
