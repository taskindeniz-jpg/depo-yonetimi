let mevcutBarkod = null;

// ---- Kimlik doğrulama ----
function tokenGetir() {
  return localStorage.getItem("depo_token");
}

function tokenKaydet(token) {
  localStorage.setItem("depo_token", token);
}

function tokenSil() {
  localStorage.removeItem("depo_token");
}

function yetkiliBasliklar(ekBaslik = {}) {
  return { Authorization: `Bearer ${tokenGetir()}`, ...ekBaslik };
}

async function girisYap() {
  const kullaniciAdi = document.getElementById("girisKullaniciAdi").value.trim();
  const sifre = document.getElementById("girisSifre").value;
  const hataDiv = document.getElementById("girisHata");
  hataDiv.textContent = "";

  if (!kullaniciAdi || !sifre) {
    hataDiv.textContent = "Kullanıcı adı ve şifre gerekli";
    return;
  }

  try {
    const yanit = await fetch("/api/auth/giris", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kullanici_adi: kullaniciAdi, sifre }),
    });

    if (!yanit.ok) {
      const hata = await yanit.json();
      hataDiv.textContent = hata.detail || "Giriş başarısız";
      return;
    }

    const veri = await yanit.json();
    tokenKaydet(veri.access_token);
    girisEkraniniGizle();
    await sayfaVerileriniYukle();
  } catch (hata) {
    hataDiv.textContent = "Bağlantı hatası: " + hata;
  }
}

function cikisYap() {
  tokenSil();
  document.getElementById("girisEkrani").style.display = "flex";
  document.getElementById("anaIcerik").style.display = "none";
  document.getElementById("girisKullaniciAdi").value = "";
  document.getElementById("girisSifre").value = "";
}

function girisEkraniniGizle() {
  document.getElementById("girisEkrani").style.display = "none";
  document.getElementById("anaIcerik").style.display = "block";
}

async function sayfaVerileriniYukle() {
  await urunleriListele();
  await hareketleriListele();
}

// 401 (oturum geçersiz) hatası gelirse otomatik olarak giriş ekranına dön
function oturumKontrolEt(yanit) {
  if (yanit.status === 401) {
    cikisYap();
    return true;
  }
  return false;
}

// ---- Ürün işlemleri ----
async function urunSorgula() {
  const barkod = document.getElementById("barkodGirisi").value.trim();
  if (!barkod) return;

  const sonucKutu = document.getElementById("urunSonuc");
  const hareketKarti = document.getElementById("hareketKarti");

  try {
    const yanit = await fetch(`/api/urunler/${encodeURIComponent(barkod)}`, {
      headers: yetkiliBasliklar(),
    });
    if (oturumKontrolEt(yanit)) return;

    if (!yanit.ok) {
      sonucKutu.style.display = "block";
      sonucKutu.innerHTML = `<div class="uyari">Ürün bulunamadı. Aşağıdan yeni ürün olarak ekleyebilirsin.</div>`;
      hareketKarti.style.display = "none";
      mevcutBarkod = null;
      return;
    }
    const urun = await yanit.json();
    mevcutBarkod = urun.barkod;

    sonucKutu.style.display = "block";
    sonucKutu.innerHTML = `
      <div class="ad">${urun.ad}</div>
      <div class="miktar">${urun.miktar} ${urun.birim}</div>
      <div>Barkod: ${urun.barkod}</div>
    `;
    hareketKarti.style.display = "block";
  } catch (hata) {
    sonucKutu.style.display = "block";
    sonucKutu.innerHTML = `<div class="uyari">Bağlantı hatası: ${hata}</div>`;
  }
}

async function hareketYap(tip) {
  if (!mevcutBarkod) return;
  const miktar = parseFloat(document.getElementById("hareketMiktar").value);
  const not_ = document.getElementById("hareketNot").value;

  if (!miktar || miktar <= 0) {
    alert("Geçerli bir miktar gir");
    return;
  }

  const yanit = await fetch("/api/hareketler", {
    method: "POST",
    headers: yetkiliBasliklar({ "Content-Type": "application/json" }),
    body: JSON.stringify({ barkod: mevcutBarkod, tip, miktar, not_ }),
  });

  if (oturumKontrolEt(yanit)) return;

  if (!yanit.ok) {
    const hata = await yanit.json();
    alert("Hata: " + hata.detail);
    return;
  }

  document.getElementById("hareketMiktar").value = "";
  document.getElementById("hareketNot").value = "";
  await urunSorgula();
  await urunleriListele();
  await hareketleriListele();
}

async function urunEkle() {
  const barkod = document.getElementById("yeniBarkod").value.trim();
  const ad = document.getElementById("yeniAd").value.trim();
  const birim = document.getElementById("yeniBirim").value.trim() || "adet";
  const miktar = parseFloat(document.getElementById("yeniMiktar").value) || 0;
  const sonucDiv = document.getElementById("ekleSonuc");

  if (!barkod || !ad) {
    sonucDiv.innerHTML = `<div class="uyari">Barkod ve ürün adı zorunlu</div>`;
    return;
  }

  const yanit = await fetch("/api/urunler", {
    method: "POST",
    headers: yetkiliBasliklar({ "Content-Type": "application/json" }),
    body: JSON.stringify({ barkod, ad, birim, miktar, min_stok: 0 }),
  });

  if (oturumKontrolEt(yanit)) return;

  if (!yanit.ok) {
    const hata = await yanit.json();
    sonucDiv.innerHTML = `<div class="uyari">${hata.detail}</div>`;
    return;
  }

  sonucDiv.innerHTML = `<div class="basari">Ürün eklendi ✔</div>`;
  document.getElementById("yeniBarkod").value = "";
  document.getElementById("yeniAd").value = "";
  document.getElementById("yeniMiktar").value = "";
  await urunleriListele();
}

