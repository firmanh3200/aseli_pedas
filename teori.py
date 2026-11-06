# -*- coding: utf-8 -*-
"""
AseliPedas - Halaman Teori Uji Statistik (FastHTML Edition)
=========================================================
Halaman referensi yang menjelaskan teori dan kegunaan setiap analisis
statistik yang tersedia di halaman Statistik Inferens.

Agar halaman tidak terlalu panjang, seluruh 20 kartu teori dikemas dalam
satu datatable "Pustaka Uji Statistik" dengan fitur lengkap:
  - Pencarian instan (nama, tujuan, kegunaan, asumsi, contoh, kata kunci peta)
  - Filter kelompok uji & kategori (parametrik / non-parametrik / multivariat)
  - Sorting kolom, pagination (pilih ukuran halaman, navigator bernomor)
  - Baris dapat diklik untuk membuka teori lengkap (accordion expand)

Modul ini di-register dari app.py lewat teori.setup(rt) dan berbagi
navbar/footer dengan halaman lain via teori.register_shared(nav, footer).
"""
import re

from fasthtml.common import (
    Div, Section, Nav, Main, H1, H3, H4, P, Span, A, Ul, Li, Table, Thead,
    Tbody, Tr, Th, Td, Title, Script, NotStr, Button, Input, Select, Option,
    Label,
)

from inferens import GRUP, ANALISIS, ICONS as INF_ICONS
from teori_data import KONSEP, PETA
from teori_uji1 import TEORI_A
from teori_uji2 import TEORI_B

TEORI = {**TEORI_A, **TEORI_B}

# ------------------------------------------------------------------
# IKON TAMBAHAN (di luar ikon bawaan inferens.py)
# ------------------------------------------------------------------
ICONS = dict(INF_ICONS)
ICONS.update({
    "book": ('<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 '
             '4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>'),
    "bulb": ('<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5 '
             '.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>'),
    "arrow": ('<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>'),
    "search": ('<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>'),
})

KAT_LABEL = {"p": "Parametrik", "n": "Non-Parametrik", "m": "Multivariat"}


def icon(name, size=18):
    return NotStr(
        f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{ICONS[name]}</svg>'
    )


ICON_SVG = icon  # keselarasan penamaan dengan inferens.py


# ------------------------------------------------------------------
# PETA -> "cocok untuk" per uji (inversi baris peta pemilihan uji)
# ------------------------------------------------------------------
COCOK = {}
for _tujuan, _data, _uji, _anchor in PETA:
    _key = _anchor.replace("th-", "", 1)
    COCOK.setdefault(_key, []).append((_tujuan, _data))


def _norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def _search_text(akey, meta):
    """Gabungan teks yang bisa dicari untuk satu uji."""
    t = TEORI[akey]
    parts = [
        meta["judul"], t["jenis"], KAT_LABEL[t["jcls"]],
        GRUP[meta["grup"]][0], t["tujuan"], t["apa"], t["baca"],
    ]
    parts += t["kegunaan"] + t["asumsi"] + t["contoh"] + t["rumus"]
    if t["hip"]:
        parts += list(t["hip"])
    for tujuan, data in COCOK.get(akey, []):
        parts += [tujuan, data]
    return _norm(" ".join(parts))


# ------------------------------------------------------------------
# HERO
# ------------------------------------------------------------------
def teori_hero():
    return Div(
        Span(ICON_SVG("book", 13), "Panduan Konsep & Kegunaan", cls="eyebrow"),
        H1("Pustaka ", Span("Teori Uji", cls="grad-text"), " Statistik"),
        P("Pahami kegunaan, hipotesis, asumsi, dan cara membaca hasil dari seluruh 20 analisis "
          "yang tersedia di AseliPedas. Gunakan pencarian, filter, dan pagination pada tabel di "
          "bawah, lalu klik baris uji untuk membuka teori lengkapnya.", cls="hero-sub"),
        Div(
            Span("20 analisis", cls="chip chip-cyan"),
            Span("Pencarian & filter instan", cls="chip"),
            Span("8 konsep dasar", cls="chip chip-pink"),
            cls="teori-chips",
        ),
        cls="hero",
    )


