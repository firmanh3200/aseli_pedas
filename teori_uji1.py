# -*- coding: utf-8 -*-
"""
AseliPedas - Data Teori Uji (Bagian 1)
===================================
Kelompok Regresi & Model Terkait (5) + ANOVA & Kovarians (4).
Struktur entri: judul, jenis, jcls (p=parametrik, n=non-parametrik, m=multivariat),
tujuan, apa, kegunaan[], hip(H0,H1)|None, asumsi[], rumus[], baca, contoh[].
"""

TEORI_A = {

    # ------------------------------------------------------------------
    "ols": dict(
        judul="Regresi Linear (OLS)", jenis="Parametrik", jcls="p",
        tujuan="Mengukur pengaruh satu atau lebih variabel independen (X) terhadap variabel dependen numerik (Y) sekaligus memprediksi nilai Y.",
        apa="Regresi linear dengan metode kuadrat terkecil (Ordinary Least Squares) mencari persamaan "
            "Ŷ = b₀ + b₁X₁ + … + bₖXₖ yang meminimalkan jumlah kuadrat residual. Model ini menjawab dua "
            "pertanyaan sekaligus: variabel mana yang berpengaruh (uji t per koefisien) dan seberapa "
            "baik model menjelaskan data (R² serta uji F). Diagnostik asumsi klasik - normalitas, "
            "homoskedastisitas, independensi residual, dan VIF - tersedia di aplikasi agar "
            "kesimpulan tidak menyesatkan.",
        kegunaan=[
            "Menguji hipotesis pengaruh variabel bebas terhadap variabel terikat melalui uji t dan uji F.",
            "Memprediksi nilai Y untuk kombinasi nilai X tertentu di dalam rentang data (interpolasi).",
            "Mengukur besar perubahan Y setiap kali satu X naik satu unit dengan variabel lain tetap.",
            "Menilai proporsi variasi Y yang mampu dijelaskan model melalui R² dan R² terkoreksi.",
            "Mendeteksi multikolinearitas antar prediktor melalui VIF sebelum menafsirkan koefisien.",
        ],
        hip=("Semua koefisien slope = 0 - tidak ada X yang berpengaruh signifikan terhadap Y (model tidak layak).",
             "Minimal satu koefisien slope ≠ 0 - model layak dan setidaknya satu prediktor berpengaruh."),
        asumsi=[
            "Hubungan antara X dan Y bersifat linear.",
            "Residual berdistribusi normal (uji Jarque-Bera).",
            "Homoskedastisitas: variansi residual konstan (uji Breusch-Pagan).",
            "Residual saling independen (uji Durbin-Watson).",
            "Tidak ada multikolinearitas berat (VIF < 10).",
        ],
        rumus=[
            "Ŷ = b₀ + b₁X₁ + b₂X₂ + … + bₖXₖ",
            "R² = 1 − (Jumlah Kuadrat Residual / Total Kuadrat)",
            "t = bⱼ / SE(bⱼ)",
        ],
        baca="Uji F yang signifikan (p < α) berarti model secara keseluruhan layak digunakan. Perhatikan "
             "p-value tiap koefisien: bⱼ yang signifikan menandakan Xⱼ berpengaruh riil, dan tanda "
             "positif/negatif menunjukkan arah pengaruhnya. R² = 0.62 berarti 62% variasi Y terjelaskan "
             "model, sisanya faktor di luar model. Selalu periksa diagnostik asumsi sebelum menafsirkan "
             "dan hindari ekstrapolasi ke luar rentang data.",
        contoh=[
            "Memprediksi nilai ujian akhir berdasarkan jam belajar, kehadiran, dan nilai tugas mahasiswa.",
            "Menganalisis pengaruh luas lahan, jumlah pupuk, dan curah hujan terhadap hasil panen padi.",
        ],
    ),

    # ------------------------------------------------------------------
    "logit": dict(
        judul="Regresi Logistik Biner", jenis="Parametrik (GLM)", jcls="p",
        tujuan="Mengmodelkan peluang suatu kejadian biner (ya/tidak) berdasarkan satu atau lebih variabel prediktor.",
        apa="Regresi logistik memodelkan logit - log-odds - peluang Y = 1 sebagai fungsi linear prediktor, "
            "sehingga prediksi selalu berada di rentang 0-1. Koefisien dieksponensiasi menjadi odds ratio "
            "(OR = e^b): berapa kali odds kejadian berlipat untuk setiap kenaikan satu unit X. Aplikasi "
            "menyajikan koefisien, OR, signifikansi, evaluasi model (LLR, pseudo R²), serta matriks "
            "konfusi dengan akurasi klasifikasi.",
        kegunaan=[
            "Memprediksi kejadian biner: lulus/tidak, membeli/tidak, positif/negatif penyakit.",
            "Mengukur pengaruh prediktor terhadap peluang kejadian melalui odds ratio.",
            "Menyaring faktor risiko dominan pada penelitian kesehatan, sosial, dan ekonomi.",
            "Membangun model klasifikasi sederhana yang akurasinya dapat diuji lewat matriks konfusi.",
        ],
        hip=("Semua koefisien = 0 - prediktor tidak memengaruhi peluang kejadian.",
             "Minimal satu koefisien ≠ 0 - ada prediktor yang berpengaruh signifikan."),
        asumsi=[
            "Variabel dependen berskala biner (dua kategori).",
            "Observasi saling independen satu sama lain.",
            "Tidak ada multikolinearitas berat antar prediktor.",
            "Hubungan logit-linear dengan prediktor kontinu.",
            "Jumlah kejadian minimum memadai (±10 per prediktor).",
        ],
        rumus=[
            "ln(p / (1 − p)) = b₀ + b₁X₁ + … + bₖXₖ",
            "Odds Ratio = e^(bⱼ)",
            "p = 1 / (1 + e^−z)",
        ],
        baca="OR > 1 berarti X menaikkan peluang kejadian, OR < 1 menurunkan, OR = 1 berarti tanpa pengaruh. "
             "OR = 2.5 dibaca: setiap kenaikan satu unit X melipatgandakan odds kejadian 2.5 kali. "
             "Koefisien signifikan (p < α) menandakan pengaruh riil. Gunakan akurasi matriks konfusi untuk "
             "menilai kemampuan klasifikasi model - model bisa signifikan namun akurasinya biasa-biasa saja "
             "bila kelas sangat timpang.",
        contoh=[
            "Memodelkan peluang mahasiswa lulus tepat waktu berdasarkan IPK, kehadiran, dan keaktifan organisasi.",
            "Menganalisis faktor risiko hipertensi: merokok, umur, dan indeks massa tubuh.",
        ],
    ),

    # ------------------------------------------------------------------
    "mnlogit": dict(
        judul="Regresi Logistik Multinomial", jenis="Parametrik (GLM)", jcls="p",
        tujuan="Memprediksi variabel dependen kategorik dengan lebih dari dua kategori yang tidak berurutan.",
        apa="Perluasan regresi logistik biner untuk Y multikategori. Satu kategori ditetapkan sebagai acuan "
            "(baseline), lalu model membangun satu persamaan logit untuk membandingkan tiap kategori lain "
            "terhadap acuan tersebut. Hasil utamanya berupa relative risk ratio (RRR = e^b) per kategori, "
            "sehingga setiap prediktor bisa punya efek berbeda untuk tiap pilihan.",
        kegunaan=[
            "Memprediksi pilihan di antara lebih dari dua kategori tak berurutan: merek, jurusan, moda transportasi.",
            "Mengidentifikasi faktor-faktor yang membedakan tiap kategori dari kategori acuan.",
            "Menilai probabilitas keanggotaan tiap kategori untuk unit baru (profil klasifikasi).",
            "Membandingkan perilaku pilihan antar segmen responden.",
        ],
        hip=("Semua koefisien = 0 - prediktor tidak membedakan kategori-kategori Y.",
             "Minimal satu koefisien ≠ 0 - ada prediktor yang membedakan kategori."),
        asumsi=[
            "Y berskala nominal dengan 2-10 kategori.",
            "Independensi antar observasi.",
            "Tidak ada separasi sempurna (kategori terpisah penuh) pada prediktor.",
            "Tidak ada multikolinearitas berat antar prediktor.",
        ],
        rumus=[
            "ln(P(Y = j) / P(Y = acuan)) = b₀ⱼ + b₁ⱼX₁ + … + bₖⱼXₖ",
            "Relative Risk Ratio = e^(bⱼₖ)",
        ],
        baca="Tafsirkan tiap persamaan relatif terhadap kategori acuan: RRR = 3.2 untuk kategori 'menggunakan "
             "motor' berarti kenaikan satu unit X melipatgandakan risiko relatif memilih motor dibanding "
             "kategori acuan sebesar 3.2 kali. Perhatikan p-value per koefisien per kategori, karena satu "
             "prediktor bisa signifikan untuk satu kategori tetapi tidak untuk kategori lainnya.",
        contoh=[
            "Menganalisis faktor yang memengaruhi pilihan moda harian: motor, mobil, atau KRL.",
            "Memodelkan pemilihan jurusan siswa SMA: IPA, IPS, atau Bahasa dan Budaya.",
        ],
    ),

    # ------------------------------------------------------------------
    "ordinal": dict(
        judul="Regresi Ordinal", jenis="Parametrik (GLM)", jcls="p",
        tujuan="Memprediksi variabel dependen bertingkat (ordinal) - kategori berurutan seperti skala Likert.",
        apa="Logit ordinal (proportional-odds model) memodelkan peluang Y berada pada level tertentu atau di "
            "bawahnya menggunakan sekumpulan threshold antar tingkatan. Satu set koefisien menggambarkan "
            "pengaruh prediktor terhadap peluang naiknya tingkatan Y, dengan asumsi pengaruh itu konsisten "
            "di semua ambang (proportional odds).",
        kegunaan=[
            "Menganalisis jawaban bertingkat: sangat tidak setuju hingga sangat setuju.",
            "Menguji pengaruh perlakuan terhadap tingkat kepuasan, kategori performa, atau derajat kesepakatan.",
            "Memprediksi kategori tingkatan untuk observasi baru.",
            "Alternatif regresi linear saat Y Likert tidak layak diperlakukan kontinu.",
        ],
        hip=("Semua koefisien = 0 - prediktor tidak memengaruhi tingkatan Y.",
             "Minimal satu koefisien ≠ 0 - ada prediktor yang menggeser tingkatan Y."),
        asumsi=[
            "Y berskala ordinal dengan minimal tiga tingkatan.",
            "Proportional odds: pengaruh prediktor sama di semua threshold.",
            "Tidak ada multikolinearitas berat antar prediktor.",
            "Jumlah observasi di tiap tingkatan memadai.",
        ],
        rumus=[
            "logit(P(Y ≤ j)) = θⱼ − (b₁X₁ + … + bₖXₖ)",
        ],
        baca="Koefisien positif berarti kenaikan X meningkatkan peluang Y berada pada kategori lebih tinggi; "
             "negatif berarti sebaliknya. Uji proportional odds yang dilanggar menandakan interpretasi "
             "global kurang tepat - pertimbangkan model multinomial atau kategori yang digabung. Fokuskan "
             "tafsiran pada arah dan signifikansi koefisien, bukan besaran angkanya semata.",
        contoh=[
            "Menguji pengaruh pelatihan terhadap tingkat kepercayaan diri siswa: rendah, sedang, tinggi.",
            "Menganalisis faktor yang memengaruhi tingkat kepuasan pelanggan pada skala 1-5.",
        ],
    ),

    # ------------------------------------------------------------------
    "poisson": dict(
        judul="Regresi Poisson", jenis="Parametrik (GLM)", jcls="p",
        tujuan="Memprediksi variabel dependen berupa data hitungan (0, 1, 2, ...) dari sekumpulan prediktor.",
        apa="GLM dengan fungsi link log untuk Y berdistribusi Poisson - lazim untuk jumlah kejadian dalam "
            "satuan waktu atau ruang. Koefisien dieksponensiasi menjadi incidence rate ratio (IRR): rasio "
            "perubahan rata-rata jumlah kejadian per satu unit kenaikan X. Aplikasi menampilkan koefisien, "
            "IRR, signifikansi, serta indikasi overdispersion sebagai peringatan kesesuaian model.",
        kegunaan=[
            "Memodelkan jumlah kejadian: kunjungan, kecelakaan, keluhan, absensi.",
            "Mengukur faktor yang menaikkan atau menurunkan laju kejadian melalui IRR.",
            "Memprediksi jumlah kejadian untuk kombinasi kondisi tertentu.",
            "Alternatif regresi linear saat Y berupa hitungan dengan banyak nilai nol kecil.",
        ],
        hip=("Semua koefisien = 0 - prediktor tidak memengaruhi laju kejadian.",
             "Minimal satu koefisien ≠ 0 - ada prediktor yang memengaruhi laju kejadian."),
        asumsi=[
            "Y berupa bilangan bulat non-negatif (hasil hitungan).",
            "Rata-rata mendekati variansi (equidispersion).",
            "Jika variansi jauh melebihi rata-rata, terjadi overdispersion - pertimbangkan negative binomial.",
            "Kejadian antar observasi saling independen.",
        ],
        rumus=[
            "ln(μ) = b₀ + b₁X₁ + … + bₖXₖ",
            "IRR = e^(bⱼ)",
        ],
        baca="IRR = 1.8 dibaca: rata-rata jumlah kejadian naik 80% untuk setiap kenaikan satu unit X; IRR < 1 "
             "berarti penurunan. Periksa signifikansi tiap koefisien beserta indikasi overdispersion - "
             "deviance atau Pearson chi² yang jauh melebihi derajat bebas menandakan model Poisson murni "
             "kurang cocok dan estimasi galat bisa terlalu kecil.",
        contoh=[
            "Memodelkan jumlah absensi siswa berdasarkan jarak rumah dan metode belajar.",
            "Menganalisis jumlah klaim asuransi per klien menurut umur dan jenis kendaraan.",
        ],
    ),

    # ------------------------------------------------------------------
    "anova1": dict(
        judul="ANOVA Satu Arah", jenis="Parametrik", jcls="p",
        tujuan="Membandingkan rata-rata dua kelompok atau lebih sekaligus dalam satu uji yang konsisten.",
        apa="ANOVA memecah variasi total data menjadi variasi antar kelompok (efek faktor) dan variasi dalam "
            "kelompok (galat). Statistik F adalah rasio keduanya - F yang besar berarti perbedaan antar "
            "rata-rata kelompok jauh melampaui sebaran di dalam kelompok sehingga kecil kemungkinan muncul "
            "karena kebetulan. Aplikasi melengkapi hasil dengan uji Levene, eta squared, dan post-hoc Tukey "
            "HSD untuk mengungkap pasangan kelompok yang berbeda.",
        kegunaan=[
            "Menguji perbedaan rata-rata beberapa perlakuan sekaligus tanpa inflasi kesalahan Tipe I dari uji-t berulang.",
            "Mengevaluasi efektivitas beberapa metode pembelajaran, pupuk, atau obat dalam satu eksperimen.",
            "Menilai pengaruh satu faktor berlevel ganda terhadap respons numerik.",
            "Post-hoc Tukey HSD menunjukkan pasangan kelompok mana yang berbeda signifikan.",
            "Eta squared mengukur besarnya kontribusi faktor terhadap variasi data.",
        ],
        hip=("Semua rata-rata kelompok sama (μ₁ = μ₂ = … = μₖ).",
             "Minimal ada satu rata-rata kelompok yang berbeda."),
        asumsi=[
            "Observasi independen antar kelompok.",
            "Residual mendekati distribusi normal.",
            "Homogenitas variansi antar kelompok (uji Levene, p > α).",
            "Data berskala interval atau rasio.",
        ],
        rumus=[
            "F = MS Antar Kelompok / MS Dalam Kelompok",
            "η² = SS Antar Kelompok / SS Total",
            "Tukey HSD: selisih minimum yang signifikan antar pasangan rata-rata",
        ],
        baca="H₀ ditolak (p < α) berarti minimal ada satu pasang kelompok yang berbeda - tetapi ANOVA tidak "
             "menyebutkan pasangan mana; baca tabel Tukey HSD untuk melihat pasangan yang berbeda signifikan "
             "beserta arah selisihnya. Jika uji Levene signifikan (variansi tidak homogen), pertimbangkan "
             "Kruskal-Wallis sebagai alternatif. Eta squared < 0.06 tergolong kecil, 0.06-0.14 sedang, "
             "dan > 0.14 besar.",
        contoh=[
            "Membandingkan hasil belajar tiga kelas dengan metode berbeda: ceramah, diskusi, dan proyek.",
            "Menguji perbedaan produksi padi di bawah empat jenis pupuk.",
        ],
    ),

    # ------------------------------------------------------------------
    "anova2": dict(
        judul="ANOVA Dua Arah", jenis="Parametrik", jcls="p",
        tujuan="Menguji pengaruh dua faktor sekaligus - beserta interaksinya - terhadap satu variabel respons numerik.",
        apa="ANOVA dua arah memecah variasi menjadi efek faktor A, efek faktor B, dan interaksi A×B (bila "
            "diaktifkan). Interaksi yang signifikan berarti efek satu faktor bergantung pada level faktor "
            "lainnya - informasi penting yang tidak akan tampak dari dua ANOVA satu arah terpisah. Aplikasi "
            "menyajikan tabel ANOVA lengkap, uji Levene, dan plot interaksi.",
        kegunaan=[
            "Menguji dua faktor eksperimen sekaligus - lebih efisien daripada dua eksperimen terpisah.",
            "Mendeteksi interaksi: misalnya efek metode belajar berbeda antara kelompok pria dan wanita.",
            "Mengendalikan faktor kedua agar estimasi efek faktor pertama lebih bersih.",
            "Membandingkan kombinasi level terbaik untuk keputusan praktis (sel mana yang optimal).",
        ],
        hip=("Semua rata-rata sama antar level faktor A, antar level faktor B, dan tidak ada interaksi A×B.",
             "Minimal ada satu efek (A, B, atau interaksi A×B) yang signifikan."),
        asumsi=[
            "Independensi observasi, normalitas residual, dan homogenitas variansi.",
            "Setiap kombinasi sel A×B memiliki minimal satu observasi (idealnya desain seimbang).",
            "Tidak ada covariat lain yang belum dikontrol (gunakan ANCOVA bila ada).",
        ],
        rumus=[
            "F_A = MS Faktor A / MS Galat",
            "F_B = MS Faktor B / MS Galat",
            "F_AB = MS Interaksi A×B / MS Galat",
        ],
        baca="Baca interaksi terlebih dahulu: jika A×B signifikan, efek utama tidak boleh ditafsirkan "
             "sendiri-sendiri - gunakan plot interaksi atau tabel rata-rata per sel untuk melihat pola "
             "gabungannya. Jika interaksi tidak signifikan, tafsirkan efek utama masing-masing faktor dari "
             "tabel ANOVA seperti biasa.",
        contoh=[
            "Menguji efek metode belajar (tiga level) dan jenis kelamin terhadap nilai ujian.",
            "Menganalisis pengaruh jenis pupuk dan kepadatan tanam terhadap hasil panen.",
        ],
    ),

    # ------------------------------------------------------------------
    "ancova": dict(
        judul="ANCOVA", jenis="Parametrik", jcls="p",
        tujuan="Membandingkan rata-rata kelompok sambil mengontrol pengaruh satu variabel numerik lain (covariat).",
        apa="ANCOVA adalah kombinasi ANOVA dan regresi: covariat (misalnya nilai pre-test) dimasukkan sebagai "
            "pengendali sehingga perbandingan antar kelompok menjadi lebih adil dan presisi. Dengan menyertakan "
            "variasi covariat dalam model, variansi galat mengecil dan uji beda kelompok menjadi lebih "
            "sensitif terhadap efek yang benar-benar ada.",
        kegunaan=[
            "Menguji efek perlakuan dengan mengontrol nilai awal (pre-test) pada desain quasi-eksperimen.",
            "Menurunkan variansi galat sehingga uji perbedaan kelompok menjadi lebih sensitif.",
            "Menyetarakan kelompok yang tidak dapat dirandomisasi sempurna.",
            "Menilai apakah perbedaan kelompok bertahan setelah pengaruh covariat dieliminasi.",
        ],
        hip=("Rata-rata antar kelompok sama setelah efek covariat dikontrol (dan slope covariat homogen).",
             "Minimal ada satu perbedaan kelompok yang signifikan setelah kontrol covariat."),
        asumsi=[
            "Asumsi ANOVA satu arah berlaku (independensi, normalitas, homogenitas variansi).",
            "Hubungan antara covariat dan Y bersifat linear.",
            "Homogenitas slope: efek covariat sama di semua kelompok.",
            "Covariat diukur sebelum perlakuan dan tidak terpengaruh perlakuan.",
        ],
        rumus=[
            "Y = μ + efek kelompok + b·(covariat) + galat",
            "F kelompok = MS Kelompok / MS Galat (terkoreksi covariat)",
        ],
        baca="Uji F kelompok menilai perbedaan adjusted mean - rata-rata yang telah disesuaikan posisi "
             "covariatnya. Bila signifikan, bandingkan adjusted mean antar kelompok untuk melihat urutan "
             "efektivitas. Pastikan asumsi homogenitas slope terpenuhi; jika dilanggar, hasil ANCOVA tidak "
             "valid dan model interaksi perlu dipertimbangkan.",
        contoh=[
            "Membandingkan efektivitas dua metode remedial dengan mengontrol nilai awal siswa.",
            "Menguji program gizi terhadap berat badan bayi dengan mengontrol berat lahir.",
        ],
    ),

    # ------------------------------------------------------------------
    "manova": dict(
        judul="MANOVA", jenis="Parametrik", jcls="p",
        tujuan="Menguji perbedaan antar kelompok terhadap dua atau lebih variabel dependen sekaligus.",
        apa="MANOVA menggabungkan beberapa variabel dependen numerik menjadi kombinasi linear (variat) yang "
            "memaksimalkan pemisahan antar kelompok. Empat statistik multivariat dikeluarkan: Pillai's "
            "Trace, Wilks' Lambda, Hotelling's Trace, dan Roy's Largest Root - semuanya menghasilkan uji F "
            "dengan p-value yang lazimnya konsisten satu sama lain.",
        kegunaan=[
            "Menguji efek perlakuan terhadap beberapa luaran terkait sekaligus (mis. nilai matematika dan verbal).",
            "Mengendalikan inflasi kesalahan Tipe I yang akan membengkak jika tiap Y diuji ANOVA terpisah.",
            "Menangkap struktur korelasi antar variabel dependen yang dilewatkan uji univariat.",
            "Titik awal analisis profil: memutuskan perlunya uji follow-up per variabel.",
        ],
        hip=("Vektor rata-rata semua kelompok sama - tidak ada perbedaan secara gabungan.",
             "Minimal ada perbedaan vektor rata-rata antar kelompok."),
        asumsi=[
            "Observasi saling independen.",
            "Normalitas multivariat pada tiap kelompok.",
            "Homogenitas matriks kovarians antar kelompok.",
            "Tidak ada outlier multivariat yang ekstrem.",
        ],
        rumus=[
            "Wilks' Λ = det(W) / det(W + B)",
            "Pillai's Trace = trace[B (W + B)⁻¹]",
        ],
        baca="P-value signifikan (semua statistik < α) berarti kelompok berbeda secara gabungan; Pillai's "
             "Trace paling robust terhadap pelanggaran asumsi sehingga layak dijadikan acuan utama. Untuk "
             "mengetahui variabel mana yang benar-benar membedakan kelompok, lanjutkan dengan ANOVA "
             "terpisah per variabel sebagai uji follow-up dan bandingkan pola rata-ratanya.",
        contoh=[
            "Membandingkan lulusan dua kurikulum pada nilai matematika, bahasa, dan sains sekaligus.",
            "Menguji efek program latihan terhadap kekuatan, daya tahan, dan kelenturan atlet.",
        ],
    ),
}
