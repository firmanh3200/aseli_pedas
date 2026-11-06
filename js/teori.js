/* AseliPedas - Pustaka Uji Statistik: datatable (search, filter, sort, pagination, expand) */
(function () {
  "use strict";

  var tbody = document.getElementById("dt-body");
  if (!tbody) return;

  var qInput = document.getElementById("dt-q");
  var qClear = document.getElementById("dt-q-clear");
  var fGrup = document.getElementById("dt-grup");
  var fKat = document.getElementById("dt-kat");
  var sizeSel = document.getElementById("dt-size");
  var infoEl = document.getElementById("dt-info");
  var pagerEl = document.getElementById("dt-pager");
  var emptyEl = document.getElementById("dt-empty");
  var counterEl = document.getElementById("dt-counter");
  var resetBtn = document.getElementById("dt-reset");
  var headRow = document.querySelector("#dt-table thead tr");

  /* ---------- State ---------- */
  var state = { q: "", grup: "", kat: "", sort: "no", dir: 1, page: 1, size: 10 };

  /* ---------- Entries: pasangan baris utama + baris detail ---------- */
  var entries = [];
  Array.prototype.forEach.call(tbody.querySelectorAll("tr.dt-row"), function (row) {
    entries.push({
      row: row,
      det: document.getElementById(row.getAttribute("aria-controls")),
      no: parseInt(row.querySelector(".dt-no").textContent, 10) || 0,
      judul: row.getAttribute("data-judul") || "",
      grup: row.getAttribute("data-grup") || "",
      grupt: row.getAttribute("data-grupt") || "",
      kat: row.getAttribute("data-kat") || "",
      search: row.getAttribute("data-search") || ""
    });
  });

  function norm(s) {
    return (s || "").toLowerCase().replace(/\s+/g, " ").trim();
  }

  /* ---------- Ekspansi detail (accordion) ---------- */
  function setExpand(entry, open) {
    if (!entry.det) return;
    entry.det.hidden = !open;
    entry.row.classList.toggle("open", open);
    entry.row.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function toggle(entry) {
    var open = entry.det && entry.det.hidden;
    setExpand(entry, open);
  }

  entries.forEach(function (entry) {
    entry.row.addEventListener("click", function (ev) {
      if (ev.target.closest("a")) return; /* biarkan link bekerja */
      toggle(entry);
    });
    entry.row.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        toggle(entry);
      }
    });
  });

  /* ---------- Filter + sort ---------- */
  function filtered() {
    var q = norm(state.q);
    var out = entries.filter(function (e) {
      if (state.grup && e.grup !== state.grup) return false;
      if (state.kat && e.kat !== state.kat) return false;
      if (q && e.search.indexOf(q) === -1) return false;
      return true;
    });
    var k = state.sort, d = state.dir;
    if (k === "no") out.sort(function (a, b) { return (a.no - b.no) * d; });
    else if (k === "judul") out.sort(function (a, b) { return a.judul.localeCompare(b.judul, "id") * d; });
    else if (k === "grup") out.sort(function (a, b) { return (a.grupt.localeCompare(b.grupt, "id") || a.no - b.no) * d; });
    else if (k === "kat") out.sort(function (a, b) { return (a.kat.localeCompare(b.kat) || a.no - b.no) * d; });
    return out;
  }

  /* ---------- Pagination ---------- */
  function pageCount(n) {
    return state.size > 0 ? Math.max(1, Math.ceil(n / state.size)) : 1;
  }

  function buildPager(total, pages) {
    pagerEl.textContent = "";
    if (pages <= 1) return;

    function btn(label, page, opts) {
      opts = opts || {};
      var b = document.createElement("button");
      b.type = "button";
      b.className = "dt-page-btn" + (opts.cls ? " " + opts.cls : "");
      b.textContent = label;
      if (opts.page != null) b.setAttribute("data-page", opts.page);
      if (opts.disabled) b.disabled = true;
      if (opts.active) b.setAttribute("aria-current", "page");
      b.setAttribute("aria-label", opts.label || ("Halaman " + page));
      pagerEl.appendChild(b);
    }

    btn("\u2039", state.page - 1, { cls: "dt-nav", page: state.page - 1, disabled: state.page <= 1, label: "Halaman sebelumnya" });

    var win = [];
    for (var p = 1; p <= pages; p++) {
      if (p === 1 || p === pages || Math.abs(p - state.page) <= 1) win.push(p);
    }
    var last = 0;
    win.forEach(function (p) {
      if (last && p - last > 1) {
        var s = document.createElement("span");
        s.className = "dt-ellipsis";
        s.textContent = "\u2026";
        pagerEl.appendChild(s);
      }
      btn(String(p), p, { page: p, active: p === state.page });
      last = p;
    });

    btn("\u203A", state.page + 1, { cls: "dt-nav", page: state.page + 1, disabled: state.page >= pages, label: "Halaman berikutnya" });
  }

  /* ---------- Render ---------- */
  function apply(opts) {
    opts = opts || {};
    var list = filtered();
    var total = list.length;
    var pages = pageCount(total);

    if (state.page > pages) state.page = pages;
    var start = state.size > 0 ? (state.page - 1) * state.size : 0;
    var end = state.size > 0 ? Math.min(start + state.size, total) : total;

    /* Sembunyikan semua, tampilkan irisan halaman (detail ikut barisnya) */
    entries.forEach(function (e) {
      e.row.style.display = "none";
      if (!e.det.hidden) e.det.hidden = true;
    });
    list.slice(start, end).forEach(function (e) {
      e.row.style.display = "";
      if (e.row.classList.contains("open") && e.det) e.det.hidden = false;
    });

    /* Susun ulang urutan DOM sesuai hasil sort/filter */
    var frag = document.createDocumentFragment();
    list.forEach(function (e) { frag.appendChild(e.row); frag.appendChild(e.det); });
    tbody.appendChild(frag);

    /* Info & counter */
    if (total === 0) {
      infoEl.textContent = "";
      counterEl.textContent = "0";
    } else {
      infoEl.textContent = "Menampilkan " + (start + 1) + "\u2013" + end + " dari " + total + " uji";
      counterEl.textContent = String(total);
    }
    emptyEl.classList.toggle("show", total === 0);

    /* Indikator sort di header */
    if (headRow) {
      Array.prototype.forEach.call(headRow.querySelectorAll(".dt-sortable"), function (th) {
        var on = th.getAttribute("data-sort") === state.sort;
        th.classList.toggle("asc", on && state.dir === 1);
        th.classList.toggle("desc", on && state.dir === -1);
        th.setAttribute("aria-sort", on ? (state.dir === 1 ? "ascending" : "descending") : "none");
      });
    }

    buildPager(total, pages);

    /* reset partial */
    if (!opts.keepScroll) state.page = Math.min(state.page, Math.max(1, pages));
  }

  /* ---------- Interaksi kontrol ---------- */
  var debounce;
  qInput.addEventListener("input", function () {
    clearTimeout(debounce);
    debounce = setTimeout(function () {
      state.q = qInput.value;
      state.page = 1;
      apply();
    }, 140);
    qClear.classList.toggle("show", qInput.value.length > 0);
  });
  qInput.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") {
      qInput.value = "";
      state.q = "";
      state.page = 1;
      qClear.classList.remove("show");
      apply();
    }
  });
  qClear.addEventListener("click", function () {
    qInput.value = "";
    state.q = "";
    state.page = 1;
    qClear.classList.remove("show");
    qInput.focus();
    apply();
  });

  fGrup.addEventListener("change", function () { state.grup = fGrup.value; state.page = 1; apply(); });
  fKat.addEventListener("change", function () { state.kat = fKat.value; state.page = 1; apply(); });

  sizeSel.addEventListener("change", function () {
    state.size = parseInt(sizeSel.value, 10) || 0;
    state.page = 1;
    apply();
  });

  pagerEl.addEventListener("click", function (ev) {
    var b = ev.target.closest("button[data-page]");
    if (!b || b.disabled) return;
    state.page = parseInt(b.getAttribute("data-page"), 10);
    apply();
    var wrap = document.querySelector(".dt-wrap");
    if (wrap) {
      var y = wrap.getBoundingClientRect().top + window.scrollY - 78;
      if (window.scrollY > y) window.scrollTo({ top: y, behavior: "smooth" });
    }
  });

  if (headRow) {
    headRow.addEventListener("click", function (ev) {
      var th = ev.target.closest(".dt-sortable");
      if (!th) return;
      var k = th.getAttribute("data-sort");
      if (state.sort === k) state.dir = -state.dir;
      else { state.sort = k; state.dir = 1; }
      state.page = 1;
      apply();
    });
  }

  resetBtn.addEventListener("click", function () {
    state = { q: "", grup: "", kat: "", sort: "no", dir: 1, page: 1, size: state.size };
    qInput.value = "";
    fGrup.value = "";
    fKat.value = "";
    qClear.classList.remove("show");
    apply();
    qInput.focus();
  });

  /* ---------- Deep-link #uji-<key> ---------- */
  function openFromHash() {
    var m = /^#uji-([\w-]+)$/.exec(location.hash || "");
    if (!m) return false;
    var key = m[1];
    var hit = entries.filter(function (e) { return e.row.getAttribute("data-key") === key; })[0];
    if (!hit) return false;

    /* jika pencarian/filter aktif menyembunyikan target, bersihkan dulu */
    if (filtered().indexOf(hit) === -1) {
      state.q = ""; qInput.value = "";
      state.grup = ""; fGrup.value = "";
      state.kat = ""; fKat.value = "";
      qClear.classList.remove("show");
    }

    /* pastikan baris berada pada halaman yang tepat sesuai filter aktif */
    var list = filtered();
    var idx = list.indexOf(hit);
    if (idx >= 0 && state.size > 0) state.page = Math.floor(idx / state.size) + 1;

    entries.forEach(function (e) { setExpand(e, false); });
    setExpand(hit, true);
    apply({ keepScroll: true });

    hit.row.classList.remove("flash");
    void hit.row.offsetWidth; /* restart animasi */
    hit.row.classList.add("flash");
    setTimeout(function () {
      var y = hit.row.getBoundingClientRect().top + window.scrollY - 96;
      window.scrollTo({ top: y, behavior: "smooth" });
    }, 60);
    return true;
  }
  window.addEventListener("hashchange", openFromHash);
  openFromHash();

  apply();
})();
