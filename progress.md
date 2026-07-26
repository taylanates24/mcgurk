# İlerleme Raporu — McGurk / SSD Platformu

Son güncelleme: 2026-07-26
Aktif adım: 3 (Adım 2 tamamlandı)

## Durum tablosu

| Adım | Başlık | Durum | Tarih | Commit |
|---|---|---|---|---|
| 0 | Baseline düzeltme | TAMAMLANDI | 2026-07-26 | `f45eeda`…`618ef1c` |
| 1 | Proje iskeleti | TAMAMLANDI | 2026-07-26 | `0fb3d3f`…`9dbedee` |
| 2 | Uyaran hazırlama | TAMAMLANDI | 2026-07-26 | `d6e7aaf` |
| 3 | A/V senkron çekirdeği | BEKLİYOR | | |
| 4 | Modül 1: McGurk | BEKLİYOR | | |
| 5 | Modül 2: AVSR | BEKLİYOR | | |
| 6 | Modül 3: TBW | BEKLİYOR | | |
| 7 | Modül 4: Oddball | BEKLİYOR | | |
| 7b | Modül 5: Dikotik dinleme | BEKLİYOR | | |
| 7c | Modül 6: GIN | BEKLİYOR | | |
| 8 | Oturum akışı ve arayüz | BEKLİYOR | | |
| 9 | Analiz ve entegrasyon | BEKLİYOR | | |

Durum değerleri: BEKLİYOR / PLAN ONAYINDA / GELİŞTİRİLİYOR / TESTTE / TAMAMLANDI

**Adım 7b ve 7c `steps.md`'de yoktur** — kullanıcı kararıyla eklendi
(2026-07-26). Dikotik kodda zaten vardı; GIN (Gaps-In-Noise) yeni bir istek.
İkisi de Adım 8'den önce bitmeli, çünkü Adım 8 modülleri oturuma bağlıyor.
`steps.md` §C'ye karşılık gelen iki bölümün yazılması gerekiyor.

## Adım kayıtları

### Adım 0 — Baseline: mevcut kodun düzeltilmesi ve doğrulanması
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-26. Otomatik testler yeşil (58 test, ruff + mypy
  temiz); `TEST_ADIM_0.md` içindeki 13 manuel testin tamamı kullanıcı
  tarafından yürütüldü ve geçti.
- **Commit:**
  - `f45eeda` — KVKK anonimleştirme, veri bozan bug'lar, §A ihlalleri
  - `e8bc700` — progress kaydı
  - `cd2cc0d` — dikotik ve audio-only videosuz sunuma taşındı
  - `0e7c053`, `e8f69bb`, `ab49050` — conda ortam tuzağı belgelendi
  - `039c5c2` — ESC her aşamada, kesilen oturum doğru raporlanıyor
  - `618ef1c` — MovieStim SDL2 uyarısı bastırıldı

