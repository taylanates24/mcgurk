# Adım 2 Manuel Test — Uyaran hazırlama ve kalite kontrol

Adım 2, `assets/` altındaki ham kayıtlardan `stimuli/` altına **hazırlanmış**
bir uyaran seti üretir: sessiz sabit kare hızlı video, patlama anına
hizalanmış ve eşit seviyeye getirilmiş ses, konuşma şekilli gürültü, gürültülü
türevler, dikotik çiftler ve GIN segmentleri.

Otomatik testler (292 test, ruff + mypy temiz) hepsini zaten ölçüyor. Aşağıdaki
testler otomatikleştirilemeyen ikisini yapar: **kulakla dinlemek** ve
**gözle izlemek**. Bir uyaran ölçüm olarak doğru ama işitsel olarak bozuk
olabilir.

## Ön koşullar

- [ ] `conda activate C:\Users\tayla\miniconda3\envs\mcgurk` (veya tam yolla)
- [ ] `assets/female_speaker_1/` ve `assets/male_speaker_1/` yerinde
- [ ] Kulaklık (dikotik testi için **şart** — hoparlörle yapılamaz)

## İkinci turda yeniden yapılacaklar

İlk turun bulguları üzerine kenar rampaları değişti ve set yeniden üretildi
(`stimuli/` şu an güncel — yeniden üretmenize gerek yok). Yalnızca şunları
tekrarlayın:

