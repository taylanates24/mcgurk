# Adım 9b Manuel Test — QC raporu + entegrasyon/başarısızlık testleri

Adım 9'un ikinci turu: **kalite kontrol raporu** (`tools/qc_report.py`) ve
otomatik **uçtan uca entegrasyon** + **başarısızlık modu** testleri. QC eşikleri
config'e yeni bir `qc:` bloğu olarak girdi (geçici, danışman onayına açık).

**Ekran/ses gerekmez** (çapraz dinleme yargısını gerçek veride görmek isteyen
opsiyonel Test 4 hariç). **Toplam süre ~4 dakika.**

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| Otomatik testler | **835 test yeşil** (CI alt kümesi; ~27 yeni), `ruff` + `mypy` temiz |
| Uçtan uca entegrasyon | `test_analysis_integration.py`: sahte katılımcı → **8 modül** (practice + 6 ölçüm + cross_hearing) tek DB'ye → export + measures + qc çökmeden |
| Başarısızlık modları | `test_failure_modes.py`: kesme→`aborted`+devam, yanıtsız→`NONE`/yanlış, eksik uyaran→config yüklemede yakalanır, ses yolu→`AudioError` (sessiz geri düşüş yok), yazım hatası→açık hata (sessiz veri kaybı yok) |
| QC birim testleri | `test_analysis_qc.py`: işaretleme kuralları, çapraz dinleme binomial, zaman aşımı muhasebesi |
| Config | yeni `qc:` bloğu: `max_dropped_frames`, `soa_tolerance_ms`, `cross_hearing_alpha` — **oturum snapshot'ıyla taşınır** (analiz canlı config'i değil snapshot'ı okur) |

**Not:** Otomatik uçtan uca test, steps.md Adım 9'un "uçtan uca entegrasyon
testi" kabul kriterini karşılar. **Gerçek kişiyle prova oturumu** kapısı Adım
9c'de.

## Ön koşullar

- [ ] Conda ortamı etkin (`C:\Users\tayla\miniconda3\envs\mcgurk`).
- [ ] Elde analiz edilecek bir `data/mcgurk.sqlite` olması iyi olur (Adım 9a
      Test 2'de `run_module --module mcgurk --limit 12` ile oluşturmuştunuz).
      Yoksa Test 2 için önce onu koşun.
- [ ] Komutlar PowerShell.

---

## Test 1: Otomatik testler yeşil (~1 dk)

**Komut:**
```bash
python -m pytest tests/mcgurk/test_analysis_qc.py tests/mcgurk/test_analysis_integration.py tests/mcgurk/test_failure_modes.py -q
```
**Beklenen çıktı:** son satırda `24 passed`.
**Kontrol edilecek:** kırmızı yok — özellikle uçtan uca ve başarısızlık modu testleri.
**Başarısızsa:** çıktıyı bildirin.

---

## Test 2: KK raporu — gerçek veri (~1 dk)

**Komut:**
```bash
python tools/qc_report.py
```
**Beklenen çıktı:** her oturum için:
- **Zamanlama** bloğu (düşen kare, en kötü kare aralığı, en büyük SOA sapması),
- **Modüller** (modül başına zaman aşımı oranı — forced-choice'ta; yanıt dağılımı),
- **İşaretlenen deneme** listesi (varsa; yoksa "yok").

**Kontrol edilecek:**
1. Türkçe karakterler bozulmadan yazılıyor.
2. `mcgurk` gibi forced-choice modülde "zaman aşımı %..." görünüyor; akış/tespit
   modüllerinde (varsa) "yanıtsız N (basımsız — beklenebilir)".
3. Bir oturuma bakmak için `--session 1`.

**Başarısızsa:** çıktıyı bildirin. `data/mcgurk.sqlite` yoksa "Veritabanı
bulunamadı" verir — önce Adım 9a Test 2'yi koşun.

---

## Test 3: QC eşikleri config'te ve snapshot'la taşınıyor (~1 dk)

**Komut:**
```bash
python -m mcgurk.config
```
**Beklenen:** config sorunsuz yükleniyor (tasarım özeti + süre). Bu, yeni `qc:`
bloğunun doğrulamadan geçtiğini gösterir.

`config/experiment.yaml` içinde `qc:` bloğunu açın:
```
qc:
  max_dropped_frames: 3
  soa_tolerance_ms: 20.0
  cross_hearing_alpha: 0.05
```
**Kontrol edilecek:**
1. Blok var ve değerler geçici/danışman notlarıyla açıklanmış.
2. **Önemli:** Bu eşikler oturum başında **snapshot'a** yazılır; `qc_report.py`
   eski bir oturumu **o oturumun snapshot'ındaki** eşiklerle değerlendirir, canlı
   config'i değil. Yani buradaki değeri değiştirmek **eski** oturumların
   raporunu değiştirmez — yalnızca bundan sonra başlayan oturumları etkiler.
   (Analiz, veriyi toplandığı tasarımla yorumlar — §G.)

---

## Test 4 (OPSİYONEL, donanım): Çapraz dinleme yargısı gerçek oturumda

Çapraz dinleme "şans üstü mü" yargısını gerçek veride görmek isterseniz, SSD
grubuyla tam bir oturum koşup (çapraz dinleme bloğu SSD'de çalışır) sonra:

```bash
python tools/qc_report.py --session <N>
```
**Beklenen:** "Çapraz dinleme (... kulak)" bölümü — isabet/kaçırma, yanlış
alarm/doğru ret, ve "Şans üstü mü? (binomial) ... (p=..., alfa=0.05)". Şans üstü
çıkarsa SSD katılımcısı için "UYARI: ... Modül 1-2 uzamsal yön verisi geçersiz
sayılmalı (§6.5)" satırı.

Bu adımın **kabulü için zorunlu değil** (otomatik testler binomial yolu ve uyarıyı
zaten doğruluyor); yalnızca canlı görmek isterseniz.

---

## Kabul kriterleri

- [ ] `test_analysis_qc` + `test_analysis_integration` + `test_failure_modes` yeşil
- [ ] `qc_report.py` gerçek veride Türkçe, bozulmadan zamanlama/zaman aşımı/işaretleme yazdırıyor
- [ ] `python -m mcgurk.config` yeni `qc:` bloğuyla sorunsuz yükleniyor
- [ ] QC eşiklerinin snapshot'la taşındığı (analizin canlı config'i değil snapshot'ı okuduğu) anlaşıldı