- **Ne yapıldı:**
  - `git tag baseline-original` → `867939c`; `data/mcgurk.db` `VACUUM INTO` ile
    `backups/mcgurk_pre_adim0_20260726T153149.sqlite` olarak yedeklendi ve
    eski dosya silindi.
  - **KVKK (§A.6):** Katılımcı adı toplama tamamen kaldırıldı. `participants.name`
    → `participant_code`; giriş formunda ad-soyad alanı yok; kod dosya sistemi
    için sanitize ediliyor (`sanitize_participant_code`); ad sütunu içeren eski
    veritabanı `SchemaMismatchError` ile reddediliyor. Admin paneli ve CSV
    dışa aktarımı da koda geçirildi.
  - **Veri bozan bug:** `sections.py` içinde `specs * repetitions` liste
    çarpımı aynı `TrialSpec` nesnesini tekrarlıyordu; motor `ear_side`'ı bu
    nesneye geri yazdığı için `trial_repetitions > 1` olduğunda tekrarlar
    birbirini eziyordu. `dataclasses.replace` ile ayrı nesneler üretiliyor,
    iki regresyon testi eklendi.
  - **§A.11 seed:** `random.shuffle` → `random.Random(seed).shuffle`. Seed
    config'ten gelir (`seed: null` ise üretilir), `sessions.seed` sütununa
    yazılır ve loglanır.
  - **§A.2 ses backend'i:** `require_ptb_backend()` eklendi; veri yazılmadan
    önce çalışır. `present_video` içindeki `except Exception: audio.play()`
    sessiz geri düşüşü kaldırıldı. `prefs.hardware['audioLib']` artık tek
    öğeli (`["ptb"]`).
  - **§A.10 doğru cevap:** `mcgurk` ve `dichotic` denemelerinde `is_correct`
    artık `NULL`. Bitiş ekranından başarı yüzdesi kaldırıldı (talep
    karakteristiği). Admin paneli NULL'ları doğruluk hesabından çıkarıyor.
  - **Oturum durumu:** `sessions.status` (`running`/`completed`/`aborted`)
    eklendi; `finally` bloğunda her çıkış yolunda yazılıyor. Önceden ESC ile
    kesilen oturum da "tamamlandı" olarak işaretleniyordu.
  - **Sessiz bozulma:** Gürültü dosyası bulunamadığında artık `FileNotFoundError`;
    önceden uyarı verip temiz koşula düşüyordu.
  - **§A.7:** `_get_ffmpeg` içindeki geniş `except Exception: pass` → `ImportError`
    + açık hata; üç `raise ... from exc` zincirlemesi eklendi.
  - **Kaynak yönetimi:** Her denemeden sonra `movie.unload()` (`finally` içinde),
    video bitiminde `movie.stop()`.
  - **§A.8:** `visual.Window(..., waitBlanking=True)` açıkça ayarlandı.
  - Yapılandırılmış loglama (`logs/session_<zaman>.log` + konsol), `argparse`
    ile `--config` / `--log-level`.
  - Test altyapısı: `pyproject.toml` (pytest/ruff/mypy), `tests/` (43 test),
    `requirements.txt` kesin pinlere çevrildi, `requirements-dev.txt` eklendi.
  - `.gitignore` genişletildi (`*.exe`, `data/`, `backups/`, `logs/`, `*.sqlite`);
    `asd.py` silindi.
  - `README.md` yeniden yazıldı; `CLAUDE.md`'deki yanlış bilgiler düzeltildi.
  - **Dikotik uyaranlar ve videosuz ses sunumu (kullanıcı isteği üzerine ek iş):**
    - `generate_dichotic_stimuli.py` artık mp4 değil **48 kHz stereo PCM WAV**
      üretiyor. Script zaten stereo WAV üretip ona `color=c=black:s=64x64:r=1`
      ile siyah dolgu video ekliyor ve WAV'ı siliyordu; video hiçbir işlev
      taşımıyordu. Script ayrıca `ffmpeg`'i PATH'ten çağırdığı için bu makinede
      hiç çalışmıyordu — `_get_ffmpeg()` kullanacak şekilde düzeltildi.
    - `stimuli.load_audio_stimulus()` ve `present_audio_only()` eklendi:
      `audio_only` ve `dichotic` bölümleri artık `MovieStim` **oluşturmuyor**,
      ekranda sabitleme haçı kalıyor, deneme sesin kendi süresi kadar sürüyor.
      Önceden deneme bitiş anı — yani RT referanslarından biri — 1 fps'lik bir
      video akışının bitmesine bağlıydı.
    - `sections.generate_dichotic_trials` `.wav` arıyor ve dosyayı `audio_path`
      alanında taşıyor (`video_path` artık `None`). Eski `.mp4` dosyaları
      yok sayılıyor; bunu doğrulayan test eklendi.
    - **Ölçüm — AAC kanal sızıntısı yoktu:** kontrollü test (sol kanal konuşma,
      sağ kanal mutlak sessizlik, script'in kendi AAC ayarları) sağ kanalda
      −200 dB, tepe değeri tam 0 verdi. Yani uyaranların dikotik içeriği
      zaten sağlamdı; sorun yalnızca gereksiz video ve kayıplı turdu.
    - Üretilen WAV'lar doğrulandı: 48 kHz stereo, `Left-ba_Right-da` dosyasının
      sol kanalı ile `Left-da_Right-ba` dosyasının sağ kanalı **birebir aynı**
      (korelasyon +1.0000), kanallar arası korelasyon 0.008–0.048.

- **Alınan kararlar:**
  - `src/` yerinde düzeltildi, `legacy/` altına taşınmadı (A0-1). `steps.md`
    §C Adım 0'ın "7 main dosyasından birini seç / legacy'ye taşı" maddeleri bu
    depoda karşılıksızdı.
  - Eski DB yedeklenip silindi, şema migrasyonu yapılmadı (A0-5). İçerik
    geliştirme sırasında girilmiş test verisiydi.
  - Konuşmacı sayısı 2 olarak sabitlendi (kullanıcı kararı, 2026-07-26).
    `steps.md`'nin "8 konuşmacı" ifadesi geçersiz.
  - mypy Adım 0'da da temiz tutuldu (`steps.md` "Faz 1'den itibaren" diyor);
    ayarlar gevşek başlatıldı, Adım 1'de sıkılaştırılacak.

- **Bilinen sınırlar:** Tam liste `README.md` → *Bilinen sınırlar*. Özet:
  uyaran kalitesi (29.97 fps, AAC 44.1 kHz, hizalanmamış patlama anları,
  tüm-dosya RMS üzerinden SNR) Adım 2'de; gerçekleşen zamanlama kaydı, SOA ve
  lateralizasyon Adım 3'te; yanıt seti/kategorizasyon Adım 4'te; config'e
  taşınacak metinler ve oturum akışı Adım 8'de.

  - **Manuel test turunda çıkan dört düzeltme (2026-07-26, Test 8 sırasında):**
    - **ESC artık her aşamada çalışıyor.** Önceden yalnızca `collect_response`
      içinde ele alınıyordu; talimat ekranında, sabitleme haçında veya uyaran
      sunumu sırasında basmak hiçbir şey yapmıyordu. `AbortSession` istisnası
      ve `check_abort()` eklendi; `present_fixation` ve `present_audio_only`
      `core.wait` yerine flip döngüsüne çevrildi (yan kazanç: sabitleme süresi
      artık yenileme ızgarasına oturuyor), `present_video` döngüsünde de
      kontrol ediliyor. Ses `finally` bloğunda durduruluyor, yani kesince
      anında susuyor.
    - **"Deney başarıyla tamamlandı" yanlış raporlaması.** `run_experiment`
      kesilen oturumda da normal dönüyordu ve `main.py` koşulsuz başarı
      logluyordu. Fonksiyon artık oturum durumunu döndürüyor; `main.py`
      duruma bakıyor, kesilmişse uyarı basıp çıkış kodu 1 veriyor.
    - **`[800 600]` tam ekran uyarısı.** `visual.Window`'a `size` verilmiyordu.
      `config.yaml`'a `window_size` eklendi.
    - **SDL2 uyarısının gerçek sebebi bulundu.** PsychoPy 2026.1'de
      `MovieStim.__init__`, `audioLib is None` iken `self._noAudio = False`
      atayarak çağıranın `noAudio=True` argümanını **koşulsuz eziyor**; başka
      bir `audioLib` verilirse `MovieAudioError` fırlatıyor. Yani SDL2 yolu
      kapatılamıyor ve uyarı kaçınılmaz. `CLAUDE.md`'deki "bazı ffpyplayer
      derlemelerinde yok sayılıyor" teşhisi yanlıştı — sorun derlemede değil,
      PsychoPy'nin kendi kodunda. Mevcut sessiz-video yaklaşımı tek çalışan
      çözüm; `tests/test_silent_video.py` sessiz kopyalarda ses akışı
      olmadığını her koşuda doğruluyor. Uyarı `_quiet_movie_init()` ile
      yalnızca constructor çağrısı boyunca bastırılıyor (PsychoPy kendi
      `psychopy.logging.console`'unu kullandığı için stdlib logger seviyesi
      etkisizdi — önceki `logging.getLogger("psychopy.visual.movies")`
      denemesi hiç işe yaramıyordu). Pencere dar tutuldu ki sunum sırasındaki
      düşen kare uyarıları operatöre ulaşmaya devam etsin; canlı MovieStim ile
      bastırmalı/bastırmasız karşılaştırılarak doğrulandı.

- **Sonraki adıma not:**
  - **Dikotik bölümü yöntem dokümanında YOK.** Yöntem dokümanı §6'da üç modül
    (McGurk, AVSR, TBW) + §6.4 oddball tanımlıyor; `steps.md` de aynı dördü
    sayıyor. Dikotik dinleme ikisinde de geçmiyor; §7'de bunun yerine
    "işitsel uyaranın uzamsal yönü" bir **bağımsız değişken** olarak var.
    Kullanıcı bölümün kullanılacağını bildirdi (2026-07-26) → **yöntem
    dokümanına eklenmesi gerekiyor**; kodda olup dokümanda olmayan bir ölçüm
    etik kurul ve yayın açısından sorun yaratır. Aşağıdaki bekleyen aksiyona
    işlendi.
  - `assets/dichotic/` altındaki 12 eski `.mp4` dosyası silinmedi; artık
    kullanılmıyorlar. Üretim script'i çalıştırıldığında uyarı basıyor.
  - `present_audio_only()` sesin bitişini `core.wait()` ile bekliyor. Ekranda
    değişen bir şey olmadığı için bu baseline'da yeterli; Adım 3'te gerçekleşen
    onset ve bitiş `ptb` saatinden okunup `TimingRecord`'a yazılacak.
  - **PsychoPy 2026.1.2 ses API'si değişmiş:** backend seçimi
    `prefs.hardware['audioLib']` yerine `sound.Sound.backend` sınıf niteliğinde;
    `sound.audioLib` **artık yok**. İlk yazdığım doğrulama bu kaldırılmış
    niteliği okuduğu için her çalıştırmada hata verecekti — gerçek API ile
    yeniden yazıldı ve teste bağlandı (`tests/test_audio_backend.py`).
    `SoundPTB.play(when=...)` ve `Window.getFutureFlipTime(clock=...)` bu
    sürümde mevcut, yani Adım 3'ün zamanlama mimarisi uygulanabilir.
  - `data/mcgurk.db` silindi; ilk çalıştırmada yeni şemayla oluşacak.
  - `assets/dichotic/` dosyaları 64×64 piksel **1 fps** sahte videolar. Kare
    döngüsü bunların bitmesini bekliyor; Adım 3'te dikotik yol videosuz
    kurgulanmalı.
  - **Conda ortamı (2026-07-26'da kullanıcıyı engelledi).** Çalışma ortamı
    `C:\Users\tayla\miniconda3\envs\mcgurk` (Python 3.10.20, tüm paketler
    pinlenmiş sürümlerde kurulu). Bu dizin conda'nın `envs_dirs` listesinde
    değil (liste `anaconda3\envs`, `.conda\envs`, `AppData\Local\conda\conda\envs`),
    bu yüzden ortam `conda env list` çıktısında **isimsiz** görünür ve
    `conda activate mcgurk` onu bulamaz. Başlangıçta `anaconda3\envs\mcgurk`
    altında boş bir kabuk ortam da vardı ve ismi o kapıyordu; kullanıcı onu
    sildi (2026-07-26), ancak isim çözümlemesi hâlâ arama yoluna bağlı.
    Kalıcı çözüm: `conda config --append envs_dirs C:\Users\tayla\miniconda3\envs`
    (2026-07-26'da uygulandı, `.condarc` oluşturuldu).
    İkinci engel: `conda init powershell` hiç çalıştırılmamıştı, bu yüzden
    `conda activate` shell fonksiyonu yüklenmiyor ve komut **hata vermeden**
    hiçbir şey yapmıyordu; `python` base'de kalıyordu. 2026-07-26'da çalıştırıldı,
    profil `OneDrive\Belgeler\WindowsPowerShell\profile.ps1` olarak oluştu.
    Etkili olması için terminalin yeniden açılması gerekir.
    Tam yolla aktivasyon her koşulda çalışır.
    Aktivasyon tutmazsa pip base ortamda (Python 3.13.9) çalışır ve
    `No matching distribution found for psychopy==2026.1.2` verir
    (psychopy 2026.1.2 → `>=3.9,<3.12`).
    README, CLAUDE.md ve TEST_ADIM_0.md bu duruma göre güncellendi.
  - Sistemde `ffmpeg`/`ffprobe` PATH'te yok; kod `imageio-ffmpeg` ikilisine
    düşüyor. `ffprobe` o pakette **yok** → Adım 2'nin uyaran doğrulama
    araçları kurulu ffmpeg gerektirecek.

### Adım 1 — Proje iskeleti
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-26. Otomatik testler yeşil (209 test, ruff + mypy
  temiz), `TEST_ADIM_1.md` manuel testleri kullanıcı tarafından yürütüldü ve
  geçti.
- **Commit:**
  - `0fb3d3f` — mcgurk/ paketi: config, veritabanı, yedekleme, loglama, CI
  - `213b4ca` — progress kaydı
  - `9dbedee` — oddball 300'e geri alındı (kullanıcı)
  - `109426a` — oddball testi hizalandı, dikotik taslak bölümü eklendi

- **Ne yapıldı:**
  - **Yeni paket `mcgurk/`**, `src/` yanına kuruldu (A0-1 kararı). Alt paketler:
    `config/`, `db/`, `engine/`, `modules/`, `analysis/`, `ui/`. Son dördü şu an
    boş — sırasıyla Adım 3, 4–7c, 9 ve 8'de doldurulacak.
  - **Config katmanı (Pydantic v2, `extra="forbid"`).** `config/experiment.yaml`
    §G şemasını uygular; `mcgurk/config/schema.py` doğrular. Mod bazlı kapı:
    `data_collection` için `system_av_offset_ms`, `calibration_file`,
    `fullscreen: true` ve `audio.device` zorunlu; eksikler **tek seferde**
    bildiriliyor. Dosya varlığı kontrolü `loader.py`'de (şema diske dokunmuyor).
  - **Config, tasarım hatalarını da yakalıyor:** `fusion_map`/`combination_map`
    anahtarları gerçek bir `av_pairs` çiftini göstermeli ve değerleri
    `response_set` içinde olmalı; TBW SOA listesi artan ve tekrarsız olmalı;
    oddball'da rampa ton süresine ve hedef aralığı deneme sayısına sığmalı;
    dikotik çiftler farklı ve tekrarsız olmalı; GIN'de boşluklar segmentlere
    hem sayıca hem süre olarak sığmalı; etkin her modül `module_order`'da
    olmalı. `display.video_position` [0,0] dışında bir değeri reddediyor (§A.13).
  - **Kalibrasyon okuyucu.** `02_kalibrasyon.md`'nin `hesap` komutu Türkçe
    anahtarlı JSON yazıyor (`K_ortalama`, `trim_sol_db`…); Pydantic `alias` ile
    İngilizce alanlara eşlendi. Bilinmeyen anahtar reddediliyor.
  - **Veritabanı (`data/mcgurk.sqlite`, şema sürümü 1).** Altı tablo
    (`participants`, `calibrations`, `sessions`, `blocks`, `trials`,
    `responses`) + `v_trials_flat` VIEW. WAL, `foreign_keys = ON`, CHECK
    kısıtları (grup kodu, yaş 18–60, oturum/blok durumu, modül adı).
  - **`trials.design_extra` (JSON) + modül başına Pydantic doğrulama.** Dikotik
    iki eşzamanlı token, GIN boşluk listesi, oddball ton tipi taşıyor. Sabit
    sütun eklemek her yeni modülde şema migrasyonu demekti; 12 aylık bir
    çalışmada bu daha büyük risk. VIEW `json_extract` ile bilinen anahtarları
    sütun olarak açıyor, analiz JSON görmüyor.
  - **`responses` deneme başına 0..n satır.** Zaman aşımında hiç satır yok
    (VIEW `LEFT JOIN` kullandığı için deneme yine görünüyor), GIN segmentinde
    birden fazla tuş basımı olabiliyor.
  - **§A.10 veritabanı tetikleyicisiyle zorlanıyor:** `mcgurk` ve `dichotic`
    denemelerinde `is_correct` yazma girişimi INSERT ve UPDATE'te reddediliyor.
  - **§A.5 commit sınırı:** `add_trial`, `set_trial_timing` ve `add_response`
    commit etmiyor; `finish_block` ediyor. Ayrı bir bağlantıyla test edildi.
  - **Yedekleme.** `VACUUM INTO` ile; ham dosya kopyası kullanılmıyor (WAL'da
    tutarsız kopya üretir). `tools/verify_backup.py` yedeği açıp
    `integrity_check`, `foreign_key_check`, şema sürümü, tablo varlığı ve satır
    sayımlarını kontrol ediyor, canlı veritabanıyla karşılaştırabiliyor;
    çıkış kodu 0/1.
  - **`provenance.py`** git commit (kirli ağaçta `+dirty`), Python/OS ve paket
    sürümlerini topluyor. PsychoPy sürümünü `importlib.metadata` ile okuyor —
    import etmiyor.
  - **Loglama** (`logging_setup.py`): dosyaya DEBUG, konsola INFO; tekrar
    çağrıldığında handler çoğaltmıyor.
  - **CI (GitHub Actions):** `ruff` + `mypy` ve `pytest -m "not psychopy"`.
    `requirements-ci.txt` PsychoPy içermiyor.
  - **Test:** 151 yeni test (toplam 209; CI'da 172). `pyproject.toml`'a `psychopy`
    marker'ı, `mypy` sıkılaştırması (`mcgurk.*` ve `tools.*` için
    `disallow_untyped_defs`), `explicit_package_bases`. `.gitignore`'a
    `stimuli/` ve `raw_recordings/`. README ve CLAUDE.md güncellendi.

- **Alınan kararlar:**
  - **Dikotik ve GIN eklendi (kullanıcı, 2026-07-26).** Config ve DB yerleri
    açıldı; modül gerçeklemeleri Adım 7b ve 7c'ye bırakıldı (§B.3: bir adımın
    işi o adımda). GIN parametreleri standart GIN'den (Musiek ve ark., 2005)
    alındı.
  - **`mcgurk/config` ve `mcgurk/db` PsychoPy import etmiyor.** CI'da PsychoPy
    kurulu değil ve analiz makinesinde de gerekmemeli. AST tabanlı bir test
    (`test_package_boundaries.py`) bunu her koşuda doğruluyor; `engine/`,
    `modules/` ve `ui/` muaf.
  - **İki ayrı veritabanı dosyası.** Eski `data/mcgurk.db` (src/) ve yeni
    `data/mcgurk.sqlite`. Şemalar uyumsuz, aynı dosyayı paylaşamazlar. Yeni
    katman eski dosyayı açmaya çalışırsa açık hata veriyor.
  - **İki ayrı config dosyası.** Eski `config.yaml` (src/), yeni
    `config/experiment.yaml`. İkisi de Adım 8'de tek dosyaya inecek.
  - **Yaş aralığı veritabanında zorlanıyor** (`CHECK age BETWEEN 18 AND 60`,
    yöntem dokümanı §4). Kullanıcı onayı bekliyor — prova/pilot için gevşetmek
    gerekebilir.
  - **§G'deki `fusion_map` ve `combination_map` örnekleri tutarsızdı:**
    `"ga|pa"` ve `"ba|da"` anahtarları `av_pairs` içinde yok, `bda` da
    `response_set`'te yoktu. Doğrulama bunları reddediyor; config'e tutarlı
    hâlleri yazıldı ve `response_set`'e `BGA`/`BDA` eklendi (Adım 0'ın
    BA/DA/GA seti kombinasyon algısını ifade edemiyordu).
  - **Deneme sayısı hesabı config katmanında.** Adım 4–7c'nin üreteçleri bu
    sayıyı üretmek zorunda olacak, böylece tahmin ile gerçek tasarım
    ayrışamıyor. V-only hücreleri gürültü ve kulakla çaprazlanmıyor (§C Adım 5).
  - **Varsayılan deneme sayıları minimuma çekildi (kullanıcı, 2026-07-26).**
    §G'nin örnek değerleri 1167 deneme / ~99.5 dakika veriyordu; config artık
    797 deneme / ~58.8 dakika ile geliyor. Her modülde ölçtüğü şeyi hâlâ
    verebilen en küçük sayı seçildi (gerekçeler config yorumlarında ve
    `TEST_ADIM_1.md` K1 tablosunda). Azaltılmayanlar: gürültü × kulak
    çaprazlaması (SSD hipotezi), **oddball 300** (dikkat kontrol görevi —
    zayıf kontrol, grup farkını dikkat farkından ayıramaz; kullanıcı kararı),
    GIN (normlu klinik test — 4/6 eşik kuralı ve normlarla
    karşılaştırılabilirlik bozulur), `practice_trials`.

- **Bilinen sınırlar:**
  - Yeni paket henüz hiçbir deney çalıştırmıyor; `main.py` Adım 8'e kadar
    `src/` yolunu kullanıyor.
  - `engine/`, `modules/`, `analysis/`, `ui/` boş.
  - AVSR kelime seti yalnızca şema düzeyinde. `enabled: true` yapılırsa deneme
    sayısı hesabı açık hata veriyor (§F.2, Adım 5).
  - `sessions.audio_backend` ve `measured_refresh_hz` sütunları var ama Adım
    1'de doldurulmuyor — PsychoPy gerektiriyorlar, Adım 3'ün işi.
  - GIN uyaran üretimi yok (§A.12 gereği offline olmalı) — Adım 2.
  - Yedekleme oturum kapanışına **bağlanmadı**; `db.backup()` ve
    `database.backup_on_session_end` bayrağı hazır, çağrı noktası Adım 8'de
    oturum akışıyla gelecek.

- **Sonraki adıma not:**
  - `steps.md` §C'ye **Adım 7b (dikotik) ve 7c (GIN)** bölümleri yazılmalı.
  - Adım 2'nin `prepare_stimuli.py`'si artık **GIN gürültü segmentlerini de**
    üretmek zorunda: geniş bantlı gürültü, config'teki boşluk süreleri,
    segment başına en fazla `max_gaps_per_segment`, aralarında en az
    `min_gap_separation_s`. Boşluk konumları `trials.design_extra`'ya yazılacak.
  - Adım 2 çıktısı `paths.stimuli` (`stimuli/`) altına gidiyor; `assets/` ham
    kayıt olarak kalıyor ve `src/` ile birlikte emekli olacak.
  - Adım 3 `sessions.audio_backend`, `measured_refresh_hz` ve
    `trials`'ın gerçekleşen zamanlama sütunlarını doldurmalı.
  - Adım 8 `db.backup()`'ı oturum kapanışına bağlamalı (kesilen oturumda da) ve
    `mcgurk.checklist` içinde `latest_backup()` tarihini raporlamalı.
  - Adım 9 `v_trials_flat` üzerinden çalışmalı; modüle özgü alanlar orada zaten
    sütun hâlinde.

### Adım 2 — Uyaran hazırlama ve kalite kontrol
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-26. Otomatik testler yeşil (301 test, ruff + mypy
  temiz; CI alt kümesi 264), `TEST_ADIM_2.md` manuel testleri kullanıcı
  tarafından iki turda yürütüldü ve geçti.
- **Commit:**
  - `d6e7aaf` — mcgurk/stimuli paketi, hazırlama ve doğrulama araçları,
    config'e stimulus_prep bölümü

- **Ne yapıldı:**
  - **Yeni paket `mcgurk/stimuli/`** — PsychoPy import etmez, sınır testine
    eklendi. `ffmpeg.py` (ikili bulma, akış çözümleme, sessiz yeniden
    kodlama), `wavfile.py` (24-bit PCM), `dsp.py` (patlama tespiti,
    aktif-konuşma seviyesi, gürültü tabanı, LTAS/SSN, SNR, GIN boşlukları),
    `manifest.py`, `prepare.py`, `verify.py`. CLI'lar `tools/prepare_stimuli.py`
    ve `tools/verify_stimuli.py`.
  - **Üretilen set** (`stimuli/`, 121 dosya, ~70 MB, gitignore'lu): 6 sessiz
    CFR 30 fps all-intra video, 18 hizalanmış 48 kHz 24-bit ses, 54 gürültülü
    türev (SSN +5 dB SNR, hücre başına 3 farklı gürültü), 12 dikotik stereo
    WAV, 30 GIN segmenti, 1 SSN master. Ölçülen: hizalama sapması **< 1 ms**
    (tolerans 5 ms), SSN LTAS sapması **0.35 dB** (tolerans 3 dB), tüm
    token'lar −23.0 dBFS aktif-konuşma seviyesinde.
  - **Patlama anları yeniden ölçüldü (A0-3).** Konuşmacı 1: 1092/1119/1108 ms
    (`steps.md`'nin 1105/1119/1108 değerleriyle ±13 ms uyuşuyor). Konuşmacı 2:
    **1084/849/836 ms — aralarında 248 ms fark var.** /da/ ve /ga/ çekimleri
    /ba/'dan çeyrek saniye erken başlamış. Hizalama olmadan Vis-ga + Aud-ba
    denemesinde ses görüntüden 248 ms geç gelirdi; bu, McGurk füzyonunun
    zamansal penceresinin (~±200 ms) tamamen dışıdır. Bu adım o denemeyi
    kurtarıyor. `steps.md`'nin "14 ms yayılım" tespiti yalnızca konuşmacı 1
    için geçerli.
  - **Kaynak yalnızca uyumlu kayıtlar.** `Vis-<t>_Aud-<t>.mp4` doğal
    çekimlerdir; 6 uyumsuz mp4 aynı token'ların sesi t=0'a yapıştırılmış eski
    bir re-mux'ı ve bu adımın düzelttiği şey tam olarak o hizalama.
  - **Hizalama hedefi videoya özgü**: Vis-X videosuna monte edilen her Y sesi,
    X'in kendi akustik patlama anına oturur (`steps.md` §C Adım 2). 29.97 → 30
    fps dönüşümü görsel zaman eksenini %0.1 sıkıştırdığı için hedef
    `source_fps / target_fps` ile ölçekleniyor. Kare sayısı korunumu QC'de
    doğrulanıyor (77 → 77).
  - **Config'e `stimulus_prep` bölümü** (§G "eksik gördüğün alanı ekle").
    İçinde `speaker_id` → klasör eşlemesi de var; bu eşleme daha önce hiçbir
    yerde yazılı değildi. Config artık yükleme anında tasarımı uyaran setiyle
    karşılaştırıyor: olmayan bir `speaker_id` veya hazırlanmamış bir token
    açık hata veriyor. SNR listesi ikinci kez yazılmıyor, etkin modüllerin
    `noise_conditions`'larından türetiliyor.
  - **`verify_stimuli.py`** diskteki her dosyayı manifest'e karşı yeniden
    ölçüyor (sağlama toplamı, ses akışı yokluğu, kare sayısı/fps, patlama,
    seviye, LTAS, kırpma, GIN kısıtları, kenar sessizliği) ve etkin modüllerin
    istediği her uyaranın var olduğunu kontrol ediyor. Çıkış kodu 0/1.
  - **Test:** 92 yeni test (toplam 301). Ölçüm fonksiyonları sentetik
    sinyallerle test ediliyor — gerçek korpusa karşı test etmek yalnızca
    korpusun kendisiyle tutarlı olduğunu söylerdi. ffmpeg gerektirenler
    `ffmpeg` marker'ıyla ayrıldı ve ikili yoksa kendini atlıyor;
    `requirements-ci.txt`'e numpy/scipy/soundfile eklendi.

- **Alınan kararlar:**
  - **29.97 → 30 fps.** 60 Hz'de kare başına 2.002 yenileme periyodik takılma
    üretiyordu. 2.58 s'lik klipte `fps=30` hiçbir kareyi çoğaltmıyor/atmıyor,
    yalnızca zaman damgaları %0.1 sıkışıyor (klip sonunda en fazla 2.6 ms,
    patlama anında ~1.1 ms). All-intra H.264 CRF 16: her kare bağımsız
    çözülür, sunumda çözücü duraklaması olmaz.
  - **24-bit PCM, kaynak kayıplı AAC olmasına rağmen.** Depoda ham kayıt yok
    (A0-3). Bit derinliği kaynak hassasiyeti eklemez ama normalizasyon +
    gürültü karışımı sonrası kuantalama gürültüsü biriktirmez. Manifest her
    dosyanın kaynak codec'ini (`aac`, 44100 Hz) kaydediyor.
  - **Gürültü örneği başına 3 varyant.** Gürültülü hücrede 10 tekrar var; aynı
    dalga formunu 10 kez duymak o dalga formunun sessiz anlarını öğrenmeyi
    ("listening in the dips") mümkün kılar. Üç varyant birbirinden bağımsız
    (korelasyon < 0.05) ama *aynı duyulmaları beklenir* — SSN durağan bir
    süreçtir, farklı duyulsalardı biri diğerinden farklı bir gürültü olurdu.
  - **Dikotik dosyalarda iki kulak ortak bir patlama anına hizalanıyor.**
    Konuşmacı 2'de token'ların doğal patlama anları 248 ms ayrışıyor; kulak
    avantajı bu farkla ölçülseydi kısmen başlangıç asenkronisi etkisi olurdu.
    Video olmadığı için ortak bir an dayatmanın maliyeti yok.
  - **Oddball tonları bu adımda üretilmedi** — `steps.md` onları Adım 7'ye
    koyuyor ve kabul kriteri orada (§B.3).
  - **Sentetik test korpusu bant şekilli gürültüden yapılıyor**, tondan değil.
    SSN korpusun kendi spektrumundan türetildiği için ayrık spektral çizgilerden
    oluşan bir korpus dar bantlı gürültü üretiyordu; zarfı birkaç dB oynayan
    dar bantlı gürültüyle yapılan her seviye ölçümü, boru hattıyla ilgisi
    olmayan nedenlerle yazı-tura hâline geliyordu.

- **Manuel test turunda çıkan beş düzeltme (2026-07-26):**
  - **GIN segment rampası 50 → 200 ms.** Kullanıcı segmentin sert başladığını
    bildirdi; ölçüm doğruladı (25 ms'te −6 dB). Rampa, gürültülü konuşma
    uyaranlarındaki SSN kesitiyle **aynı parametreyi** paylaşıyordu ve orada
    kısa olması gerekiyor. Ayrıldı: `stimulus_prep.gin.segment_ramp_ms`.
    Config doğrulaması eklendi — segment rampası `min_gap_separation_s`'i
    aşamaz, yoksa bir boşluk kendi rampasının içine düşer ve diğerlerinden
    daha kısık sunulur; duyulup duyulmaması nereye denk geldiğine bağlı olurdu.
  - **Gürültü rampası 50 → 250 ms.** Aynı sorun gürültülü konuşma
    uyaranlarında da vardı. Yukarıdan sınırlı: rampa token'ın patlama anından
    önce bitmeli, yoksa konuşmanın başı nominalinden yüksek SNR'de sunulur —
    ve token'a göre değişen miktarda. `_check_noise_is_up_before_the_speech`
    bunu her dosyada kontrol ediyor.
  - **Ölçüt olarak patlama anı, enerji tabanlı "konuşma başlangıcı" değil.**
    İlk yazdığım kontrol konuşmacı 2'de yanlış alarm verdi: o kaydın gürültü
    tabanı konuşma tepesinin yalnızca ~31 dB altında, aktiflik eşiği (30 dB)
    tabanın kendisini yakalıyor ve konuşmanın 180 ms'te başladığını sanıyor.
    Patlayıcılarda patlamadan önce kapanma sessizliği vardır, yani konuşmanın
    başlangıcı patlamadır — ve o zaten milimetrik ölçülüyor.
  - **Her yazılan konuşma dosyasına 10 ms kenar rampası**
    (`stimulus_prep.audio.edge_ramp_ms`). 121 dosyanın tamamı taranınca çıktı:
    hizalamada başından kırpılan iki dosya (`speaker_2/Vis-da_Aud-ba` ve
    `Vis-ga_Aud-ba`, 235–249 ms kırpıldı) **kaydın hışırtısının ortasından**
    başlıyordu (−48/−54 dBFS), diğerleri dijital sessizlikle. Yani bazı
    denemelerde başlangıç tıklaması var, bazılarında yok — uyaranla ilgisi
    olmayan, denemeye göre değişen bir ipucu. SSN master'ının hiç rampası
    yoktu; eklendi ve kesitler yalnızca iç bölgeden alınıyor ki master'ın
    rampası bir kesitin içine düşmesin. `verify_stimuli.py` artık her denetimde
    kenar sessizliğini kontrol ediyor.
  - `TEST_ADIM_2.md`'de iki yanlış beklenti düzeltildi: gürültü varyantlarının
    kulağa farklı gelmesi beklenmez (ölçüm komutu eklendi), ve `provenance`
    manifest'in kökünde, tek tek kayıtlarda değil.

- **Yol boyunca çıkan üç sorun:**
  - **`.gitignore`'daki `stimuli/` kuralı `mcgurk/stimuli/` paketini de
    gizliyordu** — yeni paketin tamamı sessizce commit edilmeyecekti. Kural
    köke sabitlendi (`/stimuli/`).
  - Hizalama sesi 248 ms kaydırınca dosyanın başına **tam dijital sıfır**
    ekliyor; patlama detektörünün gürültü tabanı tahmini bunu "çok sessiz
    kayıt" sanıp ilk gerçek hışırtıyı patlama olarak işaretliyordu (764 ms
    hata). Taban tahmini artık tam sıfır çerçeveleri hariç tutuyor — çözülmüş
    ses hiçbir zaman tam sıfır değildir, ayrım kesin.
  - LTAS karşılaştırması `n_fft=1024` ile yapılınca 125 Hz 1/3 oktav bandına
    hiç FFT bini düşmüyor ve bant "sessiz" okunuyordu — sahte 21.6 dB sapma.
    `n_fft=4096`'ya çıkarıldı, bini olmayan bantlar NaN döndürüp
    karşılaştırmadan çıkarılıyor.

- **Bilinen sınırlar:**
  - **Kaynak kayıpsız değil.** Set 44.1 kHz AAC'den türetiliyor (A0-3: depoda
    ham kayıt yok). Yeni bir çekim yapılırsa aynı boru hattı kayıpsız kaynakla
    daha iyisini üretir — kod değişmez.
  - Oddball tonları yok (Adım 7).
  - `src/` hâlâ doğrudan `assets/` içindeki ham mp4'leri sunuyor ve Adım 0'ın
    tüm uyaran sınırlarını taşımaya devam ediyor. İki yol Adım 8'e kadar yan
    yana duruyor.
  - GIN segmentlerinde boşluk sayısı segment başına 0–3 arasında dağılıyor
    (60 boşluk / 30 segment). Standart GIN'de 0 boşluklu yakalama segmentleri
    de var; mevcut dağılımda bunlar rastlantısal olarak ortaya çıkıyor,
    garanti edilmiyor. Gerekiyorsa Adım 7c'de tasarım kararı.
  - `stimuli/` ~70 MB ve gitignore'lu; makineler arası taşınırsa
    `verify_stimuli.py` ile doğrulanmalı.

- **Sonraki adıma not:**
  - **Adım 3 `stimuli/manifest.json`'dan okumalı, `assets/`'ten değil.**
    `TokenEntry.burst_time_s` ve `VideoEntry.burst_time_s` aynı zaman eksenine
    oturuyor; SOA hesabı bu ortak patlama anı üzerinden yapılacak
    (`steps.md` §C Adım 3: "ses zamanlaması ortak patlama anı üzerinden").
  - Videolar 2.567 s / 77 kare / 30 fps; ses dosyaları tam olarak aynı
    uzunlukta. Negatif SOA'da sesin videodan önce başlaması gerekiyor, yani
    pay hesabı ses dosyasının kendi giriş boşluğundan (en az ~586 ms)
    yararlanabilir.
  - `mcgurk.stimuli.manifest.load()` ve `verify(..., deep=False)` Adım 8'in
    `mcgurk.checklist` komutu için hazır: hızlı yol yalnızca dosya varlığı ve
    sağlama toplamına bakıyor.
  - Adım 7c (GIN) boşluk konumlarını manifest'ten `trials.design_extra`'ya
    taşımalı: `gin_segments[].gap_onsets_s` ve `gap_durations_ms` alanları
    `mcgurk/db/design.py`'nin beklediği adlarla aynı.
  - Adım 4–5 gürültülü koşulda `manifest.noisy(...)` ile gelen 3 varyanttan
    birini tohumlanmış RNG ile seçmeli ve hangisinin kullanıldığını
    `design_extra`'ya yazmalı.

### Adım 3 — A/V senkron çekirdeği
- **Durum:** BEKLİYOR
- **Tamamlanma:** —
- **Commit:** —
- **Ne yapıldı:**
- **Alınan kararlar:**
- **Bilinen sınırlar:**
- **Sonraki adıma not:**

### Adım 4 — Modül 1: McGurk
- **Durum:** BEKLİYOR
- **Tamamlanma:** —
- **Commit:** —
- **Ne yapıldı:**
- **Alınan kararlar:**
- **Bilinen sınırlar:**
- **Sonraki adıma not:**

### Adım 5 — Modül 2: AVSR
- **Durum:** BEKLİYOR
- **Tamamlanma:** —
- **Commit:** —
- **Ne yapıldı:**
- **Alınan kararlar:**
- **Bilinen sınırlar:**
- **Sonraki adıma not:**

### Adım 6 — Modül 3: TBW
- **Durum:** BEKLİYOR
- **Tamamlanma:** —
- **Commit:** —
- **Ne yapıldı:**
- **Alınan kararlar:**
- **Bilinen sınırlar:**
- **Sonraki adıma not:**

### Adım 7 — Modül 4: Oddball
- **Durum:** BEKLİYOR
- **Tamamlanma:** —
- **Commit:** —
- **Ne yapıldı:**
- **Alınan kararlar:**
- **Bilinen sınırlar:**
- **Sonraki adıma not:**

### Adım 7b — Modül 5: Dikotik dinleme
- **Durum:** BEKLİYOR
- **Tamamlanma:** —
- **Commit:** —
- **Ne yapıldı:** (Adım 1'de config ve DB yeri açıldı: `modules.dichotic`,
  `trials.design_extra` → `left_token`/`right_token`, `blocks.module` CHECK
  listesi. Modül gerçeklemesi bu adımda.)
- **Alınan kararlar:**
- **Bilinen sınırlar:** Yöntem dokümanında tanımlı değil — bkz. bekleyen
  aksiyonlar.
- **Sonraki adıma not:**

### Adım 7c — Modül 6: GIN (Gaps-In-Noise)
- **Durum:** BEKLİYOR
- **Tamamlanma:** —
- **Commit:** —
- **Ne yapıldı:** (Adım 1'de config ve DB yeri açıldı: `modules.gin`,
  `trials.design_extra` → `gap_onsets_s`/`gap_durations_ms`, deneme başına
  0..n yanıt. Uyaran üretimi Adım 2'de, modül gerçeklemesi bu adımda.)
- **Alınan kararlar:** Standart GIN parametreleri (Musiek ve ark., 2005)
  config varsayılanı olarak girildi; eşik ölçütü `4_of_6`.
- **Bilinen sınırlar:** Yöntem dokümanında tanımlı değil — taslak bölüm
  `docs/EK_GIN.docx`, danışman onayı bekliyor. Kulak seçimi katılımcıya bağlı
  (`ear_selection: good_ear`), seçim mantığı Adım 8'de.
- **Sonraki adıma not:**
  - **Config'de eksik alan: yanıt penceresi.** Bir tuş basımının hangi zaman
    aralığında isabet sayılacağı `modules.gin` altında tanımlı değil.
    Puanlama bu adımın işi olduğu için Adım 1'de eklenmedi, ancak
    `response_window_ms` alanı bu adımda şemaya girmeli. Değerin **veri
    toplanmadan önce** sabitlenmesi gerekiyor; sonradan seçilmesi isabet ve
    yanlış alarm oranlarının sonuçlara göre ayarlanabilmesi anlamına gelir.
    `docs/EK_GIN.docx` bu maddeyi danışman kararına bırakıyor.
  - Kontrol grubunda kulak seçimi kuralı (`ear_selection` için yeni bir
    strateji gerekebilir: SSD gruplarının iyi kulak dağılımına oranlı
    dengeleme) danışman kararına bağlı — bkz. `docs/EK_GIN.docx`.

### Adım 8 — Oturum akışı ve arayüz
- **Durum:** BEKLİYOR
- **Tamamlanma:** —
- **Commit:** —
- **Ne yapıldı:**
- **Alınan kararlar:**
- **Bilinen sınırlar:**
- **Sonraki adıma not:**

### Adım 9 — Analiz, dışa aktarım ve entegrasyon
- **Durum:** BEKLİYOR
- **Tamamlanma:** —
- **Commit:** —
- **Ne yapıldı:**
- **Alınan kararlar:**
- **Bilinen sınırlar:**
- **Sonraki adıma not:**

## Açık kararlar (kullanıcı + danışman verecek)

Bunlar §F'den gelir. Karşılaşıldığında burada işaretlenir, karar gelince güncellenir.

- [ ] Deneysel tasarım / deneme sayıları (Adım 4'ten önce netleşmeli) — §F.1
- [ ] Modül 2 kelime listesi (Adım 5, çekim gerekiyor) — §F.2
- [ ] Kulaklık tipi (donanım, çapraz dinleme kontrolünü etkiler) — §F.3
- [ ] Konuşmacı seçim stratejisi — §F.4

### Ek açık kararlar (2026-07-26 depo incelemesinde çıktı)

- [x] **A0-1 — `steps.md` §C Adım 0 ile depo uyuşmuyor.** Doküman "7 adet neredeyse aynı
  `main*.py`, düz CSV yazımı, `conditions.csv`, `assets.zip`" tarif ediyor. Depo bunların
  hiçbirini içermiyor: tek `main.py`, modüler `src/` paketi, SQLite yazımı var.
  **Karar (2026-07-26, kullanıcı):** `src/` yerinde düzeltilecek, `legacy/` altına
  taşınmayacak. Adım 1'de yeni `mcgurk/` paketi yanına kurulacak, `src/` o zaman emekli
  edilecek. `steps.md`'nin "7 main dosyasından birini seç / legacy'ye taşı" maddeleri bu
  depoda karşılıksız olduğu için uygulanmıyor.
- [x] **A0-5 — Mevcut `data/mcgurk.db` içindeki ad-soyad verisi.**
  **Karar (2026-07-26, kullanıcı):** DB bir kez `backups/` altına yedeklenecek, sonra
  anonim kod şemasıyla sıfırdan oluşturulacak. İçerik geliştirme sırasında girilmiş test
  verisidir.
- [x] **A0-2 — Konuşmacı sayısı.** `steps.md` §C Adım 2 "8 konuşmacı × 3 token" diyor;
  `assets/` içinde 2 konuşmacı var. **Karar (2026-07-26, kullanıcı):** 2 konuşmacı ile
  devam edilecek. `steps.md`'nin "8 konuşmacı" ifadesi geçersizdir; Adım 2 kabul kriteri
  "2 konuşmacı × 3 token" olarak okunacak.
- [x] **A0-3 — Uyaran patlama gecikmesi ölçümü.** `steps.md` /ba/ 1105 ms, /da/ 1119 ms,
  /ga/ 1108 ms değerlerini veriyor ve `video_create.py`'ye atıf yapıyor; o dosya depoda yok.
  **Yanıt (2026-07-26, kullanıcı):** Depoda var olanlardan başka kaynak yok. Adım 2'de
  patlama anları mevcut `assets/` dosyalarından **yeniden ölçülecek**; `steps.md`'deki
  sayılar referans alınmayacak.
- [x] **A0-4 — Referans yöntem dokümanı.** **Çözüldü (2026-07-26):** kullanıcı
  `docs/946383_YONTEM (3).docx` dosyasını ekledi. İlgili doğrulamalar: §5.2 demografide
  yalnızca "kullanıcı kodu" (ad-soyad yok — §A.6 ile uyumlu), §5.3 Psychtoolbox, §5.4
  SQLite, §6 görsel merkezde + işitsel kulaklıkla lateralize, §4 yaş aralığı 18–60.
  Not: yöntem dokümanı arayüz için CustomTkinter, uyaran üretimi için MoviePy diyor;
  uygulama PsychoPy `gui.Dlg` ve ffmpeg kullanıyor. Teknik olarak eşdeğer/daha uygun,
  `steps.md` de PsychoPy diyor — sapma burada belgelendi.

## Kullanıcıya bekleyen aksiyonlar

- **Dikotik dinleme — taslak bölüm hazır, danışman onayı bekliyor.**
  `docs/EK_DIKOTIK_DINLEME.docx`, yöntem dokümanının 6.4'ünden sonra **6.5**
  olarak eklenmek üzere yazıldı (2026-07-26): gerekçe, uyaranlar, tasarım
  tablosu, yordam, ölçülen değişkenler (kulak avantajı indeksi), analiz,
  yazılım karşılığı tablosu ve §7'ye eklenmesi önerilen değişken. Belgenin
  sonunda danışmanın karara bağlaması gereken beş madde listelendi (deneme
  sayısı, görevin SSD grubuna uygulanıp uygulanmayacağı, indeksin birincil mi
  kalite kontrol ölçütü mü olduğu, yönerge biçimi, kovaryat kullanımı).
  Kaynak numaraları mevcut kaynakçaya göre yeniden numaralandırılmalı.
- **GIN — taslak bölüm hazır, danışman onayı bekliyor.**
  `docs/EK_GIN.docx`, yöntem dokümanına **6.6** olarak eklenmek üzere yazıldı
  (2026-07-26). Gerekçe, görevin TBW ölçütü için bir kontrol olması üzerine
  kuruldu: geniş bir TBW, modaliteler arası entegrasyon farkından değil düşük
  düzeyli işitsel zamansal keskinlikten kaynaklanıyor olabilir; GIN bu ikisini
  ayrıştırır. Bu, oddball'ın dikkat için üstlendiği role paralel — ölçüt Bölüm
  8 modellerinde kovaryat olarak konumlandırıldı.
  Danışmanın karara bağlaması gereken altı madde listelendi; en kritik ikisi
  **kontrol grubunda kulak seçimi** (taslak, SSD gruplarının iyi kulak
  dağılımına oranlı dengeleme öneriyor) ve **yanıt penceresi süresi**.
- **Adım 1 manuel testleri** (`TEST_ADIM_1.md`): tasarım özeti, config kapısı
  ve push sonrası GitHub Actions.
- **Yaş aralığı kısıtı (K4).** `participants.age` için `CHECK (18–60)` kondu.
  Prova/pilot bu aralık dışında biriyle yapılacaksa gevşetilmeli.
- **§F.1 — deneme sayıları.** Config **minimumlarla** geliyor: 797 deneme /
  ~58.8 dakika (§G örnek değerleri 1167 / ~99.5 dakika veriyordu). Bunlar karar
  değil, başlangıç noktası — danışman her sayıyı config'ten yükseltebilir.
  Ayrıntılı tablo ve gerekçeler `TEST_ADIM_1.md` → K1. Adım 4'ten önce
  netleşmeli.
  - Süre tahmini **alt sınırdır**: `practice` (12) ve `cross_hearing` (20)
    deneme sayısına giriyor ama süreye katılmıyor; yönerge ekranları, kulaklık
    yerleşimi ve modüller arası geçiş hiç sayılmıyor. Gerçek oturumu ~75–80
    dakika olarak planlayın.
- §F.2 (kelime listesi) Adım 5'ten önce; §F.3 (kulaklık tipi) Adım 8'den önce.
- **Konuşmacı 2'nin token'ları arasında 248 ms patlama farkı var** (Adım 2
  ölçümü: ba 1084, da 849, ga 836 ms). Hizalama bunu düzeltiyor, ama fark
  şunu ima ediyor: /da/ ve /ga/ çekimlerinde konuşmacı hem görsel hem işitsel
  olarak daha erken başlamış. Hizalama, kaynak kaydın kendi içinde senkron
  olduğu varsayımına dayanıyor (`steps.md` §C Adım 2'nin gerekçesi). Bu
  varsayım konuşmacı 2 için de geçerli görünüyor, ancak **fotodiyot ölçümü
  (`01_av_gecikme_olcumu.md`) yapılırken konuşmacı 2'nin bir uyumsuz
  denemesiyle de bir kontrol koşulması** varsayımı doğrudan sınar. Adım 3'ün
  kademe 3 ölçümüne not düşüldü.
