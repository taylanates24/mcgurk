# İlerleme Raporu — McGurk / SSD Platformu

Son güncelleme: 2026-07-26
Aktif adım: 0

## Durum tablosu

| Adım | Başlık | Durum | Tarih | Commit |
|---|---|---|---|---|
| 0 | Baseline düzeltme | TESTTE | 2026-07-26 | |
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
- **Durum:** TESTTE (otomatik testler yeşil; manuel test onayı bekleniyor —
  `TEST_ADIM_0.md`)
- **Tamamlanma:** —
- **Commit:** —

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

- **Sonraki adıma not:**
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
  - Gerçek çalışma ortamı `C:\Users\tayla\miniconda3\envs\mcgurk` (Python
    3.10.20). `anaconda3\envs\mcgurk` boş bir kabuk — karıştırmayın.
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

- **`TEST_ADIM_0.md` manuel testlerinin yapılması (§B.2 kapısı).** Otomatik testler
  yeşil (43 test, ruff + mypy temiz), ancak ekran ve ses gerektiren testler
  yapılmadan Adım 0 TAMAMLANDI işaretlenmeyecek.
- Adım 1'e geçmeden önce §F.1 (deneme sayıları) kararı henüz gerekmiyor; Adım 4'ten
  önce netleşmeli.
