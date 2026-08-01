# Adım 11 Manuel Test — Operatör panelinde "Ayarlar" sekmesi

Panele **"Ayarlar"** sekmesi eklendi: modül başına **tekrar sayıları** artık
`config/experiment.yaml` elle düzenlenmeden, spinbox'larla ayarlanıyor. Değer
değiştikçe **toplam deneme / süre canlı** güncelleniyor; **Kaydet** dosyaya
yazıyor (**yorumlar korunarak**), **Varsayılana dön** fabrika değerlerini
getiriyor.

**Ekran gerekir. Süre ~10 dk.** Ses/deney penceresi gerekmez.

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| Tüm testler (yerel, PsychoPy'li) | **939 passed, 59 skipped** |
| CI alt kümesi (PyQt6'sız/PsychoPy'siz venv) | **896 passed, 58 skipped** |
| `ruff` + `mypy` | temiz — hem yerel hem Qt'siz CI venv'inde |
| Yeni dosyalar | `mcgurk/config/edit.py`, `config/experiment.defaults.yaml`, `tests/mcgurk/test_config_edit.py` |
| Yeni testler | 27 (config düzenleme) + 8 (panel çekirdeği) + 7 (Ayarlar sekmesi smoke) |
| Benim açılış denemem | Panel offscreen açıldı; 11 spinbox doğru değerlerle doldu, canlı toplam 797 -> 897 (oddball 300 -> 400) güncellendi |
| Paketleme (§E11.1) | `.exe` yeniden derlendi (2026-08-02): `ruamel` (32 dosya) + `experiment.defaults.yaml` bundle'da; donmuş panel açılıyor; `--run checklist` çıkış 0. **Test 8 kullanıcı tarafından geçildi.** |

## Ön koşullar

- [ ] Komutlar **PowerShell**'de. Doğru yorumlayıcı:

```powershell
$PY = "C:\Users\tayla\miniconda3\envs\mcgurk\python.exe"
```

- [ ] **Yeni bağımlılık kuruldu mu?** `ruamel.yaml` eklendi (YAML'ı yorumları
      koruyarak yazmak için). Kurulu değilse panel açılmaz:

```powershell
& $PY -m pip install -r requirements.txt
```

- [ ] **Config'inizin bir yedeğini alın** — testler dosyayı gerçekten
      değiştiriyor. Test bitince geri alacağız, ama emniyet için:

```powershell
Copy-Item config\experiment.yaml config\experiment.yaml.yedek
```

---

## Test 1: Sekme açılıyor, alanlar dolu (~2 dk)

**Komut:**
```powershell
& $PY -m mcgurk.panel
```

**Beklenen:** Pencerenin üstünde iki sekme: **Panel** ve **Ayarlar**. "Panel"
sekmesi Adım 10'daki hâliyle duruyor (aksiyon çubuğu, Sonuçlar tablosu, Çıktı).

**Adım:** **Ayarlar** sekmesine geçin.

**Kontrol edilecek:**
- En üstte uyarı: değişikliklerin yalnızca **bundan sonraki** oturumları
  etkilediği, geçmiş verilerin değişmediği yazıyor.
- Modüle göre gruplar ve şu değerler:

| Grup | Alan | Değer |
|---|---|---|
| Alıştırma | Alıştırma denemesi | 12 |
| Modül 1 — McGurk | fusion_pair (V:ga / A:ba) | 10 |
| | combination_pair (V:ba / A:ga) | 10 |
| | congruent_ba / da / ga | 5 / 5 / 5 |
| Modül 2 — AVSR | Hece seti (ba, da, ga) | 5 |
| Modül 3 — TBW | SOA değeri başına tekrar | 10 |
| Modül 4 — Oddball | Toplam ton sayısı | 300 |
| Modül 5 — Dikotik dinleme | Çift başına tekrar | 5 |
| Çapraz dinleme kontrolü | Deneme sayısı | 20 |

- **Modül 6 — GIN** grubu **soluk/pasif**: "değiştirilemez", 30 segment,
  boşluk başına 6 sunum, `4_of_6` eşik kuralı yazıyor. Spinbox **yok**.
- En altta özet: `TOPLAM: 797 deneme / yaklaşık 58.8 dk`.
- En altta düzenlenen dosyanın tam yolu görünüyor
  (`...\mcgurk\config\experiment.yaml`).
- Her satırın yanında ne ile çarpıldığını söyleyen soluk açıklama var.
- Bütün metinler **Türkçe**, Türkçe karakterler düzgün.

**Başarısızsa:** ekran görüntüsü + terminaldeki hata.

---

## Test 2: Canlı toplam (kaydetmeden) (~2 dk)

**Adım:** **Modül 3 — TBW**'nin "SOA değeri başına tekrar" değerini `10` -> `20`
yapın (okla veya yazarak).

**Beklenen:** Alt satır anında değişir: `tbw` 130 -> **260**, TOPLAM 797 ->
**927**, süre 58.8 -> **70.7 dk**.

**Kontrol edilecek:**
- Toplam **yazmadan** güncelleniyor.
- **Başka bir terminalde** config'e bakın — henüz değişmemiş olmalı:

```powershell
Select-String -Path config\experiment.yaml -Pattern "reps_per_soa"
```
`reps_per_soa: 10` görmelisiniz (20 değil).

**Adım:** Değeri `10`'a geri alın; TOPLAM tekrar 797 olsun.

---

## Test 3: Geçersiz değer toplam yerine uyarı veriyor (~1 dk)

**Adım:** **Modül 4 — Oddball**'da "Toplam ton sayısı"nı `1` yapın.

**Beklenen:** Alt satırda toplam yerine **`Geçersiz değer: ...`** ile başlayan
Türkçe açıklama çıkar (1 deneme x %18 hedef oranı = hiç hedef üretilemez).

**Adım:** `300`'e geri alın; toplam geri gelsin.

---

## Test 4: Kaydet — yorumlar korunuyor (~3 dk)

**Adım:**
1. **Modül 5 — Dikotik dinleme**'de "Çift başına tekrar"ı `5` -> `8` yapın
   (TOPLAM 797 -> 815 olmalı).
2. **Kaydet**'e basın.

**Beklenen:**
- Durum çubuğunda `Ayarlar kaydedildi - 815 deneme`.
- **Panel** sekmesindeki Çıktı bölümünde `[Ayarlar] kaydedildi: <yol> (815 deneme)`.

**Kontrol edilecek (PowerShell'de):**

```powershell
Select-String -Path config\experiment.yaml -Pattern "reps: 8"
git diff --stat config\experiment.yaml
```

- `reps: 8` yazıyor.
- `git diff` **tek satırlık** olmalı (`1 insertion, 1 deletion`) — yani yalnız
  değişen anahtar değişmiş, dosyanın kalanına dokunulmamış.

```powershell
git diff config\experiment.yaml
```
- Diff'te yalnız `-    reps: 5` / `+    reps: 8` görünmeli.
- Yorum satırları (`# 6 pairs x 5 = 30 trials...` gibi) **yerinde**.

**Adım:** Doğrulama olarak tasarım özetini bastırın:

```powershell
& $PY -m mcgurk.config
```
`dichotic` satırı **48** deneme, TOPLAM **815** göstermeli — panelin gösterdiğiyle
birebir aynı.

---

## Test 5: Geçersiz kayıt diski bozmuyor (doğrula-geri-al) (~2 dk)

**Adım:**
1. **Modül 4 — Oddball**'da "Toplam ton sayısı"nı `2` yapın.
2. **Kaydet**'e basın.

**Beklenen:**
- **Hata diyaloğu** çıkar; metin "…geri alındı" diyor ve nedeni açıklıyor.
- Diyaloğu kapatın.

**Kontrol edilecek:**

```powershell
Select-String -Path config\experiment.yaml -Pattern "n_trials: "
& $PY -m mcgurk.config
```
- `n_trials: 300` (2 değil) — dosya eski hâlinde.
- `python -m mcgurk.config` **hatasız** çalışıyor, yani diskte bozuk config yok.
- `config\` klasöründe `*.tmp` artığı yok:

```powershell
Get-ChildItem config\*.tmp
```
(hiçbir şey dönmemeli)

**Adım:** Oddball'ı `300`'e geri alın.

---

## Test 6: Varsayılana dön (~2 dk)

**Adım:** **Varsayılana dön** butonuna basın.

**Beklenen:** Onay soruluyor ("…dosyaya YAZMAZ; değerleri görüp Kaydet'e
basmanız gerekir"). **Evet** deyin.

**Kontrol edilecek:**
- Dikotik "Çift başına tekrar" **8 -> 5**'e döndü, TOPLAM tekrar **797**.
- Durum çubuğu: `Varsayılan değerler yüklendi - kaydetmek için Kaydet`.
- **Henüz dosyaya yazılmadı**: `Select-String -Path config\experiment.yaml
  -Pattern "reps: 8"` hâlâ 8'i bulmalı.

**Adım:** **Kaydet**'e basın.

**Kontrol edilecek:**

```powershell
git diff config\experiment.yaml
```
- **Boş** olmalı — dosya tamamen başlangıçtaki hâline döndü (yorumlar dahil,
  bayt bayt).

Diff boş değilse yedeği geri koyun ve bildirin:
```powershell
Copy-Item config\experiment.yaml.yedek config\experiment.yaml -Force
```

---

## Test 7: Panel sekmesi bozulmadı (~1 dk)

**Adım:** **Panel** sekmesine dönün.

**Kontrol edilecek:** Adım 10b'deki her şey yerinde ve çalışıyor:
- **Oturum başlat / Kontrol listesi / Uyaranları doğrula / Yedek doğrula...**
- Sonuçlar tablosu + **Yenile / Analiz / QC raporu / Dışa aktar... / Sil...**
- **Kontrol listesi**'ne basın: rapor Çıktı bölümüne akıyor, bu sırada
  **Ayarlar sekmesindeki Kaydet ve Varsayılana dön de kilitli** (işlem bitince
  açılıyor).

---

## Test 8: Paketlenmiş app (`.exe`) — §E11 (~10 dk, isteğe bağlı ama önerilir)

Bu test **ruamel'in bundle'a girip girmediğini** ve **donmuş app'te config'in
doğru (yazılabilir) konuma yazıldığını** doğrular. Yalnız `.exe` dağıtacaksanız
gerekli.

> **DİKKAT — derleme `dist\McGurkSSD\` klasörünün TAMAMINI siler:** oraya
> kopyaladığınız `stimuli\`, oluşan `config\`, `data\`, `backups\`, `logs\`
> dahil. Bu yüzden **ben derlemedim**. Devam etmeden önce saklamak
> istediklerinizi taşıyın:
>
> ```powershell
> Move-Item dist\McGurkSSD\stimuli $env:TEMP\mcgurk_stimuli_yedek
> Copy-Item dist\McGurkSSD\data,dist\McGurkSSD\backups $env:TEMP -Recurse -EA SilentlyContinue
> ```

**Adım:**
```powershell
& $PY tools\build_exe.py --clean
```
Derleme bitince `stimuli\` klasörünü geri koyun (packaging\README.md), sonra
`McGurkSSD.exe`'ye çift tıklayın:

```powershell
Move-Item $env:TEMP\mcgurk_stimuli_yedek dist\McGurkSSD\stimuli
```

**Kontrol edilecek:**
- **Ayarlar** sekmesi açılıyor, alanlar dolu.
- Alt satırdaki "Düzenlenen dosya" yolu **`dist\McGurkSSD\config\experiment.yaml`**
  (bundle'ın içi değil).
- Bir değeri değiştirip **Kaydet** -> hata yok, o dosyada değer değişmiş,
  yorumlar duruyor (ruamel bundle'lanmış demektir).
- **Varsayılana dön** çalışıyor (`experiment.defaults.yaml` bundle'lanmış demektir).
- `Kaydet` sonrası `.exe`'den bir oturum başlatınca yeni deneme sayısı geçerli.

**Başarısızsa:** derleme çıktısındaki eksik import satırını bildirin
(`ruamel` / `ruamel.yaml.clib` geçiyorsa `mcgurk.spec`'ten çözülür).

---

## Temizlik

```powershell
git diff config\experiment.yaml     # boş olmalı
Remove-Item config\experiment.yaml.yedek
```

---

## Kabul kriterleri

- [ ] Ayarlar sekmesi açılıyor, alanlar mevcut config değerleriyle dolu (Test 1)
- [ ] Değer değişince toplam/süre canlı güncelleniyor, dosyaya yazılmıyor (Test 2)
- [ ] Geçersiz değer toplam yerine Türkçe uyarı veriyor (Test 3)
- [ ] Kaydet config'e yazıyor, **yorumlar korunuyor**, diff tek satır (Test 4)
- [ ] Geçersiz kayıt diski bozmuyor, dosya geri alınıyor (Test 5)
- [ ] "Varsayılana dön" onaylı çalışıyor, kaydedince dosya birebir eski hâline
      dönüyor (Test 6)
- [ ] Panel sekmesi ve tüm Adım 10 işlevleri bozulmamış (Test 7)
- [ ] (Paketleyecekseniz) `.exe`'de Ayarlar + Varsayılana dön çalışıyor (Test 8)
