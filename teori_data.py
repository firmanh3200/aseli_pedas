# -*- coding: utf-8 -*-
"""
AseliPedas - Data Teori: Konsep Dasar & Peta Pemilihan Uji
=======================================================
Konten pengantar untuk halaman Teori Uji Statistik:
  - KONSEP : kartu konsep dasar statistik inferensial
  - PETA   : tabel panduan memilih uji sesuai tujuan & jenis data
"""

# (ikon, judul, isi) - ikon mengacu ke dict ICONS inferens.py
KONSEP = [
    ("database", "Populasi & Sampel",
     "Statistik inferensial menggeneralisasi hasil dari sampel ke populasi. Karakter "
     "populasi disebut parameter (μ, σ²) dan bersifat tetap namun tak terketahui; "
     "karakter sampel disebut statistik (x̄, s²) dan berubah dari sampel ke sampel. "
     "Seluruh uji pada aplikasi ini pada dasarnya menilai seberapa jauh temuan sampel "
     "dapat dipercaya sebagai gambaran populasi."),
    ("scale", "Hipotesis H₀ & H₁",
     "H₀ (hipotesis nol) menyatakan tidak ada efek atau tidak ada perbedaan; H₁ "
     "(hipotesis alternatif) menyatakan efek yang hendak dibuktikan. Uji berjalan "
     "dengan asumsi H₀ benar, lalu menilai apakah data terlalu tidak wajar untuk "
     "dijelaskan oleh kebetulan semata. Hipotesis dua arah (≠) mendeteksi perbedaan "
     "ke mana pun; hipotesis satu arah (> atau <) mendeteksi arah tertentu."),
    ("percent", "P-value",
     "P-value adalah peluang memperoleh statistik uji se ekstrem (atau lebih ekstrem) "
     "dari yang teramati, diasumsikan H₀ benar. P-value kecil berarti data sulit "
     "dijelaskan oleh H₀. Perlu diingat: p-value bukan peluang H₀ benar, dan bukan "
     "pula ukuran besarnya efek - dua perbedaan yang paling sering disalahpahami."),
    ("target", "Taraf Signifikansi α",
     "α adalah ambang toleransi kesalahan Tipe I - risiko menolak H₀ padahal H₀ benar. "
     "Praktik umum memakai α = 0.05 (5%). Kebalikannya, kesalahan Tipe II adalah gagal "
     "menolak H₀ padahal H₁ benar; peluang menghindarinya disebut power (1 − β). "
     "Aplikasi mengizinkan α = 0.10, 0.05, atau 0.01 agar keputusan bisa disesuaikan "
     "dengan keketatan bidang penelitian Anda."),
    ("crosshair", "Interval Kepercayaan",
     "Interval kepercayaan memberi rentang nilai yang masuk akal bagi parameter "
     "populasi. CI 95% berarti jika pengambilan sampel diulang berkali-kali, sekitar "
     "95% interval yang dihasilkan akan memuat parameter sejati. Interval yang tidak "
     "memuat nilai nol/acuan setara dengan uji yang signifikan, tetapi CI jauh lebih "
     "informatif karena sekaligus menunjukkan presisi estimasi."),
    ("activity", "Ukuran Efek",
     "Signifikansi menunjukkan efek itu nyata, ukuran efek menunjukkan seberapa besar "
     "efek itu - keduanya bukan hal yang sama. Sampel sangat besar bisa membuat efek "
     "samar tetap signifikan. Aplikasi ini melaporkan ukuran efek bila tersedia: "
     "Cohen's d (uji t), eta² (ANOVA), Cramér's V (chi-square), R² (regresi), dan "
     "Kendall's W (Friedman)."),
    ("component", "Parametrik vs Non-Parametrik",
     "Uji parametrik (t, ANOVA, Pearson, OLS) berdaya uji lebih tinggi tetapi "
     "menuntut asumsi: data numerik, mendekati normal, dan homogen variansinya. Uji "
     "non-parametrik (Mann-Whitney, Kruskal-Wallis, Wilcoxon, Friedman, chi-square) "
     "bekerja lewat peringkat/frekuensi sehingga tahan terhadap data ordinal, skewed, "
     "dan outlier. Jika asumsi parametrik dilanggar, turunlah ke padanan "
     "non-parametriknya."),
    ("shield", "Uji Asumsi",
     "Sebelum menafsirkan hasil, periksa asumsi: normalitas (histogram, Shapiro-Wilk), "
     "homogenitas variansi (uji Levene - otomatis pada ANOVA dan uji t independen di "
     "aplikasi ini), serta independensi observasi. Pelanggaran ringan pada sampel "
     "besar biasanya masih dapat ditoleransi; pelanggaran berat mengharuskan beralih "
     "ke uji non-parametrik atau transformasi data."),
]

