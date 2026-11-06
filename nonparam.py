# -*- coding: utf-8 -*-
"""
AseliPedas - Halaman STATISTIK NON-PARAMETRIK (FastHTML Edition)
==============================================================
Halaman pengolahan uji non-parametrik dengan alur yang sama dengan halaman
Statistik Inferens: unggah data -> pilih uji -> isi parameter -> RUN ->
hasil (angka, tabel, grafik) + narasi analisis otomatis.

12 uji tersedia dalam 4 kelompok:
  1. Uji Normalitas & Homogenitas : Shapiro-Wilk, Kolmogorov-Smirnov, Levene
  2. Uji Beda                     : Mann-Whitney U, Wilcoxon, Kruskal-Wallis, Friedman
  3. Uji Frekuensi & Keacakan     : Chi-Square GOF, McNemar, Runs
  4. Korelasi Non-Parametrik      : Spearman, Kendall Tau

Keunggulan halaman ini: setiap uji dilengkapi kartu "Tentang Uji Ini" yang
menerangkan kegunaan uji beserta contoh penggunaannya dalam kehidupan
sehari-hari, langsung pada form parameter.

Modul ini di-register dari app.py lewat nonparam.setup(rt).
"""
import io
import os
import uuid

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.contingency_tables import mcnemar as sm_mcnemar
from statsmodels.stats.diagnostic import lilliefors

from inferens import (  # pola, tema grafik, dan util dibagi dengan halaman inferens
    ICONS, ICON_SVG, Hasil, hasil_error, inf_error_fragment, test_card, narasi_card,
    fmt_stat, fmt_p, size_str, persiapkan, konversi_numerik, num_cols, cat_cols, _aslist,
    df_table, f_select, f_multi, f_seg, f_field,
    fig_png, img_tag, legend_style,
    load_data_inf, excel_sheets, buat_data_contoh, plt,
    PAL, EDGE, BG,
)

# Ikon tambahan khusus halaman non-parametrik (didaftarkan ke dict bersama agar
# ICON_SVG dari inferens dapat memakainya).
ICONS.setdefault("bulb", (
    '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5 '
    '.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>'))
from matplotlib.colors import LinearSegmentedColormap
from fasthtml.common import (
    Div, Section, Main, H1, H3, P, Span, B, Button, Input, Select, Option, Label,
    Form, A, Title, Script, Ul, Li, Table, Thead, Tbody, Tr, Th, Td, Pre, NotStr,
)
from starlette.requests import Request
from starlette.responses import Response

from narasi_np import buat_narasi_np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NP_FORMATS = ["csv", "xls", "xlsx", "xlsm", "sav", "dta", "dbf", "json",
              "txt", "tsv", "dat", "parquet", "pkl"]
NP_ACCEPT = ",".join(f".{e}" for e in NP_FORMATS)
NP_SESSIONS = {}
MAX_NP_SESSIONS = 6


# ==========================================================
# HELPER GRAFIK (tema gelap selaras seluruh aplikasi)
# ==========================================================
def _new_fig(h=4.2, w=7.6):
    fig, ax = plt.subplots(figsize=(w, h))
    return fig, ax


def _chart_hist_normal(data, judul, xlabel, bins=20):
    """Histogram + kurva normal overlay (uji normalitas)."""
    fig, ax = _new_fig()
    ax.hist(data, bins=bins, density=True, color=PAL[0], alpha=.78, edgecolor=EDGE)
    try:
        mu, sd = float(np.mean(data)), float(np.std(data, ddof=1))
        xs = np.linspace(float(np.min(data)), float(np.max(data)), 260)
        ax.plot(xs, stats.norm.pdf(xs, mu, sd), color=PAL[1], lw=2.3,
                label=f"Normal (\u03bc = {fmt_stat(mu)}, \u03c3 = {fmt_stat(sd)})")
        legend_style(ax)
    except (ValueError, ZeroDivisionError, FloatingPointError):
        pass
    ax.set_title(judul)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Kepadatan")
    return fig


def _chart_box(groups, labels, judul, ylabel):
    """Boxplot per kelompok (Levene, Mann-Whitney, Kruskal-Wallis)."""
    fig, ax = _new_fig()
    bp = ax.boxplot(groups, positions=range(1, len(groups) + 1), patch_artist=True,
                    widths=.52, medianprops=dict(color="#0B1322", lw=2),
                    whiskerprops=dict(color=EDGE), capprops=dict(color=EDGE),
                    flierprops=dict(markerfacecolor=PAL[8], markersize=4, alpha=.7))
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(PAL[i % len(PAL)])
        patch.set_alpha(.7)
        patch.set_edgecolor(EDGE)
    ax.set_xticks(range(1, len(groups) + 1))
    ax.set_xticklabels([str(l) for l in labels])
    ax.set_title(judul)
    ax.set_ylabel(ylabel)
    return fig


def _chart_paired(sub, v1, v2, judul):
    """Garis berpasangan sebelum-sesudah (Wilcoxon)."""
    fig, ax = _new_fig(4.6)
    show = sub.head(60)
    for _, r in show.iterrows():
        naik = r[v2] >= r[v1]
        ax.plot([0, 1], [r[v1], r[v2]], color=PAL[1] if naik else PAL[8],
                alpha=.4, lw=1.3)
    med1, med2 = float(sub[v1].median()), float(sub[v2].median())
    ax.plot([0, 1], [med1, med2], color=PAL[3], lw=3.4, marker="o", markersize=8,
            label="Median", zorder=5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([v1, v2])
    ax.set_xlim(-.3, 1.3)
    ax.set_title(judul)
    ax.set_ylabel("Nilai")
    legend_style(ax)
    return fig


def _chart_medians(meds, judul, ylabel):
    """Bar median per kondisi (Friedman)."""
    fig, ax = _new_fig(4.2)
    labels = [str(i) for i in meds.index]
    ax.bar(range(len(meds)), meds.values, color=PAL[:len(meds)], alpha=.85, edgecolor=EDGE)
    ax.set_xticks(range(len(meds)))
    ax.set_xticklabels(labels, rotation=20 if max(len(l) for l in labels) > 8 else 0)
    for i, v in enumerate(meds.values):
        ax.text(i, v, fmt_stat(v), ha="center", va="bottom", fontsize=9, color="#E7EBF4")
    ax.set_title(judul)
    ax.set_ylabel(ylabel)
    return fig


def _chart_runs(data, med, judul):
    """Urutan data + garis median, titik diwarnai per sisi median (Runs)."""
    fig, ax = _new_fig(4.2)
    xs = np.arange(1, len(data) + 1)
    vals = data.values.astype(float)
    atas = vals > med
    ax.plot(xs, vals, color=PAL[7], lw=1.1, alpha=.75, zorder=2)
    ax.scatter(xs[atas], vals[atas], color=PAL[1], s=26, label="Di atas median", zorder=3)
    ax.scatter(xs[~atas], vals[~atas], color=PAL[8], s=26, label="Di bawah median", zorder=3)
    ax.axhline(med, color=PAL[3], lw=1.9, ls="--", label=f"Median = {fmt_stat(med)}")
    ax.set_xlabel("Urutan observasi")
    ax.set_ylabel("Nilai")
    ax.set_title(judul)
    legend_style(ax)
    return fig


def _chart_grouped_counts(cnt1, cnt2, lv1, lv2, judul, lbl1, lbl2):
    """Bar frekuensi dua pengukuran berpasangan (McNemar)."""
    fig, ax = _new_fig(4.2)
    x = np.arange(2)
    w = .34
    o1 = [int(cnt1.get(l, 0)) for l in [lv1, lv2]]
    o2 = [int(cnt2.get(l, 0)) for l in [lv1, lv2]]
    ax.bar(x - w / 2, o1, w, color=PAL[0], alpha=.85, edgecolor=EDGE, label=lbl1)
    ax.bar(x + w / 2, o2, w, color=PAL[3], alpha=.85, edgecolor=EDGE, label=lbl2)
    for xi, v in zip(x - w / 2, o1):
        ax.text(xi, v, str(v), ha="center", va="bottom", fontsize=9.5, color="#E7EBF4")
    for xi, v in zip(x + w / 2, o2):
        ax.text(xi, v, str(v), ha="center", va="bottom", fontsize=9.5, color="#E7EBF4")
    ax.set_xticks(x)
    ax.set_xticklabels([lv1, lv2])
    ax.set_ylabel("Frekuensi")
    ax.set_title(judul)
    legend_style(ax)
    return fig


def _chart_gof(obs, exp_val, labels, judul):
    """Bar observasi + garis ekspektasi seragam (GOF)."""
    fig, ax = _new_fig(4.4)
    xs = np.arange(len(obs))
    ax.bar(xs, obs, color=PAL[0], alpha=.85, edgecolor=EDGE, label="Observasi")
    ax.axhline(exp_val, color=PAL[3], ls="--", lw=2.2,
               label=f"Ekspektasi seragam = {fmt_stat(exp_val)}")
    ax.set_xticks(xs)
    ax.set_xticklabels([str(l) for l in labels],
                       rotation=25 if max(len(str(l)) for l in labels) > 7 else 0)
    ax.set_ylabel("Frekuensi")
    ax.set_title(judul)
    legend_style(ax)
    return fig


CMAP_NP = LinearSegmentedColormap.from_list("npdiv", ["#F472B6", "#0B1322", "#34D399"])


def _chart_heatmap(rho, labels, judul):
    """Heatmap korelasi peringkat (Spearman)."""
    n = len(labels)
    fig, ax = _new_fig(h=5.2, w=6.4)
    im = ax.imshow(rho.values, vmin=-1, vmax=1, cmap=CMAP_NP)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    short = [str(l)[:14] for l in labels]
    ax.set_xticklabels(short, rotation=30, ha="right")
    ax.set_yticklabels(short)
    ax.grid(False)
    for i in range(n):
        for j in range(n):
            v = float(rho.values[i, j])
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8.6,
                    color="#E7EBF4" if abs(v) < .65 else "#0B1322")
    fig.colorbar(im, ax=ax, shrink=.8, label="rho")
    ax.set_title(judul)
    return fig


def _chart_scatter(x, y, judul, xlabel, ylabel):
    """Scatter dua variabel (Kendall)."""
    fig, ax = _new_fig(4.4)
    ax.scatter(x, y, s=30, color=PAL[0], alpha=.7, edgecolor=EDGE)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(judul)
    return fig


# ==========================================================
# FORM PARAMETER 12 UJI
# ==========================================================
def _np_shapiro_form(df, cur):
    nums = num_cols(df)
    return [f_select("y", "Variabel yang diuji (numerik)", nums, cur,
                     hint="Uji normalitas dijalankan pada satu kolom numerik.")]


def _np_ks_form(df, cur):
    nums = num_cols(df)
    return [f_select("y", "Variabel yang diuji (numerik)", nums, cur,
                     hint="Gunakan untuk sampel n > 50; Shapiro-Wilk untuk sampel kecil.")]


