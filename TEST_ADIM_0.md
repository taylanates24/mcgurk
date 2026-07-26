# Adım 0 Manuel Test

Bu adım bir **baseline düzeltmesidir**: mevcut kodun hataları giderildi,
mimari değiştirilmedi. Testlerin amacı düzeltilen davranışların gerçekten
düzeldiğini ve hiçbir şeyin bozulmadığını doğrulamaktır.

Tahmini süre: ekransız testler ~5 dakika, ekran/ses testleri ~25 dakika.

## Ön koşullar

### Doğru conda ortamı

Ortam `C:\Users\tayla\miniconda3\envs\mcgurk` altında. Bu dizin conda'nın isim
arama yolunda (`envs_dirs`) olmadığı için `conda env list` çıktısında isimsiz
görünür. Tek seferlik olarak arama yoluna ekleyin:

```bash
conda config --append envs_dirs C:\Users\tayla\miniconda3\envs
```

`conda activate` bir shell fonksiyonudur; kabuğunuz için bir kez
başlatılmalıdır. VS Code'un PowerShell terminalinde:

```bash
conda init powershell
```

(Git Bash kullanıyorsanız `conda init bash`.) **Ardından terminali kapatıp
yeniden açın** — profil yalnızca yeni oturumlarda yüklenir. Bu adım
atlanırsa `conda activate mcgurk` hata vermeden hiçbir şey yapmaz ve
`python` base ortamda (3.13) kalır.

Sonra normal şekilde aktive edin:

```bash
conda activate mcgurk
```

Aktivasyonla hiç uğraşmak istemezseniz komutları tam yolla da
çalıştırabilirsiniz, örneğin `python` yerine:

```bash
C:\Users\tayla\miniconda3\envs\mcgurk\python.exe -m pytest
```

Doğrulayın — çıktıda `3.10.20`, bir PsychoPy sürümü ve `miniconda3` yolu
görmelisiniz:

```bash
python -c "import sys, psychopy; print(sys.version.split()[0], psychopy.__version__, sys.executable)"
```

`ModuleNotFoundError: psychopy` veya `3.13.x` görüyorsanız yanlış ortamdasınız.
`pip install` çalıştırmayın — base ortamda Python 3.13 olduğu için
`No matching distribution found for psychopy==2026.1.2` hatası alırsınız.

- [ ] Yukarıdaki doğrulama komutu `3.10.20 2026.1.2 ...\miniconda3\envs\mcgurk\python.exe` veriyor
- [ ] Bu ortamda paketler **zaten kurulu** — `pip install` adımına gerek yok
- [ ] `assets/` yerinde: `female_speaker_1/`, `male_speaker_1/`,
      `dichotic/`, `noise/`
- [ ] Kulaklık takılı ve ses çıkışı çalışıyor
- [ ] Depo kökündesiniz (`C:\Users\tayla\projects\mcgurk`)

---

## Test 1: Otomatik testler

**Komut:**
```bash
pytest
```

**Beklenen çıktı:** son satır
```
43 passed
```

**Kontrol edilecek:** Hiç `FAILED` veya `ERROR` satırı olmamalı.

**Başarısızsa:** Çıktıyı olduğu gibi paylaşın; hangi testin düştüğü hangi
düzeltmenin bozulduğunu gösterir.

---

## Test 2: Lint ve tip denetimi

**Komut:**
```bash
ruff check .
```

**Beklenen çıktı:**
```
All checks passed!
```

**Komut:**
```bash
mypy
```

**Beklenen çıktı:**
```
Success: no issues found in 27 source files
```

**Kontrol edilecek:** İkisi de temiz olmalı.

---

## Test 3: Yardım çıktısı doğru parser'dan geliyor

PsychoPy kendi argüman ayrıştırıcısını çalıştırır ve daha önce `--help`'i
ele geçiriyordu.

**Komut:**
```bash
python main.py --help
```

**Beklenen çıktı:**
```
usage: mcgurk [-h] [--config CONFIG] [--log-level {DEBUG,INFO,WARNING,ERROR}]

McGurk deney yürütücüsü
```

