# İlerleme Raporu — McGurk / SSD Platformu

Son güncelleme: 2026-07-30
Aktif adım: 10 — 10a TAMAMLANDI; 10b + 10c-i + 10c-ii kod olarak commit edildi, **manuel test bekliyor (TESTTE)**. 10c bölündü: 10c-i (yol katmanı + --run dağıtıcısı) ✓, 10c-ii (PyInstaller .exe — paketleme dosyaları yazıldı, gerçek derleme kullanıcının Windows makinesinde) ✓. **Adım 10'un tüm kodu yazıldı.** Sıra: **Windows'ta derleme + 10b/10c manuel testler → prova oturumu → master merge + v1.0.0**

## Durum tablosu

| Adım | Başlık | Durum | Tarih | Commit |
|---|---|---|---|---|
| 0 | Baseline düzeltme | TAMAMLANDI | 2026-07-26 | `f45eeda`…`618ef1c` |
| 1 | Proje iskeleti | TAMAMLANDI | 2026-07-26 | `0fb3d3f`…`9dbedee` |
| 2 | Uyaran hazırlama | TAMAMLANDI | 2026-07-26 | `d6e7aaf` |
| 3 | A/V senkron çekirdeği | TAMAMLANDI | 2026-07-26 | `bc215d8` |
| 4 | Modül 1: McGurk | TAMAMLANDI | 2026-07-27 | `709958e` |
| 5 | Modül 2: AVSR | TAMAMLANDI | 2026-07-27 | `79fec8b` |
| 6 | Modül 3: TBW | TAMAMLANDI | 2026-07-27 | `3974aee` |
| 7 | Modül 4: Oddball | TAMAMLANDI | 2026-07-28 | `d6f5340` |
| 7b | Modül 5: Dikotik dinleme | TAMAMLANDI | 2026-07-29 | `160f663` |
| 7c | Modül 6: GIN | TAMAMLANDI | 2026-07-30 | `0294156` |
| 8a | Oturum metinleri + checklist | TAMAMLANDI | 2026-07-30 | `8683fa2` |
| 8b-i | Oturum akışı iskeleti | TAMAMLANDI | 2026-07-30 | `1882dcb` |
| 8b-ii | Alıştırma + çapraz dinleme + ESC onayı | TAMAMLANDI | 2026-07-30 | `82a9a4d` |
| 8c-i | Kesinti/devam (resume) | TAMAMLANDI | 2026-07-30 | `0602fbb` |
| 8c-ii | src emekliliği + master merge | TAMAMLANDI | 2026-07-30 | `56c902e` |
| 8.5 | Arayüz cilası + uçtan uca gösterim | İPTAL | 2026-07-30 | (kullanıcı kararı) |
| 9a | Analiz kütüphanesi (dışa aktarım + ölçümler) | TAMAMLANDI | 2026-07-30 | `d53b61e` |
| 9b | QC + entegrasyon/başarısızlık testleri | TAMAMLANDI | 2026-07-30 | `e24c01a` |
| 9c | Dokümantasyon (+ prova/merge en son kapıda) | TAMAMLANDI | 2026-07-30 | `94c90bc` |
| 10a | Panel çekirdeği (GUI'siz, CI-testli) | TAMAMLANDI | 2026-07-30 | `15d428f` |
| 10b | PySide6 paneli (GUI kabuğu) | TESTTE | 2026-07-30 | `d276cc9` |
| 10c-i | Donmuş yol katmanı + --run dağıtıcısı | TESTTE | 2026-07-30 | `b5141e6` |
| 10c-ii | PyInstaller ile Windows .exe | TESTTE | 2026-07-30 | |

**Adım 9 kod + doküman olarak TAMAMLANDI (kullanıcı onayı, 2026-07-30).** 9a
analiz kütüphanesi, 9b QC + testler, 9c dokümanlar. Prova oturumu ve master merge
**en sona alındı** (aşağıdaki sıra).

**Adım 10 eklendi (kullanıcı isteği, 2026-07-30):** operatör araçları (checklist/
export/analiz/QC) için **buton temelli PySide6 paneli** + **PyInstaller ile Windows
.exe paketleme**. steps.md dışı yeni kapsam; ayrıntılı prompt `docs/ADIM_10.md`.

**Sıra (kullanıcı kararı, 2026-07-30 — güncellendi):** Adım 9 kapat → **Adım 10
(panel + paketleme)** → **prova oturumu** (paketlenmiş app üzerinde — provanın son
teslim biçimini denemesi için) → (bug çıkarsa düzeltme) → `develop → master`
merge + `git tag v1.0.0`. Yani prova ve master merge **en son**, Adım 10'dan
sonra; v1.0.0 = dağıtılabilir Windows uygulaması. Prova kılavuzu `TEST_ADIM_9C.md`
Adım 10 sonrası koşulacak biçime uyarlanacak.

**Adım 8 (oturum akışı) tamamen tamamlandı** — 8a/8b-i/8b-ii/8c-i/8c-ii.
`develop` → `master` merge + `git tag adim-8-oturum-akisi` yapıldı.

**Adım 9 alt adımlara bölündü (kullanıcı kararı, 2026-07-30).** En büyük ve son
kod adımı olduğu için 9a (analiz kütüphanesi: dışa aktarım + ölçümler), 9b (QC
raporu + uçtan uca entegrasyon + başarısızlık modu testleri) ve 9c
(dokümantasyon + prova oturumu kapısı + `master` merge + `v1.0.0`) diye üçe
ayrıldı; her birinde 7b/7c/8 gibi ayrı plan-onay, test ve commit. `master`
yalnızca 9c sonunda güncellenir (dal politikası değişmedi).

Durum değerleri: BEKLİYOR / PLAN ONAYINDA / GELİŞTİRİLİYOR / TESTTE / TAMAMLANDI

**Adım 7b ve 7c `steps.md`'de yoktur** — kullanıcı kararıyla eklendi
(2026-07-26). Dikotik kodda zaten vardı; GIN (Gaps-In-Noise) yeni bir istek.
İkisi de Adım 8'den önce bitmeli, çünkü Adım 8 modülleri oturuma bağlıyor.
`steps.md` §C'ye karşılık gelen iki bölümün yazılması gerekiyor.

**Commit sırası 7b ve 7c'de gevşetildi (kullanıcı kararı, 2026-07-29).**
§B.2 adım 4 normalde manuel test onayı gelmeden commit edilmemesini söyler; bu
iki adımda kod önce commit ediliyor, manuel test sonra yapılıyor. Karşılığında
adım manuel test onayı gelene kadar `TAMAMLANDI` değil **`TESTTE`** olarak
işaretleniyor ve düzeltme gerekirse ayrı bir commit geliyor. Adım 7b'de bu
gecikme kısa sürdü: kod `160f663` ile commit edildi, manuel testler aynı gün
yürütüldü ve geçti.

**Adım 8 alt adımlara bölündü (kullanıcı kararı, 2026-07-30).** En büyük parça
olduğu için 8a (oturum metinleri + checklist), 8b (oturum akışı çekirdeği) ve
8c (kesinti/devam + entegrasyon + master merge) diye üçe ayrıldı; her birinde
7b/7c gibi ayrı plan-onay, test ve commit. Ayrıca **src/ Adım 8 sonunda (8c)
emekliye ayrılacak** (kullanıcı kararı, 2026-07-30): `main.py` yeni oturum
akışına yönlendirilecek, eski `src/` + `config.yaml` + `data/mcgurk.db` legacy'ye
alınacak. Dal politikası değişmedi — master yalnızca 8c sonunda ve Adım 9 sonunda
güncellenir.

## Dal politikası — master'a ne zaman merge edilir

**Karar (2026-07-26, kullanıcı):** `master` yalnızca **iki dönüm noktasında**
güncellenir. Geliştirme `develop` üzerinde sürer.

| Ne zaman | Neden orası | Yapılacak |
|---|---|---|
| **Adım 8 sonu** | Yeni paketin ilk kez baştan sona bir oturum koşabildiği nokta. O ana kadar `python main.py` eski `src/` yolunu kullanıyor, yani master'a alınacak "çalışan platform" yok. | `develop` → `master` merge + `git tag adim-8-oturum-akisi` |
| **Adım 9 sonu** | `steps.md` §C: "Bu adım bittiğinde kod tarafı tamamlanmış olur." Prova oturumu kapısı da orada. | `develop` → `master` merge + `git tag v1.0.0` |

Ara adımlarda merge edilmez: `master` ile `develop` birebir aynı olduğunda iki
dal ayrımı anlamını yitirir ve "master ne zaman güncellenir?" sorusunun cevabı
kalmaz (depo iş akışı: `master` = stable releases).

**2026-07-26 itibarıyla `master` hâlâ GitHub'ın attığı "Initial commit"te**
(`2398acd`, yalnızca `LICENSE` + tek satırlık `README.md`), 26 commit geride ve
0 commit ileride — yani merge sırası geldiğinde **fast-forward** olacak,
çakışma riski yok. Bunun tek yan etkisi, `origin/HEAD → master` olduğu için
depoyu klonlayan veya GitHub'da açan birinin boş bir depo görmesi. Gerekirse
merge beklemeden GitHub'da varsayılan dal `develop` yapılabilir (Settings →
Branches); bu, master'ın "sürüm" anlamını korur.

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
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-26. Otomatik testler yeşil (381 test, ruff + mypy
  temiz; CI alt kümesi 332), `TEST_ADIM_3.md` manuel testleri kullanıcı
  tarafından yürütüldü ve geçti.
- **Commit:**
  - `bc215d8` — mcgurk/engine paketi, timing_selftest aracı, config'te
    expected_refresh_hz 75

- **Ne yapıldı:**
  - **Yeni paket `mcgurk/engine/`**, dört katmana ayrıldı — ayrım "çalışmak
    için neye ihtiyaç duyuyor" ölçütüne göre:
    - `scheduling.py` — pay hesabı, ses planlama anı, gerçekleşen SOA, kare
      istatistiği. **PsychoPy yok, G/Ç yok.** Sesin ne zaman başlayacağına
      karar veren kod böylece ekransız ve ses kartsız bir makinede test
      edilebiliyor (kabul kriteri: "sentetik zaman damgalarıyla, PsychoPy'sız").
    - `audio.py` — lateralizasyon, kalibrasyon trim'i, PTB kapısı, aygıt açma.
      Dizi işleri saf numpy; yalnızca `sound.Sound` kurulumu PsychoPy'ye
      dokunuyor ve onu lazy import ediyor.
    - `window.py` — pencere, **ölçülen** yenileme hızı, kare aralığı kaydı,
      sabitleme haçı.
    - `av_presenter.py` — `TrialSpec` → sunum → `TimingRecord`.
    - `loopback.py` — kademe 2 jitter analizi (saf numpy).
    - `psychopy_prefs.py` — `psychopy.sound` import'undan önce çalışması
      gereken tek yer.
  - **`tools/timing_selftest.py`**: kademe 1 (donanımsız), kademe 2 (loopback,
    `--play` / `--analyze` iki fazlı), kademe 3 (fotodiyot yönergesi —
    `docs/01`'i yeniden yazmıyor), `--demo` (hazırlanmış uyaranlarla altı
    gerçek deneme), `--devices` / `--device` (aygıt listeleme ve tek koşuluk
    ezme).
  - **Test: 80 yeni test (301 → 381).** CI'da koşanlar: zamanlama matematiği
    (34), ses dizisi hazırlama (16), loopback analizi (9), TrialSpec/
    TimingRecord sözleşmesi (9), paket sınırı (yeni 6). Gerçek donanımda
    koşanlar (`psychopy` işaretli, 6): pencere + ses aygıtı açılıyor,
    hazırlanmış uyaranlarla AV / −200 ms SOA / A-only / V-only denemeleri
    sunuluyor, negatif SOA'da sesin videodan önce başladığı ve payın
    config'teki 6 kareyi aştığı doğrulanıyor.
  - **Manuel doğrulama** (kullanıcı): sol/sağ kulak izolasyonu, deneme 3↔4
    farkı, V-only sessizliği, ESC'nin video ortasında çalışması, kademe 3
    yönergesi.

- **Alınan kararlar:**
  - **`trials.actual_soa_ms` = katılımcının yaşadığı SOA** (kullanıcı kararı,
    2026-07-26): yazılımda ölçülen fark **artı** uygulanan
    `system_av_offset_ms`. Nominal ile doğrudan karşılaştırılabilir olması
    seçildi; ham yazılım farkı `actual_soa_ms − sessions.system_av_offset_ms`
    ile geri hesaplanıyor. Alternatif (ham farkı saklamak) analizde D'nin elle
    eklenmesini gerektirirdi ve unutulduğunda sistematik bir kayma olarak
    görünürdü.
  - **Fark iki akışın akustik patlama anları arasında ölçülüyor**, dosya
    başlangıçları arasında değil. Hazırlanmış dosyalardaki kalıntı hizalama
    hatası (< 1 ms, Adım 2) böylece varsayılmak yerine kayda giriyor.
  - **Çalışma anında gürültü karıştırma yok** (plan onayında kullanıcıyla
    doğrulandı). `steps.md` §C Adım 3 SNR karıştırmayı `engine/audio.py`'ye
    koyuyor, ama o madde Adım 2'den önce yazılmış: gürültülü dosyalar artık
    offline üretiliyor ve §A.12 çalışma anında ağır DSP'yi zaten yasaklıyor.
    `mix_at_snr` `stimuli/dsp.py`'de kaldı, yalnızca hazırlıkta kullanılıyor.
    Motorun ses tarafındaki işi dosyaya gömülemeyecek olanlar: **lateralizasyon**
    (kulak bir tasarım değişkeni, tek mono dosya iki kulağa hizmet ediyor) ve
    **kalibrasyon trim'i** (makineye ve kulaklığa ait, uyarana değil).
  - **Pay (lead) denemeye göre hesaplanıyor.** Config'in `lead_frames: 6`
    değeri 60 Hz'de 100 ms eder ve TBW'nin −300 ms'ine yetmez; taban değer
    olarak kullanılıyor, gereken pay her denemede `|SOA − D|` üzerinden
    yeniden hesaplanıyor (−300 ms için 60 Hz'de ~19 kare). Üst sınır 1 saniye
    (`max_lead_s`): aşılırsa deneme **hata veriyor**. Sessizce bir saniye
    bekleyen bir deneme "başarısız olmuş" görünmez, tam da bu yüzden
    başarısız olması sağlandı.
  - **Lateralizasyonda karşı kanal tam sıfır**, kısılmış değil. Manipülasyonun
    anlamı, ses kartının o tarafa hiçbir şey göndermemesi; oraya ulaşan şey
    kafatası yoluyla ulaşmış demektir ve Adım 8'in çapraz dinleme kontrolü
    tam olarak onu ölçecek.
  - **Kalibrasyon trim'i kırpma yaparsa hata**, limiter yok. Çalışmadaki her
    seviye kalibrasyon sayılarından türüyor; limiter yanlış bir trim'i sessizce
    bozulmuş ama geçerli görünen bir uyarana çevirirdi.
  - **Aygıtın akış hızı `audio.sample_rate` ile karşılaştırılıyor**, tutmazsa
    program duruyor. PsychoPy aksi hâlde her uyaranı yükleme anında yeniden
    örnekler ve setin 48 kHz'de hazırlanmış olması anlamını yitirirdi.
  - **Kademe 2 penceresiz koşuyor.** Ölçtüğü şey ses yolunun jitter'ı; pencere
    açmak ekranın zamanlamasını ses kartı hakkındaki bir sayıya karıştırırdı.
  - **Kademe 3 gerçeklenmedi**, `docs/01_av_gecikme_olcumu.md`'ye yönlendiriyor
    (`steps.md`: "yeniden yazma"). Çıktısına projeye özel bir not eklendi:
    doğrulama süpürmesine konuşmacı 2'nin bir uyumsuz denemesi de konmalı
    (Adım 2'nin 248 ms bulgusu, hizalamanın dayandığı varsayımı doğrudan sınar).

- **PsychoPy 2026.1 API'siyle ilgili üç bulgu (Adım 0'daki `sound.audioLib`
  olayının devamı):**
  - **`prefs.hardware['audioLatencyMode']` tercih şemasından kaldırılmış.**
    Gecikme sınıfı artık `SpeakerDevice(latencyClass=...)` argümanı ve
    **varsayılanı 1** — yani "aygıtı sistemle paylaş". Eski anahtarı yazmak
    hata vermiyor, configobj kabul edip sessizce yok sayıyor; config'teki
    `timing.audio_latency_mode: 3` hiç uygulanmamış olacaktı. Artık
    `audio.open_speaker()` içinde uygulanıyor.
  - **`SoundPTB.statusDetailed['StartTime']` bir ölçüm değil.** Bu makinede
    (WASAPI, gecikme sınıfı 3) istenen zamanın **birebir aynısı** dönüyor;
    aygıt çıkış damgası vermediği için (`PredictedLatency` ve `LatencyBias`
    ikisi de 0) PTB'nin bildirecek başka bir şeyi yok. İlk yazdığım alan adı
    `audio_onset_measured` idi ve planlanan zamanı "ölçüldü" diye kaydederdi;
    `audio_onset_reported` olarak değiştirildi ve ne olduğu docstring'e
    yazıldı. Onset'i doğrulayan tek şey fiziksel ölçüm: kademe 2 (jitter) ve
    fotodiyot (mutlak gecikme). Aynı status sözlüğündeki **`TimeFailed` ve
    `XRuns` ise gerçek** — sıfır değilse ses istendiği anda çıkmamıştır — ve
    her denemede okunup loglanıyor.
  - **`MovieStim.frameIndex` her zaman 0 dönüyor** (gövdesi `return 0`);
    hangi karenin gösterildiğini öğrenmek için `pts` kullanılıyor.
    **`movie.stop()` dosyayı diskten yeniden yüklüyor**, bu yüzden denemeler
    arasında hiç çağrılmıyor (`pause()` / `unload()`).

- **Manuel test turunda çıkan bulgu — ses duyulmuyordu:**
  Sorun kodda değildi: `audio.device: null` olduğu için PTB **listedeki ilk
  aygıtı** seçiyordu, o da hiçbir şeyin bağlı olmadığı SPDIF dijital çıkışıydı.
  Sessizlik burada şanslı sonuç; şanssız olanı oturumun fark edilmeden monitör
  hoparlöründen toplanmasıydı. Araca `--devices` (aygıtları listeler, config'in
  hangisini seçtiğini işaretler) ve `--device` (config'e dokunmadan tek koşuluk
  ezer; değer şemadan geçtiği için hatalı ad orada patlar) eklendi. Kademe 1
  ayrıca `audio.device` boşken uyarı basıyor. Gerçek veri toplamada bu hata
  oluşamaz — `data_collection` config kapısı `audio.device`'ı zaten zorunlu
  kılıyor (Adım 1).

- **Bilinen sınırlar:**
  - **Kademe 2 (loopback) koşulmadı** — ses arayüzü ve kablo yok. Kod yazıldı,
    analiz sentetik kayıtlarla test edildi (bilinen 3 ms jitter enjekte edilip
    ±1 ms içinde geri okunuyor). Donanım geldiğinde koşulacak; `TEST_ADIM_3.md`
    yordamı içeriyor.
  - **Kademe 3 (fotodiyot) yapılmadı** — tasarım gereği tüm kod bittikten
    sonra. `timing.system_av_offset_ms` hâlâ `null`, motor 0 kabul ediyor ve
    oturum başına bir kez uyarı loglanıyor.
  - **Test kulaklığı Bluetooth (WH-1000XM4) ve veri toplama için uygun değil**
    — aşağıdaki bekleyen aksiyona işlendi.
  - **İlk denemenin flip'i birkaç ms kayabiliyor** (ölçülen: +5.13 ms, kare
    13.3 ms). İlk video çözümlemesinin ısınma maliyeti; sonraki denemelerde
    1–2 ms'e iniyor. Kayda giriyor (`flip_error_ms`, ve dolayısıyla
    `actual_soa_ms`). Adım 8'in alıştırma bloğu bu ısınmayı doğal olarak
    karşılayacak.
  - **`TimeFailed`/`XRuns` veritabanına yazılmıyor**, yalnızca loglanıyor —
    `trials`'ta sütunları yok. §A.4'ün istediği alanlar arasında değiller;
    Adım 9'un QC raporu isterse şema kararı orada verilir.
  - Motor henüz hiçbir modül tarafından kullanılmıyor; `TrialSpec` üretimi
    Adım 4'ün işi.

- **Sonraki adıma not:**
  - **Adım 4 `TrialSpec`'i manifest'ten kuracak.** Presenter açık yollar ve
    patlama anları alıyor (`video_path`, `video_burst_s`, `audio_path`,
    `audio_burst_s`, `ear`, `nominal_soa_ms`); gürültülü koşulda
    `manifest.noisy(...)`'den gelen 3 varyanttan birini tohumlanmış RNG ile
    seçmek ve hangisinin kullanıldığını `design_extra`'ya yazmak modülün işi.
  - **RT referansı hazır:** `TimingRecord.burst_onset_s` akustik patlamanın
    duvar saati (oturum referansına göre). `responses.rt_from_burst_ms` bundan
    hesaplanacak; `rt_from_prompt_ms` yanıt ekranının kendi flip'inden.
  - **Yanıt toplama motorda yok.** `check_abort()` ve `ABORT_KEY`
    `av_presenter.py`'de; Adım 4 tuş toplamayı eklerken `event.getKeys`'in
    `keyList` dışındaki tuşları **tamponu boşaltarak** attığına dikkat etmeli.
  - `AVPresenter` `fixation` alıyor ve video olmayan denemelerde onu çiziyor;
    sabitleme süresi ve deneme yapısı Adım 4'ün kararı.
  - `TimingRecord.to_trial_timing()` doğrudan `db.set_trial_timing()`'e
    veriliyor — modül ayrıca bir dönüşüm yazmamalı.
  - **Adım 8'in kontrol listesi bu adımdan üç şey devralabilir:**
    `window.measure_refresh_hz` + `check_refresh_hz(strict=True)`,
    `audio.open_speaker` (aygıt adı ve örnekleme hızı kapısı) ve
    `audio.require_ptb_backend`.