def _np_levene_form(df, cur):
    nums, cats = num_cols(df), cat_cols(df)
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in nums else (nums[0] if nums else "")
    g_sel = (cur.get("g") or [None])[0]
    g_sel = g_sel if g_sel in cats else (cats[0] if cats else "")
    return [
        f_select("y", "Variabel (numerik)", nums, cur, default=y_sel),
        f_select("g", "Faktor kelompok (kategorik)", cats, cur, default=g_sel,
                 hint="Varians dibandingkan antar level faktor ini."),
    ]


def _np_mwu_form(df, cur):
    nums, cats = num_cols(df), cat_cols(df)
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in nums else (nums[0] if nums else "")
    g_sel = (cur.get("g") or [None])[0]
    g_sel = g_sel if g_sel in cats else (cats[0] if cats else "")
    lv = sorted(df[g_sel].dropna().astype(str).unique()) if g_sel else []
    dua_def = (cur.get("dua") or None) or lv[:2]
    return [
        f_select("y", "Variabel (numerik)", nums, cur, default=y_sel),
        f_select("g", "Variabel kelompok (kategorik)", cats, cur, default=g_sel),
        f_multi("dua", "Pilih tepat 2 kelompok", lv, cur, dua_def),
    ]


def _np_wilcoxon_form(df, cur):
    nums = num_cols(df)
    v1_sel = (cur.get("v1") or [None])[0]
    v1_sel = v1_sel if v1_sel in nums else (nums[0] if nums else "")
    v2_opts = [c for c in nums if c != v1_sel]
    v2_sel = (cur.get("v2") or [None])[0]
    v2_sel = v2_sel if v2_sel in v2_opts else (v2_opts[0] if v2_opts else "")
    return [
        f_select("v1", "Pengukuran 1 (sebelum)", nums, cur, default=v1_sel),
        f_select("v2", "Pengukuran 2 (sesudah)", v2_opts, cur, default=v2_sel,
                 hint="Kedua kolom harus diukur pada subjek yang sama."),
    ]


def _np_kruskal_form(df, cur):
    nums, cats = num_cols(df), cat_cols(df)
    y_sel = (cur.get("y") or [None])[0]
    y_sel = y_sel if y_sel in nums else (nums[0] if nums else "")
    g_sel = (cur.get("g") or [None])[0]
    g_sel = g_sel if g_sel in cats else (cats[0] if cats else "")
    return [
        f_select("y", "Variabel Dependen (numerik)", nums, cur, default=y_sel),
        f_select("g", "Faktor (kategori, \u2265 3 level)", cats, cur, default=g_sel),
    ]


def _np_friedman_form(df, cur):
    nums = num_cols(df)
    cols_def = (cur.get("cols") or None) or nums[:3]
    return [f_multi("cols", "Pilih \u2265 3 kondisi/pengukuran", nums, cur, cols_def,
                    "Setiap baris = subjek yang sama, tiap kolom = satu kondisi.")]


def _np_gof_form(df, cur):
    cats = cat_cols(df)
    v_sel = (cur.get("v") or [None])[0]
    v_sel = v_sel if v_sel in cats else (cats[0] if cats else "")
    return [f_select("v", "Variabel kategorik", cats, cur, default=v_sel,
                     hint="Uji membandingkan frekuensi kategori dengan pola seragam.")]


def _np_mcnemar_form(df, cur):
    cats = cat_cols(df)
    v1_sel = (cur.get("v1") or [None])[0]
    v1_sel = v1_sel if v1_sel in cats else (cats[0] if cats else "")
    v2_opts = [c for c in cats if c != v1_sel]
    v2_sel = (cur.get("v2") or [None])[0]
    v2_sel = v2_sel if v2_sel in v2_opts else (v2_opts[0] if v2_opts else "")
    return [
        f_select("v1", "Kondisi 1 (sebelum) - biner", cats, cur, default=v1_sel),
        f_select("v2", "Kondisi 2 (sesudah) - biner", v2_opts, cur, default=v2_sel,
                 hint="Kedua kolom harus biner (2 kategori) dan diukur pada subjek yang sama."),
    ]


def _np_runs_form(df, cur):
    nums = num_cols(df)
    return [f_select("y", "Variabel (numerik, urutan baris = urutan waktu)", nums, cur,
                     hint="Urutan baris pada data dianggap urutan kemunculan aktual.")]


def _np_spearman_form(df, cur):
    nums = num_cols(df)
    cols_def = (cur.get("cols") or None) or nums[:6]
    return [f_multi("cols", "Pilih \u2265 2 variabel", nums, cur, cols_def,
                    "Semua pasangan antar kolom terpilih dikorelasikan.")]


def _np_kendall_form(df, cur):
    nums = num_cols(df)
    v1_sel = (cur.get("v1") or [None])[0]
    v1_sel = v1_sel if v1_sel in nums else (nums[0] if nums else "")
    v2_opts = [c for c in nums if c != v1_sel]
    v2_sel = (cur.get("v2") or [None])[0]
    v2_sel = v2_sel if v2_sel in v2_opts else (v2_opts[0] if v2_opts else "")
    return [
        f_select("v1", "Variabel 1", nums, cur, default=v1_sel),
        f_select("v2", "Variabel 2", v2_opts, cur, default=v2_sel),
    ]


# ==========================================================
# RUN 12 UJI
# ==========================================================
def _np_shapiro_run(df, p, alpha):
    y = p["y"]
    data = pd.to_numeric(df[y], errors="coerce").dropna()
    if len(data) < 3:
        raise ValueError("Shapiro-Wilk membutuhkan minimal 3 data valid.")
    if len(data) > 5000:
        pass  # peringatan ditambahkan setelah perhitungan
    w, pv = stats.shapiro(data)
    n = len(data)

    h = Hasil()
    h.metric("n Data", f"{n:,}", "database")
    h.metric("Mean", fmt_stat(data.mean()), "sigma")
    h.metric("Median", fmt_stat(data.median()), "list")
    h.metric("Std Deviasi", fmt_stat(data.std(ddof=1)), "activity")
    h.tabel("Hasil Uji Shapiro-Wilk", pd.DataFrame(
        {"Nilai": [n, w, pv]},
        index=["n", "W (statistik uji)", "p-value"]).round(4))
    h.uji("Shapiro-Wilk W", w, pv, alpha)
    skew, kurt = float(data.skew()), float(data.kurtosis())
    h.notes.append(f"Skewness = {skew:.3f} ({'relatif simetris' if abs(skew) < .5 else 'menceng'}), "
                   f"Kurtosis = {kurt:.3f} - pelengkap pembacaan bentuk distribusi.")
    if n > 5000:
        h.warnings.append(
            "n > 5000: p-value Shapiro-Wilk dapat kurang akurat pada sampel sangat besar; "
            "pertimbangkan juga Uji Kolmogorov-Smirnov Lilliefors dan periksa histogram.")
    h.grafik("Histogram + Kurva Normal", _chart_hist_normal(
        data, f"Distribusi {y} terhadap kurva normal", y))
    return h


def _np_ks_run(df, p, alpha):
    y = p["y"]
    data = pd.to_numeric(df[y], errors="coerce").dropna()
    if len(data) < 5:
        raise ValueError("Uji Kolmogorov-Smirnov membutuhkan minimal 5 data valid.")
    stat, pv = lilliefors(data, dist="norm")
    n = len(data)

    h = Hasil()
    h.metric("n Data", f"{n:,}", "database")
    h.metric("Mean", fmt_stat(data.mean()), "sigma")
    h.metric("Median", fmt_stat(data.median()), "list")
    h.metric("Std Deviasi", fmt_stat(data.std(ddof=1)), "activity")
    h.tabel("Hasil Uji Kolmogorov-Smirnov (Lilliefors)", pd.DataFrame(
        {"Nilai": [n, stat, pv]},
        index=["n", "L (jarak maksimum CDF)", "p-value"]).round(4))
    h.uji("Kolmogorov-Smirnov L", stat, pv, alpha)
    h.notes.append("Koreksi Lilliefors dipakai karena parameter normal (\u03bc, \u03c3) diestimasi dari data, "
                   "sehingga hasil lebih konservatif dan tepat daripada KS klasik.")
    h.grafik("Histogram + Kurva Normal", _chart_hist_normal(
        data, f"Distribusi {y} terhadap kurva normal", y))
    return h


def _np_levene_run(df, p, alpha):
    y, g = p["y"], p["g"]
    data = persiapkan(df, [y, g])
    data.columns = ["Y", "G"]
    groups = [gg["Y"].values for _, gg in data.groupby("G")]
    if len(groups) < 2:
        raise ValueError("Uji Levene membutuhkan minimal 2 kelompok.")
    if min(len(x) for x in groups) < 2:
        raise ValueError("Setiap kelompok harus memiliki minimal 2 observasi.")
    w, pv = stats.levene(*groups, center="median")
    profil = data.groupby("G")["Y"].agg(n="count", mean="mean", std="std")
    profil["varians"] = data.groupby("G")["Y"].var()

    h = Hasil()
    h.tabel("Statistik per Kelompok", profil.round(3))
    h.tabel("Hasil Uji Levene", pd.DataFrame(
        {"Nilai": [w, pv]},
        index=["W (statistik uji)", "p-value"]).round(4))
    h.uji("Levene W", w, pv, alpha)
    h.grafik("Boxplot per Kelompok", _chart_box(
        groups, profil.index.tolist(), f"Sebaran {y} per kelompok ({g})", y))
    return h


def _np_mwu_run(df, p, alpha):
    y, g, dua = p["y"], p["g"], _aslist(p.get("dua", []))
    if len(dua) != 2:
        raise ValueError("Pilih tepat 2 kelompok untuk Uji Mann-Whitney U.")
    data = persiapkan(df, [y, g])
    data.columns = ["Y", "G"]
    data["G"] = data["G"].astype(str)
    a = data.loc[data.G == dua[0], "Y"]
    b = data.loc[data.G == dua[1], "Y"]
    if len(a) == 0 or len(b) == 0:
        raise ValueError("Salah satu kelompok tidak memiliki data valid.")
    u, pv = stats.mannwhitneyu(a, b, alternative="two-sided")
    n1, n2 = len(a), len(b)
    mu_u = n1 * n2 / 2
    sd_u = np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z = (u - mu_u) / sd_u
    r = abs(z) / np.sqrt(n1 + n2)

    h = Hasil()
    h.metric("n Kelompok 1", f"{n1:,}", "database")
    h.metric("n Kelompok 2", f"{n2:,}", "database")
    h.metric("Median 1", fmt_stat(a.median()), "list")
    h.metric("Median 2", fmt_stat(b.median()), "list")
    h.tabel("Statistik Kelompok", pd.DataFrame(
        {"n": [n1, n2], "Median": [a.median(), b.median()],
         "Mean": [a.mean(), b.mean()], "Mean Rank approx": [mu_u / n2, mu_u / n1]},
        index=list(dua)).round(3))
    h.tabel("Hasil Uji Mann-Whitney U", pd.DataFrame(
        {"Nilai": [u, z, pv, r]},
        index=["U", "Z", "p-value", "r (ukuran efek)"]).round(4))
    h.uji("Mann-Whitney U", u, pv, alpha)
    h.grafik("Boxplot per Kelompok", _chart_box(
        [a.values, b.values], list(dua), f"Sebaran {y} antara {dua[0]} dan {dua[1]}", y))
    return h


