let mevcutBarkod = null;

async function urunSorgula() {
  const barkod = document.getElementById("barkodGirisi").value.trim();
  if (!barkod) return;

  const sonucKutu = document.getElementById("urunSonuc");
  const hareketKarti = document.getElementById("hareketKarti");

  try {
    const yanit = await fetch(`/api/urunler/${encodeURIComponent(barkod)}`);
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ barkod: mevcutBarkod, tip, miktar, not_ }),
  });

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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ barkod, ad, birim, miktar, min_stok: 0 }),
  });

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

async function urunleriListele() {
  const yanit = await fetch("/api/urunler");
  const urunler = await yanit.json();
  const govde = document.querySelector("#urunTablosu tbody");
  govde.innerHTML = urunler
    .map(
      (u) => `<tr><td>${u.barkod}</td><td>${u.ad}</td><td>${u.miktar}</td><td>${u.birim}</td></tr>`
    )
    .join("");
}

async function hareketleriListele() {
  const yanit = await fetch("/api/hareketler?limit=20");
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

// Sayfa açılışında listeleri getir
urunleriListele();
hareketleriListele();
