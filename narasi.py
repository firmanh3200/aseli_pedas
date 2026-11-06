# -*- coding: utf-8 -*-
"""
AseliPedas - Generator Narasi Analisis Otomatis
=============================================
Menghasilkan narasi interpretasi (bahasa Indonesia) untuk setiap hasil
perhitungan statistik, sehingga pengguna mendapatkan teks siap laporan
di samping angka dan tabel.

Fungsi publik:
  - buat_narasi(akey, h, alpha)          -> list[str] untuk halaman inferens
  - narasi_dasar_kolom(nama, s_all, kolom) -> list[str] detail kolom dasar
  - narasi_dasar_ringkasan(df, kolom_num)  -> list[str] ringkasan semua kolom
  - narasi_dasar_kategorik(df, kolom_kat)  -> list[str] ringkasan kategorik

Semua builder defensif: kegagalan satu analisis tidak pernah merusak hasil.
"""
import math

import numpy as np
import pandas as pd
from scipy import stats as sps


# ==========================================================
# FORMAT ANGKA
# ==========================================================
def _f(v, d=4):
    try:
        if v is None:
            return "-"
        if isinstance(v, (float, np.floating)) and math.isnan(v):
            return "-"
        pf = float(v)
    except (TypeError, ValueError):
        return str(v)
    if math.isnan(pf):
        return "-"
    if abs(pf) >= 1e15:
        return f"{pf:.3e}"
    if pf == int(pf) and abs(pf) < 1e9:
        return f"{int(pf):,}"
    if abs(pf) >= 100:
        return f"{pf:,.1f}"
    s = f"{pf:.{d}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def _pv(p):
    """String perbandingan p-value lengkap dengan operator, mis. '< 0.0001' atau '= 0.0301'."""
    try:
        pf = float(p)
    except (TypeError, ValueError):
        return "= " + str(p)
    if math.isnan(pf):
        return "= -"
    if pf < 1e-4:
        return "< 0.0001"
    return f"= {pf:.4f}"


def _pc(x, d=1):
    try:
        return f"{float(x) * 100:.{d}f}%"
    except (TypeError, ValueError):
        return "-"


def _sig(p, alpha):
    try:
        return (not math.isnan(float(p))) and float(p) < float(alpha)
    except (TypeError, ValueError):
        return False


def _angka(val):
    """Coba ubah string metrik menjadi float."""
    try:
        return float(str(val).replace(",", ""))
    except (TypeError, ValueError):
        return None


# ==========================================================
# KATEGORI INTERPRETASI
# ==========================================================
def _kat_d(d):
    if d is None:
        return ""
    a = abs(d)
    if a < 0.2:
        return "sangat kecil"
    if a < 0.5:
        return "kecil"
    if a < 0.8:
        return "sedang"
    return "besar"


def _kat_eta(e):
    if e is None:
        return ""
    if e < 0.01:
        return "sangat kecil"
    if e < 0.06:
        return "kecil"
    if e < 0.14:
        return "sedang"
    return "besar"


def _kat_v(v):
    if v is None:
        return ""
    if v < 0.1:
        return "sangat lemah"
    if v < 0.3:
        return "lemah"
    if v < 0.5:
        return "sedang"
    return "kuat"


def _kat_r(r):
    if r is None:
        return ""
    a = abs(r)
    if a < 0.2:
        return "sangat lemah"
    if a < 0.4:
        return "lemah"
    if a < 0.6:
        return "sedang"
    if a < 0.8:
        return "kuat"
    return "sangat kuat"


def _kat_r_efek(r):
    if r is None:
        return ""
    a = abs(r)
    if a < 0.1:
        return "sangat kecil"
    if a < 0.3:
        return "kecil"
    if a < 0.5:
        return "sedang"
    return "besar"


def _kat_kmo(k):
    if k is None:
        return ""
    if k < 0.5:
        return "tidak memadai"
    if k < 0.6:
        return "kurang (miserable)"
    if k < 0.7:
        return "sedang (mediocre)"
    if k < 0.8:
        return "baik (middling)"
    if k < 0.9:
        return "meritorious (bagus)"
    return "marvelous (sangat bagus)"


def _kat_sil(s):
    if s is None or math.isnan(s):
        return ""
    if s < 0.25:
        return "struktur cluster lemah"
    if s < 0.5:
        return "struktur cluster cukup lemah namun dapat dipertimbangkan"
    if s < 0.7:
        return "struktur cluster masuk akal (reasonable)"
    return "struktur cluster kuat"


def _kat_w(w):
    if w is None:
        return ""
    if w < 0.1:
        return "konsordansi sangat lemah"
    if w < 0.3:
        return "konsordansi lemah"
    if w < 0.5:
        return "konsordansi sedang"
    if w < 0.7:
        return "konsordansi kuat"
    return "konsordansi sangat kuat"


def _arah_skew(s):
    if s is None or math.isnan(s):
        return ""
    if abs(s) < 0.5:
        return "relatif simetris"
    return "menceng ke kanan (positif)" if s > 0 else "menceng ke kiri (negatif)"


def _cv_kat(cv):
    if cv is None or math.isnan(cv):
        return ""
    if cv < 10:
        return "sangat homogen"
    if cv < 20:
        return "homogen"
    if cv < 30:
        return "cukup beragam"
    return "sangat beragam"


# ==========================================================
# PENGAMBILAN DATA DARI OBJEK Hasil
# ==========================================================
def _uji(h, *prefiks):
    for label, st, pv, al in getattr(h, "tests", []):
        for pr in prefiks:
            if str(label).startswith(pr):
                return str(label), st, pv, float(al)
    return None


def _tab(h, *prefiks):
    for judul, df, note in getattr(h, "tables", []):
        for pr in prefiks:
            if str(judul).startswith(pr):
                return str(judul), df, (note or "")
    return None


def _met(h, *prefiks):
    for lbl, val, ic in getattr(h, "metrics", []):
        for pr in prefiks:
            if str(lbl).startswith(pr):
                return str(val)
    return None


def _kep(p, alpha):
    """Frasa keputusan hipotesis."""
    return "ditolak" if _sig(p, alpha) else "gagal ditolak"


def _pvs(p, alpha):
    """Frasa perbandingan p-value dengan alpha."""
    return "lebih kecil daripada" if _sig(p, alpha) else "lebih besar daripada"


# ==========================================================
# 1) REGRESI LINEAR (OLS)
# ==========================================================
def _narasi_ols(h, alpha):
    r2 = _angka(_met(h, "R²") or "")
    adj = _angka(_met(h, "Adj. R²") or "")
    pf = _angka(_met(h, "p-value F-statistik") or "")
    n = _met(h, "n Observasi") or "-"
    par = []
    par.append(
        f"Analisis regresi linear dijalankan untuk memodelkan hubungan antara variabel dependen "
        f"dan satu atau lebih variabel independen berdasarkan {n} observasi. "
        f"Model yang dihasilkan mampu menjelaskan {_pc(r2 if r2 else 0)} variasi variabel dependen "
        f"(R² = {_f(r2)}; R² tersesuaikan = {_f(adj)}). "
        + (f"Nilai p-value F-statistik sebesar {_pv(pf)} "
           f"{'lebih kecil daripada' if _sig(pf, alpha) else 'lebih besar daripada'} α ({_f(alpha)}), sehingga model "
           f"{'signifikan secara keseluruhan dan layak digunakan untuk prediksi' if _sig(pf, alpha) else 'belum signifikan secara keseluruhan sehingga perlu ditinjau ulang pemilihan prediktornya'}.")
    )
    tb = _tab(h, "Tabel Koefisien")
    if tb is not None:
        df = tb[1]
        sig_rows, tidak = [], 0
        for idx, row in df.iterrows():
            if str(idx).lower() in ("const", "intercept"):
                continue
            p = row.get("p-value")
            if _sig(p, alpha):
                arah = "menaikkan" if float(row.get("Koefisien", 0)) > 0 else "menurunkan"
                sig_rows.append(f"{idx} (β = {_f(row.get('Koefisien'))}, p {_pv(p)}) yang {arah} nilai Y")
            else:
                tidak += 1
        if sig_rows:
            par.append(
                f"Berdasarkan tabel koefisien, terdapat {len(sig_rows)} prediktor yang berpengaruh signifikan "
                f"terhadap variabel dependen, yaitu " + ", ".join(sig_rows) + ". "
                + (f"Adapun {tidak} prediktor lainnya tidak berpengaruh signifikan pada taraf α = {_f(alpha)}. "
                   if tidak else "")
                + "Tanda koefisien menunjukkan arah pengaruh masing-masing variabel dengan menahan variabel lain tetap."
            )
        else:
            par.append(
                f"Tidak ada satu pun prediktor yang signifikan pada taraf α = {_f(alpha)}. "
                f"Hal ini dapat disebabkan ukuran sampel yang terbatas, hubungan yang lemah, "
                f"atau multikolinearitas antar prediktor; pertimbangkan memperbanyak data atau "
                f"menyederhanakan model."
            )
    asum = _tab(h, "Uji Asumsi Klasik")
    if asum is not None:
        df = asum[1]
        catatan = []
        for idx, row in df.iterrows():
            nama = str(idx).lower()
            p = row.get("p-value")
            if "durbin-watson" in nama:
                dw = _angka(row.get("Statistik"))
                if dw is not None:
                    ok = 1.5 <= dw <= 2.5
                    catatan.append(
                        f"Durbin-Watson = {_f(dw)} → residual "
                        f"{'bebas autokorelasi' if ok else 'berindikasi autokorelasi'}")
            elif "breusch-pagan" in nama and pd.notna(p):
                catatan.append(
                    f"Breusch-Pagan p {_pv(p)} → varians residual "
                    f"{'homogen (homoskedastik)' if not _sig(p, alpha) else 'tidak homogen (heteroskedastik)'}")
            elif "jarque-bera" in nama and pd.notna(p):
                catatan.append(
                    f"Jarque-Bera p {_pv(p)} → residual "
                    f"{'berdistribusi normal' if not _sig(p, alpha) else 'tidak berdistribusi normal'}")
        if catatan:
            par.append(
                "Pemeriksaan asumsi klasik memberikan hasil sebagai berikut: " +
                "; ".join(catatan) + ". "
                + ("Ketika asumsi terpenuhi, estimasi koefisien dapat ditafsirkan dengan lebih andal. "
                   if all(("tidak" not in c and "hetero" not in c and "autokorelasi" not in c) for c in catatan)
                   else "Pelanggaran asumsi tertentu dapat mengurangi efisiensi estimasi; "
                        "pertimbangkan transformasi data atau metode robust.")
            )
    vif = _tab(h, "Uji Multikolinearitas (VIF)")
    if vif is not None:
        dfv = vif[1]
        try:
            vmax = float(dfv["VIF"].max())
            varv = str(dfv["VIF"].idxmax())
            if vmax > 10:
                par.append(
                    f"Nilai VIF tertinggi sebesar {_f(vmax)} pada variabel {varv} (> 10) mengindikasikan "
                    f"multikolinearitas serius; prediktor yang sangat berkorelasi sebaiknya salah satunya "
                    f"dikeluarkan dari model agar koefisien lebih stabil.")
            elif vmax > 5:
                par.append(
                    f"Nilai VIF tertinggi sebesar {_f(vmax)} pada variabel {varv} berada pada rentang "
                    f"5-10, menandakan multikolinearitas moderat yang perlu diwaspadai.")
            else:
                par.append(
                    f"Seluruh nilai VIF ≤ {_f(vmax, 2)} (< 5) sehingga tidak terdapat masalah "
                    f"multikolinearitas yang berarti antar prediktor.")
        except (TypeError, ValueError, KeyError):
            pass
    par.append(
        "Secara keseluruhan, hasil regresi ini dapat digunakan untuk menjelaskan hubungan antar variabel "
        "serta membuat prediksi dalam rentang data yang diamati; berhati-hatilah saat mengekstrapolasi "
        "di luar rentang nilai data.")
    return par