### Adım 4 — Modül 1: McGurk
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-27. Otomatik testler yeşil (381 → **451 test**,
  ruff + mypy temiz; CI alt kümesi 401). `TEST_ADIM_4.md` manuel testleri
  kullanıcı tarafından yürütüldü ve geçti; Test 8'in ölçüm kısmı (süre, blok
  yapısı, kare/ses istatistiği) simüle yanıtlarla önceden koşulmuştu.
- **Commit:**
  - `709958e` — mcgurk/modules paketi, run_module aracı, config'te yanıt
    alanları, design_extra'da speaker_id/noise_instance (şema sürümü 2),
    DeviceNotConnectedError düzeltmesi

- **Ne yapıldı:**
  - **`mcgurk/modules/` dolduruldu**, motorla aynı ölçüte göre dört dosyaya
    ayrıldı ("çalışmak için neye ihtiyaç duyuyor"):
    - `base.py` — modül başına tohum türetme, tur bazlı sıralama, gürültü
      varyantı dağıtımı, `PlannedTrial`, blok parçalama. **PsychoPy yok.**
    - `mcgurk.py` — çaprazlama, deneme listesi, manifest'ten yol/patlama
      çözümü, kategorizasyon. **PsychoPy yok** (paket sınırı testine eklendi).
    - `response.py` — yanıt ızgarası, klavye, iki RT, serbest metin.
    - `block.py` — sabitleme → sunum → yanıt → DB döngüsü ve blok sınırları.
  - **`tools/run_module.py`** — geliştirme koşucusu: `--dry-run` (donanımsız
    tasarım denetimi + dosya kontrolü), `--limit N` (kısa koşu), `--seed`,
    `--speaker-id`, `--device`. Oturum satırını `provenance` ile dolduruyor;
    kapanışta `db.backup()` çağırıyor.
  - **Config'e Adım 4'ün ihtiyaç duyduğu alanlar** (§A.9): `response_keys`,
    `free_text_response`, `fixation_duration_ms`, `post_response_ms`,
    `prompts.{question,other,timeout}`. Şema `response_keys` ↔ `response_set`
    birebir eşlemesini, tekrarsızlığı ve `free_text_response`'un sette
    olduğunu doğruluyor.
  - **`db/design.py` → `McGurkExtra`**: `speaker_id` (zorunlu) ve
    `noise_instance` (gürültülüde 1–3, sessizde null). `v_trials_flat` bu iki
    alanı sütun olarak açıyor; VIEW değiştiği için **şema sürümü 1 → 2**.
    Etkisi yok: `data/mcgurk.sqlite` bu makinede hiç oluşturulmamıştı.
  - **`db.next_block_index()`** eklendi — bir modül birden fazla blok
    üretiyor, blok indeksi veritabanından alınıyor.
  - **Test: 69 yeni test (381 → 450).** CI'da koşanlar: sıralama/tohum
    matematiği (21), tasarım üretimi + kategorizasyon + config kapıları (39).
    Gerçek donanımda koşanlar (`psychopy` işaretli, 6): **betiklenmiş
    klavyeyle** gerçek pencere ve ses aygıtında tam blok döngüsü — zamanlama
    kaydı, iki RT, füzyon kategorisi, zaman aşımının satır üretmemesi, blok
    sınırında commit, çok bloklu bölünme.
  - **Kendi koşabildiğim doğrulamalar:** `--dry-run` (140 deneme, 23 dosya,
    20 hücre), bir denemelik canlı duman koşusu (oturum satırı, yedek, özet;
    `audio_backend: ptb`, `measured_refresh_hz: 74.94`, `actual_soa_ms: 0.04`).

- **Tam uzunlukta dayanıklılık koşusu (Test 8'in insan gerektirmeyen kısmı,
  2026-07-27):** 140 deneme, tam ekran, 75 Hz, yanıtlar simüle (sabit tuş,
  700 ms). Betik scratchpad'de tutuldu ve scratchpad'deki bir veritabanına
  yazdı — uydurma yanıt üretebilen bir bayrak `tools/`'a girmemeli, çünkü
  uydurma bir satır `data/mcgurk.sqlite`'a düştüğünde gerçeğinden ayırt
  edilemez.

  | Ölçüm | Sonuç |
  |---|---|
  | Süre | **11.69 dk** (140 deneme, 5.01 s/deneme) — config'in tahmini 14.0 dk |
  | Bloklar | 60 / 60 / 20, üçü de `completed`, her biri ayrı commit |
  | Düşen kare | **0** (en kötü kare aralığı 15.58 ms; kare 13.33 ms, sınır 20.00 ms) |
  | `TimeFailed` / `XRuns` | **0** |
  | `actual_soa_ms` | ort **−0.061 ms**, SD 0.213, aralık [−1.07, +0.50] |
  | `rt_from_burst − rt_from_prompt` | 1512 ms — patlamadan sonra kalan video süresiyle (≈1.52 s) tutuyor |
  | Yanıt satırı | 140/140, `is_correct` hepsinde NULL |

  Süre tahmini gerçekçi: 700 ms'lik bir yanıtla deneme 5.0 s sürüyor, gerçek
  RT 1–1.5 s olacağı için 5.3–5.8 s, yani config'in 6.0 s'i **üst sınıra
  yakın ama aşılmıyor**. McGurk modülü için ~12–13.5 dk planlanabilir.

  Kategori dağılımı (OTHER 80 / FUSION 40 / AUDITORY 20) bir algı ölçümü
  değil — sabit "DA" tuşunun tasarımdaki karşılığı — ama **tam tasarım
  üzerinde kategorizasyonun doğruluğunu** gösteriyor: ga|ba'nın 40 hücresi
  FUSION, da|da'nın 20'si AUDITORY, kalan 80 OTHER. Beklenen sayılarla birebir.

