# -*- coding: utf-8 -*-
"""
AseliPedas - Halaman Statistik Inferensial (FastHTML Edition)
===========================================================
Konversi dari aplikasi Streamlit "Statistik_Inferens" dengan fungsi yang sama:
20 analisis inferensial - regresi (OLS, logistik biner/multinomial, ordinal,
Poisson), ANOVA 1 & 2 arah, ANCOVA, MANOVA, uji t, chi-square, korelasi,
analisis faktor, PCA, diskriminan, K-Means, Kruskal-Wallis, Mann-Whitney,
Wilcoxon, Friedman.

Modul ini di-register dari app.py lewat inferens.setup(rt).
"""
import io
import os
import uuid
import base64
import itertools
import tempfile

import numpy as np
import pandas as pd
from scipy import stats

import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson, jarque_bera
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.weightstats import ttest_ind as sm_ttest
from statsmodels.multivariate.manova import MANOVA
from statsmodels.miscmodels.ordinal_model import OrderedModel

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import cross_val_score
from sklearn.metrics import confusion_matrix, accuracy_score, silhouette_score

try:
    from factor_analyzer import FactorAnalyzer
    from factor_analyzer.factor_analyzer import calculate_kmo, calculate_bartlett_sphericity
    FA_OK = True
except ImportError:
    FA_OK = False

try:
    import pyreadstat
    SAV_OK = True
except ImportError:
    SAV_OK = False

try:
    from dbfread import DBF
    DBF_OK = True
except ImportError:
    DBF_OK = False

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.colors import LinearSegmentedColormap

from fasthtml.common import (
    Div, Section, H1, H2, H3, P, Span, B, Button, Input, Select, Option, Label,
    Table, Thead, Tbody, Tr, Th, Td, Pre, Img, Form, A, Output, NotStr,
    Title, Script, Main,
)
from starlette.requests import Request
from starlette.responses import Response

from narasi import buat_narasi

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INF_FORMATS = ["csv", "xls", "xlsx", "xlsm", "sav", "dta", "dbf", "json",
               "txt", "tsv", "dat", "parquet", "pkl"]
INF_ACCEPT = ",".join(f".{e}" for e in INF_FORMATS)
INF_SESSIONS = {}
MAX_INF_SESSIONS = 6

# ==========================================================
# TEMA GRAFIK MATPLOTLIB (selaras tema gelap aplikasi)
# ==========================================================
BG = "#0B1322"
FG = "#C9D2E3"
TITLE_C = "#E7EBF4"
MUT = "#8B97AD"
GRID_C = (1, 1, 1, 0.09)
EDGE = "#2A3752"
PAL = ["#7C5CFC", "#22D3EE", "#F472B6", "#34D399", "#FBBF24",
       "#A78BFA", "#2DD4BF", "#FB7185", "#4F7BFF", "#F97316"]

plt.rcParams.update({
    "figure.dpi": 108, "font.size": 9.5, "font.family": "DejaVu Sans",
    "text.color": FG, "axes.edgecolor": EDGE, "axes.labelcolor": FG,
    "axes.titlecolor": TITLE_C, "axes.titleweight": "bold", "axes.titlesize": 10.5,
    "xtick.color": MUT, "ytick.color": MUT,
    "axes.facecolor": BG, "figure.facecolor": BG, "savefig.facecolor": BG,
    "axes.grid": True, "grid.color": GRID_C, "grid.linewidth": .7, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.facecolor": "#0E1626", "legend.edgecolor": EDGE, "legend.labelcolor": FG,
})


def fig_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return buf.getvalue()


def img_tag(png, alt, judul):
    b64 = base64.b64encode(png).decode("ascii")
    return Img(src=f"data:image/png;base64,{b64}", alt=alt, cls="chart-img", loading="lazy")


def legend_style(ax):
    lg = ax.legend(frameon=True)
    if lg:
        lg.get_frame().set_alpha(.96)
    return lg


# ==========================================================
# FORMAT ANGKA & HELPER DATA
# ==========================================================
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
    if xf == int(xf) and abs(xf) < 1e9:
        return f"{int(xf):,}"
    if abs(xf) >= 100:
        return f"{xf:,.1f}"
    if abs(xf) >= 1:
        s = f"{xf:,.4f}"
    else:
        s = f"{xf:.4f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def fmt_p(p):
    try:
        if p is None or pd.isna(p):
            return "-"
        pf = float(p)
    except (TypeError, ValueError):
        return str(p)
    if pf < 1e-4:
        return "< 0.0001"
    return f"{pf:.4f}"


def size_str(n):
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.2f} MB"


def persiapkan(df, cols):
    """Ambil kolom terpilih, buang baris kosong, samakan kategori ke string."""
    sub = df[cols].dropna().copy()
    for c in sub.columns:
        if not pd.api.types.is_numeric_dtype(sub[c]):
            sub[c] = sub[c].astype(str).str.strip()
    return sub


def konversi_numerik(df):
    """Coba ubah kolom teks menjadi numerik bila mayoritas isinya angka."""
    df = df.copy()
    for c in df.columns:
        if df[c].dtype == object:
            bersih = df[c].astype(str).str.replace(",", "", regex=False).str.strip()
            num = pd.to_numeric(bersih, errors="coerce")
            if num.notna().mean() > 0.6:
                df[c] = num
    return df


def num_cols(df):
    return df.select_dtypes("number").columns.tolist()


def cat_cols(df):
    return df.select_dtypes(exclude="number").columns.tolist()


def _aslist(v):
    """Pastikan parameter multi-pilih selalu berupa list (bisa satu nilai)."""
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return list(v)
    return [v]


# ==========================================================
# WADAH HASIL ANALISIS
# ==========================================================
class Hasil:
    def __init__(self):
        self.metrics = []    # (label, nilai_str, ikon)
        self.tests = []      # (label, stat_float, p_float)
        self.tables = []     # (judul, df, note)
        self.summaries = []  # (judul, teks)
        self.charts = []     # (judul, png_bytes)
        self.warnings = []   # str
        self.notes = []      # str
        self.downloads = []  # (label, filename, csv_bytes)

    def metric(self, label, val, ic="sigma"):
        self.metrics.append((label, str(val), ic))

    def uji(self, label, stat, p, alpha):
        self.tests.append((label, stat, p, float(alpha)))

    def tabel(self, judul, df, note=""):
        self.tables.append((judul, df, note))

    def ringkasan(self, judul, teks):
        self.summaries.append((judul, teks))

    def grafik(self, judul, fig):
        self.charts.append((judul, fig_png(fig)))

    def unduh(self, label, fname, df):
        self.downloads.append((label, fname, df.to_csv(index=False).encode("utf-8")))


def hasil_error(msg):
    """Kartu error untuk kegagalan validasi/eksekusi analisis."""
    return Div(
        Div(ICON_SVG("alert", 20), cls="err-ic"),
        Div(B("Analisis Gagal Dijalankan"), P(str(msg)), cls="err-body"),
        cls="card error-card anim-in",
    )


def inf_error_fragment(msg, kind="error"):
    return Div(
        Div(ICON_SVG("alert", 20), cls="err-ic"),
        Div(B("Gagal Memproses" if kind == "error" else "Perhatian"), P(msg),
            cls="err-body"),
        cls=f"card {'error-card' if kind == 'error' else 'warn-card'} anim-in",
    )


# ==========================================================
# IKON SVG (gaya Lucide, tanpa emoji)
# ==========================================================
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
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "layers": '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    "trendup": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "trenddown": '<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "shuffle": '<path d="M2 18h1.4c1.3 0 2.5-.6 3.3-1.7l6.1-8.6c.8-1.1 2-1.7 3.3-1.7H22"/><path d="m18 2 4 4-4 4"/><path d="M2 6h1.9c1.5 0 2.9.9 3.6 2.2"/><path d="M22 18h-5.9c-1.3 0-2.6-.7-3.3-1.8l-.5-.8"/><path d="m18 14 4 4-4 4"/>',
    "list": '<line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/>',
    "listordered": '<line x1="10" x2="21" y1="6" y2="6"/><line x1="10" x2="21" y1="12" y2="12"/><line x1="10" x2="21" y1="18" y2="18"/><path d="M4 6h1v4"/><path d="M4 10h2"/><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/>',
    "hash": '<line x1="4" x2="20" y1="9" y2="9"/><line x1="4" x2="20" y1="15" y2="15"/><line x1="10" x2="8" y1="3" y2="21"/><line x1="16" x2="14" y1="3" y2="21"/>',
    "flask": '<path d="M10 2v7.527a2 2 0 0 1-.211.896L4.72 20.55a1 1 0 0 0 .9 1.45h12.76a1 1 0 0 0 .9-1.45l-5.069-10.127A2 2 0 0 1 14 9.527V2"/><path d="M8.5 2h7"/><path d="M7 16h10"/>',
    "scale": '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
    "grid": '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M9 3v18"/><path d="M15 3v18"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "component": '<path d="M5.5 8.5 9 12l-3.5 3.5L2 12l3.5-3.5Z"/><path d="m12 2 3.5 3.5L12 9 8.5 5.5 12 2Z"/><path d="M18.5 8.5 22 12l-3.5 3.5L15 12l3.5-3.5Z"/><path d="m12 15 3.5 3.5L12 22l-3.5-3.5L12 15Z"/>',
    "compass": '<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>',
    "crosshair": '<circle cx="12" cy="12" r="10"/><line x1="22" x2="18" y1="12" y2="12"/><line x1="6" x2="2" y1="12" y2="12"/><line x1="12" x2="12" y1="6" y2="2"/><line x1="12" x2="12" y1="22" y2="18"/>',
    "share2": '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"/><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"/>',
    "leftright": '<path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/><path d="M4 17h16"/>',
    "ruler": '<path d="M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.3 8.7a2.41 2.41 0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0Z"/><path d="m14.5 12.5 2-2"/><path d="m11.5 9.5 2-2"/><path d="m8.5 6.5 2-2"/><path d="m17.5 15.5 2-2"/>',
    "boxes": '<path d="M2.97 12.92A2 2 0 0 0 2 14.63v3.24a2 2 0 0 0 .97 1.71l3 1.8a2 2 0 0 0 2.06 0L12 19v-5.5l-5-3-4.03 2.42Z"/><path d="m7 16.5-4.74-2.85"/><path d="m7 16.5 5-3"/><path d="M7 16.5v5.17"/><path d="M12 13.5V19l3.97 2.38a2 2 0 0 0 2.06 0l3-1.8a2 2 0 0 0 .97-1.71v-3.24a2 2 0 0 0-.97-1.71L17 10.5l-5 3Z"/><path d="m17 16.5-5-3"/><path d="m17 16.5 4.74-2.85"/><path d="M17 16.5v5.17"/><path d="M7.97 4.42A2 2 0 0 0 7 6.13v4.37l5 3 5-3V6.13a2 2 0 0 0-.97-1.71l-3-1.8a2 2 0 0 0-2.06 0l-3 1.8Z"/><path d="M12 8 7.26 5.15"/><path d="m12 8 4.74-2.85"/><path d="M12 13.5V8"/>',
    "percent": '<line x1="19" x2="5" y1="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    "up": '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
    "down": '<path d="m19 12-7 7-7-7"/><path d="M12 5v14"/>',
    "sparkles": '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>',
    "chat": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 9h8"/><path d="M8 12h5"/>',
    "book": '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>',
}


def ICON_SVG(name, size=18):
    inner = ICONS[name]
    return NotStr(
        f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{inner}</svg>'
    )


# ==========================================================
# TABEL DATAFRAME -> HTML
# ==========================================================
def df_table(df, index=True, min_w=None, idx_fmt=str):
    cols = [str(c) for c in df.columns]
    head_cells = []
    if index:
        head_cells.append(Th("" if df.index.name is None else str(df.index.name), cls="sticky-col"))
    for c in cols:
        head_cells.append(Th(c, cls="num-th"))
    rows = []
    for idx, r in df.iterrows():
        tds = []
        if index:
            iv = idx_fmt(idx) if not isinstance(idx, tuple) else " · ".join(str(x) for x in idx)
            tds.append(Td(iv, cls="sticky-col col-name"))
        for c in df.columns:
            v = r[c]
            try:
                is_nan = bool(pd.isna(v))
            except (TypeError, ValueError):
                is_nan = False
            if is_nan:
                tds.append(Td("-", cls="num-td na-td"))
            elif isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
                tds.append(Td(fmt_stat(v), cls="num-td"))
            else:
                s = str(v)
                tds.append(Td(s, title=s))
        rows.append(Tr(*tds))
    tbl = Table(Thead(Tr(*head_cells)), Tbody(*rows), cls="data-table inf-table")
    if min_w:
        tbl.attrs["style"] = f"min-width:{min_w}px"
    return tbl