def _np_wilcoxon_run(df, p, alpha):
    v1, v2 = p["v1"], p["v2"]
    sub = df[[v1, v2]].dropna()
    sub = sub.apply(pd.to_numeric, errors="coerce").dropna()
    if len(sub) < 6:
        raise ValueError("Uji Wilcoxon membutuhkan minimal 6 pasangan data valid.")
    if np.allclose(sub[v1], sub[v2]):
        raise ValueError("Semua selisih bernilai nol; Wilcoxon signed-rank tidak dapat dijalankan.")
    w, pv = stats.wilcoxon(sub[v1], sub[v2])
    d = (sub[v1] - sub[v2])
    d = d[d != 0]
    n = len(d)
    z = (w - n * (n + 1) / 4) / np.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    r = abs(z) / np.sqrt(n)

    h = Hasil()
    h.metric("n Pasangan", f"{len(sub):,}", "database")
    h.metric("Median Sebelum", fmt_stat(sub[v1].median()), "list")
    h.metric("Median Sesudah", fmt_stat(sub[v2].median()), "list")
    h.metric("Rata-rata Selisih", fmt_stat((sub[v1] - sub[v2]).mean()), "sigma")
    h.tabel("Hasil Uji Wilcoxon Signed-Rank", pd.DataFrame(
        {"Nilai": [len(sub), n, sub[v1].median(), sub[v2].median(), w, z, pv, r]},
        index=["n (pasangan)", "n (selisih \u2260 0)", f"Median {v1}", f"Median {v2}",
               "W", "Z", "p-value", "r (ukuran efek)"]).round(4))
    h.uji("Wilcoxon Signed-Rank", w, pv, alpha)
    h.grafik("Perubahan Sebelum \u2192 Sesudah", _chart_paired(
        sub, v1, v2, f"Perubahan {v1} menuju {v2} (maks. 60 pasangan)"))
    return h


def _np_kruskal_run(df, p, alpha):
    y, g = p["y"], p["g"]
    data = persiapkan(df, [y, g])
    data.columns = ["Y", "G"]
    groups = [gg["Y"].values for _, gg in data.groupby("G")]
    if len(groups) < 3:
        raise ValueError("Uji Kruskal-Wallis membutuhkan minimal 3 kelompok. "
                         "Untuk 2 kelompok gunakan Uji Mann-Whitney U.")
    H, pv = stats.kruskal(*groups)
    k = len(groups)
    ranks = data["Y"].rank()
    mr = data.assign(R=ranks).groupby("G")["R"].mean()

    h = Hasil()
    h.tabel("Statistik per Kelompok",
            data.groupby("G")["Y"].agg(["count", "median", "mean"])
            .join(mr.rename("Mean Rank")).round(3))
    h.tabel("Hasil Uji Kruskal-Wallis", pd.DataFrame(
        {"Nilai": [H, k - 1, pv]},
        index=["H (statistik uji)", "df", "p-value"]).round(4))
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
    h.grafik("Boxplot per Kelompok", _chart_box(
        groups, list(data.groupby("G").groups.keys()), f"Sebaran {y} per kelompok ({g})", y))
    return h


def _np_friedman_run(df, p, alpha):
    cols = _aslist(p["cols"])
    if len(cols) < 3:
        raise ValueError("Uji Friedman membutuhkan minimal 3 kolom kondisi/pengukuran.")
    data = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(data) < 4:
        raise ValueError("Uji Friedman membutuhkan minimal 4 subjek dengan data lengkap.")
    chi_sq, pv = stats.friedmanchisquare(*[data[c] for c in cols])
    n, k = data.shape

    h = Hasil()
    h.metric("n Subjek", f"{n:,}", "database")
    h.metric("Jumlah Kondisi", str(k), "layers")
    h.metric("Median Tertinggi", fmt_stat(data[cols].median().max()), "up")
    h.metric("Median Terendah", fmt_stat(data[cols].median().min()), "down")
    h.tabel("Median per Kondisi", data[cols].median().to_frame("Median").round(3))
    h.tabel("Hasil Uji Friedman", pd.DataFrame(
        {"Nilai": [chi_sq, k - 1, pv]},
        index=["Chi-square (statistik uji)", "df", "p-value"]).round(4))
    h.uji("Friedman Test", chi_sq, pv, alpha)
    h.notes.append(f"Kendall's W (ukuran efek) = {chi_sq / (n * (k - 1)):.3f}")
    meds = data[cols].median()
    h.grafik("Median per Kondisi", _chart_medians(
        meds, "Median tiap kondisi pengukuran", "Median"))
    return h


def _np_runs_run(df, p, alpha):
    y = p["y"]
    data = pd.to_numeric(df[y], errors="coerce").dropna()
    if len(data) < 10:
        raise ValueError("Uji Runs membutuhkan minimal 10 observasi untuk pendekatan normal.")
    med = data.median()
    biner = (data > med).astype(int)
    n_valid = int((data != med).sum())
    if n_valid < 10:
        raise ValueError("Terlalu banyak nilai sama dengan median; data tidak dapat didikotomisasi.")
    biner = biner[data != med]
    n1 = int(biner.sum())
    n2 = len(biner) - n1
    if n1 == 0 or n2 == 0:
        raise ValueError("Semua data berada pada satu sisi median; uji Runs tidak dapat dijalankan.")
    runs = 1 + int((biner.diff().dropna() != 0).sum())
    n = n1 + n2
    er = 2 * n1 * n2 / n + 1
    var_r = (2 * n1 * n2 * (2 * n1 * n2 - n)) / (n ** 2 * (n - 1))
    z = (runs - er) / np.sqrt(var_r)
    pv = 2 * (1 - stats.norm.cdf(abs(z)))

    h = Hasil()
    h.metric("n Data Valid", f"{n:,}", "database")
    h.metric("Jumlah Run (R)", str(runs), "shuffle")
    h.metric("E(R) Acak", fmt_stat(er), "target")
    h.metric("Z", fmt_stat(z), "activity")
    h.tabel("Hasil Uji Runs", pd.DataFrame(
        {"Nilai": [n, n1, n2, med, runs, er, var_r, z, pv]},
        index=["n (data valid)", "n1 (di atas median)", "n2 (di bawah median)", "Median",
               "R (jumlah run)", "E(R) (ekspektasi run)", "Var(R)",
               "Z (statistik uji)", "p-value"]).round(4))
    h.uji("Runs Test Z", z, pv, alpha)
    if n < 50:
        h.warnings.append("Pendekatan normal paling akurat untuk n \u2265 50; "
                          "pada sampel kecil hasil bersifat indikatif.")
    h.grafik("Urutan Data vs Median", _chart_runs(
        data[data != med], med, f"Pola urutan {y} di sekitar median"))
    return h


def _np_mcnemar_run(df, p, alpha):
    v1, v2 = p["v1"], p["v2"]
    sub = df[[v1, v2]].dropna().astype(str)
    sub[v1] = sub[v1].str.strip()
    sub[v2] = sub[v2].str.strip()
    lv = sorted(set(sub[v1].unique()) | set(sub[v2].unique()))
    if len(lv) != 2:
        raise ValueError(
            f"Uji McNemar mensyaratkan data biner (2 kategori). Kolom terpilih memiliki "
            f"{len(lv)} kategori: {', '.join(str(x) for x in lv[:6])}. "
            f"Gunakan kolom dengan dua kategori saja (misalnya Ya/Tidak).")
    tab = pd.crosstab(sub[v1], sub[v2]).reindex(index=lv, columns=lv, fill_value=0)
    b = int(tab.iloc[0, 1])   # v1=kategori1, v2=kategori2
    c = int(tab.iloc[1, 0])   # v1=kategori2, v2=kategori1
    if b + c == 0:
        raise ValueError("Tidak ada pasangan yang berubah (b + c = 0); McNemar tidak dapat dijalankan.")
    res = sm_mcnemar(tab.values, exact=(b + c) < 25, correction=True)

    h = Hasil()
    h.metric("n Pasangan", f"{len(sub):,}", "database")
    h.metric("b (A\u2192B)", str(b), "leftright")
    h.metric("c (B\u2192A)", str(c), "leftright")
    h.metric("p-value", fmt_p(res.pvalue), "percent")
    h.tabel("Tabel Kontingensi 2x2", tab, f"Baris = {v1} (sebelum), kolom = {v2} (sesudah).")
    h.tabel("Hasil Uji McNemar", pd.DataFrame(
        {"Nilai": [res.statistic, b + c,
                   "Binomial eksak" if (b + c) < 25 else "Chi-square + koreksi kontinuitas",
                   res.pvalue]},
        index=["Statistik uji", "Pasangan discordant (b + c)",
               "Metode", "p-value"]).round(4))
    h.uji("Uji McNemar", res.statistic, res.pvalue, alpha)
    h.notes.append(f"Pasangan discordant: b = {b} (berubah dari '{lv[0]}' ke '{lv[1]}'), "
                   f"c = {c} (berubah dari '{lv[1]}' ke '{lv[0]}'); pasangan konsisten tidak diikutkan.")
    h.grafik("Frekuensi Sebelum vs Sesudah", _chart_grouped_counts(
        sub[v1].value_counts(), sub[v2].value_counts(), lv[0], lv[1],
        f"Distribusi {v1} vs {v2}", v1, v2))
    return h


