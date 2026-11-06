# -*- coding: utf-8 -*-
"""
AseliPedas - Generator Narasi Analisis Halaman NON-PARAMETRIK
===========================================================
Menghasilkan narasi interpretasi (bahasa Indonesia) untuk 12 uji
non-parametrik pada halaman Non Parametrik, mengikuti pola yang sama
dengan narasi.py: statistik uji -> p-value vs alpha -> keputusan H0/H1
-> kesimpulan kontekstual siap laporan.

Fungsi publik:
  - buat_narasi_np(akey, h, alpha) -> list[str]

Semua builder defensif: kegagalan satu analisis tidak pernah merusak hasil.
"""
import math

import numpy as np

from narasi import (
    _f, _pv, _sig, _angka, _uji, _tab, _met, _kep, _pvs,
    _kat_r, _kat_r_efek, _kat_eta, _kat_w, _arah_skew, _generik,
)


# ==========================================================
# 1) SHAPIRO-WILK
# ==========================================================
def _np_shapiro(h, alpha):
    uji = _uji(h, "Shapiro-Wilk")
    tb = _tab(h, "Hasil Uji Shapiro-Wilk")
    par = [
        "Uji Shapiro-Wilk menguji apakah suatu variabel numerik berdistribusi normal dengan "
        "membandingkan pola (korelasi antar titik) data terhadap kurva normal ideal. Uji ini "
        "paling andal untuk sampel kecil hingga menengah (n < 50) dan lazim dipakai sebagai "
        "pemeriksaan prasyarat sebelum uji parametrik seperti uji t atau ANOVA.",
    ]
    n = _met(h, "n")
    if n:
        par.append(f"Data yang diuji berjumlah {n} observasi valid setelah nilai kosong dikeluarkan.")
    if uji is not None:
        par.append(
            f"Hasil uji memperoleh W = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
            f"{_pvs(uji[2], alpha)} \u03b1 ({_f(alpha)}), H\u2080 {_kep(uji[2], alpha)} — "
            + ("data tidak berdistribusi normal."
               if _sig(uji[2], alpha) else
               "data dapat dianggap berdistribusi normal pada taraf signifikansi yang dipilih.")
        )
    else:
        par.append("Hasil uji tersaji pada tabel di bawah; bandingkan p-value dengan \u03b1 untuk mengambil keputusan.")
    if uji is not None and _sig(uji[2], alpha):
        par.append(
            "Implikasinya, uji parametrik yang mensyaratkan normalitas (uji t, ANOVA, korelasi Pearson) "
            "kurang tepat digunakan. Pertimbangkan uji non-parametrik — Mann-Whitney U untuk dua kelompok "
            "bebas, Wilcoxon untuk data berpasangan, Kruskal-Wallis untuk tiga kelompok atau lebih — atau "
            "transformasi data (misalnya logaritma) sebelum menguji ulang.")
    elif uji is not None:
        par.append(
            "Implikasinya, asumsi normalitas terpenuhi sehingga uji parametrik (uji t, ANOVA, korelasi "
            "Pearson) dapat digunakan dengan lebih aman dan berdaya uji lebih tinggi.")
    for w in getattr(h, "warnings", []):
        if "Shapiro" in str(w) or "5000" in str(w):
            par.append(str(w))
    return par


# ==========================================================
# 2) KOLMOGOROV-SMIRNOV (LILLIEFORS)
# ==========================================================
def _np_ks(h, alpha):
    uji = _uji(h, "Kolmogorov-Smirnov")
    par = [
        "Uji Kolmogorov-Smirnov (koreksi Lilliefors) menguji normalitas dengan mengukur jarak terbesar "
        "antara fungsi distribusi kumulatif data dan distribusi normal yang parameternya diestimasi dari "
        "data itu sendiri, sehingga cocok untuk sampel yang lebih besar dan populer pada output SPSS "
        "untuk n > 50.",
    ]
    n = _met(h, "n")
    if n:
        par.append(f"Data yang diuji berjumlah {n} observasi valid setelah nilai kosong dikeluarkan.")
    if uji is not None:
        par.append(
            f"Hasil uji memperoleh statistik L = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
            f"{_pvs(uji[2], alpha)} \u03b1 ({_f(alpha)}), H\u2080 {_kep(uji[2], alpha)} — "
            + ("data menyimpang secara signifikan dari distribusi normal (tidak normal)."
               if _sig(uji[2], alpha) else
               "data dapat dianggap berdistribusi normal pada taraf signifikansi yang dipilih.")
        )
    if uji is not None and _sig(uji[2], alpha):
        par.append(
            "Untuk data yang tidak normal ini, pilih uji non-parametrik sebagai pengganti uji parametrik: "
            "Mann-Whitney U (dua kelompok bebas), Wilcoxon signed-rank (berpasangan), atau Kruskal-Wallis "
            "(tiga kelompok atau lebih). Perhatikan bahwa pada sampel sangat besar, uji normalitas mudah "
            "menjadi signifikan untuk penyimpangan kecil — pertimbangkan juga plot histogram pada bagian "
            "grafik untuk menilai relevansi praktisnya.")
    elif uji is not None:
        par.append(
            "Dengan asumsi normalitas terpenuhi, analisis parametrik berikutnya (uji t, ANOVA, regresi "
            "dengan residual normal) dapat dilanjutkan tanpa transformasi tambahan.")
    return par


