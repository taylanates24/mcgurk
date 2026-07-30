# Adım 8a Manuel Test — Oturum metinleri + `python -m mcgurk.checklist`

Adım 8'in ilk alt adımı. İki parça:

1. **Config'e katılımcı-metinleri** (`screens:` bölümü) — yönergeler, mola,
   alıştırma, çapraz dinleme metinleri. Bunlar 8b'de ekrana gelecek; 8a yalnızca
   şemayı ve içeriği ekliyor.
2. **`python -m mcgurk.checklist`** — operatörün her `data_collection` oturumu
   öncesi çalıştıracağı YEŞİL/KIRMIZI ön-uçuş.

Bu alt adımda **katılımcıya ekran sunulmuyor**; testlerin çoğu komut satırında
koşar. Tek ekran/ses gerektiren kısım checklist'in donanım probu (Test 3).

**Toplam süre ~3 dakika.**

## Otomatik koşulanlar (bilgi için, sizin yapmanıza gerek yok)

| Ne | Sonuç |
|---|---|
| Otomatik testler | **736 test yeşil** (CI alt kümesi); `ruff` + `mypy` temiz |
| Yeni testler | `test_config_screens.py` (8) + `test_checklist.py` (10) |
| Config kapıları | etkin modülün yönergesi eksikse / boşsa / `practice`'e yönerge yazılırsa / `cross_hearing_intro` eksikse **yükleme reddediliyor** |
| Checklist kapıları | kalibrasyon yok/bozuk/eski → KIRMIZI; uyaran manifest eksik → KIRMIZI; disk yetersiz → KIRMIZI; eşik değerleri config'ten |
| Konsol güvenliği | checklist'in bastığı her metin cp1254 (Türkçe Windows konsolu) ile uyumlu — `test_console_encoding.py` her koşuda doğruluyor |

**Önemli tasarım kararı:** Checklist'in kontrolleri **saf** (dosya) ve
**donanım** (ses + pencere) diye ikiye ayrıldı. Saf kontroller PsychoPy'siz
CI'da koşar; zorunlu kabul kriteri testi ("eksik/eski kalibrasyon → KIRMIZI,
oturumu engelle") böylece donanımsız doğrulanabiliyor.

## Ön koşullar

- [ ] Conda ortamı etkin: `C:\Users\tayla\miniconda3\envs\mcgurk`
      (aktif değilse komutlardaki `python` yerine
      `C:\Users\tayla\miniconda3\envs\mcgurk\python.exe` yazın)
- [ ] Komutlar **PowerShell** içindir (bu makinenin birincil kabuğu). Bash
      sözdizimi (`&&`, `$(...)`) PowerShell 5.1'de çalışmaz.

---

## Test 1: Dev modda checklist (donanımsız, ~10 sn)

**Komut:**

```powershell
python -m mcgurk.checklist --no-hardware
```

**Beklenen çıktı (benzeri):**

```
Oturum öncesi kontrol — mcgurk_ssd v1.0.0 (development)
=======================================================
UYARI    Mod
         development — kapılar uygulanmaz. Veri toplamak için config'te ...
UYARI    A/V gecikmesi (D)
         ölçülmedi (fotodiyot, docs/01_av_gecikme_olcumu.md). ...
UYARI    Kalibrasyon
         dosya belirtilmemiş (development). ...
YESIL    Uyaran seti
         manifest ve dosyalar yerinde (hızlı kontrol).
YESIL    Disk ve yedek klasörü
         ..... MB boş, yedek klasörü yazılabilir.
YESIL/UYARI  Son yedek
         mcgurk_....sqlite   (ya da "henüz yedek yok")
-------------------------------------------------------
SONUÇ: KIRMIZI yok (3 uyarı).
```

**Kontrol edilecek:**

1. **Mod, A/V gecikmesi ve Kalibrasyon `UYARI`** (KIRMIZI değil) — development'ta
   bunlar zorunlu değildir, o yüzden oturumu engellemezler.
2. **Uyaran seti `YESIL`** (bu makinede `stimuli/` hazır). Değilse `KIRMIZI`
   görünür ve `python tools/verify_stimuli.py`'ye yönlendirir.
3. **SONUÇ satırı "KIRMIZI yok"** ve komutun çıkış kodu 0.

Çıkış kodunu görmek için (isteğe bağlı):

```powershell
python -m mcgurk.checklist --no-hardware; "EXIT=$LASTEXITCODE"
```

