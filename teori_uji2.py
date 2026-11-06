# -*- coding: utf-8 -*-
"""
AseliPedas - Data Teori Uji (Bagian 2)
===================================
Kelompok Uji Beda & Non-Parametrik (5) + Asosiasi & Korelasi (2) +
Analisis Multivariat (4). Struktur entri sama dengan teori_uji1.py.
"""

TEORI_B = {

    # ------------------------------------------------------------------
    "ttest": dict(
        judul="Uji t", jenis="Parametrik", jcls="p",
        tujuan="Membandingkan rata-rata: satu sampel terhadap nilai acuan, dua kelompok independen, atau dua pengukuran berpasangan.",
        apa="Uji t membandingkan selisih rata-rata yang teramati dengan sebaran kebetulan (standard error) "
            "sehingga menghasilkan statistik t berdistribusi Student. Aplikasi menyediakan tiga mode: satu "
            "sampel (menguji x̄ terhadap μ₀), independen (membandingkan dua kelompok subjek berbeda dengan "
            "uji Levene otomatis untuk memilih pooled atau Welch), dan berpasangan (menguji rata-rata "
            "selisih pada subjek yang sama, pre-post).",
        kegunaan=[
            "Satu sampel: memeriksa apakah rata-rata berbeda dari standar atau acuan (misal KKM 75).",
            "Independen: membandingkan dua metode, dua kelas, dua gender, atau dua produk.",
            "Berpasangan: menilai efek program dengan desain pre-test post-test pada orang yang sama.",
            "Uji Levene otomatis memastikan pemilihan varian uji (pooled/Welch) yang tepat.",
            "Cohen's d membantu menilai besaran efek, bukan hanya signifikansinya.",
        ],
        hip=("Rata-rata populasi sama: μ = μ₀, μ₁ = μ₂, atau μd = 0.",
             "Rata-rata berbeda (dua arah), atau lebih besar/lebih kecil (satu arah)."),
        asumsi=[
            "Data numerik mendekati normal (untuk n ≥ 30 cukup robust berkat teorema limit pusat).",
            "Observasi saling independen (kecuali mode berpasangan yang justru memasangkan).",
            "Mode independen: homogenitas variansi antar kelompok dicek lewat uji Levene.",
            "Mode berpasangan: selisih d berdistribusi mendekati normal.",
        ],
        rumus=[
            "t satu sampel = (x̄ − μ₀) / (s / √n)",
            "t independen (pooled) = (x̄₁ − x̄₂) / (sₚ·√(1/n₁ + 1/n₂))",
            "Cohen's d = selisih rata-rata / simpangan baku",
        ],
        baca="p < α berarti H₀ ditolak: perbedaan signifikan secara statistik; arah perbedaan dibaca dari "
             "tanda selisih rata-rata. Cohen's d = 0.2 kecil, 0.5 sedang, 0.8 besar - perbedaan yang "
             "signifikan tetapi d kecil berarti efek nyata namun tipis secara praktis. Jika uji Levene "
             "signifikan, gunakan baris Welch pada hasil karena variansi kedua kelompok tidak sama.",
        contoh=[
            "Menguji apakah rata-rata pendapatan UMKM berbeda dari upminimum regional.",
            "Membandingkan skor kecemasan sebelum dan sesudah terapi pada pasien yang sama.",
        ],
    ),

    # ------------------------------------------------------------------
    "kruskal": dict(
        judul="Kruskal-Wallis", jenis="Non-Parametrik", jcls="n",
        tujuan="Membandingkan median atau distribusi tiga kelompok dan lebih tanpa asumsi normalitas.",
        apa="Kruskal-Wallis adalah padanan non-parametrik ANOVA satu arah: seluruh data digabung lalu "
            "diperingkat (rank), dan uji ini menilai apakah sebaran peringkat berbeda antar kelompok. "
            "Statistik H mengikuti distribusi chi-square sehingga p-value mudah dibaca. Aplikasi "
            "melengkapi dengan post-hoc Mann-Whitney berkoreksi Bonferroni dan tabel median per kelompok.",
        kegunaan=[
            "Alternatif ANOVA ketika data ordinal atau tidak normal meski sudah ditransformasi.",
            "Cocok untuk sampel kecil dengan sebaran tidak teratur atau banyak outlier.",
            "Post-hoc Mann-Whitney (Bonferroni) mengungkap pasangan kelompok yang berbeda.",
            "Analisis survei berbasis skala peringkat pada lebih dari dua kelompok.",
        ],
        hip=("Semua kelompok berasal dari distribusi yang sama (median setara).",
             "Minimal satu kelompok berbeda dari yang lain."),
        asumsi=[
            "Observasi independen antar kelompok.",
            "Variabel respons dapat diperingkat (minimal ordinal).",
            "Bentuk distribusi antar kelompok serupa agar selisih median bermakna.",
        ],
        rumus=[
            "H = (12 / (N(N+1))) · Σ(Rⱼ² / nⱼ) − 3(N + 1)",
        ],
        baca="p < α berarti minimal satu kelompok berbeda; buka tabel post-hoc Mann-Whitney untuk melihat "
             "pasangan mana yang berbeda signifikan. Bandingkan median per kelompok untuk menentukan arah. "
             "Ingat bahwa p-value tidak mengukur besar perbedaan - laporkan juga median dan selisihnya "
             "sebagai gambaran praktis.",
        contoh=[
            "Membandingkan preferensi rasa tiga produk melalui skor ordinal panelis.",
            "Menguji perbedaan lama sembuh tiga jenis terapi pada data yang skewed.",
        ],
    ),

    # ------------------------------------------------------------------
    "mwu": dict(
        judul="Mann-Whitney U", jenis="Non-Parametrik", jcls="n",
        tujuan="Membandingkan dua kelompok independen tanpa asumsi normalitas pada data.",
        apa="Mann-Whitney U menggabungkan dan memeringkat seluruh observasi dari dua kelompok, lalu menilai "
            "apakah satu kelompok cenderung bernilai lebih tinggi. Uji ini ekuivalen dengan Wilcoxon "
            "rank-sum dan merupakan padanan peringkat dari uji t independen. Karena bekerja pada peringkat, "
            "outlier hanya memengaruhi hasil sebatas posisi peringkatnya.",
        kegunaan=[
            "Alternatif uji t independen untuk data ordinal, skewed, atau sampel kecil.",
            "Membandingkan dua perlakuan ketika asumsi parametrik tidak terpenuhi.",
            "Menganalisis data kuesioner Likert antar dua segmen responden.",
            "Data dengan outlier yang mendistorsi rata-rata aritmetik.",
        ],
        hip=("Dua kelompok berasal dari distribusi yang sama.",
             "Satu kelompok cenderung bernilai lebih besar atau lebih kecil dari kelompok lain."),
        asumsi=[
            "Independensi observasi antar kelompok maupun di dalam kelompok.",
            "Variabel respons minimal berskala ordinal.",
            "Bentuk distribusi kedua kelompok serupa agar tafsiran median valid.",
        ],
        rumus=[
            "U = n₁·n₂ + n₁(n₁+1)/2 − R₁",
            "Ukuran efek r = Z / √N",
        ],
        baca="p < α berarti kedua kelompok berbeda signifikan dalam sebaran peringkat; arah dibaca dari "
             "median masing-masing kelompok. Ukuran efek r = 0.1 kecil, 0.3 sedang, 0.5 besar. Jika "
             "distribusi kedua kelompok bentuknya mirip, perbedaan dapat dilaporkan sebagai perbedaan "
             "median; jika tidak, laporkan sebagai perbedaan sebaran peringkat secara umum.",
        contoh=[
            "Membandingkan tingkat stres dua profesi dari kuesioner skala Likert.",
            "Menguji perbedaan pendapatan dua desa yang distribusinya tidak normal.",
        ],
    ),

    # ------------------------------------------------------------------
    "wilcoxon": dict(
        judul="Wilcoxon Signed-Rank", jenis="Non-Parametrik", jcls="n",
        tujuan="Membandingkan dua pengukuran berpasangan tanpa asumsi normalitas pada selisihnya.",
        apa="Padanan non-parametrik uji t berpasangan: selisih tiap pasangan dihitung, nilai absolutnya "
            "diperingkat, lalu peringkat selisih positif dan negatif masing-masing dijumlahkan. Ketimpangan "
            "besar antara kedua penjumlahan menandakan perubahan sistematis dari kondisi pertama ke "
            "kondisi kedua, dan statistik W mengujinya secara formal.",
        kegunaan=[
            "Alternatif uji t berpasangan saat selisih tidak berdistribusi normal.",
            "Desain pre-post dengan sampel kecil atau data ordinal.",
            "Menguji efek program pada subjek yang sama dengan data skewed.",
            "Perbandingan dua metode pengukuran pada objek yang sama.",
        ],
        hip=("Distribusi selisih simetris di sekitar nol (median selisih = 0).",
             "Median selisih ≠ 0, atau > 0 / < 0 untuk hipotesis satu arah."),
        asumsi=[
            "Pasangan data berasal dari subjek yang sama.",
            "Selisih dapat diperingkat berdasarkan nilai absolutnya.",
            "Distribusi selisih simetris agar tafsiran median valid.",
        ],
        rumus=[
            "W = min(R⁺, R⁻) - jumlah peringkat selisih positif dan negatif",
        ],
        baca="p < α berarti terdapat perubahan signifikan antara pengukuran pertama dan kedua; arah perubahan "
             "dilihat dari median selisih (positif berarti naik). Lengkapi laporan dengan jumlah pasangan "
             "yang naik versus turun dan median selisihnya agar pembaca mendapat gambaran praktis yang utuh.",
        contoh=[
            "Menguji penurunan berat badan sebelum dan sesudah program diet.",
            "Membandingkan tingkat kecemasan siswa sebelum dan sesudah layanan konseling.",
        ],
    ),

    # ------------------------------------------------------------------
    "friedman": dict(
        judul="Friedman", jenis="Non-Parametrik", jcls="n",
        tujuan="Menguji perbedaan tiga kondisi/pengukuran atau lebih yang diterapkan pada subjek yang sama.",
        apa="Friedman adalah padanan non-parametrik ANOVA pengukuran berulang: setiap subjek diperingkat "
            "antar kondisi, lalu statistik χ² Fr menguji apakah rata-rata peringkat antar kondisi berbeda. "
            "Karena tiap subjek menjadi bloknya sendiri, efek individu tereliminasi dan yang diuji murni "
            "perbedaan antar kondisi. Ukuran efek Kendall's W menyatakan konsistensi pemeringkatan.",
        kegunaan=[
            "Eksperimen berulang: setiap responden mencoba semua produk atau kondisi.",
            "Alternatif ANOVA repeated-measures untuk data ordinal atau tidak normal.",
            "Studi preferensi: mengukur konsistensi urutan pilihan antar penilai.",
            "Evaluasi beberapa alat/protokol pada unit yang sama tanpa randomisasi berat.",
        ],
        hip=("Semua kondisi memiliki distribusi yang sama.",
             "Minimal satu kondisi berbeda dari kondisi lainnya."),
        asumsi=[
            "Subjek yang sama terdata pada semua kondisi (desain blok lengkap).",
            "Respons dapat diperingkat di dalam tiap subjek.",
            "Tidak ada interaksi subjek × kondisi yang mengacaukan pola peringkat.",
        ],
        rumus=[
            "χ² Fr = (12 / (n·k(k+1))) · ΣRⱼ² − 3n(k+1)",
            "Kendall's W = χ² Fr / (n(k − 1))",
        ],
        baca="p < α berarti minimal satu kondisi berbeda; bandingkan median antar kondisi untuk melihat arah "
             "perbedaannya. Kendall's W = 0.1 lemah, 0.3 sedang, dan > 0.5 kuat - semakin besar nilainya, "
             "semakin konsisten subjek memeringkat kondisi, sehingga kesimpulan lebih stabil. Untuk uji "
             "lanjutan antar pasangan, gunakan Wilcoxon signed-rank dengan koreksi Bonferroni.",
        contoh=[
            "Menguji preferensi panelis terhadap tiga formulasi rasa roti.",
            "Membandingkan skor kenyamanan tiga kursi yang dicoba oleh responden yang sama.",
        ],
    ),

    # ------------------------------------------------------------------
    "chisq": dict(
        judul="Uji Chi-Square", jenis="Non-Parametrik", jcls="n",
        tujuan="Menguji asosiasi atau hubungan antara dua variabel kategorik melalui tabel kontingensi.",
        apa="Uji independensi chi-square membandingkan frekuensi teramati dengan frekuensi harapan bila kedua "
            "variabel benar-benar saling bebas. Selisih yang besar - dirangkum menjadi statistik χ² - "
            "menandakan pola frekuensi menyimpang dari pola independen, sehingga kedua variabel dinilai "
            "berasosiasi. Kekuatan asosiasi distandarkan lewat Cramér's V; untuk tabel 2×2 aplikasi "
            "otomatis menerapkan koreksi Yates.",
        kegunaan=[
            "Menguji hubungan dua variabel kategorik: gender × preferensi, pendidikan × status kerja.",
            "Menguji kesetaraan proporsi antar kelompok pada data frekuensi.",
            "Analisis silang (crosstab) klasik untuk data survei dan sensus.",
            "Cramér's V menyediakan ukuran kekuatan hubungan yang distandarkan 0-1.",
        ],
        hip=("Dua variabel saling independen - tidak ada asosiasi.",
             "Terdapat asosiasi antara kedua variabel."),
        asumsi=[
            "Data berupa frekuensi (count), bukan persentase atau proporsi.",
            "Kategori saling lepas: setiap observasi hanya masuk satu sel.",
            "Frekuensi harapan minimal 5 pada sekurang-kurangnya 80% sel.",
            "Observasi diambil secara independen.",
        ],
        rumus=[
            "χ² = Σ (O − E)² / E",
            "E = (total baris × total kolom) / total keseluruhan",
            "Cramér's V = √(χ² / (N·(min(r, c) − 1)))",
        ],
        baca="p < α berarti kedua variabel berasosiasi signifikan. Kekuatan asosiasi: V < 0.1 sangat lemah, "
             "0.1-0.3 lemah, 0.3-0.5 sedang, dan > 0.5 kuat. Asosiasi tidak berarti kausalitas - bandingkan "
             "sel teramati dengan sel harapan untuk melihat kategori mana yang berlebih atau berkurang. "
             "Bila banyak frekuensi harapan di bawah 5, gabungkan kategori yang jarang sebelum menyimpulkan.",
        contoh=[
            "Menguji hubungan tingkat pendidikan dengan pilihan media sosial utama.",
            "Menganalisis asosiasi status merokok dengan kategori penyakit kronis.",
        ],
    ),

    # ------------------------------------------------------------------
    "korelasi": dict(
        judul="Analisis Korelasi", jenis="Parametrik / Non-Parametrik", jcls="p",
        tujuan="Mengukur kekuatan dan arah hubungan antar variabel numerik dalam bentuk matriks.",
        apa="Aplikasi menyediakan tiga koefisien: Pearson (hubungan linear untuk data numerik normal), "
            "Spearman ρ (hubungan monotonic berbasis peringkat), dan Kendall τ (peringkat konkordan yang "
            "tahan outlier). Koefisien bernilai −1 hingga +1; p-value menguji apakah korelasi berbeda "
            "signifikan dari nol. Hasil disajikan sebagai matriks korelasi, matriks p-value, dan heatmap.",
        kegunaan=[
            "Menilai arah dan kekuatan hubungan antar pasangan variabel sekaligus.",
            "Menyaring kandidat prediktor sebelum membangun model regresi.",
            "Menguji validitas instrumen: korelasi antar item atau antar skala.",
            "Memilih antara Pearson dan Spearman berdasar normalitas dan pola hubungan.",
        ],
        hip=("Koefisien korelasi populasi = 0 - tidak ada hubungan.",
             "Koefisien korelasi populasi ≠ 0 - terdapat hubungan signifikan."),
        asumsi=[
            "Pearson: hubungan linear, data interval/rasio, mendekati bivariat normal, tanpa outlier ekstrem.",
            "Spearman/Kendall: data minimal ordinal dan hubungannya monotonic.",
            "Observasi saling independen satu sama lain.",
        ],
        rumus=[
            "r = Σ(xᵢ − x̄)(yᵢ − ȳ) / √(Σ(xᵢ − x̄)² · Σ(yᵢ − ȳ)²)",
            "rₛ = 1 − 6Σd² / (n(n² − 1))",
            "r² = koefisien determinasi (proporsi variasi bersama)",
        ],
        baca="Kekuatan hubungan: |r| < 0.2 sangat lemah, 0.2-0.4 lemah, 0.4-0.6 sedang, 0.6-0.8 kuat, dan "
             "> 0.8 sangat kuat; tanda positif/negatif menyatakan arah. Korelasi signifikan belum berarti "
             "sebab-akibat - keduanya bisa dipengaruhi variabel ketiga. r² menyatakan proporsi variasi yang "
             "dibagi bersama, dan heatmap membantu menemukan blok variabel yang saling terkait erat.",
        contoh=[
            "Menganalisis hubungan jam belajar, persentase kehadiran, dan IPK mahasiswa.",
            "Menilai keterkaitan indikator makroekonomi: inflasi, suku bunga, dan pertumbuhan.",
        ],
    ),

    # ------------------------------------------------------------------
    "faktor": dict(
        judul="Analisis Faktor (EFA)", jenis="Multivariat", jcls="m",
        tujuan="Mengidentifikasi struktur faktor laten yang mendasari sekumpulan variabel atau item terukur.",
        apa="Analisis faktor eksploratori mengelompokkan item yang saling berkorelasi ke dalam faktor-faktor "
            "laten. Kelayakan data diuji dengan KMO (sampling adequacy) dan uji sferisitas Bartlett. "
            "Loading menunjukkan kekuatan hubungan item dengan faktor, komunalitas menyatakan proporsi "
            "varians item yang terjelaskan, dan scree plot membantu memilih jumlah faktor yang wajar.",
        kegunaan=[
            "Menguji validitas konstruk: apakah item kuesioner benar membentuk dimensi yang direncanakan.",
            "Mereduksi banyak item menjadi beberapa skor faktor yang lebih ringkas.",
            "Menemukan dimensi laten seperti kecerdasan, kepuasan, atau gaya belajar.",
            "Menyusun dasar teoretis untuk pengembangan instrumen berikutnya.",
        ],
        hip=("Uji Bartlett: matriks korelasi adalah matriks identitas - item tidak saling berkorelasi sehingga EFA tidak layak.",
             "Uji Bartlett ditolak - terdapat korelasi antar item sehingga struktur faktor layak dieksplorasi."),
        asumsi=[
            "KMO ≥ 0.6 menandakan kecukupan sampel untuk analisis faktor.",
            "Uji Bartlett signifikan (p < α).",
            "Item numerik dengan korelasi antar item memadai.",
            "Jumlah observasi minimal 5× jumlah item (idealnya 10×).",
        ],
        rumus=[
            "X = ΛF + ε (item sebagai fungsi faktor + galat unik)",
            "Komunalitas h² = Σ loading²",
        ],
        baca="Periksa KMO dan Bartlett terlebih dahulu - bila gagal, hentikan dan perbaiki instrumen. Baca "
             "loading ≥ 0.5 sebagai indikator item mewakili faktornya. Varians kumulatif ≥ 60% umumnya "
             "dianggap memadai, dan titik elbow pada scree plot membantu menetapkan jumlah faktor. Rotasi "
             "varimax memudahkan penamaan faktor berdasarkan item yang loadingnya tinggi.",
        contoh=[
            "Menvalidasi 20 item kuesioner kepuasan pelanggan menjadi tiga faktor utama.",
            "Mengidentifikasi dimensi gaya belajar dari 15 pernyataan skala Likert.",
        ],
    ),

    # ------------------------------------------------------------------
    "pca": dict(
        judul="Analisis Komponen Utama (PCA)", jenis="Multivariat", jcls="m",
        tujuan="Mereduksi banyak variabel numerik yang berkorelasi menjadi sedikit komponen utama yang saling bebas.",
        apa="PCA membentuk kombinasi linear baru (PC) yang menangkap varians terbesar secara berturut-turut: "
            "PC1 memuat varians terbesar, PC2 berikutnya, dan seterusnya, dengan semua komponen saling tegak "
            "lurus. Berbeda dari EFA, PCA tidak memodelkan faktor laten - ini transformasi matematis untuk "
            "kompresi informasi, sehingga tidak ada hipotesis formal yang diuji.",
        kegunaan=[
            "Mereduksi dimensi data numerik besar tanpa banyak kehilangan informasi.",
            "Mengatasi multikolinearitas karena komponen yang dihasilkan saling bebas.",
            "Memvisualisasikan data berdimensi tinggi lewat biplot PC1-PC2.",
            "Pra-pemrosesan fitur untuk model machine learning berikutnya.",
        ],
        hip=None,
        asumsi=[
            "Variabel numerik dengan skala sebanding - standarisasi sangat penting.",
            "Terdapat korelasi antar variabel; jika semua saling bebas, PCA tidak bermakna.",
            "PCA sensitif terhadap outlier - bersihkan data terlebih dahulu.",
        ],
        rumus=[
            "PCⱼ = a₁X₁ + a₂X₂ + … + aₖXₖ",
            "Proporsi varians = eigenvalueⱼ / Σ eigenvalue",
        ],
        baca="Perhatikan proporsi varians kumulatif - memilih komponen hingga menjelaskan ≥ 80% variasi adalah "
             "praktik yang umum. Scree plot membantu menemukan titik elbow sebagai batas komponen yang "
             "dipertahankan. Loading tiap PC menunjukkan variabel yang dominan pada komponen tersebut, dan "
             "biplot memperlihatkan posisi observasi sekaligus arah korelasi variabel dalam satu gambar.",
        contoh=[
            "Mereduksi 12 indikator kinerja UMKM menjadi tiga komponen utama.",
            "Memvisualisasikan pola data sensor dengan biplot PC1-PC2.",
        ],
    ),

    # ------------------------------------------------------------------
    "lda": dict(
        judul="Analisis Diskriminan (LDA)", jenis="Parametrik (Klasifikasi)", jcls="m",
        tujuan="Mengklasifikasikan observasi ke dalam kelompok yang sudah diketahui berdasarkan kombinasi linear variabel prediktor.",
        apa="LDA mencari fungsi diskriminan yang memaksimalkan rasio variansi antar kelompok terhadap variansi "
            "dalam kelompok, lalu menggunakan fungsi tersebut sebagai aturan klasifikasi untuk data baru. "
            "Aplikasi menyajikan fungsi diskriminan, matriks konfusi, akurasi keseluruhan, dan cross-validation "
            "untuk menilai kemampuan generalisasi model.",
        kegunaan=[
            "Mengklasifikasikan unit baru ke kelompok: penerima bantuan vs bukan, sehat vs sakit.",
            "Menguji seberapa baik sekumpulan variabel numerik memisahkan kelompok kategorik.",
            "Membandingkan performa dengan regresi logistik pada klasifikasi multi-kelas.",
            "Mengidentifikasi variabel yang paling berkontribusi pada pemisahan kelompok.",
        ],
        hip=("Vektor rata-rata kelompok sama - kelompok tidak dapat dipisahkan.",
             "Terdapat perbedaan vektor rata-rata - kelompok dapat dipisahkan."),
        asumsi=[
            "Normalitas multivariat per kelompok.",
            "Homogenitas matriks kovarians antar kelompok.",
            "Tidak ada multikolinearitas berat antar prediktor.",
            "Variabel dependen kategorik dengan kelompok terdefinisi baik.",
        ],
        rumus=[
            "D(x) = xᵀΣ⁻¹μⱼ − ½μⱼᵀΣ⁻¹μⱼ + ln πⱼ",
        ],
        baca="Akurasi keseluruhan yang tinggi menandakan prediktor memisahkan kelompok dengan baik; bandingkan "
             "dengan baseline proporsi kelas mayoritas agar penilaian jujur. Bila akurasi cross-validation "
             "jauh lebih rendah dari akurasi training, model overfitting. Matriks konfusi memperlihatkan "
             "kelas mana yang sering tertukar - informasi penting untuk perbaikan model atau pengumpulan "
             "prediktor tambahan.",
        contoh=[
            "Mengklasifikasikan nasabah berpotensi gagal bayar berdasarkan indikator keuangan.",
            "Memilah spesimen bunga ke dalam spesies dari empat pengukuran morfologi.",
        ],
    ),

    # ------------------------------------------------------------------
    "kmeans": dict(
        judul="K-Means Clustering", jenis="Pembelajaran Tak Terawasi", jcls="m",
        tujuan="Mengelompokkan data menjadi k kelompok berdasarkan kemiripan karakteristik tanpa label awal.",
        apa="K-Means membagi data ke k cluster sehingga variansi di dalam cluster minimum: tiap titik "
            "ditugaskan ke centroid terdekat, centroid diperbarui, dan iterasi berlanjut hingga konvergen. "
            "Jumlah k dipilih lewat elbow method pada kurva inertia, dan kualitas pengelompokan dinilai "
            "silhouette score yang berkisar −1 hingga 1. Seperti PCA, analisis ini eksploratif tanpa "
            "hipotesis formal.",
        kegunaan=[
            "Segmentasi pasar atau profil responden tanpa label kategori yang sudah ada.",
            "Menemukan pola pengelompokan alami dalam data multidimensi.",
            "Membuat penanda kelompok sebagai pra-pemrosesan untuk analisis lanjutan.",
            "Penargetan program: mengelompokkan wilayah/instansi berdasar indikator.",
        ],
        hip=None,
        asumsi=[
            "Variabel numerik, idealnya distandarisasi agar skala setara.",
            "Jumlah k ditentukan peneliti - bantu dengan elbow dan silhouette.",
            "Cluster diasumsikan berbentuk bulat dan berukuran serupa (sensitif terhadap outlier).",
        ],
        rumus=[
            "Inertia = Σ Σ ‖xᵢ − cⱼ‖² (jarak kuadrat ke centroid)",
            "Silhouette = (b − a) / max(a, b)",
        ],
        baca="Pilih k pada titik elbow - tempat penurunan inertia mulai melandai - dengan silhouette idealnya "
             "≥ 0.5. Profilkan tiap cluster lewat rata-rata variabelnya lalu beri label bermakna (misal "
             "'pelanggan royal namun hemat'). Hasil clustering sangat bergantung pada skala variabel, jadi "
             "pastikan standarisasi digunakan bila satuan pengukurannya berbeda-beda.",
        contoh=[
            "Mensegmentasikan pelanggan berdasarkan frekuensi belanja, nilai transaksi, dan recency.",
            "Mengelompokkan desa berdasarkan indikator kemiskinan untuk penargetan program bantuan.",
        ],
    ),
}
