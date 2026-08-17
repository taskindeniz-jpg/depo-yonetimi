from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
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


# ---------- Mal Kabul ----------

class MalKabulKalemGiris(BaseModel):
    barkod: str
    beklenen_miktar: Optional[float] = None
    gelen_miktar: float
    fark_aciklamasi: Optional[str] = None


class MalKabulOlustur(BaseModel):
    tedarikci: str
    irsaliye_no: Optional[str] = None
    gelis_tarihi: Optional[datetime] = None
    not_: Optional[str] = None
    kalemler: List[MalKabulKalemGiris]


class MalKabulKalemiCikti(BaseModel):
    id: int
    urun_id: int
    beklenen_miktar: Optional[float] = None
    gelen_miktar: float
    fark_aciklamasi: Optional[str] = None

    class Config:
        from_attributes = True


class MalKabulCikti(BaseModel):
    id: int
    tedarikci: str
    irsaliye_no: Optional[str] = None
    gelis_tarihi: Optional[datetime] = None
    kabul_eden_adi_metin: Optional[str] = None
    not_: Optional[str] = None
    olusturma_tarihi: datetime
    kalemler: List[MalKabulKalemiCikti] = []

    class Config:
        from_attributes = True


# ---------- Sevkiyat ----------

class SevkiyatKalemGiris(BaseModel):
    barkod: str
    miktar: float


class SevkiyatOlustur(BaseModel):
    musteri: str
    sevk_no: Optional[str] = None
    sevk_tarihi: Optional[datetime] = None
    kontrol_eden_adi_metin: Optional[str] = None
    not_: Optional[str] = None
    kalemler: List[SevkiyatKalemGiris]


class SevkiyatKalemiCikti(BaseModel):
    id: int
    urun_id: int
    miktar: float

    class Config:
        from_attributes = True


class SevkiyatCikti(BaseModel):
    id: int
    musteri: str
    sevk_no: Optional[str] = None
    sevk_tarihi: Optional[datetime] = None
    hazirlayan_adi_metin: Optional[str] = None
    kontrol_eden_adi_metin: Optional[str] = None
    not_: Optional[str] = None
    olusturma_tarihi: datetime
    kalemler: List[SevkiyatKalemiCikti] = []

    class Config:
        from_attributes = True
