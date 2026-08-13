from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .models import HareketTipi


class UrunOlustur(BaseModel):
    barkod: str
    ad: str
    birim: str = "adet"
    miktar: float = 0
    min_stok: float = 0


class UrunGuncelle(BaseModel):
    ad: Optional[str] = None
    birim: Optional[str] = None
    min_stok: Optional[float] = None


class UrunCikti(BaseModel):
    id: int
    barkod: str
    ad: str
    birim: str
    miktar: float
    min_stok: float
    olusturma_tarihi: datetime

    class Config:
        from_attributes = True


class HareketOlustur(BaseModel):
    barkod: str
    tip: HareketTipi
    miktar: float
    not_: Optional[str] = None


class HareketCikti(BaseModel):
    id: int
    urun_id: int
    tip: HareketTipi
    miktar: float
    not_: Optional[str] = None
    tarih: datetime

    class Config:
        from_attributes = True
