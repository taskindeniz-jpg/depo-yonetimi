from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .models import HareketTipi, KullaniciRolu


class GirisIstek(BaseModel):
    kullanici_adi: str
    sifre: str


class TokenCikti(BaseModel):
    access_token: str
    token_type: str = "bearer"
    kullanici_adi: str
    rol: str


class SifreDegistirIstek(BaseModel):
    eski_sifre: str
    yeni_sifre: str


class KullaniciOlustur(BaseModel):
    kullanici_adi: str
    sifre: str
    rol: KullaniciRolu = KullaniciRolu.personel


class KullaniciCikti(BaseModel):
    id: int
    kullanici_adi: str
    rol: str
    aktif: bool
    olusturma_tarihi: datetime

    class Config:
        from_attributes = True


class UrunOlustur(BaseModel):
    barkod: str
    ad: str
    birim: str = "adet"
    miktar: float = 0
    min_stok: float = 0
    kritik_stok: float = 0


class UrunGuncelle(BaseModel):
    ad: Optional[str] = None
    birim: Optional[str] = None
    min_stok: Optional[float] = None
    kritik_stok: Optional[float] = None


class UrunCikti(BaseModel):
    id: int
    barkod: str
    ad: str
    birim: str
    miktar: float
    min_stok: float
    kritik_stok: float
    silindi: bool
    olusturma_tarihi: datetime

    class Config:
        from_attributes = True


class HareketOlustur(BaseModel):
    barkod: str
    tip: HareketTipi
    miktar: float
    not_: Optional[str] = None
    neden: Optional[str] = None


class HareketCikti(BaseModel):
    id: int
    urun_id: int
    tip: HareketTipi
    miktar: float
    onceki_miktar: Optional[float] = None
    sonraki_miktar: Optional[float] = None
    not_: Optional[str] = None
    neden: Optional[str] = None
    kullanici_adi_metin: Optional[str] = None
    tarih: datetime

    class Config:
        from_attributes = True


class DenetimKaydiCikti(BaseModel):
    id: int
    kullanici_adi: Optional[str] = None
    islem: str
    hedef_tip: Optional[str] = None
    hedef_id: Optional[str] = None
    eski_deger: Optional[str] = None
    yeni_deger: Optional[str] = None
    ip_adresi: Optional[str] = None
    tarih: datetime

    class Config:
        from_attributes = True