# ==========================================================
# 3) LEVENE (HOMOGENITAS VARIANS)
# ==========================================================
def _np_levene(h, alpha):
    uji = _uji(h, "Levene")
    st = _tab(h, "Statistik per Kelompok")
    par = [
        "Uji Levene menguji homogenitas varians — apakah ragam (sebaran) nilai antar kelompok relatif "
        "sama. Uji ini menjadi prasyarat penting sebelum ANOVA atau uji t independen, karena kedua uji "
        "tersebut sensitif terhadap ketidaksamaan varians antar kelompok. Versi yang dipakai berbasis "
        "median (Brown-Forsythe) sehingga tahan terhadap data yang tidak normal.",
    ]
    if st is not None:
        df = st[1]
        if "varians" in df.columns:
            profil = ", ".join(f"{i} (varians {_f(r['varians'])}, n = {_f(r['n'], 0)})"
                               for i, r in df.iterrows())
            par.append(f"Varians per kelompok yang dibandingkan: {profil}.")
    if uji is not None:
        par.append(
            f"Hasil uji memperoleh W = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
            f"{_pvs(uji[2], alpha)} \u03b1 ({_f(alpha)}), H\u2080 {_kep(uji[2], alpha)} — "
            + ("minimal satu kelompok memiliki varians yang berbeda secara signifikan (tidak homogen)."
               if _sig(uji[2], alpha) else
               "varians antar kelompok dapat dianggap homogen pada taraf signifikansi yang dipilih.")
        )
    if uji is not None and _sig(uji[2], alpha):
        par.append(
            "Karena asumsi homogenitas tidak terpenuhi, gunakan alternatif yang taman (robust): Welch ANOVA "
            "atau Welch t-test untuk data parametrik, atau langsung uji non-parametrik Kruskal-Wallis yang "
            "membandingkan peringkat dan relatif tahan terhadap perbedaan varians.")
    elif uji is not None:
        par.append(
            "Dengan varians yang homogen, ANOVA satu arah atau uji t independen (dengan pooled variance) "
            "dapat dilanjutkan dan hasilnya valid.")
    return par