# ==========================================================
# 2) REGRESI LOGISTIK BINER
# ==========================================================
def _narasi_logit(h, alpha):
    akur = _met(h, "Akurasi Klasifikasi")
    tb = _tab(h, "Odds Ratio")
    par = []
    nama_y, nama_1, nama_0 = "variabel dependen", "", ""
    for nte in getattr(h, "notes", []):
        if str(nte).startswith("Encoding:"):
            parts = str(nte).replace("Encoding:", "").strip().split(",")
            if len(parts) == 2:
                nama_0, nama_1 = parts[0].strip(), parts[1].strip()
                nama_y = f"kejadian \"{nama_1}\" (dibandingkan \"{nama_0}\")"
    par.append(
        f"Regresi logistik biner dimodelkan untuk memperkirakan peluang terjadinya {nama_y} "
        f"berdasarkan sekumpulan variabel independen. "
        + (f"Model mampu mengklasifikasikan dengan benar {akur} observasi berdasarkan ambang probabilitas 0,5, "
           f"suatu tingkat akurasi yang {'tergolong baik' if _angka(akur or 0) and (_angka(akur) or 0) >= 0.8 else 'perlu dibandingkan dengan proporsi kelas mayoritas sebagai pembanding'}."
           if akur else "")
    )
    if tb is not None:
        df = tb[1]
        sig_rows = []
        for idx, row in df.iterrows():
            if str(idx).lower() in ("const", "intercept"):
                continue
            if _sig(row.get("p-value"), alpha):
                orv = float(row.get("Odds Ratio", 0))
                arah = ("menaikkan peluang" if orv > 1 else "menurunkan peluang")
                sig_rows.append(
                    f"{idx} (OR = {_f(orv, 3)}, p {_pv(row.get('p-value'))}) yang {arah} {nama_y} "
                    f"sekitar {_pc(abs(orv - 1))} setiap kenaikan satu satuan")
        if sig_rows:
            par.append(
                f"Terdapat {len(sig_rows)} prediktor signifikan: " + "; ".join(sig_rows) +
                f". Interpretasi odds ratio mengacu pada kategori acuan \"{nama_0}\"."
                if nama_0 else
                f"Terdapat {len(sig_rows)} prediktor signifikan: " + "; ".join(sig_rows) + ".")
        else:
            par.append(
                f"Tidak terdapat prediktor yang signifikan pada taraf α = {_f(alpha)}; peluang {nama_y} "
                f"belum dapat dijelaskan dengan variabel yang tersedia.")
    par.append(
        "Perlu diingat bahwa akurasi pada data yang sama (resubstitusi) cenderung optimistis. "
        "Untuk menilai kemampuan generalisasi model, disarankan memvalidasi pada data baru atau "
        "menggunakan teknik validasi silang, serta memeriksa keseimbangan jumlah antar kategori.")
    return par


# ==========================================================
# 3) REGRESI LOGISTIK MULTINOMIAL
# ==========================================================
def _narasi_mnlogit(h, alpha):
    tb = _tab(h, "Relative Risk Ratio")
    par = [
        "Regresi logistik multinomial memodelkan peluang seseorang berada pada setiap kategori variabel "
        "dependen relatif terhadap satu kategori dasar (referensi). Koefisien yang dilaporkan berupa "
        "Relative Risk Ratio (RRR = e^β), di mana nilai > 1 berarti variabel tersebut menaikkan risiko "
        "relatif kategori terkait dan nilai < 1 berarti menurunkannya.",
    ]
    if tb is not None:
        df = tb[1]
        rows = [str(i) for i in df.index if str(i).lower() not in ("const", "intercept")]
        if rows:
            ekstrem = []
            for col in df.columns:
                vals = {r: _angka(df.loc[r, col]) for r in rows}
                vals = {r: v for r, v in vals.items() if v is not None and v > 0}
                if not vals:
                    continue
                mx = max(vals, key=vals.get)
                mn = min(vals, key=vals.get)
                ekstrem.append(
                    f"menuju kategori {col}: pendorong terbesar adalah {mx} (RRR = {_f(vals[mx], 3)}) "
                    f"dan penekan terbesar adalah {mn} (RRR = {_f(vals[mn], 3)})")
            if ekstrem:
                par.append("Profil efek tiap kategori: " + "; ".join(ekstrem) + ".")
    par.append(
        "Rilis signifikansi statistik tiap koefisien beserta kesalahan standarnya dapat dibaca pada "
        "ringkasan model di bawah. Ketika salah satu kategori memiliki jumlah anggota yang sangat sedikit, "
        "estimasi untuk kategori tersebut menjadi kurang stabil sehingga sebaiknya dilaporkan dengan hati-hati.")
    return par


# ==========================================================
# 4) REGRESI ORDINAL
# ==========================================================
def _narasi_ordinal(h, alpha):
    par = [
        "Regresi ordinal (ordered logit) digunakan karena variabel dependen merupakan kategori "
        "bertingkat; model ini memperkirakan pengaruh setiap variabel independen terhadap peluang "
        "berada pada level yang lebih tinggi dengan asumsi odds proporsional antar ambang kategori.",
    ]
    pr2 = _angka(_met(h, "Pseudo R²") or "")
    n = _met(h, "n Observasi")
    if pr2 is not None:
        par.append(
            f"Daya jelaskan model dinyatakan dengan Pseudo R² (McFadden) sebesar {_f(pr2)}, yang "
            f"{'tergolong memadai' if pr2 >= 0.2 else 'tergolong rendah sehingga interpretasi perlu dilengkapi uji kelayakan lain'} "
            f"dalam konteks model diskrit" + (f", berdasarkan {n} observasi." if n else "."))
    tb = _tab(h, "Koefisien & Ambang")
    sig_rows = []
    if tb is not None:
        df = tb[1]
        for idx, row in df.iterrows():
            if str(idx).lower().startswith("ambang") or str(idx).lower() in ("const", "intercept"):
                continue
            if _sig(row.get("p-value"), alpha):
                b = float(row.get("Koefisien", 0))
                sig_rows.append(
                    f"{idx} (e^β = {_f(math.exp(b), 3)}, p {_pv(row.get('p-value'))}) "
                    f"{'menaikkan' if b > 0 else 'menurunkan'} peluang berada pada kategori yang lebih tinggi")
        if sig_rows:
            par.append(
                f"Prediktor yang signifikan pada taraf α = {_f(alpha)}: " + "; ".join(sig_rows) +
                ". Nilai e^β lebih besar dari 1 berarti variabel tersebut menggeser respons menuju "
                "level yang lebih tinggi, sebaliknya lebih kecil dari 1 menggeser ke level bawah.")
        else:
            par.append(
                f"Tidak ada prediktor yang signifikan pada taraf α = {_f(alpha)}; urutan level respons "
                f"belum dapat dijelaskan oleh variabel independen yang tersedia.")
    par.append(
        "Keabsahan model bergantung pada asumsi odds proporsional; bila asumsi dilanggar, pertimbangkan "
        "model multinomial atau kategori biner tertentu. Nilai ambang (threshold) pada tabel menunjukkan "
        "titik batas antar kategori pada skala laten.")
    return par