# ==========================================================
# KOMPONEN FORM PARAMETER
# ==========================================================
def f_field(label, control, hint="", wide=False):
    parts = [Label(label, cls="f-label"), control]
    if hint:
        parts.append(P(hint, cls="f-hint"))
    return Div(*parts, cls="field" + (" field-wide" if wide else ""))


def f_select(name, label, options, cur=None, default=None, hint=""):
    opts = [str(o) for o in options]
    cur_v = (cur or {}).get(name)
    picked = cur_v[0] if isinstance(cur_v, list) and cur_v else cur_v
    sel = str(picked) if picked is not None and str(picked) in opts else str(
        default if default is not None and str(default) in opts else opts[0])
    ctrl = Select(
        *[Option(o, value=o, selected=(o == sel)) for o in opts],
        name=name, cls="inp inp-select",
    )
    return f_field(label, ctrl, hint)


def f_multi(name, label, options, cur=None, defaults=None, hint=""):
    opts = [str(o) for o in options]
    cur_v = (cur or {}).get(name)
    if isinstance(cur_v, list) and cur_v:
        sel = {str(v) for v in cur_v}
    else:
        sel = {str(d) for d in (defaults if defaults is not None else [])}
    chips = [
        Label(
            Input(type="checkbox", name=name, value=o, checked=(o in sel), cls="mchip-in"),
            Span(o), cls="mchip",
        ) for o in opts
    ]
    return f_field(label, Div(*chips, cls="mchip-row"), hint, wide=True)


def f_seg(name, label, options, cur=None, default=None, hint="", trigger_url=None, target=None):
    """Segmented control berbasis radio. options = [(nilai, teks)]."""
    cur_v = (cur or {}).get(name)
    picked = str(cur_v[0]) if isinstance(cur_v, list) and cur_v else (
        str(cur_v) if cur_v is not None else str(default))
    opts = []
    for val, txt in options:
        attrs = dict(type="radio", name=name, value=str(val),
                     checked=(str(val) == picked), cls="seg-in")
        if trigger_url:
            attrs.update(hx_get=trigger_url, hx_trigger="change",
                         hx_target=target or "#inf-params", hx_swap="innerHTML",
                         hx_include="closest form")
        opts.append(Label(Input(**attrs), Span(txt), cls="seg-opt"))
    return f_field(label, Div(*opts, cls="seg"), hint)


def f_toggle(name, label, cur=None, checked=False, hint=""):
    cur_v = (cur or {}).get(name)
    on = (str(cur_v[0]) in ("on", "1", "True")) if isinstance(cur_v, list) and cur_v else (
        checked if cur_v is None else str(cur_v) in ("on", "1", "True"))
    ctrl = Label(
        Input(type="checkbox", name=name, checked=on, cls="tgl-in"),
        Span(cls="tgl-track"), Span(label, cls="tgl-txt"),
        cls="toggle",
    )
    return f_field(label, ctrl, hint)


def f_num(name, label, cur=None, default=0, step="any", mn=None, mx=None, hint=""):
    cur_v = (cur or {}).get(name)
    val = cur_v[0] if isinstance(cur_v, list) and cur_v else (cur_v if cur_v is not None else default)
    attrs = dict(type="number", name=name, value=str(val), step=step, cls="inp inp-num")
    if mn is not None:
        attrs["min"] = mn
    if mx is not None:
        attrs["max"] = mx
    return f_field(label, Input(**attrs), hint)


def f_range(name, label, cur=None, lo=0, hi=10, default=3, hint=""):
    cur_v = (cur or {}).get(name)
    val = cur_v[0] if isinstance(cur_v, list) and cur_v else (cur_v if cur_v is not None else default)
    try:
        val = int(float(val))
    except (TypeError, ValueError):
        val = default
    val = max(int(lo), min(int(hi), val))
    ctrl = Div(
        Input(type="range", name=name, min=lo, max=hi, value=val, cls="rng",
              oninput="this.nextElementSibling.value=this.value"),
        Output(val, cls="rng-out"),
        cls="range-row",
    )
    return f_field(label, ctrl, hint)


def f_text(name, label, cur=None, default="", hint="", placeholder=""):
    cur_v = (cur or {}).get(name)
    val = cur_v[0] if isinstance(cur_v, list) and cur_v else (cur_v if cur_v is not None else default)
    return f_field(label, Input(type="text", name=name, value=str(val),
                                placeholder=placeholder, cls="inp inp-text"), hint)


# ==========================================================
# 1) REGRESI LINEAR (OLS)
# ==========================================================
def _ols_form(df, cur):
    nums = num_cols(df)
    y = cur.get("y", [None])
    y_sel = y[0] if y and y[0] in nums else (nums[0] if nums else "")
    xs_def = [c for c in nums if c != y_sel][:3]
    return [
        f_select("y", "Variabel Dependen / Y (numerik)", nums, cur, default=y_sel),
        f_multi("xs", "Variabel Independen / X (numerik)", [c for c in nums if c != y_sel],
                cur, xs_def, "Pilih satu atau lebih variabel bebas."),
    ]


def _ols_run(df, p, alpha):
    y, xs = p["y"], _aslist(p["xs"])
    if not xs:
        raise ValueError("Pilih minimal satu variabel X.")
    data = persiapkan(df, [y] + xs)
    X = sm.add_constant(data[xs])
    model = sm.OLS(data[y], X).fit()

    h = Hasil()
    h.metric("R²", f"{model.rsquared:.4f}", "trendup")
    h.metric("Adj. R²", f"{model.rsquared_adj:.4f}", "chart")
    h.metric("p-value F-statistik", f"{model.f_pvalue:.4g}", "percent")
    h.metric("n Observasi", f"{len(data):,}", "database")
    h.ringkasan("Ringkasan Model", model.summary().as_text())

    coef = pd.DataFrame({
        "Koefisien": model.params, "Std.Err": model.bse, "t": model.tvalues,
        "p-value": model.pvalues, "IC 2.5%": model.conf_int()[0],
        "IC 97.5%": model.conf_int()[1],
    }).round(4)
    h.tabel("Tabel Koefisien", coef, "Nilai t dan p-value menunjukkan signifikansi tiap prediktor.")

    if len(xs) >= 2:
        vif = pd.DataFrame({"Variabel": xs,
                            "VIF": [variance_inflation_factor(X.values, i)
                                    for i in range(1, X.shape[1])]}).set_index("Variabel")
        h.tabel("Uji Multikolinearitas (VIF)", vif.round(3),
                "VIF > 10 mengindikasikan multikolinearitas serius.")

    resid, fitted = model.resid, model.fittedvalues
    dw = durbin_watson(resid)
    bp_lm, bp_p, _, _ = het_breuschpagan(resid, X)
    jb, jb_p, _, _ = jarque_bera(resid)
    h.tabel("Uji Asumsi Klasik", pd.DataFrame({
        "Uji": ["Durbin-Watson (autokorelasi)", "Breusch-Pagan (heteroskedastisitas)",
                "Jarque-Bera (normalitas residual)"],
        "Statistik": [dw, bp_lm, jb],
        "p-value": [np.nan, bp_p, jb_p],
        "Kriteria": ["≈ 2 → bebas autokorelasi", "p > α → residual homogen",
                     "p > α → residual normal"],
    }).set_index("Uji"))

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].scatter(fitted, resid, alpha=.7, s=22, color=PAL[0], edgecolor=BG, linewidth=.3)
    ax[0].axhline(0, color="#F472B6", ls="--", lw=1.3)
    ax[0].set(title="Residual vs Fitted", xlabel="Nilai Prediksi", ylabel="Residual")
    sm.qqplot(resid, line="45", fit=True, ax=ax[1])
    lns = ax[1].get_lines()
    if lns:
        lns[0].set(marker="o", markersize=4.5, markerfacecolor=PAL[1],
                   markeredgecolor=BG, markeredgewidth=.4, linestyle="none", alpha=.85)
        for ln in lns[1:]:
            ln.set(color="#F472B6", lw=1.4)
    ax[1].set_title("QQ-Plot Residual")
    fig.tight_layout()
    h.grafik("Diagnostik Residual", fig)
    return h


# ==========================================================
# 2) REGRESI LOGISTIK BINER
# ==========================================================
def _logit_form(df, cur):
    kandidat = [c for c in df.columns if df[c].nunique(dropna=True) == 2]
    nums = num_cols(df)
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in kandidat else (kandidat[0] if kandidat else "")
    xs_def = [c for c in nums if c != y_sel][:3]
    return [
        f_select("y", "Variabel Dependen (tepat 2 kategori)", kandidat, cur, default=y_sel),
        f_multi("xs", "Variabel Independen (numerik)", [c for c in nums if c != y_sel],
                cur, xs_def),
    ]


def _logit_run(df, p, alpha):
    ycol, xs = p["y"], _aslist(p["xs"])
    if not xs:
        raise ValueError("Pilih minimal satu variabel X.")
    data = persiapkan(df, [ycol] + xs)
    levels = sorted(data[ycol].unique(), key=str)
    y = (data[ycol] == levels[1]).astype(int)
    X = sm.add_constant(data[xs])
    model = sm.Logit(y, X).fit(disp=0)

    h = Hasil()
    h.ringkasan("Ringkasan Model", model.summary().as_text())
    h.notes.append(f"Encoding: {levels[0]} = 0, {levels[1]} = 1")

    odds = pd.DataFrame({"Odds Ratio": np.exp(model.params),
                         "IC 2.5%": np.exp(model.conf_int()[0]),
                         "IC 97.5%": np.exp(model.conf_int()[1]),
                         "p-value": model.pvalues}).round(4)
    h.tabel("Odds Ratio (e^β)", odds, "Odds ratio > 1 → X menaikkan peluang kategori 1.")

    pred = (model.predict(X) >= .5).astype(int)
    akur = accuracy_score(y, pred)
    h.metric("Akurasi Klasifikasi", f"{akur:.1%}", "target")
    cm = pd.DataFrame(confusion_matrix(y, pred),
                      index=[f"Aktual {l}" for l in levels],
                      columns=[f"Pred {l}" for l in levels])
    h.tabel("Matriks Konfusi", cm)
    return h


# ==========================================================
# 3) REGRESI LOGISTIK MULTINOMIAL
# ==========================================================
def _mnlogit_form(df, cur):
    nums = num_cols(df)
    cats = [c for c in df.columns if 2 <= df[c].nunique(dropna=True) <= 10]
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in cats else (cats[0] if cats else "")
    xs_def = [c for c in nums if c != y_sel][:3]
    return [
        f_select("y", "Variabel Dependen (kategori, 2–10 level)", cats, cur, default=y_sel),
        f_multi("xs", "Variabel Independen (numerik)", [c for c in nums if c != y_sel],
                cur, xs_def),
    ]


def _mnlogit_run(df, p, alpha):
    ycol, xs = p["y"], _aslist(p["xs"])
    if not xs:
        raise ValueError("Pilih minimal satu variabel X.")
    data = persiapkan(df, [ycol] + xs)
    ycodes, uniques = pd.factorize(data[ycol], sort=True)
    X = sm.add_constant(data[xs])
    model = sm.MNLogit(ycodes, X).fit(disp=0)

    h = Hasil()
    h.ringkasan("Ringkasan Model", model.summary().as_text())
    h.notes.append("Pemetaan kategori: " + ", ".join(f"{i} = {u}" for i, u in enumerate(uniques)))

    co = model.params
    n_lvl = len(uniques)
    if isinstance(co.columns, pd.MultiIndex):
        rrr_rows = {}
        for col in co.columns:
            out, ex = col
            rrr_rows.setdefault(ex, {})[f"\u2192 {uniques[int(out)]}"] = float(np.exp(co[col]))
        rrr = pd.DataFrame(rrr_rows).T
    else:
        rrr = np.exp(co).copy()
        ints = []
        for c in co.columns:
            try:
                ints.append(int(c))
            except (TypeError, ValueError):
                ints.append(None)
        if all(i is not None for i in ints) and ints and max(ints) == n_lvl - 2 and min(ints) == 0:
            rrr.columns = [f"\u2192 {uniques[i + 1]}" for i in ints]
        else:
            rrr.columns = [f"\u2192 {uniques[i]}" if (i is not None and 0 <= i < n_lvl)
                           else str(c) for i, c in zip(ints, co.columns)]
    h.tabel("Relative Risk Ratio (e^β) terhadap kategori dasar (0)", rrr.round(4),
            "RRR > 1 → X menaikkan peluang kategori tsb. dibanding kategori dasar.")
    return h


# ==========================================================
# 4) REGRESI ORDINAL
# ==========================================================
def _ordinal_form(df, cur):
    nums = num_cols(df)
    cats = [c for c in df.columns if 2 <= df[c].nunique(dropna=True) <= 8]
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in cats else (cats[0] if cats else "")
    level_default = sorted(df[y_sel].dropna().astype(str).unique()) if y_sel else []
    xs_def = [c for c in nums if c != y_sel][:3]
    return [
        f_select("y", "Variabel Dependen (ordinal)", cats, cur, default=y_sel),
        f_text("urutan", "Urutan level Y (terendah → tertinggi)", cur,
               ", ".join(level_default),
               "Pisahkan dengan koma; ubah urutan bila perlu, mis. Rendah, Sedang, Tinggi."),
        f_multi("xs", "Variabel Independen (numerik)", [c for c in nums if c != y_sel],
                cur, xs_def),
    ]