# ==========================================================
# 4) MANN-WHITNEY U
# ==========================================================
def _np_mwu(h, alpha):
    uji = _uji(h, "Mann-Whitney U")
    st = _tab(h, "Statistik Kelompok")
    hs = _tab(h, "Hasil Uji Mann-Whitney")
    par = [
        "Uji Mann-Whitney U membandingkan dua kelompok independen melalui peringkat (rank) nilai, bukan "
        "rata-rata, sehingga tidak menuntut normalitas. Uji ini adalah alternatif non-parametrik dari uji t "
        "sampel independen dan tepat digunakan saat data tidak normal, ordinal, atau berukuran kecil.",
    ]
    if st is not None:
        df = st[1]
        if "Median" in df.columns:
            profil = ", ".join(f"{i} (median {_f(r['Median'])}, n = {_f(r['n'], 0)})"
                               for i, r in df.iterrows())
            par.append(f"Kelompok yang dibandingkan: {profil}.")
    if uji is not None and hs is not None:
        dfh = hs[1]
        try:
            par.append(
                f"Hasil uji memperoleh U = {_f(dfh.loc['U', 'Nilai'])} (Z = {_f(dfh.loc['Z', 'Nilai'])}) "
                f"dengan p-value {_pv(uji[2])}. Karena p-value {_pvs(uji[2], alpha)} \u03b1 ({_f(alpha)}), "
                f"H\u2080 {_kep(uji[2], alpha)} — "
                + ("terdapat perbedaan distribusi/median yang signifikan antara kedua kelompok."
                   if _sig(uji[2], alpha) else
                   "belum ada bukti perbedaan yang signifikan antara kedua kelompok.")
            )
        except KeyError:
            par.append(
                f"Hasil uji memperoleh U = {_f(uji[1])} dengan p-value {_pv(uji[2])}; H\u2080 "
                f"{_kep(uji[2], alpha)} pada \u03b1 = {_f(alpha)}.")
    if st is not None and uji is not None and _sig(uji[2], alpha):
        df = st[1]
        try:
            hi = df["Median"].astype(float).idxmax()
            lo = df["Median"].astype(float).idxmin()
            par.append(
                f"Nilai cenderung lebih besar pada kelompok {hi} (median {_f(df.loc[hi, 'Median'])}) "
                f"dibandingkan {lo} (median {_f(df.loc[lo, 'Median'])}), sehingga kelompok {hi} relatif "
                f"lebih unggul dalam skala yang diukur.")
        except (KeyError, TypeError, ValueError):
            pass
    if hs is not None:
        try:
            r = _angka(hs[1].loc["r (ukuran efek)", "Nilai"])
            if r is not None:
                par.append(
                    f"Ukuran efek r = {_f(r, 3)} tergolong {_kat_r_efek(r)}; gunakan angka ini bersama "
                    f"signifikansi untuk menilai makna praktis perbedaan kedua kelompok, karena p-value "
                    f"saja tidak menggambarkan besarnya perbedaan.")
        except (KeyError, TypeError, ValueError):
            pass
    return par


# ==========================================================
# 5) WILCOXON SIGNED-RANK
# ==========================================================
def _np_wilcoxon(h, alpha):
    uji = _uji(h, "Wilcoxon Signed-Rank")
    tb = _tab(h, "Hasil Uji Wilcoxon")
    par = [
        "Uji Wilcoxon signed-rank membandingkan dua pengukuran pada subjek yang sama (kondisi sebelum-"
        "sesudah) melalui peringkat besarnya selisih. Uji ini menjadi alternatif non-parametrik dari uji t "
        "berpasangan dan tidak menuntut normalitas selisih antar pengukuran.",
    ]
    if tb is not None:
        df = tb[1]
        try:
            n = _angka(df.iloc[0, 0])
            med1, med2 = _angka(df.iloc[1, 0]), _angka(df.iloc[2, 0])
            par.append(
                f"Sebanyak {n} pasangan data valid dianalisis; median berubah dari {_f(med1)} pada "
                f"pengukuran pertama menjadi {_f(med2)} pada pengukuran kedua."
            )
        except (IndexError, TypeError, ValueError):
            pass
    if uji is not None:
        par.append(
            f"Hasil uji memperoleh W = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
            f"{_pvs(uji[2], alpha)} \u03b1 ({_f(alpha)}), H\u2080 {_kep(uji[2], alpha)} — "
            + ("terdapat perbedaan yang signifikan antara kondisi sebelum dan sesudah perlakuan."
               if _sig(uji[2], alpha) else
               "belum ada bukti perbedaan yang signifikan antara kedua pengukuran.")
        )
    if tb is not None:
        try:
            r = _angka(tb[1].loc["r (ukuran efek)", "Nilai"])
            if r is not None:
                par.append(
                    f"Ukuran efek r = {_f(r, 3)} tergolong {_kat_r_efek(r)}; semakin besar nilainya, "
                    f"semakin kuat pula signifikansi praktis perubahan antar pengukuran tersebut.")
        except (KeyError, TypeError, ValueError):
            pass
    if uji is not None and _sig(uji[2], alpha):
        par.append(
            "Kesimpulannya, perlakuan (intervensi) yang diberikan berdampak nyata terhadap nilai yang diukur "
            "pada subjek yang sama. Sampaikan juga arah perubahan (naik/turun) dengan merujuk median kedua "
            "pengukuran pada tabel di atas agar laporan lebih informatif.")
    return par