# ==========================================================
# 5) REGRESI POISSON
# ==========================================================
def _narasi_poisson(h, alpha):
    tb = _tab(h, "IRR")
    par = [
        "Regresi Poisson dipilih karena variabel dependen merupakan data hitungan (count) bernilai "
        "non-negatif. Koefisien dilaporkan sebagai Incidence Rate Ratio (IRR = e^β): IRR > 1 berarti "
        "variabel tersebut menaikkan laju kejadian, sedangkan IRR < 1 menurunkannya.",
    ]
    if tb is not None:
        df = tb[1]
        sig_rows = []
        for idx, row in df.iterrows():
            if str(idx).lower() in ("const", "intercept"):
                continue
            if _sig(row.get("p-value"), alpha):
                irr = float(row.get("IRR", 1))
                sig_rows.append(
                    f"{idx} (IRR = {_f(irr, 3)}, p {_pv(row.get('p-value'))}) yang "
                    f"{'menaikkan' if irr > 1 else 'menurunkan'} laju kejadian sekitar {_pc(abs(irr - 1))} per satuannya")
        if sig_rows:
            par.append(
                f"Prediktor signifikan pada taraf α = {_f(alpha)}: " + "; ".join(sig_rows) + ".")
        else:
            par.append(
                f"Tidak terdapat prediktor signifikan pada taraf α = {_f(alpha)}; laju kejadian belum "
                f"dapat dijelaskan oleh variabel yang tersedia.")
    par.append(
        "Validitas model Poisson bergantung pada asumsi equidispersi (rata-rata ≈ varians). Apabila "
        "varians jauh melampaui rata-rata (overdispersion), estimasi kesalahan standar menjadi terlalu "
        "kecil sehingga disarankan beralih ke model Negative Binomial atau Quasi-Poisson.")
    return par


# ==========================================================
# 6) ANOVA SATU ARAH
# ==========================================================
def _narasi_anova1(h, alpha):
    par = []
    desc = _tab(h, "Statistik Deskriptif per Kelompok")
    ft = _tab(h, "Tabel ANOVA")
    tk = _tab(h, "Post-Hoc: Tukey")
    lev = _uji(h, "Uji Homogenitas Varians")
    an = _uji(h, "ANOVA F-Test")
    eta = _angka(_met(h, "Eta Squared") or "")
    profil = []
    if desc is not None:
        df = desc[1]
        if "mean" in df.columns:
            for idx, row in df.iterrows():
                profil.append(f"{idx} (rata-rata {_f(row['mean'])}, n = {_f(row['count'], 0)})")
    par.append(
        "Uji ANOVA satu arah dijalankan untuk membandingkan rata-rata antar kelompok secara simultan. "
        + (f"Perbandingan melibatkan {len(profil)} kelompok: " + ", ".join(profil) + ". "
           if profil else "")
        + "Hipotesis nol menyatakan seluruh rata-rata kelompok sama; hipotesis alternatif menyatakan "
          "setidaknya ada satu kelompok yang berbeda."
    )
    if lev is not None:
        homogen = not _sig(lev[2], alpha)
        par.append(
            f"Uji homogenitas varians Levene menghasilkan statistik {_f(lev[1])} dengan p {_pv(lev[2])}, "
            f"sehingga asumsi kesamaan varians antar kelompok "
            f"{'terpenuhi' if homogen else 'tidak terpenuhi'}. "
            + ("" if homogen else
               f"Dengan demikian hasil F berikut perlu ditafsirkan hati-hati dan pertimbangkan "
               f"alternatif Welch ANOVA atau uji non-parametrik Kruskal-Wallis.")
        )
    if an is not None:
        dfb = dfw = "-"
        if ft is not None:
            try:
                dfb, dfw = _f(ft[1]["df"].iloc[0], 0), _f(ft[1]["df"].iloc[1], 0)
            except (IndexError, KeyError, TypeError):
                pass
        par.append(
            f"Hasil uji F memperoleh F = {_f(an[1])} (df = {dfb}; {dfw}) dengan p-value {_pv(an[2])}. "
            f"Karena p-value {_pvs(an[2], alpha)} α ({_f(alpha)}), maka H₀ {_kep(an[2], alpha)}: "
            + ("terdapat perbedaan rata-rata yang signifikan antar kelompok."
               if _sig(an[2], alpha) else
               "belum ada bukti perbedaan rata-rata antar kelompok.")
        )
        if eta is not None:
            par.append(
                f"Ukuran efek eta squared = {_f(eta)} tergolong {_kat_eta(eta)}, artinya "
                f"{_pc(eta)} variasi variabel dependen dapat dijelaskan oleh perbedaan kelompok.")
    if tk is not None:
        dft = tk[1]
        sig_pairs = []
        for idx, row in dft.iterrows():
            rej = row.get("reject")
            rej = True if (isinstance(rej, bool) and rej) else str(rej).strip().lower() in ("true", "1.0", "1")
            p_adj = row.get("p-adj", row.get("p-adj "))
            if rej:
                sig_pairs.append(f"{idx} vs {row.get('group2')} (p-adj {_pv(p_adj)})")
        if sig_pairs:
            par.append(
                f"Uji lanjut Tukey HSD mengidentifikasi {len(sig_pairs)} pasangan kelompok yang berbeda "
                f"secara signifikan, yaitu " + "; ".join(sig_pairs) +
                ". Pasangan inilah sumber utama perbedaan yang terdeteksi oleh ANOVA.")
        else:
            par.append(
                "Meskipun ANOVA signifikan, uji lanjut Tukey HSD tidak menemukan pasangan kelompok "
                "yang berbeda secara jelas - kemungkinan karena perbedaan tersebar merata antar banyak kelompok.")
    elif an is not None and _sig(an[2], alpha):
        par.append(
            "Karena hasil ANOVA signifikan, perbedaan tersebut berlaku untuk seluruh kelompok secara "
            "simultan; untuk lebih dari dua kelompok, uji lanjut Tukey HSD otomatis ditampilkan guna "
            "menetapkan pasangan kelompok yang berbeda.")
    else:
        par.append(
            "Karena tidak terdapat perbedaan signifikan, uji lanjut (post-hoc) tidak diperlukan; "
            "seluruh kelompok dapat diperlakukan setara pada taraf signifikansi yang dipilih.")
    return par


# ==========================================================
# 7) ANOVA DUA ARAH
# ==========================================================
def _narasi_anova2(h, alpha):
    par = [
        "ANOVA dua arah menguji pengaruh dua faktor sekaligus terhadap variabel dependen, sekaligus "
        "memeriksa apakah terjadi interaksi antara keduanya. Interaksi yang signifikan berarti efek "
        "satu faktor bergantung pada level faktor lainnya.",
    ]
    tes = [(l, st, p, al) for l, st, p, al in getattr(h, "tests", [])]
    inter = None
    utama = []
    for l, st, p, al in tes:
        if ":" in l or "×" in l:
            inter = (l, st, p, al)
        else:
            utama.append((l, st, p, al))
    if inter is not None:
        par.append(
            f"Uji interaksi ({inter[0]}) menghasilkan F = {_f(inter[1])} dengan p {_pv(inter[2])}, "
            f"sehingga interaksi antar faktor {'signifikan' if _sig(inter[2], alpha) else 'tidak signifikan'} "
            f"pada α = {_f(alpha)}. "
            + ("Garis pada plot interaksi yang saling menyilang juga mengonfirmasi adanya efek gabungan; "
               "penafsiran efek utama sebaiknya dilakukan dengan hati-hati karena bergantung pada level "
               "faktor lainnya." if _sig(inter[2], alpha) else
               "Dengan tidak adanya interaksi, efek masing-masing faktor dapat ditafsirkan secara mandiri.")
        )
    for l, st, p, al in utama:
        par.append(
            f"Faktor {l} menghasilkan F = {_f(st)} dengan p {_pv(p)}: pengaruhnya "
            f"{'signifikan' if _sig(p, alpha) else 'tidak signifikan'} terhadap variabel dependen "
            f"pada taraf α = {_f(alpha)}.")
    par.append(
        "Untuk mengetahui pasangan level mana yang berbeda ketika suatu faktor signifikan, lanjutkan "
        "dengan uji post-hoc (misalnya Tukey HSD) pada faktor terkait, dan gunakan plot interaksi di "
        "bawah untuk membaca pola rata-rata antar kombinasi faktor.")
    return par


# ==========================================================
# 8) ANCOVA
# ==========================================================
def _narasi_ancova(h, alpha):
    par = [
        "ANCOVA menguji perbedaan rata-rata antar kelompok sambil mengendalikan pengaruh satu atau "
        "lebih kovariat numerik, sehingga perbandingan antar kelompok menjadi lebih adil karena efek "
        "kovariat telah disesuaikan (adjusted).",
    ]
    for l, st, p, al in getattr(h, "tests", []):
        jenis = "Faktor" if "C(" in str(l) else "Kovariat"
        par.append(
            f"{jenis} {l} menghasilkan F = {_f(st)} dengan p {_pv(p)}: pengaruhnya "
            f"{'signifikan' if _sig(p, alpha) else 'tidak signifikan'} pada taraf α = {_f(alpha)}"
            + ("; artinya terdapat perbedaan rata-rata antar kelompok setelah mengendalikan kovariat."
               if jenis == "Faktor" and _sig(p, alpha) else
               "; artinya kovariat tersebut tetap berhubungan dengan respons meski efek kelompok dikendalikan."
               if jenis == "Kovariat" and _sig(p, alpha) else "."))
    par.append(
        "Validitas ANCOVA menuntut hubungan linear antara kovariat dan respons serta kemiringan garis "
        "regresi yang homogen antar kelompok. Bila asumsi kemiringan homogen dilanggar, hasil penyesuaian "
        "dapat menyesatkan sehingga perlu diperiksa terlebih dahulu melalui plot residual.")
    return par