**Kontrol edilecek:** Başlık `mcgurk` olmalı. `usage: PsychoPy Preferences`
görüyorsanız düzeltme çalışmamıştır.

**Başarısızsa:** Bildirin — argüman ayrıştırma PsychoPy import'undan önce
yapılmalı.

---

## Test 4: Eski veritabanı reddediliyor (KVKK)

Ad-soyad sütunu içeren eski bir DB sessizce kullanılmamalı.

**Komut:**
```bash
python -c "import sqlite3; c=sqlite3.connect('data/eski_test.db'); c.execute('CREATE TABLE participants (participant_id INTEGER PRIMARY KEY, name TEXT, age INTEGER)'); c.commit(); c.close(); print('sahte eski DB olusturuldu')"
```

**Komut:**
```bash
python main.py --config config.yaml
```
> Not: bu test için `config.yaml` içindeki `database_path` değerini geçici
> olarak `data/eski_test.db` yapın.

**Beklenen çıktı:**
```
ERROR    'data/eski_test.db' eski şemayı kullanıyor (participants.name).
Bu şema katılımcı adı içerdiği için artık desteklenmiyor (KVKK).
Dosyayı backups/ altına yedekleyip silin, sonra tekrar çalıştırın.
```

**Kontrol edilecek:** Program hata verip **çıkmalı**, hiçbir pencere
açmamalı. Çıkış kodu 1 olmalı.

**Temizlik:** `config.yaml`'ı eski hâline getirin, `data/eski_test.db` dosyasını
silin.

---

## Test 5: Katılımcı kodu doğrulaması

**Komut:**
```bash
python main.py
```

Açılan **Katılımcı Bilgileri** penceresinde sırayla deneyin:

| Girdi | Beklenen |
|---|---|
| Kodu boş bırakıp OK | "Katılımcı kodu boş olamaz" hatası, form tekrar açılır |
| Yaş = `15` | "Yaş 18 ile 60 arasında olmalıdır" hatası, form tekrar açılır |
| Kod = `ssd-r-007`, Yaş = `34` | Kabul edilir, admin ayarları penceresine geçer |

**Kontrol edilecek:**
- Formda **Ad Soyad alanı olmamalı** — yalnızca Katılımcı Kodu.
- Hatalı girişte program çökmemeli, formu yeniden göstermeli.
- İptal (X) edilince temiz çıkmalı: `Deney iptal edildi (katılımcı girişi).`

**Başarısızsa:** Hangi girdide ne olduğunu not edin.

---

## Ekran/ses gerektiren testler

Bunlar tam ekran PsychoPy penceresi açar ve ses çalar. Sessiz bir odada,
kulaklıkla yapın.

> **Beklenen uyarı — endişelenmeyin.** Video içeren her denemede konsolda şu
> satır çıkar:
>
> ```
> WARNING  Using `sdl2` for audio playback via `ffpyplayer`. This is not
> recommended for applications requiring precise audio-visual synchronization.
> ```
>
> Bu uyarı bastırılamaz: PsychoPy 2026.1'de `MovieStim` `noAudio=True`
> argümanını yok sayar ve ffpyplayer'ı her durumda SDL2'ye bağlar (başka bir
> `audioLib` vermek istisna fırlatır). Zararsızdır, çünkü `MovieStim`'e verilen
> dosyada **ses akışı yoktur** — ffmpeg ile sökülmüştür, `pytest`
> (`test_silent_video.py`) bunu her koşuda doğrular. Sesi `ptb` çalar.

### Test 6: Ses backend'i gerçekten ptb

**Komut:**
```bash
python -c "import sys; sys.path.insert(0,'.'); from src.experiment.stimuli import require_ptb_backend; require_ptb_backend(); print('BACKEND OK')"
```

**Beklenen çıktı:**
```
INFO     Ses backend'i doğrulandı: ptb
BACKEND OK
```

**Kontrol edilecek:** `BACKEND OK` yazmalı. Hata alıyorsanız deney
başlatılamaz — bu kasıtlıdır, sessiz geri düşüş yasak.