# ==========================================================
# 6) KRUSKAL-WALLIS
# ==========================================================
def _np_kruskal(h, alpha):
    uji = _uji(h, "Kruskal-Wallis")
    st = _tab(h, "Statistik per Kelompok")
    post = _tab(h, "Post-Hoc: Mann-Whitney")
    profil = []
    if st is not None:
        df = st[1]
        if "median" in df.columns:
            for idx, row in df.iterrows():
                profil.append(f"{idx} (median {_f(row['median'])}, n = {_f(row['count'], 0)})")
    par = []
    par.append(
        "Uji Kruskal-Wallis membandingkan distribusi (melalui peringkat) tiga kelompok atau lebih sebagai "
        "alternatif non-parametrik ANOVA satu arah, sehingga tidak menuntut normalitas maupun homogenitas "
        "varians. "
        + (f"Kelompok yang dibandingkan: " + ", ".join(profil) + ". " if profil else "")
    )
    if uji is not None:
        par.append(
            f"Hasil uji memperoleh H = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
            f"{_pvs(uji[2], alpha)} \u03b1 ({_f(alpha)}), H\u2080 {_kep(uji[2], alpha)} — "
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
            "Mann-Whitney U (koreksi Bonferroni) di bawah, lalu bandingkan median tiap kelompok untuk "
            "menentukan urutan peringkatnya.")
    else:
        par.append(
            "Karena tidak terdapat perbedaan signifikan, kelompok-kelompok dapat diperlakukan setara pada "
            "taraf signifikansi yang dipilih dan uji lanjut tidak diperlukan.")
    return par


# ==========================================================
# 7) FRIEDMAN
# ==========================================================
def _np_friedman(h, alpha):
    uji = _uji(h, "Friedman")
    st = _tab(h, "Median per Kondisi")
    par = [
        "Uji Friedman membandingkan tiga kondisi atau lebih yang diukur berulang pada subjek yang sama "
        "(misalnya pre-test, post-test 1, post-test 2) melalui peringkat dalam tiap subjek. Uji ini adalah "
        "alternatif non-parametrik dari ANOVA ukuran berulang dan tidak menuntut normalitas.",
    ]
    if st is not None:
        df = st[1]
        try:
            profil = ", ".join(f"{i} (median {_f(r.iloc[0])})" for i, r in df.iterrows())
            par.append(f"Median tiap kondisi: {profil}.")
        except (IndexError, TypeError, ValueError):
            pass
    if uji is not None:
        par.append(
            f"Hasil uji memperoleh chi-square = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
            f"{_pvs(uji[2], alpha)} \u03b1 ({_f(alpha)}), H\u2080 {_kep(uji[2], alpha)} — "
            + ("minimal satu kondisi memiliki distribusi/median yang berbeda secara signifikan."
               if _sig(uji[2], alpha) else
               "belum ada bukti perbedaan yang signifikan antar kondisi pengukuran.")
        )
    nte = next((str(n) for n in getattr(h, "notes", []) if "Kendall" in str(n)), "")
    if nte:
        val = _angka(nte.split("=")[-1])
        if val is not None:
            par.append(
                f"Ukuran efek Kendall's W = {_f(val, 3)} tergolong {_kat_w(val)} — menggambarkan tingkat "
                f"kemiripan pola peringkat antar subjek (konsordansi) akibat perbedaan kondisi.")
    if uji is not None and _sig(uji[2], alpha):
        best = None
        if st is not None:
            try:
                best = st[1].iloc[:, 0].astype(float).idxmax()
            except (IndexError, TypeError, ValueError):
                best = None
        par.append(
            "Karena hasil signifikan, lakukan uji lanjutan antar kondisi berpasangan (misalnya Wilcoxon "
            "signed-rank dengan koreksi Bonferroni) untuk mengetahui pasangan kondisi yang berbeda."
            + (f" Kondisi {best} mencatat median tertinggi dan layak menjadi fokus perhatian." if best else "")
        )
    return par


