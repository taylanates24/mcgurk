# McGurk / SSD Değerlendirme Platformu

Tek taraflı işitme kaybı (SSD) olan yetişkinlerde görsel-işitsel konuşma
entegrasyonunun davranışsal değerlendirmesi için geliştirilen PsychoPy tabanlı
deney platformu.

**Proje:** Atılım Üniversitesi Odyoloji Bölümü, etik kurul onaylı, 12 aylık
klinik çalışma. Katılımcılar: 20 sağ SSD + 20 sol SSD + 20 kontrol.

> **Durum: Adım 1 (proje iskeleti).** Bu depo veri toplamaya hazır değildir.
> Çalışan deney hâlâ Adım 0'ın `src/` ağacıdır; yeni `mcgurk/` paketi onun
> yanında kuruluyor ve şu an config, veritabanı, yedekleme ve loglama
> katmanlarını içeriyor. Neyin eksik olduğu için aşağıdaki
> [Bilinen sınırlar](#bilinen-sınırlar) bölümüne bakın. Geliştirme planı
> `docs/steps.md`, ilerleme durumu `progress.md` dosyasındadır.

## Depo yapısı — iki paket bir arada

| | `src/` (Adım 0) | `mcgurk/` (Adım 1→) |
|---|---|---|
| Durum | Çalışan baseline deney | Yeni platform, inşa hâlinde |
| Giriş | `python main.py` | Henüz yok (Adım 8) |
| Config | `config.yaml` | `config/experiment.yaml` |
| Veritabanı | `data/mcgurk.db` | `data/mcgurk.sqlite` |
| PsychoPy | Zorunlu | `config/` ve `db/` katmanlarında **yasak** |

İkisi bilinçli olarak ayrı: şemalar uyumsuz olduğu için aynı dosyayı
paylaşamazlar, ve yeni paketin config/veritabanı katmanları PsychoPy'siz
çalışabildiği için CI'da ve analiz makinesinde koşabiliyorlar. `src/` Adım 8'de
oturum akışı yeni pakete taşındığında emekli edilecek.

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
gürültü, gürültülü türevler, dikotik çiftler ve GIN gürültü segmentleri.
Hepsi **çevrimdışı** üretilir (§A.12: çalışma anında DSP yok).

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

Deney:

```bash
python main.py
```

Farklı bir yapılandırma veya günlük düzeyiyle:

```bash
python main.py --config config.yaml --log-level DEBUG
```

Sonuçları görüntüleme ve dışa aktarma (ayrı süreç):

```bash
python admin.py
```

Akış: katılımcı girişi → admin ayarları (konuşmacı, bölümler, gürültü, ses
aygıtı) → tam ekran deney → bitiş ekranı.

`ESC` deneyin **her aşamasında** çalışır — talimat ekranı, sabitleme haçı,
uyaran sunumu ve yanıt ekranı dahil. Kesilen oturum veritabanında `aborted`
işaretlenir, o ana kadar yanıtlanan denemeler korunur ve program çıkış kodu
`1` ile döner ("başarıyla tamamlandı" demez).

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
  segmentinde birden fazla
- `v_trials_flat` — hepsini birleştiren düz tablo; `design_extra` anahtarları
  sütun olarak açılır, analiz tarafında JSON görünmez

Veritabanı `mcgurk` ve `dichotic` denemelerinde `is_correct` yazılmasını
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

**Tasarım ve arayüz (Adım 4–8):**
- Yanıt seti `BA/DA/GA` ile sınırlı; kombinasyon algısı ("bga") ifade
  edilemiyor ve "DİĞER" seçeneği yok.
- Füzyon/kombinasyon kategorizasyonu yok.
- Katılımcıya gösterilen metinler hâlâ koda gömülü (config'e taşınacak).
- Deprivasyon süresi ve PTA değerleri toplanmıyor.
- Alıştırma bloğu, molalar, oturum öncesi kontrol listesi ve çapraz dinleme
  kontrolü yok.
- Kesilen oturuma kaldığı yerden devam etme yok.

**Adım 1–2'de gelmeyenler:**
- `mcgurk/` paketinin `engine/`, `modules/`, `ui/`, `analysis/` alt paketleri
  boş — sırasıyla Adım 3, 4–7, 8 ve 9.
- Oddball tonları henüz üretilmiyor: `steps.md` onları Adım 7'ye koyuyor. Orada
  da çevrimdışı üretilecek (§A.12).
- Yeni config ve veritabanı henüz hiçbir deneyi çalıştırmıyor; `main.py` Adım
  8'e kadar `src/` yolunu kullanmaya devam ediyor.
- AVSR kelime seti (`type: word`) yalnızca şema düzeyinde var; `enabled: true`
  yapılırsa deneme sayısı hesabı açık hata verir (§F.2, Adım 5).
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
