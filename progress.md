# İlerleme Raporu — McGurk / SSD Platformu

Son güncelleme: 2026-07-26
Aktif adım: 1 (Adım 0 tamamlandı)

## Durum tablosu

| Adım | Başlık | Durum | Tarih | Commit |
|---|---|---|---|---|
| 0 | Baseline düzeltme | TAMAMLANDI | 2026-07-26 | `f45eeda`…`618ef1c` |
| 1 | Proje iskeleti | BEKLİYOR | | |
| 2 | Uyaran hazırlama | BEKLİYOR | | |
| 3 | A/V senkron çekirdeği | BEKLİYOR | | |
| 4 | Modül 1: McGurk | BEKLİYOR | | |
| 5 | Modül 2: AVSR | BEKLİYOR | | |
| 6 | Modül 3: TBW | BEKLİYOR | | |
| 7 | Modül 4: Oddball | BEKLİYOR | | |
| 8 | Oturum akışı ve arayüz | BEKLİYOR | | |
| 9 | Analiz ve entegrasyon | BEKLİYOR | | |

Durum değerleri: BEKLİYOR / PLAN ONAYINDA / GELİŞTİRİLİYOR / TESTTE / TAMAMLANDI

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
- **Durum:** BEKLİYOR
- **Tamamlanma:** —
- **Commit:** —
- **Ne yapıldı:**
- **Alınan kararlar:**
- **Bilinen sınırlar:**
- **Sonraki adıma not:**

### Adım 2 — Uyaran hazırlama ve kalite kontrol
- **Durum:** BEKLİYOR
- **Tamamlanma:** —
- **Commit:** —
- **Ne yapıldı:**
- **Alınan kararlar:**
- **Bilinen sınırlar:**
- **Sonraki adıma not:**

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

- **Dikotik dinleme görevinin yöntem dokümanına eklenmesi.** Kullanıcı bu bölümün
  çalışmada kullanılacağını bildirdi, ancak `946383_YONTEM (3).docx` içinde
  tanımlı değil. Danışmanla görüşülüp dokümana eklenmeli (ölçülen değişkenler,
  gerekçe, kaç deneme) — aksi hâlde toplanan veri protokol dışı kalır.
- **Adım 1 planının onaylanması (§B.1 kapısı).** Plan sunulduğunda.
- §F.1 (deneme sayıları) Adım 4'ten önce netleşmeli; §F.2 (kelime listesi)
  Adım 5'ten önce; §F.3 (kulaklık tipi) Adım 8'den önce.
- Adım 1'e geçmeden önce §F.1 (deneme sayıları) kararı henüz gerekmiyor; Adım 4'ten
  önce netleşmeli.
