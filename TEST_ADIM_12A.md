# Adım 12a Manuel Test — Konuşmacı seti 2'den 8'e

Menünün (12b/12c) seçeceği konuşmacılar hazırlandı: `speakers/` altındaki teslim
klasöründen **yalnız uyumlu takeler** `assets/`'e ayıklandı, klasörler
`speaker_<id>_<cinsiyet>` adına geçirildi, sekiz konuşmacılık uyaran seti
üretildi ve doğrulandı.

Bu sırada **ölçüm katmanında bir kusur bulundu ve düzeltildi** (aşağıda) — bu
adımın en önemli çıktısı odur.

**Ekran/ses gerekmez.** Hepsi konsolda. Süre ~15 dk (uyaran hazırlığı ~6 dk).

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| `pytest -m "not psychopy"` | **953 passed, 26 skipped** |
| `ruff check .` | temiz |
| `mypy` | temiz (132 dosya) |
| `python -m mcgurk.config` | **797 deneme / 58.8 dk** — değişmedi |
| `tools/verify_stimuli.py` | **UYARAN SETİ KULLANILABİLİR** (çıkış 0) |
| Yeni dosyalar | `mcgurk/stimuli/import_sources.py`, `tools/import_speakers.py`, `tests/mcgurk/test_stimuli_import_sources.py` |
| Hazır set | 70 MB → **185 MB**, 141 → **393 dosya** |

## Ön koşullar

- [ ] Komutlar **PowerShell**'de. Doğru yorumlayıcı:

```powershell
$PY = "C:\Users\tayla\miniconda3\envs\mcgurk\python.exe"
```

- [ ] `assets/` ve `stimuli/` bu makinede güncellendi (ben koştum). Testler
      mevcut hâli **doğruluyor**, yeniden üretmiyor — Test 4 hariç.

---

## Test 1: Sekiz konuşmacı config'te ve etiketli (~1 dk)

**Komut:**
```powershell
& $PY -X utf8 -c "from mcgurk.config.loader import load_config; c=load_config(check_filesystem=False); [print(s.id, s.label, s.source) for s in c.stimulus_prep.speakers]"
```

(`-X utf8` sadece bu satır için: etiketlerdeki uzun tire konsolun kod
sayfasına takılmasın.)

**Beklenen çıktı:**
```
1 Konuşmacı 1 — Kadın assets\speaker_1_female
2 Konuşmacı 2 — Erkek assets\speaker_2_male
3 Konuşmacı 3 — Erkek assets\speaker_3_male
4 Konuşmacı 4 — Erkek assets\speaker_4_male
5 Konuşmacı 5 — Kadın assets\speaker_5_female
6 Konuşmacı 6 — Kadın assets\speaker_6_female
7 Konuşmacı 7 — Erkek assets\speaker_7_male
8 Konuşmacı 8 — Kadın assets\speaker_8_female
```

**Kontrol edilecek:** Cinsiyetler sizin verdiğiniz listeyle aynı mı —
**2, 3, 4, 7 erkek; 1, 5, 6, 8 kadın**. Etiketler operatörün menüde göreceği
adlardır; yanlışsa şimdi söyleyin, 12c'de menüye bunlar yazılacak.

**Başarısızsa:** `config/experiment.yaml` → `stimulus_prep.speakers`.

---

## Test 2: İçe aktarma tekrar koşturulabilir ve hiçbir şeyi bozmuyor (~1 dk)

**Komut:**
```powershell
& $PY tools\import_speakers.py --dry-run
```

**Beklenen çıktı (son satırlar):**
```
Kopyalanacak  : 0
Atlandı       : 24

SONUÇ: DENEME (hiçbir dosya yazılmadı)
```

**Kontrol edilecek:** 24 satırın hepsi `zaten var (aynı içerik)` diyor —
yani `assets/` ile teslim klasörü birebir aynı. **Kopyalanacak 0** olmalı: iş
zaten yapıldı, araç ikinci kez hiçbir şey yazmıyor.

