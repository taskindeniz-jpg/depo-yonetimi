from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .database import Base


class HareketTipi(str, enum.Enum):
    giris = "giris"
    cikis = "cikis"


class KullaniciRolu(str, enum.Enum):
    super_admin = "super_admin"
    depo_muduru = "depo_muduru"
    personel = "personel"
    goruntuleyici = "goruntuleyici"


class Kullanici(Base):
    __tablename__ = "kullanicilar"

    id = Column(Integer, primary_key=True, index=True)
    kullanici_adi = Column(String, unique=True, index=True, nullable=False)
    sifre_hash = Column(String, nullable=False)
    rol = Column(Enum(KullaniciRolu), nullable=False, default=KullaniciRolu.personel)
    aktif = Column(Boolean, default=True)
    olusturma_tarihi = Column(DateTime(timezone=True), server_default=func.now())


class Urun(Base):
    __tablename__ = "urunler"

    id = Column(Integer, primary_key=True, index=True)
    barkod = Column(String, unique=True, index=True, nullable=False)
    ad = Column(String, nullable=False)
    birim = Column(String, default="adet")
    miktar = Column(Float, default=0)
    min_stok = Column(Float, default=0)
    kritik_stok = Column(Float, default=0)
    olusturma_tarihi = Column(DateTime(timezone=True), server_default=func.now())

    # Soft delete: ürün gerçekten silinmez, işaretlenir. Böylece geçmiş
    # hareket kayıtları bozulmaz ve yanlışlıkla silme geri alınabilir.
    silindi = Column(Boolean, default=False, nullable=False)
    silinme_tarihi = Column(DateTime(timezone=True), nullable=True)

    hareketler = relationship("StokHareketi", back_populates="urun")


class StokHareketi(Base):
    __tablename__ = "stok_hareketleri"

    id = Column(Integer, primary_key=True, index=True)
    urun_id = Column(Integer, ForeignKey("urunler.id"), nullable=False)
    tip = Column(Enum(HareketTipi), nullable=False)
    miktar = Column(Float, nullable=False)

    # Hareket öncesi/sonrası stok miktarı: geçmişi incelerken "o anda kaç
    # taneydi" sorusuna kesin cevap verir, sonradan hesaplamaya gerek kalmaz.
    onceki_miktar = Column(Float, nullable=True)
    sonraki_miktar = Column(Float, nullable=True)

    not_ = Column("not", Text, nullable=True)
    neden = Column(String, nullable=True)  # örn: "satış", "iade", "düzeltme", "sayım farkı"

    kullanici_id = Column(Integer, ForeignKey("kullanicilar.id"), nullable=True)
    kullanici_adi_metin = Column(String, nullable=True)  # kullanıcı silinse bile iz kalsın diye

    tarih = Column(DateTime(timezone=True), server_default=func.now())

    urun = relationship("Urun", back_populates="hareketler")


class DenetimKaydi(Base):
    """Audit log: sistemde kim, ne zaman, neyi değiştirdi."""
    __tablename__ = "denetim_kayitlari"

    id = Column(Integer, primary_key=True, index=True)
    kullanici_adi = Column(String, nullable=True)
    islem = Column(String, nullable=False)  # örn: "urun_olustur", "urun_sil", "giris_basarisiz"
    hedef_tip = Column(String, nullable=True)  # örn: "urun", "kullanici"
    hedef_id = Column(String, nullable=True)
    eski_deger = Column(Text, nullable=True)
    yeni_deger = Column(Text, nullable=True)
    ip_adresi = Column(String, nullable=True)
    tarih = Column(DateTime(timezone=True), server_default=func.now())