def _np_gof_run(df, p, alpha):
    v = p["v"]
    sub = df[v].dropna().astype(str).str.strip()
    if sub.nunique() < 2:
        raise ValueError("Variabel harus memiliki minimal 2 kategori.")
    obs = sub.value_counts().sort_index()
    k = len(obs)
    exp_val = obs.sum() / k
    chi_sq, pv = stats.chisquare(obs.values)

    h = Hasil()
    h.metric("n Data", f"{int(obs.sum()):,}", "database")
    h.metric("Jumlah Kategori", str(k), "grid")
    h.metric("Ekspektasi per Kategori", fmt_stat(exp_val), "target")
    h.metric("Chi-Square", fmt_stat(chi_sq), "sigma")
    tbl = pd.DataFrame({
        "Observed": obs.values,
        "Expected": [exp_val] * k,
        "Selisih (O-E)": obs.values - exp_val,
        "(O-E)\u00b2/E": (obs.values - exp_val) ** 2 / exp_val,
    }, index=obs.index)
    h.tabel("Frekuensi per Kategori", tbl.round(3))
    h.tabel("Hasil Uji Chi-Square Goodness-of-Fit", pd.DataFrame(
        {"Nilai": [chi_sq, k - 1, pv]},
        index=["Chi-square (statistik uji)", "df (k - 1)", "p-value"]).round(4))
    h.uji("Chi-Square Goodness-of-Fit", chi_sq, pv, alpha)
    h.notes.append(f"df = {k - 1}; H\u2080 menyatakan frekuensi seragam di seluruh {k} kategori.")
    if exp_val < 5:
        h.warnings.append("Ekspektasi frekuensi per kategori < 5: aproksimasi chi-square "
                          "menjadi kurang akurat. Pertimbangkan menggabungkan kategori langka.")
    h.grafik("Observasi vs Ekspektasi", _chart_gof(
        obs.values, exp_val, obs.index.tolist(), f"Frekuensi kategori {v}"))
    return h


def _np_spearman_run(df, p, alpha):
    cols = _aslist(p["cols"])
    if len(cols) < 2:
        raise ValueError("Pilih minimal 2 variabel untuk korelasi Spearman.")
    data = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(data) < 5:
        raise ValueError("Korelasi Spearman membutuhkan minimal 5 baris data lengkap.")
    rho, pm = stats.spearmanr(data.values)
    rho = np.atleast_2d(rho)
    pm = np.atleast_2d(pm)
    n = len(data)

    pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            pairs.append({"Variabel 1": cols[i], "Variabel 2": cols[j],
                          "rho": rho[i, j], "p-value": pm[i, j], "n": n})
    pairs_df = pd.DataFrame(pairs)
    strongest = pairs_df.loc[pairs_df["rho"].abs().idxmax()]

    h = Hasil()
    h.metric("n Data", f"{n:,}", "database")
    h.metric("Jumlah Pasangan", str(len(pairs)), "link")
    h.metric("rho Terkuat", fmt_stat(strongest["rho"]), "trendup")
    h.metric("Pasangan Signifikan",
             str(int((pairs_df["p-value"] < alpha).sum())), "check")
    rho_df = pd.DataFrame(rho, index=cols, columns=cols).round(4)
    h.tabel("Matriks Korelasi Spearman (rho)", rho_df,
            "Baca diagonal dari kiri atas ke kanan bawah sebagai 1.")
    h.tabel("Korelasi Spearman Berpasangan", pairs_df.set_index(
        ["Variabel 1", "Variabel 2"]).round(4))
    h.uji(f"Korelasi Spearman (terkuat): {strongest['Variabel 1']} \u00d7 {strongest['Variabel 2']}",
          strongest["rho"], strongest["p-value"], alpha)
    if len(cols) <= 8:
        h.grafik("Heatmap Korelasi Spearman", _chart_heatmap(rho_df, cols, "rho antar variabel"))
    else:
        first = pairs_df.loc[pairs_df["rho"].abs().idxmax()]
        h.grafik("Scatter Pasangan Terkuat", _chart_scatter(
            data[first["Variabel 1"]], data[first["Variabel 2"]],
            f"{first['Variabel 1']} vs {first['Variabel 2']} (rho = {fmt_stat(first['rho'])})",
            first["Variabel 1"], first["Variabel 2"]))
    return h