**Başarısızsa:** `kopyalanacak` çıkan bir satır varsa o dosya eksik demektir;
`FARKLI içerik` çıkarsa araç zaten durur — o dosyayı elle inceleyin.

---

## Test 3: Konuşmacı 1 ve 2'nin ham kayıtları değişmedi (~1 dk)

Bu adımın kırmızı çizgisi: mevcut iki konuşmacının dosyalarına dokunulmadı.

**Komut:**
```powershell
& $PY -c "import hashlib,pathlib; f=lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]; [print(t, f(f'assets/speaker_1_female/Vis-{t}_Aud-{t}.mp4'), f(f'speakers/Vis-{t}_Aud-{t}_Speaker-1.mp4')) for t in ('ba','da','ga')]"
```

**Beklenen çıktı:** her satırda **iki sağlama toplamı da aynı**:
```
ba 4d7193b2ecaee914 4d7193b2ecaee914
da 0eef2af2f0ca8bce 0eef2af2f0ca8bce
ga 7a2240f3bfac4566 7a2240f3bfac4566
```
(`4d7193b2ecae…` bu adımdan **önceki** manifest'in konuşmacı 1 /ba/ kaynağı
için kaydettiği değerin aynısıdır.)

**Kontrol edilecek:** Klasör adı değişti (`female_speaker_1` →
`speaker_1_female`), **içerik değişmedi**.

---

## Test 4: Set sıfırdan yeniden üretilebiliyor (~8 dk, isteğe bağlı)

Bu, "bende çalışıyor"u "yeniden üretilebilir"e çeviren testtir. Uzun sürer;
atlarsanız Test 5 yine de mevcut seti doğrular.

**Komut:**
```powershell
Remove-Item -Recurse -Force stimuli
& $PY tools\prepare_stimuli.py
```

**Beklenen çıktı (son satırlar):**
```
Video           : 24
Ses (hizalı)    : 72
Ses (gürültülü) : 216
Dikotik         : 48
GIN segmenti    : 30
Oddball tonu    : 2 (1000, 1500 Hz)
SSN             : 1 (en büyük LTAS sapması 0.42 dB)

SONUÇ: UYARAN SETİ HAZIR
```

**Kontrol edilecek:** Hiçbir konuşmacıda durmadı. Sayılar tam olarak yukarıdaki
gibi (8 konuşmacı × 3 token = 24 video, × 3 ses = 72 token, × 3 SNR-örneği = 216).

**Başarısızsa:** Hata mesajı hangi dosyada durduğunu ve toleransı söyler. Bana
**mesajın tamamını** iletin — sessizce geçmek yasak, o yüzden durur.

---

## Test 5: Doğrulama temiz (~3 dk)

**Komut:**
```powershell
& $PY tools\verify_stimuli.py
```

**Beklenen çıktı:**
```
YESIL    393 dosya yerinde, sağlama toplamları uyuşuyor
YESIL    Etkin modüllerin istediği her uyaran manifest'te var
YESIL    24 video sessiz, CFR ve tam kare sayısında
YESIL    72 ses dosyası hizalı (en büyük sapma 0.0 ms) ve eşit seviyede
...
SONUÇ: UYARAN SETİ KULLANILABİLİR
```

**Kontrol edilecek:** **"en büyük sapma 0.0 ms"** satırı. Bu adımdan önce bu
sayı 0 değildi ve konuşmacı 4'te toleransı aşıyordu; ölçüm düzeltmesinin sonucu
tam olarak bu satırdır.

**Başarısızsa:** tek bir KIRMIZI satır bile "set kullanılamaz" demektir.

---

## Test 6: Tasarım büyümedi (~1 dk)

**Komut:**
```powershell
& $PY -m mcgurk.config
```

**Beklenen çıktı (son satırlar):**
```
TOPLAM               797         58.8 dk
```

