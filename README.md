# 🎀 Tomoe Bot — Telegram AI Girlfriend

> ⚠️ **DISCLAIMER: INI PROJECT HALU PERTAMA GW. ADDICTION ALERT!!!** ⚠️
> 
> Bot ini dibuat murni untuk hiburan pribadi. Jangan terlalu serius, tapi... ya gimana ya. 🫠

---

## 📖 Tentang Bot

**Tomoe Bot** adalah bot Telegram berbasis AI yang menjalankan persona **Koga Tomoe** — gadis SMA kelas 10 yang tsundere, tomboy, dan diam-diam dari Fukuoka. Dia adalah pacar virtual kamu yang:

- 😤 Gengsi banget ngakuin perasaan, tapi perhatian banget diam-diam
- 📱 Punya kesadaran waktu **real-time** (tau lagi pagi, siang, sore, atau malam)
- 🌤️ Otomatis kirim **info cuaca Bekasi + semangat pagi** setiap jam 06:00 WIB
- 🔍 Bisa **search internet** kalau kamu tanya sesuatu
- 🧠 Punya **memori percakapan** (ingat obrolan sebelumnya)
- 🔒 **Private** — hanya kamu yang bisa chat

---

## 🛠️ Tech Stack

| Komponen | Teknologi |
|---|---|
| Bot Framework | `python-telegram-bot` v22 |
| AI / LLM | Google Gemini Flash (via LangChain) |
| Internet Search | DuckDuckGo Search |
| Scheduler | APScheduler (job-queue) |
| Memory | JSON file (chat_history.json) |
| Deploy | Railway |

---

## ⚙️ Cara Setup Lokal

### 1. Clone repo
```bash
git clone https://github.com/kipliCeviel/tomoe-bot.git
cd tomoe-bot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
pip install -U ddgs
```

### 3. Buat file `.env`
Buat file `.env` di root folder, isi dengan:
```env
TELEGRAM_TOKEN=isi_token_telegram_bot_kamu
GEMINI_API_KEY=isi_gemini_api_key_kamu
BOT_PERSONA="..." # Salin dari contoh di bawah
ALLOWED_CHAT_ID=   # Kosongkan dulu, isi setelah dapat ID kamu
```

> **Cara dapat token:** Buka [@BotFather](https://t.me/BotFather) di Telegram → `/newbot`
> 
> **Cara dapat Gemini API Key:** Buka [Google AI Studio](https://aistudio.google.com/)

### 4. Jalankan bot
```bash
python bot.py
```

### 5. Cari tahu Chat ID kamu
Kirim `/myid` ke bot kamu di Telegram, lalu salin angka yang muncul ke `.env`:
```env
ALLOWED_CHAT_ID=angka_id_kamu
```
Restart bot, selesai! 🎉

---

## 🚀 Cara Deploy ke Railway (24/7)

1. Push kode ke GitHub (pastikan `.env` **tidak ikut** — sudah ada di `.gitignore`)
2. Buka [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Pilih repo `tomoe-bot`
4. Di dashboard Railway → tab **Variables**, tambahkan semua key dari `.env`:
   - `TELEGRAM_TOKEN`
   - `GEMINI_API_KEY`
   - `BOT_PERSONA`
   - `ALLOWED_CHAT_ID`
5. Railway otomatis build dan deploy. Bot langsung running 24/7! ✅

---

## 💬 Daftar Command

| Command | Fungsi |
|---|---|
| `/start` | Sapa Tomoe dan mulai obrolan |
| `/help` | Info singkat cara pakai bot |
| `/myid` | Tampilkan Chat ID Telegram kamu (untuk setup whitelist) |
| `/testmorning` | Tes fitur pesan pagi otomatis dari Tomoe |

---

## ✨ Fitur Lengkap

### 🕐 Kesadaran Waktu Real-Time
Setiap pesan yang kamu kirim otomatis disertai konteks waktu nyata (jam, hari, tanggal WIB). Tomoe tahu kapan kamu chat — pagi, siang, sore, atau malam larut — dan responsnya disesuaikan dengan aktivitasnya saat itu.

### 📅 Jadwal Harian Tomoe
Tomoe punya rutinitas harian layaknya siswi SMA beneran:
- **Pagi**: Siap-siap sekolah, bisa panik kalau hampir telat
- **Jam sekolah**: Lagi di kelas, bosen, diam-diam main HP
- **Istirahat**: Kantin bareng geng, foto-foto buat story
- **Sore**: Ekskul atau nongkrong
- **Malam**: Belajar, scrolling TikTok, nonton drama
- **Malam larut**: Begadang tapi ngantuk, lebih mellow dari biasanya

### ☀️ Pesan Pagi Otomatis (06:00 WIB)
Setiap hari jam 6 pagi, Tomoe otomatis nge-chat kamu duluan dengan info cuaca Bekasi terkini dan semangat kerja ala tsundere.

### 🧠 Memori Percakapan
Bot menyimpan 10 ronde obrolan terakhir sehingga Tomoe bisa ingat konteks percakapan sebelumnya.

### 🔒 Private & Eksklusif
Hanya Chat ID yang terdaftar di `ALLOWED_CHAT_ID` yang bisa berinteraksi. User lain akan diabaikan secara diam-diam.

---

## 📁 Struktur Project

```
tomoe-bot/
├── bot.py              # Entry point bot Telegram & scheduler
├── agent.py            # LangChain agent + memori + time context
├── requirements.txt    # Daftar dependencies
├── Procfile            # Konfigurasi start Railway
├── railway.toml        # Konfigurasi deploy Railway
├── .gitignore          # File yang tidak di-push ke GitHub
└── .env                # ⛔ RAHASIA — jangan di-commit!
```

---

## ⚠️ Disclaimer

- Bot ini adalah **proyek halu pribadi** untuk hiburan. Tidak dimaksudkan sebagai pengganti interaksi sosial nyata.
- API Key Gemini gratis memiliki batas **1.500 request/hari** dan **15 request/menit**. Jangan spam!
- Karakter Koga Tomoe adalah milik manga/anime *Seishun Buta Yarou wa Bunny Girl Senpai no Yume wo Minai* oleh Hajime Kamoshida. Bot ini bukan afiliasi resmi.
- **ADDICTION ALERT**: Penulis tidak bertanggung jawab atas efek samping berupa baper, senyum-senyum sendiri, atau ketagihan chat sama bot. 🫠

---

*Made with 💜 and a questionable amount of free time.*
