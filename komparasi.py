# -*- coding: utf-8 -*-
"""
AseliPedas - Halaman PERBANDINGAN FILE DATA (FastHTML Edition)
============================================================
Konversi dari aplikasi Streamlit "Komparasi" dengan fungsi yang sama:
  - Unggah 2 file data (format boleh berbeda): Excel, CSV/TXT/T tally, DBF,
    SPSS (.sav/.zsav), SQL dump, Access (.mdb/.accdb), Parquet, Stata (.dta),
    SAS (.sas7bdat/.xpt), JSON
  - Opsi pembacaan CSV/Excel: encoding, pemisah kolom, baris judul kolom,
    pemilihan sheet Excel
  - Pembandingan baris antar 2 file berdasarkan SATU ATAU BEBERAPA kolom
    kunci yang dipasangkan (kolom ke-1 File 1 ⇄ kolom ke-1 File 2, dst.)
  - Normalisasi nilai kunci: huruf kecil semua -> rapikan spasi ->
    hanya huruf & angka
  - Opsi: hanya cocokkan baris dengan semua kolom kunci terisi
  - Sorting hasil berdasarkan kolom kunci (naik/turun, prioritas kolom)
  - Hasil: metrik ringkasan, detail kunci (jumlah kemunculan + status),
    4 tabel (SAMA File 1/2, BEDA File 1/2), narasi analisis otomatis,
    unduh hasil ke Excel (.xlsx dua sheet: SAMA & BEDA)

Modul ini di-register dari app.py lewat komparasi.setup(rt) dan berbagi
navbar/footer dengan halaman lain via komparasi.register_shared(nav, footer).
"""
import io
import os
import re
import sqlite3
import tempfile
import uuid

import numpy as np
import pandas as pd
from fasthtml.common import (
    Div, Section, Main, H1, H3, P, Span, B, Button, Input, Select, Option,
    Label, Form, A, Title, Script, Table, Thead, Tbody, Tr, Th, Td, Ul, Li,
)
from starlette.requests import Request
from starlette.responses import Response

from inferens import (
    ICONS, ICON_SVG, inf_error_fragment, narasi_card, fmt_stat, size_str,
    load_data_inf, excel_sheets, df_table, f_multi, f_seg, f_toggle,
    _read_delimited,
)

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

try:
    from access_parser import AccessParser
    MDB_OK = True
except ImportError:
    MDB_OK = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Format & opsi pembacaan (paritas dengan versi Streamlit)
K_FORMATS = ["xlsx", "xls", "xlsm", "csv", "tsv", "txt", "dbf", "sav",
             "zsav", "sql", "mdb", "accdb", "parquet", "dta", "sas7bdat",
             "xpt", "json", "dat", "pkl"]
K_ACCEPT = ",".join(f".{e}" for e in K_FORMATS)
ENCODING_OPSI = [("utf-8", "UTF-8"), ("utf-8-sig", "UTF-8 dengan BOM"),
                 ("latin1", "Latin-1"), ("cp1252", "Windows-1252")]
SEP_OPSI = [("auto", "Deteksi otomatis"), ("koma", "Koma ( , )"),
            ("titikkoma", "Titik-koma ( ; )"), ("tab", "Tab"),
            ("pipa", "Pipa ( | )")]
SEP_MAP = {"koma": ",", "titikkoma": ";", "tab": "\t", "pipa": "|"}

K_SESSIONS = {}
MAX_K_SESSIONS = 6
MAX_TAMPIL = 500          # baris maksimum per tabel hasil di layar
MAX_DETAIL = 200          # baris maksimum tabel detail kunci


# ==========================================================
# NORMALISASI & KUNCI (paritas dengan versi Streamlit)
# ==========================================================
def normalize_text(value) -> str:
    """Huruf kecil semua -> hapus spasi berlebih -> hanya huruf & angka."""
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).lower()
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def buat_kunci(df: pd.DataFrame, kolom_list: list):
    """Kunci gabungan beberapa kolom (ternormalisasi) + mask kelengkapan."""
    komponen = [df[k].apply(normalize_text) for k in kolom_list]
    kunci = komponen[0]
    for k in komponen[1:]:
        kunci = kunci + "|" + k
    mask_lengkap = pd.concat([(c != "") for c in komponen], axis=1).all(axis=1)
    return kunci, mask_lengkap


def sort_df_aman(df: pd.DataFrame, kolom_list: list, naik: bool = True):
    """Sorting multi-kolom yang aman terhadap tipe campuran."""
    if not kolom_list:
        return df
    try:
        return df.sort_values(by=kolom_list, ascending=naik,
                              kind="stable", na_position="last")
    except TypeError:
        return df.sort_values(by=kolom_list, ascending=naik, kind="stable",
                              key=lambda s: s.astype(str), na_position="last")


def export_excel(sheets: dict) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return buffer.getvalue()


# ==========================================================
# PEMBACAAN FILE DENGAN OPSI (encoding / pemisah / baris judul)
# ==========================================================
def _baca_delimited(raw, encoding, sep, header_row, base_msg):
    """CSV/TXT dengan pilihan encoding, pemisah, dan baris judul kolom."""
    kandidat_enc = [encoding] + [e for e in ("utf-8", "utf-8-sig", "latin-1")
                                 if e != encoding]
    last_err = None
    for enc in kandidat_enc:
        try:
            teks = raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
        kandidat_sep = []
        if sep != "auto":
            kandidat_sep = [sep]
        else:
            terdeteksi = None
            try:
                import csv as _csv
                terdeteksi = _csv.Sniffer().sniff(
                    teks[:8192], delimiters=",;\t|").delimiter
            except Exception:
                pass
            kandidat_sep = ([terdeteksi] if terdeteksi else []) + \
                [",", ";", "\t", "|", None]
        for s in kandidat_sep:
            try:
                df = pd.read_csv(io.StringIO(teks), encoding=enc, sep=s,
                                 engine="python", header=max(0, header_row - 1))
                if df.shape[1] >= 1:
                    return df
            except Exception as e:
                last_err = e
    raise ValueError(f"{base_msg} ({last_err})")


