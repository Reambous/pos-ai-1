import os
import json
import datetime
import uuid
from typing import List
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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

# Konfigurasi CORS agar Frontend bisa berkomunikasi dengan API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inisialisasi Google GenAI Client Resmi (Versi Terbaru 2026)
# Mengambil API Key secara aman dari os.getenv
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


# --- CORE ENDPOINTS ---

@app.get("/")
def root():
    return {
        "status": "online",
        "message": "Welcome to SmartPOS-AI Core Engine API",
        "version": "1.0.0"
    }


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
    low_stock_products = db.query(models.Product).filter(
        models.Product.stock < 15, models.Product.deleted_at == None).all()
    recent_transactions = db.query(models.Transaction).order_by(
        models.Transaction.transaction_date.desc()).limit(10).all()

    context = "=== DATA RIIL OPERASIONAL TOKO SAAT INI ===\n\n"
    context += "⚠️ DAFTAR STOK PRODUK MENIPIS:\n"
    if not low_stock_products:
        context += "- Semua stok produk aman.\n"
    for p in low_stock_products:
        context += f"- {p.name} (SKU: {p.sku}) | Sisa Stok: {p.stock} | Harga: Rp{p.price}\n"

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
            # Menggunakan SDK google-genai terupdate secara streaming
            response_stream = ai_client.models.generate_content_stream(
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
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Terjadi masalah koneksi AI: {str(e)}'})}\n\n"

    return StreamingResponse(gemini_token_generator(), media_type="text/event-stream")