def _ordinal_run(df, p, alpha):
    ycol, xs = p["y"], _aslist(p["xs"])
    urutan = [s.strip() for s in str(p.get("urutan", "")).split(",") if s.strip()]
    if len(urutan) < 2:
        raise ValueError("Isi minimal 2 level Y pada kolom urutan.")
    if not xs:
        raise ValueError("Pilih minimal satu variabel X.")
    data = df[[ycol] + xs].dropna()
    data[ycol] = pd.Categorical(data[ycol].astype(str), categories=urutan, ordered=True)
    data = data.dropna(subset=[ycol])
    model = OrderedModel(data[ycol], data[xs], distr="logit")
    res = model.fit(method="bfgs", disp=0)

    h = Hasil()
    h.ringkasan("Ringkasan Model", res.summary().as_text())
    h.notes.append("e^β > 1 → X menaikkan peluang menuju kategori yang lebih tinggi.")
    try:
        pr, bs, pv_arr = res.params, res.bse, res.pvalues
        nama_par = [str(x) for x in res.model.exog_names]
        n_cut = len(np.atleast_1d(pr).ravel()) - len(nama_par)
        idx = nama_par + [f"Ambang {i + 1}" for i in range(max(0, n_cut))]
        co = pd.DataFrame({
            "Koefisien": np.atleast_1d(pr).ravel(),
            "Std.Err": np.atleast_1d(bs).ravel(),
            "p-value": np.atleast_1d(pv_arr).ravel(),
        }, index=idx[:len(np.atleast_1d(pr).ravel())])
        h.tabel("Koefisien & Ambang (Threshold)", co.round(4))
        h.metric("Pseudo R² (McFadden)", f"{res.prsquared:.4f}", "trendup")
        h.metric("n Observasi", f"{len(data):,}", "database")
    except Exception:
        pass
    return h


# ==========================================================
# 5) REGRESI POISSON
# ==========================================================
def _poisson_form(df, cur):
    nums = num_cols(df)
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in nums else (nums[0] if nums else "")
    xs_def = [c for c in nums if c != y_sel][:3]
    return [
        f_select("y", "Variabel Dependen (hitungan, ≥ 0)", nums, cur, default=y_sel),
        f_multi("xs", "Variabel Independen (numerik)", [c for c in nums if c != y_sel],
                cur, xs_def),
    ]


def _poisson_run(df, p, alpha):
    y, xs = p["y"], _aslist(p["xs"])
    if not xs:
        raise ValueError("Pilih minimal satu variabel X.")
    data = persiapkan(df, [y] + xs)
    if (data[y] < 0).any():
        raise ValueError("Regresi Poisson membutuhkan nilai Y ≥ 0.")
    X = sm.add_constant(data[xs])
    model = sm.GLM(data[y], X, family=sm.families.Poisson()).fit()

    h = Hasil()
    h.ringkasan("Ringkasan Model", model.summary().as_text())
    irr = pd.DataFrame({"IRR": np.exp(model.params), "p-value": model.pvalues}).round(4)
    h.tabel("IRR (Incidence Rate Ratio, e^β)", irr,
            "IRR > 1 → X menaikkan laju kejadian; IRR < 1 → menurunkan.")
    return h


# ==========================================================
# 6) ANOVA SATU ARAH
# ==========================================================
def _anova1_form(df, cur):
    nums, cats = num_cols(df), cat_cols(df)
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in nums else (nums[0] if nums else "")
    f_sel = (cur.get("f") or [None])[0]
    f_sel = f_sel if f_sel in cats else (cats[0] if cats else "")
    return [
        f_select("y", "Variabel Dependen (numerik)", nums, cur, default=y_sel),
        f_select("f", "Faktor (kategori)", cats, cur, default=f_sel),
    ]


def _anova1_run(df, p, alpha):
    y, f = p["y"], p["f"]
    data = persiapkan(df, [y, f])
    data.columns = ["Y", "G"]
    groups = [g["Y"].values for _, g in data.groupby("G")]

    h = Hasil()
    desc = data.groupby("G")["Y"].agg(["count", "mean", "median", "std", "min", "max"]).round(3)
    h.tabel("Statistik Deskriptif per Kelompok", desc)

    if 2 <= len(groups) <= 12:
        sh = [stats.shapiro(g)[1] if len(g) >= 3 else np.nan for g in groups]
        h.notes.append("p-value Shapiro-Wilk per kelompok (normalitas): " +
                       ", ".join(f"{pv:.3f}" if pd.notna(pv) else "-" for pv in sh))

    lev = stats.levene(*groups, center="median")
    h.uji("Uji Homogenitas Varians (Levene)", lev.statistic, lev.pvalue, alpha)

    model = smf.ols("Y ~ C(G)", data=data).fit()
    tbl = anova_lm(model, typ=2)
    tbl.index = ["Faktor (Antar Kelompok)", "Residual (Dalam Kelompok)"]
    h.tabel("Tabel ANOVA", tbl.round(4))

    F, pv = tbl["F"].iloc[0], tbl["PR(>F)"].iloc[0]
    eta = tbl["sum_sq"].iloc[0] / tbl["sum_sq"].sum()
    h.metric("Eta Squared (ukuran efek)", f"{eta:.3f}", "percent")
    h.uji("ANOVA F-Test", F, pv, alpha)

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    order = list(data.groupby("G", observed=True).groups.keys())
    vals = [data.loc[data.G == g, "Y"].values for g in order]
    bp = ax.boxplot(vals, patch_artist=True, tick_labels=[str(g) for g in order])
    for patch, c in zip(bp["boxes"], itertools.cycle(PAL)):
        patch.set_facecolor(c)
        patch.set_alpha(.8)
        patch.set_edgecolor(BG)
    for med in bp["medians"]:
        med.set(color="#fff", lw=1.6)
    for fl in bp["fliers"]:
        fl.set(marker="o", ms=4, mfc="#F472B6", mec="none", alpha=.85)
    ax.set(xlabel="Kelompok", ylabel=y, title=f"Boxplot {y} per Kelompok")
    fig.tight_layout()
    h.grafik("Boxplot per Kelompok", fig)

    if pv < alpha and len(groups) > 2:
        tukey = pairwise_tukeyhsd(data["Y"], data["G"])
        tb = tukey.summary()
        tk = pd.DataFrame(tb.data[1:], columns=tb.data[0])
        tk = tk.set_index(tk.columns[0])
        h.tabel("Post-Hoc: Tukey HSD", tk)
        try:
            res_plot = tukey.plot_simultaneous()
            figt = res_plot[0] if isinstance(res_plot, tuple) else res_plot
            figt.patch.set_facecolor(BG)
            for fax in figt.axes:
                fax.set_facecolor(BG)
                fax.tick_params(colors=MUT)
                for sp in fax.spines.values():
                    sp.set_color(EDGE)
            figt.tight_layout()
            h.grafik("Interval Kepercayaan Tukey HSD", figt)
        except Exception:
            pass
    return h


# ==========================================================
# 7) ANOVA DUA ARAH
# ==========================================================
def _anova2_form(df, cur):
    nums, cats = num_cols(df), cat_cols(df)
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in nums else (nums[0] if nums else "")
    a_sel = (cur.get("a") or [None])[0]
    a_sel = a_sel if a_sel in cats else (cats[0] if cats else "")
    b_opts = [c for c in cats if c != a_sel]
    b_sel = (cur.get("b") or [None])[0]
    b_sel = b_sel if b_sel in b_opts else (b_opts[0] if b_opts else "")
    return [
        f_select("y", "Variabel Dependen (numerik)", nums, cur, default=y_sel),
        f_select("a", "Faktor A", cats, cur, default=a_sel),
        f_select("b", "Faktor B", b_opts, cur, default=b_sel),
        f_toggle("interaksi", "Sertakan interaksi A × B", cur, checked=True),
    ]


def _anova2_run(df, p, alpha):
    y, a, b = p["y"], p["a"], p["b"]
    interaksi = p.get("interaksi", False)
    data = persiapkan(df, [y, a, b])
    data.columns = ["Y", "A", "B"]

    formula = "Y ~ C(A) * C(B)" if interaksi else "Y ~ C(A) + C(B)"
    tbl = anova_lm(smf.ols(formula, data).fit(), typ=2)

    h = Hasil()
    h.tabel("Tabel ANOVA", tbl.round(4))
    for idx, row in tbl.iterrows():
        if idx != "Residual" and pd.notna(row.get("F")):
            h.uji(str(idx), row["F"], row["PR(>F)"], alpha)

    means = data.groupby(["A", "B"], observed=True)["Y"].mean().unstack()
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for i, col in enumerate(means.columns):
        ax.plot([str(x) for x in means.index], means[col], marker="o",
                color=PAL[i % len(PAL)], lw=2, label=str(col))
    ax.set(title="Plot Interaksi (rata-rata Y)", xlabel="Faktor A", ylabel="Rata-rata Y")
    legend_style(ax)
    fig.tight_layout()
    h.grafik("Plot Interaksi", fig)
    return h


# ==========================================================
# 8) ANCOVA
# ==========================================================
def _ancova_form(df, cur):
    nums, cats = num_cols(df), cat_cols(df)
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in nums else (nums[0] if nums else "")
    f_sel = (cur.get("f") or [None])[0]
    f_sel = f_sel if f_sel in cats else (cats[0] if cats else "")
    cov_opts = [c for c in nums if c != y_sel]
    cov_def = cov_opts[:1]
    return [
        f_select("y", "Variabel Dependen (numerik)", nums, cur, default=y_sel),
        f_select("f", "Faktor (kategori)", cats, cur, default=f_sel),
        f_multi("covs", "Kovariat (numerik)", cov_opts, cur, cov_def),
        f_toggle("interaksi", "Sertakan interaksi Faktor × Kovariat", cur, checked=False),
    ]


def _ancova_run(df, p, alpha):
    y, f = p["y"], p["f"]
    covs = _aslist(p.get("covs", []))
    interaksi = p.get("interaksi", False)
    if not covs:
        raise ValueError("Pilih minimal satu kovariat.")
    data = persiapkan(df, [y, f] + covs)
    data.columns = ["Y", "F"] + [f"K{i+1}" for i in range(len(covs))]
    cov_term = " + ".join(data.columns[2:])
    if interaksi:
        formula = "Y ~ C(F) + " + cov_term + " + " + " + ".join(
            f"C(F):{k}" for k in data.columns[2:])
    else:
        formula = "Y ~ C(F) + " + cov_term
    tbl = anova_lm(smf.ols(formula, data).fit(), typ=2)

    h = Hasil()
    h.tabel("Tabel ANCOVA", tbl.round(4),
            "Model: " + formula)
    for idx, row in tbl.iterrows():
        if idx != "Residual" and pd.notna(row.get("F")):
            h.uji(str(idx), row["F"], row["PR(>F)"], alpha)
    return h


# ==========================================================
# 9) MANOVA
# ==========================================================
def _manova_form(df, cur):
    nums, cats = num_cols(df), cat_cols(df)
    ys_cur = (cur.get("ys") or None)
    ys_def = ys_cur if ys_cur else nums[:2]
    g_sel = (cur.get("g") or [None])[0]
    g_sel = g_sel if g_sel in cats else (cats[0] if cats else "")
    return [
        f_multi("ys", "Variabel Dependen (numerik, ≥ 2)", nums, cur, ys_def),
        f_select("g", "Faktor (kategori)", cats, cur, default=g_sel),
    ]


def _manova_run(df, p, alpha):
    ys, g = _aslist(p["ys"]), p["g"]
    if len(ys) < 2:
        raise ValueError("Pilih minimal 2 variabel dependen.")
    data = persiapkan(df, ys + [g])
    safe_y = [f"Y{i+1}" for i in range(len(ys))]
    data.columns = safe_y + ["G"]
    maov = MANOVA.from_formula(" + ".join(safe_y) + " ~ C(G)", data=data)

    h = Hasil()
    try:
        mv = maov.mv_test()
        h.ringkasan("Hasil Uji Multivariat", str(mv))
        for ef, isi in mv.results.items():
            stt = isi["stat"]
            if "Wilks' lambda" in stt.index:
                w = stt.loc["Wilks' lambda"]
                h.uji(f"MANOVA — {ef} (Wilks' Lambda)", w["F Value"], w["Pr > F"], alpha)
    except Exception:
        h.ringkasan("Hasil Uji Multivariat", str(maov.mv_test()))
    h.tabel("Rata-rata per Kelompok", data.groupby("G")[safe_y].mean().round(3))
    return h


