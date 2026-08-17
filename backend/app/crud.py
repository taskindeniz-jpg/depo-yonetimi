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


# ---------- Mal Kabul ----------

def mal_kabul_olustur(db: Session, veri: schemas.MalKabulOlustur, kullanici: models.Kullanici):
    if not veri.kalemler:
        raise HTTPException(status_code=400, detail="En az bir ürün satırı eklemelisin")

    baslik = models.MalKabul(
        tedarikci=veri.tedarikci,
        irsaliye_no=veri.irsaliye_no,
        gelis_tarihi=veri.gelis_tarihi,
        kabul_eden_id=kullanici.id,
        kabul_eden_adi_metin=kullanici.kullanici_adi,
        **{"not": veri.not_},
    )
    db.add(baslik)
    db.flush()  # baslik.id'yi almak için, henüz commit etmeden

    for kalem in veri.kalemler:
        urun = (
            db.query(models.Urun)
            .filter(models.Urun.barkod == kalem.barkod, models.Urun.silindi == False)  # noqa: E712
            .with_for_update()
            .first()
        )
        if not urun:
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"'{kalem.barkod}' barkodlu ürün sistemde kayıtlı değil. Önce ürünü ekle.",
            )

        onceki_miktar = urun.miktar
        urun.miktar += kalem.gelen_miktar

        db.add(models.MalKabulKalemi(
            mal_kabul_id=baslik.id,
            urun_id=urun.id,
            beklenen_miktar=kalem.beklenen_miktar,
            gelen_miktar=kalem.gelen_miktar,
            fark_aciklamasi=kalem.fark_aciklamasi,
        ))

        db.add(models.StokHareketi(
            urun_id=urun.id,
            tip=models.HareketTipi.giris,
            miktar=kalem.gelen_miktar,
            onceki_miktar=onceki_miktar,
            sonraki_miktar=urun.miktar,
            neden="mal_kabul",
            kaynak_tip="mal_kabul",
            kaynak_id=baslik.id,
            kullanici_id=kullanici.id,
            kullanici_adi_metin=kullanici.kullanici_adi,
        ))

    db.commit()
    db.refresh(baslik)
    return baslik


def mal_kabul_listele(db: Session, limit: int = 100):
    return (
        db.query(models.MalKabul)
        .order_by(models.MalKabul.olusturma_tarihi.desc())
        .limit(limit)
        .all()
    )


def mal_kabul_getir(db: Session, mal_kabul_id: int):
    kayit = db.query(models.MalKabul).filter(models.MalKabul.id == mal_kabul_id).first()
    if not kayit:
        raise HTTPException(status_code=404, detail="Mal kabul kaydı bulunamadı")
    return kayit


# ---------- Sevkiyat ----------

def sevkiyat_olustur(db: Session, veri: schemas.SevkiyatOlustur, kullanici: models.Kullanici):
    if not veri.kalemler:
        raise HTTPException(status_code=400, detail="En az bir ürün satırı eklemelisin")

    baslik = models.Sevkiyat(
        musteri=veri.musteri,
        sevk_no=veri.sevk_no,
        sevk_tarihi=veri.sevk_tarihi,
        hazirlayan_id=kullanici.id,
        hazirlayan_adi_metin=kullanici.kullanici_adi,
        kontrol_eden_adi_metin=veri.kontrol_eden_adi_metin,
        **{"not": veri.not_},
    )
    db.add(baslik)
    db.flush()

    # Önce tüm ürünleri kilitleyip stok yeterliliğini kontrol ediyoruz;
    # herhangi biri yetersizse tüm sevkiyat iptal olur (ya hep ya hiç).
    kilitli_urunler = {}
    for kalem in veri.kalemler:
        urun = (
            db.query(models.Urun)
            .filter(models.Urun.barkod == kalem.barkod, models.Urun.silindi == False)  # noqa: E712
            .with_for_update()
            .first()
        )
        if not urun:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"'{kalem.barkod}' barkodlu ürün bulunamadı")
        if urun.miktar < kalem.miktar:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"'{urun.ad}' için yetersiz stok (mevcut: {urun.miktar}, istenen: {kalem.miktar})",
            )
        kilitli_urunler[kalem.barkod] = urun

    for kalem in veri.kalemler:
        urun = kilitli_urunler[kalem.barkod]
        onceki_miktar = urun.miktar
        urun.miktar -= kalem.miktar

        db.add(models.SevkiyatKalemi(
            sevkiyat_id=baslik.id,
            urun_id=urun.id,
            miktar=kalem.miktar,
        ))

        db.add(models.StokHareketi(
            urun_id=urun.id,
            tip=models.HareketTipi.cikis,
            miktar=kalem.miktar,
            onceki_miktar=onceki_miktar,
            sonraki_miktar=urun.miktar,
            neden="sevkiyat",
            kaynak_tip="sevkiyat",
            kaynak_id=baslik.id,
            kullanici_id=kullanici.id,
            kullanici_adi_metin=kullanici.kullanici_adi,
        ))

    db.commit()
    db.refresh(baslik)
    return baslik


def sevkiyat_listele(db: Session, limit: int = 100):
    return (
        db.query(models.Sevkiyat)
        .order_by(models.Sevkiyat.olusturma_tarihi.desc())
        .limit(limit)
        .all()
    )


def sevkiyat_getir(db: Session, sevkiyat_id: int):
    kayit = db.query(models.Sevkiyat).filter(models.Sevkiyat.id == sevkiyat_id).first()
    if not kayit:
        raise HTTPException(status_code=404, detail="Sevkiyat kaydı bulunamadı")
    return kayit


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