- **Alınan kararlar:**
  - **Modül başına türetilmiş tohum** (`derive_seed(session_seed, "mcgurk")`).
    Tek bir RNG akışı paylaşılsaydı `session.module_order`'da modülün yerini
    değiştirmek McGurk'ün deneme sırasını da değiştirirdi; oysa tasarımında
    hiçbir şey değişmiyor. `sessions.seed` yine tek başına her sırayı
    belirliyor (§A.11).
  - **`block_shuffle` = tur bazlı, eşit yayılımlı.** Uyumlu kontroller
    (`reps: 5`) uyumsuz çiftlerin (`reps: 10`) yarısı kadar; naif tur yapısı
    kontrollerin tamamını oturumun ilk yarısına koyup ikinci yarıyı tamamen
    uyumsuz bırakırdı. Az tekrarlı hücre `floor(k·R/r)` ile yayılıyor.
  - **Gürültü varyantı hücre içinde dengelenmiş** (3 varyant / 10 tekrar →
    4/3/3), bağımsız çekimle değil: bağımsız çekim 7/2/1 üretebiliyor ve o
    zaman "aynı dalga formunu tekrar tekrar duymama" amacı kayboluyor.
    Kullanılan varyant `design_extra.noise_instance`'a yazılıyor.
  - **`speaker_id` deneme başına kaydediliyor.** Config snapshot'ı yalnızca
    `speaker_selection.strategy: fixed` iken konuşmacıyı sabitliyor; §F.4
    `balanced`/`random`'ı açık bırakıyor. `plan_trials(..., speaker_id=...)`
    Adım 8'in katılımcı başına seçim yapmasına izin veriyor, modül kendi
    başına karar vermiyor.
  - **Blok = en fazla `session.break_every_n_trials` deneme** (140 → 60/60/20).
    §A.5 commit'i blok sonuna koyuyor; tek blok olsaydı bir çökme 14 dakikalık
    commit edilmemiş veriyi götürürdü. Adım 8 mola ekranlarını aynı sınırlara
    koyacak.
  - **İki RT tek ölçümden.** `rt_from_prompt_ms` klavyenin kendi saatinden
    (yanıt ekranının flip'inde sıfırlanıyor); `rt_from_burst_ms` = o sayı +
    (prompt flip − patlama) farkı. Alternatif — tuşun mutlak zaman damgasından
    patlama zamanını çıkarmak — klavye arka ucunun ptb saatiyle damgalamasına
    bağlı olurdu. Bu makinede öyle, ve fark **kontrol edilip loglanıyor**
    (`_check_clock_agreement`), ama hesap ona dayanmıyor.
  - **Yanıt ekranından önceki tuş basımları atılıyor** ve sayısı loglanıyor.
    Video sırasında basılan bir tuş sıfıra yakın RT ile kaydedilirdi.
  - **Zaman aşımında `responses` satırı yok** (Adım 1 kararı). `NONE`
    kategorisi satırın yokluğundan türetiliyor; `categorise(None)` de `NONE`
    dönüyor, yani QC ve analiz aynı sözlüğü kullanıyor.
  - **`is_correct` bu modülde her zaman NULL** — uyumlu kontroller dahil
    (tetikleyici modül adına bakıyor). Uyumlu hücrede doğruluk `AUDITORY`
    kategorisinden türetiliyor: aynı bilgi, skor değil algı olarak.
  - **Serbest metin metninden kategori çıkarılmıyor.** Katılımcı, yazdığı
    seçenek ekranda dururken "DİĞER"i seçti; metni o seçeneğin kategorisine
    saymak vermeyi reddettiği yanıtı uydurmak olurdu. Metin `free_text`'e
    ham hâliyle giriyor, `raw_response` `DIGER` kalıyor.
  - **Fare desteği yazılmadı.** steps.md "fare opsiyonel" diyor; karışık girdi
    her RT modelinde `input_device`'ı kovaryat yapardı. Sütun duruyor.
  - **Serbest metin yalnızca ASCII harf/rakam + boşluk + tire.** Alan hece
    transkripsiyonu için; PsychoPy'nin Türkçe ölü tuş adları güvenilir değil.
  - **Kategorizasyon sırası sabit** (işitsel > görsel > füzyon > kombinasyon)
    ve config doğrulaması buna dayanıyor: bir haritanın çiftin kendi
    token'ını içermesi **hata**, çünkü o kural hiç çalışmaz ve yazan kişi
    çalışmasını bekler.
  - **Onay geri bildirimi yalnızca "tuş algılandı"** (seçenek kısa süre
    sarıya dönüyor). Doğru/yanlış geri bildirimi yok: McGurk etkisini oturum
    sırasında öğretmek talep karakteristiği yaratır.

- **Dayanıklılık koşusunun ortaya çıkardığı bir kod açığı (Adım 3'ten
  kalmış):** `audio.device` bağlı olmayan bir aygıtı gösterdiğinde
  `open_speaker` operatör mesajı yerine çıplak bir traceback veriyordu.
  Sebebi: **PsychoPy 2026.1'in `DeviceNotConnectedError`'ı `Exception`'dan
  değil doğrudan `BaseException`'dan türüyor**, yani `except (ConnectionError,
  OSError, ValueError, KeyError)` onu yakalamıyor — ve yukarıdaki hiçbir
  `except Exception` de yakalamaz. İstisna adıyla yakalanıyor, mesaj artık
  aygıtın bağlı olup olmadığını sormakla `--devices` komutunu söylüyor.
  Regresyon testi var olmayan bir aygıt adı deniyor ve **çalışan bir aygıt
  gerektirmiyor** (aksi hâlde tam olarak tarif ettiği makine durumunda
  atlanırdı). `steps.md` §C Adım 9'un "ses aygıtı kayboluyor → açık hata"
  başarısızlık modu böylece şimdiden karşılanıyor.

- **Config'e `audio.device` yazılması kırılgan bir testi düşürdü** (kullanıcı,
  2026-07-27): `test_all_problems_are_reported_at_once` gönderilen config'in
  hangi alanlarının boş olduğuna güveniyordu. Test artık gated alanların
  hepsini kendisi boşaltıyor — aksi hâlde fotodiyot ölçümü yapıldığı gün de
  aynı şekilde kırılırdı.

- **Yol boyunca çıkan iki test altyapısı sorunu:**
  - **PTB aygıtı oturum başına bir kez açılmalı.** İki `psychopy` işaretli
    test dosyası kendi modül kapsamlı aygıtını açınca, gecikme sınıfı 3'te
    aygıt tekelde olduğu için ikinci dosya **sessizce atlanıyordu** ve hangisi
    olduğu toplama sırasına bağlıydı. `tests/conftest.py`'ye oturum kapsamlı
    `hardware_speaker` fixture'ı eklendi; iki dosya da onu kullanıyor.
  - **`MCGURK_TEST_AUDIO_DEVICE`** ortam değişkeni eklendi: config'teki aygıt
    bir Bluetooth kulaklık olduğu için kapalıyken tüm donanım süiti atlanıyor.
    Fixture'ın sessizce başka bir aygıt seçmesi alternatifi, testlerin hangi
    aygıtta koştuğunu gizlerdi.
  - **`test_package_boundaries.py` modülleri `importlib.reload` ediyor** ve
    bundan sonra `mcgurk.config.schema.DisplayConfig` artık başka bir sınıf
    nesnesi oluyor: `config.display = DisplayConfig(...)` ataması pydantic'te
    "geçerli bir DisplayConfig değil" hatası veriyor — ama yalnızca tam
    süit koşarken. Blok testi alan alan atama yapıyor
    (`config.display.fullscreen = False`) ve bu tuzak yorumda yazıyor.
    **Adım 5–9 testleri için not:** yeniden yüklenmiş bir şemadan sonra sınıf
    kimliğine güvenilmez.

- **Bilinen sınırlar:**
  - Modül tek başına koşuyor; yönerge, alıştırma, mola, katılımcı girişi ve
    kesilen oturumdan devam Adım 8'de. `tools/run_module.py` bir geliştirme
    aracı, oturum akışı değil.
  - `audio.device` hâlâ `null` → duman koşusu bağlı olmayan SPDIF çıkışına
    gitti. `data_collection` kapısı bunu zorunlu kılıyor ama geliştirme
    koşularında hâlâ sessiz bir tuzak (aşağıdaki bekleyen aksiyon).
  - `timing.system_av_offset_ms` `null`, yani `actual_soa_ms` mutlak A/V
    gecikmesini içermiyor (fotodiyot ölçümü sonrası anlam kazanacak).
  - Yanıt ızgarası 1920×1080 için sabit piksel değerleriyle yerleştirildi
    (5 + 4 sütun, 300×130 px aralık). Başka bir çözünürlükte taşarsa
    parametreler `ResponseGrid`'de; config'e taşımak Adım 8'in arayüz işi.
  - Klavye zaman damgasının ptb saatiyle uyuşup uyuşmadığı **loglanıyor ama
    veritabanına yazılmıyor**; QC raporu isterse şema kararı Adım 9'da.
  - Süre tahmini (`estimated_trial_duration_s: 6.0`) gerçek deneme yapısıyla
    karşılaştırılmadı: sabitleme 1.0 s + video 2.57 s + yanıt (≤5 s) + 0.3 s
    ≈ 5–9 s. Test 8 (tam blok) gerçek süreyi verecek.

- **Sonraki adıma not:**
  - **Adım 5 (AVSR) `base.py`'yi doğrudan kullanabilir**: `derive_seed`,
    `order_cells`, `balanced_cycle`, `PlannedTrial`, `chunk`. Yeni olan şey
    V-only hücrelerinin gürültü ve kulakla çaprazlanmaması (§C Adım 5) ve
    doğruluk skorlaması — AVSR'de `is_correct` **var**, tetikleyici yalnızca
    `mcgurk`/`dichotic`'i engelliyor.
  - **`response.py` yeniden kullanılabilir**: `ResponseGrid` etiket + tuş
    listesi alıyor, modüle bağlı değil. AVSR'nin kapalı setine ve dikotiğin
    dört seçeneğine olduğu gibi uyuyor. `PromptTexts` modeli de paylaşımlı —
    her modülün config'ine `prompts` bloğu eklenmeli.
  - **`block.py` kopyalanmamalı, ihtiyaç ortaya çıkınca ortaklaştırılmalı.**
    AVSR'nin döngüsü McGurk'ünkiyle neredeyse aynı (tek fark skorlama ve
    A/V/AV yolları); TBW'nin yanıt seti iki seçenekli; GIN ve oddball
    uyaran içinde 0..n yanıt topluyor. İkinci örnek gelince ortak kısmı
    `base.py`'ye çekmek doğru zaman olur.
  - Adım 8 `tools/run_module.py`'nin oturum kurulumunu devralacak: katılımcı
    satırı, `SessionRecord` alanları (provenance + ölçülen yenileme +
    backend + aygıt), kapanışta `finish_session` + `db.backup()`. Kod orada
    hazır örnek olarak duruyor.
  - Adım 9 `v_trials_flat`'tan okurken artık `speaker_id` ve `noise_instance`
    sütunlarını da bulacak. Füzyon oranı = `category = 'FUSION'` / sunulan
    uyumsuz deneme; zaman aşımı `response_id IS NULL` ile sayılıyor.

### Adım 5 — Modül 2: AVSR
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-27. Otomatik testler yeşil (451 → **556 test**,
  ruff + mypy temiz; CI alt kümesi 502). `TEST_ADIM_5.md` Test 1 kullanıcı
  tarafından yürütüldü ve geçti: 12/12 deneme, 0 düşen kare, 0 ses zamanlaması
  bozulması, üç sunum modu da doğru sunuldu.
- **Commit:**
  - `79fec8b` — mcgurk/modules/avsr.py, block.py'nin ortaklaştırılması,
    kelime listesi altyapısı, konsol kodlama düzeltmesi ve testi

- **Ne yapıldı:**
  - **`mcgurk/modules/avsr.py`** — `stimulus_sets × presentation_modes ×
    noise_conditions × ears` çaprazlaması, tohumlu sıralama, manifest'ten yol
    çözümü, skorlama ve türetilen ölçütler. **PsychoPy yok** (paket sınırı
    testine eklendi). Mevcut config ile **135 deneme**: 3 hece × 5 tekrar = 15
    öğe; A ve AV her biri 15 × 2 gürültü × 2 kulak = 60; V-only 15.
  - **`block.py` ortaklaştırıldı.** Adım 4'ün notu "ikinci örnek gelince ortak
    kısmı çek" diyordu; AVSR o ikinci örnek. Döngü (sabitleme → sunum → yanıt →
    DB → blok sınırı) tek yerde; modül farkı bir `TrialPolicy`'de: hangi ızgara,
    yanıt ne anlama geliyor, doğru cevap var mı. `run_mcgurk` ve `run_avsr`
    ince sarmalayıcı. McGurk'ün altı donanım testi değişmeden geçiyor.
  - **Config'e AVSR yanıt alanları** (§A.9): `response_set` (BA/DA/GA),
    `response_keys`, `free_text_response: null`, `fixation_duration_ms`,
    `post_response_ms`, `randomization`, `prompts` ve **`mode_questions`**.
    McGurk ile ortak olan yedi alan `ResponseUIConfig` tabanına çekildi; hata
    mesajları `config_path` ClassVar'ı üzerinden doğru bölümü adlandırıyor.
  - **Kelime listesi altyapısı** (§F.2, içerik boş): `mcgurk/config/word_lists.py`
    (Pydantic şema + okuyucu), `config/word_lists/tr_pb_50.yaml` (şablon,
    `items: []`) ve `config/word_lists/README.md` (biçim + devreye alma
    adımları). Listeyi **loader** okuyor — şema diske dokunmuyor kuralı korundu —
    ve okuduktan sonra tasarım kontrolünü tekrar koşuyor.
  - **`db/design.py`:** `AVSRExtra` artık `speaker_id` (zorunlu),
    `noise_instance`, `stimulus_type` ve `item` taşıyor. `McGurkExtra` ile
    ortak iki alan `_SpeakerExtra` tabanında. `v_trials_flat` üç alanı zaten
    sütun olarak açıyor → **şema sürümü 2'de kaldı**.
  - **Motorda tek satırlık ekleme:** V-only denemesinde `burst_onset_s`
    videonun kendi patlama anından hesaplanıyor (aşağıda gerekçe).
  - **`tools/run_module.py`** iki modülü de koşuyor (`--module avsr`);
    modül tablosu üzerinden çalışıyor, Adım 6–7c yalnızca satır ekleyecek.
    AVSR koşusunun sonunda ölçütler de basılıyor.
  - **Test: 105 yeni test (451 → 556).** CI'da koşanlar: 42 AVSR testi
    (tasarım, V-only'nin çaprazlanmaması, tohum, gürültü dengelemesi,
    skorlama, ölçütler, kelime listesi hata yolları, `open_set`,
    `mode_questions`) + 42 konsol kodlama testi (aşağıda). Donanımda koşanlar
    (`psychopy`, 4): üç sunum modunun gerçekten sunulması, `is_correct`
    yazılması, V-only'de iki RT'nin de kaydı, zaman aşımı. `ScriptedKeyboard`
    iki donanım test dosyasının paylaştığı `tests/scripted_keyboard.py`'ye
    taşındı.

- **Tam uzunlukta dayanıklılık koşusu (2026-07-27):** 135 deneme, tam ekran,
  75 Hz, yanıtlar simüle (koşullara göre olasılıklı, 700 ms). Adım 4'teki gibi
  betik ve veritabanı scratchpad'de tutuldu.

  | Ölçüm | Sonuç |
  |---|---|
  | Süre | **11.18 dk** (4.97 s/deneme) — config'in tahmini 15.8 dk |
  | Bloklar | 60 / 60 / 15, üçü de `completed`, her biri ayrı commit |
  | Düşen kare | **0** (en kötü kare aralığı 17.85 ms; kare 13.33 ms, sınır 20.00 ms) |
  | `TimeFailed` / `XRuns` | **0** |
  | `actual_soa_ms` | yalnızca 60 AV denemesinde; ort **+0.028 ms**, SD 0.118 |
  | A-only | 60/60 `video_onset` boş, `audio_onset` dolu |
  | V-only | 15/15 `audio_onset` boş, `video_onset` dolu, **`rt_from_burst` dolu** |
  | Gürültü varyantı | 60 gürültülü denemede 23/19/18 |

  Ölçütler simülasyona giren yapıyı geri veriyor: A %75.0, V %33.3, AV %93.3;
  görsel fayda %+18.3; koşul bazında **gürültüde (+26.7 / +33.3) sessizden
  (+6.7 / +6.7) belirgin şekilde büyük** — yani indeks, SSD hipotezinin
  aradığı etkileşimi hücre düzeyinde gösterebiliyor. Süre tahmini
  (`estimated_trial_duration_s: 7.0`) rahat bir üst sınır; gerçek RT ile
  ~12–13 dk beklenir.

- **Koşunun bulduğu hata — Windows konsolu Unicode:** özet çıktısındaki
  "Görsel fayda (AV − A)" satırı **U+2212 eksi işareti** içeriyordu ve Python,
  cp1254 konsolunda kodlanamayan bir karakteri sessizce bozmak yerine
  `UnicodeEncodeError` fırlatıyor. Yani 11 dakikalık koşunun **sonunda**, veri
  toplandıktan sonra rapor yerine traceback basıyordu. Aynı karakter sınıfı
  kodda **yedi yerde daha** vardı ve çoğu **hata mesajlarındaydı**
  (`modules.gin` doğrulaması, `design.py`, `base.py`, `prepare.py`,
  `verify_backup.py`, `timing_selftest.py`) — orada etkisi daha kötü olurdu:
  hata mesajının yerine başka bir hata geçer. Hepsi ASCII'ye çevrildi
  (`≠` → `!=`, `→` → `->`, `−` → `-`) ve
  **`tests/mcgurk/test_console_encoding.py`** her koşuda `mcgurk/` ile
  `tools/` altındaki tüm string sabitlerini tarıyor. Docstring ve yorumlar
  muaf: onlar hiçbir zaman bir akışa kodlanmıyor.

- **Alınan kararlar:**
  - **V-only gürültü ve kulakla çaprazlanmıyor** (§C Adım 5) ve o denemelerde
    `snr_db`, `noise_condition`, `ear` **NULL** yazılıyor — "sessiz/iki kulak"
    değil. NULL "uygulanamaz" demek; sessiz bir koşulla aynı sütunda toplanırsa
    analizde ayırt edilemez.
  - **Doğru cevap var, kategori yok.** `responses.is_correct` yazılıyor,
    `category` NULL kalıyor. Aynı bilgiyi iki sütuna yazmak, ikisinin
    çelişebilmesi demek. Tetikleyici yalnızca `mcgurk`/`dichotic`'i engelliyor.
  - **Zaman aşımı yanlış sayılıyor** (kullanıcı onayı, 2026-07-27), dışlanmıyor.
    Dışlamak, tam da zamanında yanıtlayamayan katılımcının doğruluğunu
    yükseltirdi — ve gürültülü A-only, grup farkının beklendiği hücre.
    `Accuracy.n_missing` zaman aşımı sayısını yanında taşıyor, böylece çoğu
    zaman aşımı olan bir hücre "düşük" değil "yanıtsız" olarak görünüyor.
  - **Yanıt seti üç seçenek, serbest metin yok** (kullanıcı onayı). McGurk'te
    kategori vardı, burada skor var: bir kaçış seçeneği, görsel fayda
    indeksinin hesaplandığı doğruluk figürünün dışına deneme çıkarırdı.
  - **V-only'nin RT referansı görsel patlama.** Ses yok, akustik patlama yok;
    referanssız bırakılsaydı V-only RT'leri temel oluşturduğu AV denemeleriyle
    karşılaştırılamazdı. `TimingRecord.burst_onset_s` ses yoksa
    `video_onset + video_burst_s`'e düşüyor — manifest'in ölçtüğü, orijinal
    çekimdeki artikülasyon anı.
  - **Soru metni moda göre değişiyor** (`mode_questions`). V-only'de "Ne
    duydunuz?" yanlış bir soru; metin config'te, çünkü ifade değişikliği bir
    protokol değişikliğidir ve `sessions.config_snapshot`'ta görünmeli.
  - **Kelime listesi ayrı dosyada, loader okuyor.** Şemaya inline yazmak
    tasarımla korpusu karıştırırdı; `StimulusSet._items` private, yani
    kelimeler YAML'a ikinci bir yoldan yazılamıyor ve iki kaynak çelişemiyor.
    Etkin bir kelime seti üç ayrı noktada açık hata veriyor: liste boş/okunamaz
    (yükleme), kelime `stimulus_prep.tokens` içinde değil (yükleme), kelime
    manifest'te yok (tasarım üretimi).
  - **`stimulus_type` VIEW'a eklenmedi.** Sütun eklemek şema sürümü 2 → 3
    demek ve mevcut `data/mcgurk.sqlite` açılamaz hâle gelirdi. Bilgi
    `design_extra` JSON'unda duruyor; VIEW'a eklemenin doğru zamanı kelime
    setinin gelmesi (o zaten manifest ve hazırlama boru hattı değişikliği
    gerektiriyor).
  - **Modül başına RNG akışı** McGurk'ünkiyle aynı gerekçe. McGurk'ün
    çekim sırası **bilinçli olarak değiştirilmedi**: gürültü varyantı
    dağıtımı AVSR'de yeniden yazıldı (hücre şekli farklı), ortaklaştırılsaydı
    aynı tohum McGurk'te başka bir sıra üretebilirdi.

- **Manuel test turu (2026-07-27):**
  - Kullanıcı `--limit 12 --seed 3` ile koştu: 12/12 sunuldu, **0 düşen kare,
    0 ses zamanlaması bozulması**, üç mod da beklendiği gibi (A'da video yok,
    V'de ses yok ve soru "Ne söyledi?", AV'de ikisi birlikte), kulak
    lateralizasyonu ve zaman aşımı mesajı doğru. Doğruluk 12/12.
  - **AV'de dudak–ses eşzamanlılığı maddesi atlandı** — kablolu kulaklık yok,
    test Bluetooth (WH-1000XM4) ile koşuldu. O kulaklık 100–300 ms **değişken**
    gecikme ekliyor, yani yargı kodun değil kulaklığın davranışı olurdu. Aynı
    madde Adım 3'ten beri açık (`TEST_ADIM_3.md` Test 2, madde 7); ikisi
    kablolu kulaklık geldiğinde birlikte kapatılacak (bekleyen aksiyonlara
    işlendi). Adım 5'i bloklamıyor: yazılım tarafındaki A/V farkı ölçüldü
    (`actual_soa_ms` ort +0.028 ms, SD 0.118) ve mutlak gecikme yalnızca
    fotodiyot ölçümüyle doğrulanabilir.
  - **Tavan etkisi gözlendi:** üç modda da %100 doğruluk, dolayısıyla görsel
    fayda %+0.0. n=12'de bu bir ölçüm değil, ama **kapalı 3 heceli sette
    +5 dB SNR'ın normal işiten bir yetişkin için kolay olduğunu** gösteriyor.
    Kontrol grubu tavanda kalırsa görsel fayda indeksi grup farkını gösteremez.
    §F.1'e (deneme sayıları/tasarım) not düşüldü — SNR'ı düşürmek bir danışman
    kararı, kod tarafında yalnızca `noise_conditions` değişikliği.

- **Ortama ffmpeg kurma denemesi geri alındı (2026-07-27):** kullanıcı isteği
  üzerine `conda install -c conda-forge ffmpeg` denendi. Kurulum "başarılı"
  döndü ama **ffmpeg çalışmadı**: `avcodec-62.dll` WinError 127 veriyor —
  karışık kanal ABI uyuşmazlığı (çözücü `libglib`'i `pkgs/main`'den,
  gerisini conda-forge'dan aldı). Daha önemlisi kurulum env'e **sdl2 ve sdl3**
  bıraktı; ortam aktive edildiğinde `ffpyplayer` bozuk `SDL2.dll`'i alıyor ve
  kullanıcının ilk manuel test denemesi "failed to load sdl3" hatası verdi.
  `conda install --revision 0` ile tam geri alındı, ortam doğrulandı
  (556 test + 54 donanım testi yeşil). **Sistem ffmpeg'i gerekmiyor:**
  `find_ffmpeg()` PATH'ten sonra `imageio-ffmpeg`'e düşüyor ve
  `mcgurk/stimuli/ffmpeg.py` `ffprobe`'u kasıtlı olarak hiç kullanmıyor —
  ihtiyaç duyulan her şey ffmpeg'in kendi stderr'inden okunuyor. Adım 0'ın
  "Adım 2'nin araçları kurulu ffmpeg gerektirecek" notu geçersiz.
  Gerçekten gerekirse doğru yol `--override-channels -c conda-forge`'dur, ama
  o da python/openssl'i conda-forge'a taşıyıp pip ile kurulmuş PsychoPy
  yığınını riske atar.

- **Bilinen sınırlar:**
  - Kelime seti içerik olarak boş (§F.2). Şema, okuyucu, şablon ve hata
    yolları hazır; kayıt yapılınca kod değişmeyecek.
  - `response_mode: open_set` gerçeklenmedi — `OpenSetNotImplemented`.
    Puanlama kuralları (transkripsiyon, kısmi kredi, Türkçe klavye) karar
    bekliyor.
  - Modül tek başına koşuyor; yönerge, alıştırma, mola ve katılımcı girişi
    Adım 8'de.
  - Ölçüt fonksiyonları (`accuracy_by_*`, `visual_benefit*`,
    `lipreading_accuracy`) `modules/avsr.py` içinde ve `v_trials_flat`
    satırlarını okuyor. Adım 9 bunları `analysis/`'ten çağıracak; taşımak
    gerekmiyor, sarmalamak yetiyor.
  - Konsol kodlama testi yalnızca **string sabitlerini** tarıyor. Çalışma
    anında birleştirilen bir metin (örneğin bir dosya adı) hâlâ konsolda
    patlatabilir; kalıcı çözüm çıkış akışını `errors="replace"` ile açmak
    olurdu ve bu Adım 8'in giriş noktası işiyle birlikte yapılmalı.

- **Sonraki adıma not:**
  - **Adım 6 (TBW) `block.py`'yi olduğu gibi kullanamaz**: yanıt iki
    seçenekli ("Aynı anda"/"Farklı zamanda") ve `nominal_soa_ms` her denemede
    dolu. İlk ikisi `TrialPolicy` ile karşılanıyor; SOA için `TrialSpec`
    zaten alan taşıyor ve motor negatif SOA'da payı kendisi hesaplıyor
    (Adım 3). TBW config'ine `ResponseUIConfig` alanları eklenmeli
    (`response_labels` bugün ayrı bir alan).
  - **Adım 7 (oddball) ve 7c (GIN) döngüyü paylaşamaz**: uyaran içinde 0..n
    yanıt topluyorlar. `run_blocks`'un blok/commit yapısı yine de örnek.
  - Adım 8 modül sırasına AVSR'yi eklerken `plan_trials(..., speaker_id=...)`
    ile konuşmacıyı katılımcı başına verebilir (§F.4).
  - Adım 9 `v_trials_flat`'tan okurken AVSR için `avsr_item` sütununu ve
    `is_correct`'i bulacak; `stimulus_type` yalnızca JSON'da.
  - **Adım 8 giriş noktalarını yazarken `sys.stdout`/`sys.stderr`'i
    `errors="replace"` ile açsın** — konsol kodlama testi string sabitlerini
    koruyor ama çalışma anında birleşen metinleri koruyamaz (bkz. yukarıdaki
    U+2212 bulgusu).

### Adım 6 — Modül 3: TBW
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-27. Otomatik testler yeşil (556 → **614 test**;
  CI'da koşan 542, donanımda 57, ffmpeg gerektirdiği için atlanan 15; ruff +
  mypy temiz). `TEST_ADIM_6.md` Test 1 kullanıcı tarafından yürütüldü ve geçti.
- **Commit:**
  - `3974aee` — mcgurk/modules/tbw.py, block.py'ye TBW politikası,
    TBWConfig'in ResponseUIConfig'e taşınması, şema sürümü 3 (§A.10
    tetikleyicisi tbw'yi de reddediyor), paket sınırı testinin izolasyonu

- **Ne yapıldı:**
  - **`mcgurk/modules/tbw.py`** — sabit uyaranlar yöntemi (`soa_values_ms ×
    reps_per_soa × ears`), tohumlu sıralama, manifest'ten tek uyaran çözümü,
    yargı eşlemesi (`SAME`/`DIFFERENT`), **binom maksimum olabilirlikle Gauss
    psikometrik uydurma**, bootstrap güven aralıkları ve operatör raporu.
    **PsychoPy yok** (paket sınırı testine eklendi). Mevcut config ile
    **130 deneme**: 13 SOA × 10 tekrar × 1 kulak.
  - **`block.py`'ye `tbw_policy` + `run_tbw`** — döngü yine kopyalanmadı; TBW
    iki seçenekli bir ızgara ve kategorili/skorsuz bir değerlendirme olarak
    `TrialPolicy` üzerinden geldi. McGurk ve AVSR'nin donanım testleri
    değişmeden geçiyor.
  - **`TBWConfig` artık `ResponseUIConfig`'ten türüyor** (Adım 5'in notu):
    `response_set`, `response_keys`, `fixation_duration_ms`,
    `post_response_ms`, `prompts`, `randomization` ortak tabandan geliyor.
    TBW'ye özgü doğrulamalar: tam iki seçenek, `response_labels` değerleri
    `response_set` ile birebir aynı, `free_text_response` null, `ears`
    tekrarsız, `bootstrap_samples` ya 0 ya en az 200.
  - **`prompts.other` artık koşullu zorunlu**: `free_text_response` doluysa
    gerekli, değilse yazılamaz durumda değil ama TBW'de hiç yazılmıyor. Hiç
    açılmayacak bir ekranın metnini config'e koymak, katılımcının okumayacağı
    bir protokol satırı yazmaktır.
  - **`db/design.py` → `TBWExtra`**: `tbw` artık `NoExtra` değil, `speaker_id`
    (zorunlu) taşıyor — McGurk ve AVSR ile aynı gerekçe (§F.4). `v_trials_flat`
    `speaker_id`'yi zaten sütun olarak açıyor.
  - **§A.10 tetikleyicisi `tbw`'yi de reddediyor → şema sürümü 2 → 3.**
    Mevcut geliştirme veritabanı `backups/mcgurk_pre_adim6_schema2_*.sqlite`
    olarak `VACUUM INTO` ile yedeklendi (14 oturum, 43 deneme — hepsi DEV01
    geliştirme koşusu), sonra `data/mcgurk.sqlite` silindi; ilk koşuda yeni
    şemayla oluşuyor.
  - **`tools/run_module.py --module tbw`**: kuru koşuda SOA aralığı, gereken
    sunum payı ve pencere tanımı; canlı koşunun sonunda psikometrik fonksiyon
    ve uydurma raporu.
  - **`base.row_value`** ortaklaştırıldı (AVSR'nin `_field`'ı oradan geliyor):
    üçüncü modül de `v_trials_flat` satırı okuyor, "bir sütun nasıl okunur"un
    üç kopyası üç farklı KeyError davranışı demekti.
  - **Test: 58 yeni test (556 → 614; CI'da koşan 542 + 15 atlanan, donanımda
    57).** CI'da koşanlar: 25 tasarım/yargı/config testi + 25 uydurma testi (bilinen
    parametreden geri kestirim, tanım farkı, bootstrap kapsama ve
    yeniden üretilebilirlik, dört hata yolu, zaman aşımının eğriye girmemesi)
    + veritabanı tetikleyicisi. Donanımda koşanlar (`psychopy`, 3): −300/0/+300
    ms gerçek pencerede sunuluyor, negatif SOA'da ses videodan **önce**
    başlıyor, `actual_soa_ms` nominale kare süresi içinde oturuyor, `category`
    yazılıyor ve `is_correct` NULL kalıyor, zaman aşımı eğriye nokta koymuyor.

- **Tam uzunlukta dayanıklılık koşusu (2026-07-27):** 130 deneme, tam ekran,
  74.77 Hz, yanıtlar **bilinen bir gözlemciden** simüle edildi (PSS +40 ms,
  sigma 90 ms, tepe 0.95) — böylece koşu yalnızca dayanıklılığı değil,
  tasarım → sunum → veritabanı → uydurma zincirinin tamamını sınadı. Betik ve
  veritabanı scratchpad'de tutuldu.

  | Ölçüm | Sonuç |
  |---|---|
  | Süre | **11.13 dk** (5.14 s/deneme) — config'in tahmini 10.8 dk |
  | Bloklar | 60 / 60 / 10, üçü de `completed`, her biri ayrı commit |
  | Düşen kare | **1 deneme** (en uzun aralık 20.23 ms; kare 13.37 ms, sınır 20.06 ms) |
  | `TimeFailed` / `XRuns` | **0** |
  | `actual_soa_ms − nominal_soa_ms` | ort **+0.389 ms**, SD 0.732, aralık [−1.24, +2.39] |
  | Geri kestirim | PSS **+44.8** ms (gerçek +40.0), sigma **96.8** ms (gerçek 90.0) |
  | Bootstrap | 2000 örnekten 1'i uydurulamadı; GA'lar [28.0, 62.8] ve [83.3, 109.9] — ikisi de gerçek değeri kapsıyor |

  Süre tahmini tutuyor: 700 ms'lik bir yanıtla deneme 5.14 s sürüyor, gerçek RT
  ile ~5.5–6 s, yani modül için **~12–13 dk** planlanabilir. Kestirim sapması
  (PSS +4.8 ms, sigma +6.8 ms) 130 denemede beklenen örnekleme gürültüsü
  mertebesinde; güven aralıkları gerçek değerleri kapsıyor.

- **Alınan kararlar:**
  - **Uydurma modülün içinde, `analysis/` içinde değil** — AVSR'nin ölçütleriyle
    aynı yer ve aynı gerekçe: Adım 9 sarmalayacak, taşımayacak. scipy CI'da
    kurulu olduğu için PSS/sigma kestirimi **CI'da** test ediliyor.
  - **Binom maksimum olabilirlik**, oranlar üzerinde en küçük kareler değil.
    Zaman aşımları düşünce noktalar farklı deneme sayısı taşıyor ve kare hata,
    10/10'luk bir oranı olduğundan daha bilgili sayıyor.
  - **Zaman aşımı eksik gözlem** (AVSR'nin tam tersi, ve tam tersi gerekçeyle):
    orada doğru cevap vardı, burada yok. Bir zaman aşımını "farklı" saymak
    eğriyi daraltır, "aynı" saymak genişletir; hangisini seçerseniz seçin,
    katılımcının vermediği bir yanıtı siz vermiş olursunuz.
    `SOAPoint.n_missing` sayıyı yanında taşıyor.
  - **`is_correct` NULL, `category` `SAME`/`DIFFERENT`** ve **tetikleyici bunu
    veritabanı düzeyinde zorluyor** (şema 3). ±300 ms'te akışlar gerçekten
    eşzamanlı değil — ama ölçülen şey **algılanıp algılanmadığı**; "farklı"yı
    doğru saymak katılımcının pencere genişliğini hata oranına çevirirdi.
    Bedeli mevcut geliştirme veritabanının yeniden oluşturulması oldu.
  - **Test edilen ızgaradan geniş pencere rapor edilmiyor.** İlk yazdığım
    kontrol sigmanın optimizasyon sınırına dayanmasına bakıyordu ve düz bir
    eğride (her SOA'da p = 0.5) **sigma 2770 ms** dönüyordu: sınıra dayanmıyor,
    ama 600 ms'lik bir ızgarada ölçülmüş de değil. Ölçüt sigma ≥ aralık/2
    yapıldı — o noktada eğri en uçtaki SOA'da yalnızca %12 düşüyor, yani veri
    daha geniş her genişlikle uyumlu ve optimizasyon yine de birini seçiyor.
    "TBW 6500 ms" bir tabloda ölçüm gibi okunur.
  - **Bootstrap tohumu oturum tohumundan türetiliyor** (§A.11): aynı veri her
    zaman aynı güven aralığını verir, yoksa analiz iki koşuda aynı katılımcı
    hakkında iki farklı şey söyler. Uydurulamayan örnekler sayılıyor; yarıdan
    fazlası düşerse **hiç aralık verilmiyor**, çünkü uyanlardan hesaplanan
    aralık tam da uyan şekle yanlıdır.
  - **SOA planlama anında denetleniyor** (`check_soa_is_schedulable`): motorun
    pay hesabı beklenen yenileme hızıyla önceden koşuluyor. −300 ms 75 Hz'de
    320 ms pay istiyor (üst sınır 1 s). Sunulamayacak bir ızgarayı oturumun
    ortasında öğrenmek geç.
  - **`response_set` ekranı, `response_labels` anlamı veriyor** ve şema ikisinin
    aynı iki metni adlandırdığını doğruluyor. Uyuşmazlık eğriyi ters çevirirdi
    — ve ters eğri de uyar, yalnızca pencereyi tümleyeni olarak raporlar.
  - **Serbest metin yok.** İki alternatifli bir yargının üçüncü yanıtı yoktur;
    bir kaçış seçeneği psikometrik fonksiyondan deneme düşürürdü.

- **Yol boyunca çıkan bir test altyapısı sorunu (Adım 4'ün notunun kökü):**
  `test_package_boundaries.py` PsychoPy'siz import denemesini
  `importlib.reload` ile yapıyordu. `reload` modülü **kendi namespace'inde**
  yeniden çalıştırır, yani tanımladığı her sınıf yeni bir nesne olur; oturumun
  geri kalanı eskisini tutmaya devam eder. Sonuç: alfabetik olarak bu dosyadan
  **sonra** koşan her test dosyasında `pytest.raises(FitError)` o modülün kendi
  `FitError`'ını yakalamıyor. Adım 4 bunu `DisplayConfig` atamasında görmüş ve
  "yeniden yüklenmiş şemadan sonra sınıf kimliğine güvenilmez" diye not
  düşmüştü; Adım 6'da aynı tuzak yedi testi düşürdü. Kalıcı çözüm: modüller
  `sys.modules`'tan çıkarılıp **taze nesnelere** import ediliyor, test bitince
  taze kopyalar atılıp orijinaller (paket niteliği dahil) geri konuyor. Artık
  hiçbir sınıf kimliği değişmiyor.

- **Bilinen sınırlar:**
  - **PSS mutlak olarak henüz anlamlı değil.** `timing.system_av_offset_ms`
    `null` (fotodiyot ölçümü tüm kod bittikten sonra), yani kestirilen PSS
    makinenin A/V gecikmesini içeriyor. Grup **karşılaştırması** bundan
    etkilenmez (herkese aynı sabit eklenir), ama "PSS +45 ms" tek başına
    rapor edilemez. Ölçüm yapıldığında yeniden hesap gerekmiyor:
    `actual_soa_ms` D'yi zaten içeriyor (Adım 3 kararı).
  - Dayanıklılık koşusunda **bir denemede kare düştü** (20.23 ms, sınır
    20.06 ms). Adım 4–5'te sıfırdı; fark, TBW'nin negatif SOA'da 24 kare
    boyunca sabitleme haçını çizerek beklemesi olabilir. Tek deneme ve sınırın
    0.2 ms üstünde; QC raporu (Adım 9) bu denemeyi işaretleyecek.
  - Kulak **çaprazlanmıyor** (`ears: [both]`). Config her üç değeri de
    destekliyor; SSD'de TBW'nin kulağa göre değişip değişmediği bir tasarım
    kararı (§F.1) ve açık.
  - Uydurma **tek Gauss**. Literatürde iki ayrı sigmoid (sol/sağ kenar ayrı)
    uyduran çalışmalar da var ve asimetrik bir pencere onlarla tam
    karşılaştırılamaz. `steps.md` §C Adım 6 Gauss diyor; asimetri gerekirse
    `tbw_definition` gibi bir config alanı ve ikinci bir uydurma fonksiyonu
    yeterli, veri yapısı değişmiyor.
  - Modül tek başına koşuyor; yönerge, alıştırma, mola ve katılımcı girişi
    Adım 8'de.

- **Sonraki adıma not:**
  - **Adım 7 (oddball) ve 7c (GIN) `block.py`'yi paylaşamaz**: uyaran içinde
    0..n yanıt topluyorlar. `run_blocks`'un blok/commit yapısı yine örnek.
    **Adım 7b (dikotik) paylaşabilir** — tek zorunlu seçim, dört seçenek,
    doğru cevap yok (tetikleyici zaten reddediyor); `TrialPolicy` yazmak
    yetiyor. Dikotik config'ine `ResponseUIConfig` alanları eklenmeli
    (bugün yalnızca `response_set` ve `response_timeout_s` var).
  - Adım 9 `v_trials_flat`'tan okurken TBW için `nominal_soa_ms`,
    `actual_soa_ms` ve `category` sütunlarını bulacak;
    `tbw.psychometric_points()` + `tbw.fit_from_rows()` doğrudan çağrılabilir,
    taşımaya gerek yok. **Gerçekleşen SOA analizde kullanılabilir:** nominal
    yerine `actual_soa_ms` ile uydurmak isteniyorsa noktaları oradan gruplamak
    yeterli (sapma ölçüldü: SD 0.73 ms, yani pratikte fark etmeyecek).
  - Fotodiyot ölçümü yapıldığında (`docs/01`) TBW'nin PSS'i mutlak anlam
    kazanır; kod değişmiyor, yalnızca `timing.system_av_offset_ms` doluyor.

### Adım 7 — Modül 4: Oddball
- **Durum:** TAMAMLANDI
- **Tamamlanma:** Kod 2026-07-27, manuel test 2026-07-28. Otomatik testler
  yeşil (614 → **688 test**; CI'da koşan 610, donanımda 61, ffmpeg gerektirdiği
  için atlanan 17; ruff + mypy temiz). `TEST_ADIM_7.md`'deki tek manuel test
  (kulakla dinleme + gerçek klavye) kullanıcı tarafından yürütüldü ve geçti.
- **Commit:**
  - `d6f5340` — mcgurk/modules/oddball.py + stream.py, çevrimdışı ton üretimi,
    config'e response_window_ms/lead_in_s/tones.level_dbfs, OddballExtra.isi_ms

- **Ne yapıldı:**
  - **`mcgurk/modules/oddball.py`** — hedef yerleşimi, ISI çekimi, onset
    takvimi, tuş atfetme, sinyal tespiti ölçütleri (isabet/kaçırma/yanlış
    alarm/doğru ret, d′, kriter, isabet RT'si) ve operatör raporu. **PsychoPy
    yok** (paket sınırı testine eklendi).
  - **`mcgurk/modules/stream.py`** — kesintisiz akış koşucusu. `block.py`
    kopyalanmadı: oddball'ın yanıt ekranı yok, tonları kendi saatine göre akıyor
    ve deneme başına 0..n yanıt topluyor. Adım 7c'nin GIN'i buraya katılabilir.
  - **`stimuli/tones/tone_<hz>Hz.wav`** — tonlar çevrimdışı üretiliyor
    (`dsp.tone`, `prepare._write_tones`, `manifest.ToneEntry`,
    `verify._check_tones`). Frekanslar `modules.oddball`'dan **türetiliyor**
    (`config.required_tones()`), ikinci kez yazılmıyor.
  - **Config'e üç alan:** `modules.oddball.response_window_ms` ([100, 800] ms),
    `lead_in_s` (1.0 s) ve `stimulus_prep.tones.level_dbfs` (−23 dBFS).
  - **`db/design.py` → `OddballExtra`** artık nominal `isi_ms` de taşıyor.
    Şema sürümü **değişmedi** (3): `v_trials_flat` `oddball_tone_type`'ı zaten
    açıyordu ve `isi_ms` VIEW'e eklenmedi — gerçekleşen aralık `audio_onset_s`
    farklarından zaten çıkıyor.
  - **`tools/run_module.py --module oddball`**: kuru koşuda hedef oranı,
    hedefler arası standart dağılımı, ISI aralığı ve akış süresi; canlı koşunun
    sonunda sinyal tespiti tablosu.
  - **Test: 74 yeni test.** CI'da koşanlar: 52 tasarım/atfetme/ölçüt testi
    (hedef sayısı, kısıt her tohumda, yerleşimin düzgün dağılımlı olduğu,
    pencere kenarları, blok sınırı, elle hesaplanmış d′ ve kriter, sınır
    durumları) + 13 ton üretimi testi (frekans, süre, seviye, rampa, spektral
    saçılma) + config kapıları. Donanımda koşanlar (`psychopy`, 4): tonlar
    tasarlanan aralıklarla sunuluyor, basım doğru tona düşüyor, bloğu kapanmış
    bir tona gelen geç basım da kaydediliyor, pencere dışı basım puanlanmıyor.

- **Tam uzunlukta dayanıklılık koşusu (2026-07-27):** 300 ton, tam ekran,
  75.01 Hz, yanıtlar **bilinen bir gözlemciden** simüle edildi (hedeflerin
  %90'ına 350 ± 60 ms'de basım, standartların %2'sinde yanlış alarm).

  | Ölçüm | Sonuç |
  |---|---|
  | Süre | **5.06 dk** (1.013 s/ton) — config'in tahmini 5.2 dk |
  | Bloklar | 5 × 60, hepsi `completed`, her biri ayrı commit |
  | Düşen kare | **0** (en uzun kare aralığı 17.27 ms) |
  | `TimeFailed` / `XRuns` | **0** — 300 tonun hiçbirinde kaçırılan planlama yok |
  | Geri kestirim | isabet %92.6 (gerçek %90), yanlış alarm %2.4 (gerçek %2) |
  | d′ / kriter | **3.33** / +0.27 |
  | Isabet RT | 344 ms (SD 71), n=50 — simülasyonun 350 ± 60'ı |

  **Aralık sapması ölçüm değildir:** `trials.audio_onset_s` planlanan onset'i
  taşıyor (Adım 3 kararı — PTB bu makinede kendisine söyleneni aynen geri
  bildiriyor), dolayısıyla nominal ile gerçekleşen aralık farkının 0.0000 ms
  çıkması aritmetiğin doğruluğunu söyler, sesin o anda çıktığını değil. Onu
  söyleyen şey `TimeFailed`/`XRuns` = 0 ve kademe 2 loopback ölçümü.

- **Alınan kararlar:**
  - **Tonlar çevrimdışı üretiliyor**, çalışma anında değil. Bir sinüs ucuz, ama
    sunulan her şey hazırlanmış setten gelir, manifest'te kaydı olur ve
    `verify_stimuli.py` onu denetler — 50 ms'lik bir tonu tona çeviren şey
    (rampa) tam olarak diskten ölçülebilmesi gereken şey. Manifest sürümü
    **bump edilmedi**: alan eklemek geriye uyumlu, eksik ton açık hatayla
    bildiriliyor (AVSR kelime setiyle aynı yol).
  - **Yanıt penceresi config'te ve veri toplanmadan önce sabit.** Sonradan
    seçilmesi, isabet ve yanlış alarm oranlarının sonuçlara bakarak
    ayarlanabilmesi demek. Üst sınır en kısa ISI'dan kısa olmak zorunda —
    aksi hâlde bir basım iki tona birden ait olurdu ve oran, kodun hangisini
    seçtiğine bağlı kalırdı. Değer (100–800 ms) **danışman kararına açık**.
  - **Pencere dışı basım atılmıyor.** Takip ettiği tona `OUTSIDE_WINDOW`
    kategorisi ve `is_correct = NULL` ile yazılıyor: rastgele tuşa basan bir
    katılımcı QC'de görünmeli, ama basımları isabet ya da yanlış alarm sayımına
    girmemeli. İlk tondan önceki basımlar hiçbir denemeye ait olmadığı için
    yalnızca sayılıp loglanıyor.
  - **Kaçırma ve doğru ret satır üretmiyor** — ikisi de basımın *yokluğu*.
    Zaman aşımı kuralıyla aynı: `v_trials_flat` LEFT JOIN olduğu için deneme
    yine görünüyor ve ölçütler oradan türüyor.
  - **Basımlar atfediliyor, toplanmıyor.** Zaman damgasıyla tamponlanıp sonradan
    tonlara dağıtılıyor. Bunun bir sonucu: bloğu kapanmış bir tona gelen geç
    basım kayıp değil — kendi tonuna yazılıyor, yalnızca bir sonraki bloğun
    commit'iyle diske iniyor. Bir yanıt satırının hangi commit'le indiği ne
    söylediğini değiştirmiyor; kaybolması ise isabet oranını blok sınırlarının
    nereye düştüğüne bağlardı.
  - **Klavye saati bir kez sıfırlanıyor** (akış başında); RT = `press.rt +
    (sıfırlama anı − ton onset'i)`. Ton başına sıfırlama, sıfırlamanın tam
    onset anında olmasını gerektirirdi ve bunu hiçbir flip döngüsü milisaniye
    hassasiyetinde vaat edemez. `tDown`'dan yine hiçbir şey hesaplanmıyor
    (Adım 4 kuralı).
  - **Her hedefin önünde standart koşusu var — ilkinin de.** Hiçbir standart
    kurulmadan sunulan bir "sapma" sapma değildir. Config doğrulaması buna göre
    değişti (`hedef × (1 + min_standards)`); 300 denemede 162, bol bol sığıyor.
  - **Yerleşim geçerli dizilerden düzgün rastgele** (yıldızlar-ve-çubuklar),
    açgözlü değil. Açgözlü yerleştirme boş yerin biriktiği yere — akışın
    sonuna — yığar; dikkat görevinde hedef oranının sabit kalması gereken yer
    tam olarak ikinci yarıdır. Test bunu hem tek tek konumların dağılımıyla hem
    de yarı-yarıya dengeyle kontrol ediyor.
  - **`ears` tam bir öğe içermeli.** `n_trials` toplam deneme sayısı, yani
    kulak çaprazlanmıyor; ikinci bir değerin tanımlı anlamı olmazdı. Diotik
    (`both`) sunum seçildi: bu dikkat *kontrol* görevi, tek tarafa sunmak SSD
    örnekleminin yarısında sağır kulağın dikkatini ölçmek olurdu.
  - **d′ ve kriter log-lineer düzeltmeli** (Hautus 1995), koşulsuz. Koşullu
    düzeltme (yalnızca oran 0 ya da 1 iken) kestiriciyi tam da kolay bir görevin
    çoğu katılımcıyı bıraktığı yerde süreksiz yapar. Bir yan etkisi belgelendi:
    54 hedefe karşı 246 standartla, **her** tona basan biri sıfır yerine küçük
    negatif bir d′ alıyor; onu tanımlayan şey kriter (−2.6).
  - **Akış flip ızgarasına bağlanmadı.** Video yok, dolayısıyla `AVPresenter`
    kullanılmıyor; onset'ler tek bir başlangıçtan kümülatif hesaplanıp mutlak
    ptb zamanı olarak PTB'ye veriliyor. Her tonu bir öncekinin *gerçekleşen*
    anına göre planlamak, planlayıcının hatasını beş dakika boyunca biriktirirdi.
  - **Planlama anı kaçırılırsa deneme değil akış hatalıdır:** `play(when=geçmiş)`
    PTB'de anında başlar ve tasarlanan aralık hiç var olmamış olur. Bu durumda
    koşu **hata verip duruyor** (`StreamError`); yalnızca pay daralmışsa uyarı
    basılıp sayılıyor.

- **Bilinen sınırlar:**
  - **Yanıt penceresi (100–800 ms) danışman onayı bekliyor** — GIN'inkiyle
    (Adım 7c) birlikte kararlaştırılmalı. Veri toplama başlamadan önce
    kesinleşmeli; sonradan değiştirmek isabet/yanlış alarm oranlarını yeniden
    tanımlar.
  - **Kayıtlı onset planlanan onsettir**, ölçülen değil (yukarıdaki not).
    Motorun geri kalanında da böyle (§ Adım 3, `audio_onset_reported`).
  - **Hedefler arası en uzun boşluk 17 standarda kadar çıkabiliyor** (~17 s
    hedefsiz). Düzgün rastgele yerleşimin doğal kuyruğu; standart oddball
    uygulamasıyla uyumlu, ama isterse config'e bir üst sınır eklenebilir.
  - Modül tek başına koşuyor; yönerge ("tiz tonu duyunca boşluğa basın"),
    alıştırma, mola ve katılımcı girişi Adım 8'de. Şu an ne yapılacağını
    yalnızca `TEST_ADIM_7.md` söylüyor.
  - Dayanıklılık koşusu monitörün HD Audio çıkışında yapıldı (Bluetooth
    kulaklık kapalıydı). Ses yolunun mutlak gecikmesi ölçülmedi — kademe 2/3'ün
    işi.

- **Sonraki adıma not:**
  - **Adım 7c (GIN) `stream.py`'yi paylaşabilir.** Aynı şekil: uyaran içinde
    0..n yanıt, yanıt ekranı yok, tuş basımı zaman damgasıyla atfediliyor. GIN'de
    "onset" bir tonun değil bir boşluğun başlangıcı olacak ve pencere
    `modules.gin.response_window_ms` (henüz yok) olacak. `_flush`/`_hold`/
    `_schedule` üçlüsü olduğu gibi kullanılabilir; segment başına tek bir uzun
    ses ve segment içinde birden çok "onset" listesi gerekiyor.
  - **Adım 7b (dikotik) `block.py`'yi paylaşır**, `stream.py`'yi değil — tek
    zorunlu seçim. Adım 6'nın notu geçerli: dikotik config'ine `ResponseUIConfig`
    alanları eklenmeli.
  - Adım 8 modül sırasına oddball'ı eklerken yönerge ekranını da vermeli;
    `lead_in_s` yönergeden sonra, ilk tondan önceki sabitleme süresidir.
  - Adım 9 `v_trials_flat`'tan okurken oddball için `oddball_tone_type`,
    `is_correct` ve `rt_from_burst_ms` sütunlarını bulacak;
    `oddball.measures_from_rows()` doğrudan çağrılabilir, taşımaya gerek yok.
    QC raporu iki şeye bakmalı: `category = 'OUTSIDE_WINDOW'` basım sayısı
    (rastgele basan katılımcı) ve `criterion` (her tona basan katılımcı — d′
    onları güvenilir biçimde göstermez).

### Adım 7b — Modül 5: Dikotik dinleme
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-29. Otomatik testler yeşil (**721 test**; CI'da koşan
  655, donanımda 66, ffmpeg gerektirdiği için atlanan 18; ruff + mypy temiz).
  `TEST_ADIM_7B.md`'deki üç test kullanıcı tarafından yürütüldü ve geçti.
  **Kanal yönü doğrulandı** (Test 1): dosyanın 0. kanalı sol kulaktan çıkıyor,
  yani `Left-*` adlandırması gerçekte sol kulağa karşılık geliyor. Bu bulgu
  yalnızca bu modülü değil, Modül 1 ve 2'nin lateralizasyonunu da doğruluyor —
  ikisi de aynı kanal eşlemesine dayanıyor.
- **Commit:**
  - `160f663` — mcgurk/modules/dichotic.py, block.py'ye dichotic policy,
    DichoticConfig → ResponseUIConfig, DichoticExtra'ya speaker_id

- **Ne yapıldı:**
  - **`mcgurk/modules/dichotic.py`** — tasarım (çift × tekrar, tohumlanmış
    sıra), hazırlanmış stereo dosyaya çözümleme, yanıtın hangi kulağa ait
    olduğunun türetilmesi, kulak avantajı indeksi ve operatör raporu.
    **PsychoPy yok** (paket sınırı testine eklendi).
  - **`block.py` paylaşıldı, kopyalanmadı:** `dichotic_policy()` +
    `run_dichotic()`. Tek zorunlu seçim, tek yanıt ekranı — oddball'ın akış
    koşucusu değil, McGurk/AVSR/TBW'nin döngüsü. Sarmalayıcı 12 satır.
  - **Config:** `DichoticConfig` artık `ResponseUIConfig`'ten türüyor.
    Eklenenler: `response_keys`, `free_text_response`, `fixation_duration_ms`,
    `post_response_ms`, `prompts`. Yanıt seti ve zaman aşımı zaten vardı ve
    tekrar tanımlanmıyor; `config_path` hata mesajlarının `modules.dichotic`'i
    göstermesini sağlıyor.
  - **`db/design.py` → `DichoticExtra`** artık `_SpeakerExtra`'dan türüyor,
    yani `speaker_id` zorunlu (`noise_instance` her zaman None). **Şema sürümü
    değişmedi (3):** `v_trials_flat` `speaker_id`, `dichotic_left_token` ve
    `dichotic_right_token`'ı zaten sütun olarak açıyordu, `blocks.module` CHECK
    listesinde `dichotic` zaten vardı ve §A.10 tetikleyicisi onu Adım 1'den
    beri reddediyordu.
  - **`tools/run_module.py --module dichotic`**: kuru koşuda çift tablosu ve
    sunum özeti, canlı koşunun sonunda kulak avantajı raporu.
  - **Uyaran tarafında değişiklik yok** — 12 stereo WAV Adım 2'de üretilmişti.
    Ölçümle doğrulandı (aşağıda).
  - **Test: 48 yeni test** (688 → **721**; CI'da koşan 655, donanımda 66,
    ffmpeg gerektirdiği için atlanan 18). CI'da 43 test: deneme sayısı
    `config.trial_counts()` ile birebir, aynı tohum → aynı sıra, sıranın
    `module_order`'dan bağımsız olduğu, her turda her çiftin bir kez geçtiği,
    dosya çözümlemesi, `design_extra` doğrulaması, kategorizasyon (sekiz
    durum), KAİ aritmetiği (elle hesaplanmış), zaman aşımının indekse
    girmemesi, karışım yanıtının paydada olup indekste olmaması, tanımsız
    indeks, config kapıları. Donanımda 5 test: yanıt doğru kulağa atfediliyor,
    iki token da kayda giriyor, karışım yanıtı, zaman aşımı satır üretmiyor,
    stereo dosya yönlendirilmeden aygıta gidiyor.
  - **Canlı duman testi** (3 deneme, tam ekran, 75 Hz, monitör HD Audio
    çıkışı): 3/3 sunuldu, **0 düşen kare**, **0 ses zamanlaması bozulması**,
    zaman aşımları doğru raporlandı, yedek yazıldı.

- **Uyaran ölçümü (2026-07-29, `stimuli/dichotic/speaker_1/`):**
  - Aynı hece farklı dosyalarda **birebir aynı**: `Left-ba_Right-da` ile
    `Left-ba_Right-ga`'nın sol kanalları örnek örnek özdeş (altı hece × kanal
    kombinasyonunun tamamında).
  - Simetrik çiftler **tam kanal takası**: `Left-ba_Right-da`'nın sol kanalı
    `Left-da_Right-ba`'nın sağ kanalıyla birebir aynı. Kulak avantajı ölçümü
    içerik farkından değil yalnızca taraftan geliyor.
  - Kanallar arası korelasyon **|r| < 0.06**; iki kulak arasındaki seviye farkı
    **≤ 0.2 dB**.
  - Bunların söyleyemediği tek şey: dosyanın 0. kanalı gerçekten sol
    kulaktan mı çıkıyor. `TEST_ADIM_7B.md` Test 1 tam olarak onu ölçüyor
    (ilk iki deneme bilerek birbirinin aynası: sol=ba, sonra sol=da).

