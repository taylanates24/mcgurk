# Adım 1 Manuel Test — Proje iskeleti

**Ekran veya ses aygıtı gerekmez.** Bu adımda sunum kodu yok; test edilenler
config doğrulama, veritabanı, yedekleme, loglama ve CI.

Bu dosya kısa, çünkü Adım 1'in kabul kriterlerinin çoğu otomatik teste bağlandı
ve burada koşuldu. Aşağıda önce **ne zaten doğrulandı**, sonra **yalnızca senin
yapabileceklerin** var.

---

## Ön koşullar

- [ ] Conda ortamı aktif: `C:\Users\tayla\miniconda3\envs\mcgurk` (Python 3.10)
- [ ] `pip install -r requirements.txt` çalıştırıldı (yeni bağımlılık:
      `pydantic==2.13.4`)

```bash
python -c "import sys, pydantic; print(sys.version.split()[0], pydantic.VERSION)"
```

**Beklenen çıktı:**
```
3.10.20 2.13.4
```

**Başarısızsa:** ortam aktive değildir (bkz. README → Kurulum) veya pydantic
kurulmamıştır: `pip install -r requirements.txt`.

---

## Zaten doğrulanmış olanlar (yeniden koşabilirsin, gerekmez)

`docs/steps.md` Adım 1 kabul kriterleri ve karşılıkları:

