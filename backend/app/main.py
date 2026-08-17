import os
import io
import time
import httpx
from collections import defaultdict, deque
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
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

# Rol hiyerarşisi: sayı büyüdükçe yetki artar
ROL_SEVIYESI = {
    "goruntuleyici": 0,
    "personel": 1,
    "depo_muduru": 2,
    "super_admin": 3,
}


# ---------------- Basit hız sınırlama (rate limiting) ----------------
# Aynı IP'den kısa sürede çok fazla giriş denemesi yapılmasını engeller
# (brute-force koruması). Harici kütüphane gerektirmez.
_giris_denemeleri = defaultdict(deque)
GIRIS_LIMIT = 8          # pencere içinde izin verilen deneme sayısı
GIRIS_PENCERE_SANIYE = 60


def _rate_limit_kontrol(ip: str):
    simdi = time.time()
    denemeler = _giris_denemeleri[ip]
    while denemeler and simdi - denemeler[0] > GIRIS_PENCERE_SANIYE:
        denemeler.popleft()
    if len(denemeler) >= GIRIS_LIMIT:
        raise HTTPException(status_code=429, detail="Çok fazla deneme yapıldı, biraz sonra tekrar dene")
    denemeler.append(simdi)


def _istemci_ip(request: Request) -> str:
    ileri = request.headers.get("x-forwarded-for")
    if ileri:
        return ileri.split(",")[0].strip()
    return request.client.host if request.client else "bilinmiyor"


# ---------------- Kimlik ve yetki bağımlılıkları ----------------

def gecerli_kullanici(kimlik: HTTPAuthorizationCredentials = Depends(guvenlik), db: Session = Depends(get_db)):
    veri = auth.token_dogrula(kimlik.credentials)
    if not veri:
        raise HTTPException(status_code=401, detail="Oturum geçersiz veya süresi dolmuş, tekrar giriş yap")
    kullanici = crud.kullanici_getir(db, veri.get("kullanici_adi"))
    if not kullanici or not kullanici.aktif:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı veya devre dışı")
    return kullanici


def rol_gerekli(min_rol: str):
    def kontrol(kullanici: models.Kullanici = Depends(gecerli_kullanici)):
        if ROL_SEVIYESI.get(kullanici.rol.value, 0) < ROL_SEVIYESI.get(min_rol, 99):
            raise HTTPException(status_code=403, detail="Bu işlem için yetkin yok")
        return kullanici
    return kontrol


@app.on_event("startup")
def baslangicta_admin_olustur():
    db = next(get_db())
    try:
        mevcut = db.query(models.Kullanici).first()
        if not mevcut:
            varsayilan_ad = os.getenv("ADMIN_KULLANICI_ADI", "admin")
            varsayilan_sifre = os.getenv("ADMIN_SIFRE", "admin123")
            crud.kullanici_olustur(db, varsayilan_ad, auth.sifre_hashle(varsayilan_sifre), rol="super_admin")
    finally:
        db.close()


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def anasayfa():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# ---------------- Kimlik doğrulama ----------------

@app.post("/api/auth/giris", response_model=schemas.TokenCikti)
def giris_yap(istek: schemas.GirisIstek, request: Request, db: Session = Depends(get_db)):
    ip = _istemci_ip(request)
    _rate_limit_kontrol(ip)

    kullanici = crud.kullanici_getir(db, istek.kullanici_adi)
    if not kullanici or not kullanici.aktif or not auth.sifre_dogrula(istek.sifre, kullanici.sifre_hash):
        crud.denetim_kaydet(db, istek.kullanici_adi, "giris_basarisiz", ip_adresi=ip)
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı")

    token = auth.token_olustur(kullanici.kullanici_adi, kullanici.rol.value)
    crud.denetim_kaydet(db, kullanici.kullanici_adi, "giris_basarili", ip_adresi=ip)
    return {
        "access_token": token,
        "token_type": "bearer",
        "kullanici_adi": kullanici.kullanici_adi,
        "rol": kullanici.rol.value,
    }


