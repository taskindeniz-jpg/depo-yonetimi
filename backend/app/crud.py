from sqlalchemy.orm import Session
from fastapi import HTTPException

from . import models, schemas


def kullanici_getir(db: Session, kullanici_adi: str):
    return db.query(models.Kullanici).filter(models.Kullanici.kullanici_adi == kullanici_adi).first()


def kullanici_olustur(db: Session, kullanici_adi: str, sifre_hash: str):
    kullanici = models.Kullanici(kullanici_adi=kullanici_adi, sifre_hash=sifre_hash)
    db.add(kullanici)
    db.commit()
    db.refresh(kullanici)
    return kullanici


def urun_getir_barkod(db: Session, barkod: str):
    return db.query(models.Urun).filter(models.Urun.barkod == barkod).first()


def urun_listele(db: Session):
    return db.query(models.Urun).order_by(models.Urun.ad).all()


def urun_olustur(db: Session, urun: schemas.UrunOlustur):
    mevcut = urun_getir_barkod(db, urun.barkod)
    if mevcut:
        raise HTTPException(status_code=400, detail="Bu barkod zaten kayıtlı")
    yeni_urun = models.Urun(**urun.dict())
    db.add(yeni_urun)
    db.commit()
    db.refresh(yeni_urun)
    return yeni_urun


def urun_guncelle(db: Session, barkod: str, degisiklik: schemas.UrunGuncelle):
    urun = urun_getir_barkod(db, barkod)
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    for alan, deger in degisiklik.dict(exclude_unset=True).items():
        setattr(urun, alan, deger)
    db.commit()
    db.refresh(urun)
    return urun


def urun_sil(db: Session, barkod: str):
    urun = urun_getir_barkod(db, barkod)
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    db.delete(urun)
    db.commit()
    return {"mesaj": "Ürün silindi"}


def hareket_olustur(db: Session, hareket: schemas.HareketOlustur):
    urun = urun_getir_barkod(db, hareket.barkod)
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı, önce ürünü ekleyin")

    if hareket.tip == models.HareketTipi.cikis and urun.miktar < hareket.miktar:
        raise HTTPException(status_code=400, detail="Yetersiz stok")

    if hareket.tip == models.HareketTipi.giris:
        urun.miktar += hareket.miktar
    else:
        urun.miktar -= hareket.miktar

    yeni_hareket = models.StokHareketi(
        urun_id=urun.id,
        tip=hareket.tip,
        miktar=hareket.miktar,
        **{"not": hareket.not_},
    )
    db.add(yeni_hareket)
    db.commit()
    db.refresh(yeni_hareket)
    return yeni_hareket


def hareket_listele(db: Session, limit: int = 100):
    return (
        db.query(models.StokHareketi)
        .order_by(models.StokHareketi.tarih.desc())
        .limit(limit)
        .all()
    )


def urun_toplu_ekle_veya_guncelle(db: Session, satirlar: list):
    """
    satirlar: [{barkod, ad, birim, miktar, min_stok}, ...] şeklinde liste.
    Barkod zaten varsa günceller (miktarı YERİNE koyar, üstüne eklemez),
    yoksa yeni ürün olarak ekler.
    Dönüş: {eklenen, guncellenen, hatalar: [{satir, mesaj}]}
    """
    eklenen = 0
    guncellenen = 0
    hatalar = []

    for i, satir in enumerate(satirlar, start=2):  # 2: Excel'de 1. satır başlık
        barkod = str(satir.get("barkod", "")).strip()
        ad = str(satir.get("ad", "")).strip()

        if not barkod or not ad or barkod == "nan" or ad == "nan":
            hatalar.append({"satir": i, "mesaj": "Barkod veya ürün adı boş, atlandı"})
            continue

        try:
            birim = str(satir.get("birim") or "adet").strip()
            miktar = float(satir.get("miktar") or 0)
            min_stok = float(satir.get("min_stok") or 0)
        except (ValueError, TypeError):
            hatalar.append({"satir": i, "mesaj": "Miktar/min_stok sayı olmalı, atlandı"})
            continue

        mevcut = urun_getir_barkod(db, barkod)
        if mevcut:
            mevcut.ad = ad
            mevcut.birim = birim
            mevcut.miktar = miktar
            mevcut.min_stok = min_stok
            guncellenen += 1
        else:
            yeni_urun = models.Urun(
                barkod=barkod, ad=ad, birim=birim, miktar=miktar, min_stok=min_stok
            )
            db.add(yeni_urun)
            eklenen += 1

    db.commit()
    return {"eklenen": eklenen, "guncellenen": guncellenen, "hatalar": hatalar}
