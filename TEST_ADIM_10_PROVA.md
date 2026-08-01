# Prova Oturumu — Paketlenmiş App (Adım 10 sonrası, steps.md Adım 9 kabul kapısı)

`TEST_ADIM_9C.md`'nin **paketlenmiş `.exe` + panel** biçimine uyarlanmış,
somutlaştırılmış hâli. İki kısım:

- **A. Mini prova (2–3 dk)** — kendi başınıza, akışı hızlıca hissetmek için.
- **B. Tam prova** — gerçek bir kişiyle, baştan sona (~75–80 dk), kabul kapısı.

> **Bu bir "iş akışı provasıdır", gerçek veri toplama DEĞİL.** Fotodiyot (`docs/01`)
> ve kalibrasyon (`docs/02`) henüz yapılmadı; oturum **development modunda** koşar
> (`experiment.mode: development`). Toplanan veri bilimsel analiz için kullanılmaz.

## Kurulum (bir kez)

- [ ] `.exe` derlenmiş: `dist\McGurkSSD\McGurkSSD.exe`
- [ ] `stimuli\` uygulamanın yanında: `dist\McGurkSSD\stimuli\`
- [ ] Ses aygıtı bağlı, **kulaklık sol=sol / sağ=sağ**. (config `audio.device`
      bekleneni bulmalı; checklist YEŞİL demeli.)
- [ ] Konum **yazılabilir** (Masaüstü / `C:\McGurkSSD`, Program Files değil).

---

# A. Mini prova (2–3 dk) — kendi başınıza

Amaç: paketlenmiş akışı uçtan uca **hızlıca** görmek. Tam oturum ~75 dk sürdüğü
için burada **her modülden 1 deneme** koşuyoruz (`--limit 1`).

### A.1 — Panel + checklist (~30 sn)
1. `dist\McGurkSSD\McGurkSSD.exe`'ye çift tıklayın → panel açılır.
2. **Kontrol listesi** butonu → YEŞİL/KIRMIZI. (Kısa bir PsychoPy penceresi açılıp
   yenileme hızını ölçer, kapanır.) Ses aygıtı satırı **YEŞİL** olmalı.

### A.2 — Hızlı deney (~1.5 dk)
Panelin "Oturum başlat"ı **tam** oturumu açar; mini prova için terminalden sınırlı
koşun. PowerShell'de:
```powershell
cd C:\Users\tayla\projects\mcgurk\dist\McGurkSSD
.\McGurkSSD.exe --run session --limit 1 --new-session
```
- Giriş formu: kod `MINI-01`, **grup CTRL** (çapraz dinlemeyi atlar → daha hızlı),
  yaş 30, cinsiyet seçin. (Grup **SSD_R/SSD_L** seçerseniz sonda çapraz dinleme
  kontrolü de gelir — onu da görmek isterseniz.)
- Kontrol onayı ekranı → alıştırma → her modülden 1 deneme (yönerge ekranlarını
  hızlı geçin; `--limit 1` olduğu için mola gelmez) → bitiş + otomatik yedek.

### A.3 — Panelden sonuçlar (~30 sn)
1. Panele dönün → **Yenile** → `MINI-01` oturumu listede.
2. Oturumu seçin → **QC raporu** ve **Analiz** → çıktı panelinde okunur metin
   (Türkçe düzgün, anonim).
3. **Dışa aktar...** → bir klasör seçin → `trials_flat.csv` yazılır.

**Gördüyseniz akış tamam:** panel → checklist → deney (ayrı süreç) → sonuç/QC/
export. Tam provaya (B) hazırsınız.

> Mini provanın `MINI-01` verisini silmek isterseniz oturumu bırakın; gerçek
> provada ayrı kodlar (`PROVA-01`…) kullanın. Development verisi analiz edilmez.

---

# B. Tam prova — kabul kapısı

Gerçek bir kişiyle, `docs/OPERATOR_SOP.md` takip edilerek, baştan sona tam bir
oturum. Otomatik test bunun yerine **geçmez** — insan akışı, süre, kulaklık
yerleşimi, yönerge anlaşılırlığı ve gerçek RT ancak burada görülür.

## Ön koşullar
- [ ] Mini prova (A) geçti.
- [ ] Gerçek katılımcı (kendiniz veya gönüllü), **yaş 18–60** (`participants.age`
      CHECK; değilse kısıt geçici gevşetilmeli).
- [ ] Operatör `docs/OPERATOR_SOP.md`'yi okudu. **McGurk etkisi katılımcıya ASLA
      önceden anlatılmaz** (talep karakteristiği).
- [ ] Sessiz oda, kronometre.

## Test 1: Panelden baştan sona tam oturum (~75–80 dk)
1. `McGurkSSD.exe` çift-tık → panel.
2. **Kontrol listesi** → YEŞİL/KIRMIZI. **KIRMIZI varsa başlatmayın.**
3. **Oturum başlat** → deney **ayrı pencerede** açılır (panel donmaz).
4. Giriş: **anonim kod** (`PROVA-01`), grup, yaş, cinsiyet, deprivasyon, PTA.
   **Ad-soyad alanı yok.**
5. Kontrol onayı → alıştırma → modüller sırayla (yönerge + molalar): mcgurk →
   avsr → tbw → oddball → dichotic → gin.
6. **Çapraz dinleme kontrolü** — yalnız grup SSD ise.
7. Bitiş + **otomatik yedek**.

**Kronometreyle** toplam (ve mümkünse modül başına) süreyi ölçün.

**Kontrol edilecek:**
1. "Oturum başlat"tan sonra panel **donmuyor**, deney ayrı pencerede.
2. Her modül yönergesiyle açılıyor, moduna uygun soruyu soruyor.
3. Molalar `break_every_n_trials`'da geliyor.
4. Katılımcıya **başarı yüzdesi / doğru-yanlış gösterilmiyor**.
5. Ses doğru kulaktan geliyor (lateralize denemeler).
6. Bitişte yedek yazıldı, deney penceresi temiz kapandı, panel çalışıyor.
7. Katılımcıya gösterilen **hiçbir metin koda gömülü değil** (Türkçe, config'ten).

**Başarısızsa:** hangi modül, ne oldu — not alın; **her bug master merge öncesi
düzeltilir.**

## Test 2: Oturum sonrası — panel butonları (~3 dk)
Panelde **Yenile** → oturumu seçin:
1. **QC raporu** → zamanlama (düşen kare/SOA), zaman aşımı oranı, yanıt dağılımı;
   (SSD ise) çapraz dinleme yargısı.
2. **Analiz** → modül ölçütleri (McGurk oranları, AVSR fayda vb.).
3. **Dışa aktar...** → klasör seç → `trials_flat.csv` açılıyor; **`participants.csv`'de
   ad yok** (KVKK).
4. **Yedek doğrula...** → son yedek kullanılabilir mi.

**Kontrol:** Sonuçlar listesi **anonim**; hiçbir ekranda ad yok. Uzun işlerde panel
donmuyor.

## Test 3: Kasıtlı bozma senaryoları (~10 dk)
Her biri **açık davranış** göstermeli:

### 3a. Kes → panelden devam et
- **Oturum başlat** (`PROVA-02`), birkaç modül sonra deney penceresinde
  **`ESC` → Evet**. Beklenen: onay ekranı; onayınca `aborted`, veri korunur, yedek
  yazılır. Panelde **Yenile** → o oturum `aborted`. Tekrar **Oturum başlat** → aynı
  kod → **"kaldığı yerden devam?"** → devam; tamamlanan modüller atlanır.

### 3b. Yanıt verme (zaman aşımı)
- Bir forced-choice denemesinde (mcgurk/avsr) **hiç yanıt vermeyin**. Beklenen:
  zaman aşımı; `responses` satırı yok; **QC raporu**nda o modülün zaman aşımında
  görünür, McGurk'te `NONE`.

### 3c. Uyaran eksik
- **Uyaranları doğrula** — set eksikse **KIRMIZI/hata**, oturum başlamaz.

### 3d. Ses aygıtı yok
- Kulaklığı çıkarın/kapatın → **Kontrol listesi** KIRMIZI (ses aygıtı); tam oturumda
  **Oturum başlat** deneyi açık `AudioError` ile durur (sessiz geri düşüş yok).

---

## Kabul kriterleri
- [ ] Operatör her şeyi **panelden/exe'den, komut yazmadan** yaptı (mini provanın
      `--limit` terminal koşusu hariç)
- [ ] Tam oturum baştan sona çalıştı, süre ölçüldü (~75–80 dk hedefi)
- [ ] Panel "Oturum başlat"ta donmadı; deney ayrı süreçte açıldı
- [ ] Katılımcıya gösterilen hiçbir metin koda gömülü değil; başarı yüzdesi yok
- [ ] Kesip devam ettirme panelden çalışıyor, veri kaybı yok (3a)
- [ ] Zaman aşımı `NONE`/yanıtsız kaydediliyor (3b)
- [ ] Eksik uyaran (3c) ve ses aygıtı kaybı (3d) açık hata
- [ ] QC/Analiz/Dışa aktar/Sonuçlar anonim, anlamlı çıktı
- [ ] Bulunan buglar düzeltildi

**Bu adım geçince:** `develop → master` merge + `git tag v1.0.0` (onayınızla).
**v1.0.0 = dağıtılabilir Windows uygulaması.**