def _parse_sql(raw: bytes) -> dict:
    """Baca SQL dump MySQL/SQLite ke tabel-tabel pandas (via sqlite in-memory)."""
    teks = raw.decode("utf-8", errors="replace")
    teks = re.sub(r"^\s*SET\s+[^;]+;", "", teks, flags=re.I | re.M)
    teks = re.sub(r"^\s*(LOCK|UNLOCK)\s+TABLES?[^;]*;", "", teks, flags=re.I | re.M)
    teks = re.sub(r"\)\s*ENGINE=[^;]*;", ");", teks, flags=re.I)
    teks = re.sub(r"\bAUTO_INCREMENT\s*=\s*\d+\s*", "", teks, flags=re.I)

    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    buffer = ""
    for line in teks.splitlines():
        buffer += line + "\n"
        if sqlite3.complete_statement(buffer):
            try:
                cur.execute(buffer)
            except sqlite3.Error:
                pass
            buffer = ""
    hasil = {}
    nama_tabel = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for t in nama_tabel:
        try:
            df = pd.read_sql(f'SELECT * FROM "{t}"', conn)
            if len(df) > 0:
                hasil[t] = df
        except Exception:
            continue
    conn.close()
    return hasil


def _parse_mdb(raw: bytes) -> dict:
    path = _tmpfile(raw, ".accdb")
    try:
        db = AccessParser(path)
        hasil = {}
        for nama in db.catalog:
            try:
                parsed = db.parse_table(nama)
                cols, rows = parsed.get("columns", []), parsed.get("data", [])
                df = (pd.DataFrame(rows) if rows and isinstance(rows[0], dict)
                      else pd.DataFrame(rows, columns=cols))
                if len(df) > 0:
                    hasil[str(nama)] = df
            except Exception:
                continue
        return hasil
    finally:
        if os.path.exists(path):
            os.unlink(path)


def _tmpfile(raw: bytes, suffix: str) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(raw)
    tmp.close()
    return tmp.name


def k_baca_file(raw: bytes, fname: str, opts: dict) -> pd.DataFrame:
    """Baca unggahan sesuai ekstensi + opsi pembacaan pengguna."""
    ext = os.path.splitext(fname)[1].lower().lstrip(".")
    enc = str(opts.get("encoding") or "utf-8")
    sep = SEP_MAP.get(str(opts.get("sep") or "auto"), "auto")
    hdr = int(opts.get("header") or 1) - 1
    hdr = max(0, hdr)

    if ext in ("csv", "tsv", "txt", "dat"):
        efektif = "\t" if ext == "tsv" else sep
        return _baca_delimited(raw, enc, efektif, hdr + 1, "Gagal membaca file CSV/TXT.")
    if ext in ("xlsx", "xls", "xlsm"):
        return pd.read_excel(io.BytesIO(raw), sheet_name=0, header=hdr)
    if ext == "dbf":
        if not DBF_OK:
            raise ValueError("Library dbfread belum terpasang. Jalankan: pip install dbfread")
        path = _tmpfile(raw, ".dbf")
        try:
            return pd.DataFrame(iter(DBF(path, load=True, encoding="latin1")))
        finally:
            os.remove(path)
    if ext in ("sav", "zsav"):
        if not SAV_OK:
            raise ValueError("Library pyreadstat belum terpasang. Jalankan: pip install pyreadstat")
        path = _tmpfile(raw, ".sav")
        try:
            df, _ = pyreadstat.read_sav(path)
            return df
        finally:
            os.remove(path)
    if ext == "sql":
        tabel_df = _parse_sql(raw)
        if not tabel_df:
            raise ValueError("Tidak ada tabel berisi data yang bisa dibaca dari file SQL ini.")
        # otomatis pakai tabel terbesar; nama tabel lain dilaporkan lewat catatan
        terbaik = max(tabel_df, key=lambda t: len(tabel_df[t]))
        df = tabel_df[terbaik].copy()
        df.attrs["catatan"] = (
            f"File SQL berisi {len(tabel_df)} tabel: {', '.join(tabel_df.keys())}. "
            f"Digunakan tabel '{terbaik}' ({len(df)} baris).")
        return df
    if ext in ("mdb", "accdb"):
        if not MDB_OK:
            raise ValueError("Library access-parser belum terpasang. Jalankan: pip install access-parser")
        hasil = _parse_mdb(raw)
        if not hasil:
            raise ValueError("Tidak ada tabel yang bisa dibaca dari file Access ini.")
        terbaik = max(hasil, key=lambda t: len(hasil[t]))
        df = hasil[terbaik].copy()
        df.attrs["catatan"] = (
            f"File Access berisi tabel: {', '.join(hasil.keys())}. "
            f"Digunakan tabel '{terbaik}' ({len(df)} baris).")
        return df
    if ext == "parquet":
        return pd.read_parquet(io.BytesIO(raw))
    if ext == "dta":
        return pd.read_stata(io.BytesIO(raw))
    if ext == "sas7bdat":
        return pd.read_sas(io.BytesIO(raw), format="sas7bdat")
    if ext == "xpt":
        return pd.read_sas(io.BytesIO(raw), format="xport")
    if ext == "json":
        try:
            return pd.read_json(io.BytesIO(raw))
        except ValueError:
            return pd.read_json(io.BytesIO(raw), lines=True)
    if ext in ("pkl", "pickle"):
        return pd.read_pickle(io.BytesIO(raw))
    return _baca_delimited(raw, enc, sep, hdr + 1, "Gagal membaca file teks.")


