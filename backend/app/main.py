import os
import io
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import pandas as pd

from . import models, schemas, crud, auth
from .database import engine, get_db, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Depo Yönetim Sistemi")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

guvenlik = HTTPBearer()


def gecerli_kullanici(kimlik: HTTPAuthorizationCredentials = Depends(guvenlik)):
    kullanici_adi = auth.token_dogrula(kimlik.credentials)
    if not kullanici_adi:
        raise HTTPException(status_code=401, detail="Oturum geçersiz veya süresi dolmuş, tekrar giriş yap")
    return kullanici_adi


@app.on_event("startup")
def baslangicta_admin_olustur():
    db = next(get_db())
    try:
        mevcut = db.query(models.Kullanici).first()
        if not mevcut:
            varsayilan_ad = os.getenv("ADMIN_KULLANICI_ADI", "admin")
            varsayilan_sifre = os.getenv("ADMIN_SIFRE", "admin123")
            crud.kullanici_olustur(db, varsayilan_ad, auth.sifre_hashle(varsayilan_sifre))
    finally:
        db.close()


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def anasayfa():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/auth/giris", response_model=schemas.TokenCikti)
def giris_yap(istek: schemas.GirisIstek, db: Session = Depends(get_db)):
    kullanici = crud.kullanici_getir(db, istek.kullanici_adi)
    if not kullanici or not auth.sifre_dogrula(istek.sifre, kullanici.sifre_hash):
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı")
    token = auth.token_olustur(kullanici.kullanici_adi)
    return {"access_token": token, "token_type": "bearer", "kullanici_adi": kullanici.kullanici_adi}


@app.get("/api/urunler", response_model=List[schemas.UrunCikti])
def urunleri_listele(db: Session = Depends(get_db), _: str = Depends(gecerli_kullanici)):
    return crud.urun_listele(db)


@app.get("/api/urunler/{barkod}", response_model=schemas.UrunCikti)
def urun_sorgula(barkod: str, db: Session = Depends(get_db), _: str = Depends(gecerli_kullanici)):
    urun = crud.urun_getir_barkod(db, barkod)
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    return urun


@app.post("/api/urunler", response_model=schemas.UrunCikti)
def urun_ekle(urun: schemas.UrunOlustur, db: Session = Depends(get_db), _: str = Depends(gecerli_kullanici)):
    return crud.urun_olustur(db, urun)


@app.put("/api/urunler/{barkod}", response_model=schemas.UrunCikti)
def urun_duzenle(barkod: str, degisiklik: schemas.UrunGuncelle, db: Session = Depends(get_db), _: str = Depends(gecerli_kullanici)):
    return crud.urun_guncelle(db, barkod, degisiklik)


@app.delete("/api/urunler/{barkod}")
def urun_kaldir(barkod: str, db: Session = Depends(get_db), _: str = Depends(gecerli_kullanici)):
    return crud.urun_sil(db, barkod)


@app.post("/api/hareketler", response_model=schemas.HareketCikti)
def hareket_ekle(hareket: schemas.HareketOlustur, db: Session = Depends(get_db), _: str = Depends(gecerli_kullanici)):
    return crud.hareket_olustur(db, hareket)


@app.get("/api/hareketler", response_model=List[schemas.HareketCikti])
def hareketleri_listele(limit: int = 100, db: Session = Depends(get_db), _: str = Depends(gecerli_kullanici)):
    return crud.hareket_listele(db, limit)


@app.get("/api/saglik")
def saglik_kontrolu():
    return {"durum": "calisiyor"}


BEKLENEN_SUTUNLAR = {
    "barkod": ["barkod", "barcode", "kod", "ürün kodu", "urun kodu"],
    "ad": ["ad", "ürün adı", "urun adi", "isim", "ürün", "urun"],
    "birim": ["birim", "unit"],
    "miktar": ["miktar", "adet", "stok", "quantity"],
    "min_stok": ["min_stok", "min stok", "minimum stok", "kritik stok"],
}


def _sutun_bul(kolonlar, adaylar):
    kolonlar_kucuk = {str(k).strip().lower(): k for k in kolonlar}
    for aday in adaylar:
        if aday in kolonlar_kucuk:
            return kolonlar_kucuk[aday]
    return None


@app.post("/api/urunler/toplu-yukle")
async def urunleri_toplu_yukle(dosya: UploadFile = File(...), db: Session = Depends(get_db), _: str = Depends(gecerli_kullanici)):
    if not dosya.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Sadece .xlsx, .xls veya .csv dosyası yükleyebilirsin")

    icerik = await dosya.read()
    try:
        if dosya.filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(icerik))
        else:
            df = pd.read_excel(io.BytesIO(icerik))
    except Exception as hata:
        raise HTTPException(status_code=400, detail=f"Dosya okunamadı: {hata}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Dosya boş görünüyor")

    kolonlar = list(df.columns)
    eslenen = {}
    for anahtar, adaylar in BEKLENEN_SUTUNLAR.items():
        bulunan = _sutun_bul(kolonlar, adaylar)
        if bulunan:
            eslenen[anahtar] = bulunan

    if "barkod" not in eslenen or "ad" not in eslenen:
        raise HTTPException(
            status_code=400,
            detail=(
                "Dosyada 'barkod' ve 'ad' (ürün adı) sütunlarını bulamadım. "
                f"Bulunan sütunlar: {kolonlar}. "
                "Lütfen sütun başlıklarını 'barkod' ve 'ad' olarak düzenle."
            ),
        )

    satirlar = []
    for _, satir in df.iterrows():
        yeni_satir = {}
        for anahtar in BEKLENEN_SUTUNLAR:
            if anahtar in eslenen:
                yeni_satir[anahtar] = satir[eslenen[anahtar]]
            else:
                yeni_satir[anahtar] = None
        satirlar.append(yeni_satir)

    sonuc = crud.urun_toplu_ekle_veya_guncelle(db, satirlar)
    return sonuc
