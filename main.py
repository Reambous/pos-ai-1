import asyncio  # Pastikan ini di-import di bagian atas file jika belum ada
import os
import json
import datetime
import uuid
from typing import List
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Struktur impor resmi google-genai SDK modern
from google import genai
from google.genai import types

from database import get_db
import models

# Muat variabel lingkungan dari file .env
load_dotenv()

# Inisialisasi aplikasi FastAPI
app = FastAPI(
    title="SmartPOS-AI Backend",
    description="Enterprise API untuk Sistem Kasir & Gudang Pintar berbasis AI",
    version="1.0.0"
)

# Daftarkan folder templates agar bisa diakses sebagai file statis
app.mount("/static", StaticFiles(directory="templates"), name="static")

# Konfigurasi CORS agar Frontend bisa berkomunikasi dengan API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inisialisasi Google GenAI Client Resmi (Versi Terbaru 2026)
api_key_env = os.getenv("GEMINI_API_KEY")
if not api_key_env:
    raise RuntimeError("❌ GEMINI_API_KEY tidak ditemukan di file .env!")

ai_client = genai.Client(api_key=api_key_env)

# --- SCHEMAS (VALIDASI DATA) ---


class OrderItem(BaseModel):
    product_id: int
    quantity: int


class TransactionCreate(BaseModel):
    payment_method: str  # tunai, qris, e_wallet, debit
    items: List[OrderItem]


class AIChatRequest(BaseModel):
    query: str


# --- CORE UI ENDPOINT ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    """Menyajikan halaman utama antarmuka kasir langsung dari server"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


