let mevcutBarkod = null;
let mevcutRol = null;

// ---- Kimlik doğrulama ----
function tokenGetir() {
  return localStorage.getItem("depo_token");
}

function tokenKaydet(token, kullaniciAdi, rol) {
  localStorage.setItem("depo_token", token);
  localStorage.setItem("depo_kullanici_adi", kullaniciAdi);
  localStorage.setItem("depo_rol", rol);
}

function tokenSil() {
  localStorage.removeItem("depo_token");
  localStorage.removeItem("depo_kullanici_adi");
  localStorage.removeItem("depo_rol");
}

function yetkiliBasliklar(ekBaslik = {}) {
  return { Authorization: `Bearer ${tokenGetir()}`, ...ekBaslik };
}

const ROL_ETIKETLERI = {
  super_admin: "Süper Admin",
  depo_muduru: "Depo Müdürü",
  personel: "Personel",
  goruntuleyici: "Görüntüleyici",
};

// Belirli işlemler için minimum rol seviyesi kontrolü (frontend tarafı;
// gerçek güvenlik backend'de sağlanıyor, burası sadece UI'ı sadeleştirmek için)
const ROL_SEVIYESI = { goruntuleyici: 0, personel: 1, depo_muduru: 2, super_admin: 3 };

function rolYeterliMi(minRol) {
  return (ROL_SEVIYESI[mevcutRol] ?? 0) >= (ROL_SEVIYESI[minRol] ?? 99);
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
    tokenKaydet(veri.access_token, veri.kullanici_adi, veri.rol);
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
  mevcutRol = localStorage.getItem("depo_rol");
  document.getElementById("girisEkrani").style.display = "none";
  document.getElementById("anaIcerik").style.display = "block";

  const kullaniciAdi = localStorage.getItem("depo_kullanici_adi");
  const rolEtiket = ROL_ETIKETLERI[mevcutRol] || mevcutRol;
  document.getElementById("kullaniciBilgisi").innerHTML =
    `${kacisEt(kullaniciAdi)} <span class="rozet">${kacisEt(rolEtiket)}</span>`;

  // Denetim kayıtları sadece depo_muduru ve üstü için görünsün
  document.getElementById("denetimKarti").style.display = rolYeterliMi("depo_muduru") ? "block" : "none";
}

async function sayfaVerileriniYukle() {
  await urunleriListele();
  await hareketleriListele();
  if (rolYeterliMi("depo_muduru")) {
    await denetimKayitlariniListele();
  }
}

function oturumKontrolEt(yanit) {
  if (yanit.status === 401) {
    cikisYap();
    return true;
  }
  return false;
}

// Basit HTML kaçış fonksiyonu: kullanıcıdan gelen metinleri (ürün adı,
// not, kullanıcı adı vb.) tabloya yazmadan önce güvenli hale getirir.
function kacisEt(metin) {
  const d = document.createElement("div");
  d.textContent = metin ?? "";
  return d.innerHTML;
}

// ---- Şifre değiştirme ----
function sifrePaneliAcKapat() {
  const panel = document.getElementById("sifrePaneli");
  panel.style.display = panel.style.display === "none" ? "block" : "none";
}

async function sifreDegistir() {
  const eskiSifre = document.getElementById("eskiSifre").value;
  const yeniSifre = document.getElementById("yeniSifre").value;
  const sonucDiv = document.getElementById("sifreSonuc");

  if (!eskiSifre || !yeniSifre) {
    sonucDiv.innerHTML = `<div class="uyari">Her iki alanı da doldur</div>`;
    return;
  }
  if (yeniSifre.length < 6) {
    sonucDiv.innerHTML = `<div class="uyari">Yeni şifre en az 6 karakter olmalı</div>`;
    return;
  }

  const yanit = await fetch("/api/auth/sifre-degistir", {
    method: "POST",
    headers: yetkiliBasliklar({ "Content-Type": "application/json" }),
    body: JSON.stringify({ eski_sifre: eskiSifre, yeni_sifre: yeniSifre }),
  });

  if (oturumKontrolEt(yanit)) return;

  if (!yanit.ok) {
    const hata = await yanit.json();
    sonucDiv.innerHTML = `<div class="uyari">${kacisEt(hata.detail)}</div>`;
    return;
  }

  sonucDiv.innerHTML = `<div class="basari">Şifre güncellendi ✔</div>`;
  document.getElementById("eskiSifre").value = "";
  document.getElementById("yeniSifre").value = "";
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

    const kritikUyari =
      urun.kritik_stok > 0 && urun.miktar <= urun.kritik_stok
        ? `<div class="uyari">⚠️ Kritik stok seviyesinde!</div>`
        : "";

    sonucKutu.style.display = "block";
    sonucKutu.innerHTML = `
      <div class="ad">${kacisEt(urun.ad)}</div>
      <div class="miktar">${urun.miktar} ${kacisEt(urun.birim)}</div>
      <div>Barkod: ${kacisEt(urun.barkod)}</div>
      ${kritikUyari}
    `;
    hareketKarti.style.display = rolYeterliMi("personel") ? "block" : "none";
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
    sonucDiv.innerHTML = `<div class="uyari">${kacisEt(hata.detail)}</div>`;
    return;
  }

  sonucDiv.innerHTML = `<div class="basari">Ürün eklendi ✔</div>`;
  document.getElementById("yeniBarkod").value = "";
  document.getElementById("yeniAd").value = "";
  document.getElementById("yeniMiktar").value = "";
  await urunleriListele();
}

