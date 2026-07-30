# Adım 9c Manuel Test — Prova Oturumu

Adım 9'un **kabul kapısı**: gerçek bir kişiyle, `docs/OPERATOR_SOP.md` takip
edilerek, baştan sona tam bir oturum. Otomatik uçtan uca test bunun yerine
**geçmez** — insan akışı, süre, kulaklık yerleşimi, yönerge anlaşılırlığı ve
gerçek RT ancak burada görülür.

> **Bu bir "iş akışı provasıdır", gerçek veri toplama DEĞİL.** Fotodiyot ölçümü
> (`docs/01`) ve ses kalibrasyonu (`docs/02`) henüz yapılmadı, o yüzden oturum
> **development modunda** koşulur (`experiment.mode: development`). Toplanan veri
> bilimsel analiz için kullanılmaz; amaç akışın ve araçların baştan sona
> çalıştığını görmek.

## Ön koşullar

- [ ] Conda ortamı etkin (`C:\Users\tayla\miniconda3\envs\mcgurk`), ses aygıtı bağlı.
- [ ] Uyaran seti hazır: `python tools/verify_stimuli.py` → çıkış 0.
- [ ] `config/experiment.yaml` → `experiment.mode: development`.
- [ ] Gerçek bir katılımcı (kendiniz veya bir gönüllü). **Yaş 18–60** olmalı
      (`participants.age` CHECK); değilse kısıt geçici gevşetilmeli.
- [ ] Operatör `docs/OPERATOR_SOP.md`'yi önceden okudu. **McGurk etkisi
      katılımcıya ASLA önceden anlatılmaz.**
- [ ] Sessiz oda, kulaklık (sol=sol, sağ=sağ).
- [ ] Kronometre (süre ölçümü için).

---

## Test 1: Baştan sona tam oturum (~75–80 dk)

**Komut:**
```bash
python main.py
```

**Adımlar (operatör SOP'u takip eder):**
1. Giriş formu: **anonim kod** (ör. `PROVA-01`), grup, yaş, cinsiyet, deprivasyon,
   PTA. Ad-soyad alanı **yok**.
2. Oturum öncesi kontrol onayı ekranı.
3. Alıştırma bloğu.
4. Modüller sırayla (yönerge ekranları + molalar): mcgurk → avsr → tbw → oddball
   → dichotic → gin (config'teki `module_order`).
5. **Çapraz dinleme kontrolü** — yalnız grup SSD (`SSD_R`/`SSD_L`) seçilirse çalışır.
6. Bitiş ekranı + **otomatik yedek**.

**Kronometreyle ölçün:** toplam süre, ve mümkünse modül başına süre.

**Kontrol edilecek:**
1. Her modül yönergesiyle açılıyor, moduna uygun soruyu soruyor (V-only'de "ne
   gördünüz", A-only'de "ne duydunuz" vb.).
2. Molalar `break_every_n_trials`'da geliyor.
3. Katılımcıya hiçbir yerde **başarı yüzdesi / doğru-yanlış** gösterilmiyor.
4. Ses doğru kulaktan geliyor (lateralize denemelerde).
5. Bitişte yedek yazıldı (`backups/` altında yeni dosya), çıkış kodu 0.
6. Katılımcıya gösterilen **hiçbir metin koda gömülü değil** (hepsi Türkçe, config'ten).

**Başarısızsa:** hangi modülde, ne oldu — not alın. Bulunan **her bug bu adımda
düzeltilir** (master merge öncesi).

---

## Test 2: Oturum sonrası araçlar (~3 dk)

Oturum bittikten sonra, operatörün yapacağı işler:

```bash
python tools/qc_report.py
```
**Kontrol edilecek:** zamanlama (düşen kare/SOA), zaman aşımı oranı, yanıt
dağılımı; (SSD ise) çapraz dinleme yargısı. Anlamlı çıktı veriyor mu.

```bash
python tools/analyse.py
```
**Kontrol edilecek:** oturumun modül ölçütleri (McGurk oranları, AVSR fayda vb.).

```bash
python tools/export_data.py --out data/export
```
**Kontrol edilecek:** `trials_flat.csv` yazıldı, açılıyor, `participants.csv`'de
ad yok (KVKK).

---

## Test 3: Kasıtlı bozma senaryoları (~10 dk)

Her biri **açık davranış** göstermeli, sessizce bozulmamalı:

### 3a. Oturumu ortada kes → devam et
- Yeni bir oturum başlatın (`PROVA-02`), birkaç modül sonra **`ESC` → Evet**.
- **Beklenen:** "çıkmak istediğinize emin misiniz?" onayı; onayınca oturum
  `aborted`, o ana kadarki veri korunur, yedek yazılır, çıkış kodu 2.
- Aynı kod (`PROVA-02`) ile yeniden başlatın → **"kaldığı yerden devam?"** teklifi.
  Devam edin; **tamamlanan modüller atlanıyor**, aynı oturum numarası.

### 3b. Yanıt verme (zaman aşımı)
- Bir forced-choice denemesinde (mcgurk/avsr) **hiç yanıt vermeyin**.
- **Beklenen:** deneme zaman aşımına uğrar, `responses` satırı yazılmaz;
  `qc_report.py`'de o modülün zaman aşımı oranında görünür, McGurk'te `NONE`.

### 3c. Uyaran dosyası eksik (başlamadan yakalanır)
- (İsteğe bağlı) `config/experiment.yaml`'de `av_pairs`'e hazırlanmamış bir token
  ekleyin (ör. `visual: zz`) ve `python -m mcgurk.config` çalıştırın.
- **Beklenen:** config **yüklenirken açık hata** — katılımcı oturmadan yakalanır.
  (Testten sonra değişikliği geri alın.)

### 3d. Ses aygıtı yok
- (İsteğe bağlı) Kulaklığı çıkarın/kapatın ve bir modül koşmayı deneyin
  (`python tools/run_module.py --module mcgurk --limit 2`).
- **Beklenen:** açık `AudioError`; sessiz geri düşüş **yok**.

---

## Kabul kriterleri

- [ ] Tam oturum baştan sona çalıştı, süre ölçüldü (~75–80 dk hedefi)
- [ ] Katılımcıya gösterilen hiçbir metin koda gömülü değil; başarı yüzdesi yok
- [ ] Kesip devam ettirme çalışıyor, veri kaybı yok (3a)
- [ ] Zaman aşımı `NONE`/yanıtsız olarak kaydediliyor (3b)
- [ ] Eksik uyaran başlatmadan yakalanıyor (3c), ses aygıtı kaybı açık hata (3d)
- [ ] `qc_report.py` / `analyse.py` / `export_data.py` oturum sonrası anlamlı çıktı veriyor
- [ ] Bulunan buglar düzeltildi

**Bu adım geçince:** `develop → master` merge + `git tag v1.0.0` (onayınızla).
Ardından **Adım 10** (operatör paneli + `.exe` paketleme).
