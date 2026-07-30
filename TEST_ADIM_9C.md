# Prova Oturumu Manuel Testi (Adım 9 kabul kapısı — Adım 10 sonrası koşulur)

Adım 9'un **kabul kapısı**: gerçek bir kişiyle, `docs/OPERATOR_SOP.md` takip
edilerek, baştan sona tam bir oturum. Otomatik uçtan uca test bunun yerine
**geçmez** — insan akışı, süre, kulaklık yerleşimi, yönerge anlaşılırlığı ve
gerçek RT ancak burada görülür.

> **Bu prova, Adım 10'un ürettiği biçimde koşulur:** operatör **çift-tıkla açılan
> `.exe`** ile **operatör panelini** açar ve her şeyi **butonlarla** yapar (komut
> yazmaz). Kullanıcı kararı (2026-07-30): prova, son teslim biçimini denemeli.
>
> Her adımda panel butonunun yanında **komut satırı karşılığı** parantez içinde
> verilmiştir — Adım 10 tamamlanmadan (panel/exe hazır olmadan) provayı bu
> karşılıklarla da koşabilirsiniz; 10b bittiyse `python -m mcgurk.panel` ile
> panelden, 10c bittiyse `.exe` ile.

> **Bu bir "iş akışı provasıdır", gerçek veri toplama DEĞİL.** Fotodiyot ölçümü
> (`docs/01`) ve ses kalibrasyonu (`docs/02`) henüz yapılmadı, o yüzden oturum
> **development modunda** koşulur (`experiment.mode: development`). Toplanan veri
> bilimsel analiz için kullanılmaz; amaç akışın ve araçların baştan sona
> çalıştığını görmek.

## Ön koşullar

- [ ] **Adım 10 tamam** (panel + `.exe`). Değilse: 10b için `python -m mcgurk.panel`,
      hiç yoksa komut satırı karşılıklarıyla koşun.
- [ ] Ses aygıtı bağlı; **kulaklık sol=sol, sağ=sağ**.
- [ ] Uyaran seti hazır — panelde **"Uyaranları doğrula"** yeşil
      (komut karşılığı: `python tools/verify_stimuli.py` → çıkış 0).
- [ ] `experiment.mode: development`.
- [ ] Gerçek bir katılımcı (kendiniz veya bir gönüllü). **Yaş 18–60** olmalı
      (`participants.age` CHECK); değilse kısıt geçici gevşetilmeli.
- [ ] Operatör `docs/OPERATOR_SOP.md`'yi önceden okudu. **McGurk etkisi
      katılımcıya ASLA önceden anlatılmaz.**
- [ ] Sessiz oda, kronometre (süre ölçümü için).

---

## Test 1: Panelden baştan sona tam oturum (~75–80 dk)

**Başlat:** `.exe`'yi çift-tıklayın → **operatör paneli** açılır.
*(komut karşılığı: `python -m mcgurk.panel`; panel yoksa doğrudan `python main.py`)*

1. Panelde **"Kontrol listesi"** → YEŞİL/KIRMIZI ön-uçuş. **KIRMIZI varsa
   oturum başlatmayın.** *(karşılık: `python -m mcgurk.checklist`)*
2. Panelde **"Oturum başlat"** → deney **ayrı pencerede** açılır (panel donmaz).
   *(karşılık: `python main.py`)*
3. Giriş formu: **anonim kod** (ör. `PROVA-01`), grup, yaş, cinsiyet, deprivasyon,
   PTA. **Ad-soyad alanı yok.**
4. Oturum öncesi kontrol onayı ekranı.
5. Alıştırma → modüller sırayla (yönerge + molalar): mcgurk → avsr → tbw →
   oddball → dichotic → gin.
6. **Çapraz dinleme kontrolü** — yalnız grup SSD (`SSD_R`/`SSD_L`) seçilirse.
7. Bitiş ekranı + **otomatik yedek**.

**Kronometreyle ölçün:** toplam süre (ve mümkünse modül başına).