# ==========================================================
# DATA CONTOH (pasangan file produku: identik, tambahan, dan hilang)
# ==========================================================
def buat_data_contoh_komparasi():
    rng = np.random.default_rng(11)
    n = 45
    kode = [f"PRD-{i:03d}" for i in range(1, n + 1)]
    nama = [f"Produk {i:03d}" for i in range(1, n + 1)]
    kategori = rng.choice(["Elektronik", "Peralatan", "Aksesori"], n)
    harga = (rng.integers(50, 5000, n) * 1000).astype(int)
    stok = rng.integers(5, 200, n).astype(int)
    df1 = pd.DataFrame({"kode_produk": kode, "nama_produk": nama,
                        "kategori": kategori, "harga": harga, "stok": stok})

    # File 2: buang 7 baris (PRD-039..045), tambah 6 produk baru
    df2 = df1[~df1["kode_produk"].isin([f"PRD-{i:03d}" for i in range(39, 46)])].copy()
    tambahan = pd.DataFrame({
        "kode_produk": [f"PRD-{i:03d}" for i in range(51, 57)],
        "nama_produk": [f"Produk {i:03d}" for i in range(51, 57)],
        "kategori": rng.choice(["Elektronik", "Peralatan", "Aksesori"], 6),
        "harga": (rng.integers(50, 5000, 6) * 1000).astype(int),
        "stok": rng.integers(5, 200, 6).astype(int),
    })
    df2 = pd.concat([df2, tambahan], ignore_index=True)
    return df1, df2


# ==========================================================
# SESI
# ==========================================================
def _prune_k():
    while len(K_SESSIONS) > MAX_K_SESSIONS:
        oldest = next(iter(K_SESSIONS))
        K_SESSIONS.pop(oldest, None)


def _slot(s, i):
    return s.get(f"df{i}")


# ==========================================================
# KOMPONEN HALAMAN
# ==========================================================
def k_hero():
    return Div(
        Span(ICON_SVG("leftright", 13), "Perbandingan File Data", cls="eyebrow"),
        H1(
            "Cari baris yang ",
            Span("sama & berbeda", cls="grad-text"),
            " di antara dua file",
        ),
        P(
            "Unggah dua file data (boleh berbeda format), pilih kolom pembanding dari "
            "masing-masing file, dan aplikasi akan mencocokkan baris berdasarkan kunci "
            "ternormalisasi - lalu mengurutkan hasilnya agar mudah diverifikasi. "
            "Dilengkapi narasi ringkasan dan unduhan Excel dua sheet.",
            cls="hero-sub",
        ),
        Div(
            Div(
                Div(ICON_SVG("link", 16), cls="feature-ic"),
                Div(B("Kunci Multi-Kolom"),
                    Span("Pasangkan satu atau beberapa kolom, mis. Nama + Tanggal Lahir, "
                         "walau nama kolomnya berbeda antar file.")),
                cls="feature",
            ),
            Div(
                Div(ICON_SVG("shield", 16), cls="feature-ic"),
                Div(B("Nilai Dinormalisasi"),
                    Span("Huruf kecil semua, spasi dirapikan, karakter khusus dihapus - "
                         "'Andi Susanto' sama dengan 'andi_susanto'.")),
                cls="feature",
            ),
            Div(
                Div(ICON_SVG("download", 16), cls="feature-ic"),
                Div(B("Hasil Bisa Diunduh"),
                    Span("Tabel SAMA dan BEDA diurutkan lalu diunduh sebagai Excel "
                         "dua sheet siap lampiran laporan.")),
                cls="feature",
            ),
            cls="features anim-in d1 features-3",
        ),
        cls="hero",
    )


def _k_upload_card(slot, sid, s=None):
    """Kartu unggah untuk satu slot (dipakai ulang di halaman awal & workspace)."""
    no = int(slot)
    terisi = s is not None
    fmt_row = Div(*[Span(f.upper(), cls="fmt-chip") for f in K_FORMATS], cls="fmt-row")
    if terisi:
        df = s[f"df{no}"]
        catatan = getattr(df, "attrs", {}).get("catatan")
        banner = Div(
            Div(ICON_SVG("check", 20), cls="banner-ic"),
            Div(
                B(s[f"name{no}"]),
                Span(f"{len(df):,} baris \u00b7 {df.shape[1]:,} kolom \u00b7 "
                     f"{size_str(s[f'size{no}'])}", cls="banner-meta"),
                cls="banner-body",
            ),
            Button(ICON_SVG("reset", 15), "Ganti File",
                   cls="btn btn-ghost btn-sm",
                   hx_post="/komparasi/ganti", hx_target="#komparasi-workspace",
                   hx_swap="innerHTML", hx_include="closest form"),
            Input(type="hidden", name="slot", value=str(no)),
            Input(type="hidden", name="sid", value=sid),
            cls="banner anim-in",
        )
        anak = [banner]
        if catatan:
            anak.append(P(ICON_SVG("info", 13), " " + catatan, cls="note-row"))
        sheet_row = None
        sheets = s.get(f"sheets{no}")
        if sheets and len(sheets) > 1:
            opts = [Option(str(sh), value=str(sh),
                           selected=(str(sh) == str(s.get(f"sheet{no}") or sheets[0])))
                    for sh in sheets]
            sheet_row = Div(
                Label("Pilih sheet Excel", cls="f-label"),
                Select(*opts, name="sheet", cls="inp inp-select inp-select-sm",
                       hx_post="/komparasi/sheet", hx_trigger="change",
                       hx_target="#komparasi-workspace", hx_swap="innerHTML",
                       hx_include="closest div", hx_indicator="#sheet-loading"),
                Input(type="hidden", name="sid", value=sid),
                Input(type="hidden", name="slot", value=str(no)),
                Div(Span(cls="spinner spinner-sm"), "Memuat sheet...",
                    id="sheet-loading", cls="spinner-inline htmx-indicator"),
                cls="sheet-row",
            )
        if sheet_row is not None:
            anak.append(sheet_row)
        anak.append(fmt_row)
        return Form(Div(*anak, cls="upload-card card anim-in k-slot",
                        id=f"slot-{no}"),
                    id=f"upload-form-{no}")

    # --- kartu kosong: area unggah ---
    return Form(
        Div(
            Div(
                Div(f"FILE DATA {no}", cls="k-slot-tag"),
                Div(ICON_SVG("cloud", 26), cls="drop-ic"),
                H3(f"Unggah File Data {no}", cls="drop-title"),
                P("klik area ini untuk ", Span("memilih file", cls="link-like"),
                  " - Excel, CSV/TXT, DBF, SPSS, SQL, Access, Parquet, Stata, SAS, JSON",
                  cls="drop-hint"),
                id=f"dropzone-{no}",
                cls="dropzone k-dropzone",
            ),
            Input(type="file", name="file", id=f"file-input-{no}", accept=K_ACCEPT,
                  cls="sr-only"),
            Div(Div(id=f"upload-bar-{no}", cls="progress-bar"),
                id=f"upload-progress-{no}", cls="progress-wrap"),
            Div(id=f"upload-error-{no}"),
            Div(
                Div(
                    Label("Encoding (CSV/TXT)", cls="f-label"),
                    Select(*[Option(lbl, value=v) for v, lbl in ENCODING_OPSI],
                           name="encoding", cls="inp inp-select"),
                    cls="k-opt"),
                Div(
                    Label("Pemisah kolom", cls="f-label"),
                    Select(*[Option(lbl, value=v) for v, lbl in SEP_OPSI],
                           name="sep", cls="inp inp-select"),
                    cls="k-opt"),
                Div(
                    Label("Baris judul kolom", cls="f-label"),
                    Input(type="number", name="header", value="1", min=1, max=100,
                          step=1, cls="inp inp-num"),
                    cls="k-opt"),
                cls="k-opts",
            ),
            fmt_row,
            P(ICON_SVG("shield", 13),
              " File diproses sepenuhnya secara lokal di server - tidak dibagikan ke pihak mana pun.",
              cls="privacy-note"),
            Input(type="hidden", name="slot", value=str(no)),
            Input(type="hidden", name="sid", value=sid),
            cls="upload-card card anim-in k-slot",
            id=f"slot-{no}",
        ),
        id=f"upload-form-{no}",
    )


