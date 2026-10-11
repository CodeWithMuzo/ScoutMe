# 🎓 SCOUTME YÜKSEK LİSANS TEZİ: VERİ KAZIMA, ÖZNİTELİK MÜHENDİSLİĞİ VE MATEMATİKSEL BECERİ MODELİ
**Tez Başlığı:** AI-Powered Multi-Stakeholder Football Scouting & Recommender System for Low-Resource Leagues  
**Yazar:** Muzaffer (DAÜ / EMU Bilgisayar Mühendisliği)  
**Tarih:** 4 Ekim 2026  
**Doküman Türü:** Tez Metodolojisi, Veri Mimarisi ve Matematiksel Model Dokümantasyonu  

---

## 📌 BÖLÜM 1: GİRİŞ VE PROBLEM TANIMI (VERİ KITLIĞI)

### 1.1. Düşük Kaynaklı Liglerdeki Temel Kısıtlar
Modern profesyonel futbolda (Premier League, La Liga vb.) oyuncu analitiği; optik takip kameraları (ChyronHego, Second Spectrum) ve saniyede onlarca veri noktası üreten mikro olay kayıtları (StatsPerform/Opta, Wyscout) üzerinden yürütülmektedir. Bu sistemlerde pas açıları, koşu hızları, pres şiddeti ve beklenen gol ($xG$) değerleri doğrudan sensörlerle ölçülebilmektedir.

Ancak **Kuzey Kıbrıs Türk Futbol Federasyonu (KTFF)** ve benzeri bölgesel, düşük bütçeli liglerde:
1. Optik takip kamerası veya GPS yelek sensörü verisi **bulunmamaktadır**.
2. Federasyon veri tabanında resmi **asist, kilit pas, isabetli şut, dripling veya top kapma** kayıtları **tutulmamaktadır**.
3. Oyuncuların boy, kilo, tercih edilen ayak gibi fiziksel nitelikleri federasyon bilgi bankasında **yayımlanmamaktadır**.

### 1.2. Akademik Çözüm Stratejimiz
Bu veri kıtlığını aşmak için tez kapsamında üç aşamalı bir sentetik analitik metodolojisi kurulmuştur:
* **Makro Verilerden Mikro Davranış Türetme:** Sezonluk süreler, ilk 11 başlama oranları, maç esamelerindeki oyuna giriş-çıkış dakikaları ve maç içi olaylar üzerinden vekâleten (proxy) metrikler türetilmiştir.
* **Saha İçi Skor Katkısı ($On\text{-}Pitch\ Scoring\ Differential$ - Khan et al., 2021 Modeli):** Resmi asist olmasa dahi, oyuncunun sahada kaldığı süre boyunca takımın attığı ve yediği gollerin net averajı hesaplanarak pasörlük ve oyun yönlendirme kalitesi kestirilmiştir.
* **4 Temel Sütun Üzerine Becerilerin Modellenmesi:** Futbolcu yetenekleri scouting standartlarına uygun olarak **Fiziksel**, **Şut**, **Teknik** ve **Defans** olmak üzere $0-100$ ölçeğinde normalize edilmiş 4 parametreye indirgenmiştir.

---

## 🏗️ BÖLÜM 2: VERİ TABANI ŞEMASI VE VERİ KAZIMA MİMARİSİ

