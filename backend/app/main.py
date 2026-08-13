import os
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas, crud
from .database import engine, get_db, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Depo Yönetim Sistemi")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def anasayfa():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/urunler", response_model=List[schemas.UrunCikti])
def urunleri_listele(db: Session = Depends(get_db)):
    return crud.urun_listele(db)


@app.get("/api/urunler/{barkod}", response_model=schemas.UrunCikti)
def urun_sorgula(barkod: str, db: Session = Depends(get_db)):
    urun = crud.urun_getir_barkod(db, barkod)
    if not urun:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    return urun


@app.post("/api/urunler", response_model=schemas.UrunCikti)
def urun_ekle(urun: schemas.UrunOlustur, db: Session = Depends(get_db)):
    return crud.urun_olustur(db, urun)


@app.put("/api/urunler/{barkod}", response_model=schemas.UrunCikti)
def urun_duzenle(barkod: str, degisiklik: schemas.UrunGuncelle, db: Session = Depends(get_db)):
    return crud.urun_guncelle(db, barkod, degisiklik)


@app.delete("/api/urunler/{barkod}")
def urun_kaldir(barkod: str, db: Session = Depends(get_db)):
    return crud.urun_sil(db, barkod)


@app.post("/api/hareketler", response_model=schemas.HareketCikti)
def hareket_ekle(hareket: schemas.HareketOlustur, db: Session = Depends(get_db)):
    return crud.hareket_olustur(db, hareket)


@app.get("/api/hareketler", response_model=List[schemas.HareketCikti])
def hareketleri_listele(limit: int = 100, db: Session = Depends(get_db)):
    return crud.hareket_listele(db, limit)


@app.get("/api/saglik")
def saglik_kontrolu():
    return {"durum": "calisiyor"}