# --- DATA ENDPOINTS ---
@app.get("/api/v1/health-check")
def health_check(db: Session = Depends(get_db)):
    try:
        total_products = db.query(models.Product).count()
        return {
            "database_status": "connected",
            "total_products_in_db": total_products
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database connection failed: {str(e)}")


@app.get("/api/v1/products")
def get_all_products(db: Session = Depends(get_db)):
    return db.query(models.Product).filter(models.Product.deleted_at == None).all()


@app.post("/api/v1/transactions")
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    cashier_id = 2
    invoice_num = f"INV-{uuid.uuid4().hex[:8].upper()}"

    new_transaction = models.Transaction(
        invoice_number=invoice_num,
        user_id=cashier_id,
        total_amount=Decimal("0.00"),
        payment_method=payload.payment_method,
        status="completed"
    )
    db.add(new_transaction)
    db.flush()

    running_total = Decimal("0.00")
    for item in payload.items:
        product = db.query(models.Product).filter(
            models.Product.id == item.product_id).first()
        if not product:
            db.rollback()
            raise HTTPException(
                status_code=404, detail=f"Produk ID {item.product_id} tidak ditemukan")
        if product.stock < item.quantity:
            db.rollback()
            raise HTTPException(
                status_code=400, detail=f"Stok {product.name} tidak mencukupi")

        item_subtotal = Decimal(str(product.price)) * item.quantity
        running_total += item_subtotal

        detail = models.TransactionDetail(
            transaction_id=new_transaction.id,
            product_id=product.id,
            quantity=item.quantity,
            unit_price=product.price,
            subtotal=item_subtotal
        )
        db.add(detail)

        product.stock -= item.quantity

        inv_log = models.InventoryLog(
            product_id=product.id,
            user_id=cashier_id,
            quantity_changed=-item.quantity,
            reason="penjualan"
        )
        db.add(inv_log)

    new_transaction.total_amount = running_total
    try:
        db.commit()
        db.refresh(new_transaction)
        return {
            "message": "Transaksi berhasil diproses",
            "invoice_number": new_transaction.invoice_number,
            "total_pembayaran": new_transaction.total_amount
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Gagal memproses transaksi: {str(e)}")


# --- ENGINE RAG (RETRIEVAL-AUGMENTED GENERATION) ---
def get_business_context_string(db: Session) -> str:
    # 1. Ambil SEMUA produk yang tidak dihapus agar AI tahu seluruh isi toko
    all_products = db.query(models.Product).filter(
        models.Product.deleted_at == None).all()

    # 2. Ambil 10 transaksi terakhir di kasir
    recent_transactions = db.query(models.Transaction).order_by(
        models.Transaction.transaction_date.desc()).limit(10).all()

    context = "=== DATA RIIL OPERASIONAL TOKO SAAT INI ===\n\n"

    context += "📦 DAFTAR SELURUH STOK PRODUK DI GUDANG & ETALASE:\n"
    if not all_products:
        context += "- Tidak ada produk terdaftar di database.\n"
    for p in all_products:
        # Beri penanda khusus jika stok produk di bawah 15 agar AI tahu mana yang kritis
        status_stok = "⚠️ MENIPIS" if p.stock < 15 else "✅ AMAN"
        context += f"- {p.name} (SKU: {p.sku}) | Stok: {p.stock} pcs | Harga: Rp{p.price} | Status: {status_stok} | Tags: {p.ai_tags}\n"

    context += "\n📊 10 TRANSAKSI TERAKHIR DI KASIR:\n"
    if not recent_transactions:
        context += "- Belum ada transaksi.\n"
    for t in recent_transactions:
        context += f"- Nota: {t.invoice_number} | Total: Rp{t.total_amount} | Metode: {t.payment_method}\n"

    return context


@app.post("/api/v1/ai/chat")
async def ai_chat_stream(payload: AIChatRequest, db: Session = Depends(get_db)):
    store_data = get_business_context_string(db)
    system_instruction = (
        "Anda adalah seorang Analis Bisnis Senior untuk SmartPOS-AI. "
        "Bantu owner menganalisis performa toko berdasarkan DATA RIIL berikut:\n\n"
        f"{store_data}\n\n"
        "Patuhi: Jawab secara faktual berdasarkan data di atas. Berikan saran taktis. Gunakan bahasa Indonesia kasual profesional."
    )

    async def gemini_token_generator():
        try:
            local_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

            response_stream = local_client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=payload.query,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                )
            )

            for chunk in response_stream:
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"
                    await asyncio.sleep(0.01)

        except Exception as e:
            # === KECERDASAN CADANGAN DINAMIS (FALLBACK ENGINE 3.0) ===
            yield f"data: {json.dumps({'text': '⚠️ [Server Gemini Cloud Sibuk (503). Beralih ke Kueri Lokal...]\n\n'})}\n\n"
            await asyncio.sleep(0.1)

            query_lower = payload.query.lower()
            # Hapus kata-kata tanya umum agar pencarian lebih fokus ke nama barang
            stop_words = ["berapa", "sisa", "stock", "stok", "ada",
                          "yang", "toko", "kah", "ini", "itu", "produk", "barang"]
            query_words = [word for word in query_lower.split()
                           if word not in stop_words]

            # Ambil semua produk aktif dari database
            all_products = db.query(models.Product).filter(
                models.Product.deleted_at == None).all()
            matched_product = None

            # Taktik 1: Cari yang benar-benar mengandung kata kunci penting (misal: mouse, kopi, susu)
            for p in all_products:
                p_name_lower = p.name.lower()
                # Jika ada kata dari kueri yang cocok dengan nama atau SKU produk
                if any(word in p_name_lower for word in query_words) or p.sku.lower() in query_lower:
                    matched_product = p
                    break

            if matched_product:
                status_limit = "⚠️ DI BAWAH LIMIT AMAN" if matched_product.stock < 15 else "✅ STOK AMAN"
                saran_taktis = (
                    "Sangat disarankan untuk segera melakukan pemesanan ulang (*restock*) ke supplier agar tidak kehilangan potensi penjualan esok hari!"
                    if matched_product.stock < 15 else
                    "Kondisi pasokan aman. Pertahankan kestabilan penjualan dan pantau pergerakan visualisasi produk di etalase."
                )

                jawaban_lokal = (
                    f"Halo Bos! Karena antrean Google AI sedang padat, saya tarik data riil langsung via database internal:\n\n"
                    f"📌 **Detail Informasi Produk:**\n"
                    f"* Nama Barang: **{matched_product.name}**\n"
                    f"* SKU: `{matched_product.sku}`\n"
                    f"* **Sisa Stok: {matched_product.stock} pcs** ({status_limit})\n"
                    f"* Harga Satuan: Rp{matched_product.price:,.0f}\n"
                    f"* Karakteristik (AI Tags): *{matched_product.ai_tags or '-'}*\n\n"
                    f"💡 **Rekomendasi Operasional:** {saran_taktis}"
                )
            else:
                jawaban_lokal = (
                    "Mohon maaf Bos, server AI Google Gemini sedang mengalami gangguan trafik (503).\n\n"
                    "Saya tidak menemukan kecocokan nama produk spesifik dari kueri Anda di database lokal toko. "
                    "Namun, Anda tetap dapat memantau grafik stok barang secara riil melalui kartu produk di panel sebelah kiri layar!"
                )

            yield f"data: {json.dumps({'text': jawaban_lokal})}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive"
    }
    return StreamingResponse(gemini_token_generator(), media_type="text/event-stream", headers=headers)