**Kontrol edilecek:** Konuşmacı sayısı 4 katına çıktı, **deneme sayısı aynı
kaldı**. Oturum başına tek konuşmacı kullanılır; konuşmacı sayısı tasarımı
değil seçeneği büyütür.

---

## Test 7: Yeni bir konuşmacı gerçekten duyuluyor (~2 dk) — ses gerekir

12c'nin ekranlı testinin habercisi; burada sadece **ses** yolu.

**Komut:**
```powershell
& $PY tools\run_module.py --module mcgurk --limit 4 --speaker-id 5
```

**Kontrol edilecek:** Konuşmacı 5 (kadın) sunuluyor mu — 1'den farklı bir ses ve
yüz. Aynısını `--speaker-id 4` (erkek) ile de yapın.

**Başarısızsa:** dosya bulunamadı hatası hazırlık eksikliğidir (Test 4/5).

---

## Ölçüm düzeltmesi — ne değişti, ne değişmedi

Bunu onaylarken bilmeniz gereken tek teknik konu bu.

**Kusur:** `dsp.detect_burst` (patlama anı) ve `dsp.active_speech_level_dbfs`
(konuşma seviyesi) zarfı **bitişik karelerle** örneklüyordu. Aynı ses dosyasını
birkaç örnek kaydırıp yeniden ölçtüğünüzde sonuç değişiyordu:

| | Kaydırma yayılımı (önce) | (sonra) |
|---|---|---|
| Patlama, konuşmacı 1 /ba/ | 12.98 ms | **0.000 ms** |
| Patlama, konuşmacı 2 /ga/ | 8.92 ms | **0.000 ms** |
| Patlama, 24 token'ın kaçı > 2 ms | 13 / 24 | **0 / 24** |
| Seviye, konuşmacı 8 /ga/ | 0.97 dB | **0.000 dB** |

Hizalama, ses dosyasının önünden birkaç örnek kırpar — yani bu kaydırma her
denemede gerçekten oluyordu. Hem hizalama hedefi hem token patlaması bu
ölçümden geldiği için belirsizlik **sunulan uyaranın A/V ofsetine** giriyordu.

**Değişmeyenler:** toleranslar (5.0 ms hizalama, 0.5 dB seviye), patlama
tanımı, hazırlama hattının mantığı, deneme sayıları, config'teki tasarım.

**Değişenler:** ölçülen patlama anları birkaç ms oynadı (ör. konuşmacı 2 /ga/
836.0 → 842.8 ms), dolayısıyla **hazır set tümüyle yeniden üretildi** —
konuşmacı 1 ve 2 dâhil. Veritabanındaki tek geliştirme oturumu (12 deneme)
dışında etkilenen veri yok.

**Danışmana anlatılırken:** patlama anının *tanımı* değişmedi; ölçüm
*tekrarlanabilir* hâle geldi. Bu, yeni konuşmacıların ortaya çıkardığı ama
baştan beri var olan bir sorundu.

---

## Kabul kriterleri

- [ ] Sekiz konuşmacı config'te, cinsiyetler ve etiketler doğru (Test 1)
- [ ] `import_speakers.py` ikinci koşuda hiçbir şey yazmıyor (Test 2)
- [ ] Konuşmacı 1 ve 2'nin ham kayıtları bayt bayt aynı (Test 3)
- [ ] Hazırlık sekiz konuşmacıda da durmadan tamamlanıyor (Test 4)
- [ ] `verify_stimuli.py` temiz ve hizalama sapması 0.0 ms (Test 5)
- [ ] Deneme sayısı 797'de kaldı (Test 6)
- [ ] Yeni bir konuşmacının kaydı gerçekten sunuluyor (Test 7)
- [ ] Ölçüm düzeltmesinin gerekçesi anlaşıldı ve kabul edildi

## Sırada ne var

**12b** — seçim çekirdeği + CLI (`mcgurk/config/selection.py`, `--speaker`,
`--modules`); GUI yok, hepsi CI-testli. Menünün kendisi **12c**'de.