# ==========================================================
# 10) UJI t
# ==========================================================
TT_MODES = [("satu", "Satu Sampel"), ("independen", "Sampel Independen"),
            ("berpasangan", "Sampel Berpasangan")]


def _ttest_form(df, cur):
    nums, cats = num_cols(df), cat_cols(df)
    mode_cur = (cur.get("mode") or ["independen"])[0]
    mode = mode_cur if mode_cur in ("satu", "independen", "berpasangan") else "independen"
    url = (cur.get("__form_url__") or "")
    fields = [
        f_seg("mode", "Jenis uji", TT_MODES, cur, default="independen",
              trigger_url=url, target="#inf-params"),
    ]
    if mode == "satu":
        v_sel = (cur.get("v") or [None])[0]
        v_sel = v_sel if v_sel in nums else (nums[0] if nums else "")
        fields.append(f_select("v", "Variabel (numerik)", nums, cur, default=v_sel))
        fields.append(f_num("mu", "Nilai hipotesis μ₀", cur, default=0))
    elif mode == "independen":
        if not nums or not cats:
            fields.append(Div(
                Div(ICON_SVG("alert", 18), cls="warn-ic"),
                Div(B("Data Belum Memenuhi"),
                    P("Butuh 1 variabel numerik + 1 variabel kelompok (kategorik)."),
                    cls="err-body"),
                cls="card warn-card form-alert anim-in"))
            return fields
        v_sel = (cur.get("v") or [None])[0]
        v_sel = v_sel if v_sel in nums else (nums[0] if nums else "")
        g_sel = (cur.get("g") or [None])[0]
        g_sel = g_sel if g_sel in cats else (cats[0] if cats else "")
        levels = sorted(df[g_sel].dropna().astype(str).unique())
        dua_def = (cur.get("dua") or None) or levels[:2]
        fields.append(f_select("v", "Variabel (numerik)", nums, cur, default=v_sel))
        fields.append(f_select("g", "Variabel kelompok", cats, cur, default=g_sel))
        fields.append(f_multi("dua", "Pilih 2 kelompok yang dibandingkan", levels,
                              cur, dua_def))
    else:
        if len(nums) < 2:
            fields.append(Div(
                Div(ICON_SVG("alert", 18), cls="warn-ic"),
                Div(B("Data Belum Memenuhi"),
                    P("Butuh minimal 2 kolom numerik untuk uji berpasangan."),
                    cls="err-body"),
                cls="card warn-card form-alert anim-in"))
            return fields
        v1_sel = (cur.get("v1") or [None])[0]
        v1_sel = v1_sel if v1_sel in nums else (nums[0] if nums else "")
        v2_opts = [c for c in nums if c != v1_sel]
        v2_sel = (cur.get("v2") or [None])[0]
        v2_sel = v2_sel if v2_sel in v2_opts else (v2_opts[0] if v2_opts else "")
        fields.append(f_select("v1", "Pengukuran 1 (sebelum)", nums, cur, default=v1_sel))
        fields.append(f_select("v2", "Pengukuran 2 (sesudah)", v2_opts, cur, default=v2_sel))
    return fields


def _ttest_run(df, p, alpha):
    mode = p.get("mode", "independen")
    h = Hasil()

    if mode == "satu":
        v, mu = p["v"], float(p.get("mu", 0) or 0)
        x = df[v].dropna()
        t, pv = stats.ttest_1samp(x, mu)
        d = (x.mean() - mu) / x.std(ddof=1)
        h.tabel("Hasil Uji t Satu Sampel", pd.DataFrame(
            {"Nilai": [len(x), x.mean(), x.std(ddof=1), t, len(x) - 1, pv, d]},
            index=["n", "Mean sampel", "Std", "t-statistik", "df", "p-value", "Cohen's d"]).round(4))
        h.uji(f"Uji t Satu Sampel (H₀: μ = {mu:g})", t, pv, alpha)
        h.notes.append("Cohen's d: 0.2 kecil · 0.5 sedang · 0.8 besar")

    elif mode == "independen":
        v, g, dua = p["v"], p["g"], _aslist(p.get("dua", []))
        if len(dua) != 2:
            raise ValueError("Pilih tepat 2 kelompok yang dibandingkan.")
        data = persiapkan(df, [v, g])
        data.columns = ["V", "G"]
        data["G"] = data["G"].astype(str)
        a = data.loc[data.G == dua[0], "V"]
        b = data.loc[data.G == dua[1], "V"]
        lev = stats.levene(a, b, center="median")
        h.uji("Uji Levene (homogenitas varians)", lev.statistic, lev.pvalue, alpha)
        equal = lev.pvalue >= alpha
        t, pv, dfr = sm_ttest(a, b, usevar="pooled" if equal else "unequal")
        n1, n2 = len(a), len(b)
        sp = np.sqrt(((n1 - 1) * a.std(ddof=1) ** 2 + (n2 - 1) * b.std(ddof=1) ** 2)
                     / (n1 + n2 - 2))
        d = (a.mean() - b.mean()) / sp
        h.tabel("Statistik Kelompok", pd.DataFrame(
            {"n": [n1, n2], "Mean": [a.mean(), b.mean()], "Std": [a.std(ddof=1), b.std(ddof=1)]},
            index=list(dua)).round(4))
        h.tabel("Hasil Uji t Independen", pd.DataFrame(
            {"Nilai": [t, dfr, pv, d]},
            index=["t-statistik", "df", "p-value", "Cohen's d"]).round(4))
        h.uji(f"Uji t Independen (varians {'homogen' if equal else 'tidak homogen'})", t, pv, alpha)

    else:
        v1, v2 = p["v1"], p["v2"]
        sub = df[[v1, v2]].dropna()
        t, pv = stats.ttest_rel(sub[v1], sub[v2])
        diff = sub[v1] - sub[v2]
        h.tabel("Hasil Uji t Berpasangan", pd.DataFrame(
            {"Nilai": [len(sub), sub[v1].mean(), sub[v2].mean(),
                       diff.mean(), diff.std(ddof=1), t, pv,
                       diff.mean() / diff.std(ddof=1)]},
            index=["n pasangan", f"Mean {v1}", f"Mean {v2}", "Mean selisih",
                   "Std selisih", "t-statistik", "p-value", "Cohen's dz"]).round(4))
        h.uji("Uji t Berpasangan", t, pv, alpha)
    return h


# ==========================================================
# 11) CHI-SQUARE
# ==========================================================
def _chisq_form(df, cur):
    cats = [c for c in df.columns if df[c].nunique(dropna=True) <= 20]
    c1_sel = (cur.get("c1") or [None])[0]
    c1_sel = c1_sel if c1_sel in cats else (cats[0] if cats else "")
    c2_opts = [c for c in cats if c != c1_sel]
    c2_sel = (cur.get("c2") or [None])[0]
    c2_sel = c2_sel if c2_sel in c2_opts else (c2_opts[0] if c2_opts else "")
    return [
        f_select("c1", "Variabel 1", cats, cur, default=c1_sel),
        f_select("c2", "Variabel 2", c2_opts, cur, default=c2_sel),
    ]


def _chisq_run(df, p, alpha):
    c1, c2 = p["c1"], p["c2"]
    data = df[[c1, c2]].dropna().astype(str)
    tab = pd.crosstab(data[c1], data[c2])
    chi2v, pv, dof, exp = stats.chi2_contingency(tab)
    n = tab.values.sum()
    cramers = np.sqrt(chi2v / (n * (min(tab.shape) - 1)))

    h = Hasil()
    h.tabel("Tabel Kontingensi (Observed)", tab)
    h.tabel("Frekuensi Harapan",
            pd.DataFrame(exp, index=tab.index, columns=tab.columns).round(2))
    h.tabel("Persentase per Baris (%)",
            (pd.crosstab(data[c1], data[c2], normalize="index") * 100).round(2))
    h.metric("Cramér's V (ukuran efek)", f"{cramers:.3f}", "percent")
    h.uji(f"Chi-Square Independensi (df = {dof})", chi2v, pv, alpha)
    if (exp < 5).any():
        h.warnings.append("Ada sel dengan frekuensi harapan < 5 — interpretasikan dengan hati-hati.")
    h.notes.append(f"Kontingensi: {c1} × {c2} (n = {n:,})")
    h.notes.append("Cramér's V: < 0.1 kecil · < 0.3 sedang · < 0.5 besar")
    return h


# ==========================================================
# 12) KORELASI
# ==========================================================
def _korelasi_form(df, cur):
    nums = num_cols(df)
    cols_def = (cur.get("cols") or None) or nums[:6]
    return [
        f_multi("cols", "Pilih variabel numerik", nums, cur, cols_def,
                "Minimal 2 variabel."),
        f_seg("metode", "Metode", [("pearson", "Pearson"), ("spearman", "Spearman"),
                                   ("kendall", "Kendall")], cur, default="pearson"),
    ]


def _matriks_p(data, metode):
    n = len(data.columns)
    pm = pd.DataFrame(np.eye(n), index=data.columns, columns=data.columns)
    for i in range(n):
        for j in range(i + 1, n):
            x, yy = data.iloc[:, i], data.iloc[:, j]
            if metode == "pearson":
                _, pv = stats.pearsonr(x, yy)
            elif metode == "spearman":
                _, pv = stats.spearmanr(x, yy)
            else:
                _, pv = stats.kendalltau(x, yy)
            pm.iloc[i, j] = pm.iloc[j, i] = pv
    return pm


def _korelasi_run(df, p, alpha):
    cols, metode = _aslist(p["cols"]), p.get("metode", "pearson")
    if len(cols) < 2:
        raise ValueError("Pilih minimal 2 variabel.")
    data = df[cols].dropna()
    corr = data.corr(method=metode)

    h = Hasil()
    h.tabel(f"Matriks Korelasi ({metode.capitalize()})", corr.round(3))
    h.tabel("Matriks p-value", _matriks_p(data, metode).round(4))
    h.notes.append("|r|: < 0.3 lemah · 0.3–0.5 sedang · 0.5–0.7 kuat · > 0.7 sangat kuat")

    n = len(cols)
    fig, ax = plt.subplots(figsize=(0.6 * n + 3, 0.5 * n + 2.5))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(n))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(n))
    ax.set_yticklabels(corr.index)
    ax.grid(False)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(corr.values[i, j]) > .5 else "#10131C")
    cb = fig.colorbar(im, shrink=.8)
    cb.ax.tick_params(colors=MUT)
    ax.set_title(f"Heatmap Korelasi ({metode.capitalize()})")
    fig.tight_layout()
    h.grafik("Heatmap Korelasi", fig)
    return h


# ==========================================================
# 13) ANALISIS FAKTOR (EFA)
# ==========================================================
def _faktor_form(df, cur):
    nums = num_cols(df)
    cols_def = (cur.get("cols") or None) or nums[:8]
    cols_sel = [c for c in cols_def if c in nums]
    try:
        ev = np.sort(np.linalg.eigvalsh(df[cols_sel].dropna().corr().values))[::-1]
        n_kaiser = max(1, int((ev > 1).sum()))
    except Exception:
        n_kaiser = 1
    if not FA_OK:
        return [Div(
            Div(ICON_SVG("alert", 18), cls="warn-ic"),
            Div(B("Library Belum Tersedia"),
                P("Analisis faktor membutuhkan paket factor-analyzer. "
                  "Jalankan: pip install factor-analyzer"),
                cls="err-body"),
            cls="card warn-card form-alert anim-in")]
    return [
        f_multi("cols", "Pilih variabel (indikator)", nums, cur, cols_def,
                "Minimal 3 variabel numerik."),
        f_num("k", "Jumlah faktor", cur, default=min(n_kaiser, max(1, len(cols_sel))),
              step="1", mn=1, mx=max(1, len(cols_sel)),
              hint="Nilai awal mengikuti kaidah Kaiser (eigenvalue > 1)."),
        f_seg("rot", "Rotasi", [("varimax", "Varimax"), ("promax", "Promax"),
                                ("none", "Tanpa rotasi")], cur, default="varimax"),
        f_toggle("sembunyi", "Sembunyikan loading dengan |nilai| < 0.40", cur, checked=False),
    ]