---

### Test 7: Tam oturum — McGurk + AV uyumlu

**Komut:**
```bash
python main.py
```

Ayarlar:
- Katılımcı Kodu: `TEST-001`, Yaş: `30`
- Konuşmacı: herhangi biri
- Bölümler: **McGurk (Uyumsuz)** ve **AV Uyumlu** işaretli
- Gürültülü koşul: işaretsiz

**Kontrol edilecek — sırayla:**

1. **Talimat ekranı** toplam deneme sayısını gösteriyor (9 olmalı: 6 uyumsuz +
   3 uyumlu).
2. Her denemede sabitleme haçı → video → yanıt ekranı sırası izleniyor.
3. **Video oynarken ses ile görüntü senkron** — dudak hareketi ile sesin
   birbirinden kaymadığını dinleyin.
4. **Yanıt ekranında video görünmüyor ve ses duyulmuyor.** (Eskiden video
   yanıt penceresine taşabiliyordu.)
5. Yanıt ekranının sağ altında `[ESC] Testi Bitir` ipucu var.
6. Tüm denemeleri tamamlayın.
7. **Bitiş ekranı yalnızca deneme sayısını gösteriyor — başarı yüzdesi
   GÖSTERMİYOR.** Bu kasıtlıdır: algı görevinde performans geri bildirimi
   talep karakteristiği yaratır.

**Başarısızsa:** Hangi maddede takıldığını ve ekranda ne gördüğünüzü yazın.

---

### Test 8: ESC ile kesme ve veri korunması

`ESC` artık **her aşamada** çalışır: talimat ekranı, sabitleme haçı, uyaran
sunumu ve yanıt ekranı. Dördünü de ayrı ayrı deneyin.

**Komut:**
```bash
python main.py
```

Katılımcı Kodu `TEST-002`, McGurk bölümü seçili.