async function urunSil(barkod) {
  if (!confirm(`"${barkod}" barkodlu ürünü silmek istediğine emin misin?`)) return;

  const yanit = await fetch(`/api/urunler/${encodeURIComponent(barkod)}`, {
    method: "DELETE",
    headers: yetkiliBasliklar(),
  });

  if (oturumKontrolEt(yanit)) return;

  if (!yanit.ok) {
    const hata = await yanit.json();
    alert("Silinemedi: " + hata.detail);
    return;
  }

  await urunleriListele();
}

async function urunleriListele() {
  const yanit = await fetch("/api/urunler", { headers: yetkiliBasliklar() });
  if (oturumKontrolEt(yanit)) return;

  const urunler = await yanit.json();
  const govde = document.querySelector("#urunTablosu tbody");
  govde.innerHTML = urunler
    .map(
      (u) => `<tr>
        <td>${u.barkod}</td>
        <td>${u.ad}</td>
        <td>${u.miktar}</td>
        <td>${u.birim}</td>
        <td><button class="sil-btn" onclick="urunSil('${u.barkod}')" title="Sil">🗑️</button></td>
      </tr>`
    )
    .join("");
}

async function excelYukle() {
  const dosyaInput = document.getElementById("excelDosya");
  const sonucDiv = document.getElementById("excelSonuc");

  if (!dosyaInput.files.length) {
    sonucDiv.innerHTML = `<div class="uyari">Önce bir dosya seç</div>`;
    return;
  }

  const formData = new FormData();
  formData.append("dosya", dosyaInput.files[0]);

  sonucDiv.innerHTML = `<div>Yükleniyor, lütfen bekle...</div>`;

  try {
    const yanit = await fetch("/api/urunler/toplu-yukle", {
      method: "POST",
      headers: yetkiliBasliklar(),
      body: formData,
    });

    if (oturumKontrolEt(yanit)) return;

    const sonuc = await yanit.json();

    if (!yanit.ok) {
      sonucDiv.innerHTML = `<div class="uyari">${sonuc.detail}</div>`;
      return;
    }

    let mesaj = `<div class="basari">✔ ${sonuc.eklenen} yeni ürün eklendi, ${sonuc.guncellenen} ürün güncellendi.</div>`;
    if (sonuc.hatalar && sonuc.hatalar.length > 0) {
      mesaj += `<div class="uyari">${sonuc.hatalar.length} satır atlandı:<ul>`;
      sonuc.hatalar.slice(0, 10).forEach((h) => {
        mesaj += `<li>Satır ${h.satir}: ${h.mesaj}</li>`;
      });
      mesaj += `</ul></div>`;
    }
    sonucDiv.innerHTML = mesaj;
    dosyaInput.value = "";
    await urunleriListele();
  } catch (hata) {
    sonucDiv.innerHTML = `<div class="uyari">Bağlantı hatası: ${hata}</div>`;
  }
}

async function hareketleriListele() {
  const yanit = await fetch("/api/hareketler?limit=20", { headers: yetkiliBasliklar() });
  if (oturumKontrolEt(yanit)) return;

  const hareketler = await yanit.json();
  const govde = document.querySelector("#hareketTablosu tbody");
  govde.innerHTML = hareketler
    .map((h) => {
      const tarih = new Date(h.tarih).toLocaleString("tr-TR");
      const tipEtiket = h.tip === "giris" ? "🟢 Giriş" : "🔴 Çıkış";
      return `<tr><td>${tarih}</td><td>${tipEtiket}</td><td>${h.miktar}</td><td>${h.not_ || ""}</td></tr>`;
    })
    .join("");
}

document.getElementById("barkodGirisi").addEventListener("keydown", (e) => {
  if (e.key === "Enter") urunSorgula();
});

document.getElementById("girisSifre").addEventListener("keydown", (e) => {
  if (e.key === "Enter") girisYap();
});

// ---- Kamera ile barkod/QR tarama ----
let taramaAktif = null;

function taramaBaslat() {
  const kutu = document.getElementById("taramaKutusu");
  const buton = document.getElementById("taramaBaslatBtn");
  kutu.style.display = "block";
  buton.style.display = "none";

  taramaAktif = new Html5Qrcode("taramaAlani");

  const ayarlar = {
    fps: 10,
    qrbox: { width: 250, height: 150 },
  };

  taramaAktif
    .start(
      { facingMode: "environment" }, // arka kamera
      ayarlar,
      (kodMetni) => {
        // Barkod/QR okundu
        document.getElementById("barkodGirisi").value = kodMetni;
        taramaDurdur();
        urunSorgula();
      },
      () => {
        // okuma denemesi başarısız, sessizce devam (her karede tetiklenir)
      }
    )
    .catch((hata) => {
      alert("Kameraya erişilemedi: " + hata + "\nTarayıcının kamera iznini kontrol et.");
      kutu.style.display = "none";
      buton.style.display =