| Test | Neden |
|---|---|
| 4 — Denetim | Yeni bir satır eklendi: her ses dosyası sessizlikten başlıyor mu |
| 8 — Hizalanmış ses | Her dosyaya 10 ms kenar rampası eklendi; başı kırpılan dosya artık hışırtının ortasından başlamıyor |
| 9 — Gürültülü uyaran | Gürültü rampası 50 → **250 ms** |
| 10 — Dikotik | Kenar rampası bunlara da uygulandı |
| 11 — GIN | Segment rampası 50 → **200 ms** |
| 12 — Manifest | Komut düzeltildi (künye manifest'in kökünde) |

Test 1, 2, 3, 5, 6 ve 7 değişmedi — video kodlaması ve hizalama aynı.

---

## Test 1: Config yeni bölümle birlikte geçerli

**Komut:**
```bash
python -m mcgurk.config
```

**Beklenen çıktı:** Adım 1'dekiyle aynı tablo — 797 deneme, ~58.8 dakika.

**Kontrol edilecek:** Hata yok. `stimulus_prep` bölümü eklendiği hâlde tasarım
özeti değişmedi; bu bölüm deneme sayısını etkilemez.

**Başarısızsa:** Hata mesajı hangi alanın sorunlu olduğunu yazar
(`stimulus_prep.…`). `config/experiment.yaml`'daki ilgili satırı düzeltin.

---

## Test 2: Config, tasarımla uyaran setini karşılaştırıyor

`config/experiment.yaml` içinde `modules.mcgurk.speaker_id: 1` → `3` yapın.

**Komut:**
```bash
python -m mcgurk.config
```

**Beklenen çıktı:**
```
HATA: Config doğrulaması başarısız: ...\config\experiment.yaml
  - (kök): Value error, Tasarım ile uyaran seti uyuşmuyor:
  - stimulus_prep.speakers içinde olmayan speaker_id: [3] (tanımlı: [1, 2])
```
Çıkış kodu 1.

**Kontrol edilecek:** Hata `speaker_id`'yi ve tanımlı olanları adıyla söylüyor.

**Sonra:** değeri `1`'e geri alın.

---

## Test 3: Uyaran setini üret

**Komut:**
```bash
python tools/prepare_stimuli.py --force
```

**Beklenen çıktı (patlama anları makinenizde birebir aynı çıkmalı):**
```
INFO     Konuşmacı 1: ...\assets\female_speaker_1
INFO       ba: patlama 1092.0 ms, kazanç -9.4 dB, gürültü tabanı -62.3 dBFS
INFO       da: patlama 1119.0 ms, kazanç -7.4 dB, gürültü tabanı -60.7 dBFS
INFO       ga: patlama 1108.0 ms, kazanç -7.8 dB, gürültü tabanı -59.5 dBFS
INFO     Konuşmacı 2: ...\assets\male_speaker_1
INFO       ba: patlama 1084.0 ms, ...
INFO       da: patlama  849.0 ms, ...
INFO       ga: patlama  836.0 ms, ...
INFO     SSN üretildi: en büyük 1/3 oktav sapması 0.20 dB
INFO     Gürültülü uyaran: 54 dosya
INFO     Dikotik uyaran: 12 dosya
INFO     GIN: 30 segment, 60 boşluk

Video           : 6
Ses (hizalı)    : 18
Ses (gürültülü) : 54
Dikotik         : 12
GIN segmenti    : 30
SSN             : 1 (en büyük LTAS sapması 0.20 dB)

SONUÇ: UYARAN SETİ HAZIR
```

**Kontrol edilecek:**
- Süre ~1–2 dakika, `stimuli/` yaklaşık **70 MB**.
- **Konuşmacı 2'nin patlama anları 1084 / 849 / 836 ms** — aralarında 248 ms
  fark var. Bu bir hata değil, kayıtların gerçeği; hizalamanın neden gerekli
  olduğunun kanıtı. `steps.md`'deki 1105/1119/1108 sayıları konuşmacı 1'e ait
  ve bizim ölçtüğümüzle ±13 ms uyuşuyor (A0-3: sayılar yeniden ölçüldü).

**Başarısızsa:** Boru hattı ilk tolerans ihlalinde durur ve hangi dosyada
neyin kaç dB/ms saptığını yazar. Yarım set üretmez.

---

## Test 4: Seti denetle

**Komut:**
```bash
python tools/verify_stimuli.py
```

**Beklenen çıktı:**
```
YESIL    Manifest okundu (sürüm 1)
YESIL    121 dosya yerinde, sağlama toplamları uyuşuyor
YESIL    Etkin modüllerin istediği her uyaran manifest'te var
YESIL    6 video sessiz, CFR ve tam kare sayısında
YESIL    18 ses dosyası hizalı (en büyük sapma 0.8 ms) ve eşit seviyede
YESIL    SSN'in LTAS'ı korpusla uyuşuyor (en büyük sapma 0.34 dB)
YESIL    54 gürültülü uyaran kırpma sınırının altında
YESIL    30 GIN segmenti: boşluklar sessiz, aralık ve dağılım kısıtları sağlanıyor
YESIL    115 ses dosyası sessizlikten başlıyor ve bitiyor

SONUÇ: UYARAN SETİ KULLANILABİLİR
```

**Kontrol edilecek:** Tek satır bile KIRMIZI değil. **Hizalama sapması 1 ms'in
altında** (tolerans 5 ms).

Son satır kenar tıklamalarını kovalar: hizalama bazı token'ların başından
250 ms'e kadar kırpıyor, o dosyalar aksi hâlde kaydın hışırtısının tam
ortasından başlardı — komşuları dijital sessizlikle başlarken. Bazı
denemelerde tıklama, bazılarında yokluk, uyaranla ilgisi olmayan bir ipucu
demektir.

---

## Test 5: Denetim gerçekten bozulmayı yakalıyor mu

Yeşil bir rapor, ancak kırmızı da verebiliyorsa bir şey ifade eder.

**Komut:**
```bash
python -c "import pathlib; p=pathlib.Path('stimuli/gin/segment_01.wav'); p.unlink()"
python tools/verify_stimuli.py
```

**Beklenen çıktı:**
```
KIRMIZI  1/121 dosya eksik: ['gin/segment_01.wav']
...
SONUÇ: UYARAN SETİ KULLANILAMAZ (1 sorun)
```

**Kontrol edilecek:** Çıkış kodu 1 (`echo $?` / `echo $LASTEXITCODE`).

**Sonra:** `python tools/prepare_stimuli.py --force` ile seti geri getirin ve
`verify_stimuli.py`'nin yine yeşil verdiğini görün.

---

## Test 6: Aynı seed aynı seti üretiyor

**Komut:**
```bash
python -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('stimuli/gin/segment_01.wav').read_bytes()).hexdigest()[:16])"
python tools/prepare_stimuli.py --force
python -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('stimuli/gin/segment_01.wav').read_bytes()).hexdigest()[:16])"
```

**Beklenen çıktı:** İki sağlama toplamı **birebir aynı**.

**Kontrol edilecek:** Gürültü ve GIN boşluk yerleşimi rastgele ama tohumlanmış;
set yeniden üretilebilir (§A.11'in uyaran tarafındaki karşılığı).

---

# Ses ve görüntü gerektiren testler

Bunlar hazırlanmış dosyaları doğrudan açar; PsychoPy penceresi açılmaz.

## Test 7: Videolar sessiz ve akıcı

`stimuli/video/speaker_1/Vis-ba.mp4` dosyasını herhangi bir oynatıcıyla açın
(VLC, Windows Media Player, `ffplay`).

**Kontrol edilecek:**
- [ ] **Hiç ses yok.** (Bu §A.1'dir: MovieStim gömülü sesi SDL2 üzerinden
      çalar ve A/V senkronunu bozar. `noAudio=True` PsychoPy 2026.1'de
      çalışmıyor; dosyada ses akışı olmaması tek çözüm.)
- [ ] Görüntü akıcı, kesik/donma yok, 2.57 saniye sürüyor.
- [ ] Konuşmacının ağzı normal hızda hareket ediyor (hızlanma/yavaşlama yok).

Altı videonun hepsine bakın: `speaker_1` ve `speaker_2` × `Vis-ba/da/ga`.

**Başarısızsa:** Ses duyuyorsanız durun ve bildirin — bu, tüm zamanlama
mimarisini geçersiz kılar.

---

## Test 8: Hizalanmış ses doğru heceyi taşıyor

**Kulaklıkla** şu dosyaları dinleyin:

| Dosya | Duyulması gereken |
|---|---|
| `stimuli/audio/speaker_1/Vis-ba_Aud-ba.wav` | "ba" |
| `stimuli/audio/speaker_1/Vis-ga_Aud-ba.wav` | **"ba"** (dosya adındaki `Aud-` neyse o) |
| `stimuli/audio/speaker_1/Vis-ba_Aud-ga.wav` | **"ga"** |
| `stimuli/audio/speaker_2/Vis-ba_Aud-da.wav` | "da" |
| `stimuli/audio/speaker_2/Vis-ga_Aud-ba.wav` | "ba" — **başı 249 ms kırpılan dosya** |

**Kontrol edilecek:**
- [ ] Duyulan hece her zaman dosya adındaki `Aud-` değeri. (`Vis-` yalnızca
      hangi videoyla eşleneceğini ve dolayısıyla sesin nereye hizalandığını
      söyler.)
- [ ] **Başta ve sonda tıklama/pat sesi yok.** Özellikle son satırdaki dosya:
      hizalama onun başından 249 ms kırptı, yani dosya kaydın hışırtısının
      ortasından başlıyor. 10 ms'lik kenar rampası bu adımı yumuşatır; tıklama
      duyuyorsanız rampa yetmiyor demektir.
- [ ] Hece kesilmemiş — başı da sonu da tam.
- [ ] Altı dosyanın ses yüksekliği kulağa **eşit** geliyor (bir tanesi belirgin
      şekilde kısık/yüksek değil).

**Başarısızsa:** Kesilmiş bir hece duyuyorsanız hangi dosya olduğunu not edin;
hizalama kırpma denetimi bunu yakalamalıydı.

---

## Test 9: Gürültülü uyaranlar

**Kulaklıkla** dinleyin:

```
stimuli/audio_noisy/speaker_1/Vis-ba_Aud-ba_ssn5dB_1.wav
stimuli/audio_noisy/speaker_1/Vis-ba_Aud-ba_ssn5dB_2.wav
stimuli/audio_noisy/speaker_1/Vis-ba_Aud-ba_ssn5dB_3.wav
```

**Kontrol edilecek:**
- [ ] Gürültü var ama hece **hâlâ anlaşılıyor** (+5 dB SNR bunu vermeli).
- [ ] Gürültü konuşma gibi tınlıyor — beyaz gürültünün "tıs"ı değil, daha
      pesli/dolgun. (Korpusun LTAS'ından üretiliyor.)
- [ ] Gürültü **250 ms boyunca** yumuşak giriyor ve çıkıyor, kesik/tıklama yok.
      (İlk sürümde 50 ms'ti ve gürültü "açılıyor" gibiydi. Rampa yukarıdan
      sınırlı: token'ın kendi giriş boşluğundan uzun olamaz, yoksa konuşmanın
      başı nominalinden yüksek SNR'de sunulurdu — hazırlık bunu reddediyor.)
- [ ] Kırpma (distorsiyon) yok.
- [ ] **Üç dosya birbirinin aynısı gibi duyuluyor** — evet, *aynı* gibi. Bu
      beklenen: konuşma şekilli gürültü durağan bir süreçtir, her kesiti aynı
      spektruma ve aynı istatistiğe sahiptir. Farklı duyulsalardı biri
      diğerinden farklı bir gürültü olurdu.

Kulakla ayırt edilemeyen şeyin gerçekten farklı olduğunu ölçerek doğrulayın:

```bash
python -c "import sys; sys.path.insert(0,'.'); import numpy as np; from pathlib import Path; from mcgurk.stimuli import wavfile; c=wavfile.read(Path('stimuli/audio/speaker_1/Vis-ba_Aud-ba.wav'))[0]; n=[wavfile.read(Path(f'stimuli/audio_noisy/speaker_1/Vis-ba_Aud-ba_ssn5dB_{i}.wav'))[0]-c for i in (1,2,3)]; print('korelasyonlar:', [round(float(np.corrcoef(n[i],n[j])[0,1]),4) for i,j in ((0,1),(0,2),(1,2))])"
```

**Beklenen çıktı:** üç korelasyon da sıfıra yakın (|r| < 0.05).

**Neden önemli:** Amaç algısal çeşitlilik değil. Gürültülü hücrede aynı deneme
10 kez tekrarlanıyor; aynı **dalga formunu** 10 kez dinlemek o dalga formunun
sessiz anlarını öğrenmeyi mümkün kılar ("listening in the dips"). Ölçülmek
istenen beceri bu değil. Dalga formları farklı olduğu sürece amaç sağlanmıştır.

---

## Test 10: Dikotik uyaranlar — kulaklık şart

`stimuli/dichotic/speaker_1/Left-ba_Right-da.wav` dosyasını **kulaklıkla**
dinleyin.

**Kontrol edilecek:**
- [ ] Sol kulakta "ba", sağ kulakta "da".
- [ ] İkisi **aynı anda** başlıyor — biri ötekinden belirgin şekilde geç
      gelmiyor. (Konuşmacının doğal patlama anları 248 ms'e kadar ayrışıyor;
      dikotik dosyalarda ikisi ortak bir ana hizalanır, yoksa ölçülen "kulak
      avantajı" kısmen başlangıç farkı olurdu.)
- [ ] Kulaklığı ters takıp tekrar dinleyin: heceler yer değiştirmeli. (Kanal
      karışıklığı bu şekilde yakalanır.)

Bir de tersini dinleyin: `Left-da_Right-ba.wav`.

---

## Test 11: GIN segmentleri

`stimuli/gin/segment_01.wav` dosyasını dinleyin (6 saniye gürültü).

Boşlukların nerede olduğunu manifest'ten okuyun:

```bash
python -c "import json; m=json.load(open('stimuli/manifest.json',encoding='utf-8')); s=m['gin_segments'][0]; print(list(zip(s['gap_onsets_s'], s['gap_durations_ms'])))"
```

**Kontrol edilecek:**
- [ ] Gürültü sabit seviyede, dalgalanma yok.
- [ ] Uzun boşluklar (12–20 ms) duyuluyor; kısa olanlar (2–3 ms) duyulmayabilir
      — zaten ölçülen şey budur.
- [ ] Boşlukların yerinde **tıklama yok**. Tıklama duyuyorsanız katılımcı
      boşluğu değil tıklamayı tespit ediyor demektir; bu, ölçümü geçersiz kılar.
- [ ] Segmentin başı ve sonu **200 ms boyunca** yumuşak giriyor/çıkıyor —
      gürültü "geliyor" değil, "başlıyor" gibi olmalı.

Rampayı ölçerek de görebilirsiniz:

```bash
python -c "import sys; sys.path.insert(0,'.'); from pathlib import Path; from mcgurk.stimuli import wavfile, dsp; s,r=wavfile.read(Path('stimuli/gin/segment_01.wav')); e=dsp.frame_rms(s,r,10.0); print('ilk 300 ms:', ' '.join(f'{dsp.to_db(v):.0f}' for v in e[:30]))"
```

**Beklenen çıktı:** −75'ten −23 dBFS'e ~180 ms'de yükselen bir dizi; yaklaşık
100 ms'te −29 (yarı genlik) civarında olmalı.

---

## Test 12: Manifest okunabilir ve dolu

**Komut (bir ses kaydı):**
```bash
python -c "import json; m=json.load(open('stimuli/manifest.json',encoding='utf-8')); t=[e for e in m['tokens'] if e['speaker_id']==2][0]; print(json.dumps(t,indent=1,ensure_ascii=False))"
```

**Kontrol edilecek:**
- [ ] `burst_time_s` dolu — Adım 3 sesi ekranın flip saatine karşı buna göre
      planlayacak.
- [ ] `active_level_dbfs` ≈ −23.0.
- [ ] `source.codec: "aac"`, `source.sample_rate: 44100` — kaynağın kayıplı
      olduğu kayıt altında, gizlenmiyor.

**Komut (üretim künyesi — manifest'in kökünde, tek tek kayıtlarda değil):**
```bash
python -c "import json; m=json.load(open('stimuli/manifest.json',encoding='utf-8')); print(json.dumps(m['provenance'],indent=1,ensure_ascii=False)); print('uretim:', m['created_at'])"
```

**Kontrol edilecek:**
- [ ] `git_commit` dolu (çalışan ağaçta değişiklik varsa `+dirty` ekli olur).
- [ ] `python_version`, `os_name`, `psychopy_version` dolu.

---

## Kabul kriterleri

`docs/steps.md` §C Adım 2:

- [ ] **2 konuşmacı × 3 token** pipeline'dan geçiyor (A0-2: "8 konuşmacı"
      ifadesi geçersiz)
- [ ] Manifest'teki patlama anları bağımsız ölçümle uyuşuyor
      (`verify_stimuli.py` yeniden ölçüyor; sapma < 1 ms)
- [ ] Üretilen videolarda ses akışı **yok** (Test 7 + otomatik kontrol)
- [ ] SSN'in LTAS'ı korpusunkiyle eşleşiyor (sapma 0.34 dB, tolerans 3 dB)
- [ ] Bozuk/hizasız girdi verildiğinde pipeline hata veriyor (otomatik
      testler: sessiz kaynak, patlaması olmayan token, eksik kayıt)
- [ ] `pytest` yeşil, `ruff check .` ve `mypy` temiz

---

## Sonraki adıma taşınanlar

- **Oddball tonları bu adımda üretilmedi.** `steps.md` onları Adım 7'ye
  koyuyor ve kabul kriteri orada. Orada da çevrimdışı üretilecek (§A.12).
- **Kaynak kayıplı.** Depoda ham kayıt yok (A0-3); set 44.1 kHz AAC'den
  türetildi. Manifest bunu kaydediyor. Yeni bir çekim yapılırsa (§F.2 kelime
  seti) aynı boru hattı kayıpsız kaynakla daha iyisini üretir — kod değişmez.
- **Adım 3** `stimuli/manifest.json`'daki `burst_time_s` üzerinden SOA
  hesabını yapacak; `assets/` yolunu kullanmayacak.