@app.post("/api/auth/sifre-degistir")
def sifre_degistir(
    istek: schemas.SifreDegistirIstek,
    db: Session = Depends(get_db),
    kullanici: models.Kullanici = Depends(gecerli_kullanici),
):
    if not auth.sifre_dogrula(istek.eski_sifre, kullanici.sifre_hash):
        raise HTTPException(status_code=401, detail="Eski şifre hatalı")
    if len(istek.yeni_sifre) < 6:
        raise HTTPException(status_code=400, detail="Yeni şifre en az 6 karakter olmalı")
    crud.kullanici_sifre_guncelle(db, kullanici, auth.sifre_hashle(istek.yeni_sifre))
    crud.denetim_kaydet(db, kullanici.kullanici_adi, "sifre_degistirildi")
    return {"mesaj": "Şifre güncellendi"}


# ---------------- Kullanıcı yönetimi (sadece super_admin) ----------------

@app.get("/api/kullanicilar", response_model=List[schemas.KullaniciCikti])
def kullanicilari_listele(db: Session = Depends(get_db), _: models.Kullanici = Depends(rol_gerekli("super_admin"))):
    return crud.kullanicilari_listele(db)


@app.post("/api/kullanicilar", response_model=schemas.KullaniciCikti)
def kullanici_ekle(
    istek: schemas.KullaniciOlustur,
    db: Session = Depends(get_db),
    aktif_kullanici: models.Kullanici = Depends(rol_gerekli("super_admin")),
):
    if crud.kullanici_getir(db, istek.kullanici_adi):
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten var")
    if len(istek.sifre) < 6:
        raise HTTPException(status_code=400, detail="Şifre en az 6 karakter olmalı")
    yeni = crud.kullanici_olustur(db, istek.kullanici_adi, auth.sifre_hashle(istek.sifre), rol=istek.rol.value)
    crud.denetim_kaydet(db, aktif_kullanici.kullanici_adi, "kullanici_olustur", "kullanici", yeni.kullanici_adi)
    return yeni


# ---------------- Ürünler ----------------
# Görüntüleme: herkes (goruntuleyici dahil). Ekleme/düzenleme: personel ve üstü.
# Silme: depo_muduru ve üstü.

@app.get("/api/urunler", response_model=List[schemas.UrunCikti])
def urunleri_listele(db: Session = Depends(get_db), _: models.Kullanici = Depends(gecerli_kullanici)):
    return crud.urun_listele(db)


@app.get("/api/urunler/silinmis", response_model=List[schemas.UrunCikti])
def silinmis_urunleri_listele(
    db: Session = Depends(get_db),
    _: models.Kullanici = Depends(rol_gerekli("depo_muduru")),
):
    tumu = crud.urun_listele(db, silinmisleri_dahil_et=True)
    return [u for u in tumu if u.silindi]


@app.get("/api/urunler/{barkod}", response_model=schemas.UrunCikti)
def urun_sorgula(barkod: str, db: Session = Depends(get_db), _: models.Kullanici = Depends(gecerli_kullanici)):
    urun = crud.urun_getir_barkod(db, barkod)
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    return urun


