# SRS Modul Inventaris & Pemeliharaan Aset v1

## 1. Pendahuluan

### 1.1 Tujuan

Dokumen ini mendefinisikan kebutuhan perangkat lunak untuk Modul
Inventaris & Pemeliharaan Aset pada Sistem Manajemen Sekolah. Modul ini
**tidak mencakup aspek keuangan** dan berfokus pada pencatatan,
pemantauan, dan pemeliharaan aset sekolah.

### 1.2 Ruang Lingkup

Modul mencakup: - Pendaftaran aset - Pemeliharaan aset - Penjadwalan
pemeliharaan - Monitoring kondisi aset

### 1.3 Definisi & Istilah

-   **Aset**: Barang milik sekolah yang digunakan untuk operasional.
-   **Pemeliharaan**: Aktivitas perawatan atau perbaikan aset.
-   **Penanggung Jawab**: Guru atau staf yang bertanggung jawab atas
    aset.

------------------------------------------------------------------------

## 2. Deskripsi Umum

### 2.1 Perspektif Produk

Modul ini merupakan bagian dari aplikasi manajemen sekolah dan
terintegrasi dengan modul: - Data Pengguna - Data Lokasi/Ruang

### 2.2 Karakteristik Pengguna

  Peran            Deskripsi
  ---------------- -------------------------------------
  Admin            Mengelola master data & konfigurasi
  Staff Sarpras    Mengelola inventaris & pemeliharaan
  Kepala Sekolah   Monitoring & laporan

------------------------------------------------------------------------

## 3. Kebutuhan Fungsional

### 3.1 Pendaftaran Aset

-   Menambah, mengubah, menghapus data aset
-   Generate kode aset & QR Code
-   Upload foto aset
-   Penentuan lokasi & penanggung jawab
-   Status aset: Aktif, Dipinjam, Rusak, Dihapus

#### 3.1.1 Struktur Data Ases
-   Kode Aset (auto / QR Code), Format : YYYY-MM-COUNTER berdasarkan tanggal perolehan, digenerate setiap kali mendaftarkan asset, reset per bulan. QR Code berisi kode dan data ringkas . QR Code ketika discan akan menuju ke halaman detail aset
-   Nama Aset
-   Kategori (Elektronik, Meubel, Gedung, Kendaraan, dll)
-   Lokasi (Gedung → Ruang), Buatkan master lokasi. Lokasi bisa bertingkat, asset mempunyai riwayat lokasi.
-   Penanggung Jawab (Guru / Staff), Ambilkan dari master guru/staff, 1 asset bisa menjadi tanggung jewab beberapa orang.
-   Kondisi Awal (Baik / Rusak Ringan / Rusak Berat), bisa berubah di luar pemeliharaan
-   Tanggal Perolehan
-   Status Aset (Aktif, Dipinjam, Rusak, Dihapus)

#### 3.1.2 Lain - lain
-   Dibuatkan fitur cetak label

### 3.2 Pemeliharaan Aset

-   Mencatat pemeliharaan rutin (yang sudah terjadwal) & insidental (tidak terjadwal)
-   Menyimpan kondisi sebelum & sesudah
-   Upload dokumentasi foto
-   Riwayat pemeliharaan per aset

#### 3.2.1 Lain-lain
-   Field biaya diinput, hanya untuk catatan
-   Yang input asset dan pemeliharaan adalah admin asset = admin

### 3.3 Jadwal Pemeliharaan

-   Penjadwalan berdasarkan periode (harian/mingguan/bulanan/tahunan). Terlamabt jika sudah terlambat 1 hari atau lebih
-   Reminder di dashboard saja
-   Status jadwal: Tepat Waktu / Terlambat

### 3.4 Mutasi & Peminjaman Aset

-   Pindah lokasi
-   Peminjaman & pengembalian aset
-   Tidak ada persetujuan peminjaman asset
-   Data peminjaman meliputi peminjam, tanggal pinjam, rencana kembali, tanggal kembali tanpa approval

### 3.5 Penghapusan Aset

-   Pencatatan alasan penghapusan, tidak perlu approval, soft delete, Tidak ada fitur restore
-   Tidak perlu ada berita acara

### 3.6 Laporan

-   Laporan daftar aset
-   Laporan pemeliharaan
-   Export PDF & Excel
-   Format tentukan saja oleh codex

------------------------------------------------------------------------

## 4. Kebutuhan Non-Fungsional

-   Role-based access control
-   Audit trail aktivitas meliputi perubahan status aset, dan semua perubahan field penting (lokasi, PJ, kondisi)
-   Responsif (desktop & mobile)
-   Backup data

------------------------------------------------------------------------

## 5. Batasan

-   Modul tidak menangani nilai aset & transaksi keuangan
-   Tidak terhubung dengan modul akuntansi

------------------------------------------------------------------------

## 6. Lain-lain

-   Dibangun menggunakan Django, Alpine.js, Bootsrap 5, html, mysql

------------------------------------------------------------------------
## 7. Lampiran

Versi Dokumen: v1.0\
Tanggal: 2026