**Kontrol edilecek:**
1. Panel "Oturum başlat"a bastıktan sonra **donmuyor**, deney ayrı pencerede açılıyor.
2. Her modül yönergesiyle açılıyor, moduna uygun soruyu soruyor.
3. Molalar `break_every_n_trials`'da geliyor.
4. Katılımcıya hiçbir yerde **başarı yüzdesi / doğru-yanlış** gösterilmiyor.
5. Ses doğru kulaktan geliyor (lateralize denemelerde).
6. Bitişte yedek yazıldı, deney penceresi temiz kapandı, panel çalışıyor.
7. Katılımcıya gösterilen **hiçbir metin koda gömülü değil** (hepsi Türkçe, config'ten).

**Başarısızsa:** hangi modülde, ne oldu — not alın. Bulunan **her bug bu adımda
düzeltilir** (master merge öncesi).

---

## Test 2: Oturum sonrası — panel butonları (~3 dk)

Panelde **"Sonuçlar"** → oturum/katılımcı listesi (anonim kod, grup, tarih,
durum). Koştuğunuz oturumu seçin ve:

1. **"QC raporu"** → zamanlama (düşen kare/SOA), zaman aşımı oranı, yanıt
   dağılımı; (SSD ise) çapraz dinleme yargısı. *(karşılık: `python tools/qc_report.py`)*
2. **"Analiz"** → oturumun modül ölçütleri (McGurk oranları, AVSR fayda vb.).
   *(karşılık: `python tools/analyse.py`)*
3. **"Dışa aktar"** → çıktı klasörü seçin, CSV (+ parquet). Yazılan
   `trials_flat.csv` açılıyor; **`participants.csv`'de ad yok** (KVKK).
   *(karşılık: `python tools/export_data.py --out data/export`)*
4. **"Yedek doğrula"** → son yedek kullanılabilir mi.
   *(karşılık: `python tools/verify_backup.py <yedek>`)*

**Kontrol edilecek:** Sonuçlar listesi **anonim**; hiçbir ekranda ad yok. Uzun
işlerde panel donmuyor (durum gösteriliyor).

---

## Test 3: Kasıtlı bozma senaryoları (~10 dk)

Her biri **açık davranış** göstermeli, sessizce bozulmamalı:

### 3a. Oturumu ortada kes → panelden devam et
- "Oturum başlat" (`PROVA-02`), birkaç modül sonra deney penceresinde
  **`ESC` → Evet**.
- **Beklenen:** "çıkmak istediğinize emin misiniz?" onayı; onayınca oturum
  `aborted`, o ana kadarki veri korunur, yedek yazılır, deney penceresi kapanır.
- Panelde **"Sonuçlar"** → o oturum **`aborted`** görünür.
- Tekrar **"Oturum başlat"** → aynı kod (`PROVA-02`) → **"kaldığı yerden devam?"**
  teklifi. Devam edin; **tamamlanan modüller atlanıyor**, aynı oturum numarası.

### 3b. Yanıt verme (zaman aşımı)
- Bir forced-choice denemesinde (mcgurk/avsr) **hiç yanıt vermeyin**.
- **Beklenen:** deneme zaman aşımına uğrar, `responses` satırı yazılmaz;
  panelde **"QC raporu"**nda o modülün zaman aşımı oranında görünür, McGurk'te `NONE`.

### 3c. Uyaran eksik (başlamadan yakalanır)
- Panelde **"Uyaranları doğrula"** — set eksikse **KIRMIZI/hata** verir, oturum
  başlatılmaz. *(karşılık: `verify_stimuli` çıkış 1)*
- (İsteğe bağlı, kaynaktan) config'e hazırlanmamış bir token ekleyip
  `python -m mcgurk.config` → config **yüklenirken açık hata**. (Sonra geri alın.)

### 3d. Ses aygıtı yok
- Kulaklığı çıkarın/kapatın, panelden **"Oturum başlat"** deneyin.
- **Beklenen:** açık `AudioError`; sessiz geri düşüş **yok**; panel deneyin
  başlamadığını/hata çıkış kodunu gösterir.

---

## Kabul kriterleri

- [ ] Operatör her şeyi **panelden/exe'den, komut yazmadan** yaptı
- [ ] Tam oturum baştan sona çalıştı, süre ölçüldü (~75–80 dk hedefi)
- [ ] Panel "Oturum başlat"ta donmadı; deney ayrı süreçte açıldı
- [ ] Katılımcıya gösterilen hiçbir metin koda gömülü değil; başarı yüzdesi yok
- [ ] Kesip devam ettirme panelden çalışıyor, veri kaybı yok (3a)
- [ ] Zaman aşımı `NONE`/yanıtsız kaydediliyor (3b)
- [ ] Eksik uyaran başlatmadan yakalanıyor (3c), ses aygıtı kaybı açık hata (3d)
- [ ] Panelin "QC raporu"/"Analiz"/"Dışa aktar"/"Sonuçlar" butonları anlamlı,
      anonim çıktı veriyor
- [ ] Bulunan buglar düzeltildi

**Bu adım geçince:** `develop → master` merge + `git tag v1.0.0` (onayınızla).
**v1.0.0 = dağıtılabilir Windows uygulaması.**