def _faktor_run(df, p, alpha):
    if not FA_OK:
        raise ValueError("Paket factor-analyzer belum terinstall (pip install factor-analyzer).")
    cols = _aslist(p["cols"])
    k = int(float(p.get("k", 1) or 1))
    rot = p.get("rot", "varimax")
    sembunyi = p.get("sembunyi", False)
    data = df[cols].dropna()
    h = Hasil()
    if data.shape[0] < 5 * len(cols):
        h.warnings.append("Disarankan jumlah observasi ≥ 5 × jumlah variabel "
                          f"(saat ini {data.shape[0]:,} observasi untuk {len(cols)} variabel).")

    ev = np.sort(np.linalg.eigvalsh(data.corr().values))[::-1]

    try:
        chi_b, p_b = calculate_bartlett_sphericity(data)
        h.uji("Uji Bartlett's Test of Sphericity", chi_b, p_b, alpha)
        _, kmo = calculate_kmo(data)
        h.metric("KMO (Kaiser-Meyer-Olkin)", f"{kmo:.3f}", "percent")
        if kmo < .5:
            h.warnings.append("KMO < 0.5 → kecukupan sampling kurang untuk analisis faktor.")
    except Exception as e:
        h.warnings.append(f"KMO/Bartlett gagal dihitung: {e}")

    fa = FactorAnalyzer(n_factors=k, rotation=None if rot == "none" else rot)
    fa.fit(data)
    load = pd.DataFrame(fa.loadings_, index=cols,
                        columns=[f"Faktor {i+1}" for i in range(k)])
    if sembunyi:
        load = load.where(load.abs() >= .4, "")
        h.notes.append("Loading dengan |nilai| < 0.40 disembunyikan.")
    h.tabel("Matriks Loading", load.round(3))

    h.tabel("Komunalitas",
            pd.DataFrame({"Komunalitas": fa.get_communalities()}, index=cols).round(3))

    ss, prop, cum = fa.get_factor_variance()
    h.tabel("Varians yang Dijelaskan",
            pd.DataFrame({"SS Loading": ss, "Proporsi": prop, "Kumulatif": cum},
                         index=[f"Faktor {i+1}" for i in range(k)]).round(3))

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(range(1, len(ev) + 1), ev, "o-", color=PAL[0], lw=2)
    ax.axhline(1, color="#F472B6", ls="--", lw=1.3, label="Eigenvalue = 1 (kaidah Kaiser)")
    ax.set(xlabel="Komponen", ylabel="Eigenvalue", title="Scree Plot")
    legend_style(ax)
    fig.tight_layout()
    h.grafik("Scree Plot", fig)
    return h


# ==========================================================
# 14) PCA
# ==========================================================
def _pca_form(df, cur):
    nums = num_cols(df)
    cols_def = (cur.get("cols") or None) or nums[:6]
    cols_sel = [c for c in cols_def if c in nums]
    n_show = (cur.get("nshow") or [None])[0]
    n_show = int(float(n_show)) if n_show else min(3, len(cols_sel))
    return [
        f_multi("cols", "Pilih variabel", nums, cur, cols_def),
        f_toggle("skala", "Standarisasi data (z-score)", cur, checked=True),
        f_range("nshow", "Jumlah komponen pada tabel loading", cur,
                lo=2, hi=max(2, len(cols_sel)), default=max(2, n_show)),
    ]


def _pca_run(df, p, alpha):
    cols = _aslist(p["cols"])
    skala = p.get("skala", True)
    n_show = int(float(p.get("nshow", 3) or 3))
    data = df[cols].dropna()
    Z = StandardScaler().fit_transform(data) if skala else data.values
    pca = PCA().fit(Z)
    evr = pca.explained_variance_ratio_

    h = Hasil()
    h.tabel("Varians yang Dijelaskan",
            pd.DataFrame({"Eigenvalue": pca.explained_variance_,
                          "Proporsi": evr, "Kumulatif": np.cumsum(evr)},
                         index=[f"PC{i+1}" for i in range(len(evr))]).round(4))
    h.tabel("Loading Komponen",
            pd.DataFrame(pca.components_.T[:, :n_show], index=cols,
                         columns=[f"PC{i+1}" for i in range(n_show)]).round(3))

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.bar(range(1, len(evr) + 1), evr, alpha=.85, color=PAL[0], label="Proporsi varians")
    ax2 = ax.twinx()
    ax2.plot(range(1, len(evr) + 1), np.cumsum(evr), "o-", color=PAL[1], lw=2,
             label="Kumulatif")
    ax2.axhline(.8, ls="--", color="#94A1B8", lw=1)
    ax2.set_ylim(0, 1.05)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax.set(xlabel="Komponen Utama", ylabel="Proporsi Varians", title="Scree Plot PCA")
    handles = [mlines.Line2D([], [], color=PAL[0], lw=7, alpha=.85, label="Proporsi varians"),
               mlines.Line2D([], [], color=PAL[1], marker="o", lw=2, label="Kumulatif")]
    ax.legend(handles=handles, frameon=True)
    fig.tight_layout()
    h.grafik("Scree Plot PCA", fig)

    scores = PCA(n_components=2).fit_transform(Z)
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.scatter(scores[:, 0], scores[:, 1], alpha=.55, s=16, color=PAL[0], edgecolor=BG, lw=.2)
    vsc = np.abs(scores[:, :2]).max(axis=0)
    for i, c in enumerate(cols):
        xv, yv = pca.components_[0, i] * vsc[0], pca.components_[1, i] * vsc[1]
        ax.arrow(0, 0, xv, yv, color="#F472B6", alpha=.85,
                 head_width=vsc[0] * .03, length_includes_head=True)
        ax.text(xv * 1.12, yv * 1.12, str(c), color="#F472B6", fontsize=8.5, fontweight="bold")
    ax.axhline(0, color="#3A4763", lw=.6)
    ax.axvline(0, color="#3A4763", lw=.6)
    ax.set(title="Biplot PCA (PC1 vs PC2)", xlabel="PC1", ylabel="PC2")
    fig.tight_layout()
    h.grafik("Biplot PCA", fig)
    h.notes.append(f"PC1 + PC2 menjelaskan {evr[:2].sum():.1%} dari total varians.")
    return h


# ==========================================================
# 15) ANALISIS DISKRIMINAN (LDA)
# ==========================================================
def _lda_form(df, cur):
    nums, cats = num_cols(df), cat_cols(df)
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in cats else (cats[0] if cats else "")
    xs_def = [c for c in nums if c != y_sel][:4]
    return [
        f_select("y", "Variabel kelompok (kategori)", cats, cur, default=y_sel),
        f_multi("xs", "Variabel pembeda (numerik)", [c for c in nums if c != y_sel],
                cur, xs_def),
    ]


def _lda_run(df, p, alpha):
    y, xs = p["y"], _aslist(p["xs"])
    if not xs:
        raise ValueError("Pilih minimal satu variabel X.")
    data = persiapkan(df, xs + [y])
    X, yv = data[xs].values, data[y].values
    lda = LinearDiscriminantAnalysis().fit(X, yv)
    pred = lda.predict(X)

    h = Hasil()
    h.metric("Akurasi (resubstitusi)", f"{accuracy_score(yv, pred):.1%}", "target")
    try:
        cv = min(5, pd.Series(yv).value_counts().min())
        if cv >= 2:
            sc = cross_val_score(LinearDiscriminantAnalysis(), X, yv, cv=cv)
            h.metric(f"Akurasi Cross-Validation ({cv}-fold)", f"{sc.mean():.1%}", "shield")
    except Exception:
        pass

    h.tabel("Rata-rata Variabel per Kelompok",
            pd.DataFrame(lda.means_, index=lda.classes_, columns=xs).round(3))
    h.tabel("Koefisien Fungsi Diskriminan",
            pd.DataFrame(lda.scalings_, index=xs,
                         columns=[f"LD{i+1}" for i in range(lda.scalings_.shape[1])]).round(4))
    cm = confusion_matrix(yv, pred, labels=lda.classes_)
    h.tabel("Matriks Klasifikasi",
            pd.DataFrame(cm, index=[f"Aktual {c}" for c in lda.classes_],
                         columns=[f"Pred {c}" for c in lda.classes_]))
    return h


# ==========================================================
# 16) K-MEANS CLUSTERING
# ==========================================================
def _kmeans_form(df, cur):
    nums = num_cols(df)
    xs_def = (cur.get("xs") or None) or nums[:4]
    return [
        f_multi("xs", "Variabel clustering", nums, cur, xs_def, "Minimal 2 variabel."),
        f_range("k", "Jumlah cluster (k)", cur, lo=2, hi=10, default=3),
        f_toggle("skala", "Standarisasi variabel", cur, checked=True),
    ]


def _kmeans_run(df, p, alpha):
    xs = _aslist(p["xs"])
    k = int(float(p.get("k", 3) or 3))
    skala = p.get("skala", True)
    if len(xs) < 2:
        raise ValueError("Pilih minimal 2 variabel.")
    data = df[xs].dropna()
    Z = StandardScaler().fit_transform(data) if skala else data.values
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(Z)
    lab = km.labels_

    h = Hasil()
    sil = silhouette_score(Z, lab) if k < len(Z) else np.nan
    h.metric("Silhouette Score", f"{sil:.3f}" if pd.notna(sil) else "-", "target")
    h.metric("Jumlah Cluster", str(k), "share2")
    h.metric("Anggota Cluster (min–maks)",
             f"{int(pd.Series(lab).value_counts().min())} – "
             f"{int(pd.Series(lab).value_counts().max())}", "list")

    counts = pd.Series(lab).value_counts().sort_index()
    h.tabel("Distribusi Anggota Cluster",
            pd.DataFrame({"Jumlah Anggota": counts.values},
                         index=[f"Cluster {i}" for i in counts.index]))

    centers = km.cluster_centers_
    if skala:
        centers = StandardScaler().fit(data).inverse_transform(centers)
    h.tabel("Pusat Cluster (skala asli)",
            pd.DataFrame(centers, columns=xs,
                         index=[f"Cluster {i}" for i in range(k)]).round(3))

    inert = [KMeans(n_clusters=i, n_init=10, random_state=42).fit(Z).inertia_
             for i in range(1, 9)]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.plot(range(1, 9), inert, "o-", color=PAL[0], lw=2)
    ax.set(title="Elbow Method (bantu menentukan k)", xlabel="k", ylabel="Inertia")
    fig.tight_layout()
    h.grafik("Elbow Method", fig)

    p2 = PCA(n_components=2).fit_transform(Z)
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for i in range(k):
        ax.scatter(p2[lab == i, 0], p2[lab == i, 1], alpha=.75, s=20,
                   color=PAL[i % len(PAL)], edgecolor=BG, lw=.2, label=f"Cluster {i}")
    legend_style(ax)
    ax.set(title="Visualisasi Cluster (proyeksi PCA 2D)", xlabel="PC1", ylabel="PC2")
    fig.tight_layout()
    h.grafik("Visualisasi Cluster", fig)

    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    bars = ax.bar([f"C{i}" for i in counts.index], counts.values,
                  color=[PAL[i % len(PAL)] for i in range(len(counts))], alpha=.9)
    for b, v in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width() / 2, v, str(int(v)), ha="center",
                va="bottom", fontsize=9, color=TITLE_C, fontweight="bold")
    ax.set(title="Jumlah Anggota per Cluster", xlabel="Cluster", ylabel="n")
    fig.tight_layout()
    h.grafik("Komposisi Cluster", fig)

    hasil = data.copy()
    hasil["Cluster"] = lab
    h.tabel("Data + Label Cluster (pratinjau 100 baris)", hasil.head(100))
    key = uuid.uuid4().hex[:8]
    h.downloads.append(("Unduh hasil clustering (CSV)", "hasil_cluster.csv", key, hasil))
    return h


# ==========================================================
# 17) KRUSKAL-WALLIS
# ==========================================================
def _kruskal_form(df, cur):
    nums, cats = num_cols(df), cat_cols(df)
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in nums else (nums[0] if nums else "")
    g_sel = (cur.get("g") or [None])[0]
    g_sel = g_sel if g_sel in cats else (cats[0] if cats else "")
    return [
        f_select("y", "Variabel Dependen (numerik)", nums, cur, default=y_sel),
        f_select("g", "Faktor (kategori)", cats, cur, default=g_sel),
    ]


def _kruskal_run(df, p, alpha):
    y, g = p["y"], p["g"]
    data = persiapkan(df, [y, g])
    data.columns = ["Y", "G"]
    groups = [gg["Y"].values for _, gg in data.groupby("G")]
    H, pv = stats.kruskal(*groups)
    k = len(groups)
    ranks = data["Y"].rank()
    mr = data.assign(R=ranks).groupby("G")["R"].mean()

    h = Hasil()
    h.tabel("Statistik per Kelompok",
            data.groupby("G")["Y"].agg(["count", "median", "mean"])
            .join(mr.rename("Mean Rank")).round(3))
    h.uji("Kruskal-Wallis H", H, pv, alpha)
    h.notes.append(f"Epsilon-squared (ukuran efek) = {(H - k + 1) / (len(data) - k):.3f}")

    if pv < alpha and k > 2:
        lv = sorted(data.G.unique(), key=str)
        n_tes = k * (k - 1) // 2
        rows = []
        for i in range(k):
            for j in range(i + 1, k):
                u, pp = stats.mannwhitneyu(data.loc[data.G == lv[i], "Y"],
                                           data.loc[data.G == lv[j], "Y"])
                rows.append({"Perbandingan": f"{lv[i]} vs {lv[j]}", "U": u,
                             "p-value": pp, "p terkoreksi": min(pp * n_tes, 1.0)})
        h.tabel("Post-Hoc: Mann-Whitney U (koreksi Bonferroni)",
                pd.DataFrame(rows).set_index("Perbandingan").round(4),
                f"{n_tes} perbandingan berpasangan diuji.")
    return h


