# McGurk / SSD Değerlendirme Platformu

Tek taraflı işitme kaybı (SSD) olan yetişkinlerde görsel-işitsel konuşma
entegrasyonunun davranışsal değerlendirmesi için geliştirilen PsychoPy tabanlı
deney platformu.

**Proje:** Atılım Üniversitesi Odyoloji Bölümü, etik kurul onaylı, 12 aylık
klinik çalışma. Katılımcılar: 20 sağ SSD + 20 sol SSD + 20 kontrol.

> **Durum: kod tarafı özünde tamamlandı (Adım 9a/9b).** Platform `mcgurk/` yeni
> paketidir ve tam bir oturumu baştan sona koşar: `python main.py`
> (= `python -m mcgurk.ui`); toplanan veri dışa aktarılır, ölçülür ve kalite
> kontrolünden geçirilir (`tools/analyse.py`, `tools/export_data.py`,
> `tools/qc_report.py`). Adım 0'ın `src/` ağacı emekliye ayrıldı ve `legacy/`
> altında donduruldu (bkz. `legacy/README.md`).
>
> **Bu depo henüz veri toplamaya hazır DEĞİLDİR.** Kapıda üç kod dışı iş var:
> fotodiyot A/V gecikme ölçümü (`docs/01_av_gecikme_olcumu.md`), ses
> kalibrasyonu (`docs/02_kalibrasyon.md`) ve gerçek bir kişiyle prova oturumu.
> Ayrıca **dikotik ve GIN modülleri yöntem dokümanına eklenip danışman onayı
> almadan** kullanılmamalıdır (aşağıdaki [Bilinen sınırlar](#bilinen-sınırlar)).
> Geliştirme planı `docs/steps.md`, ilerleme durumu `progress.md`, yöntem↔kod
> eşlemesi `docs/PROTOKOL.md`, operatör el kitabı `docs/OPERATOR_SOP.md`.

## Depo yapısı

| | `mcgurk/` (yeni platform) | `legacy/` (Adım 0, donmuş) |
|---|---|---|
| Durum | Tek çalışan platform | Tarihsel referans — çalıştırılmaz, test edilmez |
| Giriş | `python main.py` / `python -m mcgurk.ui` | `legacy/main.py` (koşulmaz) |
| Config | `config/experiment.yaml` | `legacy/config.yaml` |
| Veritabanı | `data/mcgurk.sqlite` | `data/mcgurk.db` (eski, gitignore) |
| PsychoPy | `config/`, `db/`, `stimuli/` katmanlarında **yasak** | — |

`config/` ve `db/` katmanları PsychoPy'siz çalışır (CI'da ve analiz makinesinde),
bu yüzden PsychoPy oralarda yasaktır ve bir test bunu her koşuda doğrular.

---

## Ne yapar

Katılımcıya görsel-işitsel konuşma uyaranları sunar, yanıt ve tepki süresini
psikofizik hassasiyetinde kaydeder. **Altı değerlendirme modülü** vardır
(yöntem↔kod eşlemesi: `docs/PROTOKOL.md`):

| Modül | İçerik | Ana bağımlı değişkenler | Doğru cevap? |
|---|---|---|---|
| `mcgurk` | Uyumlu/uyumsuz heceler (fonem düzeyi) | Füzyon, görsel baskınlık, işitsel yanıt oranı, RT | **Hayır** — algı kategorisi |
| `avsr` | A-only / V-only / AV | Doğruluk, görsel fayda (AV−A), lipreading | Evet |
| `tbw` | −300…+300 ms SOA, eşzamanlılık yargısı | TBW genişliği, PSS | **Hayır** |
| `oddball` | İşitsel dikkat kontrolü (ton akışı) | Hedef doğruluğu, RT, d′ | Evet (kovaryat) |
| `dichotic` | Her kulağa farklı hece | Kulak avantajı indeksi (KAİ) | **Hayır** |
| `gin` | Gürültüdeki boşluk saptama | Saptama eşiği | Evet |

`mcgurk` ve `avsr` iki manipülasyon taşır: **gürültü** (sessiz / +5 dB SNR
konuşma şekilli gürültü) ve **uzamsal yön** (sağ / sol kulak) — SSD hipotezini
taşıyan değişkenler. Ayrıca oturum akışında **alıştırma** ve (SSD'de) **çapraz
dinleme geçerlilik kontrolü** vardır; bunlar ölçüm modülü değildir.

> **Dikotik ve GIN yöntem dokümanında henüz yoktur** — §6.5/§6.6 taslakları
> danışman onayı bekliyor (`docs/EK_*.docx`). Protokole eklenmeden verileri
> kullanılmamalıdır.

---

## Kurulum

**Python 3.10 gerekir.** Pinlenmiş `psychopy==2026.1.2` yalnızca 3.9–3.11
aralığını destekler; 3.12 ve üstünde pip bu sürümü bulamaz ve sessizce
2023 sürümlerine düşmeye çalışır.

```bash
conda create -n mcgurk python=3.10
```

`conda activate` bir shell fonksiyonudur ve kabuk başına bir kez
başlatılmalıdır. Daha önce yapmadıysanız (PowerShell için; Git Bash'te
`conda init bash`):

```bash
conda init powershell
```

**Ardından terminali kapatıp yeniden açın.** Bu adım atlanırsa `conda
activate` hata vermeden hiçbir şey yapmaz ve kurulum base ortamına gider.

```bash
conda activate mcgurk
```

**Kurulumdan önce doğru yorumlayıcıda olduğunuzu doğrulayın:**

```bash
python -c "import sys; print(sys.version.split()[0], sys.executable)"
```

Çıktı `3.10.x` ile başlamalı ve yol `envs\mcgurk` içinde olmalı. `3.12`/`3.13`
görüyorsanız ortam aktive olmamıştır — bu durumda kurulum base ortamına gider
ve `No matching distribution found for psychopy==2026.1.2` hatası alırsınız.

```bash
pip install -r requirements.txt
```

Geliştirme ve test araçları için ek olarak:

```bash
pip install -r requirements-dev.txt
```

> **Hem Anaconda hem Miniconda kuruluysa dikkat.** `conda activate <isim>`
> yalnızca `envs_dirs` listesindeki dizinlerde arar (`conda config --show
> envs_dirs`). Diğer kurulumun ortamları `conda env list` çıktısında **isimsiz**
> görünür ve isimle aktive edilemez. Ortamı arama yoluna ekleyin:
>
> ```bash
> conda config --append envs_dirs C:\Users\tayla\miniconda3\envs
> ```
>
> Alternatif olarak tam yolla aktivasyon her koşulda çalışır:
>
> ```bash
> conda activate C:\Users\tayla\miniconda3\envs\mcgurk
> ```

**Sürümler pinlidir.** Aylarca sürecek bir psikofizik çalışmasında PsychoPy
veya ses/video yığınında sessiz bir ara sürüm değişikliği zamanlamayı hiçbir
hata vermeden kaydırabilir. Pinleri gevşetmeyin.

### Uyaranlar

Ham kayıtlar (`assets/`) ve hazırlanmış set (`stimuli/`) depoya dâhil değildir
(`.gitignore`). Ham kayıt `assets/speaker_{id}_{cinsiyet}/Vis-{hece}_Aud-{hece}.mp4`
desenindeki **uyumlu** çekimlerdir; hangi klasörün hangi `speaker_id` olduğu
`config/experiment.yaml` → `stimulus_prep` bölümünde yazılıdır. Sekiz konuşmacı
hazırdır (dördü kadın, dördü erkek); oturumda **biri** kullanılır, yani konuşmacı
sayısı deneme sayısını değil seçeneği büyütür. Ayrıntı:
[docs/KONUSMACI_DEGISTIRME.md](docs/KONUSMACI_DEGISTIRME.md).

Teslim edilen ham kayıtlar `Vis-<g>_Aud-<s>_Speaker-<n>.mp4` desenli düz bir
klasördeyse `python tools/import_speakers.py` yalnız uyumlu takeleri config'in
gösterdiği klasörlere ayıklar; var olan ve **aynı** hedefi atlar, **farklı**
hedefte durur.

### Hazırlanmış uyaran seti (`stimuli/`)

`assets/` ham kayıttır ve **doğrudan sunulmaz**. Platform `stimuli/` altındaki
**hazırlanmış** seti kullanır: sessiz sabit kare hızlı video, patlama anına
hizalanmış ve eşit seviyeye getirilmiş 48 kHz 24-bit ses, konuşma şekilli
gürültü, gürültülü türevler, dikotik çiftler, GIN gürültü segmentleri ve
oddball tonları. Hepsi **çevrimdışı** üretilir (§A.12: çalışma anında DSP yok).

```bash
python tools/prepare_stimuli.py            # ilk üretim
python tools/prepare_stimuli.py --force    # mevcut setin üzerine yaz
python tools/verify_stimuli.py             # denetle (çıkış kodu 0/1)
```

Üretim `config/experiment.yaml` → `stimulus_prep` bölümünden okunur; hangi
klasörün hangi `speaker_id` olduğu orada yazılıdır. Çıktının yanında
`stimuli/manifest.json` durur: her dosyanın sağlama toplamı, süresi, ölçülen
patlama anı, seviyesi ve kaynağı. Adım 3 sesi ekranın flip saatine karşı bu
patlama anına göre planlayacak, Adım 8'in kontrol listesi de setin eksiksiz
olduğunu buradan doğrulayacak.

Tolerans dışı her durum **hata verip çıkar** — yarım hazırlanmış bir set
dışarıdan tam görünür. `verify_stimuli.py` diskteki dosyaları manifest'e
*yeniden ölçerek* karşılaştırır; setin makineler arasında kopyalanması veya
elle düzenlenmesi bu yüzden yakalanır.

Uyaran seti ve `assets/` depoya dâhil değildir (`.gitignore`).

### Monitör profili (ilk kurulumda bir kez)

```bash
python scripts/setup_monitor.py
```

---

## Çalıştırma

Tam oturum (yeni platform):

```bash
python main.py
```

Bu, `python -m mcgurk.ui` ile aynıdır. Geliştirme/kısaltma seçenekleri:
`--limit N` (modül başına ilk N deneme), `--db PATH`, `--device NAME`,
`--new-session` (yarım oturum devam teklifini atla).

**Konuşmacı seçimi panelde** (Adım 12c-ii). Operatör panelindeki **"Konuşmacı"**
sekmesi sekiz konuşmacıyı **fotoğraflarıyla** gösterir; hangisi seçiliyse o
tiklidir, yanında bugüne kadar kaç oturumda kullanıldığı yazar. **Konuşmacıyı
kaydet** seçimi `config/experiment.yaml`'a yazar (yorumlar korunur, geçersiz
sonuç geri alınır) ve bundan sonraki oturumlar o yüzü kullanır. Bir katılımcının
bütün modülleri **aynı** konuşmacıyla ölçülmelidir; konuşmacı oturum başına
sorulmaz, çünkü oturumun değil kurulumun özelliğidir.

Fotoğraflar hazırlanmış setten gelir (`stimuli/thumbnails/speaker_<id>.png`,
kaydın kendi çözünürlüğünde); `prepare_stimuli.py` üretir, `verify_stimuli.py`
eksiğini KIRMIZI verir.

**Oturum kurulum menüsü** (Adım 12). Girişten sonra, tam ekran pencere açılmadan
önce çıkar ve **modülleri** sorar: her ölçüm modülü için bir onay kutusu (yanında
deneme sayısı), **alıştırma** ve **çapraz dinleme kontrolü**. Katılımcı kodu ve o
oturumun konuşmacısı üstte **salt okunur** görünür. Menü **önceden dolu gelir** —
tam tasarım — yani hiçbir şeye dokunmadan onaylamak eskisiyle aynı oturumu koşar.
İptal edilirse oturum başlamaz.

Katılımcı daha önce **başka bir konuşmacıyla** ölçüldüyse oturum başlarken uyarı
çıkar; onaylanmazsa oturum başlamaz (değişiklik panelden yapılır). Seçim
`operator_notes`'a da yazılır. **Devam (resume) ettirilen oturumda menü çıkmaz** —
o oturumun tasarımı kendi snapshot'ında.

Komut satırından: `--modules mcgurk,dichotic`, `--no-practice`,
`--no-cross-hearing` menüyü **önceden doldurur**; `--no-ask` menüyü hiç
göstermeden o seçimi koşar. `--speaker N` konuşmacıyı yalnız o koşu için ezer
(config'e yazmaz) — normal yol paneldeki sekmedir.

Seçim **config'e uygulanır**: seçilmeyen modüller `enabled: false`,
`session.module_order` kısaltılmış ve konuşmacı sabitlenmiş hâldeki tasarım
oturumun `config_snapshot`'ına yazılır. Devam (resume) ettirilen bir oturum
kendi snapshot'ıyla koşar ve seçim yok sayılır. Yanlış yazılmış bir modül adı
ya da hazır olmayan bir konuşmacı, katılımcı ekrana oturmadan **komut satırında**
hata verir.

Akış: katılımcı girişi → (yarım oturum varsa) devam teklifi → **oturum kurulumu
(konuşmacı + modüller)** → oturum öncesi kontrol onayı → alıştırma → her modül
yönergesiyle → molalar → çapraz dinleme (SSD) → bitiş + yedek. Oturum yarıda kalırsa aynı katılımcıyla **kaldığı yerden
devam** edilebilir (tamamlanan modüller atlanır).

`ESC` **her aşamada** çalışır (uyaran sunumu dâhil) ve "çıkmak istediğinize emin
misiniz?" onayı sorar. Onaylanırsa oturum veritabanında `aborted` işaretlenir,
o ana kadarki denemeler korunur, yedek yazılır ve çıkış kodu `2` döner.

Oturum öncesi kontrol (operatör): `python -m mcgurk.checklist`.

> **SDL2 uyarısı.** `MovieStim` her oluşturulduğunda PsychoPy
> `Using \`sdl2\` for audio playback via \`ffpyplayer\`` uyarısı üretir
> (sebebi aşağıda). Uyarı zararsızdır — verilen dosyada ses akışı yoktur — ve
> yalnızca oluşturma anında bastırılır. Bastırma dar tutulmuştur: sunum
> sırasındaki düşen kare uyarıları gibi tanısal mesajlar operatöre ulaşmaya
> devam eder.

---

## Veri

SQLite: `data/mcgurk.sqlite` (config'ten `database.path` ile değiştirilebilir).

**KVKK:** Ad, soyad ve doğum tarihi hiçbir yere yazılmaz. Katılımcı yalnızca
anonim bir kodla (`SSD-R-007` gibi) tanımlanır. Kod ↔ kimlik eşleşme dosyası
bu depoda tutulmaz ve bulut senkronizasyonuna konulmaz. Ad-soyad sütunu içeren
eski bir veritabanı dosyası açılmaya çalışılırsa program **açık hatayla durur**,
sessizce devam etmez.

Şema (sürüm 5) altı tablo ve analiz için düz bir `VIEW` içerir:

- `participants` — anonim kod, grup (`SSD_R`/`SSD_L`/`CTRL`), yaş, cinsiyet,
  **deprivasyon süresi**, PTA sağ/sol, postlingual bayrağı
- `calibrations` — `02_kalibrasyon.md` çıktısı, dosyanın kendisi de saklanır
- `sessions` — seed, **config anlık görüntüsü**, git commit, PsychoPy/Python
  sürümü, işletim sistemi, ses backend'i, ölçülen yenileme hızı,
  `system_av_offset_ms`, durum
- `blocks` — modül, blok sırası, planlanan deneme sayısı, durum
- `trials` — ortak tasarım alanları + gerçekleşen zamanlama; modüle özgü
  alanlar `design_extra` (JSON) içinde, `mcgurk/db/design.py` ile doğrulanır
- `responses` — deneme başına **0..n** satır: zaman aşımında hiç, GIN
  segmentinde birden fazla. `event_index` (şema sürümü 4, Adım 7c) yanıtın
  denemenin **içindeki hangi olaya** ait olduğunu söyler — GIN'de segmentteki
  boşluğun sırası; başka her modülde deneme zaten olayın kendisi olduğu için
  NULL
- `v_trials_flat` — hepsini birleştiren düz tablo; `design_extra` anahtarları
  sütun olarak açılır, analiz tarafında JSON görünmez. Sürüm 5'te (Adım 9a)
  `cross_hearing_signal_present` sütunu da açılır — çapraz dinleme QC'sinin
  sinyal denemesini yakalama denemesinden ayırması için

Veritabanı `mcgurk`, `dichotic` ve `tbw` denemelerinde `is_correct` yazılmasını
**tetikleyiciyle reddeder** — §A.10 depolama katmanında da geçerlidir.

### Analiz ve dışa aktarım (`mcgurk/analysis/`, Adım 9)

Analiz katmanı PsychoPy gerektirmez; `v_trials_flat` görünümünü ve her oturumun
**config anlık görüntüsünü** okur. Bir oturumun sayıları, o oturumun kendi
tasarımının ürettiği sayılardır — sonradan `config/experiment.yaml` değişse bile.

Oturum başına modül ölçütleri (McGurk oranları, AVSR fayda indeksi, TBW PSS/genişlik,
oddball d′, dikotik KAİ, GIN eşiği):

```bash
python tools/analyse.py            # tüm oturumlar
python tools/analyse.py --session 3
```

Düz dosyaya aktarım (analiz ortamına — R/Python). CSV her zaman; **parquet
yalnız `pyarrow` kuruluysa** (yoksa uyarıp atlar):

```bash
python tools/export_data.py --out data/export --format both
```

Kalite kontrol raporu — düşen kare, SOA sapması, zaman aşımı oranı, yanıt
dağılımı, **nesnel olarak işaretlenen bozuk denemeler** ve (SSD) çapraz dinleme
geçerlilik yargısı (tek yönlü binomial, `config.qc`):

```bash
python tools/qc_report.py --session 3
```

QC eşikleri (`config.qc`: `max_dropped_frames`, `soa_tolerance_ms`,
`cross_hearing_alpha`) **oturum anlık görüntüsüyle taşınır** — bir oturum kendi
snapshot'ındaki eşiklerle değerlendirilir. Bunlar veri toplamadan önce sabit,
danışman onayına açık geçici değerlerdir.

### Yedekleme

`data/`, `backups/`, `logs/`, `stimuli/` ve `raw_recordings/` git dışıdır.

Yedekler `VACUUM INTO` ile alınır, **ham dosya kopyası kullanılmaz**: WAL
modunda `.sqlite` dosyasının tek başına kopyalanması son commit'leri eksik,
sessizce tutarsız bir kopya üretir. Her oturum kapanışında otomatik alınır
(kesilen oturumda da).

Bir yedeği doğrulamak — test edilmemiş yedek yedek değildir:

```bash
python tools/verify_backup.py backups/mcgurk_20260726T153149.sqlite --compare-with data/mcgurk.sqlite
```

Çıkış kodu `0` yedek kullanılabilir, `1` güvenilir değil demektir.

**3-2-1 kuralı:** verinin **3** kopyası, **2** farklı ortamda, **1**'i farklı
fiziksel konumda. Pratikte: çalışma makinesindeki `data/`, aynı makinedeki
`backups/`, ve **haftalık** olarak harici bir diske alınan kopya. 12 aylık bir
çalışmada tek makine kabul edilemez risktir.

**KVKK sınırı:** kod ↔ kimlik eşleşme dosyası bulut senkronizasyonuna
konulmaz ve yedeklerle aynı yerde tutulmaz.

### Doğru cevap olmayan denemeler

`mcgurk` ve `dichotic` bölümlerinde doğru cevap **yoktur**. Bu denemelerde
`is_correct` sütunu `NULL` yazılır ve doğruluk hesaplarının dışında tutulur.
Uyumsuz bir uyaranda "yanlış cevap" saymak kategori hatasıdır: Vis-/ga/ +
Aud-/ba/ karşısında "DA" yanıtı klasik füzyondur, hata değil.

Bitiş ekranı katılımcıya başarı yüzdesi göstermez — bir algı görevinde
performans geri bildirimi vermek talep karakteristiği yaratır.

---

## Zamanlama mimarisi

`MovieStim` (ffpyplayer) gömülü sesi SDL2 üzerinden çalar ve bu Windows'ta
belirgin gecikme yaratır; `prefs.hardware['audioLatencyMode']` bu yolu
etkilemez. Bu yüzden:

1. Videodan ffmpeg ile **sesi tamamen sökülmüş** bir kopya üretilir ve
   `MovieStim` yalnızca bunu oynatır. Bu bir tercih değil zorunluluk:
   PsychoPy 2026.1'de `MovieStim.__init__` çağıranın `noAudio` argümanını
   koşulsuz eziyor (`self._noAudio = False`) ve SDL2 dışında bir `audioLib`
   verilirse `MovieAudioError` fırlatıyor. SDL2'yi susturmanın tek yolu
   dosyada ses akışı bırakmamak. `tests/test_silent_video.py` bunu doğrular.
2. Ses ayrı bir WAV olarak çıkarılır ve **Psychtoolbox** backend'i üzerinden
   `Sound.play(when=win.getFutureFlipTime(clock="ptb"))` ile ekranın flip
   saatine karşı zamanlanır.
3. Backend gerçekten `ptb` değilse program **başlamaz** — sessiz geri düşüş
   yoktur.

**Gösterilecek bir şeyin olmadığı denemelerde video hiç oluşturulmaz.** AVSR'nin
A-only modunda, dikotikte, oddball ve GIN akışlarında ekranda yalnızca sabitleme
haçı kalır ve deneme sesin kendi süresi kadar sürer. Aksi hâlde denemenin bitiş
anı — yani RT referanslarından biri — bir video akışının kare ızgarasına bağlı
olurdu.

> PsychoPy 2026.1 backend seçimini `prefs.hardware['audioLib']` yerine
> `sound.Sound.backend` sınıf niteliğine taşıdı; `sound.audioLib` artık
> mevcut değil. Kod her ikisini de ayarlar ve sonucu çalışma öncesinde
> doğrular.

### Sunum motoru (`mcgurk/engine/`)

Sessiz video ve hizalanmış WAV `stimuli/` altında çevrimdışı hazırdır (Adım 2),
bu yüzden motorun işi çalışma anında yalnızca zamanlamadır (§A.12: çalışma
anında ağır DSP yok):

| Katman | İş | PsychoPy |
|---|---|---|
| `scheduling.py` | Pay hesabı, ses planlama anı, gerçekleşen SOA, kare istatistiği | **Hayır** — CI'da test edilir |
| `audio.py` | Lateralizasyon, kalibrasyon trim'i, PTB kapısı, aygıt açma | Yalnızca `Sound` için |
| `window.py` | Pencere, ölçülen yenileme hızı, kare aralığı kaydı | Evet |
| `av_presenter.py` | `TrialSpec` → sunum → `TimingRecord` | Evet |

**Pay (lead) denemeye göre hesaplanır.** Video yalnızca yenileme ızgarasında
başlayabilir, ses örnek hassasiyetinde planlanır; bu yüzden **tüm SOA
manipülasyonu ses tarafındadır** ve flip hedefi yalnızca yer açmak için
ileri itilir. Config'in `lead_frames: 6` değeri 60 Hz'de 100 ms eder ve
TBW'nin −300 ms'i için yetmez, o yüzden taban değerdir: gereken pay her
denemede `|SOA − D|` üzerinden yeniden hesaplanır. Hesaplanan pay 1 saniyeyi
aşarsa deneme **hata verir** — sessizce uzatılmaz.

**`trials.actual_soa_ms` katılımcının yaşadığı SOA'dır**, yani yazılımda
ölçülen fark artı uygulanan `system_av_offset_ms` telafisi. Böylece nominal
ile doğrudan karşılaştırılabilir; ham yazılım farkı
`actual_soa_ms − sessions.system_av_offset_ms` ile geri hesaplanır. Fark iki
akışın **akustik patlama anları** arasında ölçülür, dosya başlangıçları
arasında değil — hazırlanmış dosyalardaki kalıntı hizalama hatası (< 1 ms)
böylece varsayılmak yerine kayda giriyor.

**Ses onset'i "ölçülmüyor", bildiriliyor.** PsychPortAudio'nun `StartTime`
alanı bu makinede (WASAPI, gecikme sınıfı 3) istenen zamanın **birebir
aynısıdır** — aygıt çıkış damgası vermediği için PTB'nin bildirecek başka bir
şeyi yok. Kayda giren değer budur ve `TimingRecord.audio_onset_reported` bunun
bir ölçüm olmadığını söyler. Onset'i gerçekten doğrulayan şey fiziksel
ölçümdür: `tools/timing_selftest.py --level 2` (jitter) ve fotodiyot (mutlak
gecikme).

> PsychoPy 2026.1'de `prefs.hardware['audioLatencyMode']` **tercih şemasından
> kaldırıldı**; gecikme sınıfı artık `SpeakerDevice(latencyClass=...)`
> argümanı ve varsayılanı 1. Config'teki `timing.audio_latency_mode` bu yüzden
> `audio.open_speaker()` içinde uygulanıyor. Eski tercih anahtarını yazmak
> hata vermez, sessizce yok sayılırdı.

Aygıtın akış hızı `audio.sample_rate` ile karşılaştırılır ve tutmazsa program
durur: PsychoPy aksi hâlde her uyaranı yükleme anında yeniden örnekler ve
setin 48 kHz'de hazırlanmış olması anlamını yitirirdi.

### Yeniden üretilebilirlik

Deneme sırası tohumlanmış bir RNG ile karıştırılır ve tohum oturum kaydına
(`sessions.seed`) yazılır. Her modülün tohumu bu oturum tohumundan **modüle özgü**
türetilir, tek akış değildir. Bir oturumun sırasını birebir yeniden üretmek için
`config/experiment.yaml` içindeki `seed` alanına o oturumun tohumunu yazın.

---

## Geliştirme

```bash
pytest
```

```bash
ruff check .
```

```bash
mypy
```

Üçü de temiz olmadan bir adım kapatılmaz (`docs/steps.md` §B.2).

Ekran veya ses aygıtı gerektiren testler `psychopy` işaretini taşır. Yalnızca
donanımsız olanları koşmak için:

```bash
pytest -m "not psychopy"
```

Bu, GitHub Actions'ın koştuğu komuttur — CI'da PsychoPy hiç kurulu değildir.
`tests/mcgurk/test_package_boundaries.py` bunun bozulmadığını doğrular:
`mcgurk/config`, `mcgurk/db` ve `mcgurk/stimuli` altında PsychoPy import'u
testle yasaklıdır.

ffmpeg ikilisi gerektiren uyaran testleri `ffmpeg` işaretini taşır ve ikili
yoksa kendilerini atlar. Ölçüm fonksiyonlarının kendisi (patlama tespiti,
seviye, SNR, GIN boşluk yerleşimi) sentetik sinyallerle test edilir ve her
yerde koşar — gerçek korpusa karşı test etmek yalnızca korpusun kendisiyle
tutarlı olduğunu söylerdi.

### Tasarımın maliyetini görmek

Config'i doğrulamak ve deneme sayısı / süre tahminini almak:

```bash
python -m mcgurk.config
```

Deneme sayısı kararı (`docs/steps.md` §F.1) bu çıktıya bakılarak verilecek.

### Zamanlamayı doğrulamak

Önce çıkış aygıtını seçin. `audio.device: null` bırakılırsa PTB **bulduğu ilk
aygıtı** kullanır; bu, hiçbir şeyin bağlı olmadığı bir SPDIF portu da olabilir
(sessizlik), monitörün hoparlörü de (sessizlik değil, daha kötüsü):

```bash
python tools/timing_selftest.py --devices
```

Yazılım tarafı (backend, yenileme ızgarası, ses planlama) — her makinede
koşar, donanım gerektirmez:

```bash
python tools/timing_selftest.py --level 1
```

Hazırlanmış uyaranlarla altı gerçek deneme sunar ve gerçekleşen zamanlamayı
basar (AV, ±200 ms SOA, A-only, V-only, lateralize):

```bash
python tools/timing_selftest.py --demo
```

Loopback jitter ölçümü (bir kablo gerektirir) ve fotodiyot yönergesi:

```bash
python tools/timing_selftest.py --level 2 --play
```

```bash
python tools/timing_selftest.py --level 3
```

Kademe 3 bu araçta gerçeklenmez; `docs/01_av_gecikme_olcumu.md` scriptleriyle,
**tüm kod bittikten sonra** bir kez yapılır.

### Bir modülü tek başına koşmak (geliştirme aracı)

Tam oturum `python main.py` iledir; tek bir modülü izole koşmak (geliştirme,
kontrol, kısa demo) için `tools/run_module.py` vardır. Koşulabilen modüller:
`mcgurk`, `avsr`, `tbw`, `oddball`, `dichotic` ve `gin`. GIN tek kulaklıdır ve
hangi kulağın test edileceği katılımcıya bağlı olduğu için koşuya
`--ear right|left` eklenmesi gerekir.
Önce tasarımı donanım açmadan denetleyin — deneme sayısını config'in hesabıyla
karşılaştırır, hücre tablosunu basar ve her uyaran dosyasının yerinde olduğunu
doğrular:

```bash
python tools/run_module.py --module avsr --dry-run
```

Sonra gerçek koşu. `--limit` kısa bir kontrol için, `--seed` sırayı tekrar
üretmek için:

```bash
python tools/run_module.py --module avsr --limit 12 --seed 3
```

AVSR koşusunun sonunda modülün kendi ölçütleri de basılır: mod başına
doğruluk, görsel fayda indeksi (AV - A) ve lipreading (V). TBW koşusunun
sonunda psikometrik fonksiyon (SOA başına "aynı" oranı), uydurulan PSS, sigma
ve pencere genişliği ile bootstrap güven aralıkları basılır. Kısa bir `--limit`
koşusunda uydurma **yapılamaz** ve bunu açıkça söyler: SOA başına birkaç yanıt
eğriyi kestirmeye yetmez.

Oddball koşusu diğerlerinden farklı görünür: yanıt ekranı yoktur, ekranda
yalnızca sabitleme haçı durur ve tonlar kendi saatlerine göre akar. Sonunda
sinyal tespiti tablosu basılır — isabet, kaçırma, yanlış alarm, doğru ret,
d′, kriter ve isabet RT'si. Pencere dışında kalan tuş basımları ayrı sayılır:
kaydedilirler ama hiçbir orana girmezler.

Dikotik koşuda video yoktur: iki kulağa aynı anda farklı hece gelir ve ekranda
yalnızca sabitleme haçı durur. Sonunda kulak başına bildirim oranı, karışım
yanıtı oranı ve kulak avantajı indeksi (KAİ = [(Sağ - Sol) / (Sağ + Sol)] x 100)
basılır. Doğru cevap yoktur; yanıtsız deneme indekse girmez, ayrıca sayılır.

GIN koşusu da bir akıştır: altı saniyelik geniş bantlı gürültü segmentleri tek
kulaktan akar, içlerine 2–20 ms sessiz boşluklar yerleştirilmiştir ve katılımcı
boşluk duydukça tuşa basar. Bir segment birden çok boşluk taşıyabildiği için
deneme başına 0..n yanıt olabilir; hangi boşluğun saptandığı `responses.event_index`
ile kaydedilir. Sonunda süre başına saptama oranı, boşluk saptama eşiği (4/6
ölçütünü sağlayan en kısa süre) ve yanlış alarm sayısı basılır — eşik her zaman
yanlış alarmla birlikte, çünkü çok basan biri kısa boşlukları şansla yakalar.

Bu bir **geliştirme aracıdır**: yönerge, alıştırma bloğu, mola ve katılımcı
girişi yok, veritabanına `DEV01` kodlu bir geliştirme katılımcısı yazıyor.
Gerçek oturum akışı `python main.py` (`mcgurk/ui/`) ile koşulur.

Kod, değişken adları ve docstring'ler İngilizce; katılımcıya ve operatöre
gösterilen metinler Türkçedir.

---

## Bilinen sınırlar

Kod tarafı özünde tamam; aşağıdakiler **veri toplamadan önce** kapanması gereken
kod dışı işler ve bilinçli açık uçlardır. Tam liste `progress.md` → *Açık
kararlar* ve *Kullanıcıya bekleyen aksiyonlar*.

**Veri toplamayı engelleyen kapılar (kod dışı):**
- **Fotodiyot A/V gecikme ölçümü** (`docs/01_av_gecikme_olcumu.md`) yapılmadı.
  O ana kadar `timing.system_av_offset_ms` `null` ve motor 0 kabul edip uyarı
  basar. `data_collection` modu bu ölçüm olmadan başlamaz.
- **Ses kalibrasyonu** (`docs/02_kalibrasyon.md`) yapılmadı; mutlak SPL
  bilinmiyor. `data_collection` modu kalibrasyon dosyası olmadan başlamaz.
- **Prova oturumu** (gerçek kişiyle, SOP takip edilerek) koşulmadı — otomatik
  uçtan uca test bunun yerine geçmez.
- **Kulaklık tipi (§F.3):** test kulaklığı (Bluetooth) veri toplama için uygun
  değil (değişken gecikme, kendi DSP'si, düşük kulaklar arası zayıflama). SSD
  lateralizasyonu için insert kulaklık gerekebilir. Çapraz dinleme kontrolü bu
  yüzden kodda hazır ve her SSD katılımcısında çalışır.

**Protokol kapıları (danışman):**
- **Dikotik ve GIN yöntem dokümanında henüz yok.** §6.5/§6.6 taslakları hazır
  (`docs/EK_DIKOTIK_DINLEME.docx`, `docs/EK_GIN.docx`) ve danışman onayı bekliyor;
  protokole eklenmeden bu iki modülün verisi kullanılmamalı.
- **Deneme sayıları (§F.1)** config'ten geliyor (geçici minimumlar); danışman
  yükseltebilir. `python -m mcgurk.config` tahmini süreyi basar.
- **QC eşikleri ve çapraz duyma α'sı** (`config.qc`) geçici; danışman onaylamalı.

**İçerik/özellik açık uçları:**
- **AVSR kelime seti** (`type: word`) içerik olarak **boş**: kayıt seansı
  yapılmadı (§F.2). Şema ve okuyucu hazır (`config/word_lists/`), liste şablon
  hâlinde. `enabled: true` yapılırsa config yüklenirken açık hata verir.
- **AVSR `response_mode: open_set`** tanımlı ama gerçeklenmedi; seçilirse
  `NotImplementedError`. Açık set puanlama kuralları karara bağlanmadı.

**Hazırlanmış set:** kaynaklar kayıpsız değil. Depoda ham kayıt yok (A0-3), bu
yüzden `stimuli/` 44.1 kHz AAC'den türetiliyor; 48 kHz / 24 bit kaynağa
hassasiyet eklemez, yalnızca sonraki işlemlerin kuantalama gürültüsü
biriktirmesini engeller. Yeni bir çekim yapılırsa aynı boru hattı kayıpsız
kaynakla daha iyisini üretir — kod değişmez. Manifest her dosyanın kaynak
codec'ini kaydeder.

**Ortam:**
- `ffmpeg` PATH'te yoksa `imageio-ffmpeg` ile gelen ikili kullanılır. `ffprobe`
  bu pakette **yoktur**; uyaran araçları bu yüzden `ffprobe` kullanmaz, akış
  bilgisini `ffmpeg -i` çıktısından okur. Ayrı bir kurulum gerekmez.
- Ses aygıtı **adları** config'te sabittir, indeksleri değil (Bluetooth kulaklık
  kapalıyken listeye hiç girmez). Listelemek için:
  `python tools/timing_selftest.py --devices`.

---

## Lisans

Bkz. [LICENSE](LICENSE).