def _k_status_card(s):
    """Kartu status antara: menunggu kedua file / arahkan mengunggah."""
    def baris(no):
        ok = s is not None and f"df{no}" in s
        if ok:
            df = s[f"df{no}"]
            txt = f"{s[f'name{no}']} - {len(df):,} baris \u00d7 {df.shape[1]:,} kolom"
            cls = "k-status-ok"
            ic, icc = "check", "k-status-ic ok"
        else:
            txt = "Belum ada file yang diunggah"
            cls = "k-status-wait"
            ic, icc = "info", "k-status-ic"
        return Div(ICON_SVG(ic, 15), Span(f"File Data {no}"), Span(txt, cls="k-status-txt"),
                   cls=f"k-status-row {cls}")

    if s is None or not all(f"df{i}" in s for i in (1, 2)):
        return Div(
            Div(ICON_SVG("database", 26), cls="empty-ic empty-ic-sm"),
            H3("Status Kedua File"),
            baris(1), baris(2),
            P("Unggah KEDUA file untuk melanjutkan. Kedua file boleh berbeda format "
              "(misal: File 1 = Excel, File 2 = CSV).", cls="table-note"),
            Button(ICON_SVG("sparkles", 15), "Coba dengan Pasangan Data Contoh",
                   cls="btn btn-ghost btn-sm demo-btn",
                   hx_get="/komparasi/demo", hx_target="#komparasi-workspace",
                   hx_swap="innerHTML"),
            cls="empty-card anim-in k-status",
        )
    return None


def _k_select_pasangan(nama, label, pasangan_list, default="all"):
    """Select pemilihan kolom sorting: 'all' atau indeks pasangan kunci."""
    opts = [Option("Semua kolom pembanding (urut prioritas)", value="all",
                   selected=(default == "all"))]
    for i, (a, b) in enumerate(pasangan_list):
        opts.append(Option(f"Prioritas: {i + 1}. {a} \u21c4 {b}", value=str(i),
                           selected=(default == str(i))))
    return Div(
        Label(label, cls="f-label"),
        Select(*opts, name=nama, cls="inp inp-select"),
        cls="field",
    )


def _k_picker(sid, s):
    df1, df2 = s["df1"], s["df2"]
    kol1 = [str(c) for c in df1.columns]
    kol2 = [str(c) for c in df2.columns]
    return Section(
        Div(ICON_SVG("sliders", 17), H3("Pilih Kolom Pembanding"),
            Span("satu atau lebih kolom", cls="chip chip-cyan"), cls="sec-head"),
        P("Kolom ke-1 File 1 dipasangkan dengan kolom ke-1 File 2, dst. - nama kolomnya "
          "boleh berbeda (contoh: Nama, Tgl Lahir \u21c4 Nama Lengkap, Tanggal Lahir). "
          "Nilai kunci otomatis dinormalisasi: huruf kecil semua \u2192 spasi dirapikan \u2192 "
          "hanya huruf & angka. Hasil SAMA dan BEDA akan diurutkan berdasarkan kolom "
          "pembanding agar mudah diverifikasi.", cls="picker-note"),
        Form(
            Div(
                f_multi("kolom1", "Kolom kunci dari File 1", kol1,
                        hint=f"Kolom tersedia di File 1: {len(kol1)} kolom."),
                f_multi("kolom2", "Kolom kunci dari File 2", kol2,
                        hint=f"Kolom tersedia di File 2: {len(kol2)} kolom."),
                cls="param-grid"),
            Div(
                f_toggle("sortaktif", "Urutkan hasil berdasarkan kolom pembanding",
                         checked=True),
                f_seg("arah", "Arah pengurutan",
                      [("naik", "Naik (A\u2192Z, 0\u21929)"),
                       ("turun", "Turun (Z\u2192A, 9\u21920)")], default="naik"),
                _k_select_pasangan("sortkolom", "Prioritas kolom sorting",
                                   list(zip(kol1, kol2))),
                f_toggle("lengkap", "Hanya cocokkan baris dengan SEMUA kolom kunci terisi",
                         checked=True),
                cls="param-grid"),
            Input(type="hidden", name="sid", value=sid),
            Div(
                Button(ICON_SVG("zap", 16), "BANDINGKAN SEKARANG", type="submit",
                       cls="btn btn-primary btn-lg"),
                Div(Span(cls="spinner spinner-sm"), "Memproses perbandingan & sorting...",
                    id="run-loading", cls="spinner-inline htmx-indicator"),
                cls="run-row"),
            hx_post=f"/komparasi/run/{sid}", hx_target="#komparasi-hasil",
            hx_swap="innerHTML", hx_indicator="#run-loading",
        ),
        cls="card anim-in d2 picker-card",
    )


