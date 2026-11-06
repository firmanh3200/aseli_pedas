# -*- coding: utf-8 -*-
"""
AseliPedas - Aplikasi Pengolah Statistik Dasar (FastHTML Edition)
================================================================
Konversi dari aplikasi Streamlit asli dengan fungsi yang sama:
  - Unggah file multi-format: CSV, XLS, XLSX, DBF, JSON, TXT, TSV, Parquet
  - Pratinjau data (10 baris pertama)
  - Statistik dasar 13 metrik untuk semua kolom numerik
  - Detail per kolom + histogram distribusi interaktif
  - Statistik kolom kategorik
  - Unduh hasil statistik sebagai CSV

Cara menjalankan:
  python app.py            -> http://0.0.0.0:3000
  PORT=8080 python app.py  -> port kustom
"""
import os
import io
import csv
import json
import math
import uuid
import tempfile

import numpy as np
import pandas as pd
from fasthtml.common import (
    fast_app, Div, Section, Header, Footer, Main, Form, H1, H2, H3, P, Span,
    B, Button, Input, Select, Option, Label, Table, Thead, Tbody, Tr, Th, Td,
    Canvas, Script, Link, Meta, Title, A, NotStr,
)
from starlette.requests import Request
from starlette.responses import Response

from narasi import narasi_dasar_kolom, narasi_dasar_ringkasan, narasi_dasar_kategorik

try:
    from dbfread import DBF
    DBF_OK = True
except ImportError:
    DBF_OK = False

try:
    import pyreadstat
    SAV_OK = True
except ImportError:
    SAV_OK = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FORMATS = ["csv", "xls", "xlsx", "xlsm", "sav", "dta", "dbf", "json",
           "txt", "tsv", "dat", "parquet", "pkl"]
ACCEPT_STR = ",".join(f".{e}" for e in FORMATS)
SESSIONS = {}
MAX_SESSIONS = 12

CHARTJS_LOCAL = os.path.join(BASE_DIR, "vendor", "chart.umd.min.js")
CHARTJS_SRC = "/vendor/chart.umd.min.js" if os.path.exists(CHARTJS_LOCAL) else (
    "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"
)
FONTS_URL = (
    "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800"
    "&family=JetBrains+Mono:wght@500;600;700&display=swap"
)
FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E"
    "%3Crect width='100' height='100' rx='22' fill='%237C5CFC'/%3E"
    "%3Cpath d='M26 72V52h12v20zm18 0V32h12v40zm18 0V44h12v28z' fill='white'/%3E%3C/svg%3E"
)


# ==========================================
# PEMBACAAN DATA BERBAGAI FORMAT
# ==========================================
def _read_delimited(file_bytes, base_msg):
    """Pembaca file CSV/TXT yang andal: deteksi pemisah via csv.Sniffer,
    lalu coba kandidat pemisah umum sebelum fallback ke auto-detect pandas."""
    encodings = ["utf-8", "utf-8-sig", "latin-1"]
    last_err = None
    for enc in encodings:
        try:
            file_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
        sep_terdeteksi = None
        try:
            sep_terdeteksi = csv.Sniffer().sniff(
                file_bytes.decode(enc)[:8192], delimiters=",;\t|"
            ).delimiter
        except csv.Error:
            pass
        kandidat = ([sep_terdeteksi] if sep_terdeteksi else []) + [",", ";", "\t", "|", None]
        for s in kandidat:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc, sep=s, engine="python")
                if df.shape[1] >= 1:
                    return df
            except Exception as e:
                last_err = e
                continue
    raise ValueError(f"{base_msg} ({last_err})")