@app.get("/api/barkod-oner/{barkod}")
async def barkod_oner(barkod: str, _: models.Kullanici = Depends(gecerli_kullanici)):
    """
    Sistemde kayıtlı olmayan bir barkod okutulduğunda, ürün adını otomatik
    doldurmaya yardımcı olmak için global bir barkod veritabanını (Open Food
    Facts, ücretsiz ve anahtar gerektirmez) sorgular. Sadece bir öneri
    sunar; bulunamazsa kullanıcı elle girer, sistem çökmez.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            yanit = await client.get(
                f"https://world.openfoodfacts.org/api/v2/product/{barkod}.json"
            )
        if yanit.status_code != 200:
            return {"bulundu": False}

        veri = yanit.json()
        if veri.get("status") != 1:
            return {"bulundu": False}

        urun = veri.get("product", {})
        ad_parcalari = [urun.get("product_name"), urun.get("brands")]
        ad = " - ".join([p for p in ad_parcalari if p])

        if not ad:
            return {"bulundu": False}

        birim_onerisi = "adet"
        miktar_metni = (urun.get("quantity") or "").lower()
        if "kg" in miktar_metni:
            birim_onerisi = "kg"
        elif "ml" in miktar_metni or "l" in miktar_metni:
            birim_onerisi = "litre"
        elif "g" in miktar_metni:
            birim_onerisi = "gr"

        return {"bulundu": True, "ad": ad[:200], "birim_onerisi": birim_onerisi}
    except Exception:
        # Dış servise ulaşılamazsa (zaman aşımı, ağ sorunu vb.) sessizce
        # "bulunamadı" dön; bu özellik olmadan da ürün elle eklenebilmeli.
        return {"bulundu": False}


@app.post("/api/urunler", response_model=schemas.UrunCikti)
def urun_ekle(
    urun: schemas.UrunOlustur,
    db: Session = Depends(get_db),
    kullanici: models.Kullanici = Depends(rol_gerekli("personel")),
):
    yeni = crud.urun_olustur(db, urun)
    crud.denetim_kaydet(db, kullanici.kullanici_adi, "urun_olustur", "urun", yeni.barkod, yeni_deger=urun.dict())
    return yeni


@app.put("/api/urunler/{barkod}", response_model=schemas.UrunCikti)
def urun_duzenle(
    barkod: str,
    degisiklik: schemas.UrunGuncelle,
    db: Session = Depends(get_db),
    kullanici: models.Kullanici = Depends(rol_gerekli("personel")),
):
    guncel = crud.urun_guncelle(db, barkod, degisiklik)
    crud.denetim_kaydet(db, kullanici.kullanici_adi, "urun_guncelle", "urun", barkod, yeni_deger=degisiklik.dict(exclude_unset=True))
    return guncel


@app.delete("/api/urunler/{barkod}")
def urun_kaldir(
    barkod: str,
    db: Session = Depends(get_db),
    kullanici: models.Kullanici = Depends(rol_gerekli("depo_muduru")),
):
    sonuc = crud.urun_sil(db, barkod)
    crud.denetim_kaydet(db, kullanici.kullanici_adi, "urun_sil", "urun", barkod)
    return sonuc


@app.post("/api/urunler/{barkod}/geri-yukle", response_model=schemas.UrunCikti)
def urun_geri_yukle(
    barkod: str,
    db: Session = Depends(get_db),
    kullanici: models.Kullanici = Depends(rol_gerekli("depo_muduru")),
):
    urun = crud.urun_geri_yukle(db, barkod)
    crud.denetim_kaydet(db, kullanici.kullanici_adi, "urun_geri_yukle", "urun", barkod)
    return urun


# ---------------- Stok hareketleri ----------------

@app.post("/api/hareketler", response_model=schemas.HareketCikti)
def hareket_ekle(
    hareket: schemas.HareketOlustur,
    db: Session = Depends(get_db),
    kullanici: models.Kullanici = Depends(rol_gerekli("personel")),
):
    return crud.hareket_olustur(db, hareket, kullanici)


@app.get("/api/hareketler", response_model=List[schemas.HareketCikti])
def hareketleri_listele(
    limit: int = 100,
    barkod: Optional[str] = None,
    db: Session = Depends(get_db),
    _: models.Kullanici = Depends(gecerli_kullanici),
):
    return crud.hareket_listele(db, limit, barkod)


# ---------------- Denetim kayıtları (audit log) ----------------

@app.get("/api/denetim-kayitlari", response_model=List[schemas.DenetimKaydiCikti])
def denetim_kayitlarini_listele(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: models.Kullanici = Depends(rol_gerekli("depo_muduru")),
):
    return crud.denetim_kayitlarini_listele(db, limit)


# ---------------- Excel toplu aktarım ----------------

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
async def urunleri_toplu_yukle(
    dosya: UploadFile = File(...),
    db: Session = Depends(get_db),
    kullanici: models.Kullanici = Depends(rol_gerekli("personel")),
):
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
    crud.denetim_kaydet(
        db, kullanici.kullanici_adi, "excel_toplu_yukle",
        yeni_deger={"eklenen": sonuc["eklenen"], "guncellenen": sonuc["guncellenen"]},
    )
    return sonuc


@app.get("/api/saglik")
def saglik_kontrolu():
    return {"durum": "calisiyor"}