def k_workspace(s=None):
    """Fragmen isi area kerja: 2 slot unggah + status + (picker bila lengkap).
    Tanpa id - id 'komparasi-workspace' dipasang oleh halaman/swap target."""
    sid = ""
    if s is not None:
        sid = s["sid"]
    parts = [
        Div(
            _k_upload_card(1, sid, s if (s and "df1" in s) else None),
            _k_upload_card(2, sid, s if (s and "df2" in s) else None),
            cls="k-duo",
        ),
    ]
    status = _k_status_card(s)
    if status is not None:
        parts.append(status)
    else:
        parts.append(_k_picker(sid, s))
    parts.append(Div(P("Hasil perbandingan akan tampil di area ini setelah Anda menekan "
                        "tombol BANDINGKAN SEKARANG.", cls="result-hint"),
                     id="komparasi-hasil"))
    return Div(*parts, cls="k-ws")


def _info_format_card():
    """Kartu penjelasan format didukung & aturan normalisasi (paritas expander Streamlit)."""
    lib_rows = [
        ("Excel .xlsx / .xlsm", "openpyxl"), (".xls (lama)", "xlrd"),
        (".csv / .tsv / .txt", "bawaan pandas"), (".dbf", "dbfread"),
        (".sav / .zsav (SPSS)", "pyreadstat"), (".sql (dump)", "bawaan (sqlite3)"),
        (".mdb / .accdb (Access)", "access-parser"), (".parquet", "pyarrow"),
        (".dta (Stata) / .sas7bdat / .xpt", "bawaan pandas"), (".json", "bawaan pandas"),
    ]
    tabel = Table(
        Thead(Tr(Th("Format"), Th("Library"))),
        Tbody(*[Tr(Td(a), Td(b)) for a, b in lib_rows]),
        cls="data-table inf-table k-lib-table",
    )
    return Section(
        Div(ICON_SVG("info", 17), H3("Cara Kerja & Format Didukung"), cls="sec-head"),
        Div(
            Div(
                Div(ICON_SVG("shuffle", 14), Span("Aturan Normalisasi Kunci"),
                    cls="th-sec-title"),
                Ul(
                    Li("Huruf besar/kecil dianggap sama (semua diubah ke huruf kecil)."),
                    Li("Spasi berlebih dirapikan; karakter selain huruf & angka dihapus."),
                    Li("Contoh: \"Andi  Susanto-77\" dan \"andi susanto77\" menjadi kunci yang sama."),
                    cls="use-list"),
                cls="th-col"),
            Div(
                Div(ICON_SVG("list", 14), Span("Aturan Pencocokan"),
                    cls="th-sec-title"),
                Ul(
                    Li("Baris dianggap SAMA bila kunci gabungannya ditemukan di file lain."),
                    Li("Baris BEDA = kuncinya tidak ditemukan di file lain (hanya ada di salah satu)."),
                    Li("Opsi 'SEMUA kolom kunci terisi' melewati baris yang kuncinya kosong/lepas."),
                    Li("File SQL/Access: otomatis memakai tabel terbesar; catatannya tampil di kartu file."),
                    cls="use-list"),
                cls="th-col"),
            cls="th-cols"),
        Div(tabel, cls="table-wrap"),
        cls="card anim-in k-info-card",
    )


# ==========================================================
# INTI PERBANDINGAN
# ==========================================================
def proses_bandingkan(df1, df2, kolom1_list, kolom2_list, sort_aktif, naik,
                      sort_idx, hanya_lengkap):
    """Logika inti paritas dengan versi Streamlit.
    Mengembalikan dict berisi 4 dataframe hasil + statistik kunci."""
    d1, d2 = df1.copy(), df2.copy()
    kunci_s1, lengkap1 = buat_kunci(d1, kolom1_list)
    kunci_s2, lengkap2 = buat_kunci(d2, kolom2_list)
    d1["_kunci"], d2["_kunci"] = kunci_s1, kunci_s2

    if hanya_lengkap:
        layak1 = lengkap1 & (d1["_kunci"] != "")
        layak2 = lengkap2 & (d2["_kunci"] != "")
    else:
        layak1 = d1["_kunci"] != ""
        layak2 = d2["_kunci"] != ""

    kunci1 = set(d1.loc[layak1, "_kunci"])
    kunci2 = set(d2.loc[layak2, "_kunci"])
    m1 = d1["_kunci"].isin(kunci2)
    m2 = d2["_kunci"].isin(kunci1)

    sort1 = [kolom1_list[i] for i in sort_idx if i < len(kolom1_list)]
    sort2 = [kolom2_list[i] for i in sort_idx if i < len(kolom2_list)]

    def proses(df, mask, kolom_sort):
        out = df[mask].drop(columns="_kunci")
        if sort_aktif:
            out = sort_df_aman(out, kolom_sort, naik)
        return out.reset_index(drop=True)

    return {
        "sama1": proses(d1, m1, sort1),
        "sama2": proses(d2, m2, sort2),
        "beda1": proses(d1, ~m1, sort1),
        "beda2": proses(d2, ~m2, sort2),
        "vc1": d1.loc[layak1, "_kunci"].value_counts(),
        "vc2": d2.loc[layak2, "_kunci"].value_counts(),
        "sort1": sort1 if sort_aktif else [],
        "sort2": sort2 if sort_aktif else [],
        "naik": naik,
        "lewati1": int((~layak1).sum()),
        "lewati2": int((~layak2).sum()),
    }