# (tujuan analisis, jenis data, label uji, anchor) - anchor menuju id kartu teori
PETA = [
    ("Membandingkan rata-rata satu sampel dengan nilai acuan", "1 variabel numerik",
     "Uji t - satu sampel", "th-ttest"),
    ("Membandingkan rata-rata dua kelompok bebas (data normal)", "numerik + 2 kelompok",
     "Uji t - independen", "th-ttest"),
    ("Membandingkan dua kelompok bebas (tidak normal / ordinal)", "numerik-ordinal + 2 kelompok",
     "Mann-Whitney U", "th-mwu"),
    ("Membandingkan sebelum-sesudah pada subjek sama (normal)", "2 numerik berpasangan",
     "Uji t - berpasangan", "th-ttest"),
    ("Membandingkan sebelum-sesudah (tidak normal / ordinal)", "2 pasangan data",
     "Wilcoxon Signed-Rank", "th-wilcoxon"),
    ("Membandingkan rata-rata ≥ 3 kelompok (normal)", "numerik + faktor kelompok",
     "ANOVA Satu Arah", "th-anova1"),
    ("Membandingkan median ≥ 3 kelompok (tidak normal)", "ordinal/numerik + kelompok",
     "Kruskal-Wallis", "th-kruskal"),
    ("Membandingkan ≥ 3 pengukuran berulang pada subjek sama", "numerik-ordinal berulang",
     "Friedman", "th-friedman"),
    ("Menguji dua faktor sekaligus beserta interaksinya", "numerik + 2 faktor kategorik",
     "ANOVA Dua Arah", "th-anova2"),
    ("Membandingkan kelompok sambil mengontrol variabel lain", "numerik + faktor + covariat",
     "ANCOVA", "th-ancova"),
    ("Menguji kelompok terhadap ≥ 2 variabel dependen", "≥ 2 numerik + faktor",
     "MANOVA", "th-manova"),
    ("Mengukur kekuatan & arah hubungan antar variabel numerik", "≥ 2 variabel numerik",
     "Analisis Korelasi", "th-korelasi"),
    ("Menguji asosiasi dua variabel kategorik", "2 variabel kategorik",
     "Uji Chi-Square", "th-chisq"),
    ("Memodelkan & memprediksi Y numerik dari beberapa X", "Y numerik + X numerik",
     "Regresi Linear (OLS)", "th-ols"),
    ("Memodelkan & memprediksi Y biner (ya/tidak)", "Y biner + X bebas",
     "Regresi Logistik Biner", "th-logit"),
    ("Memodelkan Y kategorik > 2 tanpa urutan", "Y nominal + X bebas",
     "Regresi Logistik Multinomial", "th-mnlogit"),
    ("Memodelkan Y bertingkat (ordinal)", "Y ordinal + X bebas",
     "Regresi Ordinal", "th-ordinal"),
    ("Memodelkan Y berupa data hitungan", "Y hitungan + X bebas",
     "Regresi Poisson", "th-poisson"),
    ("Menemukan struktur dimensi laten dari banyak item", "banyak item numerik",
     "Analisis Faktor (EFA)", "th-faktor"),
    ("Mereduksi banyak variabel jadi sedikit komponen utama", "banyak variabel numerik",
     "Analisis Komponen Utama (PCA)", "th-pca"),
    ("Mengklasifikasikan unit ke kelompok yang sudah ada", "Y kategorik + X numerik",
     "Analisis Diskriminan (LDA)", "th-lda"),
    ("Mensegmentasikan data menjadi kelompok alami", "banyak variabel numerik",
     "K-Means Clustering", "th-kmeans"),
]