`EXIT=0` bekleniyor. (PowerShell'de çıkış kodu `$LASTEXITCODE`'tadır; `$?`
bir True/False değeridir, çıkış kodu değil.)

---

## Test 2: Eksik data_collection config → KIRMIZI ve oturum engeli (~10 sn)

Bu, adımın **zorunlu kabul kriteri**: eksik bir `data_collection` config'i
başlatılamaz. Config'te hiçbir kalıcı değişiklik yapmadan, geçici bir kopyada
`mode`'u `data_collection`'a çevirip checklist'i koşuyoruz.

**Komut (PowerShell):**

```powershell
$tmp = Join-Path $env:TEMP 'dc_test.yaml'; (Get-Content config\experiment.yaml -Raw -Encoding utf8) -replace 'mode: development','mode: data_collection' | Set-Content $tmp -Encoding utf8; python -m mcgurk.checklist --config $tmp --no-hardware; "EXIT=$LASTEXITCODE"; Remove-Item $tmp
```

**Beklenen çıktı:**

```
KIRMIZI  Config yüklenemedi:
Config doğrulaması başarısız: ...
  - (kök): Value error, mode: data_collection için eksikler:
  - timing.system_av_offset_ms boş — fotodiyot ölçümü yapılmadan ...
  - audio.calibration_file boş — ses kalibrasyonu yapılmadan ...
EXIT=1
```

**Kontrol edilecek:**

1. **Çıkış kodu `EXIT=1`** — eksik data_collection config'i geçmez.
2. Mesaj **hangi alanların eksik olduğunu tek tek** söylüyor (fotodiyot ölçümü
   ve kalibrasyon dosyası) — operatör tek tek düzeltip yeniden koşmak zorunda
   kalmasın diye hepsi bir arada.

**Başarısızsa:** `EXIT=0` çıkarsa ya da mesaj eksik alanları söylemiyorsa
bildirin.

---

## Test 3 (ekran + ses gerektirir): checklist donanım probu (~30 sn)

`--no-hardware` olmadan çalıştırıldığında checklist ayrıca **ses aygıtını** ve
**gerçek yenileme hızını** kontrol eder — bunun için kısa süreliğine tam ekran
bir pencere açar ve ses aygıtını açar.

**Ön koşul:** Kulaklık/aygıt bağlı ve `config/experiment.yaml`'daki
`audio.device` onu gösteriyor olmalı. Aygıt listesi:

```powershell
python tools/timing_selftest.py --devices
```

**Komut:**

```powershell
python -m mcgurk.checklist
```

Test 1'deki satırlara ek olarak iki satır daha çıkar:

```
YESIL    Ses backend ve aygıt
         ptb, aygıt: <aygıt adı>
YESIL    Yenileme hızı
         ölçülen 75.0 Hz, beklenen 75 Hz
```

**Kontrol edilecek:**

1. **Ses backend ve aygıt `YESIL`** ve aygıt adı beklediğiniz kulaklık.
   Bluetooth kulaklık **kapalıysa** ya da eşleşmemişse burada `KIRMIZI` çıkar ve
   aygıtın bağlı olmadığını söyler — bu doğru davranıştır.
2. **Yenileme hızı** satırı: bu monitör 75 Hz ise `YESIL`. Monitörünüz 60 Hz
   ise `config/experiment.yaml`'daki `display.expected_refresh_hz` ile
   uyuşmadığı için `KIRMIZI` çıkar (sapma) — bu da doğru davranış; gerçek
   monitörde `expected_refresh_hz` doğru ayarlanmalı.
3. Pencere ölçüm biter bitmez kapanıyor; takılıp kalmıyor.

**Başarısızsa:** Pencere açılmıyor veya program çöküyorsa (KIRMIZI satır yerine
traceback) bildirin — donanım probu her hatayı KIRMIZI satıra çevirmeli, asla
çökmemeli.

---

## Kabul kriterleri

- [ ] Test 1: dev modda Mod/A-V/Kalibrasyon UYARI, uyaran YESIL, SONUÇ "KIRMIZI
      yok", çıkış 0
- [ ] Test 2: eksik data_collection config'i çıkış 1 veriyor ve eksik alanları
      tek tek söylüyor
- [ ] Test 3 (donanım): ses aygıtı ve yenileme hızı kontrolleri çalışıyor,
      pencere açılıp kapanıyor, program çökmüyor
- [ ] (Bilgi) `screens:` bölümü config'te; `python -m mcgurk.config` hâlâ
      geçerli tasarım özetini basıyor
