==========================================================
  AseliPedas - APLIKASI PENGOLAH STATISTIK (FastHTML)
  Panduan Singkat Penggunaan
==========================================================

CARA PALING MUDAH (Windows)
---------------------------
1. Klik dua kali file:  jalankan.bat
2. Tunggu pemeriksaan selesai:
   - Langkah 1: Python dipasang otomatis bila belum ada.
   - Langkah 2: Modul Python dipasang otomatis bila belum lengkap
     (butuh koneksi internet, hanya sekali di awal).
   - Langkah 3: Aplikasi berjalan dan browser terbuka otomatis di:
       http://localhost:3000
3. Untuk menghentikan: tekan Ctrl+C di jendela aplikasi, lalu tutup.

CARA MANUAL (semua sistem operasi)
----------------------------------
1. Pastikan Python 3.10+ terpasang.
2. Di folder aplikasi, jalankan:
      pip install -r requirements.txt
3. Jalankan aplikasi:
      python app.py
4. Buka http://localhost:3000 di browser.

ISI APLIKASI (5 HALAMAN)
------------------------
1. Statistik Dasar   - unggah data, pratinjau, 13 metrik statistik,
                       detail per kolom + histogram, statistik kategorik.
2. Statistik Inferens - 20 analisis inferensial (regresi OLS/logistik/
                       ordinal/Poisson, ANOVA 1-2 arah, ANCOVA, MANOVA,
                       uji t, chi-square, korelasi, faktor, PCA,
                       diskriminan, K-Means) lengkap dengan narasi
                       analisis otomatis.
3. Non Parametrik    - 12 uji non-parametrik (Shapiro-Wilk, Kolmogorov-
                       Smirnov, Levene, Mann-Whitney, Wilcoxon, Kruskal-
                       Wallis, Friedman, Chi-Square GOF, McNemar, Runs,
                       Spearman, Kendall) + penjelasan kegunaan dan
                       contoh penerapan sehari-hari tiap uji.
4. Bandingkan File   - membandingkan baris data di antara 2 file
                       (kolom kunci multi-kolom, nilai dinormalisasi,
                       hasil terurut, unduh Excel 2 sheet).
5. Teori Uji         - datatable teori seluruh uji (pencarian instan,
                       filter, sorting, pagination, detail per baris).

FORMAT DATA YANG DIDUKUNG
-------------------------
Excel (.xlsx/.xlsm/.xls), CSV, TXT, TSV, DBF, SPSS (.sav/.zsav),
SQL dump (.sql), Access (.mdb/.accdb), Parquet, Stata (.dta),
SAS (.sas7bdat/.xpt), JSON, Pickle (.pkl).

FILE PENTING
------------
- jalankan.bat        : penghidup otomatis (cek Python, cek modul, jalankan).
- requirements.txt    : daftar modul Python yang dibutuhkan.
- PANDUAN_ADMIN.md    : panduan lengkap bagi admin yang ingin MENGUBAH
                        KODE secara manual (menambah uji, mengubah
                        tampilan, menambah halaman, dll).
- contoh_data/        : berkas contoh untuk mencoba tiap halaman.
- app.py              : aplikasi utama (halaman Statistik Dasar + perekat
                        seluruh halaman).
- inferens.py / nonparam.py / komparasi.py / teori.py
                      : modul halaman Statistik Inferens, Non Parametrik,
                        Bandingkan File, dan Teori Uji.
- narasi.py / narasi_np.py
                      : generator narasi analisis otomatis (bahasa Indonesia).
- app.css / js/ / vendor/ : tampilan dan interaksi sisi browser.

CATATAN
-------
- Seluruh data diproses LOKAL di komputer Anda; tidak ada data yang
  dikirim ke internet.
- Instalasi pertama butuh koneksi internet (unduh modul Python dan font).
- Jika port 3000 sedang dipakai aplikasi lain, aplikasi otomatis pindah
  ke port berikutnya (3001, 3002, ...). Bisa juga dipaksa dengan:
      set PORT=8080  lalu  python app.py