| Kabul kriteri | Nasıl doğrulandı | Sonuç |
|---|---|---|
| `pytest` yeşil, config ve DB için anlamlı kapsam | 209 test (151'i yeni) | ✅ |
| Geçersiz config açık hata mesajı veriyor | `test_config_schema.py` — 32 test | ✅ |
| `data_collection`'da eksik kalibrasyon → başlatma reddediliyor | `test_config_modes.py` — 11 test | ✅ |
| DB oluşuyor, yabancı anahtar kısıtları çalışıyor | `test_db_schema.py` — 21 test | ✅ |
| Oturum kapanışında yedek üretiliyor; `verify_backup.py` doğruluyor | `test_backup.py` — 16 test | ✅ |
| `ruff check` ve `mypy` temiz | ruff: temiz, mypy: 58 dosya temiz | ✅ |

Ek olarak koşulan, kriterlerde olmayan doğrulamalar:

- **CI ortamı simülasyonu:** PsychoPy import'u ve `find_spec`'i engellenerek
  `pytest -m "not psychopy"` koşuldu → 168 geçti, 3 atlandı, hata yok.
- **`requirements-ci.txt` çözümlemesi:** Python 3.10'a izole dizine kuruldu,
  çıkış kodu 0.
- **Uçtan uca yazma:** katılımcı → oturum → blok → deneme → yanıt → yedek →
  `verify_backup.py` zinciri gerçek dosyayla çalıştırıldı, `YEDEK
  KULLANILABİLİR` ve çıkış kodu 0 alındı.
- **`.github/workflows/ci.yml`** YAML olarak ayrıştırıldı, iki iş ve adımları
  doğrulandı.

İstersen üçünü birden tekrar koş:

```bash
pytest -q
```
```bash
ruff check .
```
```bash
mypy
```

**Beklenen:** `206 passed, 3 skipped`, `All checks passed!`,
`Success: no issues found in 58 source files`.

(Atlanan 3 test, PsychoPy'nin sunum katmanlarına ait olduğu dosyalar için
paket sınırı kontrolünü atlayan `test_package_boundaries.py` maddeleridir.)

---

## Test 1: Tasarım özetini kendi gözünle gör

Bu Adım 1'in sana bıraktığı asıl çıktı: §F.1 kararını bu tabloya bakarak
vereceksin.

**Komut:**
```bash
python -m mcgurk.config
```

**Beklenen çıktı:**
```
Tasarım özeti — mcgurk_ssd v1.0.0 (development)
Modül             Deneme    Tahmini süre
----------------------------------------
practice              12               —
mcgurk               140         14.0 dk
avsr                 135         15.8 dk
tbw                  130         10.8 dk
oddball              200          3.5 dk
dichotic              30          2.5 dk
gin                   30          4.0 dk
cross_hearing         20               —
----------------------------------------
TOPLAM               697         56.1 dk
```

**Kontrol edilecek:** Türkçe karakterler düzgün görünüyor mu; toplam 697
deneme / ~56 dakika.

**Başarısızsa:** Türkçe karakterler bozuksa `chcp 65001` çalıştırıp tekrar
deneyin (kozmetik sorun, koda ait değil).

> **Bu sayılar minimum, karar değil.** §G'nin örnek değerleri 1167 deneme /
> 99.5 dakika veriyordu — `docs/steps.md` §F.1'in "bir oturuma sığmaz"
> uyarısını doğruluyordu. Config artık her modülün ölçtüğü şeyi hâlâ verebilen
> en küçük sayılarla geliyor. Danışman daha yüksek isterse tek yapılacak
> config'te sayıyı değiştirip bu komutu tekrar koşmak.

---

## Test 2: Config'i bozunca ne oluyor

Config'in gerçekten koruduğunu görmek için kasıtlı bozma.

`config/experiment.yaml` içinde `mode: development` satırını
`mode: data_collection` yapın (elle veya aşağıdaki komutla), sonra çalıştırın.

**Komut:**
```bash
python -c "import pathlib; p=pathlib.Path('config/experiment.yaml'); p.write_text(p.read_text(encoding='utf-8').replace('mode: development','mode: data_collection'),encoding='utf-8')"
```
```bash
python -m mcgurk.config
```

**Beklenen çıktı:**
```
HATA: Config doğrulaması başarısız: ...config\experiment.yaml
  - (kök): Value error, mode: data_collection için eksikler:
  - timing.system_av_offset_ms boş — fotodiyot ölçümü yapılmadan veri toplanamaz (01_av_gecikme_olcumu.md)
  - audio.calibration_file boş — ses kalibrasyonu yapılmadan veri toplanamaz (02_kalibrasyon.md)
  - audio.device boş — veri toplamada çıkış aygıtı açıkça belirtilmeli, operatör seçimine bırakılamaz
```

**Kontrol edilecek:** Üç eksik de **tek seferde** bildiriliyor mu (birini
düzeltip tekrar koşmak zorunda kalmamalısın); çıkış kodu 1 mi.

**Geri al:**
```bash
git checkout config/experiment.yaml
```

**Başarısızsa:** hata yerine tasarım özeti geldiyse mod kapısı çalışmıyor
demektir — bildir.

---

## Test 3: CI (GitHub Actions) — yalnızca push sonrası

Bu testi ben yapamam: koşum GitHub'da, senin deponda gerçekleşiyor.

**Ne zaman:** Adım 1 commit'lenip `develop`'a push edildikten sonra.

**Nereye bakılacak:** https://github.com/taylanates24/mcgurk/actions

**Beklenen:** `CI` iş akışında iki iş de yeşil.
- `ruff + mypy`
- `pytest` → `169 passed, 3 skipped` (PsychoPy gerektiren 5 dosyadaki 37 test
  CI'da hiç toplanmaz)

**Kontrol edilecek:** `pytest` işinde PsychoPy kurulum denemesi **olmamalı**;
adım listesi yalnızca `pip install -r requirements-ci.txt` içermeli.

**Başarısızsa:**
- `ModuleNotFoundError: psychopy` bir test dosyasından geliyorsa: o dosya
  `tests/conftest.py` içindeki `_NEEDS_PSYCHOPY` listesine eklenmeli. Bildir.
- Actions sekmesi hiç iş göstermiyorsa depo ayarlarında Actions kapalı olabilir
  (Settings → Actions → General).

---

## Karar gerektirenler (test değil)

Bunlar kod tarafında bitti ama **senin ve danışmanının kararını bekliyor.**

### K1 — Deneme sayıları (§F.1)

Config **minimumlarla** geliyor: her modül için ölçtüğü şeyi hâlâ verebilen en
küçük sayı. §G'nin örnek değerleriyle karşılaştırma:

| Modül | §G örneği | Şimdiki minimum | Gerekçe |
|---|---|---|---|
| mcgurk | 280 | **140** | Kritik uyumsuz çiftler hücre başına 20→10 (oranda 10 puan çözünürlük, binom SE ~%16); uyumlu kontroller 10→5 |
| avsr | 270 | **135** | Hece başına 10→5 tekrar; hücre başına 15 deneme, doğruluk üç hece üzerinden havuzlanıyor |
| tbw | 195 | **130** | SOA noktası başına 15→10. **SOA ızgarası kısaltılmadı** — TBW çözünürlüğünü o belirliyor |
| oddball | 300 | **200** | 36 hedef, d′ için taban |
| dichotic | 60 | **30** | Kulak avantajı indeksi 30 gözlem üzerinden |
| gin | 30 | **30** | Değişmedi (aşağıya bak) |
| **TOPLAM** | **1167 / 99.5 dk** | **697 / 56.1 dk** | |

**Kasten azaltılmayan üç şey:**
- `noise_conditions` × `ears` çaprazlaması — SSD hipotezini taşıyan değişken bu.
  Kesilirse çalışmanın sorusu kalmıyor.
- **GIN** — normlu klinik bir test. `reps_per_gap` 6'nın altına inince 4/6 eşik
  kuralı ve onunla birlikte yayımlanmış normlarla karşılaştırılabilirlik gider.
  Zaten 4 dakika.
- `practice_trials: 12` — altı modül için modül başına iki deneme, zaten asgarî.

**Bir itirazım var:** oddball'ı 300→200 indirmek toplam süreden yalnızca ~1.7
dakika kazandırıyor, buna karşılık bir **dikkat kontrol** görevini zayıflatıyor.
Kontrol görevi zayıfsa SSD gruplarındaki farkı "dikkat farkı olabilir"
açıklamasından ayıramazsın. Tasarruf listesindeki en verimsiz kesinti bu;
danışman 300'e döndürmek isterse tek satır.

Karar Adım 4'ten önce gerekli. Seçenekler `docs/04_kod_disi_isler.md` §1'de.
Değiştireceğin alanlar: `av_pairs[].reps`, `stimulus_sets[].reps`,
`reps_per_soa`, `n_trials`, `reps`, `reps_per_gap`. Her değişiklikten sonra
`python -m mcgurk.config` yeni toplamı verir.

> **`reps` hücre başınadır, toplam değil.** `{visual: ga, audio: ba, reps: 10}`
> + 2 gürültü + 2 kulak = katılımcı bu uyaranı **40 kez** görür. Sayıyı
> seçerken bu çarpanı unutma; `test_reps_are_per_cell_not_per_module` bu
> anlamı teste bağlıyor.

### K2 — Dikotik ve GIN yöntem dokümanında yok

İkisi de artık config ve veritabanı şemasında var, ancak
`docs/946383_YONTEM (3).docx` içinde tanımlı değil. **Veri toplamaya
başlamadan önce** danışmanla görüşülüp dokümana eklenmeli — kodda olup
protokolde olmayan bir ölçüm etik kurul ve yayın açısından sorun yaratır.

Dokümana girmesi gerekenler: ölçülen değişkenler, gerekçe, deneme sayısı,
GIN için kulak seçimi kuralı.

### K3 — GIN parametreleri

Standart GIN (Musiek ve ark., 2005) değerleri girildi:
boşluklar 2–20 ms (10 değer), her biri 6 tekrar, 6 s segment, 30 segment,
eşik = 4/6. Danışman farklı bir liste isterse `config/experiment.yaml` →
`modules.gin` altında değiştirilir, kod değişmez.

**Kulak seçimi:** `ear_selection: good_ear`. GIN monaural bir testtir; sağır
kulağa sunulması anlamsızdır. Katılımcı başına iyi kulağın seçilmesi Adım 8'de
kodlanacak; veritabanı gerçekte kullanılan kulağı kaydediyor.

### K4 — Yaş kısıtı veritabanında zorlanıyor

`participants.age` için `CHECK (age BETWEEN 18 AND 60)` kondu (yöntem dokümanı
§4). Aralık dışı bir katılımcı kaydı **reddedilir**. Prova/pilot sırasında bu
aralığın dışında biriyle çalışmayı planlıyorsan şimdi söyle, kısıtı gevşetirim.

---

## Kabul kriterleri

- [ ] `python -m mcgurk.config` tasarım özetini yazdırıyor (Test 1)
- [ ] `data_collection` modu üç eksiği birden bildirip çıkış kodu 1 veriyor (Test 2)
- [ ] Push sonrası GitHub Actions'ta iki iş de yeşil (Test 3)
- [ ] K2 (dikotik + GIN protokole ekleme) danışmana iletildi
- [ ] K4 (yaş aralığı kısıtı) onaylandı veya değiştirilmesi istendi