# ------------------------------------------------------------------
# SEKSI KONSEP DASAR
# ------------------------------------------------------------------
def konsep_section():
    cards = [
        Div(
            Div(ICON_SVG(ic, 17), cls="concept-ic"),
            H4(title),
            P(txt),
            cls="concept-card",
        ) for ic, title, txt in KONSEP
    ]
    return Section(
        Div(ICON_SVG("info", 16), H3("Konsep Dasar Statistik Inferens"), cls="sec-head"),
        P("Sebagian besar kebingungan membaca hasil uji statistik berasal dari konsep dasar yang "
          "belum mapan. Kartu-kartu berikut merangkum gagasan inti yang dipakai berulang kali "
          "pada seluruh analisis di aplikasi ini.", cls="th-intro"),
        Div(*cards, cls="concept-grid"),
        cls="card th-sec anim-in",
        id="th-konsep",
    )


# ------------------------------------------------------------------
# KONTEN TEORI LENGKAP (untuk baris detail datatable)
# ------------------------------------------------------------------
def detail_body(akey, meta):
    t = TEORI[akey]

    cocok_items = COCOK.get(akey, [])
    if cocok_items:
        cocok = Div(
            Div(ICON_SVG("compass", 14), Span("Cocok untuk kebutuhan berikut"), cls="th-sec-title"),
            Div(*[
                Span(Span(f"{tujuan} ", cls="cocok-tujuan"), Span(f"data: {data}", cls="cocok-data"),
                     cls="chip cocok-chip")
                for tujuan, data in cocok_items
            ], cls="cocok-list"),
            cls="dt-cocok",
        )
    else:
        cocok = Div()

    cols = Div(
        Div(
            Div(ICON_SVG("zap", 14), Span("Kegunaan"), cls="th-sec-title"),
            Ul(*[Li(k) for k in t["kegunaan"]], cls="use-list"),
            cls="th-col",
        ),
        Div(
            Div(ICON_SVG("shield", 14), Span("Asumsi"), cls="th-sec-title"),
            Ul(*[Li(a) for a in t["asumsi"]], cls="use-list assume-list"),
            cls="th-col",
        ),
        cls="th-cols",
    )

    if t["hip"]:
        hyps = Div(
            Div(Div("H\u2080", cls="hyp-tag"), P(t["hip"][0]), cls="hyp-box hyp-null"),
            Div(Div("H\u2081", cls="hyp-tag"), P(t["hip"][1]), cls="hyp-box hyp-alt"),
            cls="th-hyps",
        )
    else:
        hyps = Div(
            Div(
                ICON_SVG("info", 15),
                Span("Analisis eksploratif - tidak menguji hipotesis formal. Penilaian mengandalkan "
                     "kriteria internal seperti proporsi varians, silhouette, atau interpretabilitas."),
                cls="expl-note",
            ),
            cls="th-hyps th-hyps-full",
        )

    rumus = Div(
        Div(ICON_SVG("sigma", 14), Span("Rumus Utama"), cls="th-sec-title"),
        Div(*[Div(r, cls="formula-box") for r in t["rumus"]], cls="th-rumus"),
    )

    baca = Div(
        Div(ICON_SVG("info", 15), Span("Cara Membaca Hasil"), cls="baca-head"),
        P(t["baca"]),
        cls="baca-box",
    )

    contoh = Div(
        Div(ICON_SVG("bulb", 14), Span("Contoh Penerapan"), cls="th-sec-title"),
        Div(*[Div(ICON_SVG("bulb", 15), Span(c), cls="contoh-row") for c in t["contoh"]],
            cls="th-contoh"),
    )

    link = A("Coba uji ini di Statistik Inferens", icon("arrow", 14),
             href="/inferens", cls="th-link")

    return Div(
        P(t["tujuan"], cls="th-tujuan"),
        P(t["apa"], cls="th-apa"),
        cocok,
        cols,
        hyps,
        rumus,
        baca,
        contoh,
        link,
        cls="dt-detail-body",
    )