# ==========================================================
# 18) MANN-WHITNEY U
# ==========================================================
def _mwu_form(df, cur):
    nums, cats = num_cols(df), cat_cols(df)
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in nums else (nums[0] if nums else "")
    g_sel = (cur.get("g") or [None])[0]
    g_sel = g_sel if g_sel in cats else (cats[0] if cats else "")
    lv = sorted(df[g_sel].dropna().astype(str).unique()) if g_sel else []
    dua_def = (cur.get("dua") or None) or lv[:2]
    return [
        f_select("y", "Variabel (numerik)", nums, cur, default=y_sel),
        f_select("g", "Variabel kelompok", cats, cur, default=g_sel),
        f_multi("dua", "Pilih 2 kelompok", lv, cur, dua_def),
    ]


def _mwu_run(df, p, alpha):
    y, g, dua = p["y"], p["g"], _aslist(p.get("dua", []))
    if len(dua) != 2:
        raise ValueError("Pilih tepat 2 kelompok.")
    data = persiapkan(df, [y, g])
    data.columns = ["Y", "G"]
    data["G"] = data["G"].astype(str)
    a = data.loc[data.G == dua[0], "Y"]
    b = data.loc[data.G == dua[1], "Y"]
    u, pv = stats.mannwhitneyu(a, b, alternative="two-sided")
    n1, n2 = len(a), len(b)
    mu_u, sd_u = n1 * n2 / 2, np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z = (u - mu_u) / sd_u

    h = Hasil()
    h.tabel("Statistik Kelompok", pd.DataFrame(
        {"n": [n1, n2], "Median": [a.median(), b.median()],
         "Mean Rank approx": [mu_u / n2, mu_u / n1]}, index=list(dua)).round(3))
    h.tabel("Hasil Uji Mann-Whitney U", pd.DataFrame(
        {"Nilai": [u, z, pv, abs(z) / np.sqrt(n1 + n2)]},
        index=["U", "Z", "p-value", "r (ukuran efek)"]).round(4))
    h.uji("Mann-Whitney U", u, pv, alpha)
    return h


# ==========================================================
# 19) WILCOXON SIGNED-RANK
# ==========================================================
def _wilcoxon_form(df, cur):
    nums = num_cols(df)
    v1_sel = (cur.get("v1") or [None])[0]
    v1_sel = v1_sel if v1_sel in nums else (nums[0] if nums else "")
    v2_opts = [c for c in nums if c != v1_sel]
    v2_sel = (cur.get("v2") or [None])[0]
    v2_sel = v2_sel if v2_sel in v2_opts else (v2_opts[0] if v2_opts else "")
    return [
        f_select("v1", "Pengukuran 1 (sebelum)", nums, cur, default=v1_sel),
        f_select("v2", "Pengukuran 2 (sesudah)", v2_opts, cur, default=v2_sel),
    ]


def _wilcoxon_run(df, p, alpha):
    v1, v2 = p["v1"], p["v2"]
    sub = df[[v1, v2]].dropna()
    w, pv = stats.wilcoxon(sub[v1], sub[v2])
    d = (sub[v1] - sub[v2])
    d = d[d != 0]
    n = len(d)
    z = (w - n * (n + 1) / 4) / np.sqrt(n * (n + 1) * (2 * n + 1) / 24)

    h = Hasil()
    h.tabel("Hasil Uji Wilcoxon Signed-Rank", pd.DataFrame(
        {"Nilai": [n, sub[v1].median(), sub[v2].median(), w, z, pv, abs(z) / np.sqrt(n)]},
        index=["n (selisih ≠ 0)", f"Median {v1}", f"Median {v2}",
               "W", "Z", "p-value", "r (ukuran efek)"]).round(4))
    h.uji("Wilcoxon Signed-Rank", w, pv, alpha)
    return h


# ==========================================================
# 20) FRIEDMAN
# ==========================================================
def _friedman_form(df, cur):
    nums = num_cols(df)
    cols_def = (cur.get("cols") or None) or nums[:3]
    return [
        f_multi("cols", "Pilih ≥ 3 kondisi/pengukuran", nums, cur, cols_def,
                "Minimal 3 kolom numerik."),
    ]


def _friedman_run(df, p, alpha):
    cols = _aslist(p["cols"])
    if len(cols) < 3:
        raise ValueError("Pilih minimal 3 variabel.")
    data = df[cols].dropna()
    chi_sq, pv = stats.friedmanchisquare(*[data[c] for c in cols])
    n, k = data.shape

    h = Hasil()
    h.tabel("Median per Kondisi", data[cols].median().to_frame("Median").round(3))
    h.uji("Friedman Test", chi_sq, pv, alpha)
    h.notes.append(f"Kendall's W (ukuran efek) = {chi_sq / (n * (k - 1)):.3f}")
    return h


# ==========================================================
# REGISTRY 20 ANALISIS
# ==========================================================
GRUP = {
    "regresi": ("Regresi & Model Terkait", "trendup"),
    "varians": ("ANOVA & Kovarians", "flask"),
    "beda": ("Uji Beda & Non-Parametrik", "scale"),
    "asosiasi": ("Asosiasi & Korelasi", "link"),
    "multivariat": ("Analisis Multivariat", "layers"),
}

ANALISIS = {
    "ols": {
        "judul": "Regresi Linear (OLS)", "ikon": "trendup", "grup": "regresi",
        "desc": "Regresi linear berganda dengan VIF, uji asumsi klasik & diagnostik residual.",
        "form": _ols_form, "run": _ols_run,
    },
    "logit": {
        "judul": "Regresi Logistik Biner", "ikon": "target", "grup": "regresi",
        "desc": "Pemodelan peluang Y biner, odds ratio & matriks konfusi.",
        "form": _logit_form, "run": _logit_run,
    },
    "mnlogit": {
        "judul": "Regresi Logistik Multinomial", "ikon": "shuffle", "grup": "regresi",
        "desc": "Y kategorik 2–10 level, relative risk ratio terhadap kategori dasar.",
        "form": _mnlogit_form, "run": _mnlogit_run,
    },
    "ordinal": {
        "judul": "Regresi Ordinal", "ikon": "listordered", "grup": "regresi",
        "desc": "Logit ordinal (OrderedModel) untuk Y bertingkat.",
        "form": _ordinal_form, "run": _ordinal_run,
    },
    "poisson": {
        "judul": "Regresi Poisson", "ikon": "hash", "grup": "regresi",
        "desc": "Model data hitungan (GLM Poisson) dengan IRR.",
        "form": _poisson_form, "run": _poisson_run,
    },
    "anova1": {
        "judul": "ANOVA Satu Arah", "ikon": "flask", "grup": "varians",
        "desc": "Bandingkan rata-rata ≥ 2 kelompok, Levene, eta squared & Tukey HSD.",
        "form": _anova1_form, "run": _anova1_run,
    },
    "anova2": {
        "judul": "ANOVA Dua Arah", "ikon": "flask", "grup": "varians",
        "desc": "Dua faktor sekaligus dengan opsi interaksi A × B.",
        "form": _anova2_form, "run": _anova2_run,
    },
    "ancova": {
        "judul": "ANCOVA", "ikon": "ruler", "grup": "varians",
        "desc": "ANOVA dengan kovariat numerik untuk mengontrol pengaruh lain.",
        "form": _ancova_form, "run": _ancova_run,
    },
    "manova": {
        "judul": "MANOVA", "ikon": "boxes", "grup": "varians",
        "desc": "Uji multivariat untuk ≥ 2 variabel dependen sekaligus.",
        "form": _manova_form, "run": _manova_run,
    },
    "ttest": {
        "judul": "Uji t", "ikon": "scale", "grup": "beda",
        "desc": "Satu sampel, independen (dengan Levene), atau berpasangan.",
        "form": _ttest_form, "run": _ttest_run,
    },
    "chisq": {
        "judul": "Uji Chi-Square", "ikon": "grid", "grup": "asosiasi",
        "desc": "Independensi dua variabel kategorik + Cramér's V.",
        "form": _chisq_form, "run": _chisq_run,
    },
    "korelasi": {
        "judul": "Analisis Korelasi", "ikon": "link", "grup": "asosiasi",
        "desc": "Matriks korelasi & p-value Pearson/Spearman/Kendall + heatmap.",
        "form": _korelasi_form, "run": _korelasi_run,
    },
    "faktor": {
        "judul": "Analisis Faktor (EFA)", "ikon": "component", "grup": "multivariat",
        "desc": "KMO, Bartlett, loading, komunalitas, varians & scree plot.",
        "form": _faktor_form, "run": _faktor_run,
    },
    "pca": {
        "judul": "Analisis Komponen Utama (PCA)", "ikon": "compass", "grup": "multivariat",
        "desc": "Varians dijelaskan, loading, scree plot & biplot PC1–PC2.",
        "form": _pca_form, "run": _pca_run,
    },
    "lda": {
        "judul": "Analisis Diskriminan (LDA)", "ikon": "crosshair", "grup": "multivariat",
        "desc": "Klasifikasi ke kelompok + akurasi & cross-validation.",
        "form": _lda_form, "run": _lda_run,
    },
    "kmeans": {
        "judul": "K-Means Clustering", "ikon": "share2", "grup": "multivariat",
        "desc": "Segmentasi data, silhouette, elbow method & visualisasi cluster.",
        "form": _kmeans_form, "run": _kmeans_run,
    },
    "kruskal": {
        "judul": "Kruskal-Wallis", "ikon": "scale", "grup": "beda",
        "desc": "Alternatif non-parametrik ANOVA + post-hoc Mann-Whitney Bonferroni.",
        "form": _kruskal_form, "run": _kruskal_run,
    },
    "mwu": {
        "judul": "Mann-Whitney U", "ikon": "leftright", "grup": "beda",
        "desc": "Bandingkan 2 kelompok independen secara non-parametrik.",
        "form": _mwu_form, "run": _mwu_run,
    },
    "wilcoxon": {
        "judul": "Wilcoxon Signed-Rank", "ikon": "leftright", "grup": "beda",
        "desc": "Alternatif non-parametrik uji t berpasangan.",
        "form": _wilcoxon_form, "run": _wilcoxon_run,
    },
    "friedman": {
        "judul": "Friedman", "ikon": "activity", "grup": "beda",
        "desc": "≥ 3 pengukuran berulang pada subjek yang sama.",
        "form": _friedman_form, "run": _friedman_run,
    },
}


# ==========================================================
# PEMBACAAN FILE (format diperluas)
# ==========================================================
def _read_delimited(file_bytes, base_msg):
    import csv as _csv
    encodings = ["utf-8", "utf-8-sig", "latin-1"]
    last_err = None
    for enc in encodings:
        try:
            file_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
        sep_terdeteksi = None
        try:
            sep_terdeteksi = _csv.Sniffer().sniff(
                file_bytes.decode(enc)[:8192], delimiters=",;\t|").delimiter
        except _csv.Error:
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


def load_data_inf(raw, fname):
    ext = os.path.splitext(fname)[1].lower()
    if ext == ".csv":
        return _read_delimited(raw, "Gagal membaca file CSV.")
    if ext in (".xls", ".xlsx", ".xlsm"):
        return pd.read_excel(io.BytesIO(raw), sheet_name=0)
    if ext == ".tsv":
        return pd.read_csv(io.BytesIO(raw), sep="\t")
    if ext == ".json":
        try:
            return pd.read_json(io.BytesIO(raw))
        except ValueError:
            return pd.read_json(io.BytesIO(raw), lines=True)
    if ext == ".dbf":
        if not DBF_OK:
            raise ValueError("Library dbfread belum terinstall. Jalankan: pip install dbfread")
        with tempfile.NamedTemporaryFile(suffix=".dbf", delete=False) as tmp:
            tmp.write(raw)
            path = tmp.name
        try:
            return pd.DataFrame(iter(DBF(path, load=True, encoding="latin1")))
        finally:
            os.remove(path)
    if ext == ".sav":
        if not SAV_OK:
            raise ValueError("Library pyreadstat belum terinstall. Jalankan: pip install pyreadstat")
        with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as tmp:
            tmp.write(raw)
            path = tmp.name
        try:
            d, _ = pyreadstat.read_sav(path)
            return d
        finally:
            os.remove(path)
    if ext == ".dta":
        return pd.read_stata(io.BytesIO(raw))
    if ext == ".parquet":
        return pd.read_parquet(io.BytesIO(raw))
    if ext in (".pkl", ".pickle"):
        return pd.read_pickle(io.BytesIO(raw))
    return _read_delimited(raw, "Gagal membaca file teks.")


def excel_sheets(raw):
    x = pd.ExcelFile(io.BytesIO(raw))
    return x.sheet_names