def _np_kendall_run(df, p, alpha):
    v1, v2 = p["v1"], p["v2"]
    sub = df[[v1, v2]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(sub) < 8:
        raise ValueError("Korelasi Kendall membutuhkan minimal 8 pasangan data valid.")
    tau, pv = stats.kendalltau(sub[v1], sub[v2], variant="b")
    n = len(sub)

    h = Hasil()
    h.metric("n Pasangan", f"{n:,}", "database")
    h.metric("Tau-b", fmt_stat(tau), "link")
    h.metric("Arah", "Positif" if tau > 0 else ("Negatif" if tau < 0 else "Netral"), "trendup")
    h.metric("p-value", fmt_p(pv), "percent")
    h.tabel("Hasil Uji Kendall Tau", pd.DataFrame(
        {"Nilai": [n, tau, pv]},
        index=["n (pasangan data)", "tau-b (statistik uji)", "p-value"]).round(4))
    h.uji("Kendall Tau-b", tau, pv, alpha)
    h.notes.append("Tau-b tepat dipakai bila data memiliki banyak ikatan (ties) atau sampel kecil.")
    h.grafik("Scatter Kedua Variabel", _chart_scatter(
        sub[v1], sub[v2], f"{v1} vs {v2}", v1, v2))
    return h


# ==========================================================
# KATALOG 12 UJI NON-PARAMETRIK
# Setiap entri memuat: identitas, form/run, kegunaan, hipotesis,
# asumsi, cara membaca hasil, dan contoh penggunaan sehari-hari.
# ==========================================================
GRUP_NP = {
    "normalitas": ("Uji Normalitas & Homogenitas", "shield"),
    "beda": ("Uji Beda Non-Parametrik", "scale"),
    "frekuensi": ("Uji Frekuensi & Keacakan", "grid"),
    "asosiasi": ("Korelasi Non-Parametrik", "link"),
}

KATALOG = {
    "shapiro": {
        "judul": "Uji Normalitas Shapiro-Wilk", "ikon": "shield", "grup": "normalitas",
        "desc": "Menguji apakah data mengikuti distribusi normal; paling akurat untuk sampel kecil (n < 50) - prasyarat uji parametrik.",
        "tujuan": "Menilai apakah sebuah variabel numerik berdistribusi normal, sebagai langkah pemeriksaan prasyarat sebelum memilih uji parametrik (uji t, ANOVA) atau non-parametrik.",
        "kegunaan": [
            "Menentukan apakah data memenuhi syarat normalitas untuk uji parametrik seperti uji t dan ANOVA.",
            "Menjadi dasar keputusan pemilihan uji: p \u2265 \u03b1 pakai uji parametrik, p < \u03b1 gunakan uji non-parametrik.",
            "Memeriksa normalitas residual model regresi sebagai bagian dari uji asumsi klasik.",
            "Memvalidasi kualitas proses produksi (misalnya bobot produk) yang diasumsikan normal.",
        ],
        "harian": [
            ("Guru membandingkan nilai dua kelas",
             "Sebelum menguji apakah nilai matematika kelas A dan kelas B berbeda, guru menguji normalitas nilai dengan Shapiro-Wilk. Jika normal, lanjut uji t; jika tidak, gunakan Mann-Whitney U."),
            ("Kontrol kualitas pabrik roti",
             "Tim QA menguji normalitas berat roti per batch. Distribusi normal menandakan proses stabil sehingga peta kendali X-bar dan kapabilitas proses (Cpk) sah digunakan."),
            ("Peneliti klinik memeriksa tekanan darah",
             "Sebelum uji beda tekanan darah dua kelompok pasien, peneliti memastikan data tekanan darah normal agar hasil uji t valid dan dapat dipertanggungjawabkan di jurnal."),
        ],
        "hip": ("Data berdistribusi normal.",
                "Data tidak berdistribusi normal."),
        "asumsi": [
            "Data berjenis numerik kontinu (interval/rasio).",
            "Observasi saling bebas (independen), tidak berulang pada subjek sama.",
            "Sampel diambil secara acak dari populasi.",
        ],
        "baca": "Fokus pada p-value: jika p \u2265 \u03b1 (mis. 0.05), gagal tolak H\u2080 - data cukup normal. Jika p < \u03b1, tolak H\u2080 - data tidak normal. Nilai W mendekati 1 menandakan data mendekati kurva normal. Selalu lihat juga histogram untuk menilai relevansi praktis, karena pada sampel sangat besar penyimpangan kecil pun bisa signifikan.",
        "form": _np_shapiro_form, "run": _np_shapiro_run,
    },
    "ks": {
        "judul": "Uji Normalitas Kolmogorov-Smirnov", "ikon": "activity", "grup": "normalitas",
        "desc": "Menguji normalitas lewat jarak maksimum kurva CDF data vs normal; umum dipakai untuk n > 50 (versi Lilliefors).",
        "tujuan": "Menilai normalitas data dengan mengukur jarak terbesar antara fungsi distribusi kumulatif data dan distribusi normal; pilihan lazim untuk sampel menengah-besar dan standar output SPSS.",
        "kegunaan": [
            "Uji prasyarat normalitas untuk data berukuran lebih besar (umumnya n > 50).",
            "Alternatif Shapiro-Wilk yang lebih stabil pada sampel besar.",
            "Membandingkan pola sebaran data dengan distribusi teoretis apa pun (versi klasik).",
            "Mendukung keputusan metode analisis: parametrik vs non-parametrik pada laporan penelitian.",
        ],
        "harian": [
            ("Menganalisis pendapatan pelanggan marketplace",
             "Data pendapatan biasanya menceng ke kanan. Analis menguji normalitas dengan KS-Lilliefors; hasil tidak normal membuat mereka memakai median dan uji non-parametrik alih-alih mean."),
            ("Waktu tunggu antrean bank",
             "Manajemen menguji apakah waktu tunggu nasabah berdistribusi normal untuk menentukan standar layanan; jika tidak normal, target ditetapkan berbasis persentil."),
            ("Skor survei kepuasan skala besar",
             "Pada 500 responden, normalitas dicek dengan KS-Lilliefors sebelum memilih uji beda antar segmen pelanggan."),
        ],
        "hip": ("Data mengikuti distribusi normal.",
                "Data tidak mengikuti distribusi normal."),
        "asumsi": [
            "Data numerik kontinu dengan skala interval/rasio.",
            "Observasi independen satu sama lain.",
            "Parameter distribusi (versi Lilliefors) diestimasi dari data itu sendiri.",
        ],
        "baca": "Statistik L adalah jarak maksimum antara kurva CDF data dan CDF normal - semakin kecil semakin normal. Jika p \u2265 \u03b1, gagal tolak H\u2080 (data cukup normal); jika p < \u03b1, tolak H\u2080 (data tidak normal). Perhatikan histogram pendukung karena pada n besar penyimpangan kecil bisa membuat uji signifikan.",
        "form": _np_ks_form, "run": _np_ks_run,
    },
    "levene": {
        "judul": "Uji Homogenitas Levene", "ikon": "ruler", "grup": "normalitas",
        "desc": "Menguji kesamaan varians antar kelompok (homogenitas) - prasyarat ANOVA dan uji t independen; tahan data tidak normal.",
        "tujuan": "Menguji apakah varians (sebaran) nilai antar kelompok relatif sama. Homogenitas varians adalah asumsi kunci ANOVA dan uji t independen yang menentukan rumus mana yang sah digunakan.",
        "kegunaan": [
            "Memeriksa asumsi homogenitas varians sebelum ANOVA satu arah atau dua arah.",
            "Menentukan varian pooled vs Welch pada uji t dua sampel independen.",
            "Membandingkan konsistensi (bukan besarnya) antar kelompok, misalnya stabilitas mesin produksi.",
            "Basis penilaian kelayakan ANOVA klasik: jika Levene signifikan, gunakan Welch ANOVA atau Kruskal-Wallis.",
        ],
        "harian": [
            ("Membandingkan efektivitas 3 metode belajar",
             "Sebelum ANOVA nilai ujian tiga kelompok metode belajar, peneliti menguji homogenitas. Jika varians tidak sama, kesimpulan ANOVA klasik bisa menyesatkan - dipakai Welch atau Kruskal-Wallis."),
            ("Konsistensi dua mesin pengisian",
             "Mesin A dan B mengisi volume rata-rata sama, tetapi Levene menunjukkan varians mesin B jauh lebih besar - artinya mesin B lebih tidak konsisten meskipun rata-ratanya sama."),
            ("Fluktuasi harga di dua pasar tradisional",
             "Pedagang menguji apakah fluktuasi harga cabai di dua pasar sama derasnya; varians yang berbeda menandakan satu pasar lebih berisiko."),
        ],
        "hip": ("Semua kelompok memiliki varians yang sama (homogen).",
                "Minimal ada satu kelompok dengan varians yang berbeda."),
        "asumsi": [
            "Variabel dependen berupa numerik kontinu.",
            "Faktor kelompok bersifat kategorik dengan \u2265 2 level.",
            "Observasi independen antar dan dalam kelompok (versi median/Brown-Forsythe tidak mensyaratkan normalitas).",
        ],
        "baca": "Jika p \u2265 \u03b1, gagal tolak H\u2080 - varians antar kelompok homogen, ANOVA/uji t klasik aman dipakai. Jika p < \u03b1, tolak H\u2080 - varians tidak homogen; gunakan Welch ANOVA/Welch t-test atau uji non-parametrik. Bandingkan juga kolom varians pada tabel per kelompok untuk melihat kelompok mana yang paling beragam.",
        "form": _np_levene_form, "run": _np_levene_run,
    },
    "mwu": {
        "judul": "Uji Mann-Whitney U", "ikon": "leftright", "grup": "beda",
        "desc": "Membandingkan 2 kelompok independen melalui peringkat - alternatif uji t saat data tidak normal atau ordinal.",
        "tujuan": "Menguji apakah dua kelompok independen berasal dari populasi dengan distribusi (peringkat) yang berbeda, tanpa menuntut normalitas - alternatif resmi uji t sampel independen.",
        "kegunaan": [
            "Membandingkan dua kelompok bebas saat data tidak berdistribusi normal.",
            "Menguji perbedaan pada data ordinal seperti peringkat, skala Likert, atau nilai preferensi.",
            "Uji beda pada sampel kecil yang membuat uji t tidak andal.",
            "Uji lanjut (post-hoc) perbandingan berpasangan setelah Kruskal-Wallis signifikan.",
        ],
        "harian": [
            ("Kepuasan pelanggan cabang A vs B",
             "Skor kepuasan (1-5) tidak berdistribusi normal. Manajer membandingkan cabang A vs B dengan Mann-Whitney U untuk menentukan cabang mana yang layak menjadi contoh layanan."),
            ("Rating aplikasi Android vs iOS",
             "Tim produk menguji apakah rating pengguna Android berbeda dari iOS; data rating menumpuk di nilai ekstrem sehingga uji peringkat lebih tepat daripada uji t."),
            ("Waktu tunggu dua jalur kasir",
             "Pemilik minimarket membandingkan durasi antrean jalur reguler vs self-checkout; distribusi waktu tunggu menceng, sehingga Mann-Whitney U dipilih."),
        ],
        "hip": ("Distribusi (peringkat) kedua kelompok sama.",
                "Distribusi (peringkat) kedua kelompok berbeda."),
        "asumsi": [
            "Kedua kelompok saling independen (subjek berbeda).",
            "Variabel dependen minimal ordinal (bersifat kontinu atau berperingkat).",
            "Bentuk distribusi kedua kelompok serupa bila ingin menafsirkan perbedaan median.",
        ],
        "baca": "Jika p \u2265 \u03b1, gagal tolak H\u2080 - belum ada bukti perbedaan antar kelompok. Jika p < \u03b1, tolak H\u2080 - kelompok berbeda secara signifikan; lihat median masing-masing untuk menentukan kelompok yang lebih tinggi. Ukuran efek r melengkapi p-value: r = Z/\u221an dengan kategori kecil (<0.3), sedang (0.3-0.5), atau besar (>0.5).",
        "form": _np_mwu_form, "run": _np_mwu_run,
    },
    "wilcoxon": {
        "judul": "Uji Wilcoxon Signed-Rank", "ikon": "leftright", "grup": "beda",
        "desc": "Membandingkan dua pengukuran pada subjek yang sama (sebelum-sesudah) - alternatif uji t berpasangan.",
        "tujuan": "Menguji apakah terdapat perbedaan antara dua pengukuran berpasangan (pre-post, tanpa perlakuan vs dengan perlakuan) pada subjek yang sama, melalui peringkat selisihnya.",
        "kegunaan": [
            "Menguji dampak intervensi dengan desain pre-test dan post-test pada subjek sama.",
            "Alternatif uji t berpasangan saat selisih antar pengukuran tidak normal.",
            "Membandingkan dua metode pengukuran yang diterapkan pada objek yang sama.",
            "Uji lanjutan antar kondisi pada analisis Friedman yang signifikan.",
        ],
        "harian": [
            ("Efektivitas pelatihan karyawan",
             "HR mengukur skor kompetensi sebelum dan sesudah pelatihan pada karyawan yang sama. Wilcoxon signed-rank menilai apakah kenaikan skor cukup signifikan untuk melanjutkan program."),
            ("Program penurunan berat badan",
             "Berat badan peserta diukur sebelum dan sesudah program 8 minggu. Karena selisihnya tidak normal, Wilcoxon dipakai untuk memastikan penurunan bukan kebetulan."),
            ("Rating aplikasi sebelum vs sesudah pembaruan",
             "Tim produk membandingkan rating pengguna yang sama sebelum dan sesudah update besar untuk menilai dampak perubahan antarmuka."),
        ],
        "hip": ("Median selisih antara kedua pengukuran sama dengan nol (tidak ada perbedaan).",
                "Median selisih antara kedua pengukuran berbeda dari nol."),
        "asumsi": [
            "Data berpasangan: kedua kolom berasal dari subjek yang sama.",
            "Skala pengukuran minimal interval (selisihnya bermakna).",
            "Selisih antar pasangan saling bebas; distribusi selisih simetris di sekitar mediannya.",
        ],
        "baca": "Jika p \u2265 \u03b1, gagal tolak H\u2080 - tidak ada perbedaan signifikan antara kondisi sebelum dan sesudah. Jika p < \u03b1, tolak H\u2080 - perlakuan berdampak nyata; tunjukkan arah perubahan lewat median kedua pengukuran. Ukuran efek r = |Z|/\u221an membantu menilai seberapa besar dampak praktisnya.",
        "form": _np_wilcoxon_form, "run": _np_wilcoxon_run,
    },
    "kruskal": {
        "judul": "Uji Kruskal-Wallis", "ikon": "scale", "grup": "beda",
        "desc": "Membandingkan \u2265 3 kelompok independen melalui peringkat - alternatif ANOVA satu arah + post-hoc Mann-Whitney Bonferroni.",
        "tujuan": "Menguji apakah tiga kelompok atau lebih (independen) berbeda dalam distribusi/median nilainya, sebagai alternatif non-parametrik ANOVA satu arah yang tidak menuntut normalitas maupun homogenitas varians.",
        "kegunaan": [
            "Membandingkan lebih dari dua kelompok bebas saat data tidak normal.",
            "Menganalisis data ordinal (peringkat, rating, skala Likert) antar banyak kelompok.",
            "Pengganti ANOVA pada sampel kecil dengan sebaran menyimpang.",
            "Dilengkapi post-hoc Mann-Whitney dengan koreksi Bonferroni untuk menemukan kelompok yang berbeda.",
        ],
        "harian": [
            ("Membandingkan durasi belajar tiga jurusan",
             "Kemahasiswaan membandingkan jam belajar mahasiswa tiga jurusan. Data menceng dan varians tak sama, sehingga Kruskal-Wallis dipakai; hasil signifikan lalu ditelusuri post-hoc pasangan jurusan."),
            ("Rating empat cabang restoran",
             "Pemilik restoran menguji apakah rating empat cabang berbeda; bila signifikan, cabang dengan median terendah menjadi prioritas perbaikan."),
            ("Hasil panen tiga varietas padi",
             "Penyuluh membandingkan produktivitas tiga varietas di lahan petani berbeda; uji peringkat lebih tahan terhadap pencilan hasil satu petani."),
        ],
        "hip": ("Distribusi (peringkat) semua kelompok sama.",
                "Minimal satu kelompok memiliki distribusi (peringkat) yang berbeda."),
        "asumsi": [
            "Variabel dependen numerik atau ordinal yang dapat diberi peringkat.",
            "Kelompok saling independen dengan \u2265 3 level.",
            "Observasi saling bebas; bentuk distribusi antar kelompok serupa untuk menafsirkan median.",
        ],
        "baca": "Jika p \u2265 \u03b1, gagal tolak H\u2080 - tidak ada perbedaan antar kelompok pada taraf \u03b1. Jika p < \u03b1, tolak H\u2080 - minimal satu kelompok berbeda; baca tabel post-hoc Mann-Whitney (Bonferroni) untuk menemukan pasangan kelompok yang signifikan, lalu urutkan median tiap kelompok. Epsilon-squared menunjukkan besarnya porsi perbedaan yang dijelaskan kelompok.",
        "form": _np_kruskal_form, "run": _np_kruskal_run,
    },
    "friedman": {
        "judul": "Uji Friedman", "ikon": "activity", "grup": "beda",
        "desc": "Membandingkan \u2265 3 pengukuran berulang pada subjek yang sama - alternatif ANOVA ukuran berulang.",
        "tujuan": "Menguji apakah tiga kondisi atau lebih yang diukur berulang pada subjek yang sama menghasilkan distribusi (peringkat) berbeda - alternatif non-parametrik ANOVA ukuran berulang.",
        "kegunaan": [
            "Membandingkan performa/preferensi antar \u2265 3 produk, kondisi, atau perlakuan pada panelis sama.",
            "Menganalisis desain pengukuran berulang (pre, post 1, post 2) saat asumsi normalitas gagal.",
            "Menguji konsistensi penilaian beberapa penilai terhadap objek yang sama.",
            "Menyediakan Kendall's W sebagai ukuran konsordansi (kesepakatan) antar subjek.",
        ],
        "harian": [
            ("Uji rasa tiga resep minuman",
             "Panelis yang sama mencoba tiga resep dan memberi skor. Friedman menguji apakah preferensi benar-benar berbeda, bukan sekadar variasi selera individu."),
            ("Menilai tiga algoritma pada dataset sama",
             "Data scientist mengukur akurasi tiga model pada dataset yang sama; Friedman membandingkan performa ketiganya tanpa asumsi normalitas akurasi."),
            ("Skor pasien pada tiga tahap terapi",
             "Klinisi mengukur tingkat nyeri sebelum terapi, setelah sesi 1, dan setelah sesi 3 pada pasien yang sama untuk melihat tren perbaikan."),
        ],
        "hip": ("Distribusi (peringkat) semua kondisi sama pada populasi.",
                "Minimal satu kondisi memiliki distribusi (peringkat) yang berbeda."),
        "asumsi": [
            "Desain berulang: setiap subjek mengalami semua kondisi.",
            "Variabel dependen minimal ordinal dan dapat diberi peringkat dalam tiap subjek.",
            "Observasi antar subjek saling bebas.",
        ],
        "baca": "Jika p \u2265 \u03b1, gagal tolak H\u2080 - kondisi-kondisi tidak berbeda signifikan. Jika p < \u03b1, tolak H\u2080 - minimal satu kondisi berbeda; bandingkan median tiap kondisi pada tabel, dan jika perlu lakukan Wilcoxon antar pasangan dengan koreksi Bonferroni. Kendall's W mendekati 1 berarti subjek secara konsisten menempatkan kondisi yang sama pada urutan serupa.",
        "form": _np_friedman_form, "run": _np_friedman_run,
    },
    "gof": {
        "judul": "Uji Chi-Square Goodness-of-Fit", "ikon": "grid", "grup": "frekuensi",
        "desc": "Menguji apakah frekuensi kategori satu variabel mengikuti pola tertentu (di sini: seragam) - mis. keadilan distribusi permintaan.",
        "tujuan": "Menguji apakah distribusi frekuensi satu variabel kategorik sesuai pola yang diharapkan. Pada aplikasi ini pola yang diuji adalah seragam - setiap kategori diharapkan muncul dalam proporsi yang sama.",
        "kegunaan": [
            "Menguji keseimbangan permintaan/distribusi antar kategori produk, layanan, atau wilayah.",
            "Memeriksa keadilan (fairness) alat acak seperti dadu, roda undian, atau alokasi sampel.",
            "Menilai apakah preferensi konsumen tersebar merata atau terkonsentrasi pada kategori tertentu.",
            "Dasar keputusan operasional: stok, jadwal, dan alokasi sumber daya antar kategori.",
        ],
        "harian": [
            ("Keseimbangan permintaan menu restoran",
             "Pemilik restoran mengecek apakah permintaan lima kategori menu merata. Chi-square signifikan berarti ada menu favorit - dasar penyesuaian stok bahan baku dan promosi menu sepi."),
            ("Keadilan roda undian berhadiah",
             "Auditor menguji apakah tiap sektor roda undian terpilih sama seringnya; deviasi signifikan menandakan roda tidak fair dan harus dikalibrasi ulang."),
            ("Distribusi warna produk yang terjual",
             "Toko pakaian menguji apakah penjualan empat warna seragam; hasil yang tidak seragam memandu keputusan pembelian stok warna berikutnya."),
        ],
        "hip": ("Frekuensi semua kategori sama (distribusi seragam).",
                "Frekuensi minimal satu kategori berbeda dari pola seragam."),
        "asumsi": [
            "Data berupa frekuensi (count) kategori, bukan persentase atau ukuran lain.",
            "Observasi saling bebas - satu data hanya masuk satu kategori.",
            "Ekspektasi frekuensi tiap kategori idealnya \u2265 5 untuk aproksimasi chi-square yang akurat.",
        ],
        "baca": "Jika p \u2265 \u03b1, gagal tolak H\u2080 - frekuensi kategori dapat dianggap seragam. Jika p < \u03b1, tolak H\u2080 - distribusi tidak seragam; gunakan tabel selisih (O-E) dan grafik untuk menemukan kategori paling dominan atau paling sepi. Waspadai ekspektasi < 5 karena aproksimasi chi-square menjadi kurang akurat.",
        "form": _np_gof_form, "run": _np_gof_run,
    },
    "mcnemar": {
        "judul": "Uji McNemar", "ikon": "target", "grup": "frekuensi",
        "desc": "Menguji perubahan proporsi data biner berpasangan (sebelum-sesudah) - mis. efektivitas kampanye iklan.",
        "tujuan": "Menguji apakah proporsi kategori berubah signifikan antara dua pengukuran pada subjek yang sama untuk data biner (2 kategori) - versi chi-square untuk desain berpasangan.",
        "kegunaan": [
            "Menguji efektivitas intervensi pada data biner: minat beli, kesediaan vaksinasi, status merokok.",
            "Membandingkan akurasi dua model klasifikasi pada dataset uji yang sama.",
            "Menilai perubahan jawaban responden sebelum vs sesudah kampanye, pelatihan, atau sosialisasi.",
            "Alternatif Wilcoxon ketika hasil pengukuran berskala nominal biner.",
        ],
        "harian": [
            ("Efektivitas kampanye iklan",
             "Sebelum kampanye 45 dari 200 responden berminat membeli; sesudahnya 68. McNemar menguji apakah kenaikan minat beli signifikan atau hanya kebisingan sampling."),
            ("Sosialisasi protokol kesehatan",
             "Puskesmas mengukur kepatuhan cuci tangan sebelum dan sesudah sosialisasi pada orang yang sama; McNemar menilai perubahan perilaku yang bermakna."),
            ("Membandingkan dua model deteksi spam",
             "Tim data menguji apakah model baru lebih sering benar pada email yang salah ditebak model lama; pasangan discordant menjadi fokus uji."),
        ],
        "hip": ("Proporsi jawaban sama pada kedua pengukuran (b = c).",
                "Proporsi jawaban berbeda antara kedua pengukuran (b \u2260 c)."),
        "asumsi": [
            "Kedua variabel berskala nominal biner (tepat 2 kategori).",
            "Data berpasangan: kedua pengukuran berasal dari subjek yang sama.",
            "Sampel representatif; pasangan discordant (b + c) memadai, binomial eksak dipakai bila b + c < 25.",
        ],
        "baca": "Fokus pada pasangan discordant: b = berubah A\u2192B dan c = berubah B\u2192A. Jika p \u2265 \u03b1, gagal tolak H\u2080 - intervensi tidak mengubah proporsi secara signifikan. Jika p < \u03b1, tolak H\u2080 - terjadi perubahan nyata; arah perubahan ditentukan oleh mana yang lebih besar antara b atau c, dan selisih (b - c) adalah perubahan net-nya.",
        "form": _np_mcnemar_form, "run": _np_mcnemar_run,
    },
    "runs": {
        "judul": "Uji Runs (Keacakan)", "ikon": "shuffle", "grup": "frekuensi",
        "desc": "Menguji apakah urutan kemunculan data terjadi secara acak di sekitar median - deteksi tren/pola tersembunyi.",
        "tujuan": "Menguji apakah urutan kemunculan data bersifat acak dengan menghitung jumlah run (rangkaian nilai berurutan pada sisi yang sama dari median). Melangkahi uji beda biasa: yang dinilai adalah POLA urutannya.",
        "kegunaan": [
            "Memeriksa keacakan proses produksi: apakah produk cacat muncul menggerombol atau menyebar.",
            "Mendeteksi tren tersembunyi pada data deret waktu sebelum analisis lanjutan.",
            "Menguji kualitas generator angka acak atau keacakan hasil pengundian.",
            "Pemeriksaan awal diagnostik peta kendali (control chart) dalam statistik kualitas.",
        ],
        "harian": [
            ("Pengawasan cacat produksi",
             "Inspektur mencatat produk baik/cacat sesuai urutan produksi. Run terlalu sedikit (cacat menggerombol) menandakan penyebab khusus seperti mesin yang perlu dikalibrasi pada jam tertentu."),
            ("Pola antrean teller bank",
             "Manajer menguji apakah lonjakan nasabah terjadi acak sepanjang hari; pola berulang mengarah pada penyesuaian jadwal shift pegawai."),
            ("Verifikasi undian digital",
             "Panitia lomba mengecek apakah urutan pemenang yang dihasilkan aplikasi benar-benar acak agar undian tidak dapat diprediksi."),
        ],
        "hip": ("Urutan data bersifat acak.",
                "Urutan data tidak acak (ada pola menggerombol atau bergantian)."),
        "asumsi": [
            "Data tercatat sesuai urutan kemunculan aktual (urutan baris = urutan waktu).",
            "Variabel numerik yang dapat didikotomisasi di sekitar median.",
            "Pendekatan normal memadai untuk n yang cukup besar (idealnya \u2265 50).",
        ],
        "baca": "Bandingkan R (run teramati) dengan E(R) (ekspektasi acak): R jauh lebih kecil berarti pola menggerombol (clustering), R jauh lebih besar berarti pola bergantian. Jika p \u2265 \u03b1, gagal tolak H\u2080 - urutan dapat dianggap acak; jika p < \u03b1, tolak H\u2080 - ada pola sistematis yang perlu diinvestigasi melalui grafik urutan data.",
        "form": _np_runs_form, "run": _np_runs_run,
    },
    "spearman": {
        "judul": "Korelasi Spearman", "ikon": "link", "grup": "asosiasi",
        "desc": "Korelasi berbasis peringkat untuk hubungan monotonic - tahan outlier, tepat untuk data ordinal/Likert.",
        "tujuan": "Mengukur kekuatan dan arah hubungan monotonic antara dua variabel melalui peringkatnya, tanpa menuntut normalitas maupun hubungan linear - standar korelasi non-parametrik.",
        "kegunaan": [
            "Mengukur hubungan dua variabel ordinal seperti skala Likert (kepuasan, persepsi, motivasi).",
            "Analisis hubungan monotonic saat data kontinu tidak normal atau mengandung outlier.",
            "Alternatif Pearson saat hubungan konsisten tetapi tidak linear (selalu naik/selalu turun).",
            "Analisis korelasi pada sampel kecil yang membuat Pearson tidak andal.",
        ],
        "harian": [
            ("Jam belajar vs peringkat kelas",
             "Guru BK menguji apakah semakin tinggi jam belajar siswa, semakin baik pula peringkatnya. Spearman menyimpulkan hubungan searah yang kuat tanpa peduli skala unit keduanya."),
            ("Kepuasan vs loyalitas pelanggan",
             "Manajer CRM menghubungkan skor kepuasan (Likert 1-5) dengan frekuensi pembelian ulang; korelasi peringkat lebih tepat karena data kepuasan ordinal."),
            ("Penilaian dua juri lomba",
             "Panitia menguji apakah peringkat dua juri sejalan; rho tinggi berarti kriteria penilaian keduanya konsisten."),
        ],
        "hip": ("Tidak ada korelasi monotonic antara kedua variabel (rho = 0).",
                "Terdapat korelasi monotonic antara kedua variabel (rho \u2260 0)."),
        "asumsi": [
            "Hubungan kedua variabel bersifat monotonic (konsisten naik atau turun, walau tidak linear).",
            "Data minimal ordinal dan dapat diberi peringkat.",
            "Observasi berpasangan saling bebas.",
        ],
        "baca": "rho bernilai -1 sampai +1: tanda menunjukkan arah, besaran menunjukkan kekuatan (|rho| < 0.2 sangat lemah; 0.2-0.4 lemah; 0.4-0.6 sedang; 0.6-0.8 kuat; > 0.8 sangat kuat). Jika p < \u03b1 korelasi signifikan. Ingat: korelasi bukan bukti kausalitas - perlu logika teori atau eksperimen lanjutan.",
        "form": _np_spearman_form, "run": _np_spearman_run,
    },
    "kendall": {
        "judul": "Korelasi Kendall Tau", "ikon": "link", "grup": "asosiasi",
        "desc": "Korelasi peringkat berbasis pasangan konkordan/diskordan - lebih robust untuk sampel kecil & data dengan banyak ikatan.",
        "tujuan": "Mengukur kesesuaian peringkat dua variabel dengan membandingkan seluruh pasangan titik data (konkordan vs diskordan). Tau-b menjadi pilihan tepat untuk sampel kecil dan data dengan banyak nilai sama (ties).",
        "kegunaan": [
            "Korelasi pada sampel kecil di mana estimasi Spearman/Pearson kurang stabil.",
            "Data dengan banyak ikatan (nilai berulang) seperti peringkat bersama atau skor terbatas.",
            "Menguji kesepakatan penilaian antar penilai (inter-rater) pada objek yang sama.",
            "Alternatif interpretasi probabilitas: tau terkait langsung peluang urutan pasangan sesuai.",
        ],
        "harian": [
            ("Konsistensi diagnosis dua dokter",
             "Sepuluh pasien diringkat tingkat keparahannya oleh dua dokter. Kendall tau mengukur sejauh mana urutan diagnosis mereka sejalan sebagai indikator reliabilitas."),
            ("Kesesuaian dua reviewer produk",
             "Platform e-commerce menguji apakah penilaian dua reviewer terhadap sepuluh produk menempatkan produk yang sama pada urutan serupa."),
            ("Pendidikan vs peringkat pendapatan",
             "Peneliti menghubungkan tingkat pendidikan (peringkat) dengan tingkatan pendapatan pada sampel kecil; tau-b memberi estimasi yang lebih stabil daripada Spearman."),
        ],
        "hip": ("Tidak ada korelasi peringkat antara kedua variabel (tau = 0).",
                "Terdapat korelasi peringkat antara kedua variabel (tau \u2260 0)."),
        "asumsi": [
            "Data minimal ordinal dan berpasangan antar dua variabel.",
            "Observasi saling bebas antar pasangan.",
            "Variant tau-b memperhitungkan ikatan (ties) pada kedua variabel.",
        ],
        "baca": "Tau-b berkisar -1 sampai +1 dengan interpretasi arah dan kekuatan serupa korelasi umum. Jika p < \u03b1, korelasi signifikan. Secara intuitif, tau menyatakan selisih peluang pasangan searah minus pasangan berlawanan urutan - sehingga mudah dikomunikasikan ke audiens non-teknis.",
        "form": _np_kendall_form, "run": _np_kendall_run,
    },
}


# ==========================================================
# DATA CONTOH KHUSUS NON-PARAMETRIK (menambah pasangan biner utk McNemar)
# ==========================================================
def buat_data_contoh_np():
    df = buat_data_contoh().copy()
    rng = np.random.default_rng(7)
    n = len(df)
    pre = rng.random(n) < 0.42
    post = (pre & (rng.random(n) > 0.14)) | (~pre & (rng.random(n) < 0.30))
    df["beli_sebelum"] = np.where(pre, "Ya", "Tidak")
    df["beli_sesudah"] = np.where(post, "Ya", "Tidak")
    return df


# ==========================================================
# KOMPONEN HALAMAN
# ==========================================================
def np_hero():
    return Div(
        Span(ICON_SVG("shuffle", 13), "Statistik Non-Parametrik", cls="eyebrow"),
        H1(
            "Uji tanpa asumsi normalitas, ",
            Span("tetap tajam", cls="grad-text"),
        ),
        P(
            "Unggah data, pilih salah satu dari 12 uji non-parametrik - dari uji normalitas, "
            "uji beda berbasis peringkat, uji frekuensi, hingga korelasi Spearman dan Kendall. "
            "Setiap uji dilengkapi penjelasan kegunaan, contoh penggunaan dalam kehidupan "
            "sehari-hari, keputusan uji, dan narasi analisis otomatis.",
            cls="hero-sub",
        ),
        Div(
            Span("12 uji non-parametrik", cls="chip chip-cyan"),
            A(ICON_SVG("book", 13), "Teori uji parametrik", href="/teori", cls="chip chip-link"),
            cls="teori-chips",
        ),
        Div(
            Div(
                Div(ICON_SVG("shield", 16), cls="feature-ic"),
                Div(B("Bebas Asumsi Normalitas"),
                    Span("Cocok untuk data tidak normal, ordinal (Likert), sampel kecil, "
                         "atau mengandung outlier.")),
                cls="feature",
            ),
            Div(
                Div(ICON_SVG("bulb", 16), cls="feature-ic"),
                Div(B("Penjelasan Tiap Uji"),
                    Span("Kartu \"Tentang Uji Ini\" menerangkan kegunaan, hipotesis, asumsi, "
                         "dan cara membaca hasilnya.")),
                cls="feature",
            ),
            Div(
                Div(ICON_SVG("chat", 16), cls="feature-ic"),
                Div(B("Contoh Kehidupan Sehari-hari"),
                    Span("Setiap uji disertai skenario nyata - dari kampanye iklan hingga "
                         "kontrol kualitas pabrik - dan narasi siap laporan.")),
                cls="feature",
            ),
            cls="features anim-in d1 features-3",
        ),
        cls="hero",
    )


def np_upload_section():
    return Section(
        Div(
            Div(ICON_SVG("cloud", 28), cls="drop-ic"),
            H3("Tarik & letakkan file di sini", cls="drop-title"),
            P("atau klik area ini untuk ", Span("memilih file", cls="link-like"),
              " dari perangkat Anda", cls="drop-hint"),
            id="dropzone",
            cls="dropzone",
        ),
        Input(type="file", name="file", id="file-input", accept=NP_ACCEPT, cls="sr-only"),
        Div(Div(id="upload-bar", cls="progress-bar"), id="upload-progress", cls="progress-wrap"),
        Div(id="upload-error"),
        Div(*[Span(f.upper(), cls="fmt-chip") for f in NP_FORMATS], cls="fmt-row"),
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


def np_empty():
    return Div(
        Div(ICON_SVG("database", 30), cls="empty-ic"),
        H3("Belum Ada Data"),
        P("Unggah file untuk memilih dan menjalankan uji non-parametrik. Hasil uji, narasi "
          "analisis, dan grafik akan muncul di area ini."),
        Div(*[Span(f.upper(), cls="fmt-chip") for f in NP_FORMATS], cls="fmt-row"),
        Button(ICON_SVG("sparkles", 15), "Coba dengan Data Contoh",
               cls="btn btn-ghost btn-sm demo-btn",
               hx_get="/nonparam/demo", hx_target="#workspace", hx_swap="innerHTML"),
        cls="empty-card anim-in",
    )


def np_tabs(sid, df):
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
                  href=f"/nonparam/dl-data/{sid}", cls="btn btn-ghost btn-sm",
                  download="data_dimuat.csv"),
                cls="tab-dl"),
            cls="tab-bar",
        ),
        Div(
            Div(_np_data_table_preview(df, 200), cls="table-wrap"),
            P(f"Menampilkan {min(200, n_rows)} dari {n_rows:,} baris \u00d7 {n_cols:,} kolom",
              cls="table-note"),
            cls="tab-panel active", data_panel="tab-prev",
        ),
        Div(Div(df_table(info), cls="table-wrap"), cls="tab-panel", data_panel="tab-info"),
        Div(Div(df_table(desc), cls="table-wrap"), cls="tab-panel", data_panel="tab-desc"),
        cls="card anim-in d1 tabs-card",
    )