# ------------------------------------------------------------------
# DATATABLE "PUSTAKA UJI"
# ------------------------------------------------------------------
def _uji_row(idx, akey, meta):
    t = TEORI[akey]
    gtitle, _gicon = GRUP[meta["grup"]]

    row = Tr(
        Td(str(idx + 1), cls="dt-no"),
        Td(
            Div(
                Div(ICON_SVG(meta["ikon"], 17), cls="dt-ic"),
                Div(
                    Span(meta["judul"], cls="dt-judul"),
                    Span(t["jenis"], cls=f"badge-j {t['jcls']} dt-badge"),
                    cls="dt-uji-txt",
                ),
                cls="dt-uji",
            ),
            cls="col-uji",
        ),
        Td(Span(gtitle, cls="chip chip-grup"), cls="col-grup"),
        Td(Span(KAT_LABEL[t["jcls"]], cls="kat-text"), cls="col-kat"),
        Td(Span(t["tujuan"], cls="dt-tujuan"), cls="col-tujuan"),
        Td(ICON_SVG("down", 15), cls="dt-chev-cell"),
        cls="dt-row",
        id=f"uji-{akey}",
        tabindex="0",
        role="button",
        aria_expanded="false",
        aria_controls=f"det-{akey}",
        data_key=akey,
        data_judul=_norm(meta["judul"]),
        data_grup=meta["grup"],
        data_grupt=_norm(gtitle),
        data_kat=t["jcls"],
        data_search=_search_text(akey, meta),
    )

    detail = Tr(
        Td(
            Div(
                Div(ICON_SVG(meta["ikon"], 19), cls="dt-ic dt-ic-lg"),
                Div(
                    H3(meta["judul"]),
                    Div(
                        Span(t["jenis"], cls=f"badge-j {t['jcls']}"),
                        Span(gtitle, cls="chip"),
                        cls="th-badges",
                    ),
                    cls="dt-detail-head-txt",
                ),
                cls="dt-detail-head",
            ),
            detail_body(akey, meta),
            cls="dt-detail-in",
            colspan=6,
        ),
        cls="dt-detail",
        id=f"det-{akey}",
        hidden=True,
    )
    return row, detail