async function urunSil(barkod) {
  if (!confirm(`"${barkod}" barkodlu ürünü silmek istediğine emin misin? (Geri yüklenebilir)`)) return;

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
  const silmeYetkisiVar = rolYeterliMi("depo_muduru");
  const govde = document.querySelector("#urunTablosu tbody");
  govde.innerHTML = urunler
    .map((u) => {
      const kritik = u.kritik_stok > 0 && u.miktar <= u.kritik_stok ? ' style="color:#d1242f;font-weight:600;"' : "";
      const silButonu = silmeYetkisiVar
        ? `<button class="sil-btn" onclick="urunSil('${kacisEt(u.barkod)}')" title="Sil">🗑️</button>`
        : "";
      return `<tr${kritik}>
        <td>${kacisEt(u.barkod)}</td>
        <td>${kacisEt(u.ad)}</td>
        <td>${u.miktar}</td>
        <td>${kacisEt(u.birim)}</td>
        <td>${silButonu}</td>
      </tr>`;
    })
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
      sonucDiv.innerHTML = `<div class="uyari">${kacisEt(sonuc.detail)}</div>`;
      return;
    }

    let mesaj = `<div class="basari">✔ ${sonuc.eklenen} yeni ürün eklendi, ${sonuc.guncellenen} ürün güncellendi.</div>`;
    if (sonuc.hatalar && sonuc.hatalar.length > 0) {
      mesaj += `<div class="uyari">${sonuc.hatalar.length} satır atlandı:<ul>`;
      sonuc.hatalar.slice(0, 10).forEach((h) => {
        mesaj += `<li>Satır ${h.satir}: ${kacisEt(h.mesaj)}</li>`;
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
      return `<tr>
        <td>${tarih}</td>
        <td>${tipEtiket}</td>
        <td>${h.onceki_miktar ?? "-"}</td>
        <td>${h.sonraki_miktar ?? "-"}</td>
        <td>${kacisEt(h.neden || h.not_ || "")}</td>
        <td>${kacisEt(h.kullanici_adi_metin || "-")}</td>
      </tr>`;
    })
    .join("");
}

async function denetimKayitlariniListele() {
  const yanit = await fetch("/api/denetim-kayitlari?limit=100", { headers: yetkiliBasliklar() });
  if (oturumKontrolEt(yanit)) return;
  if (!yanit.ok) return; // yetkisizse sessizce geç (kart zaten gizli olacak)

  const kayitlar = await yanit.json();
  const govde = document.querySelector("#denetimTablosu tbody");
  govde.innerHTML = kayitlar
    .map((k) => {
      const tarih = new Date(k.tarih).toLocaleString("tr-TR");
      const hedef = k.hedef_tip ? `${kacisEt(k.hedef_tip)}: ${kacisEt(k.hedef_id)}` : "-";
      return `<tr>
        <td>${tarih}</td>
        <td>${kacisEt(k.kullanici_adi || "-")}</td>
        <td>${kacisEt(k.islem)}</td>
        <td>${hedef}</td>
      </tr>`;
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
      { facingMode: "environment" },
      ayarlar,
      (kodMetni) => {
        document.getElementById("barkodGirisi").value = kodMetni;
        taramaDurdur();
        urunSorgula();
      },
      () => {}
    )
    .catch((hata) => {
      alert("Kameraya erişilemedi: " + hata + "\nTarayıcının kamera iznini kontrol et.");
      kutu.style.display = "none";
      buton.style.display = "block";
    });
}

function taramaDurdur() {
  const kutu = document.getElementById("taramaKutusu");
  const buton = document.getElementById("taramaBaslatBtn");

  if (taramaAktif) {
    taramaAktif
      .stop()
      .then(() => taramaAktif.clear())
      .catch(() => {});
    taramaAktif = null;
  }

  kutu.style.display = "none";
  buton.style.display = "block";
}

// ---- Başlangıç ----
if (tokenGetir()) {
  girisEkraniniGizle();
  sayfaVerileriniYukle();
}