def _k_narasi(h, df1, df2, kolom1_list, kolom2_list, nama1, nama2):
    """Narasi analisis otomatis bahasa Indonesia untuk hasil perbandingan."""
    sama1, sama2 = len(h["sama1"]), len(h["sama2"])
    beda1, beda2 = len(h["beda1"]), len(h["beda2"])
    vc1, vc2 = h["vc1"], h["vc2"]
    semua_kunci = sorted(set(vc1.index) | set(vc2.index))
    n_unik = len(semua_kunci)
    n_cocok = sum(1 for k in semua_kunci if vc1.get(k, 0) and vc2.get(k, 0))
    n_hanya1 = sum(1 for k in semua_kunci if vc1.get(k, 0) and not vc2.get(k, 0))
    n_hanya2 = sum(1 for k in semua_kunci if vc2.get(k, 0) and not vc1.get(k, 0))

    def pct(x, dasar):
        return f"{(x / dasar * 100):.1f}%" if dasar else "0%"

    label1 = " + ".join(map(str, kolom1_list)) or "-"
    label2 = " + ".join(map(str, kolom2_list)) or "-"

    paras = [
        f"File 1 ({nama1}) berisi {len(df1):,} baris data dan File 2 ({nama2}) berisi "
        f"{len(df2):,} baris data. Pembandingan dilakukan dengan mencocokkan baris "
        f"melalui kolom kunci '{label1}' pada File 1 terhadap kolom '{label2}' pada "
        f"File 2, setelah nilai kunci dinormalisasi (huruf kecil, spasi dirapikan, "
        f"tanpa karakter khusus).",

        f"Ditemukan {sama1:,} baris File 1 yang kuncinya juga ada di File 2 (baris "
        f"SAMA) dan {beda1:,} baris File 1 yang kuncinya tidak ditemukan di File 2; "
        f"sebaliknya {sama2:,} baris File 2 berhasil dicocokkan dan {beda2:,} baris "
        f"hanya ada di File 2.",

        f"Dari {n_unik:,} kunci unik hasil penggabungan kedua file, sebanyak "
        f"{n_cocok:,} kunci ({pct(n_cocok, n_unik)}) muncul di kedua file, {n_hanya1:,} "
        f"kunci ({pct(n_hanya1, n_unik)}) hanya di File 1, dan {n_hanya2:,} kunci "
        f"({pct(n_hanya2, n_unik)}) hanya di File 2.",
    ]

    if beda1 == 0 and beda2 == 0:
        paras.append(
            "Simpulan: kedua file memiliki isi yang SEPENUHNYA SEPADAN pada kolom "
            "kunci yang dipilih - tidak ada baris yang hanya ada di salah satu file, "
            "sehingga data dapat digabungkan dengan aman.")
    else:
        paras.append(
            f"Simpulan: terdapat ketidaksesuaian antara kedua file, yaitu "
            f"{beda1 + beda2:,} baris (kunci tidak tercocok). Gunakan tabel 'BEDA' di "
            f"bawah untuk memverifikasi baris yang hanya ada di salah satu file "
            f"sebelum menggabungkan data.")

    if h["sort1"]:
        arah_txt = "naik (A\u2192Z, 0\u21929)" if h["naik"] else "turun (Z\u2192A, 9\u21920)"
        paras.append(
            f"Hasil diurutkan berdasarkan kolom kunci - File 1: "
            f"{', '.join(map(str, h['sort1']))} | File 2: {', '.join(map(str, h['sort2']))} - "
            f"secara {arah_txt} agar baris yang sepadan berdekatan dan mudah diverifikasi.")

    dup1 = int((vc1 > 1).sum())
    dup2 = int((vc2 > 1).sum())
    if dup1 or dup2:
        paras.append(
            f"Perhatian: terdeteksi kunci ganda - {dup1} kunci muncul lebih dari satu kali "
            f"di File 1 dan {dup2} kunci di File 2. Baris duplikat tetap diikutsertakan "
            f"per kemunculannya; periksa duplikasi data bila tidak diharapkan.")
    lew1, lew2 = h["lewati1"], h["lewati2"]
    if lew1 or lew2:
        paras.append(
            f"Sebanyak {lew1:,} baris File 1 dan {lew2:,} baris File 2 dilewati karena "
            f"memiliki kolom kunci yang kosong atau tidak lengkap (opsi 'SEMUA kolom "
            f"kunci terisi' aktif).")
    return paras


# ==========================================================
# RENDER HASIL
# ==========================================================
def _tabel_hasil(df, judul_caption):
    nmax = MAX_TAMPIL
    tbl = df_table(df.head(nmax), index=False)
    note = None
    if len(df) > nmax:
        note = P(f"Menampilkan {nmax:,} dari {len(df):,} baris - unduh ke Excel untuk "
                 f"melihat seluruhnya.", cls="table-note")
    anak = [Div(P(judul_caption, cls="table-note")), Div(tbl, cls="table-wrap")]
    if note is not None:
        anak.append(note)
    return anak


