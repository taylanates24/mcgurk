# ADIM 10 — Operatör Paneli (PySide6) + Windows Paketleme (.exe)

> **Bu bir Adım 10 promptudur.** `docs/steps.md` §A (değişmez kurallar) ve §B
> (her adımda işletilecek döngü: **önce plan-onay → uygula → doğrula → manuel
> test → commit**) bu adım için de aynen geçerlidir. Alt adımlara böl (10a/10b/
> 10c), her birinde ayrı plan-onay/test/commit. `progress.md`'yi her kapanışta
> güncelle. Türkçe konuş, kod/commit İngilizce.

## §0. Bağlam ve amaç

Platform bugün komut satırından çalışıyor: deney `python main.py` ile açılıyor
(sonrası tamamen pencere/diyalog), ama **oturum öncesi/sonrası operatör araçları
komut satırında**: `python -m mcgurk.checklist`, `tools/export_data.py`,
`tools/analyse.py`, `tools/qc_report.py`, `tools/verify_stimuli.py`,
`tools/verify_backup.py`.

**Amaç:** Python bilmeyen bir operatör için **çift-tıklanan bir Windows
uygulaması** ve **buton temelli bir panel**. Operatör hiçbir komut yazmaz.

Bu, `steps.md` kapsamının dışında, kullanıcı isteğiyle eklenen yeni bir adımdır
(2026-07-30). Adım 9 (kod + doküman) tamamlandıktan sonra gelir; **prova oturumu
ve `master` merge + `v1.0.0` bu adımdan sonradır** (prova, paketlenmiş app +
panel üzerinde koşulacak — son teslim biçimini denemesi için).

## §A10. Bu adıma özel değişmez kurallar

`steps.md` §A'ya **ek olarak**:

1. **Panel ve PsychoPy asla aynı süreçte çalışmaz.** PySide6 (Qt) olay döngüsü
   PsychoPy ile çakışır (`CLAUDE.md` Don'ts, eski `admin.py` de bu yüzden
   ayrıydı). Panel; deneyi (`mcgurk.ui`) ve donanım gerektiren checklist'i **ayrı
   süreç** (subprocess) olarak başlatır, çıktısını/çıkış kodunu okur.
2. **Panel PsychoPy import etmez.** `mcgurk/analysis`, `mcgurk/db` (PsychoPy'siz)
   doğrudan kullanılır; PsychoPy gereken her şey subprocess'tir. Bir sınır testi
   panelin PsychoPy import etmediğini doğrular.
3. **Panelin çekirdek mantığı GUI'den ayrıdır** (motor `scheduling.py`
   ayrımı gibi). Subprocess komutu kurma, DB listeleme, biçimlendirme —
   PySide6'sız ve **CI-testli**. Qt kabuğu ince; UI testi manuel (`ui/` gibi).
4. **KVKK.** Sonuç tarayıcısı yalnız **anonim kod** gösterir; ad-soyad yoktur ve
   kod↔kimlik eşleşme dosyası panelde açılmaz/gösterilmez.
5. **Varsayılan salt-okunur.** Tarama salt-okunur; export/yedek güvenli. Silme
   gibi **yıkıcı** işlemler ya yok ya da açık onay arkasında (12 aylık çalışmada
   yanlışlıkla silme kabul edilemez).
6. **Paketlenmiş app'te veri yolları kullanıcı-yazılabilir yerdedir.** Donmuş exe
   içinde kod salt-okunur bir geçici dizindedir (`_MEIPASS`); `data/`, `backups/`,
   `logs/`, `config/` ve `stimuli/` **exe'nin yanında veya `%APPDATA%` altında**,
   yazılabilir bir yerde olmalı. Tek bir yol-çözümleme katmanı hem kaynaktan hem
   donmuş halde doğru çalışmalı.

## §C10. Alt adımlar

### ADIM 10a — Panel çekirdeği (GUI'siz, CI-testli)

**Yapılacaklar:**
- `mcgurk/panel/core.py` (veya `mcgurk/admin/`): PySide6'sız, PsychoPy'siz mantık:
  - **Başlatıcılar:** deneyi (`mcgurk.ui`), checklist'i (`mcgurk.checklist`),
    `verify_stimuli`, `verify_backup`, tek modül (`tools/run_module.py`)
    subprocess olarak başlatan komutları **kurar** (donmuş halde exe yolunu,
    kaynaktan `sys.executable -m ...` yolunu döndürür). Komut kurma saf ve testli;
    gerçek başlatma ince bir sarmalayıcı.
  - **Sonuç tarama:** `mcgurk.db` üzerinden oturum/katılımcı listesi (anonim kod,
    grup, tarih, durum, deneme sayısı) — salt-okunur sorgu, KVKK.
  - **Araç sarmalayıcıları:** `analysis.export_database`, `analysis.session_measures`,
    `analysis.session_qc`, `verify_backup` panele uygun dönüşlerle.
  - **Yol çözümleme:** `resource_root()` / `writable_root()` — kaynaktan proje
    kökü, donmuş halde `_MEIPASS` (salt-okunur kaynak) ve yazılabilir kök
    (exe yanı / `%APPDATA%`). 10c bunu kullanır; burada arayüzü ve kaynaktan
    davranışı test edilir.
