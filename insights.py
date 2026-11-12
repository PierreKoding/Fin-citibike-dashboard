"""Teks insight yang tampil di dashboard.

Setiap angka di bawah bisa dicek pada grafik di halaman yang disebut di "page".
Sunting kalimatnya supaya sesuai dengan penjelasan di laporan dan presentasi.

Cara pakai
  - "page"  : halaman tempat insight ditampilkan -> "demand" (Pola aktivitas),
              "model" (Hasil prediksi), atau "network" (Jaringan stasiun).
  - "title" : satu kalimat pendek, temuan utamanya.
  - "body"  : apa yang terlihat di grafik dan apa artinya bagi operasional.
  - Judul semua insight juga tampil di halaman Ringkasan, sesuai urutan di bawah.
  - Jika "body" dikosongkan, dashboard menampilkan kotak pengingat kuning.
"""

INSIGHTS = [
    {
        # Cek: halaman Hasil prediksi, kartu angka MAE untuk Peminjaman dan Pengembalian.
        "page": "model",
        "title": "Riwayat stasiun cukup untuk prediksi satu jam ke depan; data cuaca belum menambah akurasi",
        "body": (
            "Model berbasis riwayat aktivitas dan kalender menurunkan rata-rata selisih prediksi peminjaman "
            "dari 0,95 menjadi 0,82 perjalanan per stasiun per jam (−14,5% dibanding baseline) dan pengembalian "
            "dari 0,92 menjadi 0,79 (−13,3%). Dengan tambahan data cuaca, selisihnya justru naik menjadi 0,89 "
            "dan 0,86. Bagi operator, prediksi jangka pendek bisa dijalankan dari data perjalanan yang sudah ada "
            "tanpa menambah sumber data cuaca pada tahap ini. Pengujian baru mencakup Juli 2019, jadi temuan "
            "soal cuaca perlu diuji lagi di musim lain."
        ),
    },
    {
        # Cek: halaman Hasil prediksi (Peminjaman), grafik selisih menurut jam dan grafik per stasiun.
        "page": "model",
        "title": "Prediksi paling meleset di stasiun dan jam tersibuk",
        "body": (
            "Selisih prediksi peminjaman sekitar 1,6 perjalanan per stasiun per jam pada jam 08.00 dan 18.00, "
            "tetapi hanya sekitar 0,1 pada dini hari. Di Grove St PATH selisihnya 2,82, lebih dari tiga kali "
            "rata-rata semua stasiun (0,82), dan rata-rata itu terbantu oleh 58,7% jam yang memang tanpa "
            "perjalanan. Untuk operasional, prediksi bisa dipakai langsung di sebagian besar stasiun, sedangkan "
            "di stasiun utama pada jam sibuk tetap perlu cadangan sepeda dan dok kosong serta pemantauan langsung."
        ),
    },
    {
        # Cek: halaman Jaringan stasiun, grafik total aktivitas, 15 rute tersibuk, dan selisih masuk − keluar.
        "page": "network",
        "title": "Jaringan bertumpu pada Grove St PATH",
        "body": (
            "Total aktivitas Grove St PATH 30.110 perjalanan, lebih dari dua kali stasiun kedua (Hamilton Park, "
            "14.102), dan 13 dari 15 rute tersibuk berawal atau berakhir di sana. Selama tiga bulan stasiun ini "
            "menerima 3.324 perjalanan lebih banyak daripada yang berangkat, sedangkan McGinley Square, "
            "Jersey & 6th St, dan Sip Ave lebih banyak ditinggalkan. Gangguan atau dok penuh di Grove St PATH "
            "berdampak pada porsi perjalanan terbesar, jadi stasiun ini layak diprioritaskan untuk kapasitas dok, "
            "perawatan, dan pemindahan sepeda. Selisih arus ini menunjukkan arah, belum jumlah sepeda yang perlu "
            "dipindahkan."
        ),
    },
    {
        # Cek: halaman Pola aktivitas, profil 24 jam untuk Semua stasiun lalu untuk Grove St PATH (Mei–Juli).
        "page": "demand",
        "title": "Pagi sepeda mengalir ke Grove St PATH, sore mengalir keluar",
        "body": (
            "Pada hari kerja, peminjaman di 52 stasiun memuncak pada jam 08.00 (sekitar 176 per jam) dan 18.00 "
            "(sekitar 159); puncak pagi itu kira-kira 3,7 kali tengah hari, sedangkan akhir pekan lebih landai "
            "dengan puncak sekitar 80. Di Grove St PATH arahnya berlawanan: jam 08.00 rata-rata 63 pengembalian "
            "dan 6 peminjaman, jam 18.00 rata-rata 41 peminjaman dan 9 pengembalian. Dok kosong perlu tersedia "
            "di sana sebelum puncak pagi dan sepeda perlu tersedia sebelum puncak sore; pemindahan sepeda dan "
            "perawatan lebih aman dijadwalkan di luar dua puncak itu."
        ),
    },
]