# ==========================================================
# 8) RUNS TEST (KEACAKAN)
# ==========================================================
def _np_runs(h, alpha):
    uji = _uji(h, "Runs")
    tb = _tab(h, "Hasil Uji Runs")
    par = [
        "Uji Runs (Wald-Wolfowitz) menilai apakah urutan kemunculan data terjadi secara acak. Data "
        "dikotomisasi di sekitar mediannya, lalu dihitung jumlah run — rangkaian nilai berurutan yang "
        "berada pada sisi yang sama dari median. Terlalu sedikit run menandakan pola menggerombol, "
        "terlalu banyak run menandakan pola bergantian yang juga tidak acak.",
    ]
    if tb is not None and uji is not None:
        df = tb[1]
        try:
            n = _angka(df.loc["n (data valid)", "Nilai"])
            n1 = _angka(df.loc["n1 (di atas median)", "Nilai"])
            n2 = _angka(df.loc["n2 (di bawah median)", "Nilai"])
            runs = _angka(df.loc["R (jumlah run)", "Nilai"])
            er = _angka(df.loc["E(R) (ekspektasi run)", "Nilai"])
            par.append(
                f"Dari {n} data valid, {n1} berada di atas median dan {n2} di bawah median, dengan jumlah "
                f"run teramati R = {runs} (ekspektasi acak {er})."
            )
        except (KeyError, TypeError, ValueError):
            pass
    if uji is not None:
        arah = ""
        try:
            runs = _angka(tb[1].loc["R (jumlah run)", "Nilai"])
            er = _angka(tb[1].loc["E(R) (ekspektasi run)", "Nilai"])
            if runs is not None and er is not None:
                arah = (" Jumlah run yang lebih kecil dari ekspektasi mengindikasikan pola menggerombol "
                        "(clustering)." if runs < er else
                        " Jumlah run yang lebih besar dari ekspektasi mengindikasikan pola bergantian "
                        "yang sistematis.")
        except (KeyError, TypeError, ValueError):
            pass
        par.append(
            f"Hasil uji memperoleh Z = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
            f"{_pvs(uji[2], alpha)} \u03b1 ({_f(alpha)}), H\u2080 {_kep(uji[2], alpha)} — "
            + ("urutan data tidak acak." + arah
               if _sig(uji[2], alpha) else
               "urutan data dapat dianggap acak pada taraf signifikansi yang dipilih.")
        )
    if uji is not None and _sig(uji[2], alpha):
        par.append(
            "Implikasinya, terdapat faktor sistematis yang memengaruhi urutan data — periksa apakah ada "
            "tren waktu, efek pembelajaran, atau pergeseran proses. Pada konteks produksi misalnya, pola "
            "menggerombol cacat menandakan penyebab khusus (special cause) yang perlu diinvestigasi.")
    elif uji is not None:
        par.append(
            "Implikasinya, tidak ada bukti pola sistematis pada urutan data sehingga proses atau mekanisme "
            "pembangkitan data dapat dianggap stabil dan acak.")
    return par


# ==========================================================
# 9) McNEMAR
# ==========================================================
def _np_mcnemar(h, alpha):
    uji = _uji(h, "Uji McNemar", "McNemar")
    tb = _tab(h, "Tabel Kontingensi 2x2")
    hs = _tab(h, "Hasil Uji McNemar")
    par = [
        "Uji McNemar membandingkan proporsi dua kondisi pada subjek yang sama untuk data biner (dua "
        "kategori), misalnya minat beli sebelum vs sesudah kampanye iklan. Uji ini hanya menggunakan "
        "pasangan yang berubah (discordant), yaitu pasangan dengan jawaban berbeda antara kedua pengukuran.",
    ]
    b = _met(h, "b (A")
    c = _met(h, "c (B")
    if b is not None and c is not None:
        try:
            bf, cf = float(b), float(c)
            if bf > cf:
                par.append(
                    f"Terdapat {bf:.0f} pasangan yang berubah dari kategori pertama ke kategori kedua "
                    f"dan {cf:.0f} pasangan yang berubah sebaliknya \u2014 perubahan net ({bf - cf:+.0f}) "
                    f"menuju kategori kedua lebih banyak terjadi.")
            else:
                par.append(
                    f"Terdapat {bf:.0f} pasangan yang berubah dari kategori pertama ke kategori kedua "
                    f"dan {cf:.0f} pasangan yang berubah sebaliknya \u2014 perubahan net ({cf - bf:+.0f}) "
                    f"menuju kategori pertama lebih banyak terjadi.")
        except (TypeError, ValueError):
            pass
    if uji is not None:
        par.append(
            f"Hasil uji memperoleh statistik = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
            f"{_pvs(uji[2], alpha)} \u03b1 ({_f(alpha)}), H\u2080 {_kep(uji[2], alpha)} — "
            + ("proporsi kedua kategori berubah secara signifikan antara kedua pengukuran."
               if _sig(uji[2], alpha) else
               "belum ada bukti perubahan proporsi yang signifikan antara kedua pengukuran.")
        )
    if uji is not None and _sig(uji[2], alpha):
        par.append(
            "Kesimpulannya, perlakuan (misalnya kampanye, pelatihan, atau intervensi) terbukti mengubah "
            "komposisi jawaban subjek secara bermakna. Laporkan besarnya perubahan net (selisih pasangan "
            "discordant) agar pembaca laporan menangkap arah dan magnitudo dampaknya.")
    elif uji is not None:
        par.append(
            "Kesimpulannya, intervensi belum mengubah proporsi jawaban secara signifikan; perbedaan kecil "
            "antara kedua pengukuran kemungkinan hanya akibat variasi acak.")
    return par