# ==========================================================
# 9) MANOVA
# ==========================================================
def _narasi_manova(h, alpha):
    par = [
        "MANOVA menguji perbedaan antar kelompok pada beberapa variabel dependen secara simultan. "
        "Keunggulan utamanya adalah mengendalikan tingkat kesalahan tipe I yang akan membengkak bila "
        "setiap variabel diuji satu per satu dengan ANOVA terpisah.",
    ]
    tes = [(l, st, p, al) for l, st, p, al in getattr(h, "tests", []) if "MANOVA" in str(l)]
    if tes:
        sig_any = any(_sig(p, alpha) for _, _, p, _ in tes)
        for l, st, p, al in tes:
            ef = str(l).split("—")[-1].split("(")[0].strip()
            par.append(
                f"Pada efek {ef}, Wilks' Lambda menghasilkan F = {_f(st)} dengan p {_pv(p)}, "
                f"sehingga {'terdapat' if _sig(p, alpha) else 'tidak terdapat'} perbedaan multivariat "
                f"yang signifikan pada α = {_f(alpha)}.")
        if sig_any:
            tb = _tab(h, "Rata-rata per Kelompok")
            if tb is not None:
                df = tb[1]
                unggul = []
                for col in df.columns:
                    try:
                        mx = df[col].idxmax()
                        unggul.append(f"{col} tertinggi pada kelompok {mx} ({_f(df.loc[mx, col])})")
                    except (ValueError, KeyError, TypeError):
                        pass
                if unggul:
                    par.append(
                        "Profil rata-rata antar kelompok: " + "; ".join(unggul) +
                        ". Pola ini membantu mengidentifikasi variabel mana yang paling membedakan "
                        "kelompok-kelompok tersebut.")
    else:
        par.append(
            "Perhatikan tabel Uji Multivariat di bawah: nilai p pada statistik Wilks' Lambda, Pillai's "
            "Trace, Hotelling-Lawley, dan Roy digunakan untuk menilai signifikansi keseluruhan efek "
            "kelompok terhadap gabungan variabel dependen.")
    par.append(
        "Untuk analisis lanjutan, ANOVA univariat per variabel atau analisis diskriminan dapat digunakan "
        "untuk memetakan variabel yang paling berkontribusi terhadap perbedaan antar kelompok.")
    return par


# ==========================================================
# 10) UJI t
# ==========================================================
def _narasi_ttest(h, alpha):
    par = []
    satu = _tab(h, "Hasil Uji t Satu Sampel")
    ind = _tab(h, "Hasil Uji t Independen")
    bp = _tab(h, "Hasil Uji t Berpasangan")
    if satu is not None:
        df = satu[1]
        mu_label = next((l for l, _, _, _ in getattr(h, "tests", []) if l.startswith("Uji t Satu Sampel")), "")
        mu = mu_label.split("μ = ")[-1].rstrip(")").strip() if "μ = " in mu_label else "0"
        n, mean = _angka(df.loc["n", "Nilai"]), _angka(df.loc["Mean sampel", "Nilai"])
        sd, t = _angka(df.loc["Std", "Nilai"]), _angka(df.loc["t-statistik", "Nilai"])
        p, dfree = _angka(df.loc["p-value", "Nilai"]), _angka(df.loc["df", "Nilai"])
        d = _angka(df.loc["Cohen's d", "Nilai"])
        par.append(
            f"Uji t satu sampel menguji apakah rata-rata populasi berbeda dari nilai acuan μ₀ = {mu}. "
            f"Berdasarkan {n} observasi, rata-rata sampel sebesar {_f(mean)} (SD = {_f(sd)}) "
            f"{'lebih tinggi' if mean is not None and float(mu or 0) < mean else 'lebih rendah'} daripada nilai acuan."
        )
        par.append(
            f"Hasil pengujian memperoleh t = {_f(t)} dengan derajat kebebasan {dfree} dan p-value {_pv(p)}. "
            f"Karena p-value {_pvs(p, alpha)} α ({_f(alpha)}), H₀ {_kep(p, alpha)} — "
            + (f"rata-rata berbeda secara signifikan dari μ₀ = {mu}. "
               if _sig(p, alpha) else
               f"belum ada bukti yang cukup bahwa rata-rata berbeda dari μ₀ = {mu}.")
        )
        if d is not None:
            par.append(
                f"Ukuran efek Cohen's d = {_f(d)} tergolong {_kat_d(d)}, yang menunjukkan seberapa besar "
                f"jarak praktis antara rata-rata sampel dan nilai acuan; signifikansi statistik sebaiknya "
                f"selalu dibarengi pertimbangan besaran efek seperti ini.")
    elif ind is not None:
        stat = _tab(h, "Statistik Kelompok")
        lev = _uji(h, "Uji Levene")
        dfi = ind[1]
        t = _angka(dfi.loc["t-statistik", "Nilai"])
        p = _angka(dfi.loc["p-value", "Nilai"])
        dfree = _angka(dfi.loc["df", "Nilai"])
        d = _angka(dfi.loc["Cohen's d", "Nilai"])
        profil = []
        if stat is not None:
            for idx, row in stat[1].iterrows():
                profil.append(f"{idx} (n = {_f(row['n'], 0)}, rata-rata {_f(row['Mean'])}, SD = {_f(row['Std'])})")
        par.append(
            "Uji t sampel independen membandingkan rata-rata dua kelompok yang saling bebas. "
            + (f"Kelompok yang dibandingkan: " + " dan ".join(profil) + ". " if profil else "")
        )
        if lev is not None:
            homogen = not _sig(lev[2], alpha)
            par.append(
                f"Uji Levene menghasilkan p {_pv(lev[2])}, sehingga asumsi homogenitas varians "
                f"{'terpenuhi dan digunakan varians gabungan (pooled)' if homogen else 'tidak terpenuhi sehingga digunakan koreksi Welch'} "
                f"pada perhitungan t.")
        if all(v is not None for v in (t, p)) and stat is not None:
            means = {str(i): _angka(r["Mean"]) for i, r in stat[1].iterrows()}
            if len(means) == 2 and None not in means.values():
                hi = max(means, key=means.get)
                lo = min(means, key=means.get)
                selisih = means[hi] - means[lo]
                par.append(
                    f"Hasil uji memperoleh t = {_f(t)} (df = {_f(dfree)}) dengan p-value {_pv(p)}. "
                    f"Karena p-value {_pvs(p, alpha)} α ({_f(alpha)}), H₀ {_kep(p, alpha)} — "
                    + (f"rata-rata kelompok {hi} secara signifikan lebih tinggi {_f(selisih)} poin dibanding kelompok {lo}."
                       if _sig(p, alpha) else
                       "belum ada bukti perbedaan rata-rata yang signifikan antara kedua kelompok."))
        if d is not None:
            par.append(
                f"Ukuran efek Cohen's d = {_f(d)} tergolong {_kat_d(d)}; semakin besar nilai ini, semakin "
                f"jelas pula bedanya secara praktis, bukan sekadar signifikan secara statistik.")
    elif bp is not None:
        dfb = bp[1]
        n = _angka(dfb.loc["n pasangan", "Nilai"])
        m_sel = _angka(dfb.loc["Mean selisih", "Nilai"])
        sd_sel = _angka(dfb.loc["Std selisih", "Nilai"])
        t = _angka(dfb.loc["t-statistik", "Nilai"])
        p = _angka(dfb.loc["p-value", "Nilai"])
        dz = _angka(dfb.loc["Cohen's dz", "Nilai"])
        v1 = [str(i) for i in dfb.index if str(i).startswith("Mean ")][0].replace("Mean ", "")
        v2 = [str(i) for i in dfb.index if str(i).startswith("Mean ")][1].replace("Mean ", "")
        arah = ("meningkat" if (m_sel or 0) < 0 else "menurun")  # selisih = v1 - v2
        par.append(
            f"Uji t berpasangan digunakan karena kedua pengukuran ({v1} dan {v2}) diambil pada subjek yang "
            f"sama, sehingga hanya selisih pasangan yang dianalisis ({n} pasangan valid). Rata-rata selisih "
            f"sebesar {_f(m_sel)} (SD = {_f(sd_sel)}), menandakan kecenderungan nilai {arah} dari "
            f"{v1} ke {v2}."
        )
        par.append(
            f"Hasil uji memperoleh t = {_f(t)} dengan p-value {_pv(p)}. Karena p-value {_pvs(p, alpha)} "
            f"α ({_f(alpha)}), H₀ {_kep(p, alpha)} — "
            + (f"terdapat perbedaan yang signifikan antara sebelum dan sesudah."
               if _sig(p, alpha) else
               "belum ada bukti perubahan yang signifikan antara kedua pengukuran.")
        )
        if dz is not None:
            par.append(
                f"Ukuran efek Cohen's dz = {_f(dz)} tergolong {_kat_d(dz)}, sehingga besaran perubahan "
                f"{'layak mendapat perhatian praktis' if abs(dz) >= 0.5 else 'relatif moderat kecil di samping hasil ujinya'}.")
    return par


