# Data Source & Provenance

## File sumber

- Nama: HR_Analytics_Encoded.csv
- Salinan yang digunakan: [HR_Analytics_Encoded.csv dari apoorva2796/DataSet](https://github.com/apoorva2796/DataSet/blob/master/HR_Analytics_Encoded.csv)
- Dataset upstream: [IBM/employee-attrition-aif360](https://github.com/IBM/employee-attrition-aif360), dataset IBM HR Analytics Employee Attrition & Performance yang didistribusikan melalui Kaggle.
- Tanggal akses: 20 November 2026
- Penggunaan dalam proyek: analisis deskriptif Work-Life Balance, overtime, kepuasan kerja, demografi, dan attrition
- Atribusi singkat: “IBM HR Analytics Employee Attrition & Performance (ODbL 1.0 / DbCL 1.0), file encoded dari apoorva2796/DataSet. Cleaning dan analisis oleh Eriel Setiawan Dewantoro.”

## Hak penggunaan

Repositori IBM menyatakan dataset upstream tersedia dengan Open Database License (ODbL) 1.0 untuk database dan Database Contents License (DbCL) 1.0 untuk isi data. Tautan file encoded yang digunakan di proyek ini berasal dari repositori apoorva2796/DataSet, sehingga atribusi mencantumkan sumber upstream IBM dan lokasi salinan encoded.

Lisensi dan pemberitahuan:

1. Sertakan pemberitahuan sumber ini saat mendistribusikan data mentah, data turunan, dashboard, atau visualisasi.
2. Dataset turunan yang dipublikasikan perlu mengikuti persyaratan share-alike ODbL atau lisensi kompatibel.
3. README ini menyediakan tautan URI lisensi bersama dataset dan dokumentasinya.
4. Lisensi dataset tidak otomatis mencakup kode aplikasi, CSS, presentasi, atau elemen lain yang dibuat dalam proyek.

Lisensi: [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) untuk database dan [DbCL 1.0](https://opendatacommons.org/licenses/dbcl/1-0/) untuk isi data. IBM mencantumkan kedua lisensi pada [repositori upstream](https://github.com/IBM/employee-attrition-aif360).

## Pemrosesan

Skrip scripts/analysis_pipeline.py membaca sumber encoded, memetakan kategori Attrition, Department, Gender, dan OverTime, memeriksa kualitas data, serta membentuk label dan kelompok analisis. Kode kategori mengikuti struktur file yang digunakan proyek; verifikasi mapping jika beralih ke sumber atau versi dataset lain.

Pipeline analisis menghapus duplikasi baris penuh, menandai nilai di luar rentang, lalu mengisi nilai kosong dengan median untuk kolom numerik dan modus untuk kolom kategorikal. Pipeline menghentikan eksekusi jika file atau kolom wajib tidak tersedia. Karena imputasi dapat mengubah distribusi, README dan laporan harus membedakan kualitas file sumber dari kualitas data setelah pemrosesan.

## Atribusi pada hasil publikasi

Cantumkan sumber data di slide metodologi atau data overview pada deck presentasi, serta di deskripsi LinkedIn. Untuk chart yang dipisahkan dari deck, pertahankan catatan sumber pada halaman visualnya.
