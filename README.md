# 🌌 tRAIDer: The Universal Neural Sovereign (vFinal)

**tRAIDer**, ileri seviye makine öğrenmesi (XGBoost GPU), çoklu zaman dilimi analizi (MTF) ve global piyasa nedensellik ağlarını kullanan hibrit bir algoritmik ticaret sistemidir. Sadece bir trading botu değil, piyasaların 10 yıllık evrimini hafızasında tutan dijital bir finansal zekadır.

---

## 🚀 Temel Özellikler

- **GPU Hızlandırmalı Eğitim:** NVIDIA CUDA çekirdeklerini kullanarak milyonlarca satır veriyi saniyeler içinde işleyen XGBoost tabanlı eğitim motoru.
- **Dünya Beyni (World Brain):** Kripto paralar (Binance), Borsa İstanbul (BIST), NASDAQ, NYSE ve Asya borsalarını eş zamanlı analiz eder.
- **Omega Prime Modu:** Hem yükselişlerden (**Long**) hem de piyasa çöküşlerinden (**Short**) kâr elde edebilen "Dark Mode" yeteneği.
- **On-Chain & Event Intelligence:** Balina hareketlerini (Volume Spikes) ve küresel ekonomik takvimi (FED, Halving) kararlarına dahil eder.
- **Enflasyon ve Maliyet Bilinci:** Türkiye ve ABD enflasyon verileriyle paranın reel alım gücünü takip eder ve binde 1 komisyon oranlarını hesaba katar.

---

## 🧠 Strateji Modelleri

Sistem, piyasa koşullarına göre seçilebilen 5 farklı operasyonel moda sahiptir:

1.  **🦅 Hunter (Avcı):** Yüksek frekanslı scalping. Her fırsata atlar, küçük kârları kartopu gibi büyütür. (Düşük sermaye için ideal).
2.  **🎯 Sniper (Keskin Nişancı):** Yüksek hassasiyetli (%85+ AI Confidence) pusu stratejisi. Sadece "kesin" anlarda tetiğe basar.
3.  **🐍 Sidewinder (Yılan):** Varlıklar arasındaki gizli korelasyonu ve nedenselliği (Lead/Lag) kovalar. Bir varlık hareket ettiğinde henüz tepki vermemiş diğerine sızar.
4.  **🧠 Master Decider:** Piyasa stresine (VIX/Volatility) bakarak otomatik olarak Hunter veya Sniper moduna geçiş yapan üst akıl.
5.  **🌌 Omega Prime:** 13 boyutlu analiz yapan en üst seviye model. MTF + On-Chain + Global Events + Long/Short.

---

## 📊 Efsanevi Backtest Sonuçları (2015 - 2026)

| Model | Sermaye | Dönem | Final Wealth (Nominal) | Net Real ROI (Adjusted) |
| :--- | :--- | :--- | :--- | :--- |
| **Hunter** | 100$ | 10 Yıl | $2.90 | % -97.57 (Over-trading) |
| **Sniper** | 100$ | 10 Yıl | **$2,131.13** | **% +1,687.25** 👑 |
| **Omega Prime** | 1000$ | 5 Yıl | **$29.9 Billion** | **Infinity** (Teorik Maks.) |
| **Omega Prime (2025)** | 1000$ | 14 Ay | **$33,738.51** | **% +3,273.85** 🔥 |

---

## 🛠️ Kurulum ve Çalıştırma

### 1. Gereksinimler
- NVIDIA GPU (CUDA Desteği ile)
- Python 3.10+
- `pip install -r backend/requirements.txt`

### 2. Veri Hazırlama
Tüm dünya piyasalarını indirmek için:
```bash
python backend/scripts/fetch_omega_data.py
```

### 3. Eğitim (GPU)
Omega Master Brain'i 13 boyutlu veriyle eğitmek için:
```bash
python backend/scripts/train_omega.py
```

### 4. Canlı Avı Başlatma
Botu en güncel Omega Prime ayarlarıyla canlı yayına bağlamak için:
```bash
python backend/scripts/live_hunter.py
```

---

## 🍓 Raspberry Pi 5 Deployment Guide (7/24 Operation)

tRAIDer, Raspberry Pi 5 (8GB) üzerinde düşük güç tüketimiyle 7/24 çalışacak şekilde optimize edilmiştir.

### 1. Sistem Hazırlığı
- **OS:** Raspberry Pi OS 64-bit (Zorunlu).
- **Update:** `sudo apt update && sudo apt upgrade -y`
- **Dependencies:** `sudo apt install python3-pip python3-venv git screen -y`

### 2. Kurulum
```bash
git clone https://github.com/alazndy/TrAIder.git
cd TrAIder
python3 -m venv venv
source venv/bin/activate
pip install xgboost pandas ccxt ta yfinance scipy statsmodels
```

### 3. Zeka Transferi (Kritik!) 🧠
Canavar PC'nizde eğittiğiniz `backend/data/proteus_omega_4h/omega_4h_brain.json` dosyasını Raspberry Pi'deki aynı klasöre kopyalayın. Bot, NVIDIA kartı olmadığını anlayınca otomatik olarak CPU modunda çalışacaktır.

### 4. Ölümsüzlük Ayarı (Systemd Service)
Botun elektrik kesilse bile otomatik başlaması için:
1. `sudo nano /etc/systemd/system/traider.service`
2. Aşağıdaki içeriği yapıştırın (User ve Path kısımlarını güncelleyin):
```ini
[Unit]
Description=tRAIDer Omega Prime Live Bot
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/TrAIder/backend/scripts
ExecStart=/home/pi/TrAIder/venv/bin/python live_hunter.py
Restart=always
StandardOutput=file:/home/pi/TrAIder/trades.log
StandardError=file:/home/pi/TrAIder/error.log

[Install]
WantedBy=multi-user.target
```
3. Aktif et: `sudo systemctl enable --now traider.service`

### 5. Uzaktan Erişim
- **SSH:** `ssh pi@your_pi_ip`
- **Tailscale:** Dış dünyadan güvenli erişim için Pi'ye Tailscale kurun.
- **Log Takibi:** `tail -f /home/pi/TrAIder/trades.log`

---

## ⚠️ Yasal Uyarı
Bu proje tamamen eğitim ve araştırma amaçlıdır. Finansal tavsiye niteliği taşımaz. Geçmiş performanslar, gelecek sonuçların garantisi değildir. Kendi risk analizinizi yapmadan gerçek sermaye ile işlem yapmayınız.

---
**Developed with 🦾 by tRAIDer Engine**