# ==========================================================
# 11) CHI-SQUARE
# ==========================================================
def _narasi_chisq(h, alpha):
    par = []
    nama = next((str(n) for n in getattr(h, "notes", []) if str(n).startswith("Kontingensi:")), "")
    obs = _tab(h, "Tabel Kontingensi")
    exp = _tab(h, "Frekuensi Harapan")
    uji = _uji(h, "Chi-Square Independensi")
    v = _angka(_met(h, "Cramér's V") or "")
    dim = ""
    if obs is not None:
        df = obs[1]
        dim = f"{df.shape[0]}×{df.shape[1]}"
    par.append(
        "Uji chi-square independensi digunakan untuk menilai apakah terdapat hubungan antara dua variabel "
        "kategorik " + (f"({nama.split(':', 1)[-1].strip()}) " if nama else "")
        + f"melalui tabel kontingensi berukuran {dim} sel. "
          "Hipotesis nol menyatakan kedua variabel saling bebas (tidak berasosiasi)."
    )
    if uji is not None:
        par.append(
            f"Hasil pengujian memperoleh χ² = {_f(uji[1])} (df = {uji[0].split('df = ')[-1].rstrip(')')}) "
            f"dengan p-value {_pv(uji[2])}. Karena p-value {_pvs(uji[2], alpha)} α ({_f(alpha)}), H₀ "
            f"{_kep(uji[2], alpha)} — "
            + ("terdapat hubungan yang signifikan antara kedua variabel."
               if _sig(uji[2], alpha) else
               "kedua variabel dapat dianggap saling bebas; belum ada bukti asosiasi yang signifikan.")
        )
    if v is not None:
        par.append(
            f"Kekuatan asosiasi diukur dengan Cramér's V = {_f(v, 3)} yang tergolong {_kat_v(v)}. "
            + ("Perlu diingat bahwa signifikansi statistik pada sampel besar tidak selalu berarti asosiasi "
               "yang kuat secara praktis; nilai V inilah yang menilai besarnya efek." if _sig((uji or (0, 0, 1))[2], alpha) else "")
        )
    if (obs is not None) and (exp is not None) and uji is not None and _sig(uji[2], alpha):
        try:
            dfo, dfe = obs[1], exp[1]
            kontrib = ((dfo.values - dfe.values) ** 2) / dfe.values
            pos = np.unravel_index(np.argmax(kontrib), kontrib.shape)
            share = kontrib[pos] / max(uji[1], 1e-12) * 100
            par.append(
                f"Kontribusi terbesar terhadap nilai χ² berasal dari kombinasi \"{dfo.index[pos[0]]}\" pada "
                f"baris dan \"{dfo.columns[pos[1]]}\" pada kolom (≈ {_pc(share)} dari total χ²). "
                f"Sel inilah yang paling menyimpang dari keadaan saling bebas sehingga layak menjadi fokus "
                f"pembahasan.")
        except (ValueError, ZeroDivisionError, IndexError, TypeError):
            pass
    if getattr(h, "warnings", []):
        par.append(
            "Catatan kehati-hatian: sebagian sel memiliki frekuensi harapan di bawah 5, sehingga statistik "
            "χ² mendekati distribusi chi-square dengan kurang baik. Pertimbangkan menggabungkan kategori "
            "yang jarang atau menggunakan uji Fisher's exact untuk tabel 2×2.")
    return par


# ==========================================================
# 12) KORELASI
# ==========================================================
def _narasi_korelasi(h, alpha):
    mt = _tab(h, "Matriks Korelasi")
    mp = _tab(h, "Matriks p-value")
    metode = mt[0].split("(")[-1].rstrip(")").lower() if mt else "pearson"
    jenis = {"pearson": "linear (Pearson)", "spearman": "monotonik berbasis peringkat (Spearman)",
             "kendall": "monotonik berbasis konkordansi (Kendall tau)"}.get(metode, metode)
    par = [
        f"Analisis korelasi {jenis} dijalankan untuk mengukur arah dan kekuatan hubungan antar pasangan "
        f"variabel numerik, dengan nilai koefisien berkisar dari -1 (hubungan negatif sempurna) hingga "
        f"+1 (hubungan positif sempurna).",
    ]
    if mt is not None:
        corr, pmat = mt[1], (mp[1] if mp else None)
        cols = list(corr.columns)
        n_pairs = len(cols) * (len(cols) - 1) // 2
        pas = []
        sig_n = 0
        terkuat = None
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                r = _angka(corr.iloc[i, j])
                p = _angka(pmat.iloc[i, j]) if pmat is not None else None
                if r is None:
                    continue
                if terkuat is None or abs(r) > abs(terkuat[2]):
                    terkuat = (cols[i], cols[j], r)
                if p is not None and _sig(p, alpha):
                    sig_n += 1
                    if len(pas) < 5:
                        pas.append(f"{cols[i]}–{cols[j]} (r = {_f(r, 3)}, p {_pv(p)})")
        par.append(
            f"Dari {n_pairs} pasangan variabel yang diuji, {sig_n} pasangan menunjukkan korelasi signifikan "
            f"pada α = {_f(alpha)}."
            + (" Pasangan signifikan: " + "; ".join(pas) + "." if pas else "")
        )
        if terkuat is not None:
            a, b, r = terkuat
            par.append(
                f"Hubungan terkuat terjadi antara {a} dan {b} dengan koefisien {_f(r, 3)} — arah "
                f"{'positif' if r > 0 else 'negatif'} dan kekuatan {_kat_r(r)}. "
                f"{'Kedua variabel cenderung bergerak searah: kenaikan salah satunya diikuti kenaikan yang lain.' if r > 0 else 'Kedua variabel cenderung bergerak berlawanan arah: kenaikan salah satunya diikuti penurunan yang lain.' if abs(r) > 0.2 else 'Meski signifikan, hubungan ini praktis masih lemah sehingga perlu ditafsirkan hati-hati.' if sig_n else ''}"
            )
    par.append(
        "Penting diingat bahwa korelasi tidak menyiratkan kausalitas: hubungan yang kuat dapat muncul "
        "akibat variabel ketiga yang tidak diamati (confounding). Untuk menguji model sebab-akibat, "
        "lanjutkan dengan analisis regresi dan pertimbangkan konteks substantif variabel.")
    return par


# ==========================================================
# 13) ANALISIS FAKTOR
# ==========================================================
def _narasi_faktor(h, alpha):
    par = []
    kmo = _angka(_met(h, "KMO") or "")
    bart = _uji(h, "Uji Bartlett")
    par.append(
        "Analisis faktor dijalankan untuk merangkum sejumlah variabel indikator yang saling berkorelasi "
        "ke dalam beberapa faktor laten yang lebih sedikit. Kelayakan data dinilai dengan dua uji prasyarat: "
        "kecukupan sampling (KMO) dan kesferisitas Bartlett."
    )
    if kmo is not None:
        par.append(
            f"Nilai KMO sebesar {_f(kmo, 3)} tergolong {_kat_kmo(kmo)}. "
            + ("" if kmo >= 0.6 else
               "Nilai di bawah 0,6 menandakan pola korelasi antar variabel terlalu tersebar sehingga "
               "ekstraksi faktor kurang ideal; pertimbangkan menghapus indikator dengan komunalitas rendah.")
        )
    if bart is not None:
        par.append(
            f"Uji Bartlett's Test of Sphericity menghasilkan χ² = {_f(bart[1])} dengan p {_pv(bart[2])}; "
            f"karena p {_pvs(bart[2], alpha)} α ({_f(alpha)}), matriks korelasi "
            f"{'bukan matriks identitas sehingga data layak difaktorkan' if _sig(bart[2], alpha) else 'mendekati identitas dan analisis faktor kurang tepat dilakukan'}."
        )
    vt = _tab(h, "Varians yang Dijelaskan")
    if vt is not None:
        dfv = vt[1]
        try:
            total = float(dfv["Kumulatif"].iloc[-1])
            k = dfv.shape[0]
            par.append(
                f"{k} faktor yang diekstraksi secara bersama-sama mampu menjelaskan {_pc(total)} "
                f"total varians data. Kriteria umum menyatakan solusi yang menjelaskan ≥ 60% varians "
                f"{'sudah' if total >= 0.6 else 'belum'} tercapai.")
        except (IndexError, KeyError, TypeError, ValueError):
            pass
    ld = _tab(h, "Matriks Loading")
    if ld is not None:
        dfl = ld[1]
        profil = []
        for col in dfl.columns:
            try:
                muat = dfl[col].apply(lambda x: abs(_angka(x) or 0))
                tinggi = muat[muat >= 0.4].sort_values(ascending=False)
                if len(tinggi):
                    profil.append(f"{col} dicirikan oleh " + ", ".join(str(i) for i in tinggi.index[:5]))
            except (TypeError, ValueError):
                pass
        if profil:
            par.append("Struktur faktor: " + "; ".join(profil) + ". "
                       "Indikator dengan loading ≥ 0,40 dianggap mewakili faktor terkait; indikator yang "
                       "berpindah faktor atau bermuat rendah sebaiknya ditinjau ulang kecocokan teorinya.")
    km = _tab(h, "Komunalitas")
    if km is not None:
        dfk = km[1]
        try:
            rendah = dfk["Komunalitas"].astype(float)
            idx_min = rendah.idxmin()
            if float(rendah.min()) < 0.4:
                par.append(
                    f"Komunalitas terendah dimiliki {idx_min} ({_f(rendah.min(), 3)} < 0,40), menandakan "
                    f"variabel tersebut kurang terepresentasikan dalam solusi faktor dan dapat dipertimbangkan "
                    f"untuk dikeluarkan pada analisis ulang.")
        except (TypeError, ValueError, KeyError):
            pass
    return par