# ==========================================================
# DATA CONTOH (untuk tombol "Coba Data Contoh")
# ==========================================================
def buat_data_contoh():
    rng = np.random.default_rng(42)
    n = 150
    metode = rng.choice(["A", "B", "C"], size=n, p=[.34, .33, .33])
    gender = rng.choice(["L", "P"], size=n)
    wilayah = rng.choice(["Utara", "Selatan", "Barat", "Timur"], size=n)
    motivasi = np.clip(rng.normal(6.5, 1.6, n), 1, 10).round(1)
    belajar = np.clip(rng.normal(9, 4, n), 0.5, 25).round(1)
    efek = np.select([metode == "A", metode == "B", metode == "C"], [2.0, 6.0, 0.0])
    pre = np.clip(rng.normal(68, 8, n), 30, 100).round(1)
    post = np.clip(pre + efek + 0.55 * (motivasi - 6.5) + rng.normal(0, 5, n), 20, 100).round(1)
    kehadiran = rng.poisson(9 + 0.5 * (motivasi - 4), n).clip(0, 20)
    skor = np.clip(0.5 * pre + 0.3 * belajar * 2 + rng.normal(0, 7, n), 0, 100).round(1)
    pendapatan = (np.exp(rng.normal(12.6, 0.42, n)) * 1000).round(0)
    kep_score = 0.35 * (motivasi - 1) + 0.25 * (post / 100 * 4) + rng.normal(0, .9, n)
    kepuasan = pd.cut(kep_score, [-9, .8, 1.6, 2.4, 3.2, 9],
                      labels=["Sangat Kurang", "Kurang", "Cukup", "Baik", "Sangat Baik"])
    promosi = np.where(0.5 * motivasi + 0.15 * skor + rng.normal(0, 3.2, n) > 11.4,
                       "Ya", "Tidak")
    df = pd.DataFrame({
        "nilai_pre": pre, "nilai_post": post, "skor_ujian": skor,
        "motivasi": motivasi, "jam_belajar": belajar, "kehadiran": kehadiran,
        "pendapatan": pendapatan, "metode": metode, "gender": gender,
        "wilayah": wilayah, "kepuasan": kepuasan.astype(str), "promosi": promosi,
    })
    return df


# ==========================================================
# FRAGMEN HALAMAN
# ==========================================================
def inf_hero():
    return Div(
        Span(ICON_SVG("sparkles", 13), "Statistik Inferensial", cls="eyebrow"),
        H1(
            "Uji hipotesis & pemodelan ",
            Span("tingkat lanjut", cls="grad-text"),
            " langsung dari browser",
        ),
        P(
            "Unggah data, pilih salah satu dari 20 analisis inferensial - regresi, ANOVA, "
            "uji non-parametrik, hingga multivariat - lalu dapatkan tabel lengkap, keputusan uji, "
            "narasi analisis otomatis, dan grafik siap publikasi.",
            cls="hero-sub",
        ),
        Div(
            Span("20 analisis", cls="chip chip-cyan"),
            A(ICON_SVG("book", 13), "Baca teori & kegunaan uji", href="/teori", cls="chip chip-link"),
            cls="teori-chips",
        ),
        Div(
            Div(
                Div(ICON_SVG("zap", 16), cls="feature-ic"),
                Div(B("Keputusan Otomatis"),
                    Span("Setiap uji dilengkapi keputusan Tolak / Gagal Tolak H\u2080 plus narasi "
                         "analisis otomatis yang siap disalin ke laporan.")),
                cls="feature",
            ),
            Div(
                Div(ICON_SVG("layers", 16), cls="feature-ic"),
                Div(B("20 Analisis Lengkap"),
                    Span("OLS, logistik biner/multinomial, ordinal, Poisson, ANOVA/ANCOVA/"
                         "MANOVA, uji t, chi-square, korelasi, EFA, PCA, LDA, K-Means, "
                         "dan uji non-parametrik.")),
                cls="feature",
            ),
            Div(
                Div(ICON_SVG("shield", 16), cls="feature-ic"),
                Div(B("Fleksibel & Responsif"),
                    Span("Parameter menyesuaikan kolom data secara otomatis; nyaman "
                         "diakses dari desktop maupun ponsel.")),
                cls="feature",
            ),
            cls="features anim-in d1 features-3",
        ),
        cls="hero",
    )


def inf_upload_section():
    return Section(
        Div(
            Div(ICON_SVG("cloud", 28), cls="drop-ic"),
            H3("Tarik & letakkan file di sini", cls="drop-title"),
            P("atau klik area ini untuk ", Span("memilih file", cls="link-like"),
              " dari perangkat Anda", cls="drop-hint"),
            id="dropzone",
            cls="dropzone",
        ),
        Input(type="file", name="file", id="file-input", accept=INF_ACCEPT, cls="sr-only"),
        Div(Div(id="upload-bar", cls="progress-bar"), id="upload-progress", cls="progress-wrap"),
        Div(id="upload-error"),
        Div(*[Span(f.upper(), cls="fmt-chip") for f in INF_FORMATS], cls="fmt-row"),
        P(
            Label(
                Input(type="checkbox", name="autoconv", checked=True, cls="tgl-in"),
                Span(cls="tgl-track"), 
                Span("Konversi otomatis kolom teks \u2192 numerik", cls="tgl-txt"),
                cls="toggle toggle-inline",
            ),
            cls="autoconv-row",
        ),
        P(ICON_SVG("shield", 13), " File diproses sepenuhnya secara lokal di server - tidak dibagikan ke pihak mana pun.",
          cls="privacy-note"),
        id="upload-section",
        cls="upload-card card anim-in",
    )


def inf_empty():
    return Div(
        Div(ICON_SVG("database", 30), cls="empty-ic"),
        H3("Belum Ada Data"),
        P("Unggah file untuk memilih dan menjalankan analisis statistik inferensial. "
          "Hasil uji, tabel, dan grafik akan muncul di area ini."),
        Div(*[Span(f.upper(), cls="fmt-chip") for f in INF_FORMATS], cls="fmt-row"),
        Button(ICON_SVG("sparkles", 15), "Coba dengan Data Contoh",
               cls="btn btn-ghost btn-sm demo-btn",
               hx_get="/inferens/demo", hx_target="#workspace", hx_swap="innerHTML"),
        cls="empty-card anim-in",
    )


def _data_table_preview(df, nmax=200):
    head = Tr(Th("#", cls="idx-th"), *[Th(str(c), title=str(c)) for c in df.columns])
    body = []
    for i, (_, row) in enumerate(df.head(nmax).iterrows(), start=1):
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


def inf_tabs(sid, df):
    n_rows, n_cols = df.shape
    info = pd.DataFrame({
        "Tipe Data": df.dtypes.astype(str),
        "Data Terisi": df.notna().sum(),
        "Data Kosong": df.isna().sum(),
        "Jumlah Unik": df.nunique(),
    })
    desc = df.describe(include="all").T.round(3)
    btn = lambda key, lbl, ic, active: Button(
        ICON_SVG(ic, 15), lbl, cls=f"tab-btn{' active' if active else ''}",
        data_tab=key, type="button",
    )
    return Section(
        Div(
            btn("tab-prev", "Pratinjau Data", "eye", True),
            btn("tab-info", "Informasi Variabel", "list", False),
            btn("tab-desc", "Statistik Deskriptif", "chart", False),
            Div(
                A(ICON_SVG("download", 14), "Unduh Data (CSV)",
                  href=f"/inferens/dl-data/{sid}", cls="btn btn-ghost btn-sm",
                  download="data_dimuat.csv"),
                cls="tab-dl"),
            cls="tab-bar",
        ),
        Div(
            Div(_data_table_preview(df, 200), cls="table-wrap"),
            P(f"Menampilkan {min(200, n_rows)} dari {n_rows:,} baris \u00d7 {n_cols:,} kolom",
              cls="table-note"),
            cls="tab-panel active", data_panel="tab-prev",
        ),
        Div(Div(df_table(info), cls="table-wrap"), cls="tab-panel", data_panel="tab-info"),
        Div(Div(df_table(desc), cls="table-wrap"), cls="tab-panel", data_panel="tab-desc"),
        cls="card anim-in d1 tabs-card",
    )


def inf_picker(sid, df):
    parts = []
    for gkey, (gtitle, gicon) in GRUP.items():
        tiles = []
        for akey, meta in ANALISIS.items():
            if meta["grup"] != gkey:
                continue
            tiles.append(Button(
                Div(ICON_SVG(meta["ikon"], 19), cls="tile-ic"),
                Div(
                    Div(meta["judul"], cls="tile-title"),
                    Div(meta["desc"], cls="tile-desc"),
                ),
                Div(ICON_SVG("up", 14), cls="tile-arrow"),
                type="button",
                cls="a-tile",
                hx_get=f"/inferens/form/{sid}?a={akey}",
                hx_target="#inf-params", hx_swap="innerHTML",
            ))
        parts.append(Div(
            Div(ICON_SVG(gicon, 17), H3(gtitle), Span(f"{len(tiles)} analisis", cls="chip"),
                cls="sec-head"),
            Div(*tiles, cls="a-grid"),
            cls="a-group",
        ))
    return Section(
        Div(ICON_SVG("sliders", 17), H3("Pilih Analisis"),
            Span("20 analisis tersedia", cls="chip chip-cyan"),
            A(ICON_SVG("book", 13), "Teori & Kegunaan", href="/teori", cls="chip chip-link"),
            cls="sec-head"),
        P("Parameter setiap analisis menyesuaikan kolom data Anda secara otomatis. "
          "Klik salah satu kartu untuk membuka form konfigurasinya.", cls="picker-note"),
        *parts,
        cls="card anim-in d2 picker-card",
    )


def param_placeholder():
    return Div(
        Div(ICON_SVG("sliders", 26), cls="empty-ic empty-ic-sm"),
        H3("Konfigurasi Analisis"),
        P("Pilih salah satu kartu analisis di atas - form parameter dan tombol RUN "
          "akan muncul di sini."),
        cls="empty-card empty-compact anim-in",
        id="param-empty",
    )


def result_placeholder():
    return Div(
        P("Hasil analisis akan tampil di area ini setelah Anda menekan tombol RUN.",
          cls="result-hint"),
        id="inf-results-inner",
    )


def inf_workspace(sid, df, fname, size, sheets=None, sheet=None):
    n_rows, n_cols = df.shape
    nums = num_cols(df)
    cats = cat_cols(df)
    banner = Div(
        Div(ICON_SVG("check", 20), cls="banner-ic"),
        Div(
            B(fname),
            Span(f"{n_rows:,} baris \u00b7 {n_cols:,} kolom \u00b7 {size_str(size)}",
                 cls="banner-meta"),
            cls="banner-body",
        ),
        Button(ICON_SVG("reset", 15), "Ganti File", cls="btn btn-ghost btn-sm",
               hx_post="/inferens/reset", hx_target="#workspace", hx_swap="innerHTML"),
        cls="banner anim-in",
    )
    sheet_sel = None
    if sheets and len(sheets) > 1:
        opts = [Option(str(sh), value=str(sh), selected=(str(sh) == str(sheet or sheets[0])))
                for sh in sheets]
        sheet_sel = Div(
            Label("Pilih sheet Excel", cls="f-label"),
            Select(*opts, name="sheet", cls="inp inp-select inp-select-sm",
                   hx_post="/inferens/sheet", hx_trigger="change",
                   hx_target="#workspace", hx_swap="innerHTML",
                   hx_include="closest div", hx_indicator="#sheet-loading"),
            Input(type="hidden", name="sid", value=sid),
            Div(Span(cls="spinner spinner-sm"), "Memuat sheet...",
                id="sheet-loading", cls="spinner-inline htmx-indicator"),
            cls="sheet-row",
        )
    chips = Div(
        Span(f"{len(nums)} kolom numerik", cls="chip"),
        Span(f"{len(cats)} kolom kategorik", cls="chip chip-cyan"),
        Span("\u03b1 dapat diatur per analisis", cls="chip chip-pink"),
        cls="chip-row",
    )
    parts = [banner]
    if sheet_sel is not None:
        parts.append(Div(sheet_sel, cls="sheet-wrap"))
    parts.append(chips)
    parts.append(inf_tabs(sid, df))
    parts.append(inf_picker(sid, df))
    parts.append(Div(param_placeholder(), id="inf-params"))
    parts.append(Div(result_placeholder(), id="inf-results"))
    return Div(*parts, cls="ws-root")


