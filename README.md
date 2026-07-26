# McGurk / SSD Değerlendirme Platformu

Tek taraflı işitme kaybı (SSD) olan yetişkinlerde görsel-işitsel konuşma
entegrasyonunun davranışsal değerlendirmesi için geliştirilen PsychoPy tabanlı
deney platformu.

**Proje:** Atılım Üniversitesi Odyoloji Bölümü, etik kurul onaylı, 12 aylık
klinik çalışma. Katılımcılar: 20 sağ SSD + 20 sol SSD + 20 kontrol.

> **Durum: Adım 0 (baseline).** Bu depo şu anda düzeltilmiş bir referans
> noktadır, veri toplamaya hazır değildir. Neyin eksik olduğu için aşağıdaki
> [Bilinen sınırlar](#bilinen-sınırlar) bölümüne bakın. Geliştirme planı
> `docs/steps.md`, ilerleme durumu `progress.md` dosyasındadır.

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
aygıtı) → tam ekran deney → bitiş ekranı. Her aşamada `ESC` ile çıkılabilir;
kesilen oturum veritabanında `aborted` olarak işaretlenir ve o ana kadarki
denemeler korunur.

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

**Yedekleme:** `data/`, `backups/` ve `logs/` git dışıdır. Düzenli yedek alın;
otomatik yedekleme katmanı Adım 1'de gelecek.

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
   `MovieStim` yalnızca bunu oynatır (`noAudio=True` ve `setVolume(0)` bazı
   ffpyplayer derlemelerinde yok sayılıyor).
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

Kod, değişken adları ve docstring'ler İngilizce; katılımcıya ve operatöre
gösterilen metinler Türkçedir.

---

## Bilinen sınırlar

Bunlar bilinçli olarak Adım 0 kapsamı dışında bırakıldı; her biri
`docs/steps.md` içinde bir adıma bağlıdır.

**Uyaranlar (Adım 2):**
- Videolar 29.97 fps — 60 Hz ekranda kare başına 2.002 yenileme, periyodik kare
  tekrarı oluşur.
- Ses AAC ile sıkıştırılmış ve 44.1 kHz; hedef 48 kHz 24-bit PCM.
- Token'ların akustik patlama anları hizalanmamış, seviyeleri eşitlenmemiş.
- SNR karışımı tüm dosya RMS'i üzerinden hesaplanıyor; konuşma-aktif RMS
  kullanılmalı (dosyaların önemli bir bölümü sessizlik).
- Gürültü dosyaları kayıplı MP3 ve 44.1 kHz. Konuşma şekilli gürültü korpusun
  LTAS'ından üretilmiş değil.
- Dikotik uyaranlar 48 kHz stereo PCM'e taşındı, ancak kaynakları hâlâ AAC
  videolar olduğu için sinyal tek bir kayıplı turdan geçmiş durumda. Adım 2'de
  ham kayıtlardan yeniden üretilecek.

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
- Pydantic ile config doğrulaması yok; geçersiz alanlar sessizce yok sayılıyor.

**Ortam:**
- `ffmpeg` PATH'te yoksa `imageio-ffmpeg` ile gelen ikili kullanılır. `ffprobe`
  bu pakette **yoktur**; uyaran doğrulama araçları (Adım 2) sistemde kurulu
  ffmpeg gerektirecek.

---

## Lisans

Bkz. [LICENSE](LICENSE).
