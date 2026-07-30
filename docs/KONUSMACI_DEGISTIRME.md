# Konuşmacıyı değiştirme / yeni konuşmacı ekleme

Bu belge, deneyde kullanılan **konuşmacıyı** (yüz + ses kaydı) nasıl
değiştireceğinizi anlatır. İki ayrı durum var:

- **A. Hâlihazırda hazırlanmış** bir konuşmacıya geçmek (şu an id 1 ve 2 hazır).
- **B. Yeni bir konuşmacı** eklemek (kayıt + hazırlık gerekir).

Her iki durumda da tek doğruluk kaynağı `config/experiment.yaml`'dır; kod
değişmez. Hangi konuşmacının kullanıldığı her oturumda `sessions.config_snapshot`
içine yazıldığı için, sonradan config değişse bile geçmiş verinin hangi
konuşmacıyla toplandığı bellidir.

> **Not — konuşmacıyı yalnızca şu modüller kullanır:** McGurk, AVSR, TBW,
> Dikotik (hepsi yüz/ses kaydından türer). **Oddball** saf ton, **GIN** geniş
> bantlı gürültü kullanır; konuşmacıdan etkilenmezler.

---

## Konuşmacı nasıl seçiliyor? (arka plan)

İki ayrı yer var:

1. **`speaker_selection`** — gerçek oturumda (`python -m mcgurk.ui`) hangi
   konuşmacının sunulacağını belirler:
   ```yaml
   speaker_selection:
     strategy: fixed      # fixed | balanced | random
     fixed_id: 1
   ```
   - `fixed` → her katılımcıya `fixed_id`'deki konuşmacı.
   - `balanced` → oturum sayısına göre sırayla döner (1, 2, 1, 2, …).
   - `random` → oturum tohumundan üretilebilir rastgele seçim.

2. **`modules.<modül>.speaker_id`** — dev aracının (`tools/run_module.py`) ve
   tasarım özetinin (`python -m mcgurk.config`) varsayılanı. Gerçek oturumda
   `speaker_selection` bunu ezer.

> Kısaca: **gerçek oturum için `speaker_selection`'ı**, tek modül denemeleri için
> `modules.*.speaker_id`'yi (veya `run_module --speaker-id`) ayarlarsınız.

---

## A. Hazır bir konuşmacıya geçmek (en hızlı yol)

Şu an `stimulus_prep.speakers` altında **id 1** (`female_speaker_1`) ve **id 2**
(`male_speaker_1`) hazır.

1. `config/experiment.yaml`'ı açın.
2. **Gerçek oturum için** `speaker_selection.fixed_id`'yi istediğiniz id yapın:
   ```yaml
   speaker_selection:
     strategy: fixed
     fixed_id: 2          # 1 -> 2
   ```
3. (İsteğe bağlı, tutarlılık için) Modül varsayılanlarını da hizalayın:
   `modules.mcgurk.speaker_id`, `modules.avsr.speaker_id`,
   `modules.tbw.speaker_id`, `modules.dichotic.speaker_id` → aynı id.
4. Doğrulayın:
   ```powershell
   python -m mcgurk.config
   ```
   Hata vermemeli (tasarım özeti basar). Konuşmacı tokenları hazır değilse
   **açık hata** verir.
5. (Donanımda) kısa bir kontrol:
   ```powershell
   python tools/run_module.py --module mcgurk --limit 4 --speaker-id 2
   ```

Bu kadar. Yeni konuşmacı **hazır olduğu** için başka bir şey gerekmez.

---

## B. Yeni bir konuşmacı eklemek (kayıt + hazırlık)

Diyelim yeni konuşmacı **id 3** olacak.

### 1. Ham kayıtları yerleştirin

`assets/` altına yeni bir klasör açın (ör. `assets/female_speaker_2/`) ve
**uyumlu çekimleri** koyun — her token için görsel ve işitsel **aynı** olan doğal
kayıt:

```
assets/female_speaker_2/Vis-ba_Aud-ba.mp4
assets/female_speaker_2/Vis-da_Aud-da.mp4
assets/female_speaker_2/Vis-ga_Aud-ga.mp4
```