# ==========================================================
# 14) PCA
# ==========================================================
def _narasi_pca(h, alpha):
    par = [
        "Analisis Komponen Utama (PCA) mereduksi banyak variabel numerik yang berkorelasi menjadi "
        "beberapa komponen utama yang saling tegak lurus, di mana setiap komponen adalah kombinasi linear "
        "dari variabel asal dan menangkap varians terbesar secara berturut-turut.",
    ]
    vt = _tab(h, "Varians yang Dijelaskan")
    if vt is not None:
        dfv = vt[1]
        try:
            eig = dfv["Eigenvalue"].astype(float)
            k_kaiser = int((eig > 1).sum())
            kum = dfv["Kumulatif"].astype(float).values
            k80 = int(np.searchsorted(kum, 0.8) + 1) if (kum < 0.8).any() else len(kum)
            par.append(
                f"Berdasarkan kaidah Kaiser (eigenvalue > 1), terdapat {k_kaiser} komponen yang layak "
                f"dipertahankan; sementara untuk menjelaskan minimal 80% total varians dibutuhkan {k80} "
                f"komponen. Kedua kaidah ini dapat dibandingkan dengan letak siku pada scree plot."
            )
        except (KeyError, TypeError, ValueError):
            pass
    ld = _tab(h, "Loading Komponen")
    if ld is not None:
        dfl = ld[1]
        profil = []
        for col in dfl.columns[:2]:
            try:
                muat = dfl[col].apply(lambda x: abs(_angka(x) or 0))
                top = muat.sort_values(ascending=False).head(3)
                profil.append(f"{col} didominasi oleh " + ", ".join(f"{i} ({_f(dfl.loc[i, col], 2)})" for i in top.index))
            except (TypeError, ValueError):
                pass
        if profil:
            par.append("Interpretasi komponen: " + "; ".join(profil) + ". "
                       "Nama komponen sebaiknya disematkan berdasarkan tema variabel yang bermuat kuat "
                       "padanya agar hasil mudah dikomunikasikan.")
    nte = next((str(n) for n in getattr(h, "notes", []) if "PC1 + PC2" in str(n)), "")
    if nte:
        par.append(
            f"Dua komponen pertama saja telah menjelaskan {nte.split('menjelaskan')[-1].strip().rstrip('.')}, "
            f"sehingga visualisasi biplot PC1-PC2 di bawah cukup representatif untuk membaca kedekatan "
            f"antar observasi maupun arah variabel.")
    par.append(
        "Ingat bahwa komponen PCA bersifat statistik (tidak otomatis bermakna substantif). Bila tujuan "
        "analisis adalah menemukan faktor laten yang bisa ditafsirkan, bandingkan dengan hasil analisis "
        "faktor yang menggunakan rotasi.")
    return par


# ==========================================================
# 15) LDA
# ==========================================================
def _narasi_lda(h, alpha):
    par = [
        "Analisis diskriminan linear (LDA) membangun fungsi kombinasi linear variabel pembeda untuk "
        "mengklasifikasikan observasi ke dalam kelompok yang telah diketahui, sekaligus menunjukkan "
        "seberapa baik kelompok-kelompok tersebut dapat dipisahkan.",
    ]
    ak = _angka(_met(h, "Akurasi (resubstitusi)") or "")
    cvm = _met(h, "Akurasi Cross-Validation")
    if ak is not None:
        par.append(
            f"Akurasi klasifikasi pada data pelatihan (resubstitusi) mencapai {_pc(ak)}."
            + (f" Validasi silang {'-'.join(cvm.split('(')[1].split('-fold')) if '(' in cvm and '-fold' in cvm else ''} menghasilkan akurasi {cvm.split(' ')[0] if cvm else ''}, "
               f"selisihnya dengan akurasi resubstitusi mengindikasikan {'generalisasi yang cukup stabil' if (cvm and _angka(cvm.split(' ')[0]) and ak and _angka(cvm.split(' ')[0]) >= ak - 0.1) else 'potensi overfitting yang perlu diwaspadai'}."
               if cvm else " Perlu diingat angka ini cenderung optimistis karena model menguji data yang sama dengan data latihnya.")
        )
    km = _tab(h, "Matriks Klasifikasi")
    if km is not None:
        dfk = km[1]
        try:
            vals = dfk.values.astype(float)
            total = vals.sum()
            benar = np.trace(vals)
            if total > 0:
                par.append(f"Dari {int(total)} observasi, {int(benar)} terklasifikasi benar ({_pc(benar / total)}).")
            off = vals.copy()
            np.fill_diagonal(off, 0)
            if off.max() > 0:
                pos = np.unravel_index(np.argmax(off), off.shape)
                par.append(
                    f"Keliru klasifikasi terbanyak terjadi antara kelompok \"{str(dfk.index[pos[0]]).replace('Aktual ', '')}\" "
                    f"dan \"{str(dfk.columns[pos[1]]).replace('Pred ', '')}\" ({int(off[pos])} kasus), menandakan "
                    f"karakteristik kedua kelompok tersebut paling sulit dibedakan oleh variabel pembeda yang dipilih.")
        except (ValueError, TypeError):
            pass
    mt = _tab(h, "Rata-rata Variabel per Kelompok")
    if mt is not None:
        dfm = mt[1]
        try:
            sebar = dfm.std(axis=0)
            top = sebar.sort_values(ascending=False).head(2)
            par.append(
                "Variabel dengan penyebaran rata-rata antar kelompok terbesar — calon pembeda utama — adalah "
                + " dan ".join(f"{c} (sebaran rata-rata {_f(v, 2)})" for c, v in top.items()) + ".")
        except (ValueError, TypeError):
            pass
    par.append(
        "Sebagai pembanding, akurasi LDA dapat diuji terhadap metode klasifikasi lain (misalnya regresi "
        "logistik atau QDA); LDA paling unggul ketika asumsi normal multivariat dan matriks kovarians "
        "antar kelompok yang sama relatif terpenuhi.")
    return par


# ==========================================================
# 16) K-MEANS
# ==========================================================
def _narasi_kmeans(h, alpha):
    par = []
    k = _met(h, "Jumlah Cluster")
    sil = _angka(_met(h, "Silhouette Score") or "")
    rentang = _met(h, "Anggota Cluster (min–maks)")
    dist = _tab(h, "Distribusi Anggota Cluster")
    par.append(
        f"K-Means mengelompokkan observasi menjadi {k or '-'} cluster berdasarkan kemiripan nilai variabel "
        f"terpilih, dengan setiap observasi ditempatkan pada cluster yang pusatnya paling dekat. "
        + (f"Ukuran cluster berkisar dari {rentang} anggota" if rentang else "")
        + (f"; " if rentang else "; ")
        + (f"komposisi {'tergolong cukup seimbang' if dist is not None and _angka(dist[1]['Jumlah Anggota'].max() or 0) and dist is not None and (_angka(dist[1]['Jumlah Anggota'].max()) / max(_angka(dist[1]['Jumlah Anggota'].min()), 1)) < 3 else 'cukup timp - cluster kecil berpotensi merepresentasikan segmen khusus atau pencilan agregat'}"
           if dist is not None else "lihat tabel distribusi untuk memeriksa keseimbangan anggota.") + "."
    )
    if sil is not None:
        par.append(
            f"Silhouette score sebesar {_f(sil, 3)} mengindikasikan {_kat_sil(sil)}. Nilai mendekati 1 "
            f"berarti observasi sangat cocok dengan cluster-nya dan terpisah jauh dari cluster lain; "
            f"nilai negatif menandakan banyak observasi salah tempat."
        )
    pusat = _tab(h, "Pusat Cluster")
    if pusat is not None:
        par.append(
            "Tabel pusat cluster (skala asli) menunjukkan nilai tipikal tiap segmen: bandingkan nilai antar "
            "baris pada setiap variabel untuk melabeli karakteristik masing-masing cluster, misalnya "
            "\"cluster bernilai tinggi\" atau \"cluster dengan kehadiran rendah\". Label substantif seperti "
            "ini jauh lebih mudah dikomunikasikan daripada nomor cluster."
        )
    par.append(
        "Karena K-Means sensitif terhadap pilihan k dan skala variabel, gunakan grafik Elbow Method dan "
        "silhouette pada berbagai nilai k untuk menguji kestabilan solusi; pastikan juga standarisasi "
        "variabel telah digunakan bila unit pengukurannya berbeda."
    )
    return par