def load_data(file_bytes, filename):
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".csv":
        return _read_delimited(file_bytes, "Gagal membaca file CSV.")

    elif ext in [".xls", ".xlsx", ".xlsm"]:
        return pd.read_excel(io.BytesIO(file_bytes))

    elif ext == ".tsv":
        return pd.read_csv(io.BytesIO(file_bytes), sep="\t")

    elif ext == ".json":
        data = json.loads(file_bytes.decode("utf-8"))
        return pd.json_normalize(data)

    elif ext == ".dbf":
        if not DBF_OK:
            raise ValueError("Library dbfread belum terinstall. Jalankan: pip install dbfread")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dbf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            table = DBF(tmp_path, encoding="latin-1")
            return pd.DataFrame(iter(table))
        finally:
            os.remove(tmp_path)

    elif ext == ".parquet":
        return pd.read_parquet(io.BytesIO(file_bytes))

    elif ext == ".sav":
        if not SAV_OK:
            raise ValueError("Library pyreadstat belum terinstall. Jalankan: pip install pyreadstat")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sav") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            d, _ = pyreadstat.read_sav(tmp_path)
            return d
        finally:
            os.remove(tmp_path)

    elif ext == ".dta":
        return pd.read_stata(io.BytesIO(file_bytes))

    elif ext in [".pkl", ".pickle"]:
        return pd.read_pickle(io.BytesIO(file_bytes))

    elif ext in [".txt", ".dat"]:
        return _read_delimited(file_bytes, "Gagal membaca file teks.")

    else:
        raise ValueError(f"Format file {ext} belum didukung.")