def pustaka_section():
    rows_details = []
    idx = 0
    for akey, meta in ANALISIS.items():
        rows_details.extend(_uji_row(idx, akey, meta))
        idx += 1

    # Opsi filter kelompok
    grup_opts = [Option("Semua Kelompok", value="", selected=True)]
    for gkey, (gtitle, _gicon) in GRUP.items():
        grup_opts.append(Option(gtitle, value=gkey))

    kat_opts = [
        Option("Semua Kategori", value="", selected=True),
        Option("Parametrik", value="p"),
        Option("Non-Parametrik", value="n"),
        Option("Multivariat", value="m"),
    ]

    toolbar = Div(
        Div(
            NotStr('<svg class="ic ic-search" width="15" height="15" viewBox="0 0 24 24" fill="none" '
                   'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                   'stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/>'
                   '<path d="m21 21-4.3-4.3"/></svg>'),
            Input(type="text", id="dt-q", placeholder="Cari nama uji, tujuan, asumsi, kata kunci\u2026",
                  autocomplete="off", **{"aria-label": "Cari uji statistik"}),
            Button("\u2715", id="dt-q-clear", cls="dt-q-clear", type="button", title="Bersihkan pencarian",
                   **{"aria-label": "Bersihkan pencarian"}),
            cls="dt-search",
        ),
        Div(
            Select(*grup_opts, id="dt-grup", **{"aria-label": "Filter kelompok uji"}),
            cls="dt-select",
        ),
        Div(
            Select(*kat_opts, id="dt-kat", **{"aria-label": "Filter kategori uji"}),
            cls="dt-select",
        ),
        Span(Span("20", id="dt-counter"), " uji", cls="dt-count"),
        Button(ICON_SVG("reset", 13), "Reset", id="dt-reset", type="button", cls="dt-reset"),
        cls="dt-toolbar",
    )

    table = Div(
        Table(
            Thead(
                Tr(
                    Th("No", cls="dt-sortable", data_sort="no", scope="col"),
                    Th("Nama Uji", cls="dt-sortable col-uji", data_sort="judul", scope="col"),
                    Th("Kelompok", cls="dt-sortable col-grup", data_sort="grup", scope="col"),
                    Th("Kategori", cls="dt-sortable col-kat", data_sort="kat", scope="col"),
                    Th("Tujuan Utama", cls="col-tujuan", scope="col"),
                    Th("", cls="dt-chev-head", scope="col"),
                )
            ),
            Tbody(*rows_details, id="dt-body"),
            id="dt-table",
        ),
        cls="dt-table-wrap",
    )

    empty = Div(
        ICON_SVG("search", 26),
        P("Tidak ada uji yang cocok dengan pencarian atau filter saat ini."),
        Span("Coba kata kunci lain, misalnya \u201crata-rata\u201d, \u201ckorelasi\u201d, atau \u201ckategorik\u201d.",
             cls="dt-empty-hint"),
        cls="dt-empty",
        id="dt-empty",
        hidden=True,
    )

    footer = Div(
        Div(
            Label("Tampilkan", **{"for": "dt-size"}),
            Select(
                Option("5", value="5"), Option("10", value="10", selected=True),
                Option("20", value="20"), Option("Semua", value="0"),
                id="dt-size", **{"aria-label": "Jumlah baris per halaman"},
            ),
            cls="dt-size-box",
        ),
        Div(id="dt-info", cls="dt-info", **{"aria-live": "polite"}),
        Div(id="dt-pager", cls="dt-pager", role="navigation",
            **{"aria-label": "Navigasi halaman tabel"}),
        cls="dt-footer",
    )

    return Section(
        Div(ICON_SVG("sliders", 16), H3("Pustaka Uji Statistik"), cls="sec-head"),
        P("Seluruh 20 analisis dalam satu tabel interaktif. Ketik kata kunci untuk mencari, "
          "sempitkan dengan filter kelompok/kategori, urutkan kolom sesuai kebutuhan, lalu "
          "klik baris uji untuk membuka teori lengkap: kegunaan, hipotesis, asumsi, rumus, "
          "cara membaca hasil, dan contoh penerapannya.", cls="th-intro"),
        Div(toolbar, table, empty, footer, cls="card dt-wrap anim-in d1"),
        cls="th-sec",
        id="th-pustaka",
    )


# ------------------------------------------------------------------
# ROUTES & SHARED NAV/FOOTER
# ------------------------------------------------------------------
def setup(rt):
    @rt("/teori")
    def get():
        return (
            Title("AseliPedas - Teori Uji Statistik"),
            teori_nav(),
            Main(
                teori_hero(),
                Div(
                    konsep_section(),
                    pustaka_section(),
                    cls="wrap teori-page",
                ),
                teori_footer(),
                Script(src="/js/teori.js?v=20261029b"),
            ),
        )


teori_nav = lambda: _NAV_FACTORY("/teori")
teori_footer = lambda: _FOOTER_FACTORY()

_NAV_FACTORY = None
_FOOTER_FACTORY = None


def register_shared(nav_factory, footer_factory):
    global _NAV_FACTORY, _FOOTER_FACTORY
    _NAV_FACTORY = nav_factory
    _FOOTER_FACTORY = footer_factory
