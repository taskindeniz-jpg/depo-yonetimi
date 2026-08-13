# Depo Yönetim Sistemi — V1

Cep telefonu / ürün stok takibi için basit depo yönetim sistemi.
FastAPI backend + PostgreSQL + tek sayfalık web arayüzü.

## Neler var?

- Barkod / ürün kodu ile stok sorgulama
- Stok giriş / çıkış işlemleri
- Tüm hareketlerin (giriş/çıkış) kaydı
- Yeni ürün ekleme
- Basit, telefonda da rahat kullanılabilen web arayüzü

## Yerel bilgisayarda çalıştırma (Docker ile)

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) kurulu olmalı.
2. Bu klasörde bir terminal aç.
3. Şu komutu çalıştır:

   ```
   docker compose up --build
   ```

4. Tarayıcıdan aç: http://localhost:8080

Durdurmak için terminalde `Ctrl + C`, tamamen kapatmak için:
```
docker compose down
```

## Railway'e (bulut) kurulum

1. https://railway.app adresinde hesap aç (GitHub ile giriş kolay).
2. "New Project" → "Deploy from GitHub repo" (bu klasörü önce bir GitHub reposuna yükle) **veya**
   Railway CLI ile doğrudan bu klasörden deploy et.
3. Railway panelinde "New" → "Database" → "Add PostgreSQL" ile bir veritabanı ekle.
   Railway otomatik olarak bir `DATABASE_URL` değişkeni oluşturur.
4. Backend servisinin **Variables** sekmesinde `DATABASE_URL` değişkeninin
   Postgres eklentisinden gelen değere bağlı olduğunu kontrol et
   (Railway genelde bunu otomatik eşler, "Add Reference" ile bağlayabilirsin).
5. Deploy tamamlanınca Railway sana `https://xxxx.up.railway.app` gibi bir adres verir.
6. O adresi telefonda Chrome'da aç, menüden **"Ana ekrana ekle"** de.

## API uç noktaları (özet)

| Metod | Yol | Açıklama |
|---|---|---|
| GET | /api/urunler | Tüm ürünleri listele |
| GET | /api/urunler/{barkod} | Barkoda göre ürün sorgula |
| POST | /api/urunler | Yeni ürün ekle |
| PUT | /api/urunler/{barkod} | Ürün bilgisi güncelle |
| DELETE | /api/urunler/{barkod} | Ürün sil |
| POST | /api/hareketler | Stok giriş/çıkış hareketi oluştur |
| GET | /api/hareketler | Son hareketleri listele |

## Sırada ne var? (V2 planı)

- Telefon kamerasıyla QR/barkod okuma (tarayıcı üzerinden, ek uygulama gerekmez)
- Kullanıcı girişi / yetkilendirme
- Excel'den toplu ürün aktarımı
- Sayım (envanter) ekranı
- QR etiket üretimi ve yazdırma
- Düzgün yönetim / rapor paneli