- **Alınan kararlar:**
  - **`trials.ear = 'both'`, NULL değil.** Sütun *hangi kulaklara ses gitti*
    sorusunu yanıtlar — ikisine de gitti. *Ne* gittiği `left_token`/
    `right_token`'da. NULL "uygulanamaz" demek olurdu (AVSR'nin V-only'si gibi)
    ve bu burada yanlış olur. **`trials.audio_token` ise NULL**: iki eşzamanlı
    token var, birini sütuna yazmak diğerini görünmez kılardı.
  - **Doğru cevap yok (§A.10).** `category` ∈ `LEFT`/`RIGHT`/`OTHER`,
    `is_correct` NULL. Sağa sunulanı bildirmek "doğru" değil, bir algı
    kategorisidir; veritabanı Adım 1'den beri aksini reddediyor.
  - **Zaman aşımı kayıp gözlemdir, indekse girmez.** TBW kuralıyla aynı ve aynı
    gerekçeyle: doğru cevabı olmayan bir görevde yanıtsız denemeyi iki taraftan
    birine yazmak indeksi kaydırır. AVSR'nin kuralının tersi, çünkü orada bir
    doğru cevap var ve zaman aşımı onu vermemektir.
  - **`OTHER` = §6.5'in "karışım yanıtı"**: sunulan iki heceden hiçbirine
    karşılık gelmeyen bildirim — üçüncü hece de, `DİĞER` seçeneği de. Oranların
    **paydasında** (bir yanıttır) ama **indekste değil** (bir kulak adlandırmaz).
    Üçüncü heceyi ayrı bir kategori yapmadım: ikisi de aynı şeyi söylüyor ve ham
    yanıt zaten kayıtta, ayrım gerektiğinde analizde yapılabilir.
  - **Kategori seçilen seçenekten türüyor, yazılan metinden değil** (Adım 4
    kuralı). `DİĞER` seçen katılımcı ekrandaki heceleri reddetmiştir; yazdığı
    metni bir kulağa geri okumak vermediği bir bildirimi uydurmak olurdu.
  - **KAİ hiçbir kulak bildirilmediyse `None`, 0 değil.** 0, yalnızca karışım
    yanıtı vermiş bir katılımcı için "tam simetrik" diye okunurdu — oysa indeksin
    hiçbir şey söylemediği tek durum tam olarak odur.
  - **Oranların paydası yanıtlanan denemeler.** Zaman aşımı hiçbir paydaya
    girmiyor, `n_missing`'de ayrıca duruyor; çoğunlukla zaman aşımından oluşan
    bir koşu böylece "düşük oran" yerine "az gözlem" olarak görünüyor.
  - **Yönerge serbest bildirim** (taslak §6.5). `prompts.question` tekil:
    "Hangi heceyi duydunuz?". İki hece sunulduğu söylenmiyor, bir kulağa
    odaklanma istenmiyor — yönlendirilmiş dikkat ölçümü uyuma kontrolüne
    çevirirdi.
  - **`speaker_id` deneme başına yazılıyor**, diğer üç konuşmacılı modülle aynı
    gerekçeyle: config anlık görüntüsü konuşmacıyı yalnızca
    `speaker_selection.strategy: fixed` iken sabitler (§F.4 açık), ve
    `plan_trials(..., speaker_id=...)` Adım 8'in seçimini kabul ediyor.
  - **Çift bazında tablo rapora eklendi** (ölçüt değil, QC). §6.5 indeksi tüm
    denemeler üzerinden hesaplıyor; çift bazında dağılım bir uyaran
    artefaktının görüneceği tek yer: /ga/ içeren her çift hangi kulaktan
    gelirse gelsin /ga/ bildiriliyorsa asimetri kulaklarda değil token'larda.