def _np_data_table_preview(df, nmax=200):
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


def np_picker(sid, df):
    parts = []
    for gkey, (gtitle, gicon) in GRUP_NP.items():
        tiles = []
        for akey, meta in KATALOG.items():
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
                hx_get=f"/nonparam/form/{sid}?a={akey}",
                hx_target="#np-params", hx_swap="innerHTML",
            ))
        parts.append(Div(
            Div(ICON_SVG(gicon, 17), H3(gtitle), Span(f"{len(tiles)} uji", cls="chip"),
                cls="sec-head"),
            Div(*tiles, cls="a-grid"),
            cls="a-group",
        ))
    return Section(
        Div(ICON_SVG("sliders", 17), H3("Pilih Uji Non-Parametrik"),
            Span("12 uji tersedia", cls="chip chip-cyan"),
            cls="sec-head"),
        P("Aturan praktis memilih uji: cek normalitas dulu (Shapiro-Wilk/KS); bandingkan 2 kelompok "
          "bebas pakai Mann-Whitney U, data berpasangan pakai Wilcoxon, \u2265 3 kelompok bebas pakai "
          "Kruskal-Wallis, \u2265 3 pengukuran berulang pakai Friedman; data biner berpasangan pakai "
          "McNemar; korelasi ordinal pakai Spearman atau Kendall. Klik kartu untuk membuka form - "
          "penjelasan kegunaan dan contoh sehari-hari ikut tampil di dalamnya.", cls="picker-note"),
        *parts,
        cls="card anim-in d2 picker-card",
    )


