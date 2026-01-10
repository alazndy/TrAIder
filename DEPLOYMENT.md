# 🚀 TrAIder Deployment Guide

Bu rehber, **TrAIder** projesini (Backend ve Frontend) tamamen **Ücretsiz** ve **7/24 Canlı** şekilde buluta kurmanız için hazırlanmıştır.

---

## 🛠️ Hazırlık (Dosyalar)

Proje şu an GitHub'da hazır: **[https://github.com/alazndy/TrAIder](https://github.com/alazndy/TrAIder)**
_(Eğer görmüyorsan önce `git push origin master` yapıldığından emin ol)_

---

## 1. Backend Kurulumu (Render.com)

Robotun beyni burada çalışacak.

1.  [Render.com Dashboard](https://dashboard.render.com/) adresine git.
2.  **New +** butonuna tıkla ve **Web Service** seç.
3.  **Connect a repository** kısmında `TrAIder` reponu seç.
4.  **Ayarlar:**
    - **Name:** `traider-bot` (veya istediğin bir isim)
    - **Region:** Frankfurt (EU Central)
    - **Root Directory:** `backend` (Çok Önemli!)
    - **Runtime:** `Docker`
    - **Plan:** Free
5.  **Environment Variables (Ortam Değişkenleri):**
    - `AUTO_START` = `true` (Robotun otomatik başlaması için)
    - `PORT` = `8000` (Render otomatik atar ama eklemek garanti olur)
6.  **Secret Files (Gizli Dosyalar):**
    - Sayfanın altındaki "Secret Files" bölümüne gel.
    - **Filename:** `serviceAccountKey.json`
    - **Contents:** Bilgisayarındaki `serviceAccountKey.json` dosyasının **içeriğini** (not defteriyle açıp kopyala) buraya yapıştır.
7.  **Create Web Service** butonuna bas.

👉 **Sonuç:** Deploy bitince sana `https://traider-bot.onrender.com` gibi bir link verecek. Bu linki kopyala.

---

## 2. Sistemi Uyanık Tutma (UptimeRobot)

Render Free Tier 15dk işlem olmazsa uyur. Robotun hep çalışması için onu dürtmemiz lazım.

1.  [UptimeRobot](https://uptimerobot.com/)'a git ve üye ol/giriş yap.
2.  **Add New Monitor** butonuna bas.
3.  **Monitor Type:** `HTTP(s)`
4.  **Friendly Name:** `TrAIder Bot`
5.  **URL (or IP):** Render'dan aldığın linki yapıştır (örn: `https://traider-bot.onrender.com/`)
6.  **Monitoring Interval:** `5 minutes`
7.  **Create Monitor** de.

✅ **Artık robotun 7/24 çalışıyor!**

---

## 3. Frontend Kurulumu (Vercel)

Dashboard'u yayınlamak için.

1.  [Vercel](https://vercel.com/)'e GitHub ile giriş yap.
2.  **Add New... > Project** de.
3.  `TrAIder` reponu seç (Import).
4.  **Framework Preset:** `Next.js` (Otomatik algılar).
5.  **Root Directory:** `Edit` butonuna bas ve `web-dashboard` klasörünü seç.
6.  **Environment Variables:**
    - Buraya `web-dashboard/.env.local` dosyanın içindeki her şeyi ekle.
    - Örn: `NEXT_PUBLIC_FIREBASE_API_KEY` -> `AIzaSy...`
    - (Toplam 6 tane değişken olacak).
7.  **Deploy** butonuna bas.

👉 **Sonuç:** Sana `https://traider-dashboard.vercel.app` gibi bir link verecek.

---

## 🎉 Mutlu Son!

Artık:

- Robotun Render'da çalışıyor, UptimeRobot onu uyanık tutuyor.
- Verileri Firebase'e yazıyor.
- Sen Vercel linkinden Dashboard'u açıp kahveni yudumlarken kâr/zarar durumunu canlı izliyorsun. 💸