# ==========================================================
# 17) KRUSKAL-WALLIS
# ==========================================================
def _narasi_kruskal(h, alpha):
    par = []
    uji = _uji(h, "Kruskal-Wallis H")
    st = _tab(h, "Statistik per Kelompok")
    post = _tab(h, "Post-Hoc: Mann-Whitney")
    profil = []
    if st is not None:
        df = st[1]
        if "median" in df.columns:
            for idx, row in df.iterrows():
                profil.append(f"{idx} (median {_f(row['median'])}, n = {_f(row['count'], 0)})")
    par.append(
        "Uji Kruskal-Wallis membandingkan distribusi (melalui peringkat) tiga kelompok atau lebih sebagai "
        "alternatif non-parametrik ANOVA, sehingga tidak menuntut normalitas data. "
        + (f"Kelompok yang dibandingkan: " + ", ".join(profil) + ". " if profil else "")
    )
    if uji is not None:
        par.append(
            f"Hasil uji memperoleh H = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
            f"{_pvs(uji[2], alpha)} α ({_f(alpha)}), H₀ {_kep(uji[2], alpha)} — "
            + ("setidaknya satu kelompok berbeda secara signifikan dalam distribusi/median nilai."
               if _sig(uji[2], alpha) else
               "belum ada bukti perbedaan distribusi antar kelompok.")
        )
    nte = next((str(n) for n in getattr(h, "notes", []) if "Epsilon-squared" in str(n)), "")
    if nte:
        val = _angka(nte.split("=")[-1])
        if val is not None:
            par.append(
                f"Ukuran efek epsilon-squared = {_f(val, 3)} tergolong {_kat_eta(val)}, menunjukkan porsi "
                f"perbedaan peringkat yang dapat dijelaskan oleh keanggotaan kelompok.")
    if post is not None:
        dfp = post[1]
        sig = []
        for idx, row in dfp.iterrows():
            p = row.get("p terkoreksi", row.get("p-value"))
            if _sig(p, alpha):
                sig.append(f"{idx} (p {_pv(p)})")
        if sig:
            par.append(
                f"Uji lanjut Mann-Whitney dengan koreksi Bonferroni menetapkan {len(sig)} perbandingan "
                f"berpasangan yang signifikan: " + "; ".join(sig) + ".")
        else:
            par.append(
                "Setelah koreksi Bonferroni, tidak ada perbandingan berpasangan yang signifikan - perbedaan "
                "global kemungkinan berasal dari akumulasi selisih kecil antar banyak kelompok.")
    elif uji is not None and _sig(uji[2], alpha):
        par.append(
            "Karena hasil uji signifikan, telusuri kelompok mana yang berbeda melalui tabel post-hoc "
            "Mann-Whitney U (koreksi Bonferroni) yang tersedia di bawah.")
    else:
        par.append(
            "Karena tidak terdapat perbedaan signifikan, kelompok-kelompok dapat diperlakukan setara pada "
            "taraf signifikansi yang dipilih dan uji lanjut tidak diperlukan.")
    return par


# ==========================================================
# 18) MANN-WHITNEY U
# ==========================================================
def _narasi_mwu(h, alpha):
    uji = _uji(h, "Mann-Whitney U")
    st = _tab(h, "Statistik Kelompok")
    hs = _tab(h, "Hasil Uji Mann-Whitney")
    par = [
        "Uji Mann-Whitney U membandingkan dua kelompok independen melalui peringkat nilai tanpa "
        "menuntut normalitas, sehingga tepat digunakan ketika data tidak berdistribusi normal atau "
        "berukuran kecil.",
    ]
    if st is not None:
        df = st[1]
        if "Median" in df.columns:
            profil = ", ".join(f"{i} (median {_f(r['Median'])}, n = {_f(r['n'], 0)})"
                               for i, r in df.iterrows())
            par.append(f"Kelompok yang dibandingkan: {profil}.")
    if uji is not None and hs is not None:
        dfh = hs[1]
        r = _angka(dfh.loc["r (ukuran efek)", "Nilai"])
        par.append(
            f"Hasil uji memperoleh U = {_f(dfh.loc['U', 'Nilai'])} (Z = {_f(dfh.loc['Z', 'Nilai'])}) dengan "
            f"p-value {_pv(uji[2])}. Karena p-value {_pvs(uji[2], alpha)} α ({_f(alpha)}), H₀ {_kep(uji[2], alpha)} — "
            + ("terdapat perbedaan distribusi/median yang signifikan antara kedua kelompok."
               if _sig(uji[2], alpha) else
               "belum ada bukti perbedaan yang signifikan antara kedua kelompok.")
        )
    if st is not None and uji is not None and _sig(uji[2], alpha):
        df = st[1]
        try:
            hi = df["Median"].astype(float).idxmax()
            lo = df["Median"].astype(float).idxmin()
            par.append(
                f"Kelompok {hi} memiliki median lebih tinggi ({_f(df.loc[hi, 'Median'])}) dibandingkan "
                f"{lo} ({_f(df.loc[lo, 'Median'])}), sehingga nilai cenderung lebih besar pada kelompok {hi}.")
        except (KeyError, TypeError, ValueError):
            pass
    if hs is not None:
        r = _angka(hs[1].loc["r (ukuran efek)", "Nilai"])
        if r is not None:
            par.append(
                f"Ukuran efek r = {_f(r, 3)} tergolong {_kat_r_efek(r)}; gunakan angka ini bersama "
                f"signifikansi untuk menilai makna praktis perbedaan kedua kelompok.")
    return par


# ==========================================================
# 19) WILCOXON SIGNED-RANK
# ==========================================================
def _narasi_wilcoxon(h, alpha):
    uji = _uji(h, "Wilcoxon Signed-Rank")
    tb = _tab(h, "Hasil Uji Wilcoxon")
    par = [
        "Uji Wilcoxon signed-rank membandingkan dua pengukuran pada subjek yang sama (kondisi sebelum-"
        "sesudah) melalui peringkat besarnya selisih, sebagai alternatif non-parametrik dari uji t "
        "berpasangan.",
    ]
    if tb is not None:
        df = tb[1]
        n = _angka(df.iloc[0, 0])
        med1, med2 = _angka(df.iloc[1, 0]), _angka(df.iloc[2, 0])
        r = _angka(df.loc["r (ukuran efek)", "Nilai"])
        par.append(
            f"Analisis didasarkan pada {n} pasangan dengan selisih tidak nol. Median pengukuran pertama "
            f"sebesar {_f(med1)} dan pengukuran kedua {_f(med2)}, memberikan indikasi awal arah perubahan "
            f"{'positif' if (med2 or 0) > (med1 or 0) else 'negatif'}."
        )
        if uji is not None:
            par.append(
                f"Hasil uji memperoleh W = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
                f"{_pvs(uji[2], alpha)} α ({_f(alpha)}), H₀ {_kep(uji[2], alpha)} — "
                + ("terdapat perbedaan signifikan antara kedua pengukuran."
                   if _sig(uji[2], alpha) else
                   "belum ada bukti perubahan yang signifikan antara sebelum dan sesudah.")
            )
        if r is not None:
            par.append(
                f"Ukuran efek r = {_f(r, 3)} tergolong {_kat_r_efek(r)}; pertimbangkan pula magnitudonya "
                f"sebelum menyimpulkan makna praktis perubahan tersebut.")
    par.append(
        "Ingat bahwa pasangan dengan selisih nol dikeluarkan dari perhitungan; bila banyak data identik "
        "(ties) atau ukuran sampel kecil, hasil uji perlu dibaca bersama statistik deskriptifnya."
    )
    return par


# ==========================================================
# 20) FRIEDMAN
# ==========================================================
def _narasi_friedman(h, alpha):
    uji = _uji(h, "Friedman")
    tb = _tab(h, "Median per Kondisi")
    par = [
        "Uji Friedman menguji perbedaan tiga pengukuran atau lebih yang diambil pada subjek yang sama "
        "(desain berulang), sebagai padanan non-parametrik dari ANOVA ukuran berulang.",
    ]
    if tb is not None:
        df = tb[1]
        urut = df["Median"].astype(float).sort_values(ascending=False)
        par.append(
            f"Median antar kondisi berkisar dari {_f(urut.iloc[-1])} (terendah: {urut.index[-1]}) "
            f"hingga {_f(urut.iloc[0])} (tertinggi: {urut.index[0]}).")
    if uji is not None:
        par.append(
            f"Hasil uji memperoleh χ² = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
            f"{_pvs(uji[2], alpha)} α ({_f(alpha)}), H₀ {_kep(uji[2], alpha)} — "
            + ("setidaknya ada satu kondisi yang berbeda secara signifikan."
               if _sig(uji[2], alpha) else
               "belum ada bukti perbedaan antar kondisi pada taraf signifikansi terpilih.")
        )
    nte = next((str(n) for n in getattr(h, "notes", []) if "Kendall's W" in str(n)), "")
    if nte:
        val = _angka(nte.split("=")[-1])
        if val is not None:
            par.append(
                f"Ukuran efek Kendall's W = {_f(val, 3)} menunjukkan {_kat_w(val)} antar subjek dalam "
                f"merangking kondisi-kondisi yang diuji.")
    par.append(
        "Bila hasil uji signifikan, lanjutkan dengan uji Wilcoxon signed-rank berpasangan antar kondisi "
        "disertai koreksi Bonferroni untuk memetakan pasangan kondisi yang berbeda."
    )
    return par


# ==========================================================
# FALLBACK GENERIK
# ==========================================================
def _generik(h, alpha):
    par = []
    for label, st, pv, al in getattr(h, "tests", []):
        sig = _sig(pv, al)
        par.append(
            f"Uji \"{label}\" menghasilkan statistik = {_f(st)} dengan p-value {_pv(pv)}. "
            f"Karena p-value {'lebih kecil daripada' if sig else 'lebih besar daripada'} α ({_f(al)}), "
            f"H₀ {_kep(pv, al)} — hasil {'signifikan secara statistik' if sig else 'belum signifikan secara statistik'}.")
    if getattr(h, "warnings", []):
        par.append("Perhatikan catatan peringatan berikut sebelum menarik kesimpulan: " +
                   " ".join(str(w) for w in h.warnings))
    if not par:
        par.append(
            "Hasil analisis tersaji pada tabel dan grafik di bawah. Baca nilai statistik uji beserta "
            "p-value-nya untuk menilai signifikansi pada taraf α yang dipilih.")
    return par