def np_param_placeholder():
    return Div(
        Div(ICON_SVG("sliders", 26), cls="empty-ic empty-ic-sm"),
        H3("Konfigurasi Uji"),
        P("Pilih salah satu kartu uji di atas - form parameter, penjelasan kegunaan uji, dan "
          "tombol RUN akan muncul di sini."),
        cls="empty-card empty-compact anim-in",
        id="param-empty",
    )


def np_result_placeholder():
    return Div(
        P("Hasil uji akan tampil di area ini setelah Anda menekan tombol RUN.",
          cls="result-hint"),
        id="np-results-inner",
    )


# ==========================================================
# KARTU "TENTANG UJI INI" (kegunaan + contoh kehidupan sehari-hari)
# ==========================================================
def about_card(akey):
    m = KATALOG[akey]
    kegunaan = Div(
        Div(ICON_SVG("zap", 14), Span("Kegunaan Uji"), cls="th-sec-title"),
        Ul(*[Li(k) for k in m["kegunaan"]], cls="use-list"),
        cls="th-col",
    )
    asumsi = Div(
        Div(ICON_SVG("shield", 14), Span("Asumsi yang Dipersyaratkan"), cls="th-sec-title"),
        Ul(*[Li(a) for a in m["asumsi"]], cls="use-list assume-list"),
        cls="th-col",
    )
    harian = Div(
        Div(ICON_SVG("bulb", 14), Span("Penggunaan dalam Kehidupan Sehari-hari"),
            cls="th-sec-title"),
        Div(*[
            Div(
                Div(ICON_SVG("bulb", 14), cls="harian-ic"),
                Div(B(judul), P(txt), cls="harian-body"),
                cls="harian-item",
            ) for judul, txt in m["harian"]
        ], cls="harian-list"),
        cls="th-col-full",
    )
    hyps = Div(
        Div(Div("H\u2080", cls="hyp-tag"), P(m["hip"][0]), cls="hyp-box hyp-null"),
        Div(Div("H\u2081", cls="hyp-tag"), P(m["hip"][1]), cls="hyp-box hyp-alt"),
        cls="th-hyps th-hyps-full",
    )
    baca = Div(
        Div(ICON_SVG("info", 15), Span("Cara Membaca Hasil"), cls="baca-head"),
        P(m["baca"]),
        cls="baca-box",
    )
    return Div(
        Div(
            Div(ICON_SVG("book", 18), cls="about-ic"),
            Div(
                Div(f"Tentang Uji Ini - {m['judul']}", cls="about-title"),
                Div("Kegunaan, hipotesis, asumsi, dan contoh penerapannya dalam kehidupan sehari-hari.",
                    cls="about-sub"),
            ),
            cls="about-head",
        ),
        P(m["tujuan"], cls="th-tujuan"),
        Div(kegunaan, asumsi, cls="th-cols"),
        harian,
        hyps,
        baca,
        cls="card anim-in np-about",
    )