def hitung_statistik(df):
    """Menghitung statistik dasar semua kolom numerik (paritas dengan versi Streamlit)."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return None
    stats = pd.DataFrame({
        "Jumlah Data": df[numeric_cols].count(),
        "Mean (Rata-rata)": df[numeric_cols].mean(),
        "Median": df[numeric_cols].median(),
        "Modus": df[numeric_cols].mode().iloc[0],
        "Std Deviasi": df[numeric_cols].std(),
        "Variansi": df[numeric_cols].var(),
        "Minimum": df[numeric_cols].min(),
        "Maksimum": df[numeric_cols].max(),
        "Q1 (25%)": df[numeric_cols].quantile(0.25),
        "Q3 (75%)": df[numeric_cols].quantile(0.75),
        "Range": df[numeric_cols].max() - df[numeric_cols].min(),
        "Skewness": df[numeric_cols].skew(),
        "Kurtosis": df[numeric_cols].kurtosis(),
    })
    return stats.round(4)


# ==========================================
# UTIL FORMAT ANGKA
# ==========================================
def fmt_stat(x):
    try:
        if x is None or pd.isna(x):
            return "-"
    except (TypeError, ValueError):
        pass
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return str(x)
    if abs(xf) >= 1e15:
        return f"{xf:.3e}"
    if xf == int(xf):
        return f"{int(xf):,}"
    if abs(xf) >= 100:
        return f"{xf:,.1f}"
    if abs(xf) >= 1:
        s = f"{xf:,.3f}"
    else:
        s = f"{xf:.4f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def bf(x):
    a = abs(x)
    if a >= 1000:
        return f"{x:,.0f}"
    if a >= 100:
        return f"{x:.0f}"
    if a >= 1:
        return f"{x:.1f}"
    return f"{x:.2f}"


def size_str(n):
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.2f} MB"


def _prune_sessions():
    while len(SESSIONS) > MAX_SESSIONS:
        oldest = next(iter(SESSIONS))
        SESSIONS.pop(oldest, None)


# ==========================================
# IKON SVG (gaya Lucide, tanpa emoji)
# ==========================================
ICONS = {
    "cloud": '<path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="M12 12v9"/><path d="m16 16-4-4-4 4"/>',
    "check": '<path d="M21.801 10A10 10 0 1 1 17 3.335"/><path d="m9 11 3 3L22 4"/>',
    "reset": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "eye": '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
    "chart": '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    "sliders": '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/>',
    "sigma": '<path d="M18 7V4H6l6 8-6 8h12v-3"/>',
    "align": '<line x1="21" x2="3" y1="6" y2="6"/><line x1="17" x2="7" y1="12" y2="12"/><line x1="19" x2="5" y1="18" y2="18"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "percent": '<line x1="19" x2="5" y1="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    "up": '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
    "down": '<path d="m19 12-7 7-7-7"/><path d="M12 5v14"/>',
    "list": '<line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/>',
    "trash": '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>',
    "tag": '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/>',
    "sparkles": '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "layers": '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    "chat": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 9h8"/><path d="M8 12h5"/>',
    "book": '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>',
    "shuffle": '<path d="M2 18h1.4c1.3 0 2.5-.6 3.3-1.7l6.1-8.6c.8-1.1 2-1.7 3.3-1.7H22"/><path d="m18 2 4 4-4 4"/><path d="M2 6h1.9c1.5 0 2.9.9 3.6 2.2"/><path d="M22 18h-5.9c-1.3 0-2.6-.7-3.3-1.8l-.5-.8"/><path d="m18 14 4 4-4 4"/>',
    "leftright": '<path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/><path d="M4 17h16"/>',
}


def icon(name, size=18):
    inner = ICONS[name]
    return NotStr(
        f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{inner}</svg>'
    )


# ==========================================
# KOMPONEN HALAMAN
# ==========================================
def top_nav(active="/"):
    def nav_link(href, ic, label):
        return A(icon(ic, 15), Span(label), href=href,
                 cls="nav-link" + (" active" if href == active else ""))
    return Header(
        Div(
            Div(
                Div(icon("chart", 20), cls="brand-mark"),
                Div(
                    Div("AseliPedas", cls="brand-name"),
                    Div("", cls="brand-sub"),
                ),
                cls="brand",
            ),
            Div(
                nav_link("/teori", "book", "Beranda"),
                nav_link("/", "sigma", "Dasar"),
                nav_link("/inferens", "zap", "Inferens"),
                nav_link("/nonparam", "shuffle", "Non Parametrik"),
                nav_link("/komparasi", "leftright", "Komparasi"),
                cls="nav-links",
            ),
            cls="nav-inner",
        ),
        cls="topnav",
    )


def hero_section():
    return Div(
        Span(icon("sparkles", 13), "Analisis Data Instan", cls="eyebrow"),
        H1(
            "Dari data mentah menjadi ",
            Span("insight statistik", cls="grad-text"),
            " dalam hitungan detik",
        ),
        P(
            "Unggah file data Anda - CSV, Excel, DBF, JSON, TXT, TSV, hingga Parquet - "
            "dan dapatkan ringkasan statistik lengkap beserta distribusi datanya secara instan, "
            "tanpa instalasi apa pun.",
            cls="hero-sub",
        ),
        Div(
            Div(
                Div(icon("zap", 16), cls="feature-ic"),
                Div(B("Instan & Otomatis"), Span("13 metrik statistik dihitung seketika setelah file diunggah.")),
                cls="feature",
            ),
            Div(
                Div(icon("shield", 16), cls="feature-ic"),
                Div(B("Privat & Aman"), Span("Semua data diproses lokal di server dan tidak pernah dibagikan.")),
                cls="feature",
            ),
            Div(
                Div(icon("layers", 16), cls="feature-ic"),
                Div(B("Fleksibel"), Span("Mendukung 8 format file dengan pratinjau data interaktif.")),
                cls="feature",
            ),
            cls="features anim-in d1",
        ),
        cls="hero",
    )


def upload_section():
    return Section(
        Div(
            Div(icon("cloud", 28), cls="drop-ic"),
            H3("Tarik & letakkan file di sini", cls="drop-title"),
            P("atau klik area ini untuk ", Span("memilih file", cls="link-like"), " dari perangkat Anda", cls="drop-hint"),
            id="dropzone",
            cls="dropzone",
        ),
        Input(type="file", name="file", id="file-input", accept=ACCEPT_STR, cls="sr-only"),
        Div(Div(id="upload-bar", cls="progress-bar"), id="upload-progress", cls="progress-wrap"),
        Div(id="upload-error"),
        Div(*[Span(f.upper(), cls="fmt-chip") for f in FORMATS], cls="fmt-row"),
        P(icon("shield", 13), " File diproses sepenuhnya secara lokal di server - tidak dibagikan ke pihak mana pun.", cls="privacy-note"),
        id="upload-section",
        cls="upload-card card anim-in",
    )


def empty_state():
    return Div(
        Div(icon("database", 30), cls="empty-ic"),
        H3("Belum Ada Data"),
        P("Unggah file untuk melihat pratinjau data dan menghitung statistik dasar. Hasil analisis akan muncul di area ini."),
        Div(*[Span(f.upper(), cls="fmt-chip") for f in FORMATS], cls="fmt-row"),
        cls="empty-card",
    )


def upload_error_fragment(msg, kind="error"):
    cls_ikon = "err-ic" if kind == "error" else "warn-ic"
    nama = "err-ic"
    return Div(
        Div(icon("alert", 20), cls=cls_ikon),
        Div(
            B("Gagal Memproses File" if kind == "error" else "Perhatian"),
            P(msg),
            cls="err-body",
        ),
        cls=f"card {'error-card' if kind == 'error' else 'warn-card'} anim-in",
    )


def data_table(df):
    head = Tr(Th("#", cls="idx-th"), *[Th(str(c), title=str(c)) for c in df.columns])
    body = []
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        tds = [Td(str(i), cls="idx-td")]
        for v in row:
            try:
                is_nan = bool(pd.isna(v))
            except (TypeError, ValueError):
                is_nan = False
            if is_nan:
                tds.append(Td("NaN", cls="na-td", title="Data kosong"))
            elif isinstance(v, float):
                tds.append(Td(fmt_stat(v), cls="num-td"))
            else:
                s = str(v)
                tds.append(Td(s, title=s))
        body.append(Tr(*tds))
    return Table(Thead(head), Tbody(*body), cls="data-table preview-table")


def uploaded_fragment(sid, df, filename, size_bytes):
    n_rows, n_cols = df.shape
    return Div(
        Div(
            Div(icon("check", 20), cls="banner-ic"),
            Div(
                B(filename),
                Span(f"{n_rows:,} baris · {n_cols:,} kolom · {size_str(size_bytes)}", cls="banner-meta"),
                cls="banner-body",
            ),
            Button(
                icon("reset", 15), "Ganti File",
                cls="btn btn-ghost btn-sm",
                hx_post="/reset", hx_target="#workspace", hx_swap="innerHTML",
            ),
            cls="banner anim-in",
        ),
        Section(
            Div(icon("eye", 17), H3("Pratinjau Data"), Span("10 baris pertama", cls="chip"), cls="sec-head"),
            Div(data_table(df.head(10)), cls="table-wrap"),
            P(f"Menampilkan {min(10, n_rows)} dari {n_rows:,} baris", cls="table-note"),
            cls="card anim-in d1",
        ),
        Div(
            Button(
                icon("chart", 17), "Hitung Statistik Dasar",
                cls="btn btn-primary btn-lg",
                hx_post=f"/stats/{sid}", hx_target="#stats-area", hx_swap="innerHTML",
                hx_indicator="#stats-loading",
            ),
            P("13 metrik statistik akan dihitung untuk setiap kolom numerik", cls="compute-note"),
            cls="compute-row anim-in d2",
        ),
        Div(
            Div(Span(cls="spinner"), "Menghitung statistik...", id="stats-loading", cls="spinner-wrap htmx-indicator"),
            id="stats-area",
        ),
        cls="ws-root",
    )


def stats_table(stats):
    cols = list(stats.columns)
    head = Tr(Th("Kolom", cls="sticky-col"), *[Th(str(c), cls="num-th") for c in cols])
    rows = []
    for col, r in stats.iterrows():
        tds = [Td(str(col), cls="sticky-col col-name")]
        for c in cols:
            tds.append(Td(fmt_stat(r[c]), cls="num-td"))
        rows.append(Tr(*tds))
    return Table(Thead(head), Tbody(*rows), cls="data-table stats-table")


def narasi_card_dasar(paras, judul="Narasi Analisis",
                      sub="Interpretasi otomatis dari data Anda - siap disalin ke laporan."):
    """Kartu narasi analisis otomatis untuk halaman Statistik Dasar."""
    if not paras:
        return None
    return Div(
        Div(
            Div(icon("chat", 17), cls="narasi-ic"),
            Div(
                Div(judul, cls="narasi-title"),
                Div(sub, cls="narasi-sub"),
            ),
            Button(icon("list", 13), "Salin Narasi", type="button",
                   cls="narasi-copy", data_copy_narasi="1"),
            cls="narasi-head",
        ),
        Div(*[P(p, cls="narasi-p") for p in paras], cls="narasi-body"),
        cls="narasi-card anim-in",
    )


def detail_fragment_inner(df, col):
    s_all = df[col]
    kolom = s_all.dropna()
    if len(kolom) == 0:
        return [
            Div(
                icon("info", 18),
                P("Kolom ini tidak memiliki nilai numerik yang valid.", style="margin:0"),
                cls="err-body",
            )
        ]

    metric_defs = [
        ("Mean", kolom.mean(), "sigma"),
        ("Median", kolom.median(), "align"),
        ("Std Deviasi", kolom.std(), "activity"),
        ("Variansi", kolom.var(), "percent"),
        ("Minimum", kolom.min(), "down"),
        ("Maksimum", kolom.max(), "up"),
        ("Jumlah Data", float(kolom.count()), "list"),
        ("Data Kosong", float(s_all.isna().sum()), "trash"),
    ]
    cards = [
        Div(
            Div(icon(ic, 15), cls="metric-ic"),
            Span(lbl, cls="metric-label"),
            Div(fmt_stat(v), cls="metric-val"),
            cls="metric-card",
        )
        for lbl, v, ic in metric_defs
    ]

    chips = []
    skew_v = kolom.skew()
    if not pd.isna(skew_v):
        if abs(skew_v) < 0.5:
            chips.append(("Distribusi relatif simetris", "chip-cyan"))
        elif skew_v >= 0.5:
            chips.append((f"Condong kanan (skewness +{fmt_stat(skew_v)})", "chip-pink"))
        else:
            chips.append((f"Condong kiri (skewness {fmt_stat(skew_v)})", "chip-pink"))
    kurt_v = kolom.kurtosis()
    if not pd.isna(kurt_v):
        if kurt_v > 0.5:
            chips.append(("Leptokurtik - puncak lebih tajam dari normal", "chip-pink"))
        elif kurt_v < -0.5:
            chips.append(("Platykurtik - puncak lebih datar dari normal", "chip-cyan"))
        else:
            chips.append(("Mesokurtik - mendekati distribusi normal", "chip-cyan"))

    hist, bins = np.histogram(kolom, bins=20)
    cfg = {
        "labels": [f"{bf(bins[i])} - {bf(bins[i + 1])}" for i in range(len(hist))],
        "data": [int(v) for v in hist],
        "col": str(col),
    }
    cfg_json = json.dumps(cfg).replace("</", "<\\/")

    parts = [Div(*cards, cls="metrics-grid anim-in")]
    if chips:
        parts.append(Div(*[Span(t, cls=f"chip {c}") for t, c in chips], cls="chip-row"))
    parts.append(
        Div(
            Div(
                icon("activity", 17),
                H3(f"Distribusi Data: {col}"),
                Span(f"{len(kolom):,} data", cls="chip"),
                cls="sec-head",
            ),
            Div(Canvas(id="hist-canvas"), cls="chart-box"),
            NotStr(f"<script>window.drawHist('hist-canvas', {cfg_json});</script>"),
            cls="chart-card anim-in d1",
        )
    )
    nar = narasi_card_dasar(
        narasi_dasar_kolom(col, s_all, kolom),
        "Narasi Analisis",
        f"Interpretasi otomatis untuk kolom {col} - siap disalin ke laporan.",
    )
    if nar is not None:
        parts.append(nar)
    return parts


def detail_section(sid, df, numeric_cols):
    first = str(numeric_cols[0])
    select = Select(
        *[Option(str(c), value=str(c), selected=(str(c) == first)) for c in numeric_cols],
        name="col",
        cls="col-select",
        hx_get=f"/detail/{sid}", hx_trigger="change", hx_target="#detail-panel",
        hx_swap="innerHTML", hx_indicator="#detail-loading",
    )
    return Section(
        Div(Div(icon("sliders", 17), H3("Detail per Kolom"), cls="sec-head-left"), cls="sec-head"),
        Div(
            Div(Label("Pilih kolom numerik", cls="select-label"), select, cls="select-group"),
            Div(Span(cls="spinner spinner-sm"), "Memuat...", id="detail-loading", cls="spinner-inline htmx-indicator"),
            cls="select-row",
        ),
        Div(*detail_fragment_inner(df, numeric_cols[0]), id="detail-panel"),
        cls="card anim-in d1",
    )


def categorical_section(df, object_cols):
    kat = df[object_cols].describe().T.rename(columns={
        "count": "Jumlah Data", "unique": "Jumlah Unik",
        "top": "Nilai Terbanyak", "freq": "Frekuensi",
    })
    head = Tr(Th("Kolom", cls="sticky-col"), *[Th(str(c)) for c in kat.columns])
    rows = []
    for col, r in kat.iterrows():
        tds = [Td(str(col), cls="sticky-col col-name")]
        for c in kat.columns:
            v = r[c]
            if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
                tds.append(Td(fmt_stat(v), cls="num-td"))
            else:
                s = str(v)
                tds.append(Td(s, title=s))
        rows.append(Tr(*tds))
    anak = [
        Div(icon("tag", 17), H3("Statistik Kolom Kategorik"), cls="sec-head"),
        Div(Table(Thead(head), Tbody(*rows), cls="data-table"), cls="table-wrap"),
    ]
    nar = narasi_dasar_kategorik(df, object_cols)
    if nar:
        anak.append(Div(
            Div(icon("chat", 15), B("Narasi Ringkas"), cls="narasi-inline-head"),
            Div(*[P(p, cls="narasi-p") for p in nar], cls="narasi-body"),
            cls="narasi-inline",
        ))
    return Section(*anak, cls="card anim-in")


def stats_fragment(sid, df):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    object_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    parts = []

    if not numeric_cols:
        parts.append(
            Div(
                Div(icon("alert", 20), cls="warn-ic"),
                Div(
                    B("Tidak Ditemukan Kolom Numerik"),
                    P("Statistik dasar hanya dapat dihitung untuk kolom numerik. "
                      "Pastikan file Anda memuat kolom berisi angka."),
                    cls="err-body",
                ),
                cls="card warn-card anim-in",
            )
        )
    else:
        stats = hitung_statistik(df)
        chips = [
            Span(f"{len(numeric_cols)} kolom numerik", cls="chip"),
            Span(f"{len(object_cols)} kolom kategorik", cls="chip chip-cyan"),
            Span("13 metrik", cls="chip chip-pink"),
        ]
        parts.append(
            Section(
                Div(
                    Div(icon("chart", 17), H3("Ringkasan Semua Kolom Numerik"), cls="sec-head-left"),
                    A(
                        icon("download", 15), "Unduh Statistik (CSV)",
                        href=f"/download/{sid}", cls="btn btn-success btn-sm",
                        download="statistik_dasar.csv",
                    ),
                    cls="sec-head sec-head-split",
                ),
                Div(*chips, cls="chip-row"),
                Div(stats_table(stats), cls="table-wrap"),
                cls="card anim-in",
            )
        )
        nar = narasi_card_dasar(
            narasi_dasar_ringkasan(df, numeric_cols),
            "Narasi Ringkasan",
            "Interpretasi otomatis atas tabel ringkasan semua kolom numerik.",
        )
        if nar is not None:
            parts.append(nar)
        parts.append(detail_section(sid, df, numeric_cols))

    if object_cols:
        parts.append(categorical_section(df, object_cols))

    return Div(*parts, cls="stats-root")


def session_gone():
    return Div(
        Div(icon("alert", 20), cls="warn-ic"),
        Div(
            B("Sesi Tidak Ditemukan"),
            P("Data sesi telah kedaluwarsa atau server baru saja dimulai ulang. "
              "Silakan unggah ulang file Anda melalui panel di atas."),
            cls="err-body",
        ),
        cls="card warn-card anim-in",
    )


# ==========================================
# ROUTES
# ==========================================
try:
    app, rt = fast_app(pico=False, hdrs=(
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Meta(name="description", content=(
            "Aplikasi pengolah statistik dasar: unggah data CSV, Excel, DBF, JSON, TXT, TSV, "
            "atau Parquet dan dapatkan ringkasan statistik lengkap secara instan."
        )),
        Link(rel="icon", type="image/svg+xml", href=FAVICON),
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin="anonymous"),
        Link(rel="stylesheet", href=FONTS_URL),
        Link(rel="stylesheet", href="/app.css?v=20261030a"),
        Script(src=CHARTJS_SRC),
        Script(src="/js/chart.js"),
    ))
except TypeError:
    # Fallback untuk versi fasthtml tanpa parameter pico
    app, rt = fast_app(default_hdrs=False, hdrs=(
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Link(rel="icon", type="image/svg+xml", href=FAVICON),
        Link(rel="stylesheet", href=FONTS_URL),
        Link(rel="stylesheet", href="/app.css?v=20261030a"),
        Script(src="https://unpkg.com/htmx.org@2.0.4"),
        Script(src=CHARTJS_SRC),
        Script(src="/js/chart.js"),
    ))


@rt("/")
def get():
    return (
        Title("AseliPedas - Pengolah Statistik Dasar"),
        top_nav(),
        Main(
            hero_section(),
            Div(
                Form(
                    upload_section(),
                    id="upload-form",
                    hx_post="/upload", hx_target="#workspace", hx_swap="innerHTML",
                    hx_encoding="multipart/form-data",
                ),
                Div(empty_state(), id="workspace"),
                cls="wrap",
            ),
            Footer(P("Aplikasi Edukasi dan Literasi Pengolahan Data Statistik - 2026 - fhy3273@gmail.com", cls="foot-txt"), cls="foot"),
            Script(src="/js/main.js"),
        ),
    )


@rt("/upload")
async def post(req: Request):
    try:
        form = await req.form()
        up = form.get("file")
        fname = getattr(up, "filename", "") or ""
        if not fname:
            return upload_error_fragment("Tidak ada file yang dipilih. Silakan pilih file terlebih dahulu.")
        data = await up.read()
        ext = os.path.splitext(fname)[1].lower().lstrip(".")
        if ext not in FORMATS:
            return upload_error_fragment(
                f"Format .{ext or '(tanpa ekstensi)'} belum didukung. "
                f"Gunakan: {', '.join(f.upper() for f in FORMATS)}."
            )
        df = load_data(data, fname)
        if df.shape[0] == 0:
            return upload_error_fragment("File berhasil dibaca tetapi tidak berisi satu baris data pun.")
        sid = uuid.uuid4().hex[:10]
        SESSIONS[sid] = {"df": df, "name": fname}
        _prune_sessions()
        return uploaded_fragment(sid, df, fname, len(data))
    except Exception as e:
        return upload_error_fragment(f"Gagal membaca file: {e}")


@rt("/stats/{sid}")
def post(sid: str):
    s = SESSIONS.get(sid)
    if not s:
        return session_gone()
    try:
        return stats_fragment(sid, s["df"])
    except Exception as e:
        return upload_error_fragment(f"Terjadi kesalahan saat menghitung statistik: {e}")


@rt("/detail/{sid}")
def get(sid: str, col: str = ""):
    s = SESSIONS.get(sid)
    if not s:
        return session_gone()
    df = s["df"]
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return Div(P("Tidak ada kolom numerik dalam data.", cls="table-note"))
    if col not in [str(c) for c in numeric_cols]:
        col = str(numeric_cols[0])
    return Div(*detail_fragment_inner(df, col))


@rt("/download/{sid}")
def get(sid: str):
    s = SESSIONS.get(sid)
    if not s:
        return Response("Sesi tidak ditemukan. Silakan unggah ulang file.",
                        status_code=404, media_type="text/plain")
    stats = hitung_statistik(s["df"])
    if stats is None:
        return Response("Tidak ada kolom numerik untuk diunduh.",
                        status_code=400, media_type="text/plain")
    csv_bytes = stats.to_csv(index_label="Kolom").encode("utf-8")
    return Response(
        csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="statistik_dasar.csv"'},
    )


@rt("/reset")
def post():
    return empty_state()


@rt("/app.css")
def get():
    with open(os.path.join(BASE_DIR, "app.css"), "rb") as f:
        return Response(f.read(), media_type="text/css; charset=utf-8",
                        headers={"Cache-Control": "no-cache"})


@rt("/js/{fname}")
def get(fname: str):
    safe = os.path.basename(fname)
    path = os.path.join(BASE_DIR, "js", safe)
    if not os.path.exists(path):
        return Response("// not found", status_code=404, media_type="application/javascript")
    with open(path, "rb") as f:
        return Response(f.read(), media_type="application/javascript; charset=utf-8",
                        headers={"Cache-Control": "no-cache"})


@rt("/vendor/chart.umd.min.js")
def get():
    if not os.path.exists(CHARTJS_LOCAL):
        return Response("// chart.js vendor tidak ditemukan",
                        status_code=404, media_type="application/javascript")
    with open(CHARTJS_LOCAL, "rb") as f:
        return Response(f.read(), media_type="application/javascript",
                        headers={"Cache-Control": "public, max-age=86400"})


# ==========================================
# REGISTRASI HALAMAN STATISTIK INFERENSIAL
# ==========================================
import inferens as _inferens


def _shared_footer():
    return Footer(P("Aplikasi Edukasi dan Literasi Pengolahan Data Statistik - 2026 - fhy3273@gmail.com", cls="foot-txt"), cls="foot")


_inferens.register_shared(top_nav, _shared_footer)
_inferens.setup(rt)


# ==========================================
# REGISTRASI HALAMAN TEORI UJI STATISTIK
# ==========================================
import teori as _teori

_teori.register_shared(top_nav, _shared_footer)
_teori.setup(rt)


# ==========================================
# REGISTRASI HALAMAN STATISTIK NON-PARAMETRIK
# ==========================================
import nonparam as _nonparam

_nonparam.register_shared(top_nav, _shared_footer)
_nonparam.setup(rt)


# ==========================================
# REGISTRASI HALAMAN PERBANDINGAN FILE DATA
# ==========================================
import komparasi as _komparasi

_komparasi.register_shared(top_nav, _shared_footer)
_komparasi.setup(rt)


if __name__ == "__main__":
    import socket
    import threading
    import webbrowser
    import uvicorn

    def _port_bebas(mulai):
        """Bila port utama terpakai, geser hingga menemukan port kosong."""
        p = mulai
        while p < mulai + 20:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("0.0.0.0", p))
                    return p
                except OSError:
                    p += 1
        return mulai

    port = _port_bebas(int(os.environ.get("PORT", 3000)))
    url = f"http://localhost:{port}"
    threading.Timer(2.5, lambda: webbrowser.open(url)).start()

    print("=" * 64)
    print("  AseliPedas - Aplikasi Pengolah Statistik (FastHTML)")
    print(f"  Buka di browser : {url}")
    print("  Jika browser tidak terbuka otomatis, ketik alamat di atas manual.")
    print("  Untuk berhenti : tekan Ctrl+C di jendela ini, lalu tutup jendela.")
    print("=" * 64)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