def test_card(label, stat, pv, alpha):
    sig = pd.notna(pv) and float(pv) < alpha
    cls = "test-ok" if sig else "test-no"
    keputusan = (f"Tolak H\u2080 (signifikan pada \u03b1 = {alpha:g})" if sig
                 else f"Gagal Tolak H\u2080 (tidak signifikan pada \u03b1 = {alpha:g})")
    stat_txt = fmt_stat(stat) if isinstance(stat, (int, float, np.integer, np.floating)) else str(stat)
    return Div(
        Div(ICON_SVG("check" if sig else "info", 18), cls="test-ic"),
        Div(
            B(label),
            P(Span(f"Statistik = {stat_txt}", cls="test-val"),
              Span(f"p-value = {fmt_p(pv)}", cls="test-val"),
              Span("\u2192 " + keputusan, cls="test-dec")),
            cls="test-body",
        ),
        cls=f"test-card {cls} anim-in",
    )


def narasi_card(paras):
    """Kartu narasi analisis otomatis — interpretasi siap salin ke laporan."""
    return Div(
        Div(
            Div(ICON_SVG("chat", 17), cls="narasi-ic"),
            Div(
                Div("Narasi Analisis", cls="narasi-title"),
                Div("Interpretasi otomatis atas seluruh hasil perhitungan di bawah — siap disalin ke laporan.",
                    cls="narasi-sub"),
            ),
            Button(ICON_SVG("list", 13), "Salin Narasi", type="button",
                   cls="narasi-copy", data_copy_narasi="1"),
            cls="narasi-head",
        ),
        Div(*[P(p, cls="narasi-p") for p in paras], cls="narasi-body"),
        cls="narasi-card anim-in",
    )


def render_hasil(sid, akey, h: Hasil, alpha):
    meta = ANALISIS[akey]
    paras = buat_narasi(akey, h, alpha)
    parts = [
        Div(
            Div(ICON_SVG(meta["ikon"], 20), cls="res-head-ic"),
            Div(
                Div(H3(f"Hasil \u2014 {meta['judul']}"), cls="res-head-title"),
                Span(f"\u03b1 = {alpha:g}", cls="chip chip-pink"),
                Span("siap dilaporkan", cls="chip"),
                cls="res-head",
            ),
            cls="res-head-row anim-in",
        )
    ]
    if paras:
        parts.append(narasi_card(paras))
    if h.metrics:
        parts.append(Div(*[
            Div(
                Div(ICON_SVG(ic, 15), cls="metric-ic"),
                Span(lbl, cls="metric-label"),
                Div(val, cls="metric-val"),
                cls="metric-card",
            ) for lbl, val, ic in h.metrics
        ], cls="metrics-grid anim-in"))
    if h.tests:
        parts.append(Div(*[test_card(lbl, st, pv, al) for lbl, st, pv, al in h.tests],
                         cls="tests-stack"))
    for w in h.warnings:
        parts.append(Div(
            Div(ICON_SVG("alert", 18), cls="warn-ic"),
            Div(B("Perhatian"), P(w), cls="err-body"),
            cls="card warn-card anim-in"))
    for judul, tbl, note in h.tables:
        sec_children = [Div(ICON_SVG("grid", 16), H3(judul), cls="sec-head"),
                        Div(df_table(tbl), cls="table-wrap")]
        if note:
            sec_children.append(P(note, cls="table-note"))
        parts.append(Section(*sec_children, cls="card anim-in"))
    for judul, teks in h.summaries:
        parts.append(Section(
            Div(ICON_SVG("list", 16), H3(judul), cls="sec-head"),
            Pre(teks, cls="summary-pre"),
            cls="card anim-in"))
    if h.charts:
        cparts = []
        for judul, png in h.charts:
            cparts.append(Div(
                Div(ICON_SVG("chart", 16), H3(judul), cls="sec-head"),
                img_tag(png, judul, judul),
                cls="chart-card",
            ))
        parts.append(Div(*cparts, cls="chart-grid anim-in"))
    if h.notes:
        parts.append(Div(*[P(ICON_SVG("info", 13), " " + n, cls="note-row") for n in h.notes],
                         cls="notes-stack"))
    if h.downloads:
        dl = []
        for lbl, fname, key, _df in h.downloads:
            INF_SESSIONS.setdefault(sid, {}).setdefault("dl", {})[key] = (fname, _df)
            dl.append(A(ICON_SVG("download", 15), lbl,
                        href=f"/inferens/dl/{sid}/{key}", cls="btn btn-success btn-sm",
                        download=fname))
        parts.append(Div(*dl, cls="dl-row anim-in"))
    return Div(*parts, cls="res-root")


# ==========================================================
# SESI
# ==========================================================
def _prune_inf():
    while len(INF_SESSIONS) > MAX_INF_SESSIONS:
        oldest = next(iter(INF_SESSIONS))
        INF_SESSIONS.pop(oldest, None)


# ==========================================================
# ROUTES
# ==========================================================
def setup(rt):
    @rt("/inferens")
    def get():
        return (
            Title("AseliPedas - Statistik Inferensial"),
            inf_nav(),
            Main(
                inf_hero(),
                Div(
                    Form(
                        inf_upload_section(),
                        id="upload-form",
                        hx_post="/inferens/upload", hx_target="#workspace", hx_swap="innerHTML",
                        hx_encoding="multipart/form-data",
                    ),
                    Div(inf_empty(), id="workspace"),
                    cls="wrap",
                ),
                inf_footer(),
                Script(src="/js/inferens.js"),
            ),
        )

    @rt("/inferens/upload")
    async def post(req: Request):
        try:
            form = await req.form()
            up = form.get("file")
            fname = getattr(up, "filename", "") or ""
            if not fname:
                return inf_error_fragment("Tidak ada file yang dipilih. Silakan pilih file terlebih dahulu.")
            data = await up.read()
            ext = os.path.splitext(fname)[1].lower().lstrip(".")
            if ext not in INF_FORMATS:
                return inf_error_fragment(
                    f"Format .{ext or '(tanpa ekstensi)'} belum didukung. "
                    f"Gunakan: {', '.join(f.upper() for f in INF_FORMATS)}.")
            df = load_data_inf(data, fname)
            if df.shape[0] == 0:
                return inf_error_fragment("File berhasil dibaca tetapi tidak berisi satu baris data pun.")
            autoconv = form.get("autoconv") in ("on", "1", "true", True)
            if autoconv:
                df = konversi_numerik(df)
            sid = uuid.uuid4().hex[:10]
            sheets = None
            if ext in ("xls", "xlsx", "xlsm"):
                sheets = excel_sheets(data)
            INF_SESSIONS[sid] = {
                "df": df, "name": fname, "size": len(data), "autoconv": autoconv,
                "raw": data if (sheets and len(sheets) > 1) else None,
                "sheets": sheets, "sheet": sheets[0] if sheets else None, "dl": {},
            }
            _prune_inf()
            return inf_workspace(sid, df, fname, len(data),
                                 sheets=sheets, sheet=sheets[0] if sheets else None)
        except Exception as e:
            return inf_error_fragment(f"Gagal membaca file: {e}")

    @rt("/inferens/sheet")
    async def post(req: Request):
        form = await req.form()
        sid = str(form.get("sid") or "")
        sheet = str(form.get("sheet") or "")
        s = INF_SESSIONS.get(sid)
        if not s or not s.get("raw"):
            return inf_error_fragment("Sesi tidak ditemukan atau file bukan Excel multi-sheet.")
        try:
            df = pd.read_excel(io.BytesIO(s["raw"]), sheet_name=sheet)
            if s.get("autoconv"):
                df = konversi_numerik(df)
            s["df"] = df
            s["sheet"] = sheet
            return inf_workspace(sid, df, s["name"], s["size"],
                                 sheets=s["sheets"], sheet=sheet)
        except Exception as e:
            return inf_error_fragment(f"Gagal membaca sheet: {e}")

    @rt("/inferens/demo")
    def get():
        df = buat_data_contoh()
        sid = uuid.uuid4().hex[:10]
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        INF_SESSIONS[sid] = {"df": df, "name": "data_contoh.csv", "size": len(csv_bytes),
                             "autoconv": True, "raw": None, "sheets": None,
                             "sheet": None, "dl": {}}
        _prune_inf()
        return inf_workspace(sid, df, "data_contoh.csv", len(csv_bytes))

    @rt("/inferens/reset")
    def post():
        return inf_empty()

    @rt("/inferens/form/{sid}")
    def get(sid: str, req: Request):
        s = INF_SESSIONS.get(sid)
        if not s:
            return inf_error_fragment("Sesi data tidak ditemukan. Silakan unggah ulang file.")
        qp = req.query_params
        akey = str(qp.get("a") or "")
        meta = ANALISIS.get(akey)
        if not meta:
            return inf_error_fragment("Analisis tidak dikenal.")
        cur = {k: qp.getlist(k) for k in qp.keys()}
        cur["__form_url__"] = f"/inferens/form/{sid}?a={akey}"
        df = s["df"]
        try:
            fields = meta["form"](df, cur)
        except Exception as e:
            return inf_error_fragment(f"Gagal menyiapkan form: {e}")
        alpha_seg = f_seg("alpha", "Taraf signifikansi (α)",
                          [("0.1", "α = 0.10"), ("0.05", "α = 0.05"), ("0.01", "α = 0.01")],
                          cur, default="0.05")
        alpha_seg.attrs.pop("name", None)
        return Section(
            Div(
                Div(ICON_SVG(meta["ikon"], 18), cls="param-head-ic"),
                Div(H3(meta["judul"]), cls="param-title"),
                Span(GRUP[meta["grup"]][0], cls="chip chip-cyan"),
                cls="sec-head param-head",
            ),
            Form(
                Div(*fields, cls="param-grid"),
                Div(alpha_seg, cls="field field-wide alpha-field"),
                Div(
                    Button(ICON_SVG("zap", 16), "RUN ANALISIS", type="submit",
                           cls="btn btn-primary btn-lg"),
                    Div(Span(cls="spinner spinner-sm"),
                        "Menghitung... analisis multivariat dapat memakan beberapa detik.",
                        id="run-loading", cls="spinner-inline htmx-indicator"),
                    cls="run-row",
                ),
                hx_post=f"/inferens/run/{sid}?a={akey}",
                hx_target="#inf-results", hx_swap="innerHTML",
                hx_indicator="#run-loading",
            ),
            cls="card anim-in param-card",
            id="inf-params-card",
        )

    @rt("/inferens/run/{sid}")
    async def post(sid: str, req: Request):
        s = INF_SESSIONS.get(sid)
        if not s:
            return inf_error_fragment("Sesi data tidak ditemukan. Silakan unggah ulang file.")
        qp = req.query_params
        akey = str(qp.get("a") or "")
        meta = ANALISIS.get(akey)
        if not meta:
            return inf_error_fragment("Analisis tidak dikenal.")
        form = await req.form()
        MULTI_KEYS = {"xs", "cols", "ys", "covs", "dua"}
        multi_keys = set()
        single_keys = set()
        for k in form.keys():
            vals = form.getlist(k)
            if len(vals) > 1:
                multi_keys.add(k)
            else:
                single_keys.add(k)
        p = {}
        for k in multi_keys:
            p[k] = [str(v) for v in form.getlist(k)]
        for k in single_keys:
            v = form.get(k)
            if k in MULTI_KEYS:
                p[k] = [str(v)] if v is not None else []
            else:
                p[k] = "on" if v == "on" else str(v)
        try:
            alpha = float(p.get("alpha", "0.05") or 0.05)
        except ValueError:
            alpha = 0.05
        try:
            h = meta["run"](s["df"], p, alpha)
        except Exception as e:
            return hasil_error(e)
        return render_hasil(sid, akey, h, alpha)

    @rt("/inferens/dl-data/{sid}")
    def get(sid: str):
        s = INF_SESSIONS.get(sid)
        if not s:
            return Response("Sesi tidak ditemukan. Silakan unggah ulang file.",
                            status_code=404, media_type="text/plain")
        csv_bytes = s["df"].to_csv(index=False).encode("utf-8")
        return Response(csv_bytes, media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="data_dimuat.csv"'})

    @rt("/inferens/dl/{sid}/{key}")
    def get(sid: str, key: str):
        s = INF_SESSIONS.get(sid)
        if not s:
            return Response("Sesi tidak ditemukan. Silakan unggah ulang file.",
                            status_code=404, media_type="text/plain")
        item = s.get("dl", {}).get(key)
        if not item:
            return Response("Berkas unduhan tidak ditemukan atau telah kedaluwarsa.",
                            status_code=404, media_type="text/plain")
        fname, df = item
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        safe = os.path.basename(fname)
        return Response(csv_bytes, media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{safe}"'})


# ==========================================================
# NAV & FOOTER SHARED (dirakit dari app.py agar konsisten)
# ==========================================================
def inf_nav():
    """Navigasi halaman inferens - dipanggil dari setup()."""
    return _NAV_FACTORY("/inferens")


def inf_footer():
    return _FOOTER_FACTORY()


_NAV_FACTORY = None
_FOOTER_FACTORY = None


def register_shared(nav_factory, footer_factory):
    global _NAV_FACTORY, _FOOTER_FACTORY
    _NAV_FACTORY = nav_factory
    _FOOTER_FACTORY = footer_factory