# ==========================================================
# 10) CHI-SQUARE GOODNESS-OF-FIT
# ==========================================================
def _np_gof(h, alpha):
    uji = _uji(h, "Chi-Square Goodness-of-Fit")
    st = _tab(h, "Frekuensi per Kategori")
    par = [
        "Uji Chi-Square Goodness-of-Fit menguji apakah distribusi frekuensi satu variabel kategorik "
        "mengikuti pola tertentu — pada aplikasi ini, pola seragam (setiap kategori diharapkan memiliki "
        "frekuensi yang sama). Uji ini menjawab pertanyaan seperti: apakah permintaan menu terdistribusi "
        "merata, ataukah ada kategori yang menonjol?",
    ]
    if st is not None:
        df = st[1]
        try:
            obs = df["Observed"].astype(float)
            exp = df["Expected"].astype(float)
            dev = (obs - exp).abs()
            top = dev.idxmax()
            par.append(
                f"Kategori {top} menyimpang paling jauh dari ekspektasi seragam "
                f"(observasi {obs.loc[top]:,.0f} vs ekspektasi {exp.loc[top]:,.0f})."
            )
        except (KeyError, TypeError, ValueError):
            pass
    if uji is not None:
        par.append(
            f"Hasil uji memperoleh chi-square = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
            f"{_pvs(uji[2], alpha)} \u03b1 ({_f(alpha)}), H\u2080 {_kep(uji[2], alpha)} — "
            + ("distribusi frekuensi antar kategori tidak seragam; terdapat kategori yang berbeda signifikan."
               if _sig(uji[2], alpha) else
               "frekuensi antar kategori dapat dianggap seragam pada taraf signifikansi yang dipilih.")
        )
    for n in getattr(h, "notes", []):
        if "df" in str(n):
            par.append(f"Derajat kebebasan uji: {n}.")
        if "ekspektasi" in str(n).lower() and "df" not in str(n):
            par.append(str(n))
    if uji is not None and _sig(uji[2], alpha):
        par.append(
            "Kesimpulannya, preferensi/kemunculan kategori tidak berimbang — gunakan tabel dan grafik "
            "frekuensi di bawah untuk menyorot kategori yang paling dominan atau paling sepi, lalu tautkan "
            "temuan ini ke konteks praktis (misalnya manajemen stok, alokasi sumber daya, atau perbaikan "
            "layanan).")
    return par


