import datetime
from decimal import Decimal
from database import engine, Base, SessionLocal
from models import User, Category, Product, Transaction, TransactionDetail, InventoryLog

print("🔄 Menginisialisasi skema database berdasarkan ERD Final...")
# Perintah ini akan membaca models.py dan menciptakan file smartpos.db otomatis
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # 1. Seed User (Hak Akses)
    print("👥 Menambahkan akun pengguna (Roles)...")
    admin_user = User(username="haidar_admin",
                      password_hash="hash_secure_password_123", role="admin")
    cashier_user = User(username="budi_kasir",
                        password_hash="hash_secure_password_456", role="cashier")
    db.add_all([admin_user, cashier_user])
    db.commit()

    # 2. Seed Kategori
    print("📦 Menambahkan kategori produk...")
    cat_elektronik = Category(name="Elektronik", is_active=True)
    cat_makanan = Category(name="Makanan & Minuman", is_active=True)
    db.add_all([cat_elektronik, cat_makanan])
    db.commit()

    # 3. Seed Produk beserta Metadata AI (ai_tags)
    print("🏷️ Menambahkan master produk dan tagging analisis AI...")
    p1 = Product(
        category_id=cat_elektronik.id,
        sku="ELK001",
        name="Mouse Wireless Logitech",
        price=Decimal("150000.00"),
        stock=50,
        ai_tags='{"karakteristik": "aksesoris komputasi, margin tinggi", "tren_musiman": "stabil sepanjang tahun"}'
    )
    p2 = Product(
        category_id=cat_makanan.id,
        sku="MKN001",
        name="Kopi Susu Gula Aren 250ml",
        price=Decimal("18000.00"),
        stock=12,  # Stok sengaja dibuat menipis agar AI nanti bisa mendeteksi alert re-stock!
        ai_tags='{"karakteristik": "fast moving, produk konsumsi harian, margin tipis", "tren_musiman": "tinggi di jam istirahat kantor"}'
    )
    db.add_all([p1, p2])
    db.commit()

    # 4. Catat Log Mutasi Gudang Pertama (Inventory Logs)
    print("📜 Mencatat mutasi log awal gudang...")
    log1 = InventoryLog(product_id=p1.id, user_id=admin_user.id,
                        quantity_changed=50, reason="restock")
    log2 = InventoryLog(product_id=p2.id, user_id=admin_user.id,
                        quantity_changed=12, reason="restock")
    db.add_all([log1, log2])
    db.commit()

    # 5. Seed Simulasi Transaksi Riil (Mencakup variasi metode pembayaran)
    print("💰 Menyusun simulasi transaksi historis kasir...")
    t1 = Transaction(
        invoice_number="INV-20260627-001",
        user_id=cashier_user.id,
        total_amount=Decimal("168000.00"),
        payment_method="qris",  # Variasi pembayaran untuk bahan analitik RAG
        status="completed"
    )
    db.add(t1)
    db.commit()

    # Detail transaksi untuk invoice di atas
    d1 = TransactionDetail(transaction_id=t1.id, product_id=p1.id, quantity=1,
                           unit_price=Decimal("150000.00"), subtotal=Decimal("150000.00"))
    d2 = TransactionDetail(transaction_id=t1.id, product_id=p2.id, quantity=1,
                           unit_price=Decimal("18000.00"), subtotal=Decimal("18000.00"))
    db.add_all([d1, d2])
    db.commit()

    print("✅ Database berhasil dibuat dan data simulasi terisi sempurna!")

except Exception as e:
    db.rollback()
    print(f"❌ Terjadi kegagalan pembuatan database: {str(e)}")
finally:
    db.close()
