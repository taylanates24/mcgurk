# McGurk / SSD Değerlendirme Platformu

Tek taraflı işitme kaybı (SSD) olan yetişkinlerde görsel-işitsel konuşma
entegrasyonunun davranışsal değerlendirmesi için geliştirilen PsychoPy tabanlı
deney platformu.

**Proje:** Atılım Üniversitesi Odyoloji Bölümü, etik kurul onaylı, 12 aylık
klinik çalışma. Katılımcılar: 20 sağ SSD + 20 sol SSD + 20 kontrol.

> **Durum: Adım 8 (oturum akışı) tamamlandı.** Platform artık `mcgurk/` yeni
> paketidir ve tam bir oturumu baştan sona koşar: `python main.py`
> (= `python -m mcgurk.ui`). Adım 0'ın `src/` ağacı emekliye ayrıldı ve
> `legacy/` altında donduruldu (bkz. `legacy/README.md`). Sırada arayüz cilası
> + danışman gösterimi (Adım 8.5) ve analiz/dışa aktarım (Adım 9) var. Bu depo
> henüz veri toplamaya hazır değildir — fotodiyot ölçümü ve ses kalibrasyonu
> bekliyor (aşağıdaki [Bilinen sınırlar](#bilinen-sınırlar)). Geliştirme planı
> `docs/steps.md`, ilerleme durumu `progress.md`.
>
> Bu README'nin bir kısmı hâlâ eski `src/` tasarımını anlatıyor; tam yenileme
> Adım 9'da yapılacak.

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
kaydeder. Beş bölüm vardır:

| Bölüm | İçerik | Doğru cevap var mı? |
|---|---|---|
| `mcgurk` | Uyumsuz (görsel ≠ işitsel) heceler | **Hayır** — algı kategorisi ölçülür |
| `av_congruent` | Uyumlu (görsel = işitsel) heceler | Evet |
| `audio_only` | Yalnızca ses | Evet |
| `visual_only` | Yalnızca görüntü (dudak okuma) | Evet |
| `dichotic` | Her kulağa farklı hece | **Hayır** — hangi kulağın duyulduğu kaydedilir |

Her bölüm sessiz ve gürültülü koşulda çalıştırılabilir.

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

Video uyaranları depoya dâhil değildir (`.gitignore`). `assets/` şu yapıda
olmalıdır:

```
assets/
├── female_speaker_1/          Vis-{hece}_Aud-{hece}.mp4
├── male_speaker_1/
├── dichotic/{konuşmacı}/      Left-{hece}_Right-{hece}.wav
└── noise/                     {tür}_noise.mp3
```

Konuşmacılar çalışma anında `{cinsiyet}_speaker_{n}` desenine göre taranır —
yeni bir klasör eklemek yeterlidir, kod veya config değişikliği gerekmez.

Dikotik uyaranlar uyumlu videolardan türetilir ve depoya dâhil değildir:

```bash
python scripts/generate_dichotic_stimuli.py
```

### Hazırlanmış uyaran seti (`stimuli/`, yeni paket)

`assets/` ham kayıttır ve doğrudan sunulmaz. Yeni paket `stimuli/` altındaki
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

Akış: katılımcı girişi → (yarım oturum varsa) devam teklifi → oturum öncesi
kontrol onayı → alıştırma → her modül yönergesiyle → molalar → çapraz dinleme
(SSD) → bitiş + yedek. Oturum yarıda kalırsa aynı katılımcıyla **kaldığı yerden
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

SQLite: `data/mcgurk.db` (config'ten değiştirilebilir).

- `participants` — **anonim kod**, yaş, cinsiyet, grup, notlar
- `sessions` — konuşmacı, çalıştırılan bölümler, **RNG seed**, durum
  (`running` / `completed` / `aborted`)
- `trials` — tasarım alanları, ham yanıt, iki RT referansı, `is_correct`

**KVKK:** Ad, soyad ve doğum tarihi hiçbir yere yazılmaz. Katılımcı yalnızca
anonim bir kodla (`SSD-R-007` gibi) tanımlanır. Kod ↔ kimlik eşleşme dosyası
bu depoda tutulmaz ve bulut senkronizasyonuna konulmaz.

Ad-soyad sütunu içeren eski bir veritabanı dosyası açılmaya çalışılırsa program
**açık hatayla durur**, sessizce devam etmez.

### Yeni paketin veritabanı (`data/mcgurk.sqlite`)

Adım 1'de gelen şema altı tablo ve analiz için düz bir `VIEW` içerir:

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
  sütun olarak açılır, analiz tarafında JSON görünmez

Veritabanı `mcgurk`, `dichotic` ve `tbw` denemelerinde `is_correct` yazılmasını
**tetikleyiciyle reddeder** — §A.10 depolama katmanında da geçerlidir.

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

**Gösterilecek bir şeyin olmadığı bölümlerde video hiç oluşturulmaz.**
`audio_only` ve `dichotic` denemelerinde ekranda yalnızca sabitleme haçı kalır
ve deneme sesin kendi süresi kadar sürer. Bu bölümler eskiden sesi gizlenmiş
bir videonun içinde taşıyordu; bu, denemenin bitiş anını — yani RT
referanslarından birini — video akışının kare ızgarasına bağlıyordu.

> PsychoPy 2026.1 backend seçimini `prefs.hardware['audioLib']` yerine
> `sound.Sound.backend` sınıf niteliğine taşıdı; `sound.audioLib` artık
> mevcut değil. Kod her ikisini de ayarlar ve sonucu çalışma öncesinde
> doğrular.

### Yeni paketin sunum motoru (`mcgurk/engine/`, Adım 3)

`src/` yukarıdaki stratejiyi çalışma anında ffmpeg çağırarak uyguluyor. Yeni
pakette sessiz video ve hizalanmış WAV zaten `stimuli/` altında hazır
(Adım 2), bu yüzden motorun işi yalnızca zamanlama:

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
yazılır. Bir oturumun sırasını birebir yeniden üretmek için `config.yaml`
içindeki `seed` alanına o oturumun tohumunu yazın.

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

### Bir modülü tek başına koşmak (Adım 4→)

Oturum akışı Adım 8'de geliyor; o zamana kadar bir modül `tools/run_module.py`
ile koşuluyor. Koşulabilen modüller: `mcgurk` (Adım 4), `avsr` (Adım 5),
`tbw` (Adım 6), `oddball` (Adım 7), `dichotic` (Adım 7b) ve `gin` (Adım 7c).
GIN tek kulaklıdır ve hangi kulağın test edileceği katılımcıya bağlı olduğu
için koşuya `--ear right|left` eklenmesi gerekir.
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
Gerçek oturum akışı Adım 8'in işi.

Kod, değişken adları ve docstring'ler İngilizce; katılımcıya ve operatöre
gösterilen metinler Türkçedir.

---

## Bilinen sınırlar

Bunlar bilinçli olarak Adım 0 kapsamı dışında bırakıldı; her biri
`docs/steps.md` içinde bir adıma bağlıdır.

**Uyaranlar — `src/` yolunda hâlâ geçerli, `stimuli/` altında çözüldü:**

`src/` doğrudan `assets/` içindeki ham mp4'leri sunar ve aşağıdaki sınırların
tamamını taşımaya devam eder. Adım 2'nin ürettiği `stimuli/` seti bunları
çözer; yeni paket Adım 8'de devralana kadar ikisi yan yana durur.

- Videolar 29.97 fps — 60 Hz ekranda kare başına 2.002 yenileme, periyodik kare
  tekrarı. *(`stimuli/`: 30 fps, sabit kare hızı.)*
- Ses AAC ile sıkıştırılmış ve 44.1 kHz. *(`stimuli/`: 48 kHz 24-bit PCM.)*
- Token'ların akustik patlama anları hizalanmamış, seviyeleri eşitlenmemiş.
  *(`stimuli/`: her ses, birlikte sunulacağı videonun kendi patlama anına
  hizalanır; ölçülen sapma 1 ms'in altında. Seviyeler ortak bir
  konuşma-aktif RMS hedefine getirilir.)*
- SNR karışımı tüm dosya RMS'i üzerinden hesaplanıyor; dosyaların önemli bir
  bölümü sessizlik olduğu için etkin SNR token'a göre değişiyor.
  *(`stimuli/`: konuşma-aktif seviye üzerinden, çevrimdışı.)*
- Gürültü dosyaları kayıplı MP3 ve 44.1 kHz, konuşma şekilli değil.
  *(`stimuli/`: korpusun LTAS'ından üretilen SSN.)*
- Dikotik uyaranlar 48 kHz stereo PCM ama kaynakları AAC.
  *(`stimuli/`: aynı kaynaktan, ama normalize edilmiş ve iki kulak ortak bir
  patlama anına hizalanmış hâlde.)*

**Hazırlanmış sette kalan sınır:** kaynaklar kayıpsız değil. Depoda ham kayıt
yok (A0-3), bu yüzden `stimuli/` 44.1 kHz AAC'den türetiliyor; 48 kHz ve
24 bit kaynağa hassasiyet eklemez, yalnızca sonraki işlemlerin kuantalama
gürültüsü biriktirmesini engeller. Manifest her dosyanın kaynak codec'ini ve
örnekleme hızını kaydeder.

**Zamanlama (Adım 3):**
- Gerçekleşen zamanlama kaydedilmiyor: onset zamanları, düşen kare sayısı,
  maksimum kare süresi, nominal↔gerçekleşen SOA farkı.
- SOA manipülasyonu yok (TBW modülü için gerekli).
- Uzamsal lateralizasyon (sağ/sol kulak) yok — SSD hipotezini taşıyan
  değişkendir.
- `system_av_offset_ms` ölçülmedi (fotodiyot ölçümü, `docs/01_av_gecikme_olcumu.md`).
- Ses kalibrasyonu yapılmadı (`docs/02_kalibrasyon.md`); mutlak SPL bilinmiyor.
- Fixation süresi `core.wait()` ile veriliyor, flip ızgarasına oturmuyor.

**Tasarım ve arayüz — `src/` yolunda geçerli; ilk üçü yeni pakette çözüldü
(Adım 4):**
- Yanıt seti `BA/DA/GA` ile sınırlı; kombinasyon algısı ("bga") ifade
  edilemiyor ve "DİĞER" seçeneği yok. *(Yeni paket: dokuz seçenek, `BGA`/`BDA`
  ve serbest metin dahil, hepsi config'ten.)*
- Füzyon/kombinasyon kategorizasyonu yok. *(Yeni paket:
  `AUDITORY`/`VISUAL`/`FUSION`/`COMBINATION`/`OTHER`/`NONE`, haritalar
  config'ten — §A.9.)*
- Katılımcıya gösterilen metinler hâlâ koda gömülü. *(Yeni paket: McGurk
  modülünün tüm metinleri `modules.mcgurk.prompts` altında; diğer modüller
  Adım 5–7c'de aynı yapıyı alacak.)*
- Deprivasyon süresi ve PTA değerleri toplanmıyor.
- Alıştırma bloğu, molalar, oturum öncesi kontrol listesi ve çapraz dinleme
  kontrolü yok.
- Kesilen oturuma kaldığı yerden devam etme yok.

**Yeni pakette henüz gelmeyenler:**
- `mcgurk/modules/` altı değerlendirme modülünü de içeriyor: McGurk (Adım 4),
  AVSR (Adım 5), TBW (Adım 6), oddball (Adım 7), dikotik (Adım 7b) ve GIN
  (Adım 7c). `ui/` ve `analysis/` hâlâ boş (Adım 8 ve 9).
- Yeni config ve veritabanı henüz hiçbir deneyi çalıştırmıyor; `main.py` Adım
  8'e kadar `src/` yolunu kullanmaya devam ediyor.
- AVSR kelime seti (`type: word`) **içerik olarak boş**: kayıt seansı yapılmadı
  (§F.2). Şema ve okuyucu hazır (`config/word_lists/`), liste dosyası şablon
  hâlinde. `enabled: true` yapılırsa config yüklenirken açık hata verir —
  listenin boş olduğunu, kelimelerin `stimulus_prep.tokens`'a eklenmesi ve
  hazırlanması gerektiğini söyleyerek.
- AVSR'nin `response_mode: open_set` seçeneği tanımlı ama gerçeklenmedi;
  seçilirse `NotImplementedError`. Açık set puanlama kuralları (transkripsiyon,
  kısmi kredi) karara bağlanmadı.
- Dikotik ve GIN modülleri **yöntem dokümanında tanımlı değil** — config ve
  veritabanı yerleri açıldı, ancak protokole eklenmeden veri toplanmamalı.
  İkisi için de taslak bölüm hazır ve danışman onayı bekliyor:
  `docs/EK_DIKOTIK_DINLEME.docx` (yöntem dokümanına 6.5 olarak) ve
  `docs/EK_GIN.docx` (6.6 olarak).

**Ortam:**
- `ffmpeg` PATH'te yoksa `imageio-ffmpeg` ile gelen ikili kullanılır. `ffprobe`
  bu pakette **yoktur**; uyaran araçları bu yüzden `ffprobe` kullanmaz, akış
  bilgisini `ffmpeg -i` çıktısından okur. Ayrı bir kurulum gerekmez.

---

## Lisans

Bkz. [LICENSE](LICENSE).
