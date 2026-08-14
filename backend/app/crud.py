import json
from sqlalchemy.orm import Session
from fastapi import HTTPException

from . import models, schemas


# ---------- Kullanıcı ----------

def kullanici_getir(db: Session, kullanici_adi: str):
    return db.query(models.Kullanici).filter(models.Kullanici.kullanici_adi == kullanici_adi).first()


def kullanici_olustur(db: Session, kullanici_adi: str, sifre_hash: str, rol: str = "personel"):
    kullanici = models.Kullanici(kullanici_adi=kullanici_adi, sifre_hash=sifre_hash, rol=rol)
    db.add(kullanici)
    db.commit()
    db.refresh(kullanici)
    return kullanici


def kullanicilari_listele(db: Session):
    return db.query(models.Kullanici).order_by(models.Kullanici.kullanici_adi).all()


def kullanici_sifre_guncelle(db: Session, kullanici: models.Kullanici, yeni_hash: str):
    kullanici.sifre_hash = yeni_hash
    db.commit()


# ---------- Denetim kaydı (audit log) ----------

def denetim_kaydet(
    db: Session,
    kullanici_adi: str,
    islem: str,
    hedef_tip: str = None,
    hedef_id: str = None,
    eski_deger=None,
    yeni_deger=None,
    ip_adresi: str = None,
):
    kayit = models.DenetimKaydi(
        kullanici_adi=kullanici_adi,
        islem=islem,
        hedef_tip=hedef_tip,
        hedef_id=str(hedef_id) if hedef_id is not None else None,
        eski_deger=json.dumps(eski_deger, ensure_ascii=False, default=str) if eski_deger is not None else None,
        yeni_deger=json.dumps(yeni_deger, ensure_ascii=False, default=str) if yeni_deger is not None else None,
        ip_adresi=ip_adresi,
    )
    db.add(kayit)
    db.commit()


def denetim_kayitlarini_listele(db: Session, limit: int = 200):
    return (
        db.query(models.DenetimKaydi)
        .order_by(models.DenetimKaydi.tarih.desc())
        .limit(limit)
        .all()
    )


# ---------- Ürün ----------

def urun_getir_barkod(db: Session, barkod: str, silinmisleri_dahil_et: bool = False):
    sorgu = db.query(models.Urun).filter(models.Urun.barkod == barkod)
    if not silinmisleri_dahil_et:
        sorgu = sorgu.filter(models.Urun.silindi == False)  # noqa: E712
    return sorgu.first()


def urun_listele(db: Session, silinmisleri_dahil_et: bool = False):
    sorgu = db.query(models.Urun)
    if not silinmisleri_dahil_et:
        sorgu = sorgu.filter(models.Urun.silindi == False)  # noqa: E712
    return sorgu.order_by(models.Urun.ad).all()


def urun_olustur(db: Session, urun: schemas.UrunOlustur):
    mevcut = urun_getir_barkod(db, urun.barkod, silinmisleri_dahil_et=True)
    if mevcut:
        if mevcut.silindi:
            raise HTTPException(
                status_code=400,
                detail="Bu barkod daha önce silinmiş bir ürüne ait. Silinen ürünü geri yükleyebilirsin.",
            )
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
    """Gerçekten silmez, işaretler (soft delete). Geçmiş hareketler korunur."""
    from sqlalchemy.sql import func as sqlfunc

    urun = urun_getir_barkod(db, barkod)
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    urun.silindi = True
    urun.silinme_tarihi = sqlfunc.now()
    db.commit()
    return {"mesaj": "Ürün silindi (geri yüklenebilir)"}


def urun_geri_yukle(db: Session, barkod: str):
    urun = urun_getir_barkod(db, barkod, silinmisleri_dahil_et=True)
    if not urun or not urun.silindi:
        raise HTTPException(status_code=404, detail="Silinmiş ürün bulunamadı")
    urun.silindi = False
    urun.silinme_tarihi = None
    db.commit()
    db.refresh(urun)
    return urun


# ---------- Stok hareketi (eşzamanlılık güvenli) ----------

def hareket_olustur(db: Session, hareket: schemas.HareketOlustur, kullanici: models.Kullanici):
    # Satırı kilitleyerek oku: aynı anda iki kişi aynı ürüne hareket
    # girerse, ikinci istek birincinin işlemi bitmesini bekler. Böylece
    # "önceki_miktar" yanlış hesaplanıp stok hatalı güncellenmez.
    urun = (
        db.query(models.Urun)
        .filter(models.Urun.barkod == hareket.barkod, models.Urun.silindi == False)  # noqa: E712
        .with_for_update()
        .first()
    )
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı, önce ürünü ekleyin")

    onceki_miktar = urun.miktar

    if hareket.tip == models.HareketTipi.cikis and urun.miktar < hareket.miktar:
        db.rollback()
        raise HTTPException(status_code=400, detail="Yetersiz stok")

    if hareket.tip == models.HareketTipi.giris:
        urun.miktar += hareket.miktar
    else:
        urun.miktar -= hareket.miktar

    yeni_hareket = models.StokHareketi(
        urun_id=urun.id,
        tip=hareket.tip,
        miktar=hareket.miktar,
        onceki_miktar=onceki_miktar,
        sonraki_miktar=urun.miktar,
        neden=hareket.neden,
        kullanici_id=kullanici.id if kullanici else None,
        kullanici_adi_metin=kullanici.kullanici_adi if kullanici else None,
        **{"not": hareket.not_},
    )
    db.add(yeni_hareket)
    db.commit()
    db.refresh(yeni_hareket)
    return yeni_hareket


def hareket_listele(db: Session, limit: int = 100, barkod: str = None):
    sorgu = db.query(models.StokHareketi)
    if barkod:
        sorgu = sorgu.join(models.Urun).filter(models.Urun.barkod == barkod)
    return sorgu.order_by(models.StokHareketi.tarih.desc()).limit(limit).all()


# ---------- Excel toplu aktarım ----------

def urun_toplu_ekle_veya_guncelle(db: Session, satirlar: list):
    eklenen = 0
    guncellenen = 0
    hatalar = []

    for i, satir in enumerate(satirlar, start=2):
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

        mevcut = urun_getir_barkod(db, barkod, silinmisleri_dahil_et=True)
        if mevcut:
            if mevcut.silindi:
                hatalar.append({"satir": i, "mesaj": f"Barkod {barkod} silinmiş bir ürüne ait, atlandı"})
                continue
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