- `mcgurk/panel/__init__.py`.
- Sınır testine `mcgurk.panel.core` eklenir (PsychoPy'siz kanıtı) + `PURE_LAYERS`.

**Kabul kriterleri:**
- [ ] Komut kurucular doğru argümanı üretiyor (kaynaktan ve donmuş-taklit halde) — test
- [ ] Oturum/katılımcı listesi anonim, salt-okunur — test
- [ ] Yol çözümleme kaynaktan doğru; donmuş dal `sys.frozen`/`_MEIPASS` taklidiyle test
- [ ] `mcgurk.panel.core` PsychoPy import etmiyor (sınır testi)
- [ ] `ruff` + `mypy` temiz; `pytest -m "not psychopy"` yeşil

**Manuel test:** ekran gerekmez.

### ADIM 10b — PySide6 paneli (GUI kabuğu)

**Yapılacaklar:**
- `requirements.txt`'e `PySide6` (kesin pin) ekle; `requirements-ci.txt`'e
  **ekleme** (CI'da Qt yok — panel UI'ı `psychopy` gibi işaretli/atlanır).
- `mcgurk/panel/app.py` + giriş noktası (`python -m mcgurk.panel`): 10a çekirdeği
  üzerine ince Qt kabuğu. Ana pencere butonları (Türkçe):
  - **Oturum başlat** → deneyi ayrı süreç açar, durum/çıkış kodunu gösterir.
  - **Kontrol listesi** → checklist'i koşar, YEŞİL/KIRMIZI'yı panelde gösterir.
  - **Uyaranları doğrula** → `verify_stimuli`.
  - **Sonuçlar** → oturum/katılımcı listesi (salt-okunur, anonim).
  - **Dışa aktar** → çıktı klasörü seç, CSV/parquet.
  - **Analiz** / **QC raporu** → seçili oturumun özetini gösterir.
  - **Yedek doğrula** → `verify_backup`.
- Uzun süren işler arayüzü dondurmamalı (subprocess/iş parçacığı; en azından
  düğmeler kilitlenip durum gösterilmeli).

**Kabul kriterleri:**
- [ ] Panel açılıyor, her buton ilgili işi tetikliyor
- [ ] "Oturum başlat" deneyi ayrı süreç olarak açıyor (panel donmuyor)
- [ ] Checklist KIRMIZI'yı panelde net gösteriyor
- [ ] Sonuç listesi anonim; hiçbir yerde ad yok
- [ ] Katılımcıya/operatöre gösterilen metinler Türkçe

**Manuel test:** ekran gerekir (`TEST_ADIM_10B.md`). Qt UI CI'da test edilmez.

### ADIM 10c — PyInstaller ile Windows .exe

**Yapılacaklar:**
- **Yol çözümleme katmanını bağla** (10a `resource_root`/`writable_root`):
  donmuş halde `data/`, `backups/`, `logs/`, `config/`, `stimuli/` yazılabilir
  konumda; ilk çalıştırmada varsayılan `config/experiment.yaml` ve gerekirse
  `stimuli/` oraya kopyalanır/aranır. Kaynaktan davranış **değişmez**.
- **PyInstaller spec** (`packaging/mcgurk.spec` gibi): PsychoPy veri dosyaları ve
  hook'ları, `ptb`/ses kütüphaneleri, ffmpeg ikilisi, `mcgurk/db/schema.sql` ve
  diğer paket verileri dahil. Panel giriş noktası ana exe; deney ya aynı exe'nin
  bir bayrağıyla ya da ikinci bir exe olarak açılır.
- **Derleme betiği** (`tools/build_exe.py` veya `packaging/README`): Windows'ta
  nasıl derlenir, çıktı nerede.
- **Boyut/dışlama:** gereksiz büyük bağımlılıklar dışlanır; `stimuli/` exe'ye
  gömülmez (yüzlerce MB) — yanına konur/işaret edilir.

**Kabul kriterleri:**
- [ ] Windows'ta `.exe` derleniyor
- [ ] Çift-tıkla panel açılıyor; "Oturum başlat" deneyi açıyor (PsychoPy exe içinde çalışıyor)
- [ ] Yazma işlemleri (DB, yedek, log, export) yazılabilir konuma gidiyor; salt-okunur `_MEIPASS`'a değil
- [ ] Kaynaktan çalıştırma (`python -m mcgurk.panel`, `python main.py`) hâlâ çalışıyor — regresyon yok
- [ ] Kısa bir oturum + export paketlenmiş app üzerinde uçtan uca çalışıyor

**Manuel test:** Windows + ekran + ses gerekir (`TEST_ADIM_10C.md`). PyInstaller +
PsychoPy en çok yineleme gerektiren kısımdır; gerçek makinede denenerek çözülür.

## §D10. Bilinen riskler / açık noktalar

- **PyInstaller + PsychoPy** kötü şöhretlidir (gizli import'lar, veri dosyaları,
  ptb/ses backend'i). 10c büyük olasılıkla birkaç yineleme ister; sorunlar gerçek
  Windows makinesinde çözülür.
- **PySide6 lisansı** (LGPL) — dağıtım biçimine göre kontrol edilmeli.
- **Tek exe vs. iki exe** (panel + deney) kararı 10c planında netleşir; ayrı süreç
  kuralı (§A10.1) korunduğu sürece ikisi de olur.
- **Kod imzalama** (Windows SmartScreen uyarısı) kapsam dışı; gerekirse ayrı iş.

## §E10. Kapanış

Adım 10 bitince:
1. **Prova oturumu** — paketlenmiş app + panel üzerinde, `TEST_ADIM_9C.md`'nin
   Adım 10 biçimine uyarlanmış hâliyle (operatör panelden başlatır).
2. Bug çıkarsa düzelt.
3. `develop → master` merge + `git tag v1.0.0` (kullanıcı onayıyla). **v1.0.0 =
   dağıtılabilir Windows uygulaması.**
