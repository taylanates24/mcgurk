# Adım 9a Manuel Test — Analiz kütüphanesi (dışa aktarım + ölçümler)

Adım 9'un ilk turu: toplanan veriyi **düz dosyalara aktarma** (CSV/parquet) ve
**oturum başına modül ölçümlerini** yazdırma. Ölçüm matematiği yeni değil — her
modül kendi sayısını zaten üretiyordu (CI-testli); bu tur onları veritabanına
bağlar. Şema **v4 → v5** yükseldi (`v_trials_flat`'e `cross_hearing_signal_present`).

**Ekran/ses gerekmez** (veri üretmek için tek modül koşusu hariç). **Toplam süre ~6 dakika.**

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| Otomatik testler | **808 test yeşil** (CI alt kümesi; ~30 yeni), `ruff` + `mypy` temiz |
| Yeni testler | `test_analysis_export.py` (CSV round-trip, parquet-opsiyonel, hata yolları, oturum filtresi), `test_analysis_measures.py` (modül dağıtımı, dejenere modül, snapshot config), `test_modules_mcgurk.py`'ye McGurk oranları, `test_db_schema.py`'ye v5 kolonu |
| Şema | v5: `v_trials_flat.cross_hearing_signal_present` (sinyal denemesi 1, yakalama 0, diğer modüller NULL) |
| Parquet | opsiyonel: pyarrow kuruluysa yazılır, değilse uyarıp atlar (CI'da yalnız CSV) |

**Not — mevcut geliştirme veritabanı yedeklendi ve silindi.** v4 `data/mcgurk.sqlite`
(1 katılımcı, 3 oturum, 37 deneme — hepsi geliştirme verisi) `VACUUM INTO` ile
`backups/mcgurk_pre_adim9a_schema4_<zaman>.sqlite` olarak alındı (integrity ok,
satır sayıları birebir), sonra silindi. İlk koşuda **v5 şemasıyla yeniden oluşur**.

## Ön koşullar

- [ ] Conda ortamı etkin (`C:\Users\tayla\miniconda3\envs\mcgurk`), ses aygıtı bağlı.
- [ ] Komutlar PowerShell.

---

## Test 1: Otomatik testler yeşil (~1 dk)

**Komut:**
```bash
python -m pytest tests/mcgurk/test_analysis_export.py tests/mcgurk/test_analysis_measures.py -q
```
**Beklenen çıktı:** son satırda `19 passed` (veya pyarrow yoksa 1 skip ile `18 passed, 1 skipped`).
**Kontrol edilecek:** kırmızı yok.
**Başarısızsa:** çıktıyı bildirin.

---

## Test 2: Veri üret + şema v5 doğrula (~2 dk)

Analiz edilecek gerçek veri için kısa bir McGurk bloğu koşun (yeni v5 DB oluşur):

```bash
python tools/run_module.py --module mcgurk --limit 12
```
- Giriş/koşu Adım 4'teki gibi; 12 deneme yanıtlayın.
- Bu, `data/mcgurk.sqlite`'i **v5 şemasıyla** sıfırdan oluşturur.

Şema sürümünü doğrulayın:
```bash
python tools/verify_backup.py data/mcgurk.sqlite
```
**Beklenen:** `YESIL    şema sürümü: 5` satırı; `SONUÇ: YEDEK KULLANILABİLİR`.
**Kontrol edilecek:** şema sürümü **5**.

> Ses aygıtınız kapalıysa `run_module` açık hatayla durur; `MCGURK_TEST_AUDIO_DEVICE`
> ortam değişkeniyle başka bir aygıt verebilirsiniz (bkz. progress notları).

---

## Test 3: Oturum ölçümlerini yazdır (~1 dk)

**Komut:**
```bash
python tools/analyse.py
```
**Beklenen çıktı:** başlık (`Katılımcı … — oturum …`) ve **McGurk kategorileri**
bloğu: İşitsel / Görsel baskınlık / Füzyon / Kombinasyon / Diğer / Yanıtsız
yüzdeleri ve ortalama RT.
**Kontrol edilecek:**
1. Yüzdeler toplamı %100 (12 deneme üzerinden).
2. Türkçe karakterler bozulmadan yazılıyor (İşitsel, Füzyon, Yanıtsız).
3. Yalnızca koştuğunuz modül(ler) görünüyor; koşmadıklarınız yok.

**Başarısızsa:** çıktıyı bildirin. Tek bir oturumu görmek için `--session 1`.

---

## Test 4: Dışa aktarım — CSV (~1 dk)

**Komut:**
```bash
python tools/export_data.py --out data/export
```
**Beklenen çıktı:** `7 dosya yazıldı -> …\data\export` (trials_flat + 6 ham tablo,
yalnız CSV; pyarrow kuruluysa 14 dosya — 7 CSV + 7 parquet).

**Kontrol edilecek:**
1. `data/export/trials_flat.csv` açılıyor (Excel veya not defteri).
2. Başlık satırında **`cross_hearing_signal_present`** sütunu **var**.
3. Zaman aşımı (yanıtsız) denemesi varsa `is_correct` / `category` hücreleri
   **boş** (McGurk'te zaten `is_correct` hep boş — §A.10).
4. `participants.csv`'de ad-soyad **yok**, yalnız anonim kod (KVKK).

**Başarısızsa:** çıktıyı ve hangi sütunun eksik olduğunu bildirin.

---

## Test 5: Parquet opsiyonel (~1 dk)

**pyarrow kurulu mu?**
```bash
python -c "import importlib.util as u; print('pyarrow:', u.find_spec('pyarrow') is not None)"
```

**A. Kuruluysa** (`True`):
```bash
python tools/export_data.py --out data/export --format both
```
**Beklenen:** hem `.csv` hem `.parquet` yazılır (14 dosya: 7 CSV + 7 parquet).

**B. Kurulu değilse** (`False`):
```bash
python tools/export_data.py --out data/export --format both
```
**Beklenen:** "parquet istendi ama pyarrow kurulu değil — yalnızca CSV yazılacak"
uyarısı; yalnız `.csv` dosyaları. **Hata değil**, uyarı.

**Kontrol edilecek:** parquet yokluğu programı durdurmuyor; CSV her hâlde yazılıyor.

---

## Kabul kriterleri

- [ ] `test_analysis_*` otomatik testleri yeşil
- [ ] `run_module` sonrası `data/mcgurk.sqlite` **şema sürümü 5** (verify_backup)
- [ ] `analyse.py` oturum ölçümlerini Türkçe, bozulmadan yazdırıyor; yalnız koşan modüller
- [ ] `export_data.py` CSV üretiyor; `trials_flat.csv`'de `cross_hearing_signal_present` sütunu var; `participants.csv`'de ad yok
- [ ] parquet: pyarrow varsa yazılıyor, yoksa uyarıp atlıyor (CSV her hâlde)