- Dosya adları **tam olarak** `Vis-<token>_Aud-<token>.mp4` olmalı.
- Token listesi `stimulus_prep.tokens` (şu an `[ba, da, ga]`) ile aynı olmalı.
- Uyumsuz (Vis ≠ Aud) dosya **eklemeyin**; boru hattı uyumsuz kombinasyonları
  bu uyumlu kayıtlardan **kendisi** üretir (ses, videonun kendi patlama anına
  hizalanarak monte edilir).
- Kayıt kalitesi mevcutlarla uyumlu olsun (tercihen kayıpsız; boru hattı 48 kHz
  24-bit'e çıkarır).

### 2. Config'e konuşmacıyı tanıtın

`config/experiment.yaml` → `stimulus_prep.speakers` listesine ekleyin:

```yaml
stimulus_prep:
  speakers:
    - {id: 1, source: assets/female_speaker_1}
    - {id: 2, source: assets/male_speaker_1}
    - {id: 3, source: assets/female_speaker_2}   # yeni
  tokens: [ba, da, ga]
```

- `id` benzersiz olmalı, `source` klasör benzersiz olmalı (şema kontrol eder).

### 3. Uyaranları hazırlayın

```powershell
python tools/prepare_stimuli.py
```

Bu, yeni konuşmacı için şunları üretir: sessiz CFR video, hizalanmış 48 kHz
24-bit ses, gürültülü türevler (SSN +5 dB), dikotik stereo dosyalar; ve
`stimuli/manifest.json`'a satırlar ekler. **Tolerans dışı bir durumda hata verip
durur** (sessizce geçmez). Gerekirse `--force` ile yeniden üretin.

### 4. Doğrulayın

```powershell
python tools/verify_stimuli.py
```

Diskteki dosyaları manifest'e karşı yeniden ölçer (patlama anı, seviye, LTAS,
ses akışı yokluğu, kare sayısı…). Çıkış kodu 0 olmalı.

### 5. Tasarımı yeni konuşmacıya yöneltin

A bölümündeki gibi:

```yaml
speaker_selection:
  strategy: fixed
  fixed_id: 3
```

(ya da `balanced`/`random` ile 3'ü de havuza dâhil edin; balanced/random
`stimulus_prep.speakers`'daki **tüm** id'ler arasında seçer.)

Ardından:

```powershell
python -m mcgurk.config
```

Hata yoksa hazır. Konuşmacı 3, artık gerçek oturumlarda sunulur.

---

## Kontrol listesi

- [ ] Ham kayıtlar `assets/<klasör>/Vis-<t>_Aud-<t>.mp4` adıyla yerinde (her token)
- [ ] `stimulus_prep.speakers`'a `{id, source}` eklendi (benzersiz)
- [ ] `python tools/prepare_stimuli.py` hatasız bitti
- [ ] `python tools/verify_stimuli.py` çıkış 0
- [ ] `speaker_selection` (gerçek oturum) ve/veya `modules.*.speaker_id` (dev)
      istenen id'yi gösteriyor
- [ ] `python -m mcgurk.config` geçerli tasarım özeti basıyor
- [ ] (Donanımda) `python tools/run_module.py --module mcgurk --limit 4
      --speaker-id <id>` ile kısa duyum kontrolü yapıldı

## Sık yapılan hatalar

- **Yeni konuşmacının tokenları `stimulus_prep.tokens`'ta yok** → config yükleme
  anında "stimulus_prep.tokens içinde olmayan token" hatası. Aynı token setini
  kullanın.
- **`speaker_id` kullanılıyor ama `stimulus_prep.speakers`'ta yok** → "olmayan
  speaker_id" hatası. Önce B/2 adımını yapın.
- **`prepare_stimuli.py` koşulmadan config'te id gösterildi** → oturumda dosya
  bulunamaz. Önce hazırlık + doğrulama, sonra yönlendirme.
- **Uyumsuz mp4 elle eklendi** → yok sayılır; boru hattı yalnızca uyumlu
  çekimleri okur.
