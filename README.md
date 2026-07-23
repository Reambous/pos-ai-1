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

<img width="1916" height="1031" alt="image" src="https://github.com/user-attachments/assets/8324e540-d929-4c81-bae6-ea0a4ea02bae" />