# ==========================================================
# DISPATCHER HALAMAN INFERENS
# ==========================================================
_PETA = {
    "ols": _narasi_ols,
    "logit": _narasi_logit,
    "mnlogit": _narasi_mnlogit,
    "ordinal": _narasi_ordinal,
    "poisson": _narasi_poisson,
    "anova1": _narasi_anova1,
    "anova2": _narasi_anova2,
    "ancova": _narasi_ancova,
    "manova": _narasi_manova,
    "ttest": _narasi_ttest,
    "chisq": _narasi_chisq,
    "korelasi": _narasi_korelasi,
    "faktor": _narasi_faktor,
    "pca": _narasi_pca,
    "lda": _narasi_lda,
    "kmeans": _narasi_kmeans,
    "kruskal": _narasi_kruskal,
    "mwu": _narasi_mwu,
    "wilcoxon": _narasi_wilcoxon,
    "friedman": _narasi_friedman,
}


def buat_narasi(akey, h, alpha):
    """Kembalikan list paragraf narasi untuk analisis `akey`. Selalu aman (tidak melempar error)."""
    try:
        fn = _PETA.get(akey)
        if fn:
            paras = fn(h, alpha)
            paras = [p for p in paras if p and p.strip()]
            if paras:
                return paras
    except Exception:
        pass
    try:
        return _generik(h, alpha)
    except Exception:
        return ["Hasil analisis tersaji pada tabel dan grafik di bawah."]


# ==========================================================
# NARASI HALAMAN STATISTIK DASAR
# ==========================================================
def narasi_dasar_kolom(nama, s_all, kolom):
    """Narasi detail satu kolom numerik pada halaman Statistik Dasar."""
    try:
        n = int(len(kolom))
        kosong = int(s_all.isna().sum())
        if n == 0:
            return []
        mean, med = float(kolom.mean()), float(kolom.median())
        sd = float(kolom.std()) if n > 1 else float("nan")
        mn, mx = float(kolom.min()), float(kolom.max())
        q1, q3 = float(kolom.quantile(.25)), float(kolom.quantile(.75))
        iqr = q3 - q1
        skew = float(kolom.skew())
        kurt = float(kolom.kurtosis())
        cv = abs(sd / mean * 100) if mean not in (0, None) and not math.isnan(sd) else float("nan")
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        out = kolom[(kolom < lo) | (kolom > hi)].sort_values()

        par = []
        sel_gap = abs(mean - med) > 0.2 * (mx - mn or 1)
        if sel_gap:
            kalimat_mm = (f"Rata-rata yang {'jauh di atas' if mean > med else 'jauh di bawah'} median "
                          f"mengindikasikan distribusi {_arah_skew(skew)}.")
        else:
            kalimat_mm = "Rata-rata dan median yang berdekatan menandakan distribusi relatif simetris."
        par.append(
            f"Variabel \"{nama}\" memiliki {n:,} data valid"
            + (f" dengan {kosong} nilai kosong yang dikeluarkan dari perhitungan" if kosong else "")
            + f". Rata-ratanya sebesar {_f(mean)} dengan median {_f(med)} dan simpangan baku {_f(sd)}. "
            + kalimat_mm + f" Nilai data berkisar dari {_f(mn)} sampai {_f(mx)}."
        )
        par.append(
            f"Seperempat data berada di bawah {_f(q1)} (Q1) dan seperempat di atas {_f(q3)} (Q3), "
            f"sehingga rentang antarkuartilnya {_f(iqr)}. Koefisien variasi sebesar "
            f"{_f(cv, 1)}% menunjukkan data {_cv_kat(cv)} relatif terhadap rata-ratanya. "
            f"Nilai kemencengan (skewness) = {_f(skew, 3)} ({_arah_skew(skew)}) dan keruncingan "
            f"(kurtosis) = {_f(kurt, 3)} "
            + ("lebih tinggi daripada distribusi normal (leptokurtik)." if kurt > 0.5 else
               "lebih datar daripada distribusi normal (platykurtik)." if kurt < -0.5 else
               "mendekati distribusi normal (mesokurtik).")
        )
        if 3 <= n <= 5000 and sd > 0 and not math.isnan(sd):
            w, p = sps.shapiro(kolom)
            par.append(
                f"Uji normalitas Shapiro-Wilk menghasilkan W = {_f(w, 4)} dengan p-value {_pv(p)}. "
                f"Karena p-value {_pvs(p, 0.05)} 0.05, data "
                + ("dapat diasumsikan berdistribusi normal sehingga uji parametrik (uji t, ANOVA, korelasi "
                   "Pearson) layak digunakan." if not _sig(p, 0.05) else
                   "menyimpang dari distribusi normal; untuk pengujian lebih lanjut pertimbangkan uji "
                   "non-parametrik atau transformasi data.")
            )
        elif n < 3:
            par.append("Jumlah data terlalu sedikit untuk uji normalitas Shapiro-Wilk (minimal 3 observasi).")
        if len(out):
            contoh = ", ".join(_f(v) for v in out.head(5).tolist())
            par.append(
                f"Terdeteksi {len(out)} pencilan berdasarkan kriteria 1,5 × IQR (batas {_f(lo)} - {_f(hi)}): "
                f"{contoh}{' …' if len(out) > 5 else ''}. Nilai-nilai ekstrem ini layak diverifikasi apakah "
                f"merupakan kesalahan pencatatan atau kejadian nyata, karena dapat memengaruhi rata-rata "
                f"dan simpangan baku secara besar.")
        else:
            par.append(
                f"Tidak ditemukan pencilan berdasarkan kriteria 1,5 × IQR (batas {_f(lo)} - {_f(hi)}), "
                f"menandakan sebaran data relatif seragam tanpa nilai yang menyimpang ekstrem.")
        return par
    except Exception:
        return []


def narasi_dasar_ringkasan(df, numeric_cols):
    """Narasi singkat tabel ringkasan semua kolom numerik."""
    try:
        if not numeric_cols:
            return []
        n_baris = int(len(df))
        cv, sk, hilang = [], [], []
        for c in numeric_cols:
            s = df[c].dropna()
            if len(s) < 2 or float(s.mean()) == 0:
                continue
            sd = float(s.std())
            m = float(s.mean())
            if not math.isnan(sd) and m != 0:
                cv.append((c, abs(sd / m * 100)))
            skv = float(s.skew())
            if not math.isnan(skv):
                sk.append((c, abs(skv)))
            nmiss = int(df[c].isna().sum())
            if nmiss > 0:
                hilang.append(f"{c} ({nmiss} nilai)")
        par = []
        par.append(
            f"Tabel di atas merangkum 13 metrik statistik untuk {len(numeric_cols)} kolom numerik "
            f"dari {n_baris:,} baris data. Statistik seperti mean dan std deviasi memberi gambaran "
            f"pusat dan penyebaran tiap variabel, sementara skewness dan kurtosis menunjukkan bentuk "
            f"distribusinya."
        )
        if cv:
            cv.sort(key=lambda t: -t[1])
            c, v = cv[0]
            par.append(
                f"Variabel \"{c}\" paling beragam (koefisien variasi {_f(v, 1)}%), sedangkan "
                + (f"variabel paling konsisten adalah \"{cv[-1][0]}\" ({_f(cv[-1][1], 1)}%). "
                   if len(cv) > 1 else "")
                + (f"Kemencengan paling kuat terjadi pada \"{sk[0][0]}\" (|skewness| = {_f(sk[0][1], 2)}) "
                   "yang perlu diwaspadai saat memilih uji parametrik. " if sk else "")
                + (f"Beberapa kolom memiliki nilai kosong: " + ", ".join(hilang[:5]) +
                   ("…" if len(hilang) > 5 else "") + "." if hilang else
                   "Tidak ditemukan nilai kosong pada kolom numerik mana pun.")
            )
        return par
    except Exception:
        return []


def narasi_dasar_kategorik(df, object_cols):
    """Narasi singkat statistik kolom kategorik."""
    try:
        if not object_cols:
            return []
        frasa = []
        dominan = []
        for c in object_cols[:8]:
            s = df[c].dropna().astype(str)
            if s.empty:
                continue
            vc = s.value_counts()
            top, freq = str(vc.index[0]), int(vc.iloc[0])
            share = freq / len(s) * 100
            frasa.append(f"{c} ({int(vc.count())} kategori; terbanyak \"{top}\" = {freq:,} atau {_pc(share)})")
            if share >= 50:
                dominan.append(c)
        if not frasa:
            return []
        return [
            "Statistik kolom kategorik merangkum keragaman kategori dan nilai yang paling sering muncul: "
            + "; ".join(frasa) + ". ",
            ("Kolom " + ", ".join(f"\"{c}\"" for c in dominan) +
             " didominasi satu kategori (≥ 50% data); ketimpangan seperti ini penting diperhatikan "
             "ketika kolom digunakan sebagai faktor pembagi dalam uji beda, karena kelompok kecil "
             "menghasilkan estimasi yang kurang stabil." if dominan else
             "Tidak ada kolom yang didominasi satu kategori secara ekstrem, sehingga pembagian kelompok "
             "untuk analisis lanjutan relatif seimbang.")
        ]
    except Exception:
        return []