### 2.1. Genişletilmiş Veri Tabanı Büyüklüğü (Audit Sonuçları)
Veri tabanımız ([`ktff.db`](file:///C:/Users/muzaf/Documents/DERSLER/IT%20MASTER/3.SENE%201.%20D%C3%96NEM/ScoutMe/data/ktff.db)), 4 Ekim 2026 tarihinde çalıştırılan çok iş parçacıklı kazıma motoruyla son 3 sezonun tamamını kapsayacak şekilde genişletilmiştir:

| Tablo Adı | Kayıt Sayısı | Kapsam ve Açıklama |
| :--- | :---: | :--- |
| **`matches`** | **1.178** | AKSA Süper Lig ve AKSA 1. Lig son 3 sezonunun tamamı (2024-2025, 2025-2026, 2026-2027). |
| **`match_lineups`** | **39.872** | 1.178 maçın ilk 11 ve yedek esame listeleri, forma numaraları, oynanan net dakikalar. |
| **`match_events`** | **16.348** | Dakika bazlı goller, penaltılar, sarı ve kırmızı kartlar, oyuncu değişiklikleri. |
| **`players`** | **2.404** | Aktif kayıtlı tüm futbolcular, lisans numaraları, doğum tarihleri, kulüpleri ve mevkileri. |
| **`player_season_stats`** | **7.212** | 2.404 futbolcunun son 3 sezondaki sezonluk toplam maç, ilk 11, yedek, gol ve kart dökümü. |
| **`player_skills`** | **2.404** | Her futbolcunun matematiksel olarak hesaplanan Fiziksel, Şut, Teknik, Defans ve OVR puanları. |
| **`clubs`** | **30** | AKSA Süper Lig (15) ve AKSA 1. Lig (15) güncel A takım kulüpleri. |
| **`coaches`** | **36** | A Takım Teknik Direktörleri, lisans ve biyografi verileri. |

### 2.2. Sezonlara Göre Maç Dağılımı
* **2026-2027 Sezonu (Devam Eden Sezon - Sezon ID: 13):**
  * AKSA Süper Lig (Comp ID: 60): **105 maç**
  * AKSA 1. Lig (Comp ID: 62): **105 maç**
* **2025-2026 Sezonu (Tamamlanan Sezon - Sezon ID: 11):**
  * AKSA Süper Lig (Comp ID: 1): **240 maç**
  * AKSA 1. Lig (Comp ID: 61): **240 maç**
* **2024-2025 Sezonu (Tamamlanan Sezon - Sezon ID: 10):**
  * AKSA Süper Lig (Comp ID: 1): **236 maç**
  * AKSA 1. Lig (Comp ID: 61): **232 maç** (+20 test maçı)
* **Toplam Kazınan Benzersiz Maç:** **1.178 Maç**

### 2.3. Kazıma Motoru Mimarisi ([`scrape_all_league_matches.py`](file:///C:/Users/muzaf/Documents/DERSLER/IT%20MASTER/3.SENE%201.%20D%C3%96NEM/ScoutMe/scraper/scrape_all_league_matches.py))
* **Çoklu İş Parçacığı (Multithreading):** `concurrent.futures.ThreadPoolExecutor(max_workers=8)` kullanılarak 1.148 yeni maç 216 saniyede (ortalama **5.5 maç/saniye**) çekilmiştir.
* **Disk Önbellekleme (Caching):** Her HTML yanıtı MD5 karmasıyla `data/raw_cache/` dizinine kaydedilmiş, ağ trafiği optimize edilmiş ve tekrarlı istekler engellenmiştir.
* **İş Parçacığı Güvenliği (Thread-Safety):** SQLite eşzamanlı yazma kilitleri `threading.Lock` ile korunarak veritabanı tutarlılığı garanti altına alınmıştır.

---

## 📐 BÖLÜM 3: 4 BOYUTLU OYUNCU BECERİ MODELİNİN MATEMATİKSEL FORMÜLASYONU

Her oyuncu $i$ için beceriler $S_i \in [0, 100]$ aralığında normalize edilen 4 temel bileşenden oluşur:

### 3.1. FİZİKSEL PUANI ($Physical\_Score_i$)
Fiziksel güç; oyuncunun maça dayanıklılığı, 90 dakikayı tamamlama kapasitesi, sakatlanmadan kadroda kalma sürekliliği ve yaşa bağlı dinamizm faktöründen türetilir.

1. **Süreklilik Endeksi (Continuity Index - $CI_i$):**
   $$CI_i = \frac{\text{starter\_matches}_i + 0.5 \times \text{sub\_in\_matches}_i}{\max(1, \text{total\_squad\_matches}_i)}$$
2. **İlk 11 Sadakat Oranı ($XI\_Ratio_i$):**
   $$XI\_Ratio_i = \frac{\text{starter\_matches}_i}{\max(1, \text{total\_played\_matches}_i)}$$
3. **Maç Başı Ortalama Süre ($Avg\_Min_i$):**
   $$Avg\_Min_i = \frac{\text{total\_minutes}_i}{\max(1, \text{total\_played\_matches}_i)}$$
4. **Yaş Dinamizm Katsayısı ($Age\_Factor_i$):**
   $$Age\_Factor_i = \begin{cases} 
   0.90 + \min(0.10, \text{played}_i \times 0.01), & \text{eğer } \text{yaş} \le 20 \\
   1.00, & \text{eğer } 21 \le \text{yaş} \le 28 \\
   0.93 - (\text{yaş} - 28) \times 0.02, & \text{eğer } 29 \le \text{yaş} \le 33 \\
   \max(0.65, 0.83 - (\text{yaş} - 33) \times 0.03), & \text{eğer } \text{yaş} \ge 34 
   \end{cases}$$
5. **Nihai Fiziksel Formülü:**
   $$\text{Raw\_Phys}_i = \left( \text{Base}_{\text{pos}} \times 0.25 + CI_i \times 35.0 + \min\left(1.0, \frac{Avg\_Min_i}{85}\right) \times 25.0 + XI\_Ratio_i \times 15.0 \right) \times Age\_Factor_i$$
   $$\text{Physical\_Score}_i = \text{clip}(\text{Raw\_Phys}_i + \text{Bonus}_{\text{disiplin}}, 35.0, 95.0)$$

---

### 3.2. ŞUT PUANI ($Shooting\_Score_i$)
Şut puanı; oyuncunun maç başına saf gol üretkenliği ($P90\_Goals$), toplam gol hacmi ve mevkisine göre gol beklentisini aşma derecesinden hesaplanır.

1. **90 Dakika Başına Düşen Gol ($P90\_Goals_i$):**
   $$P90\_Goals_i = \frac{\text{goals}_i}{\max(1, \text{total\_minutes}_i)} \times 90.0$$
2. **Mevki Bazlı Şut Puanlama Fonksiyonu:**
   * **Forvetler (FW):**
     $$\text{Shooting\_FW}_i = 52.0 + \min\left(1.0, \frac{P90\_Goals_i}{0.65}\right) \times 36.0 + \min(8.0, \text{goals}_i \times 0.4)$$
   * **Orta Sahalar (MF):**
     $$\text{Shooting\_MF}_i = 45.0 + \min\left(1.0, \frac{P90\_Goals_i}{0.35}\right) \times 35.0 + \min(12.0, \text{goals}_i \times 0.6)$$
   * **Defanslar (DF - Duran Top / Kafa Golleri):**
     $$\text{Shooting\_DF}_i = 35.0 + \min\left(1.0, \frac{P90\_Goals_i}{0.15}\right) \times 35.0 + \min(15.0, \text{goals}_i \times 1.5)$$
   * **Kaleciler (GK):**
     $$\text{Shooting\_GK}_i = 25.0 + \min(15.0, \text{goals}_i \times 5.0)$$
3. **Nihai Şut Formülü:**
   $$\text{Shooting\_Score}_i = \text{clip}(\text{Shooting\_Function}_{\text{pos}} - \text{Ceza}_{\text{inaktif}}, 30.0, 96.0)$$

---

### 3.3. TEKNİK PUANI ($Technical\_Score_i$)
Resmi asist kaydı bulunmayan KTFF liginde teknik puan; literatürde kabul görmüş **Saha İçi Skor Katkısı ($On\text{-}Pitch\ Differential$)**, oyun kurucu mevkisel rolü ve top hakimiyetine bağlı düşük kart ortalamasından (temiz oyun) türetilmiştir.

1. **Saha İçi Net Skor Katkısı ($Diff\_Per90_i$ - Khan et al., 2021 Modeli):**
   1.178 maç esamesi taranarak, oyuncunun fiilen sahada kaldığı dakikalarda takımının attığı goller ile yediği gollerin farkı hesaplanır:
   $$Diff\_Per90_i = \frac{\sum \text{Team\_Goals\_While\_Played}_i - \sum \text{Opp\_Goals\_While\_Played}_i}{\max(1, \text{total\_minutes}_i)} \times 90.0$$
2. **Diferansiyel Katkı Skoru ($Diff\_Score_i$):**
   $$Diff\_Score_i = \text{clip}(Diff\_Per90_i \times 10.0, -10.0, +18.0)$$
3. **Temiz Oyun ve Top Hakimiyeti Bonusu ($Clean\_Bonus_i$):**
   Orta sahada yüksek süre alıp faulsüz, topu ayağında tutarak oynayan oyuncular:
   $$Card\_Rate_i = \frac{\text{yellow}_i + 2 \times \text{red}_i}{\max(1, \text{played}_i)}$$
   $$\text{Clean\_Bonus}_i = \begin{cases} 
   +6.0, & \text{eğer } Card\_Rate_i \le 0.12 \text{ ve } \text{played}_i \ge 10 \\
   +3.0, & \text{eğer } Card\_Rate_i \le 0.20 \text{ ve } \text{played}_i \ge 5 \\
   0.0, & \text{diğer}
   \end{cases}$$
4. **Nihai Teknik Formülü:**
   $$\text{Technical\_Score}_i = \text{clip}(\text{Base\_Tech}_{\text{pos}} + Diff\_Score_i + Clean\_Bonus_i, 35.0, 95.0)$$
   *(Burada $\text{Base\_Tech}_{\text{pos}}$: 10 Numara ve Kanatlar için 68.0, Merkez Orta Saha için 62.0, Forvet için 58.0, Defans için 48.0'dır).*

---

### 3.4. DEFANS PUANI ($Defending\_Score_i$)
Defans puanı; sahadayken 90 dakika başına yenilen gol azlığı, kalesini gole kapatma ($Clean\ Sheet$), antrenörün savunma kurgusundaki ilk 11 vazgeçilmezliği ve kontrollü taktik faul sertliğinden hesaplanır.

1. **Yenilen Gol Oranı Skoru ($Concede\_Bonus_i$):**
   $$Conceded\_Per90_i = \frac{\sum \text{Opp\_Goals\_While\_Played}_i}{\max(1, \text{total\_minutes}_i)} \times 90.0$$
   $$Concede\_Bonus_i = \begin{cases} 
   +12.0, & \text{eğer } Conceded\_Per90_i \le 0.90 \text{ ve } \text{played}_i \ge 5 \\
   +6.0,  & \text{eğer } Conceded\_Per90_i \le 1.30 \text{ ve } \text{played}_i \ge 5 \\
   -8.0,  & \text{eğer } Conceded\_Per90_i \ge 2.20 \text{ ve } \text{played}_i \ge 5 \\
   0.0,   & \text{diğer}
   \end{cases}$$
2. **Kalesini Gole Kapatma Bonusu ($Clean\_Sheet\_Bonus_i$):**
   $$CS\_Bonus_i = \min(10.0, \text{clean\_sheets}_i \times 1.5)$$
3. **Savunma Güvenilirliği & İstikrarı:**
   $$XI\_Stability_i = XI\_Ratio_i \times 8.0$$
4. **Kontrollü Savunma Sertliği:**
   $$Tackle\_Bonus_i = \begin{cases} +4.0, & \text{eğer } 0.10 \le Card\_Rate_i \le 0.28 \text{ ve } \text{red}_i = 0 \text{ ve } \text{pos} \in \{\text{DF, MF}\} \\ 0.0, & \text{diğer} \end{cases}$$
5. **Nihai Defans Formülü:**
   $$\text{Defending\_Score}_i = \text{clip}(\text{Base\_Def}_{\text{pos}} + Concede\_Bonus_i + CS\_Bonus_i + XI\_Stability_i + Tackle\_Bonus_i, 30.0, 96.0)$$
   *(Burada $\text{Base\_Def}_{\text{pos}}$: Stoper için 72.0, Bek için 68.0, Ön Libero için 55.0, Forvet için 34.0'dır).*

---

### 3.5. GENEL REYTİNG (OVERALL RATING - $OVR_i$)
FIFA/Football Manager endüstri standardı uyarınca, her mevkideki oyuncunun genel reytingi mevkisine özel ağırlıklandırılmış kompozit formülle üretilir:

$$OVR_i = \begin{cases} 
0.45 \times Def_i + 0.35 \times Phys_i + 0.15 \times Tech_i + 0.05 \times Shoot_i, & \text{eğer } pos = \text{GK} \\
0.45 \times Def_i + 0.30 \times Phys_i + 0.15 \times Tech_i + 0.10 \times Shoot_i, & \text{eğer } pos = \text{DF} \\
0.35 \times Tech_i + 0.25 \times Phys_i + 0.20 \times Def_i + 0.20 \times Shoot_i, & \text{eğer } pos = \text{MF} \\
0.45 \times Shoot_i + 0.25 \times Tech_i + 0.25 \times Phys_i + 0.05 \times Def_i, & \text{eğer } pos = \text{FW}
\end{cases}$$

---

## 📊 BÖLÜM 4: AMPİRİK SONUÇLAR VE DAĞILIM İSTATİSTİKLERİ

Hesaplama motoru tüm 2.404 futbolcu için çalıştırılmış ve en az 5 maç oynamış **1.989 aktif futbolcu** üzerinden dağılım istatistikleri çıkarılmıştır:

### 4.1. Becerilerin Betimsel İstatistikleri
| Beceri | Ortalama | Standart Sapma | Min | Medyan | Max |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Fiziksel (Phys)** | **66.0** | 10.4 | 35.0 | 66.8 | 92.5 |
| **Şut (Shoot)** | **59.0** | 13.8 | 30.0 | 54.0 | 96.0 |
| **Teknik (Tech)** | **65.3** | 8.9 | 35.0 | 65.0 | 92.0 |
| **Defans (Def)** | **71.0** | 12.1 | 30.0 | 72.0 | 96.0 |
| **Genel Reyting (OVR)** | **69.5** | 7.6 | 45.8 | 69.8 | 86.8 |

*Bulgular:* Standart sapma ve medyan değerleri, modelin oyuncuları birbirine yığmadan homojen ve dengeli bir Gauss dağılımına yakın yaydığını; elit oyuncuların ($OVR \ge 82$) popülasyonun en üst %5'lik diliminde doğru ayrıştığını kanıtlamaktadır.

### 4.2. Doğrulama Örnekleri (Benchmarking)
Ligin gerçek performansıyla model çıktıları kıyaslandığında yüksek korelasyon gözlenmiştir:
* **Amara Fofana (China Bazaar GG):** Ligin en skorer yabancı santraforlarından biri $\rightarrow$ **OVR: 86.8** (Şut: 96.0, Fizik: 79.9, Teknik: 81.7).
* **Emre Soytürk (Doğan Türk Birliği):** Şampiyonluk yarışındaki takımın vazgeçilmez stoperi $\rightarrow$ **OVR: 84.8** (Defans: 96.0, Fizik: 89.4, Teknik: 64.3).
* **Zihni Temelci (Mağusa Türk Gücü):** Hem savunma yapan hem duran toplarda gol atan lider defans $\rightarrow$ **OVR: 84.5** (Defans: 95.7, Şut: 76.6, Fizik: 82.1).
* **Hakkı Duvarcı (Küçük Kaymaklı TSK):** Tecrübeli lig kalecisi $\rightarrow$ **OVR: 77.5** (Defans: 85.8, Fizik: 82.0).

---

## 🛠️ BÖLÜM 5: ÇALIŞAN KOD VE ARTEFAKT ENVENTERİ

Tez savunmasında ve literatür karşılaştırmasında kullanılan tüm kaynak dosyalar:

1. **[`data/ktff.db`](file:///C:/Users/muzaf/Documents/DERSLER/IT%20MASTER/3.SENE%201.%20D%C3%96NEM/ScoutMe/data/ktff.db):** SQLite veritabanı (1.178 Maç, 39.872 Kadro, 16.348 Olay, 7.212 Sezon İstatistiği, 2.404 Oyuncu Becerisi).
2. **[`scraper/scrape_all_league_matches.py`](file:///C:/Users/muzaf/Documents/DERSLER/IT%20MASTER/3.SENE%201.%20D%C3%96NEM/ScoutMe/scraper/scrape_all_league_matches.py):** Çok iş parçacıklı, önbellekli son 3 sezon maç kazıma motoru.
3. **[`analytics/calculate_player_skills.py`](file:///C:/Users/muzaf/Documents/DERSLER/IT%20MASTER/3.SENE%201.%20D%C3%96NEM/ScoutMe/analytics/calculate_player_skills.py):** 4 temel beceri ve OVR reytingi hesaplayan matematiksel formül motoru.
4. **[`audit_db.py`](file:///C:/Users/muzaf/Documents/DERSLER/IT%20MASTER/3.SENE%201.%20D%C3%96NEM/ScoutMe/audit_db.py):** Veritabanı tutarlılık, eksiklik ve dağılım denetim scripti.
5. **[`export_cards.py`](file:///C:/Users/muzaf/Documents/DERSLER/IT%20MASTER/3.SENE%201.%20D%C3%96NEM/ScoutMe/export_cards.py) & [`scoutme_visual_boxes.html`](file:///C:/Users/muzaf/Documents/DERSLER/IT%20MASTER/3.SENE%201.%20D%C3%96NEM/ScoutMe/scoutme_visual_boxes.html):** 2.404 futbolcunun OVR ve 4'lü beceri rozetleriyle incelenebildiği dinamik görsel web paneli.
6. **[`PROJECT_MEMORY.md`](file:///C:/Users/muzaf/Documents/DERSLER/IT%20MASTER/3.SENE%201.%20D%C3%96NEM/PROJECT_MEMORY.md):** Proje resmi hafızası ve yol haritası.
