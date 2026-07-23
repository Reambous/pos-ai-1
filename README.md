# SmartPOS-AI

**Sistem Kasir & Analisis Bisnis berbasis AI**

Aplikasi Point-of-Sale (POS) cerdas yang terintegrasi dengan **Google Gemini AI** sebagai asisten analis bisnis. Sistem ini memungkinkan pemilik toko untuk melakukan transaksi kasir, mengelola stok gudang secara real-time, dan bertanya langsung ke AI tentang kondisi bisnis berdasarkan data operasional toko yang sesungguhnya (RAG — Retrieval-Augmented Generation).

---

## Tech Stack & Tools

| Bagian | Teknologi |
|--------|-----------|
| Backend | Python, FastAPI |
| AI / LLM | Google Gemini (`gemini-2.5-flash`) via `google-genai` SDK |
| Database | SQLite, SQLAlchemy ORM |
| Frontend | HTML, Tailwind CSS, Alpine.js |
| Serialisasi | Pydantic |
| Streaming | Server-Sent Events (SSE) |
| Tools | dotenv, UUID, CORS |

---

## Key Features (Fitur Utama)

### 1. Kasir Digital
Tambah produk ke keranjang, pilih metode pembayaran (Tunai / QRIS / E-Wallet), dan proses transaksi dengan pembuatan nomor invoice otomatis.

### 2. Manajemen Inventaris Real-time
Stok barang berkurang secara otomatis saat transaksi, pencatatan log mutasi gudang (restock, penjualan, koreksi), dan fitur soft-delete produk.

### 3. AI Business Consultant (RAG)
Panel obrolan interaktif dengan Google Gemini yang membaca data stok & riwayat transaksi terkini dari database untuk memberikan saran bisnis taktis — misalnya produk mana yang perlu di-restock atau tren pembayaran yang dominan.

### 4. Fallback Engine Lokal
Saat layanan Gemini mengalami gangguan (error/timeout), sistem secara otomatis beralih ke mesin pencarian lokal yang mencocokkan pertanyaan user dengan database produk internal dan tetap memberikan jawaban yang informatif.

### 5. Streaming Respons Real-time
Respons AI ditampilkan token per token melalui mekanisme Server-Sent Events (SSE), memberikan pengalaman mengetik langsung seperti chat pada umumnya tanpa perlu menunggu loading lama.

### 6. Dashboard Satu Halaman
UI yang ringkas dengan panel kasir di sisi kiri dan panel AI Business Consultant di sisi kanan — semua fungsi tersedia dalam satu tampilan.

---

## Screenshot

![SmartPOS-AI Dashboard](screenshot.png)

> Tampilan dashboard SmartPOS-AI dengan panel kasir (kiri) dan AI Business Consultant (kanan).

---

## Cara Menjalankan

```bash
# 1. Clone repositori
git clone <repo-url>
cd pos1

# 2. Buat virtual environment (opsional)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Instal dependensi
pip install fastapi uvicorn sqlalchemy python-dotenv pydantic google-genai

# 4. Atur API Key
# Edit file .env dan isi GEMINI_API_KEY dengan kunci Anda

# 5. Seed database (hanya sekali)
python seed.py

# 6. Jalankan server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 7. Buka browser
# http://localhost:8000
```