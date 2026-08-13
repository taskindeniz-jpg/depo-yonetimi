from sqlalchemy.orm import Session
from fastapi import HTTPException

from . import models, schemas


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