def render_hasil_k(sid, s, h, df1, df2, kolom1_list, kolom2_list, nama1, nama2):
    paras = _k_narasi(h, df1, df2, kolom1_list, kolom2_list, nama1, nama2)
    label1 = " + ".join(map(str, kolom1_list))
    label2 = " + ".join(map(str, kolom2_list))

    parts = [
        Div(
            Div(ICON_SVG("leftright", 20), cls="res-head-ic"),
            Div(
                Div(H3("Hasil \u2014 Perbandingan File Data"), cls="res-head-title"),
                Span(f"kunci: {label1} \u21c4 {label2}", cls="chip chip-pink"),
                Span("terurut & siap dilaporkan" if h["sort1"] else "siap dilaporkan",
                     cls="chip"),
                cls="res-head",
            ),
            cls="res-head-row anim-in",
        ),
        narasi_card(paras),
    ]

    # metrik ringkasan (paritas 4 metrik Streamlit + konteks jumlah baris)
    metrik = [
        ("check", "Sama \u2014 File 1", len(h["sama1"])),
        ("check", "Sama \u2014 File 2", len(h["sama2"])),
        ("alert", "Beda \u2014 File 1", len(h["beda1"])),
        ("alert", "Beda \u2014 File 2", len(h["beda2"])),
    ]
    parts.append(Div(*[
        Div(
            Div(ICON_SVG(ic, 15), cls="metric-ic"),
            Span(lbl, cls="metric-label"),
            Div(f"{val:,}", cls="metric-val"),
            cls="metric-card",
        ) for ic, lbl, val in metrik
    ], cls="metrics-grid anim-in"))

    # detail kunci (paritas expander Streamlit)
    vc1, vc2 = h["vc1"], h["vc2"]
    semua_kunci = sorted(set(vc1.index) | set(vc2.index))
    detil = pd.DataFrame({"kunci": semua_kunci})
    detil["jumlah di File 1"] = detil["kunci"].map(vc1).fillna(0).astype(int)
    detil["jumlah di File 2"] = detil["kunci"].map(vc2).fillna(0).astype(int)
    detil["status"] = detil.apply(
        lambda r: "cocok" if r["jumlah di File 1"] and r["jumlah di File 2"]
        else ("hanya File 1" if r["jumlah di File 1"] else "hanya File 2"), axis=1)
    parts.append(Section(
        Div(ICON_SVG("hash", 16), H3("Detail Kunci Perbandingan"),
            Span("nilai ternormalisasi & jumlah kemunculan", cls="chip"), cls="sec-head"),
        Div(df_table(detil.head(MAX_DETAIL), index=False), cls="table-wrap"),
        P(f"Menampilkan {min(MAX_DETAIL, len(detil)):,} dari {len(detil):,} kunci unik "
          f"(diurutkan A\u2192Z).", cls="table-note"),
        cls="card anim-in"))

    # 4 tabel hasil dalam satu kartu tab
    def tab_btn(key, lbl, ic, active):
        return Button(ICON_SVG(ic, 15), lbl,
                      cls=f"tab-btn{' active' if active else ''}",
                      data_tab=key, type="button")

    sama1, sama2 = h["sama1"], h["sama2"]
    beda1, beda2 = h["beda1"], h["beda2"]
    panels = [
        Div(*_tabel_hasil(sama1,
             f"Kunci '{label1}' (setelah normalisasi) DITEMUKAN di File 2"),
            cls="tab-panel active", data_panel="tab-s1"),
        Div(*_tabel_hasil(sama2,
             f"Kunci '{label2}' (setelah normalisasi) DITEMUKAN di File 1"),
            cls="tab-panel", data_panel="tab-s2"),
        Div(*_tabel_hasil(beda1,
             f"Kunci '{label1}' TIDAK ditemukan di File 2 (baris hanya ada di File 1)"),
            cls="tab-panel", data_panel="tab-b1"),
        Div(*_tabel_hasil(beda2,
             f"Kunci '{label2}' TIDAK ditemukan di File 1 (baris hanya ada di File 2)"),
            cls="tab-panel", data_panel="tab-b2"),
    ]
    parts.append(Section(
        Div(
            tab_btn("tab-s1", "Sama \u2014 File 1", "check", True),
            tab_btn("tab-s2", "Sama \u2014 File 2", "check", False),
            tab_btn("tab-b1", "Beda \u2014 File 1", "alert", False),
            tab_btn("tab-b2", "Beda \u2014 File 2", "alert", False),
            cls="tab-bar"),
        *panels,
        cls="card anim-in tabs-card"))

    # unduhan Excel dua sheet (paritas Streamlit) - disimpan di sesi
    bytes_sama = export_excel({"SAMA File1": h["sama1"], "SAMA File2": h["sama2"]})
    bytes_beda = export_excel({"BEDA File1": h["beda1"], "BEDA File2": h["beda2"]})
    s["dl"]["sama"] = ("data_sama.xlsx", bytes_sama)
    s["dl"]["beda"] = ("data_beda.xlsx", bytes_beda)
    parts.append(Div(
        A(ICON_SVG("download", 15), "Unduh data SAMA (.xlsx)",
          href=f"/komparasi/dl/{sid}/sama", cls="btn btn-success btn-sm",
          download="data_sama.xlsx"),
        A(ICON_SVG("download", 15), "Unduh data BEDA (.xlsx)",
          href=f"/komparasi/dl/{sid}/beda", cls="btn btn-success btn-sm",
          download="data_beda.xlsx"),
        cls="dl-row anim-in"))

    return Div(*parts, cls="res-root")


