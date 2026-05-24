# 📁 File Sharing Telegram Bot v2

Bot Telegram berbasis [Pyrogram](https://docs.pyrogram.org/) untuk menyimpan file ke channel Telegram sebagai database cloud, lalu membagikannya lewat link unik yang **diproteksi anti-forward & anti-screenshot**.

Versi 2 ini menambahkan fitur **Force Join** — user wajib join channel tertentu sebelum bisa mengakses file, menggunakan **inline button** yang otomatis tampil sesuai jumlah channel yang belum di-join.

---

## ✨ Fitur

- 🔐 **Link Unik per File** — setiap file mendapat kode acak 10 karakter (huruf + angka)
- 🛡️ **Proteksi Konten** — file dikirim dengan `protect_content=True`, mencegah forward & screenshot
- ☁️ **Cloud Storage via Channel** — file disimpan di channel Telegram sebagai database
- 👮 **Akses Admin Only** — hanya admin yang bisa upload
- 🔒 **Force Join/Subscribe** — user wajib join 1 atau lebih channel sebelum akses file
- 🔘 **Inline Button Join** — tombol join tampil otomatis per channel yang belum di-join
- ✅ **Auto Kirim Setelah Verifikasi** — setelah klik "Sudah Join", file langsung dikirim otomatis
- ⚡ **Siap Deploy ke Railway** — sudah dilengkapi `Procfile` dan konfigurasi env variable

---

## 🚀 Deploy ke Railway

### Cara Manual

1. **Fork** repo ini ke akun GitHub kamu
2. Buka [railway.app](https://railway.app) dan login
3. Klik **New Project** → **Deploy from GitHub Repo** → pilih repo ini
4. Buka tab **Variables**, lalu isi semua environment variable berikut:

| Variable | Keterangan |
|---|---|
| `API_ID` | Telegram API ID dari [my.telegram.org](https://my.telegram.org/auth) |
| `API_HASH` | Telegram API Hash dari [my.telegram.org](https://my.telegram.org/auth) |
| `BOT_TOKEN` | Token bot dari [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | User ID Telegram kamu (owner/admin bot) |
| `DB_CHANNEL` | ID channel Telegram database (format: `-100xxxxxxxxxx`) |
| `FORCE_JOIN_CHANNELS` | ID channel yang wajib di-join, pisah koma jika lebih dari 1. Contoh: `-1001234567890,-1009876543210` |

> **Catatan:** Jika tidak ingin menggunakan force join, kosongkan saja variabel `FORCE_JOIN_CHANNELS`.

5. Railway akan otomatis menjalankan perintah dari `Procfile`:
   ```
   worker: python main.py
   ```
6. Tunggu deploy selesai — bot langsung aktif!

---

## ⚙️ Persyaratan Sebelum Deploy

### 1. API_ID & API_HASH
- Buka [my.telegram.org/auth](https://my.telegram.org/auth)
- Login → **API Development Tools** → buat aplikasi baru
- Salin `API ID` dan `API Hash`

### 2. BOT_TOKEN
- Buka [@BotFather](https://t.me/BotFather) di Telegram
- Kirim `/newbot` → ikuti instruksi → salin token

### 3. ADMIN_ID
- Buka [@userinfobot](https://t.me/userinfobot) → kirim `/start`
- Salin **User ID** kamu

### 4. DB_CHANNEL
- Buat channel Telegram baru (bisa private)
- Tambahkan bot ke channel tersebut
- **Jadikan bot sebagai Admin** dengan semua permission (terutama *Post Messages*)
- ID channel biasanya berawalan `-100...`

### 5. FORCE_JOIN_CHANNELS
- Buat channel yang ingin dijadikan syarat join (bisa public atau private)
- **Jadikan bot sebagai Admin** di setiap channel tersebut (minimal permission *Invite Users*)
- Isi ID channel, pisah dengan koma jika lebih dari 1

---

## 📖 Cara Penggunaan

### Sebagai Admin
1. Buka chat pribadi dengan bot
2. Kirim file apa saja (foto, video, dokumen)
3. Bot akan membalas dengan **link sharing** unik
4. Bagikan link tersebut ke siapa saja

### Sebagai User
1. Klik link yang dibagikan admin
2. Jika belum join channel wajib → bot akan tampilkan **tombol join** untuk tiap channel
3. Klik tombol join, lalu klik **"✅ Sudah Join, Coba Lagi"**
4. Bot otomatis memverifikasi dan langsung mengirimkan file

---

## 🧱 Struktur Project

```
File-Sharing-Telegram-Bot-v2/
├── main.py           # Logika utama bot (Pyrogram)
├── requirements.txt  # Dependensi: pyrogram, tgcrypto
├── Procfile          # Entry point untuk Railway
└── README.md
```

---

## ⚠️ Catatan Penting

- Bot **harus menjadi Admin** di DB_CHANNEL dan semua FORCE_JOIN_CHANNELS
- Link sharing bersifat **in-memory** (tidak persisten). Jika bot di-restart, semua link lama akan hilang. Pertimbangkan PostgreSQL/Supabase untuk produksi
- `tgcrypto` diperlukan untuk enkripsi — **jangan dihapus** dari `requirements.txt`
- Jika `FORCE_JOIN_CHANNELS` dikosongkan, fitur force join **otomatis dinonaktifkan**

---

## 📝 Perubahan dari v1

| Fitur | v1 | v2 |
|---|---|---|
| Force Join Channel | ❌ | ✅ |
| Inline Button Join | ❌ | ✅ |
| Support Multi Channel | ❌ | ✅ |
| Auto Kirim Setelah Verifikasi | ❌ | ✅ |
| Kode dibawa saat callback | ❌ | ✅ |