- **Bilinen sınırlar:**
  - **Çapraz duyma ölçütü bu adımda config'e girmedi.** §6.5 "SSD grubunda
    sağır kulağa sunulan hecenin şans düzeyinin üzerinde bildirilmesi" diyor;
    bu ölçüt katılımcının sağır kulağını bilmeyi gerektiriyor ve o bilgi
    katılımcı akışıyla (Adım 8) geliyor, raporu da QC raporu (Adım 9). Modül
    tarafında gereken ham sayılar üretiliyor (kulak başına bildirim oranı,
    `ear_advantage()`); eşik ve işaretleme Adım 9'a not düşüldü. **Ölçüt veri
    toplanmadan önce kesinleşmeli** — sonradan seçilmesi, hangi katılımcının
    çapraz duyduğuna sonuca bakarak karar vermek olur.
  - **Taslaktaki beş danışman maddesi hâlâ açık** (deneme sayısı, görevin SSD
    grubuna uygulanıp uygulanmayacağı, KAİ'nin birincil sonuç mu QC ölçütü mü
    olduğu, yönerge biçimi, kovaryat kullanımı). Hiçbiri kodu engellemedi:
    sayılar config'ten, yönerge metni config'ten, kalanlar analiz kararı.
  - Modül tek başına koşuyor; yönerge ("her denemede duyduğunuz heceyi
    bildirin"), alıştırma, mola ve katılımcı girişi Adım 8'de.
  - Duman testi monitörün HD Audio çıkışında yapıldı (Bluetooth kulaklık
    kapalıydı); kanal yönü kullanıcının kulaklıklı testiyle ayrıca doğrulandı.
  - 30 deneme tek bloğa sığıyor (`break_every_n_trials: 60`), yani bu modülde
    §A.5'in commit sınırı modülün sonu. Deneme sayısı yükseltilirse
    kendiliğinden bölünür.

- **Sonraki adıma not:**
  - **Adım 7c (GIN) `stream.py`'yi paylaşacak**, `block.py`'yi değil (Adım 7'nin
    notu geçerli). Dikotik `block.py`'yi paylaştı ve `TrialPolicy` bunun için
    yeterli oldu — yeni bir modülün döngüyü kopyalaması hâlâ gereksiz.
  - **Adım 8** dikotik yönerge ekranını vermeli ve orada **iki heceden söz
    etmemeli**; serbest bildirim yönergesi ölçümün parçası. Kulaklık yönü
    (L sol kulakta) oturum öncesi kontrol listesine girmeli — kanal yönü tersse
    tüm lateralizasyon verisi etkilenir.
  - **Adım 8** ayrıca çapraz dinleme kontrolüyle (`cross_hearing_check`)
    dikotik görevin ilişkisini kurmalı: ikisi de aynı varsayımı sınıyor, biri
    sessizlik/ses tespitiyle, diğeri yarışma altında.
  - **Adım 9** `v_trials_flat`'tan okurken dikotik için `dichotic_left_token`,
    `dichotic_right_token`, `category` ve iki RT sütununu bulacak;
    `dichotic.ear_advantage()` doğrudan çağrılabilir. QC raporu iki şeye
    bakmalı: **karışım yanıtı oranı** (yüksekse görev anlaşılmamış ya da seviye
    düşük) ve **SSD katılımcılarında sağır kulak bildirim oranı** (çapraz duyma
    — yukarıdaki açık ölçüt).

### Adım 7c — Modül 6: GIN (Gaps-In-Noise)
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-30. Otomatik testler yeşil (**787 test**; CI'da koşan
  716, donanımda 71, ffmpeg gerektirdiği için atlanan 19; ruff + mypy temiz).
  `TEST_ADIM_7C.md`'deki üç test kullanıcı tarafından yürütüldü ve geçti.
- **Commit:**
  - `0294156` — mcgurk/modules/gin.py, stream.py'ye run_gin, şema sürümü 4
    (responses.event_index), GINExtra'ya segment_index, config'e
    response_window_ms/lead_in_s

- **Ne yapıldı:**
  - **`mcgurk/modules/gin.py`** — segment sırası (tohumlanmış), tuş basımının
    hangi boşluğa atfedildiği, eşik hesabı (4/6 ölçütünü sağlayan en kısa süre)
    ve operatör raporu. **PsychoPy yok** (paket sınırı testine eklendi).
  - **`stream.py` paylaşıldı, kopyalanmadı:** `run_gin()` oddball'la aynı
    dosyada. Planlama (`_schedule`), ekran bekleme (`_hold`), sağlık sayacı
    okuma (`_health_delta`) ortak; döngü gövdesi ayrı çünkü şekil farklı —
    oddball ton başına bir deneme yazar ve basımı **tona** atfeder, GIN altı
    saniyelik segment başına bir deneme yazar ve basımı segmentin **içindeki
    boşluğa** atfeder. `_SegmentCache` ve `_flush_gin` GIN'e özgü.
  - **Şema sürümü 3 → 4: `responses.event_index`.** GIN, analiz birimi
    denemeden küçük olan ilk modül — bir segment 3 boşluk taşıyor ve eşik boşluk
    süresi başına hesaplanıyor, dolayısıyla bir isabet **hangi boşluğu**
    saptadığını söylemeli. `event_index` `design_extra.gap_onsets_s`'e indeks;
    başka her modülde deneme zaten olay olduğu için NULL. `v_trials_flat`'a
    `event_index` ve `gin_segment_index` eklendi.
  - **`db/design.py` → `GINExtra`** artık `segment_index` de taşıyor (hazırlanan
    dosyaya `stimuli/gin/segment_<nn>.wav` bağlanıyor).
  - **Config:** `modules.gin`'e `response_window_ms` ([100, 900] ms), `lead_in_s`
    (1.0 s) eklendi. Şema, pencerenin üst sınırının `min_gap_separation_s`'ten
    kısa olmasını zorluyor (aksi hâlde bir basım iki boşluğa ait olurdu; ölçülen
    en dar ayrım 1.029 s). `ear_selection: both` artık modülü ikiye katlıyor
    (`ears_tested()` → `total_trials()`), `fixed_ear: both` reddediliyor (GIN
    monaural).
  - **`tools/run_module.py --module gin`** kuru koşuda boşluk dağılımını ve
    yakalama segmentini, canlı koşunun sonunda eşik raporunu basıyor.
    `--ear left|right` **zorunlu** (`good_ear` iken kulak katılımcıya bağlı).
  - **Uyaran tarafında değişiklik yok** — 30 segment / 60 boşluk Adım 2'de
    üretilmişti. Ölçümle doğrulandı (aşağıda).
  - **Test: 68 yeni test** (721 → **787**; CI'da koşan 716, donanımda 71,
    ffmpeg gerektirdiği için atlanan 19; ruff + mypy temiz). CI'da 49 tasarım/
    atfetme/eşik testi (deneme sayısı `config.trial_counts()` ile birebir, aynı
    tohum → aynı sıra, boşlukların manifest'ten geldiği, yakalama segmentinin
    korunması, pencere kenarları, iki boşluk arası basım, eşik aritmetiği —
    elle kurulmuş monoton olmayan ve hiç sağlanmayan durumlar dâhil, kulak
    seçimi kapıları, config kapıları) + 7 flush testi (basımın veritabanına
    doğru satır olarak inmesi, donanımsız) + 5 donanım testi + 7 `event_index`
    şema testi.
  - **Canlı duman testi** (3 segment, tam ekran, 75 Hz): 3/3 sunuldu, 0 düşen
    kare, 0 ses zamanlaması bozulması, eşik raporu doğru bastı.

- **Yol boyunca çıkan iki gerçek hata (donanım testinde yakalandı):**
  - **İlk segment saat başladıktan sonra yükleniyordu.** Altı saniyelik dosyanın
    diskten okunması giriş süresini yiyor ve akış zaten geçmiş bir başlangıç anı
    istiyordu (`StreamError`, ~11 ms geç). İlk segment artık saat başlamadan
    önce yükleniyor — oddball'ın tüm setini önden yüklemesinin GIN'deki
    karşılığı. `lead_in_s` bir sabitleme süresidir, yükleme penceresi değil.
  - **Segment kuyruk bekleyişi bir sonraki segmentin planlama payını yiyordu.**
    Bekleyiş artık bir sonraki segmentten `SCHEDULE_LEAD_S` (0.25 s) önce
    kesiliyor; o çeyrek saniyedeki basımlar bir sonraki turun baş bekleyişinde
    toplanıp flush anında onset'e göre kovalanıyor, hiçbir şey kaybolmuyor.

- **Uyaran ölçümü (2026-07-30, `stimuli/gin/`):**
  - Her boşluk **gerçek seviye düşüşü**: 12 ms boşlukta −22.9 dB, 4 ms'te
    −21.6 dB, 3 ms'te −15.8 dB. Kısa boşlukta düşüş daha az çünkü kenar
    rampaları boşluğun içine giriyor — bu beklenen ve görevin özü.
  - Segment seviyesi −23.2 dBFS (config hedefiyle uyumlu). Segment başında
    yumuşak rampa var (Adım 2'de 200 ms'e çıkarılmıştı).
  - Segment başına boşluk dağılımı `{0:1, 1:7, 2:13, 3:9}` — **bir yakalama
    segmenti** (0 boşluk) rastlantısal olarak var; standart GIN'de garanti
    edilir, burada değil (Adım 2 bilinen sınırı hâlâ geçerli).

- **Alınan kararlar:**
  - **Analiz birimi boşluk, deneme değil.** Bu, `event_index` ve şema sürümü 4
    kararının gerekçesi: eşik boşluk süresi başına hesaplanıyor, isabet hangi
    boşluğu saptadığını söylemezse veritabanından eşik yeniden kurulamaz.
    Alternatif (RT'den boşluğu geri hesaplamak) kırılgan ve sessiz olurdu.
  - **Pencere dışı basım `OUTSIDE_WINDOW` değil, düz `FALSE_ALARM`.** Oddball'da
    bir tonu takip eden geç basım o tona yanıt olabilirdi (`OUTSIDE_WINDOW`);
    GIN'de her boşluğun penceresi dışındaki basım hiçbir boşluğu yanıtlamadı ve
    "duyulacak bir şey yokken basmak" burada yanlış alarmın **tanımı**.
    `event_index` NULL, RT NULL.
  - **Kaçırma satır üretmiyor** (oddball kuralı): basımın yokluğu. Denemenin
    taşıdığı boşluklarla dönen `event_index`'ler farkından türüyor.
  - **Eşik ulaşılamazsa `None`, en uzun boşluk değil.** Hiçbir süre 4/6'yı
    sağlamıyorsa "eşik test aralığının dışında" bir bulgudur; en uzunu yazmak
    ölçülmemiş bir eşik uydurmak olur. Eşik **her zaman yanlış alarmla birlikte**
    basılıyor (taslak §"Yorumlama Sınırları").
  - **En kısa niteleyen süre, en kısa niteleyen dizi değil.** Katılımcı 4 ms'i
    kaçırıp 3 ms'i şansla yakalayabilir; ölçüt "4/6 saptanan en kısa süre",
    "en kısa saptanan süreler dizisi" değil. Monoton olmayan durum süre başına
    tabloda sayının yanında görünüyor.
  - **GIN monaural, kulak katılımcının.** `good_ear` iken `plan_trials`'a kulak
    verilmezse **açık hata** — sessizce bir taraf seçmek ölçüm gibi görünürdü.
    `both` segment listesini iki kez sunuyor (taslağın alternatifi, oturumu ~4 dk
    uzatır); her kulakta sıra farklı (aynı sıra ikinci kez ezberden
    yanıtlanabilirdi).
  - **`trials.noise_condition = NULL`, `quiet` değil.** Uyaranın kendisi
    gürültü; "gürültüde sunuldu" burada bir koşul tarif etmiyor. NULL =
    uygulanamaz (AVSR V-only kuralı).
  - **Segmentler bir ileriden yükleniyor**, oddball gibi hepsi birden değil:
    30 × 6 saniyelik dosya yüzlerce MB tutardı. Segmentler arası 2 saniyelik ara
    yükleme için bol bol yeter (§A.12: hazırlık uyaran arası boşlukta).

- **Bilinen sınırlar:**
  - **GIN yöntem dokümanında tanımlı değil** — taslak `docs/EK_GIN.docx` §6.6,
    danışman onayı bekliyor. Standart parametreler (boşluk süreleri, 6 tekrar,
    4/6 eşik; Musiek ve ark. 2005) korundu — değiştirmek norm değerleriyle
    karşılaştırılabilirliği bozar.
  - **Yanıt penceresi ([100, 900] ms) danışman onayı bekliyor.** Taslak sayı
    vermiyor; bu bir başlangıç noktası. Oddball penceresiyle aynı kural: veri
    toplanmadan önce sabitlenmeli, sonradan seçilmesi oranları sonuca göre
    ayarlamak olur.
  - **Kontrol grubunda kulak dengeleme kuralı Adım 8'de.** Taslak, kontrol
    kulağının SSD gruplarının iyi kulak dağılımına oranlı dengelenmesini öneriyor
    (`ear_selection: both`'a alternatif). Bu, katılımcı akışını gerektiriyor;
    modül `plan_trials(..., ear=...)` ile hangi kulağı verirseniz onu sunuyor,
    dengeleme mantığı Adım 8'in.
  - **Kayıtlı onset planlanan onsettir**, ölçülen değil (motorun geri kalanı
    gibi). Aralık sapması aritmetiği doğrular, sesin o an çıktığını değil —
    onu `TimeFailed`/`XRuns` = 0 ve kademe 2 loopback söyler.
  - Modül tek başına koşuyor; yönerge, alıştırma bloğu ("yalnızca uzun
    boşluklar"), mola ve katılımcı girişi Adım 8'de.

- **Sonraki adıma not:**
  - **Adım 8 GIN için kulak seçmeli.** SSD'de iyi kulak; kontrolde dengeleme
    kuralı (yukarıda). `plan_trials(..., ear=...)` hazır; seçilen kulak deneme
    kaydına (`trials.ear`) yazılıyor.
  - **Adım 8 GIN yönergesini vermeli** ("gürültüde kısa bir kesinti duyunca
    basın") ve **boşluk sayısını/sürelerini söylememeli** (taslak). Alıştırma
    bloğu yalnızca uzun boşluklar içermeli (en kolay düzey), verisi analize
    girmemeli.
  - **Adım 9** `v_trials_flat`'tan okurken GIN için `gin_segment_index`,
    `gin_gap_durations_ms`, `event_index`, `category` ve `rt_from_burst_ms`
    sütunlarını bulacak; `gin.measures_from_rows()` doğrudan çağrılabilir. QC
    raporu **eşiği yanlış alarmla birlikte** göstermeli ve yanlış alarm oranı
    yüksek katılımcının eşiğinin yanıt eğilimini yansıtabileceğini işaretlemeli
    (taslak §"Yorumlama Sınırları").
  - **Adım 9 GIN eşiğini TBW analizlerinde kovaryat olarak** kullanmalı (taslak
    §"Analiz"): geniş bir TBW'nin modaliteler arası entegrasyondan mı yoksa
    düşük düzeyli işitsel zamansal keskinlikten mi geldiğini ayrıştırmak için.

### Adım 8 — Oturum akışı ve arayüz (alt adımlara bölündü)

**En büyük parça olduğu için 8a/8b/8c'ye bölündü (kullanıcı, 2026-07-30).** Her
alt adımda 7b/7c gibi ayrı plan-onay, test, commit. src/ Adım 8 sonunda (8c)
emekliye ayrılacak.

### Adım 8a — Oturum metinleri (config) + `python -m mcgurk.checklist`
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-30. Otomatik testler yeşil (736 CI alt kümesi, 18
  yeni; ruff + mypy temiz). `TEST_ADIM_8A.md`'deki üç test kullanıcı tarafından
  yürütüldü ve geçti (Test 1–2 donanımsız, Test 3 ses + pencere probu).
- **Commit:** `8683fa2`

- **Ne yapıldı:**
  - **Config'e katılımcı-metinleri (§A.9):** yeni `screens:` bölümü +
    `SessionScreens` modeli — `advance_key`, `continue_hint`, `welcome`,
    `practice_intro`/`practice_end`, `break` (alias'lı `break_screen`),
    `session_end`, `cross_hearing_intro` ve `module_instructions` (modül ->
    yönerge). Yeni `checklist:` bölümü + `ChecklistConfig`
    (`calibration_max_age_days: 30`, `min_free_disk_mb: 500`).
  - **Yükleme-anı doğrulaması:** `module_order`'daki etkin her ölçüm modülünün
    bir yönergesi olmalı; ölçüm modülü olmayan anahtar (ör. `practice`)
    reddedilir; boş yönerge reddedilir; `cross_hearing_intro` yalnızca çapraz
    dinleme etkinken zorunlu.
  - **`mcgurk/checklist.py`:** saf kontroller (mod, A/V gecikmesi, kalibrasyon
    yaşı, uyaran manifesti, disk + yedek klasörü, son yedek) + donanım probları
    (ptb backend + aygıt, ölçülen yenileme). `run_checks(probe_hardware=...)`,
    `any_red`, `render`, CLI (`--config`, `--no-hardware`). Herhangi bir KIRMIZI
    -> çıkış kodu 1 (8b oturumu reddederken aynı kapıyı çağıracak).
  - **Metinler "Don'ts" gözetilerek yazıldı:** McGurk etkisi anlatılmıyor,
    dikotik'te iki hece sunulduğu söylenmiyor / kulağa dikkat istenmiyor, GIN'de
    boşluk sayısı/süreleri verilmiyor.
  - **Test:** 18 yeni (`test_config_screens.py` 8, `test_checklist.py` 10).
    Mevcut konsol-encoding testi `checklist.py`'yi tarıyor -> tüm bastığı metinler
    cp1254 (Türkçe Windows konsolu) ile uyumlu.

- **Alınan kararlar:**
  - **Saf/donanım ayrımı:** zorunlu kabul kriteri testi ("eksik/eski kalibrasyon
    -> KIRMIZI -> oturumu engelle") donanımsız CI'da koşuyor; donanım probları
    lazy import edilir, modül PsychoPy'siz import olur.
  - **Eşikler config'ten** (`calibration_max_age_days`, `min_free_disk_mb`), koda
    gömülü değil (§A.9): farklı merkezler KIRMIZI çizgisini farklı yere koyar.
  - **Development'ta mod/offset/kalibrasyon UYARI, KIRMIZI değil** — dev oturumu
    bunlarsız meşru; KIRMIZI kapısı yalnızca `data_collection` için.
  - **Devre dışı bir ölçüm modülünün yönergesi config'te kalabilir** (dormant,
    yeniden etkinleşince döner); yalnızca modül-olmayan anahtar reddedilir —
    mevcut "modülü devre dışı bırak" testlerini kırmamak için.
  - **check_filesystem=False ile yüklenir:** dosya kapıları KIRMIZI *satır* olarak
    raporlanır (çökme değil); şemanın data_collection kapıları (null offset/aygıt)
    yine yüklemeyi durdurur ve hangi alanın eksik olduğunu tek tek söyler.

- **Bilinen sınırlar:**
  - Checklist çıktısının **operatör onay ekranı** (arayüzde) 8b'de — burada
    yalnızca CLI ve yeniden kullanılabilir `run_checks` var.
  - Katılımcı metinleri config'te ama henüz **hiçbir ekrana çizilmiyor** — 8b
    tüketecek.
  - Donanım probları CI'da test edilmiyor (PsychoPy yok); manuel test kapsıyor.

- **Sonraki adıma not:**
  - **8b `run_checks`/`any_red`'i oturum başında çağırmalı** ve `data_collection`
    modunda KIRMIZI varsa oturumu reddetmeli; aynı çıktı operatör onay ekranında
    da gösterilmeli.
  - **8b `screens.*` metinlerini tüketmeli:** yönerge ekranları (`advance_key` ile
    ilerleyen), mola ekranı (`break_duration_s` ile), alıştırma
    (`practice_intro`/`practice_end`), çapraz dinleme (`cross_hearing_intro`).
  - Çapraz dinleme kontrolü SSD'ye özgü; CTRL'de atlanır (loglanır). Sonuç DB'ye
    yazılır; eşik/analiz Adım 9'un işi.

### Adım 8b — Oturum akışı çekirdeği (iki tura bölündü)

**8b, hacmi nedeniyle 8b-i (iskele) ve 8b-ii (alıştırma + çapraz dinleme) diye
ikiye bölündü (kullanıcı, 2026-07-30).**

### Adım 8b-i — Oturum akışı iskeleti
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-30. Otomatik testler yeşil (763 CI alt kümesi, 22
  yeni; ruff + mypy temiz). `TEST_ADIM_8B_I.md` kullanıcı tarafından yürütüldü
  ve geçti (tam akış + ESC her aşamada).
- **Commit:** `1882dcb`

- **Ne yapıldı:**
  - **Yeni `mcgurk/ui/` paketi:** `login.py` (gui katılımcı formu; saf
    `build_participant` — grup/cinsiyet eşlemesi, yaş 18–60, kod sanitizasyonu,
    ad/soyad yok), `screens.py` (tuşla ilerleyen yönerge/mola/operatör-checklist
    ekranları, ESC ile abort), `runtime.py` (ortak `open_hardware` +
    `start_session`), `session.py` (orkestratör), `__main__.py`
    (`python -m mcgurk.ui`).
  - **Akış:** checklist(konsol; data_collection'da KIRMIZI→reddet) → giriş →
    donanım → operatör onay ekranı → karşılama → `module_order` (yönerge → koşu
    → bloklar-arası mola) → bitiş → `finish_session` + yedek. ESC her aşamada →
    `aborted` + yedek.
  - **`block.py`'ye `on_break` kancası** (bloklar arası, §A.5 commit sınırında);
    dört blok sarmalayıcısı geçiriyor. `db.count_sessions()` eklendi.
  - **`run_module` ortak `runtime`'a taşındı** — donanım açma + session satırı
    tek yerde; harness ile oturum akışı aynı kodu paylaşıyor.
  - **practice ve çapraz dinleme 8b-ii'ye:** akışta yerleri loglanıp atlanıyor.
  - **Test: 22 yeni** — `test_ui_login` (12), `test_ui_session` (8: saf kararlar
    + ui import güvenliği), `test_block_on_break` (2). Saf kararlar
    (`select_speaker` fixed/balanced/random, `good_ear_for` PTA/grup) donanımsız
    CI'da doğrulanıyor.

- **Alınan kararlar:**
  - **İyi kulak:** iki PTA da varsa daha düşük (iyi) kulak; yoksa gruptan
    (SSD_R→sol, SSD_L→sağ); CTRL'de PTA yoksa varsayılan sağ + log. Kontrol
    kulak dengeleme danışman kararı (Adım 8/9).
  - **Konuşmacı:** fixed tam; balanced oturum sayısıyla döner; random tohumdan
    üretilebilir. Seçilen konuşmacı AV modüllerine `speaker_id` ile geçer.
  - **Ortak `runtime`:** "iki kopya sürüklenir" — harness ve oturum aynı donanım
    kurulumunu kullanmalı, yoksa aralarında bir zamanlama farkı gizlenebilir.

- **Bilinen sınırlar:**
  - Alıştırma bloğu ve çapraz dinleme modülü henüz yok (8b-ii); şimdilik
    loglanıp atlanıyor.
  - Resume (kaldığı yerden devam) yok — 8c. Bu turda her koşu yeni oturum satırı.
  - Oturum akışı donanım gerektirdiği için CI'da test edilmiyor; saf kararlar
    ediliyor. Uçtan uca entegrasyon testi 8c.

- **Sonraki adıma not (8b-ii):**
  - **ESC onayı (kullanıcı isteği, 2026-07-30):** ESC'ye basınca doğrudan
    çıkmak yerine "Çıkmak istediğinize emin misiniz? Evet / İptal" ekranı çıksın;
    İptal → oturuma devam, Evet → `aborted`. Şu an ESC anında kesiyor.
  - **Alıştırma bloğu:** uyumlu ısınma, geri bildirimsiz, `practice` bloğuna
    yazılır, analize girmez (GIN alıştırması yalnızca uzun boşluklar).
  - **Çapraz dinleme modülü:** onaylı varsayılan — hazır 1000 Hz oddball tonu,
    sağır kulağa lateralize, ~%50 catch, `space`=duydum; SSD'ye özgü, CTRL'de
    atlanır; sonuç DB'ye (`cross_hearing` bloğu).
  - **Konuşmacı değiştirme:** `docs/KONUSMACI_DEGISTIRME.md` yazıldı (kullanıcı
    isteği) — mevcut konuşmacıyı değiştirme ve yeni konuşmacı ekleme adımları.

### Adım 8b-ii — Alıştırma bloğu + çapraz dinleme + ESC onayı
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-30. Otomatik testler yeşil (783 CI alt kümesi, 21
  yeni; ruff + mypy temiz). `TEST_ADIM_8B_II.md` kullanıcı tarafından yürütüldü
  ve geçti: ESC onayı (video sırasında dâhil), alıştırma, ve çapraz dinleme
  tonunun sağır (sağ) kulaktan geldiği doğrulandı.
- **Commit:** `82a9a4d`

- **Ne yapıldı:**
  - **ESC onay ekranı (kullanıcı isteği):** engine'e `set_abort_confirmer`/
    `should_abort` dolaylılığı. ESC görülen her yer (`check_abort` -> video/
    fixation/stream; `response.py`; `screens.py`) artık `should_abort()`'tan
    geçiyor. Confirmer takılıysa "emin misiniz?" (`screens.confirm_quit`, ENTER=
    Evet, ESC=İptal); takılı değilken anında kes (harness/testler). `session.py`
    confirmer'ı kurar, `finally`'de temizler. Config: `screens.quit_confirm`.
  - **Alıştırma bloğu:** `modules/practice.py` (uyumlu AV ısınma, tohumdan
    üretilebilir, `practice` bloğuna, NoExtra) + `block.py`'de `practice_policy`/
    `run_practice` (McGurk ızgarası, skorlama/geri bildirim yok). Akış:
    `practice_intro` -> denemeler -> `practice_end`.
  - **Çapraz dinleme modülü:** `modules/cross_hearing.py`. `plan_trials` (saf):
    ~%50 sinyal (`tone_hz` tonu sağır kulağa lateralize) / ~%50 catch, en az
    birer tane, tohumdan üretilebilir. `run_cross_hearing` (donanım): fixation ->
    ton/sessizlik -> yanıt penceresi -> isabet/yanlış alarm; `cross_hearing`
    bloğuna (`design_extra.signal_present`), `space`=duydum. CTRL'de atlanır.
    Config: `cross_hearing_check`'e `tone_hz`/`catch_ratio`/`response_window_ms`/
    `response_key`/`fixation_duration_ms`/`post_response_ms`; `required_tones()`
    çapraz-dinleme tonunu da türetiyor.
  - **`tools/run_cross_hearing.py`:** yalnızca çapraz dinlemeyi koşan araç
    (`--ear` = sağır kulak) — tam oturum beklemeden lateralizasyonu teyit için.
    Ortak `runtime`'ı kullanıyor.
  - **Test: 21 yeni** — çapraz dinleme tasarımı+atfetme (11, ton-türetme dâhil),
    alıştırma tasarımı (4), ESC confirmer (4) + güncellenen oddball ton testi.

- **Alınan kararlar:**
  - **ESC onayı her yerde** (kullanıcı, 2026-07-30): ekranlar + uyaran sunumu
    dâhil. Sunum sırasında "İptal" o denemeyi kare düşmesiyle işaretleyebilir —
    kabul edilen bedel.
  - **`confirm_quit` tampon temizliği `waitRelease=False`** (donanım testinde
    yakalandı): video/stream'de ESC `psychopy.event` ile yakalanıyor ama onay
    ekranı `kb` okuyor; varsayılan `waitRelease=True` bırakılmamış keydown'ı
    düşürmediği için onay ekranı anında "İptal" okuyup sönüyordu. `waitRelease=
    False` ile dialogu açan ESC de düşürülüyor.
  - **Alıştırma yalnızca forced-choice ısınma** (kullanıcı): McGurk ızgarası;
    oddball/GIN'in space-bas tuşu kendi yönergesinde. Skorlama yok (§Don'ts).
  - **Çapraz dinleme catch oranı kırpılır:** en az bir sinyal ve bir catch
    garanti (aksi hâlde bir oran tanımsız kalırdı).
  - **`practice`=NoExtra, `cross_hearing`=CrossHearingExtra(signal_present)**
    zaten Adım 1'de DB'de tanımlıydı; blocks.module CHECK ikisini de içeriyordu.

- **Bilinen sınırlar:**
  - Çapraz dinleme eşiği/"şans üstü mü" yorumu **Adım 9** (§F.3); 8b-ii yalnızca
    isabet/yanlış alarmı topluyor. `signal_present` `design_extra`'da; VIEW
    sütunu Adım 9'da eklenebilir (şema bump).
  - ESC onayı sunum sırasında bir denemeyi kare düşmesiyle işaretleyebilir
    (kabul edilen).
  - Resume yok — 8c. Oturum akışı donanım gerektirdiği için CI'da test edilmiyor;
    tasarım/atfetme/confirmer mantığı ediliyor.

- **Sonraki adıma not (8c):**
  - **Resume:** yarıda kalan (`aborted`/`running`) oturumu tespit edip kaldığı
    modül/bloktan devam. Şu an her koşu yeni oturum satırı.
  - **Uçtan uca entegrasyon testi:** sahte katılımcı, tüm modüller, DB'den
    çıktıya (donanımsız olabildiğince).
  - **main.py yönlendirmesi + src/ emekliliği** (kullanıcı kararı): main.py yeni
    akışa, eski src/ + config.yaml + data/mcgurk.db legacy'ye.
  - **`develop` -> `master` merge + `git tag adim-8-oturum-akisi`.**
  - Çapraz dinleme `signal_present`'ı `v_trials_flat`'a eklemek (şema bump)
    Adım 9'un QC/analiz işiyle birlikte.

### Adım 8c — Kesinti/devam + emeklilik + master merge (iki tura bölündü)

**8c, hacmi nedeniyle 8c-i (resume) ve 8c-ii (src emekliliği + master merge)
diye ikiye bölündü (kullanıcı, 2026-07-30).**

### Adım 8c-i — Kesinti/devam (resume)
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-30. Otomatik testler yeşil (794 CI alt kümesi, 10
  yeni; ruff + mypy temiz). `TEST_ADIM_8C_I.md` kullanıcı tarafından yürütüldü
  ve geçti (yarıda kes → devam, tamamlanan modüller atlandı; yeni/iptal/
  `--new-session`).
- **Commit:** `0602fbb`

- **Ne yapıldı:**
  - **DB yardımcıları** (`database.py`): `latest_resumable_session`
    (`aborted`/`running` son oturum), `completed_trial_counts` (yalnız
    `completed` bloklardaki deneme, modül başına), `session_speaker_id`
    (konuşmacıyı denemeden geri okur), `set_session_status` (tekrar `running`).
    Şema değişmedi.
  - **`login.py`:** `ask_resume_or_new` (Devam et / Yeni oturum / İptal).
  - **`session.py` yeniden yapılandırıldı:** girişten sonra yarım oturum aranır;
    "Devam et"te **aynı `session_id`, tohum ve saklı config snapshot'ı**
    (`config_from_snapshot`) kullanılır, durum `running`. Her modül yalnızca
    **kalanını** koşar (`remaining_plan`): tamamlanan atlanır (yönergesiz),
    forced-choice kısmi modül `plan[K:]`'ten sürer, stream/çapraz-dinleme tam
    yeniden. Konuşmacı denemeden geri okunur (balanced/random'da yeniden
    türetilemez).
  - **`__main__.py`:** `--new-session` — yarım oturum olsa da teklifi atlar.
  - **Test: 10 yeni** (`test_resume.py`): `remaining_plan` kuralları, config
    snapshot round-trip, DB yardımcıları (bellek-içi DB).

- **Alınan kararlar:**
  - **Saklı snapshot'tan yeniden kurulum:** kalan tasarım orijinalle birebir
    aynı olsun (mevcut config değişmiş olabilir) — round-trip testle doğrulandı.
  - **Stream (oddball/GIN) ve çapraz dinleme tam yeniden** (kullanıcı): sürekli
    akış ortadan sürdürülemez; yarım `aborted` blok DB'de kalır, analiz dışlar.
  - **Forced-choice blok düzeyinde sürer:** completed bloklardaki K deneme
    atlanır, `plan[K:]` yeni bloklar hâlinde koşulur; tohum sırayı sabitler.

- **Bilinen sınırlar:**
  - Resume orkestrasyonu donanım gerektirdiği için CI'da test edilmiyor; karar
    mantığı (`remaining_plan`), DB sorguları ve snapshot round-trip ediliyor.
  - Checklist yeni koşuda **mevcut** config'e karşı çalışır (makine durumu);
    resume tasarımı snapshot'tan gelir. Farklı config mod'ları arası resume
    (dev↔data_collection) beklenmiyor, ayrıca korunmadı.

- **Sonraki adıma not (8c-ii):**
  - **src/ emekliliği:** `main.py` yeni akışa (`mcgurk.ui`) yönlendirilir; eski
    `src/` + `config.yaml` + `admin.py` + `data/mcgurk.db` `legacy/`'ye
    (`git mv`, silme değil). `src/`'e bağlı testler taşınır/güncellenir. README +
    CLAUDE.md: tek çalışan platform yeni paket.
  - **`develop` → `master` merge + `git tag adim-8-oturum-akisi`** (dal
    politikası; master hâlâ initial commit'te → fast-forward).

### Adım 8c-ii — src emekliliği + master merge
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-30. Otomatik testler yeşil (773 CI alt kümesi; silinen
  21 src testi düştü, yeni paket etkilenmedi), ruff + mypy temiz (107 dosya,
  legacy hariç). `TEST_ADIM_8C_II.md` kullanıcı tarafından yürütüldü ve geçti.
- **Commit:** `56c902e` (+ `develop` → `master` merge + tag `adim-8-oturum-akisi`)

- **Ne yapıldı:**
  - **src/ emekliliği (git mv, silme değil):** `src/`, eski `main.py`,
    `admin.py`, `config.yaml`, `scripts/generate_{noisy,dichotic}_stimuli.py`,
    `TEST_ADIM_0.md` → `legacy/`. `legacy/README.md` (donmuş referans + eski↔yeni
    tablo). `data/mcgurk.db` zaten gitignore'lu (depoda değil).
  - **main.py yönlendirildi:** kök `main.py` artık `python -m mcgurk.ui`'yi
    çağıran ince shim. `SDL_AUDIODRIVER=wasapi` yeni pakette
    (`engine/psychopy_prefs.py`) zaten korunuyor.
  - **Test:** Adım 0'ın 7 src testi silindi (git rm; git geçmişi korur).
    `tests/conftest.py` yeniden yazıldı — `src` bağımlılığı kalktı, `sys.path` +
    `hardware_speaker` (yeni paketin donanım testleri) kaldı.
  - **Araç/CI:** `pyproject.toml` mypy `files`'tan `src`/`admin.py` çıktı,
    `legacy/` ruff + mypy'de hariç. README + CLAUDE.md yeni duruma göre
    güncellendi (README derin içerik yenilemesi Adım 9'a).

- **Alınan kararlar:**
  - **Taşı, silme (kullanıcı):** src ve bağlıları `legacy/`'de donmuş referans.
    Çalıştırılmaz/test edilmez; kırık `from src` importları inert.
  - **src testleri silindi (kullanıcı):** emekli kodu test ediyorlardı; yeni
    paketin tam test paketi var; geçmiş git'te.

- **Bilinen sınırlar:**
  - `legacy/` içindeki kod olduğu gibi dondu; importları kök `src/`'i işaret
    ettiği için doğrudan koşmaz (kasıtlı — referans).
  - README hâlâ eski `src/` tasarımından izler taşıyor; tam yenileme Adım 9.

- **Sonraki adıma not:** Adım 9 (analiz/dışa aktarım) `v_trials_flat` üzerinden
  çalışır; çapraz-dinleme `signal_present`'ı VIEW'e eklemek (şema bump) Adım 9'un
  işi. Prova oturumu kapısı Adım 9'da.

### Adım 8.5 — Arayüz cilası + uçtan uca gösterim (İPTAL)

**İptal edildi (kullanıcı, 2026-07-30): "arayüz geliştirmesi yapmayacağız, bu
şekilde iyi".** Mevcut arayüz yeterli görüldü; katılımcı metinleri zaten
config'te (§A.9). Danışman gösterimi ayrı bir geliştirme gerektirmiyor — platform
`python main.py` ile uçtan uca koşuyor. Bu satır kararın kaydı için tutuluyor.

### Adım 9a — Analiz kütüphanesi (dışa aktarım + ölçümler)
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-30. Otomatik testler yeşil (808 CI alt kümesi, ~30
  yeni; ruff + mypy temiz). `TEST_ADIM_9A.md` kullanıcı tarafından yürütüldü ve
  geçti (dışa aktarım dosya sayıları, `cross_hearing_signal_present` sütunu,
  KVKK — `participants.csv`'de ad yok, parquet opsiyonel davranışı).
- **Commit:** `d53b61e`

- **Ne yapıldı:**
  - **Şema v4 → v5.** `v_trials_flat`'e `cross_hearing_signal_present`
    (`json_extract(design_extra,'$.signal_present')`): çapraz dinleme QC'sinin
    (9b) sinyal denemesini yakalama denemesinden ayırması için — 8c-ii'nin Adım
    9'a bıraktığı iş. Sinyal denemesi 1, yakalama 0, diğer modüller NULL.
  - **Yeni paket `mcgurk/analysis/`** (PsychoPy'siz, sınır testine eklendi):
    - `export.py` — `v_trials_flat` ve altı ham tabloyu pandas ile **CSV** yazar;
      **parquet** yalnızca pyarrow kuruluysa (yoksa uyarıp atlar, hata değil).
      Tablo/biçim adları sabit allow-list (SQL enjeksiyonu yok); 0 satırda bile
      sütun başlıkları korunuyor (cursor.description'dan, `read_sql` değil).
    - `measures.py` — `flat_rows`'u modül başına gruplar, config'i **oturum
      snapshot'ından** kurar (canlı config'i değil), her modülün **var olan**
      ölçüm fonksiyonuna dağıtır. Matematiği yeniden yazmaz (tek doğruluk kaynağı
      modüllerde). Dejenere bir modül (ör. hedefsiz oddball → d′ yok) tüm raporu
      düşürmez: `data=None` + hata mesajı, özet metni yine üretilir.
  - **`modules/mcgurk.py`'ye eksik olan oran aggregator'ı** (`McGurkRates`,
    `rates_from_rows`, `rates_by_condition`, `summarise_measures`). Diğer beş
    modülde ölçüm fonksiyonları vardı, McGurk'te yoktu — "Modül 1 oranları"
    (füzyon / görsel baskınlık / işitsel / kombinasyon / RT) buraya, modül
    konvansiyonuna uygun, CI-testli olarak eklendi. NONE (zaman aşımı) satır
    yokluğundan türetilir ve paydada kalır.
  - **`config_from_snapshot` tekilleştirildi.** `ui/session.py`'deki kopya
    `config/loader.py`'ye taşındı (PsychoPy'siz — analiz de kullanabilir);
    session.py oradan re-export ediyor. `test_resume.py` importu korundu.
  - **Araçlar:** `tools/export_data.py` (`--session`, `--format csv|parquet|both`,
    `--out`, `--db`) ve `tools/analyse.py` (`--session`; yoksa tüm oturumlar).
  - **CI:** `requirements-ci.txt`'e `pandas` eklendi (analiz katmanı CI-testli);
    `pyarrow` **eklenmedi** — parquet opsiyonel (kullanıcı kararı).
  - **Test: ~30 yeni** — `test_analysis_export.py` (CSV round-trip, parquet iki
    dal, hata yolları, oturum filtresi, boş DB'de sütun korunması),
    `test_analysis_measures.py` (modül dağıtımı, AvsrSummary, dejenere modül,
    saf `measure_module`, bilinmeyen oturum), `test_modules_mcgurk.py` McGurk
    oranları, `test_db_schema.py` v5 kolonu (sinyal/yakalama/NULL).

- **Alınan kararlar:**
  - **Parquet opsiyonel (CSV zorunlu)** — kullanıcı kararı. pyarrow ~100 MB'lık
    indirme; zorunlu kılmak yerine kuruluysa yazılıyor. Tip/NULL koruması
    (ör. `is_correct` NULL = "doğru cevap yok", boş dizeden farklı) isteyen
    parquet'i açar. CI yalnız CSV'yi sınıyor.
  - **Ölçüm matematiği modüllerde kalır; measures.py yalnız orkestrasyon.**
    İkinci bir kopya birinciyle çelişebilirdi; her modülün sayısı zaten
    `v_trials_flat` satırlarından ve CI'da elle hesaplanmış değerlere karşı
    test ediliyor.
  - **Analiz canlı config'i değil oturum snapshot'ını okur** (§G). Sonradan
    `config/experiment.yaml` değişse bile bir veri seti toplandığı tasarımla
    yorumlanır.
  - **`cross_hearing` analiz-tarafı ölçümü 9b'ye** (QC raporu) — 9a yalnız VIEW
    kolonunu açtı. Çapraz duyma "şans üstü mü" yargısı katılımcının sağır
    kulağını gerektiriyor ve bir QC kararı; measures.py'nin altı ölçüm modülüne
    girmedi.

- **Bilinen sınırlar:**
  - `qc_report.py`, uçtan uca entegrasyon testi ve başarısızlık modu testleri
    9b'de; dokümantasyon (README yenilemesi, `docs/PROTOKOL.md`,
    `docs/OPERATOR_SOP.md`) ve prova oturumu kapısı 9c'de.
  - `analyse.py`/`export_data.py` oturum düzeyinde çalışıyor; katılımcılar arası
    toplulaştırma (grup karşılaştırması) analiz tüketicisinin işi, 9a'da yok.
  - Dev `data/mcgurk.sqlite` (v4) yedeklenip silindi — aşağıdaki bekleyen
    aksiyon maddesine işlendi.

- **Sonraki adıma not (9b):**
  - QC raporu `v_trials_flat` üzerinden: düşen kare (`dropped_frames`), SOA
    sapması (`actual_soa_ms − nominal_soa_ms`), zaman aşımı oranı (yanıtsız
    deneme = response_id NULL), yanıt dağılımı; bozuk denemeler **nesnel**
    ölçütle işaretlensin (post-hoc gerekçe değil).
  - **Çapraz dinleme QC'si artık kolona sahip:** `cross_hearing_signal_present`
    ile HIT/MISS/FALSE_ALARM/CORRECT_REJECTION türetilir; "şans üstü tespit →
    o katılımcının Modül 1–2 uzamsal yön verisi işaretlensin" (§6.5). Eşik
    (30 denemede kaç bildirim / binomial mi) hâlâ danışman kararı — aşağıdaki
    bekleyen aksiyon.
  - Başarısızlık modu testleri (steps.md Adım 9): kesme→`aborted`, yanıtsız→
    zaman aşımı, eksik uyaran, ses aygıtı kaybı, disk dolu — her biri **açık
    hata**.

### Adım 9b — QC raporu + entegrasyon/başarısızlık testleri
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-30. Otomatik testler yeşil (835 CI alt kümesi, ~27
  yeni; ruff + mypy temiz). `TEST_ADIM_9B.md` kullanıcı tarafından yürütüldü ve
  geçti.
- **Commit:** `e24c01a`

- **Ne yapıldı:**
  - **Config — yeni `qc:` bloğu (§A.9, geçici/danışman onayına açık).** `QCConfig`:
    `max_dropped_frames`, `soa_tolerance_ms`, `cross_hearing_alpha`.
    `ExperimentConfig`'e **varsayılanlı** eklendi — 9a'da yazılmış (qc'siz)
    snapshot'lar `config_from_snapshot`'ta kırılmasın. `experiment.yaml`'e yorumlu
    blok. Şema sürümü **değişmedi** (v5; tablo/VIEW dokunulmadı).
  - **`mcgurk/analysis/qc_report.py`** (PsychoPy'siz, sınır-testli):
    - Zamanlama (düşen kare, en kötü kare aralığı, SOA sapması `actual − nominal`),
      modül başına zaman aşımı oranı, yanıt dağılımı.
    - **Nesnel bozuk-deneme işaretleme** (`FlaggedTrial` + gerekçe), eşikler
      snapshot'taki `qc`'den — post-hoc değil.
    - **Çapraz dinleme:** v5 kolonuyla HIT/MISS/FA/CR türetimi; **tek yönlü
      binomial** (scipy `binomtest`), boş p₀ = yanlış-alarm oranı (catch yoksa
      0.5); `p < cross_hearing_alpha` → SSD katılımcısında "Modül 1-2 uzamsal
      veri geçersiz" uyarısı (§6.5).
    - `session_qc(db, session_id)` + `summary_text()`; CLI `tools/qc_report.py`.
  - **Uçtan uca entegrasyon testi** (`test_analysis_integration.py`): sahte
    katılımcı → 8 modül (practice + 6 ölçüm + cross_hearing) tek DB'ye → export +
    measures + qc çökmeden, hiçbir şey sessizce düşmeden. steps.md'nin "uçtan uca
    entegrasyon testi" kabul kriteri; boş oturum da temiz.
  - **Başarısızlık modu testleri** (`test_failure_modes.py`): kesme→`aborted`+veri
    korunur+devam; yanıtsız→McGurk `NONE`/AVSR yanlış; eksik uyaran→config
    yüklemede yakalanır (katılımcı oturmadan); ses yolu→`AudioError` (§A.2 sessiz
    geri düşüş yok); yazım hatası→açık hata (query_only ile; sessiz veri kaybı yok).
  - **Test: ~27 yeni** (`test_analysis_qc.py` 15, `test_analysis_integration.py`
    2, `test_failure_modes.py` 7 + config/boundary). `requirements-ci.txt`
    değişmedi (scipy zaten vardı).

- **Alınan kararlar:**
  - **QC eşikleri config'te, geçici** (kullanıcı kararı) — oddball/GIN yanıt
    pencereleriyle aynı statü. **Snapshot'la taşınır:** `qc_report.py` bir
    oturumu o oturumun snapshot'ındaki eşiklerle değerlendirir, canlı config'i
    değil (§G — veri toplandığı tasarımla yorumlanır). `experiment.yaml`'i
    değiştirmek eski oturumların raporunu değiştirmez.
  - **Çapraz dinleme şans ölçütü: tek yönlü binomial, α=0.05, yanlış-alarmla
    düzeltilmiş** (kullanıcı kararı). Danışmanın açık maddesi (§F.3) böylece
    kod tarafında kapandı; α config'ten, veri toplamadan önce sabit.
  - **Çapraz dinleme zaman aşımı değil:** catch denemesinde basmamak doğru ret.
    Zaman aşımı oranı yalnız forced-choice (mcgurk/avsr/tbw/dichotic) modüllerde
    raporlanır; akış (oddball/gin) ve cross_hearing için "yanıtsız N (basımsız —
    beklenebilir)".

- **Bilinen sınırlar:**
  - Ses aygıtı kaybı ve disk-dolu başarısızlık modları CI-koşulabilir vekillerle
    test edildi (`load_audio` eksik dosya/yanlış hız → `AudioError`; `query_only`
    bağlantıya yazma → `OperationalError`). Gerçek donanım yolları `psychopy`
    işaretli motor testlerinde.
  - QC eşikleri hâlâ danışman onayı bekliyor (geçici değerler) — aşağıdaki
    bekleyen aksiyon.
  - Dokümantasyon (README, PROTOKOL.md, OPERATOR_SOP.md) ve gerçek kişiyle prova
    oturumu 9c'de.

- **Sonraki adıma not (9c):**
  - README derin yenilemesi (kurulum, kalibrasyon, oturum yürütme, analiz +
    QC/export komutları), `docs/PROTOKOL.md` (yöntem ↔ kod eşlemesi — her bağımlı
    değişkenin kod karşılığı), `docs/OPERATOR_SOP.md` taslağı.
  - **Prova oturumu kapısı** (steps.md Adım 9): gerçek kişiyle, SOP takip
    edilerek, baştan sona tam oturum; süre ölçümü; QC raporu incelenmesi.
    Otomatik uçtan uca test bunun yerine geçmez.
  - Kapanışta `develop` → `master` merge + `git tag v1.0.0` (dal politikası).

### Adım 9c — Dokümantasyon + prova oturumu + master merge
- **Durum:** TAMAMLANDI (dokümanlar; prova oturumu + master merge **en son
  kapıya**, Adım 10 sonrasına alındı — kullanıcı kararı 2026-07-30)
- **Commit:** `94c90bc` (dokümanlar), `680d054` (prova kılavuzu)
- **Ne yapıldı (dokümanlar):**
  - **`docs/PROTOKOL.md`** — yöntem dokümanı (`946383_YONTEM (3).docx`) ↔ kod
    eşleme tablosu. §4 (katılımcı/KVKK), §5 (platform + iki **sapma**:
    MoviePy→ffmpeg, CustomTkinter→PsychoPy `gui.Dlg`), §6.1–6.4 (modüller +
    bağımlı değişkenler → modül dosyaları/fonksiyonları), §7 (bağımsız/bağımlı →
    DB sütunları), §8 (analiz → `analysis/` + dışa aktarım; §8 model kurma
    yazılım dışı). Dikotik/GIN "danışman onayı bekliyor" işaretli.
  - **`docs/OPERATOR_SOP.md`** — operatör el kitabı taslağı (Python bilmeyen için):
    kontrol listesi, karşılama/kulaklık, **ne söylenir/söylenmez** (McGurk ASLA
    anlatılmaz — en üstte uyarı), oturum davranışı, oturum sonrası (QC/yedek/
    debriefing), sorun giderme tablosu. Laboratuvara özgü yerler `[DOLDURULACAK]`.
  - **README derin yenilemesi:** durum bloğu (üç kapı: fotodiyot/kalibrasyon/prova),
    "Ne yapar" tablosu (eski 5 `src/` bölümü → doğru 6 modül), yeni "Analiz ve
    dışa aktarım" bölümü, şema v5, "Bilinen sınırlar" güncel gerçeğe göre yeniden
    yazıldı, kalan tüm `src/`/`config.yaml`/eski-bölüm atıfları temizlendi.
- **Bekleyen (en son kapı — Adım 10 sonrası):**
  - **Prova oturumu** (steps.md Adım 9 kabul kapısı): gerçek kişiyle, SOP takip
    edilerek, baştan sona tam oturum; süre ölçümü; QC raporu incelenmesi.
    Otomatik uçtan uca test bunun yerine geçmez. **Adım 10'un ürettiği
    paketlenmiş app + operatör paneli üzerinde** koşulacak (kullanıcı kararı:
    prova son teslim biçimini denemeli). Kılavuz `TEST_ADIM_9C.md`.
  - Prova'da bug çıkarsa düzeltilir, sonra `develop → master` merge +
    `git tag v1.0.0`.

### Adım 10 — Operatör paneli (PySide6) + paketleme (.exe)
- **Durum:** GELİŞTİRİLİYOR (10a TAMAMLANDI; 10b/10c bekliyor)
- **Ayrıntılı prompt:** `docs/ADIM_10.md`. **Alt adımlar (kullanıcı kararı,
  2026-07-30):** 10a panel çekirdeği (GUI'siz, CI-testli) → 10b PySide6 kabuğu →
  10c PyInstaller `.exe`. Her birinde ayrı plan-onay/test/commit.
- **Kapsam (kullanıcı isteği, 2026-07-30):**
  - **Operatör paneli** (PySide6, ayrı süreç — PsychoPy ile aynı süreçte
    çalışamaz, §CLAUDE Don'ts): butonlar → oturum başlat (deneyi ayrı süreç
    açar), kontrol listesi, dışa aktar, analiz, QC raporu, sonuçları gör
    (katılımcı/oturum listesi). KVKK: ad-soyad yok. Eski `admin.py`'nin
    (legacy) PySide6 mantığına paralel ama yeni pakete karşı.
  - **PyInstaller ile Windows `.exe`:** en kritik kısım paketlenmiş exe'de
    `stimuli/`/`config/`/`data/`/`backups/` yollarının çözümü (`_MEIPASS` vs.
    kullanıcı-yazılabilir dizin) ve PsychoPy'nin exe içinde çalışması.
  - **Sıra (kullanıcı kararı):** prova oturumu + `master` merge + `v1.0.0`
    Adım 10'un **sonuna** alındı; v1.0.0 = dağıtılabilir Windows uygulaması.

### Adım 10a — Panel çekirdeği (GUI'siz, CI-testli)
- **Durum:** TAMAMLANDI
- **Tamamlanma:** 2026-07-30. Otomatik testler yeşil (864 test, CI alt kümesi;
  25 yeni panel testi), `ruff` + `mypy` temiz; `TEST_ADIM_10A.md` manuel testleri
  kullanıcı tarafından yürütüldü ve geçti.
- **Commit:** `15d428f`
- **Ne yapıldı:**
  - **Yeni paket `mcgurk/panel/`** — PySide6'sız ve PsychoPy'siz çekirdek mantık
    (§A10.2/3). `core.py` + `__init__.py` (kamu API). Qt kabuğu (10b) ve `.exe`
    (10c) bunun üzerine oturacak; motorun `scheduling.py` ayrımı gibi, mantık
    GUI'den ayrı ve CI-testli.
  - **Yol çözümleme (§A10.6):** `resolve_roots()` saf fonksiyon +
    `detect_runtime()`. Kaynaktan iki kök de proje kökü; donmuş halde
    `resource_root = _MEIPASS` (salt-okunur kaynak), `writable_root = exe dizini`
    (taşınabilir yerleşim). Donmuş dal `sys.frozen`/`_MEIPASS` taklidiyle testli.
  - **Başlatıcılar (§A10.1):** `session_command`, `checklist_command`,
    `verify_stimuli_command`, `verify_backup_command`, `run_module_command` —
    hepsi saf `argv` listesi. Kaynaktan `-m mcgurk.ui` / `tools/*.py`; donmuş
    halde `exe --run <altkomut>`. Yalnız önek değişir, bayraklar ortak.
    `run_tool()` gerçek başlatmanın ince (subprocess) sarmalayıcısı; çıkış kodu +
    metin döndürür (KIRMIZI checklist bir sonuçtur, istisna değil).
  - **Salt-okunur tarama (§A10.4/5, KVKK):** `open_readonly()` SQLite `mode=ro`
    URI ile açar (yazma motor düzeyinde reddedilir). `list_sessions()` /
    `list_participants()` yalnız anonim kolon döndürür (kod, grup, tarih, durum,
    deneme/oturum sayısı) — ad yok.
  - **Analiz sarmalayıcıları:** `export_session`/`export_all`/`measures_text`/
    `qc_text` — PsychoPy'siz analiz katmanını doğrudan çağırıp panele hazır
    dönüş verir.
  - **Sınır testi:** `mcgurk.panel.core` hem dosya-tarama hem `PURE_LAYERS` ile
    PsychoPy'siz import garantisine bağlandı; 25 yeni test (`test_panel_core.py`).
- **Alınan kararlar:**
  - **Donmuş sözleşme:** tek exe, `--run <altkomut>` dağıtımı. 10c dağıtıcıyı
    yazacak; 10a yalnız argv sözleşmesini sabitledi (tek-exe/iki-exe kesin kararı
    §D10 gereği 10c'de).
  - **`writable_root = exe dizini`** (taşınabilir). Program Files gibi salt-okunur
    kuruluma gidilirse `%APPDATA%` fallback'i 10c'de; `resolve_roots` saf olduğu
    için o dal bugün test edilebilir durumda.
  - **`verify_backup` in-process değil, subprocess** (`tools/` paket değil,
    import edilemez; kod tekrarını önler). Export/measures/qc in-process.
  - Tarama için ayrı **salt-okunur** bağlantı; export/analiz için normal
    `Database` (§A10.5'te "güvenli", katı salt-okunur olması gerekmiyor).
- **Bilinen sınırlar / sonraki adıma not:**
  - **10b (PySide6 kabuğu):** `requirements.txt`'e PySide6 pini (CI'ya
    **eklenmez** — Qt yok), `mcgurk/panel/app.py` + `python -m mcgurk.panel`.
    Uzun işler arayüzü dondurmamalı; deneyin/checklist'in canlı çıktısı
    non-blocking (QProcess/thread) — `run_tool` yalnız kısa rapor araçları için.
  - **10c (.exe):** `resolve_roots`/`detect_runtime` gerçek bundle'a bağlanır;
    `--run` dağıtıcısı yazılır (10a'nın altkomut sözcük dağarcığını karşılar);
    PyInstaller spec (PsychoPy veri/hook, ptb/ses, ffmpeg, `schema.sql`),
    `stimuli/` gömülmez (yüzlerce MB) — exe yanına konur.
  - Panel çekirdeği analiz katmanını import ettiği için `soundfile`/`numpy`/
    `pandas` gerektirir (PsychoPy **gerektirmez**). PowerShell'de `python` base
    ortama düşerse bu bağımlılıklar bulunamaz — mcgurk ortamı kullanılmalı.

### Adım 10b — PySide6 paneli (GUI kabuğu)
- **Durum:** TESTTE (kod commit edildi; manuel ekran testi bekliyor —
  kullanıcı kararı 2026-07-30: "şimdiki halini commit/push, sonra devam".
  7b/7c precedent'i: commit önce, manuel test sonra; onaya kadar TAMAMLANDI değil.)
- **Tamamlanma:** — (manuel test sonrası). Otomatik testler yeşil (872 test, CI
  alt kümesi; +4 offscreen smoke), `ruff` + `mypy` temiz. `TEST_ADIM_10B.md`
  ekran testi **bekliyor**.
- **Commit:** `d276cc9`
- **Ne yapıldı:**
  - **`mcgurk/panel/app.py`** — `QMainWindow` (`PanelWindow`), 10a `core`'u
    üzerine ince Qt kabuğu. PsychoPy import etmez (§A10.2), yalnız PySide6.
    Üst şerit (Oturum başlat / Kontrol listesi / Uyaranları doğrula / Yedek
    doğrula), sol sonuç tablosu (anonim) + Yenile/Analiz/QC/Dışa aktar, sağ
    canlı çıktı paneli, durum çubuğu.
  - **`mcgurk/panel/__main__.py`** — `python -m mcgurk.panel`: runtime tespiti,
    config yükle (hata diyalogla, traceback değil), DB yolu writable_root'a
    göre, pencereyi aç.
  - **`tests/mcgurk/test_panel_app.py`** — offscreen smoke (4 test); PySide6
    yoksa (CI) atlanır — Qt UI CI bağımlılığı değil.
- **Alınan kararlar:**
  - **Deney *detached* süreç** (`QProcess.startDetached`): ~75 dk süren oturumu
    panel kapanınca öldürmemek için. Kısa rapor araçları (checklist/verify)
    **attached** — canlı çıktı + çıkış kodu. Panel PsychoPy'ye hiç dokunmaz
    (§A10.1).
  - **Arayüz donmaz:** alt-süreçler `QProcess` (async); in-process analiz
    (export/measures/qc) `QThread` işçisinde; sürerken butonlar kilitli.
    `core.run_tool` senkron/headless yardımcı olarak kaldı; GUI QProcess kullanır.
  - Analiz/QC/dışa aktarım **seçili oturuma** etki eder; satır yoksa uyarı.
  - `requirements.txt` zaten `PySide6==6.11.0` içeriyordu; CI'ya eklenmedi.
- **CI düzeltmesi (`320617e` sonrası, ayrı commit):** CI'ın `ruff + mypy` işi
  kırmızı geldi (pytest yeşildi). Sebep: **CI'da PySide6 kurulu değil**, bu
  yüzden `QApplication.exec()` ve `QTableWidget.currentRow()` mypy'de `Any`
  oluyor ve `warn_return_any` iki `no-any-return` hatası veriyordu
  (`app.py` `_selected_session_id`, `__main__.py` `main`). Yerelde PySide6 tipli
  olduğu için görünmüyordu. İkisi de `int`-anotasyonlu yerel değişkene alındı.
  Faydalı tuzak (10c için de): PySide6 dönüşünü doğrudan `int` bildiren bir
  fonksiyondan döndürme. **CI birebir taklit edildi** (requirements-ci.txt ile
  PySide6'sız geçici venv): düzeltme sonrası ruff + mypy + pytest yeşil.
- **Bilinen sınırlar / sonraki adıma not:**
  - Manuel ekran testi (`TEST_ADIM_10B.md`) yapılmadı; özellikle "Oturum başlat"
    ayrı-süreç davranışı ve checklist KIRMIZI gösterimi elle doğrulanmalı.
  - Benim açılış denemem (offscreen, gerçek config + `data/mcgurk.sqlite`):
    pencere açıldı, 8 buton, 1 oturum satırı, başlık doğru — davranışsal değil,
    yalnız kurulum kontrolü.
  - **10c (.exe):** `resolve_roots`/`detect_runtime` gerçek bundle'a bağlanır;
    `--run` dağıtıcısı yazılır; PyInstaller spec; `stimuli/` exe yanına konur.

### Adım 10c-i — Donmuş-farkında yol katmanı + `--run` dağıtıcısı (CI-testli)
- **Durum:** TESTTE (kod commit edildi; ekran gerektirmeyen CLI manuel kontrolleri
  bekliyor — kullanıcı kararı 2026-07-30: "şimdiki halini commit, 10c-ii'ye geç".
  7b/7c precedent'i.) **10c, kullanıcı onayıyla 10c-i (kod, CI-testli) + 10c-ii
  (PyInstaller derleme, elle) diye bölündü.**
- **Tamamlanma:** — (manuel kontrol sonrası). Otomatik testler yeşil: yerel 889,
  **PySide6'sız CI taklidi venv'inde 854 passed** (10b tuzağı önden yakalandı),
  `ruff` + `mypy` temiz.
- **Commit:** `b5141e6`
- **Ne yapıldı:**
  - **`mcgurk/paths.py`** (yeni, saf leaf, PsychoPy'siz) — tek yol-çözümleme
    otoritesi (§A10.6). 10a'nın `Runtime`/`resolve_roots`/`detect_runtime`'ı
    buraya taşındı; `panel/core` geriye-uyumlu re-export ediyor (10a/10b testleri
    kırılmadı). `ensure_writable_config`: donmuş halde ilk çalıştırmada gömülü
    varsayılan `config/experiment.yaml`'ı `writable_root/config/`'e kopyalar,
    düzenlenmiş kopyayı **ezmez**; kaynaktan repo config'ini döndürür. Paylaşılan
    altkomut sözcük dağarcığı (`RUN_FLAG`, `SUB_*`) da burada — builder ile
    dağıtıcı tek kaynaktan, drift yok.
  - **`mcgurk/app_entry.py`** (yeni) — donmuş exe giriş noktası: `--run
    session|checklist|verify-stimuli|verify-backup|run-module` → ilgili
    `main()`/tool'a; bayraksız → panel. Handler'lar lazy import (CI/PySide6
    dostu); tool'lar `runpy` ile bundle'dan koşulur (tools paketi gerekmez).
  - **Giriş noktaları bağlandı:** `ui/__main__`, `checklist`, `panel/__main__`,
    `tools/verify_stimuli` artık `_PROJECT_ROOT` yerine
    `paths.detect_runtime().writable_root` + `ensure_writable_config`. Kaynaktan
    iki kök özdeş → **sıfır regresyon** (doğrudan doğrulandı: dağıtıcı checklist =
    doğrudan checklist, `ui --help` sorunsuz).
  - **Testler:** `test_paths.py` (donmuş `detect_runtime`, ilk-çalıştırma config
    kopyası, düzenlemeyi ezmeme), `test_app_entry.py` (parse_run + yönlendirme,
    mock'lu); `PURE_LAYERS`'a `mcgurk.paths` + `mcgurk.app_entry`.
- **Alınan kararlar:**
  - Donmuş halde `project_root = writable_root`: stimuli/data/logs/backups/config
    hepsi orada; gömülü tek şey varsayılan config (ilk-çalıştırma kopyası) + paket
    verisi (`schema.sql`, `Path(__file__).with_name` ile _MEIPASS'ten otomatik).
  - Tek exe + `--run` dağıtıcısı (iki exe değil): §A10.1 ayrı-süreç kuralı korunur.
  - **PySide6'sız CI venv'inde önden doğrulama** kalıcı pratik oldu (scratchpad'de
    duruyor) — GUI/donmuş kodda "yerelde geçer CI'da patlar" sınıfını yakalar.
- **Bilinen sınırlar / sonraki adıma not (10c-ii):**
  - PyInstaller spec (`packaging/mcgurk.spec`): giriş `mcgurk/app_entry.py`;
    PsychoPy veri/hook, ptb/ses, ffmpeg, `schema.sql`, gömülü varsayılan config,
    **`tools/`** (runpy dağıtımı için), `stimuli/` **gömülmez**.
  - Build script + `packaging/README` + `TEST_ADIM_10C.md` (Windows + ekran + ses).
  - Doğası gereği makine-yinelemeli (§D10); derleyip sizin makinenizde test
    edeceğiz, çıkan sorunları düzelteceğim.

### Adım 10c-ii — PyInstaller ile Windows `.exe`
- **Durum:** TESTTE (paketleme dosyaları yazıldı ve commit edildi; **gerçek
  derleme + Windows manuel testi kullanıcının makinesinde** — §D10 gereği
  makine-yinelemeli. Kullanıcı kararı 2026-07-30: "commit et, push la".)
- **Tamamlanma:** — (Windows'ta derleme + `TEST_ADIM_10C.md` sonrası).
- **Commit:**
- **Ne yapıldı:**
  - **`packaging/mcgurk_app.py`** — PyInstaller giriş betiği (mutlak import; donmuş
    `__main__`'de relative-import kırılmasını önler). Kaynaktan da çalışır.
  - **`packaging/mcgurk.spec`** — onedir; PsychoPy yığını `collect_all`
    (psychopy, psychtoolbox, pyglet, ffpyplayer, sounddevice, soundfile,
    imageio_ffmpeg, questplus) + `copy_metadata` (sürüm okuyanlar); paket verisi
    (`schema.sql`, gömülü varsayılan `config`, `word_lists`, **`tools/`** runpy
    dağıtımı için); **`stimuli/` gömülmez**; `console=True` (iterasyon için,
    v1.0.0'da pencereli yapılabilir).
  - **`tools/build_exe.py`** — spec ile PyInstaller çağırır, çıktı/`stimuli`
    yerleşimini bildirir, PyInstaller yoksa nazik hata (`--clean`).
  - **`packaging/README.md`** — derleme, writable/`stimuli` yerleşimi, onedir
    gerekçesi, bilinen sorunlar (spec knob'ları), PySide6 LGPL, SmartScreen notu.
  - **`requirements-dev.txt`** — `pyinstaller==6.16.0` (CI'ya/runtime'a eklenmedi).
  - **`TEST_ADIM_10C.md`** — Windows + ekran + ses manuel test (5 kabul kriteri;
    paketlenmiş panelde Adım 10b'yi de doğrular).
- **Kod tarafında doğrulandı** (gerçek derleme değil): `mcgurk_app.py --run
  checklist` kaynaktan uçtan uca çalışıyor; `build_exe.py` PyInstaller yokken
  nazik hata; spec `py_compile` geçerli; ruff + mypy temiz (yerel + PySide6'sız
  CI venv); `pytest -m "not psychopy"` 890 passed.
- **Bilinen sınırlar / sonraki adıma not:**
  - **Gerçek `.exe` derleme yapılmadı** — PyInstaller bu ortamda kurulu değil ve
    PsychoPy freezing Windows'a özgü yineleme ister (§D10). İlk derlemede eksik
    gizli import/veri dosyası hatası **beklenir**; `mcgurk.spec`'ten çözülür.
  - Bu son kod adımı. Sonrası: prova oturumu (paketlenmiş app) → `develop →
    master` merge + `git tag v1.0.0` = dağıtılabilir Windows uygulaması.

## Açık kararlar (kullanıcı + danışman verecek)

Bunlar §F'den gelir. Karşılaşıldığında burada işaretlenir, karar gelince güncellenir.

- [ ] Deneysel tasarım / deneme sayıları (Adım 4'ten önce netleşmeli) — §F.1
  - **Adım 4 bunu engellemedi:** üreteç config'ten gelen her tasarımı
    üretiyor ve `config.trial_counts()` ile birebir aynı sayıyı veriyor
    (test). Danışman sayıları yükseltince kod değişmiyor. Karar hâlâ açık.
- [ ] Modül 2 kelime listesi (Adım 5, çekim gerekiyor) — §F.2
  - **Adım 5 bunu engellemedi:** hece seti çalışıyor, kelime seti için şema,
    okuyucu (`mcgurk/config/word_lists.py`), şablon
    (`config/word_lists/tr_pb_50.yaml`) ve üç ayrı hata yolu hazır. Kayıt
    yapılınca **kod değişmeyecek**: kelimeler `stimulus_prep.tokens`'a eklenir,
    `prepare_stimuli.py` koşulur, liste doldurulur, `enabled: true` yapılır.
    50 kelime × `reps: 1` oturuma **450 deneme** ekler — açmadan önce
    `python -m mcgurk.config` çıktısına bakılmalı (§F.1).
- [ ] Kulaklık tipi (donanım, çapraz dinleme kontrolünü etkiler) — §F.3
- [ ] Konuşmacı seçim stratejisi — §F.4
- [ ] **Oddball yanıt penceresi** (Adım 7'de eklendi, `[100, 800]` ms) ve **GIN
  yanıt penceresi** (Adım 7c'de eklendi, `[100, 900]` ms) — ikisi de veri
  toplamadan önce sabitlenmeli; ayrıntı aşağıdaki bekleyen aksiyonlarda.
- [ ] **GIN kontrol grubunda kulak seçimi** (Adım 7c) — SSD gruplarının iyi
  kulak dağılımına oranlı dengeleme; kod hazır, mantık Adım 8'de, karar
  danışmanın. Ayrıntı aşağıdaki bekleyen aksiyonlarda.
- [ ] **QC eşikleri** (Adım 9b'de config'e girdi, `qc:` bloğu) — `max_dropped_frames`
  (geçici 3), `soa_tolerance_ms` (20.0), `cross_hearing_alpha` (0.05). Bozuk-deneme
  ölçütü ve çapraz duyma anlamlılığı; oddball/GIN yanıt pencereleriyle aynı statü,
  veri toplamadan önce danışman onaylamalı. Snapshot'la taşınır (eski oturumlar
  eski eşikle değerlendirilir).

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
  **Adım 7b bunu engellemedi** (2026-07-29): modül taslaktaki tasarımla
  gerçeklendi, beş maddenin hiçbiri kodu değiştirmiyor — deneme sayısı ve
  yönerge metni config'ten, kalanlar analiz kararı.
- **Çapraz duyma ölçütü — kod tarafında KAPANDI (Adım 9b), danışman değerini
  onaylamalı.** §6.5, SSD katılımcısının **sağır kulağa sunulan tonu şans
  düzeyinin üzerinde tespit etmesini** çapraz duyma göstergesi sayıyor ve o
  katılımcının Modül 1–2 uzamsal yön verisinin QC raporunda işaretlenmesini
  istiyor. **Ölçüt Adım 9b'de belirlendi (kullanıcı kararı):** tek yönlü
  binomial test, boş p₀ = yanlış-alarm oranı, anlamlılık `qc.cross_hearing_alpha`
  (config, **geçici 0.05**). `tools/qc_report.py` sağır kulağın kendisini
  denemedeki `ear`'dan okur (Adım 8 girişinden gelir) ve şans üstü çıkarsa uyarı
  basar. **Sonradan seçilemez** — α veri toplamadan önce config'te sabit
  (oddball/GIN yanıt pencereleriyle aynı kural). Danışmandan beklenen: α=0.05 ve
  n_trials=20/catch_ratio değerlerinin bu görev için uygun olduğunun onayı.
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
  **Adım 7c bunu engellemedi** (2026-07-30): modül taslaktaki tasarımla
  gerçeklendi, standart parametreler (boşluk süreleri, 6 tekrar, 4/6 eşik)
  korundu. Altı maddenin hiçbiri kodu değiştirmiyor — pencere ve kulak seçimi
  config'ten/Adım 8'den, kalanlar analiz kararı.
- **Kablolu kulaklık geldiğinde iki madde birlikte kapatılacak:**
  `TEST_ADIM_3.md` Test 2 madde 7 ve `TEST_ADIM_5.md` Test 1 madde 3 — ikisi de
  "AV denemesinde dudak ile ses eşzamanlı mı" sorusu. Bluetooth'la yargılanamaz
  (aşağıdaki §F.3 maddesi). Komut: `python tools/run_module.py --module avsr
  --limit 12 --seed 3` (4., 6., 9., 10. denemeler AV).
- **§F.3 — kulaklık kararı artık somut bir gerekçeye sahip (Adım 3 bulgusu).**
  Test kulaklığı **Sony WH-1000XM4, Bluetooth** ve gerçek veri toplama için
  uygun değil: (a) 100–300 ms gecikme ekliyor ve bu gecikme **sabit değil**,
  oysa TBW modülünün ölçtüğü şey ±50 ms mertebesinde farklar; (b) kulaklığın
  kendi DSP'si (gürültü engelleme, DSEE, EQ) seviyeyi ve spektrumu
  değiştirdiği için `02_kalibrasyon.md` ölçümü kararlı olmaz; (c) SSD
  lateralizasyonu yüksek kulaklar arası zayıflama istiyor (§F.3 insert
  kulaklık öneriyor). Adım 3 testlerinde Bluetooth yeterli oldu — kulak
  izolasyonu ve SOA farkı doğrulandı — ama "ses ve dudak birlikte mi" yargısı
  kablolu kulaklıkla tekrar bakılmalı (`TEST_ADIM_3.md` Test 2, madde 7).
- **`audio.device` artık dolu:** `"Kulaklıklar (2- WH-1000XM4)"` (kullanıcı,
  2026-07-27). İki sonucu var: (a) Bluetooth kapalıyken donanım testleri ve
  `tools/run_module.py` açık hatayla duruyor — testler için
  `MCGURK_TEST_AUDIO_DEVICE` ortam değişkeni var; (b) §F.3 kulaklık kararı
  hâlâ açık, bu aygıt veri toplama için uygun değil (yukarıdaki madde).
  Aygıt **adları** sabit, **indeksleri değil**: 2026-07-26'da 6/7/8 olarak
  görünen aygıtlar 2026-07-27'de 3/4 idi (Bluetooth kulaklık kapalıyken listeye
  hiç girmiyor). Config'in isim kullanması bu yüzden. Listelemek için:
  `python tools/timing_selftest.py --devices`. Gerçek kulaklık kararı verilince
  (§F.3) config'teki değer değiştirilmeli.
- **Veritabanı şema sürümü 5'e çıktı (Adım 9a).** `v_trials_flat`'e
  `cross_hearing_signal_present` sütunu eklendi (çapraz dinleme QC'si için).
  Eski v4 `data/mcgurk.sqlite` (1 katılımcı, 3 oturum, 37 deneme — geliştirme
  verisi) `VACUUM INTO` ile
  `backups/mcgurk_pre_adim9a_schema4_20260730T175106.sqlite` olarak yedeklendi
  (integrity ok, FK temiz, satır sayıları canlıyla birebir) ve silindi; ilk
  koşuda v5 şemasıyla oluşuyor. Başka bir makinede eski sürüm dosyası varsa aynı
  şey gerekir — kod açık hata veriyor (`SchemaVersionError`), sessizce açmıyor.
  **Önceki bump (Adım 7c, sürüm 3→4):** `responses.event_index`;
  `backups/mcgurk_pre_adim7c_schema3_20260729T220000.sqlite`. **Adım 6, 2→3:**
  `backups/mcgurk_pre_adim6_schema2_20260727T222615.sqlite`.
- **Oddball yanıt penceresi — danışman kararı (Adım 7).**
  `modules.oddball.response_window_ms` config'e `[100, 800]` ms olarak girdi:
  ton başlangıcından sonra bu aralıkta gelen bir tuş basımı o tona verilmiş
  yanıt sayılıyor. Alt sınır o tona verilmiş olamayacak kadar hızlı basımları,
  üst sınır bir sonraki tona karışacak basımları dışarıda bırakıyor (şema, üst
  sınırın en kısa ISI'dan kısa olmasını zorluyor). **Veri toplama başlamadan
  önce kesinleşmeli** — sonradan değiştirmek isabet ve yanlış alarm oranlarını
  yeniden tanımlar, yani sonuca bakarak ayarlanabilir hâle getirir. GIN'in
  yanıt penceresiyle (aşağıdaki madde) birlikte karara bağlanmalı.
- **GIN yanıt penceresi ve kulak dengeleme — danışman kararı (Adım 7c).**
  `modules.gin.response_window_ms` config'e `[100, 900]` ms olarak girdi: boşluk
  başlangıcından sonra bu aralıkta gelen basım o boşluğun saptanması sayılıyor.
  Şema üst sınırın `min_gap_separation_s`'ten (1.0 s) kısa olmasını zorluyor
  (ölçülen en dar ayrım 1.029 s). Taslak `docs/EK_GIN.docx` sayı vermiyor;
  oddball penceresiyle aynı kural — **veri toplamadan önce kesinleşmeli**.
  İkinci açık madde: **kontrol grubunda kulak seçimi** — taslak, kontrol
  kulağının SSD gruplarının iyi kulak dağılımına oranlı dengelenmesini öneriyor
  (`ear_selection: both`'a alternatif). Modül `plan_trials(..., ear=...)` ile
  verilen kulağı sunuyor; dengeleme mantığı Adım 8'in katılımcı akışında.
  Diğer dört taslak maddesi (birincil sonuç mu kovaryat mı, alıştırma uzunluğu,
  sunum seviyesi dB SL/HL, standart parametrelerin korunması) kodu engellemedi.
- **Fotodiyot ölçümü (`01_av_gecikme_olcumu.md`) hâlâ bekliyor** — tasarım
  gereği tüm kod bittikten sonra. O ana kadar `timing.system_av_offset_ms`
  `null` ve motor 0 kabul edip uyarı basıyor.
- **`baseline-original` tag'i origin'e push edilmedi** (yalnızca bu makinede).
  İşaret ettiği commit (`867939c`) develop geçmişinden erişilebilir, yani
  kaybolmaz; ama Adım 0'ın "tarih kaybolmasın diye tag at" gerekçesi etiket
  uzakta yokken yarım kalıyor: `git push origin baseline-original`.
- **Adım 1 manuel testleri** (`TEST_ADIM_1.md`): tasarım özeti, config kapısı
  ve push sonrası GitHub Actions.
- **Yaş aralığı kısıtı (K4).** `participants.age` için `CHECK (18–60)` kondu.
  Prova/pilot bu aralık dışında biriyle yapılacaksa gevşetilmeli.
- **§F.1 — deneme sayıları.** Config **minimumlarla** geliyor: 797 deneme /
  ~58.8 dakika (§G örnek değerleri 1167 / ~99.5 dakika veriyordu). Bunlar karar
  değil, başlangıç noktası — danışman her sayıyı config'ten yükseltebilir.
  Ayrıntılı tablo ve gerekçeler `TEST_ADIM_1.md` → K1. **Adım 4 bunu
  engellemedi** (üreteç config'ten geleni üretiyor), ama veri toplama
  başlamadan — pratikte Adım 8'den önce — netleşmeli.
  - **Ölçülen ilk gerçek süre (Adım 4):** McGurk modülü 140 deneme = 11.7 dk
    (700 ms yanıtla), gerçek RT ile ~12–13.5 dk. Config'in tahmini 14.0 dk,
    yani modül düzeyinde tahmin **tutuyor**; toplam 58.8 dakikalık tahmin de
    bu ölçüde güvenilir sayılabilir.
  - **Ölçülen ikinci süre (Adım 5):** AVSR 135 deneme = 11.2 dk (700 ms
    yanıtla), gerçek RT ile ~12–13 dk. Config'in tahmini 15.8 dk, yani bu
    modülde tahmin **fazla cömert**; toplam 58.8 dakika bu ölçüde güvenli
    tarafta.
  - **Tavan etkisi uyarısı (Adım 5 manuel testi):** AVSR'nin kapalı 3 heceli
    setinde +5 dB SNR normal işiten bir yetişkin için kolay; ilk canlı koşuda
    üç modda da %100 doğruluk çıktı (n=12, ölçüm değil ama işaret). Kontrol
    grubu tavanda kalırsa **görsel fayda indeksi grup farkını gösteremez**.
    Danışmanla konuşulacak: `modules.avsr.noise_conditions` içindeki SNR
    düşürülmeli mi (örn. 0 veya −5 dB), ya da ikinci bir SNR eklenmeli mi.
    Kod tarafında yalnızca config değişikliği + `prepare_stimuli.py` yeniden
    koşumu gerekir.
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