# ==========================================================
# RENDER HASIL
# ==========================================================
def render_hasil_np(sid, akey, h: Hasil, alpha):
    meta = KATALOG[akey]
    paras = buat_narasi_np(akey, h, alpha)
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
            NP_SESSIONS.setdefault(sid, {}).setdefault("dl", {})[key] = (fname, _df)
            dl.append(A(ICON_SVG("download", 15), lbl,
                        href=f"/nonparam/dl/{sid}/{key}", cls="btn btn-success btn-sm",
                        download=fname))
        parts.append(Div(*dl, cls="dl-row anim-in"))
    parts.append(about_card(akey))
    return Div(*parts, cls="res-root")


def np_workspace(sid, df, fname, size, sheets=None, sheet=None):
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
               hx_post="/nonparam/reset", hx_target="#workspace", hx_swap="innerHTML"),
        cls="banner anim-in",
    )
    sheet_sel = None
    if sheets and len(sheets) > 1:
        opts = [Option(str(sh), value=str(sh), selected=(str(sh) == str(sheet or sheets[0])))
                for sh in sheets]
        sheet_sel = Div(
            Label("Pilih sheet Excel", cls="f-label"),
            Select(*opts, name="sheet", cls="inp inp-select inp-select-sm",
                   hx_post="/nonparam/sheet", hx_trigger="change",
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
        Span("12 uji non-parametrik siap dijalankan", cls="chip chip-pink"),
        cls="chip-row",
    )
    parts = [banner]
    if sheet_sel is not None:
        parts.append(Div(sheet_sel, cls="sheet-wrap"))
    parts.append(chips)
    parts.append(np_tabs(sid, df))
    parts.append(np_picker(sid, df))
    parts.append(Div(np_param_placeholder(), id="np-params"))
    parts.append(Div(np_result_placeholder(), id="np-results"))
    return Div(*parts, cls="ws-root")


# ==========================================================
# SESI
# ==========================================================
def _prune_np():
    while len(NP_SESSIONS) > MAX_NP_SESSIONS:
        oldest = next(iter(NP_SESSIONS))
        NP_SESSIONS.pop(oldest, None)


# ==========================================================
# ROUTES
# ==========================================================
def setup(rt):
    @rt("/nonparam")
    def get():
        return (
            Title("AseliPedas - Statistik Non-Parametrik"),
            np_nav(),
            Main(
                np_hero(),
                Div(
                    Form(
                        np_upload_section(),
                        id="upload-form",
                        hx_post="/nonparam/upload", hx_target="#workspace", hx_swap="innerHTML",
                        hx_encoding="multipart/form-data",
                    ),
                    Div(np_empty(), id="workspace"),
                    cls="wrap",
                ),
                np_footer(),
                Script(src="/js/nonparam.js"),
            ),
        )

    @rt("/nonparam/upload")
    async def post(req: Request):
        try:
            form = await req.form()
            up = form.get("file")
            fname = getattr(up, "filename", "") or ""
            if not fname:
                return inf_error_fragment("Tidak ada file yang dipilih. Silakan pilih file terlebih dahulu.")
            data = await up.read()
            ext = os.path.splitext(fname)[1].lower().lstrip(".")
            if ext not in NP_FORMATS:
                return inf_error_fragment(
                    f"Format .{ext or '(tanpa ekstensi)'} belum didukung. "
                    f"Gunakan: {', '.join(f.upper() for f in NP_FORMATS)}.")
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
            NP_SESSIONS[sid] = {
                "df": df, "name": fname, "size": len(data), "autoconv": autoconv,
                "raw": data if (sheets and len(sheets) > 1) else None,
                "sheets": sheets, "sheet": sheets[0] if sheets else None, "dl": {},
            }
            _prune_np()
            return np_workspace(sid, df, fname, len(data),
                                sheets=sheets, sheet=sheets[0] if sheets else None)
        except Exception as e:
            return inf_error_fragment(f"Gagal membaca file: {e}")

    @rt("/nonparam/sheet")
    async def post(req: Request):
        form = await req.form()
        sid = str(form.get("sid") or "")
        sheet = str(form.get("sheet") or "")
        s = NP_SESSIONS.get(sid)
        if not s or not s.get("raw"):
            return inf_error_fragment("Sesi tidak ditemukan atau file bukan Excel multi-sheet.")
        try:
            df = pd.read_excel(io.BytesIO(s["raw"]), sheet_name=sheet)
            if s.get("autoconv"):
                df = konversi_numerik(df)
            s["df"] = df
            s["sheet"] = sheet
            return np_workspace(sid, df, s["name"], s["size"],
                                sheets=s["sheets"], sheet=sheet)
        except Exception as e:
            return inf_error_fragment(f"Gagal membaca sheet: {e}")

    @rt("/nonparam/demo")
    def get():
        df = buat_data_contoh_np()
        sid = uuid.uuid4().hex[:10]
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        NP_SESSIONS[sid] = {"df": df, "name": "data_contoh.csv", "size": len(csv_bytes),
                            "autoconv": True, "raw": None, "sheets": None,
                            "sheet": None, "dl": {}}
        _prune_np()
        return np_workspace(sid, df, "data_contoh.csv", len(csv_bytes))

    @rt("/nonparam/reset")
    def post():
        return np_empty()

    @rt("/nonparam/form/{sid}")
    def get(sid: str, req: Request):
        s = NP_SESSIONS.get(sid)
        if not s:
            return inf_error_fragment("Sesi data tidak ditemukan. Silakan unggah ulang file.")
        qp = req.query_params
        akey = str(qp.get("a") or "")
        meta = KATALOG.get(akey)
        if not meta:
            return inf_error_fragment("Uji tidak dikenal.")
        cur = {k: qp.getlist(k) for k in qp.keys()}
        cur["__form_url__"] = f"/nonparam/form/{sid}?a={akey}"
        df = s["df"]
        try:
            fields = meta["form"](df, cur)
        except Exception as e:
            return inf_error_fragment(f"Gagal menyiapkan form: {e}")
        alpha_seg = f_seg("alpha", "Taraf signifikansi (\u03b1)",
                          [("0.1", "\u03b1 = 0.10"), ("0.05", "\u03b1 = 0.05"), ("0.01", "\u03b1 = 0.01")],
                          cur, default="0.05")
        alpha_seg.attrs.pop("name", None)
        return Section(
            about_card(akey),
            Div(
                Div(ICON_SVG(meta["ikon"], 18), cls="param-head-ic"),
                Div(H3(meta["judul"]), cls="param-title"),
                Span(GRUP_NP[meta["grup"]][0], cls="chip chip-cyan"),
                cls="sec-head param-head",
            ),
            Form(
                Div(*fields, cls="param-grid"),
                Div(alpha_seg, cls="field field-wide alpha-field"),
                Div(
                    Button(ICON_SVG("zap", 16), "RUN UJI NON-PARAMETRIK", type="submit",
                           cls="btn btn-primary btn-lg"),
                    Div(Span(cls="spinner spinner-sm"),
                        "Menghitung...",
                        id="run-loading", cls="spinner-inline htmx-indicator"),
                    cls="run-row",
                ),
                hx_post=f"/nonparam/run/{sid}?a={akey}",
                hx_target="#np-results", hx_swap="innerHTML",
                hx_indicator="#run-loading",
            ),
            cls="card anim-in param-card",
            id="np-params-card",
        )

    @rt("/nonparam/run/{sid}")
    async def post(sid: str, req: Request):
        s = NP_SESSIONS.get(sid)
        if not s:
            return inf_error_fragment("Sesi data tidak ditemukan. Silakan unggah ulang file.")
        qp = req.query_params
        akey = str(qp.get("a") or "")
        meta = KATALOG.get(akey)
        if not meta:
            return inf_error_fragment("Uji tidak dikenal.")
        form = await req.form()
        MULTI_KEYS = {"cols", "dua"}
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
        return render_hasil_np(sid, akey, h, alpha)

    @rt("/nonparam/dl-data/{sid}")
    def get(sid: str):
        s = NP_SESSIONS.get(sid)
        if not s:
            return Response("Sesi tidak ditemukan. Silakan unggah ulang file.",
                            status_code=404, media_type="text/plain")
        csv_bytes = s["df"].to_csv(index=False).encode("utf-8")
        return Response(csv_bytes, media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="data_dimuat.csv"'})

    @rt("/nonparam/dl/{sid}/{key}")
    def get(sid: str, key: str):
        s = NP_SESSIONS.get(sid)
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
def np_nav():
    return _NAV_FACTORY("/nonparam")


def np_footer():
    return _FOOTER_FACTORY()


_NAV_FACTORY = None
_FOOTER_FACTORY = None


def register_shared(nav_factory, footer_factory):
    global _NAV_FACTORY, _FOOTER_FACTORY
    _NAV_FACTORY = nav_factory
    _FOOTER_FACTORY = footer_factory
