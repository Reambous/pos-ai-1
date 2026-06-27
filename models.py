import datetime
from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="cashier")  # admin, cashier, warehouse
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # Soft Delete Mechanism

    # Hubungan Relasi (Relationships)
    transactions = relationship("Transaction", back_populates="cashier")
    inventory_logs = relationship("InventoryLog", back_populates="actor")
    chat_logs = relationship("AIChatLog", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    sku = Column(String, unique=True, index=True, nullable=False)  # Barcode
    name = Column(String, index=True, nullable=False)
    # Presisi keuangan decimal(12,2)
    price = Column(Numeric(12, 2), nullable=False)
    stock = Column(Integer, default=0)
    # JSON/Text Meta data untuk konsumsi kontekstual AI
    ai_tags = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # Soft Delete Mechanism

    category = relationship("Category", back_populates="products")
    details = relationship("TransactionDetail", back_populates="product")
    logs = relationship("InventoryLog", back_populates="product")


class InventoryLog(Base):
    __tablename__ = "inventory_logs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Bisa positif (restock) atau negatif (rusak)
    quantity_changed = Column(Integer, nullable=False)
    # restock, produk_rusak, koreksi_stok, penjualan
    reason = Column(String, nullable=False)
    logged_at = Column(DateTime, default=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="logs")
    actor = relationship("User", back_populates="inventory_logs")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"),
                     nullable=False)  # Kasir yang memproses
    total_amount = Column(Numeric(12, 2), nullable=False)
    # tunai, qris, e_wallet, debit
    payment_method = Column(String, nullable=False)
    status = Column(String, default="completed")  # completed, refunded
    transaction_date = Column(DateTime, default=datetime.datetime.utcnow)

    cashier = relationship("User", back_populates="transactions")
    items = relationship("TransactionDetail", back_populates="transaction")


class TransactionDetail(Base):
    __tablename__ = "transaction_details"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey(
        "transactions.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)

    transaction = relationship("Transaction", back_populates="items")
    product = relationship("Product", back_populates="details")


class AIChatLog(Base):
    __tablename__ = "ai_chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_query = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="chat_logs")