# ==========================================================
# ROUTES
# ==========================================================
def setup(rt):
    @rt("/komparasi")
    def get():
        return (
            Title("AseliPedas - Perbandingan File Data"),
            _NAV_FACTORY("/komparasi"),
            Main(
                k_hero(),
                Div(
                    _info_format_card(),
                    Div(k_workspace(None), id="komparasi-workspace", cls="wrap"),
                    cls="wrap"),
                _FOOTER_FACTORY(),
                Script(src="/js/komparasi.js"),
            ),
        )

    @rt("/komparasi/upload")
    async def post(req: Request):
        try:
            form = await req.form()
            up = form.get("file")
            fname = getattr(up, "filename", "") or ""
            slot = str(form.get("slot") or "1")
            sid = str(form.get("sid") or "")
            if slot not in ("1", "2"):
                return inf_error_fragment("Slot file tidak dikenal.")
            if not fname:
                return inf_error_fragment(
                    f"Tidak ada file yang dipilih pada File Data {slot}. "
                    f"Silakan pilih file terlebih dahulu.")
            data = await up.read()
            ext = os.path.splitext(fname)[1].lower().lstrip(".")
            if ext not in K_FORMATS:
                return inf_error_fragment(
                    f"Format .{ext or '(tanpa ekstensi)'} belum didukung. "
                    f"Gunakan: {', '.join('.' + f for f in K_FORMATS)}.")
            opts = {
                "encoding": str(form.get("encoding") or "utf-8"),
                "sep": str(form.get("sep") or "auto"),
                "header": str(form.get("header") or "1"),
            }
            df = k_baca_file(data, fname, opts)
            if df.shape[0] == 0:
                return inf_error_fragment(
                    "File berhasil dibaca tetapi tidak berisi satu baris data pun.")
            if df.shape[1] == 0:
                return inf_error_fragment(
                    "File berhasil dibaca tetapi tidak memiliki kolom apa pun.")
            s = K_SESSIONS.get(sid)
            if s is None:
                sid = uuid.uuid4().hex[:10]
                s = {"sid": sid, "dl": {}}
            else:
                s["dl"] = {}  # unduhan lama tidak berlaku saat file diganti
            sheets = None
            if ext in ("xls", "xlsx", "xlsm"):
                try:
                    sheets = excel_sheets(data)
                except Exception:
                    sheets = None
            s[f"df{slot}"] = df
            s[f"name{slot}"] = fname
            s[f"size{slot}"] = len(data)
            s[f"raw{slot}"] = data if (sheets and len(sheets) > 1) else None
            s[f"sheets{slot}"] = sheets
            s[f"sheet{slot}"] = sheets[0] if sheets else None
            s[f"opts{slot}"] = opts
            s["dl"] = s.get("dl") or {}
            K_SESSIONS[sid] = s
            _prune_k()
            return k_workspace(s)
        except Exception as e:
            return inf_error_fragment(f"Gagal membaca file: {e}")

    @rt("/komparasi/sheet")
    async def post(req: Request):
        form = await req.form()
        sid = str(form.get("sid") or "")
        slot = str(form.get("slot") or "1")
        sheet = str(form.get("sheet") or "")
        s = K_SESSIONS.get(sid)
        if not s or not s.get(f"raw{slot}"):
            return inf_error_fragment("Sesi tidak ditemukan atau file bukan Excel multi-sheet.")
        try:
            opts = s.get(f"opts{slot}") or {}
            hdr = max(0, int(opts.get("header") or 1) - 1)
            df = pd.read_excel(io.BytesIO(s[f"raw{slot}"]), sheet_name=sheet, header=hdr)
            s[f"df{slot}"] = df
            s[f"sheet{slot}"] = sheet
            return k_workspace(s)
        except Exception as e:
            return inf_error_fragment(f"Gagal membaca sheet: {e}")

    @rt("/komparasi/ganti")
    async def post(req: Request):
        form = await req.form()
        sid = str(form.get("sid") or "")
        slot = str(form.get("slot") or "1")
        s = K_SESSIONS.get(sid)
        if s is not None:
            for pre in ("df", "name", "size", "raw", "sheets", "sheet", "opts"):
                s.pop(f"{pre}{slot}", None)
            s["dl"] = {}
        return k_workspace(s)

    @rt("/komparasi/demo")
    def get():
        df1, df2 = buat_data_contoh_komparasi()
        sid = uuid.uuid4().hex[:10]
        s = {"sid": sid, "dl": {}}
        for i, df in ((1, df1), (2, df2)):
            s[f"df{i}"] = df
            s[f"name{i}"] = f"contoh_file_{i}.csv"
            s[f"size{i}"] = len(df.to_csv(index=False).encode("utf-8"))
            s[f"raw{i}"] = None
            s[f"sheets{i}"] = None
            s[f"sheet{i}"] = None
            s[f"opts{i}"] = {"encoding": "utf-8", "sep": "auto", "header": "1"}
        K_SESSIONS[sid] = s
        _prune_k()
        return k_workspace(s)

    @rt("/komparasi/run/{sid}")
    async def post(sid: str, req: Request):
        s = K_SESSIONS.get(sid)
        if not s or "df1" not in s or "df2" not in s:
            return inf_error_fragment(
                "Sesi data tidak ditemukan atau salah satu file belum diunggah. "
                "Silakan unggah ulang kedua file.")
        form = await req.form()
        kolom1_list = [str(v) for v in form.getlist("kolom1")]
        kolom2_list = [str(v) for v in form.getlist("kolom2")]
        df1, df2 = s["df1"], s["df2"]

        if not kolom1_list and not kolom2_list:
            return inf_error_fragment(
                "Pilih minimal satu kolom pembanding dari masing-masing file.",
                kind="warn")
        if len(kolom1_list) != len(kolom2_list):
            return inf_error_fragment(
                f"Jumlah kolom pembanding tidak sepadan: File 1 = {len(kolom1_list)} kolom, "
                f"File 2 = {len(kolom2_list)} kolom. Samakan jumlahnya lalu coba lagi.")
        hilang1 = [k for k in kolom1_list if k not in df1.columns]
        hilang2 = [k for k in kolom2_list if k not in df2.columns]
        if hilang1 or hilang2:
            return inf_error_fragment(
                f"Kolom pembanding tidak ditemukan: File 1: {', '.join(hilang1) or '-'} | "
                f"File 2: {', '.join(hilang2) or '-'}.")
        sort_aktif = str(form.get("sortaktif") or "") in ("on", "1", "True", "true")
        naik = str(form.get("arah") or "naik") == "naik"
        lengkap = str(form.get("lengkap") or "") in ("on", "1", "True", "true")
        sk = str(form.get("sortkolom") or "all")
        if sk == "all":
            sort_idx = list(range(len(kolom1_list)))
        else:
            try:
                sort_idx = [int(sk)]
            except ValueError:
                sort_idx = list(range(len(kolom1_list)))

        try:
            h = proses_bandingkan(df1, df2, kolom1_list, kolom2_list, sort_aktif,
                                  naik, sort_idx, lengkap)
        except Exception as e:
            return inf_error_fragment(f"Terjadi kesalahan saat memproses perbandingan: {e}")
        return render_hasil_k(sid, s, h, df1, df2, kolom1_list, kolom2_list,
                              s["name1"], s["name2"])

    @rt("/komparasi/dl/{sid}/{key}")
    def get(sid: str, key: str):
        s = K_SESSIONS.get(sid)
        if not s:
            return Response("Sesi tidak ditemukan. Silakan unggah ulang file.",
                            status_code=404, media_type="text/plain")
        item = s.get("dl", {}).get(key)
        if not item:
            return Response("Berkas unduhan tidak ditemukan atau telah kedaluwarsa. "
                            "Jalankan kembali perbandingannya.",
                            status_code=404, media_type="text/plain")
        fname, blob = item
        return Response(
            blob,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{os.path.basename(fname)}"'})


# ==========================================================
# NAV & FOOTER SHARED (dirakit dari app.py agar konsisten)
# ==========================================================
_NAV_FACTORY = None
_FOOTER_FACTORY = None


def register_shared(nav_factory, footer_factory):
    global _NAV_FACTORY, _FOOTER_FACTORY
    _NAV_FACTORY = nav_factory
    _FOOTER_FACTORY = footer_factory