# ==========================================================
# 11) KORELASI SPEARMAN
# ==========================================================
def _np_spearman(h, alpha):
    uji = _uji(h, "Korelasi Spearman")
    tb = _tab(h, "Korelasi Spearman Berpasangan")
    par = [
        "Korelasi Spearman (rho) mengukur kekuatan dan arah hubungan monotonic antara dua variabel melalui "
        "peringkatnya, sehingga tahan terhadap outlier dan tepat untuk data ordinal (misalnya skala Likert). "
        "Nilai rho berkisar -1 hingga +1: semakin dekat ke -1 atau +1, semakin kuat hubungan; tanda "
        "menunjukkan arah hubungan.",
    ]
    sig_pairs = []
    if tb is not None:
        df = tb[1]
        try:
            for _, row in df.iterrows():
                if _sig(row["p-value"], alpha):
                    sig_pairs.append((row["Variabel 1"], row["Variabel 2"],
                                      float(row["rho"]), float(row["p-value"])))
        except (KeyError, TypeError, ValueError):
            pass
    if uji is not None:
        par.append(
            f"Pasangan dengan korelasi terkuat adalah {uji[0].replace('Korelasi Spearman (terkuat) ', '').strip(': ')} "
            f"dengan rho = {_f(uji[1])} dan p-value {_pv(uji[2])}. Karena p-value {_pvs(uji[2], alpha)} "
            f"\u03b1 ({_f(alpha)}), H\u2080 {_kep(uji[2], alpha)} — "
            + ("terdapat korelasi monotonic yang signifikan pada pasangan tersebut."
               if _sig(uji[2], alpha) else
               "belum ada bukti korelasi yang signifikan pada pasangan terkuat sekalipun.")
        )
    if sig_pairs:
        daftar = "; ".join(f"{a} vs {b} (rho = {_f(r)}, p {_pv(p)})" for a, b, r, p in sig_pairs[:8])
        par.append(f"Seluruh pasangan signifikan ({len(sig_pairs)}): {daftar}.")
        kualifikasi = ", ".join(sorted({f"{_kat_r(r)}" for _, _, r, _ in sig_pairs}))
        par.append(
            f"Kekuatan hubungan pasangan signifikan tergolong {kualifikasi}. Ingat bahwa korelasi tidak "
            f"menunjukkan kausalitas — nilai tinggi pada satu variabel belum tentu menyebabkan nilai "
            f"tinggi pada variabel lain.")
    else:
        par.append(
            "Tidak ada pasangan variabel yang berkorelasi signifikan pada taraf \u03b1 yang dipilih; "
            "peringkat kedua variabel tidak menunjukkan hubungan monotonic yang meyakinkan.")
    return par


# ==========================================================
# 12) KORELASI KENDALL TAU
# ==========================================================
def _np_kendall(h, alpha):
    uji = _uji(h, "Kendall")
    tb = _tab(h, "Hasil Uji Kendall")
    par = [
        "Korelasi Kendall tau-b mengukur kesesuaian peringkat antara dua variabel dengan membandingkan "
        "seluruh pasangan titik data (konkordan vs diskordan). Tau lebih robust daripada Spearman untuk "
        "sampel kecil dan data dengan banyak ikatan (ties), nilainya juga lebih mudah ditafsirkan sebagai "
        "probabilitas kesesuaian urutan.",
    ]
    if tb is not None:
        df = tb[1]
        try:
            n = _angka(df.loc["n (pasangan data)", "Nilai"])
            par.append(f"Sebanyak {n} observasi valid dianalisis secara berpasangan.")
        except (KeyError, TypeError, ValueError):
            pass
    if uji is not None:
        par.append(
            f"Hasil uji memperoleh tau-b = {_f(uji[1])} dengan p-value {_pv(uji[2])}. Karena p-value "
            f"{_pvs(uji[2], alpha)} \u03b1 ({_f(alpha)}), H\u2080 {_kep(uji[2], alpha)} — "
            + ("terdapat korelasi peringkat yang signifikan antara kedua variabel."
               if _sig(uji[2], alpha) else
               "belum ada bukti korelasi peringkat yang signifikan antara kedua variabel.")
        )
        tau = abs(float(uji[1])) if uji[1] is not None else None
        if tau is not None and not (isinstance(tau, float) and math.isnan(tau)):
            arah = "positif (searah)" if float(uji[1]) > 0 else "negatif (berlawanan arah)"
            par.append(
                f"Kekuatan hubungan {arah} tergolong {_kat_r(uji[1])}; secara praktis, ketika peringkat satu "
                f"variabel naik, peringkat variabel lain "
                + ("cenderung naik pula." if float(uji[1]) > 0 else "cenderung turun.")
                + " Korelasi tetap bukan bukti kausalitas."
            )
    return par


# ==========================================================
# DISPATCHER HALAMAN NON-PARAMETRIK
# ==========================================================
_PETA_NP = {
    "shapiro": _np_shapiro,
    "ks": _np_ks,
    "levene": _np_levene,
    "mwu": _np_mwu,
    "wilcoxon": _np_wilcoxon,
    "kruskal": _np_kruskal,
    "friedman": _np_friedman,
    "runs": _np_runs,
    "mcnemar": _np_mcnemar,
    "gof": _np_gof,
    "spearman": _np_spearman,
    "kendall": _np_kendall,
}


def buat_narasi_np(akey, h, alpha):
    """Kembalikan list paragraf narasi untuk uji non-parametrik `akey`. Selalu aman."""
    try:
        fn = _PETA_NP.get(akey)
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