| Deneme | Nerede `ESC`'e basılacak | Beklenen |
|---|---|---|
| 8a | Talimat ekranında (SPACE'e basmadan) | Hiç deneme kaydedilmeden çıkar |
| 8b | Sabitleme haçı gösterilirken | O deneme kaydedilmez, öncekiler kalır |
| 8c | Video/ses oynarken | Ses anında susar, o deneme kaydedilmez |
| 8d | Yanıt ekranında (3–4 deneme yanıtladıktan sonra) | Yanıtlanan denemeler kalır |

Her seferinde `python main.py` ile yeniden başlatın.

**Kontrol edilecek (her dördünde):**
- Program çökmeden kapanıyor, pencere kapanıyor.
- Konsolda `Oturum kesildi (N deneme kaydedildikten sonra).` satırı var.
- Konsolda **`Deney başarıyla tamamlandı.` YAZMIYOR.** Bunun yerine
  `Deney tamamlanmadı (durum: aborted). Kaydedilen denemeler korundu.`
  uyarısı çıkıyor.
- Bitiş ekranı **gösterilmiyor**.
- 8c'de ses `ESC` ile birlikte kesiliyor, videonun sonunu beklemiyor.

Sonra durumu doğrulayın:

**Komut:**
```bash
python -c "import sqlite3; c=sqlite3.connect('data/mcgurk.db'); c.row_factory=sqlite3.Row; [print(dict(r)) for r in c.execute('SELECT session_id, status, seed, completed_at FROM sessions ORDER BY session_id DESC LIMIT 2')]"
```

**Beklenen çıktı:** En son oturum satırında
```
'status': 'aborted'
```
ve `seed` alanı dolu, `completed_at` dolu.

**Kontrol edilecek:**
- Kesilen oturum `aborted`, tamamlanan oturum `completed`.
- Yanıtladığınız denemeler veritabanında duruyor:

**Komut:**
```bash
python -c "import sqlite3; c=sqlite3.connect('data/mcgurk.db'); print('kaydedilen deneme:', c.execute('SELECT COUNT(*) FROM trials WHERE session_id=(SELECT MAX(session_id) FROM sessions)').fetchone()[0])"
```

Sayı, ESC'ye basmadan önce yanıtladığınız deneme sayısıyla eşleşmeli.

---

### Test 9: McGurk denemelerinde doğru/yanlış yok

**Komut:**
```bash
python -c "import sqlite3; c=sqlite3.connect('data/mcgurk.db'); c.row_factory=sqlite3.Row; [print(dict(r)) for r in c.execute('SELECT section_type, COUNT(*) n, SUM(is_correct IS NULL) nulls FROM trials GROUP BY section_type')]"
```

**Beklenen çıktı:** `mcgurk` ve `dichotic` satırlarında `n` ile `nulls` **eşit**;
`av_congruent`, `audio_only`, `visual_only` satırlarında `nulls` = 0.

**Kontrol edilecek:** McGurk denemelerinin hiçbirinde 0/1 doğruluk değeri
olmamalı.

---

### Test 10: Anonimlik ve seed kaydı

**Komut:**
```bash
python -c "import sqlite3; c=sqlite3.connect('data/mcgurk.db'); print('participants sutunlari:', [r[1] for r in c.execute('PRAGMA table_info(participants)')])"
```

**Beklenen çıktı:**
```
participants sutunlari: ['participant_id', 'participant_code', 'age', 'gender', 'group', 'notes', 'created_at']
```

**Kontrol edilecek:** `name` sütunu **olmamalı**.

---

### Test 11: Gürültülü koşul ve eksik dosya davranışı

**Komut:**
```bash
python main.py
```

Katılımcı `TEST-003`, McGurk seçili, **"Gürültülü koşul ekle" işaretli**, açılan
ikinci pencerede McGurk işaretli.

**Kontrol edilecek:**
- Deneme sayısı üçe katlanıyor (temiz + white + cocktail).
- Gürültülü denemelerde gürültü **duyuluyor**.

Sonra eksik dosya davranışını sınayın: `config.yaml` içinde
`noise.type` değerini `speech_shaped` yapın (bu dosya `assets/noise/` içinde
yok) ve `assets/noise/` klasörünü geçici olarak başka bir yere taşıyın.

**Beklenen:** Program **açık hata** vermeli:
```
ERROR    Gürültü dosyası bulunamadı: ...
Gürültülü koşul bu dosya olmadan sunulamaz.
```

**Kontrol edilecek:** Gürültülü koşul **sessizce temiz koşula dönüşmemeli**.
Eskiden yalnızca bir uyarı verip devam ediyordu; veri geçerli görünüp yanlış
oluyordu.

**Temizlik:** `assets/noise/` klasörünü geri koyun, `config.yaml`'ı eski hâline
getirin.

---

### Test 12: Dikotik dinleme — kanal ayrımı ve videosuz sunum

Bu bölüm artık video kullanmıyor; stereo WAV doğrudan çalınıyor.

**Ön koşul:** Uyaranlar üretilmiş olmalı:
```bash
python scripts/generate_dichotic_stimuli.py
```

**Komut:**
```bash
python main.py
```

Katılımcı `TEST-004`, yalnızca **Dikotik Dinleme** işaretli.

**Kontrol edilecek — kulaklığı doğru takın (L sol kulakta, R sağ kulakta):**

1. Deneme sırasında ekranda **yalnızca sabitleme haçı** var — siyah kare
   yanıp sönmüyor, görüntü titremiyor.
2. **Her kulakta farklı hece duyuluyor.** Kulaklığı ters çevirdiğinizde
   heceler yer değiştirmeli.
3. Ses ile yanıt ekranı arasında donma veya gecikme yok.
4. 6 deneme tamamlanıyor (3 hecenin ikili permütasyonu).

**Kanal ayrımını sayısal doğrulama:**
```bash
python -c "import numpy as np; from scipy.io import wavfile; sr,d=wavfile.read('assets/dichotic/female_speaker_1/Left-ba_Right-da.wav'); x=d.astype(float)/32768; print('ornekleme:',sr,'Hz  kanal:',d.shape[1]); print('L-R korelasyonu:',round(float(np.corrcoef(x[:,0],x[:,1])[0,1]),3))"
```

**Beklenen çıktı:**
```
ornekleme: 48000 Hz  kanal: 2
L-R korelasyonu: 0.008
```

**Kontrol edilecek:** Örnekleme 48000, kanal sayısı 2, korelasyon sıfıra yakın
(farklı heceler). Korelasyon 0.5'in üzerindeyse kanallar karışmış demektir.

**Başarısızsa:** `assets/dichotic/` içinde `.wav` dosyaları var mı bakın. Yalnızca
eski `.mp4` dosyaları varsa bölüm hiç deneme üretmez — üretim script'ini çalıştırın.

---

### Test 13: Admin paneli

**Komut:**
```bash
python admin.py
```

**Kontrol edilecek:**
- **Katılımcılar** sekmesinde ikinci sütun başlığı **"Katılımcı Kodu"**
  (eskiden "Ad Soyad"), değerler `TEST-001` gibi.
- **Denemeler** sekmesinde özet satırı üç sayı gösteriyor:
  `Toplam: N | Puanlanabilir: M | Doğru: K (%)`.
- McGurk satırlarında "Doğru?" sütunu **`—`** (tire), `+`/`-` değil.
- Katılımcı filtresini seçip **Yenile**'ye basın: filtre **sıfırlanmamalı**.
- "Denemeleri CSV Olarak Dışa Aktar" çalışıyor ve çıkan dosyada `name` değil
  `participant_code` sütunu var.

---

## Test verilerinin temizlenmesi

Manuel testler bittiğinde test kayıtlarını silin:

```bash
python -c "import pathlib; p=pathlib.Path('data/mcgurk.db'); p.unlink(missing_ok=True); print('test DB silindi')"
```

---

## Kabul kriterleri

- [ ] `pytest` yeşil (55 test)
- [ ] `ruff check .` ve `mypy` temiz
- [ ] Katılımcı formunda ad-soyad alanı yok; boş/geçersiz girdi reddediliyor
- [ ] `participants` tablosunda `name` sütunu yok
- [ ] Eski şemalı DB açık hatayla reddediliyor
- [ ] Tam oturum baştan sona çalışıyor, A/V senkron duyulabilir şekilde doğru
- [ ] Yanıt ekranında video görünmüyor, ses duyulmuyor
- [ ] Bitiş ekranı başarı yüzdesi göstermiyor
- [ ] ESC talimat ekranında, sabitleme haçında, uyaran sunumunda ve yanıt
      ekranında çalışıyor; oturum `aborted` işaretleniyor, veri korunuyor
- [ ] Kesilen oturumda konsol "başarıyla tamamlandı" demiyor
- [ ] Tam ekranda `User requested fullscreen with size [800 600]` uyarısı yok
- [ ] `mcgurk` ve `dichotic` denemelerinde `is_correct` NULL
- [ ] Oturum kaydında `seed` dolu
- [ ] Gürültü dosyası eksikken program açık hata veriyor
- [ ] Admin panelinde kod gösteriliyor, McGurk satırları `—` ile işaretli
- [ ] `python main.py --help` bizim yardım metnimizi gösteriyor
- [ ] Dikotik bölümde ekranda yalnızca sabitleme haçı var, her kulakta farklı
      hece duyuluyor

## Bu adımda test EDİLMEYENLER

Aşağıdakiler bilinçli olarak kapsam dışıdır ve `README.md` → *Bilinen sınırlar*
bölümünde listelenmiştir:

- Mutlak A/V gecikmesi (`system_av_offset_ms`) — fotodiyot ölçümü, tüm kod
  bittikten sonra (`docs/01_av_gecikme_olcumu.md`)
- Ses seviyesi kalibrasyonu (`docs/02_kalibrasyon.md`)
- Düşen kare / gerçekleşen onset kaydı — Adım 3
- SOA manipülasyonu ve uzamsal lateralizasyon — Adım 3
- Uyaran kalitesi (fps, örnekleme hızı, patlama hizalaması) — Adım 2
