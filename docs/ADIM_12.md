# ADIM 12 — Konuşmacı ve modül seçimi (operatör menüsü)

> **Bu bir Adım 12 promptudur.** `docs/steps.md` §A (değişmez kurallar) ve §B
> (her adımda işletilecek döngü: **önce plan-onay → uygula → doğrula → manuel
> test → commit**) bu adım için de aynen geçerlidir. Alt adımlara böl
> (12a/12b/12c/12d), her birinde ayrı plan-onay/test/commit. `progress.md`'yi her
> kapanışta güncelle. **Türkçe konuş, kod/commit İngilizce.**
>
> **Önce oku:** `mcgurk/ui/session.py` (oturum akışı ve `select_speaker`),
> `mcgurk/ui/login.py` (diyalog deseni), `mcgurk/config/schema.py`
> (doğrulayıcılar), `mcgurk/analysis/measures.py` (`session_measures`),
> `docs/KONUSMACI_DEGISTIRME.md` (konuşmacı ekleme yordamı).

## §0. Bağlam ve amaç

**İstek danışmandan geldi (2026-08-03):** (1) birden fazla konuşmacı olsun ve
menüden istediğimizi seçebilelim; (2) istediğimiz deneyleri koşabilelim —
"sadece McGurk", "sadece dikotik" gibi. Kullanıcı ayrıca **altı yeni konuşmacının
ham kaydını** verdi (`speakers/`, 2026-08-03) — bunlar projeye alınacak, yoksa
menüde seçilecek iki konuşmacı olurdu.

Bugün ikisi de yapılamıyor:

- **Konuşmacı** `speaker_selection.strategy` ile config'ten geliyor
  (`fixed` / `balanced` / `random`) ve oturum başında kod tarafında seçiliyor;
  operatörün seçeceği bir yer yok.
- **Modüller** `session.module_order`'daki her etkin modül sırayla koşuluyor
  (`mcgurk/ui/session.py`, `_run_flow`); oturuma özel alt küme diye bir şey yok.

**Amaç:** Operatör, oturum başında bir menüden **konuşmacıyı** ve **koşulacak
modülleri** seçebilsin; seçim veriye doğru biçimde yansısın; kısmi oturumlara
bölünen bir katılımcının sonuçları tek raporda birleşebilsin.

### Zaten var olan altyapı (yeniden yazılmayacak)

Bu adım büyük ölçüde **var olanı açığa çıkarmak**:

| Ne | Nerede | Durum |
|---|---|---|
| İki konuşmacının hazır uyaran seti | `stimuli/manifest.json` | **Hazır** — 6 video, 18 token, 12 dikotik, 54 gürültülü kayıt; konuşmacı 1 (`female_speaker_1`) ve 2 (`male_speaker_1`) |
| Konuşmacı seçme mantığı | `ui/session.py: select_speaker()` | `fixed`/`balanced`/`random` çalışıyor, saf ve testli |
| Modülün konuşmacısını ezme | `modules/*.plan_trials(speaker_id=…)` | Çalışıyor — modülün config'teki `speaker_id`'sini eziyor |
| Yeni konuşmacıların ham kaydı | `speakers/` (72 mp4) | **Elde** — biçim mevcut kayıtlarla birebir aynı |
| Konuşmacının kaydı | `trials.design_extra.speaker_id`, `db.session_speaker_id()` | Çalışıyor; resume geri okuyor |
| Koşmayan modülün analizde atlanması | `analysis/measures.py: session_measures()` | Çalışıyor — "koşmayan modül sonuçta yoktur" |
| Resume'un snapshot'tan kurulması | `ui/session.py`, `config_from_snapshot` | Çalışıyor |

**Eksik olan:** bir menü, konuşmacının okunabilir adı, oturuma özel modül alt
kümesi, ve alt kümenin veriye yazılması.

### Kullanıcı kararları (2026-08-03)

1. **Menü her oturumda çıkar, önceden dolu gelir.** Tam tasarım ve config'teki
   konuşmacı seçili gelir; Enter'a basmak bugünkü davranışın aynısıdır.
2. **Katılımcının konuşmacısı değiştirilebilir, ama uyarılır.** Menü önceki
   konuşmacıyı varsayılan yapar; başkası seçilirse onay ister ve
   `operator_notes`'a yazar.
3. **Katılımcı düzeyinde analiz bu adıma dahildir.** Modül seçimi, oturumların
   bölünmesini yaygınlaştıracağı için `session_measures` tek başına yetmez.

### Kapsam sınırları (2026-08-03, soruldu ve doğrulandı)

- **Konuşmacı oturum başınadır, modül başına değil.** Menüde tek konuşmacı
  seçilir ve o oturumun McGurk / AVSR / TBW / Dikotik modülleri onu kullanır.
  Motor modül başına farklı konuşmacıyı desteklerdi (`plan_trials` her modül
  için ayrı çağrılıyor), ama bir katılımcının modüllerini farklı yüzlerle
  ölçmek denek-içi karşılaştırmayı bozar. Farklı konuşmacı isteniyorsa ayrı bir
  oturum açılır.
- **Konuşmacı bir tasarım faktörü değildir.** "Aynı modülü iki konuşmacıyla
  arka arkaya koş" (füzyon oranı konuşmacıya göre değişiyor mu?) bu adımın
  dışında: modülün üreteci değişir, deneme sayısı ikiye katlanır ve bu ayrı bir
  adım olur.
- **Menü, config'te etkin olan modülleri listeler.** Bugün altısı da etkin,
  yani hepsi seçilebilir. Config'te kapatılmış bir modülü koşmak için önce
  config'ten açmak gerekir — config tasarımın kendisidir, menü onun içinden
  seçim yapar.
- **Konuşmacı listesi config'ten gelir, koddan değil.** Üçüncü bir konuşmacı
  eklemek `assets/`'e klasör + `stimulus_prep.speakers`'a bir satır +
  `tools/prepare_stimuli.py` demektir (`docs/KONUSMACI_DEGISTIRME.md`); menü onu
  kendiliğinden gösterir.

## §A12. Bu adıma özel değişmez kurallar

`steps.md` §A'ya **ek olarak**:

1. **Seçim, oturumun config anlık görüntüsüne yazılır.** Seçilmeyen modüller
   snapshot'ta `enabled: false`, `session.module_order` kısaltılmış,
   `speaker_selection` seçilen id'ye sabitlenmiş olur. Gerekçe: snapshot zaten
   "bu oturumun tasarımı" demek (§G); alt kümeyi oraya yazmak resume'u, analizi
   ve QC'yi **kendiliğinden** doğru kılar. Alternatif — `config/experiment.yaml`'ı
   her oturumda elle değiştirmek — tasarımı herkes için değiştirirdi.
   - Şema doğrulayıcıları bu kombinasyonu kabul ediyor (kontrol edildi):
     `_module_order_matches_modules`, `_screens_cover_the_session`,
     `_design_matches_the_stimulus_set`, `AVSRConfig._at_least_one_enabled_set`
     hepsi devre dışı modülü atlıyor. **Bir test bunu kalıcı kılmalı:** türetilen
     config `config_from_snapshot` turundan geçmeli.
2. **Veritabanı şeması değişmez** — sürüm 5'te kalır. Seçim zaten snapshot'ta ve
   `trials.design_extra.speaker_id`'de duruyor; yeni bir sütun ikinci bir doğruluk
   kaynağı olurdu.
3. **Varsayılan davranış değişmez.** Menü önceden dolu gelir; hiçbir şeye
   dokunmadan onaylamak Adım 8'deki oturumun aynısını koşar.
4. **Seçim mantığı GUI'den ayrı ve CI-testli** (§A10.3). Karar
   `mcgurk/config/selection.py`'de (PsychoPy'siz, PyQt6'siz); diyalog ince kabuk,
   `ui/login.py`'deki `build_participant` / `show_login_dialog` ayrımı gibi.
5. **Parametreler config'ten** (§A.9). Konuşmacı adları koda gömülmez —
   `stimulus_prep.speakers[].label`.
6. **cp1254-güvenli** metinler (`test_console_encoding.py`).
7. **Kısmi oturum gizlenmez.** QC raporu ve panel, yalnız bir alt kümenin
   koşulduğu oturumu açıkça işaretler; kısmi bir oturumu tam sanmak, eksik
   modülü "veri yok" diye okumaya yol açar.

## §C12. Alt adımlar

### ADIM 12a — Konuşmacı setinin genişletilmesi (2 -> 8)

**İlk sırada, çünkü** menünün varlık nedeni "birçok konuşmacı arasından seçmek";
menüyü iki girdiyle yazıp sonra sekize çıkarmak, asıl kullanım biçimini en sona
bırakırdı. Bir konuşmacının hazırlığı takılırsa da erken öğrenilir.

**Ham malzeme (incelendi, 2026-08-03):** `speakers/` altında 72 mp4 —
`Vis-<g>_Aud-<s>_Speaker-<n>.mp4`, g/s ∈ {ba, da, ga}, n = 1…8. Hepsi 640x480,
29.97 fps, 2.58 s, h264 + aac 44.1 kHz stereo; yani **mevcut kayıtlarla birebir
aynı biçim**, hattın tanımadığı hiçbir şey yok.

**İki tespit, işi küçültüyor:**

1. **Konuşmacı 1 ve 2 zaten projede.** `speakers/Vis-<t>_Aud-<t>_Speaker-1.mp4`
   üç uyumlu take için de `assets/female_speaker_1/Vis-<t>_Aud-<t>.mp4` ile
   **bayt bayt aynı** (sha256 ile doğrulandı); Speaker-2 de `male_speaker_1` ile.
   Kullanıcının "konuşmacı 1 projedeki kadın, 2 de erkek" demesi dosya
   düzeyinde doğrulanmış oldu. Yani bu ikisi yeniden kopyalanmaz — **yalnız 3–8
   eklenir**.
2. **Yalnız uyumlu (congruent) takeler alınır:** `Vis-<t>_Aud-<t>`, t ∈ {ba, da,
   ga} -> konuşmacı başına 3 dosya, 3–8 için **18 dosya**. Uyumsuz 48 dosya
   alınmaz: hazırlama hattı (Adım 2) zaten yalnız uyumlu takeleri okur ve
   uyumsuz sunumu **çalışma anında** sessiz videoya ayrı ses monte ederek üretir
   (§A.1). Hazır uyumsuz mp4'ler eski bir yeniden-mux'tır ve mevcut iki
   konuşmacıda da göz ardı ediliyor.

**Yapılacaklar:**

- `speakers/`'tan 18 uyumlu dosya `assets/<klasör>/Vis-<t>_Aud-<t>.mp4` adıyla
  ayıklanır (mevcut adlandırma kuralı). Ayıklamayı yapan küçük bir betik:
  **`tools/import_speakers.py`** — kaynak klasör + hedef eşlemesi alır, yalnız
  uyumlu takeleri kopyalar, konuşmacı 1/2 için hedef zaten varsa ve içerik
  aynıysa atlar, farklıysa **durur** (sessizce üzerine yazmak, hangi kaydın
  sunulduğunu belirsizleştirirdi).
- **Cinsiyetler kullanıcıdan alındı (2026-08-03):** 2, 3, 4 ve 7 **erkek**;
  1, 5, 6, 8 **kadın**. (Konuşmacıların birer karesinden oluşan tabaka
  üretilip soruldu.)

  | id | Cinsiyet | Klasör | Not |
  |---|---|---|---|
  | 1 | Kadın | `assets/speaker_1_female` | mevcut `female_speaker_1` |
  | 2 | Erkek | `assets/speaker_2_male` | mevcut `male_speaker_1` |
  | 3 | Erkek | `assets/speaker_3_male` | yeni |
  | 4 | Erkek | `assets/speaker_4_male` | yeni |
  | 5 | Kadın | `assets/speaker_5_female` | yeni |
  | 6 | Kadın | `assets/speaker_6_female` | yeni |
  | 7 | Erkek | `assets/speaker_7_male` | yeni |
  | 8 | Kadın | `assets/speaker_8_female` | yeni |

- **Klasör adı `speaker_<id>_<cinsiyet>` olur ve mevcut ikisi de yeniden
  adlandırılır.** Eski kural (`{cinsiyet}_speaker_{n}`) cinsiyet içinde sayıyor,
  yani konuşmacı **id 5** `female_speaker_2` klasöründe otururdu — hata ayıklayan
  birinin yanlış okuyacağı tam olarak budur. Yeni adda id başta ve
  `speaker_id` ile birebir aynı.
  - Yeniden adlandırmanın tek yan etkisi: eski geliştirme oturumlarının
    `config_snapshot`'ındaki `source` yolu artık diskte yok. Zararsız — o alanı
    yalnızca `tools/prepare_stimuli.py` okur ve o da **canlı** config'ten çalışır;
    çalışma anında hiçbir şey `source`'a bakmaz. Manifest'in `source.path`
    değerleri de bu adımda zaten yeniden üretiliyor.
- **Menü etiketleri** (`stimulus_prep.speakers[].label`): `"Konuşmacı 1 —
  Kadın"`, `"Konuşmacı 2 — Erkek"`, … Operatör listede cinsiyete göre seçer, id
  ise veriye yazılan şeydir.
- **`mcgurk/config/schema.py`**: `SpeakerSource.label: str | None` — operatöre
  gösterilen ad (12b'nin menüsü bunu okur; alan burada ekleniyor çünkü config
  bu adımda 8 girdiye çıkıyor). Opsiyonel, yoksa eski `config_snapshot`
  kayıtları yeniden kurulamazdı.
- **`config/experiment.yaml`**: `stimulus_prep.speakers` sekiz girdi + etiket.
  `speaker_selection.fixed_id` ve `modules.*.speaker_id` **1'de kalır** —
  varsayılan tasarım değişmiyor, yalnız seçenek çoğalıyor.
- `python tools/prepare_stimuli.py --force` ve `python tools/verify_stimuli.py`.
- `docs/KONUSMACI_DEGISTIRME.md` ve `README.md` sekiz konuşmacıya göre güncellenir.

**Kabul kriterleri:**
- [ ] `tools/import_speakers.py` yalnız uyumlu takeleri kopyalıyor; var olan ve
      **aynı** hedefi atlıyor, **farklı** hedefte duruyor — test
- [ ] Konuşmacı 1 ve 2'nin dosyaları **değişmiyor** (sha256 aynı) — test
- [ ] `manifest.json` sekiz konuşmacıyı içeriyor: 24 video, 72 token, 48 dikotik,
      216 gürültülü kayıt
- [ ] `python tools/verify_stimuli.py` temiz
- [ ] `python -m mcgurk.config` **aynı deneme sayısını** veriyor (797) —
      konuşmacı sayısı tasarımı büyütmez, oturum başına tek konuşmacı kullanılır
- [ ] `ruff` + `mypy` temiz; testler yeşil

**Manuel test:** ekran gerekmez (hazırlama + doğrulama konsolda). Yeni bir
konuşmacının gerçekten sunulduğu ekranlı test 12c'de.

### ADIM 12b — Seçim çekirdeği + CLI (GUI'siz, CI-testli)

**Yapılacaklar:**

- **`mcgurk/config/selection.py`** (yeni, saf):
  - `SessionSelection` — `speaker_id`, `modules: tuple[str, ...]`, `practice: bool`,
    `cross_hearing: bool`.
  - `available_speakers(config) -> list[SpeakerChoice]` — id + etiket + kaynak.
  - `available_modules(config) -> list[ModuleChoice]` — ad, Türkçe etiket, deneme
    sayısı (`config.trial_counts()`'tan).
  - `default_selection(config, *, session_count, seed) -> SessionSelection` —
    bugünkü davranış: tam tasarım + `speaker_selection` stratejisinin verdiği
    konuşmacı.
  - `apply(config, selection) -> ExperimentConfig` — derin kopya üzerinde
    §A12.1'i uygular; sonucu `model_validate` turundan geçirip döndürür.
  - `SelectionError(ConfigError)` — hiç ölçüm modülü seçilmemiş, bilinmeyen modül
    adı, hazır sette olmayan konuşmacı.
  - `select_speaker()` buraya **taşınır** (`ui/session.py:87`'den; zaten saf ve
    testli), `ui.session`'dan yeniden dışa verilir ki mevcut testler kırılmasın.
- **`mcgurk/config/schema.py`**: `SpeakerSource.label: str | None` — operatöre
  gösterilen ad. Opsiyonel, çünkü eski `sessions.config_snapshot` kayıtlarının
  yeniden kurulabilmesi gerekiyor.
- **`config/experiment.yaml`**: iki konuşmacıya etiket ("Kadın konuşmacı 1",
  "Erkek konuşmacı 1").
- **`mcgurk/ui/__main__.py`**: `--speaker N`, `--modules mcgurk,dichotic`,
  `--no-practice`, `--no-cross-hearing`, `--no-ask` (menüyü atla).
- **`mcgurk/ui/session.py`**: `run_session(..., selection=None, ask=True)`;
  seçim `start_session`'dan **önce** uygulanır, akışın tamamı türetilen config'i
  kullanır.

**Kabul kriterleri:**
- [ ] Alt küme uygulanınca `trial_counts()` yalnız seçilenleri sayıyor — test
- [ ] Türetilen config `config_from_snapshot` turundan geçiyor (her doğrulayıcı
      hâlâ memnun) — test
- [ ] Seçilen konuşmacı `speaker_selection.fixed_id` ve ilgili dört modülün
      `speaker_id`'sine yazılıyor; `required_speaker_ids()` onu içeriyor — test
- [ ] Ölçüm modülü seçilmeyince / bilinmeyen ad / hazır olmayan konuşmacı →
      `SelectionError` — test
- [ ] `--modules` + `--speaker` uçtan uca çalışıyor (`--dry-run` yok; `--limit`
      ile kısa koşu)
- [ ] `ruff` + `mypy` temiz; `pytest -m "not psychopy"` yeşil (yerel **ve**
      Qt'siz CI venv'inde)

**Manuel test:** ekran gerekmez (CLI bayrakları ekranlı testte 12b ile birlikte).

### ADIM 12c — Operatör menüsü (PsychoPy diyaloğu)

**Yapılacaklar:**

- **`mcgurk/ui/setup_dialog.py`** (yeni): girişten **sonra**, tam ekran pencere
  açılmadan **önce** bir `gui.DlgFromDict`. `login.py` deseni: `build_selection(
  fields, ...)` saf ve CI-testli, `ask_session_setup(...)` ince kabuk.
  - Alanlar: **Konuşmacı** (etiketli liste), her ölçüm modülü için onay,
    **Alıştırma**, **Çapraz dinleme kontrolü**.
  - Başlıkta/alanlarda bilgi: katılımcının **önceki konuşmacısı** ve konuşmacı
    başına oturum sayısı — elle dengeleme için (`balanced` stratejisi artık
    yalnızca ön seçim).
  - İptal → oturum başlatılmaz (girişteki davranışın aynısı).
- **Farklı konuşmacı uyarısı:** katılımcının önceki oturumlarında başka bir
  konuşmacı kullanılmışsa onay istenir ve seçim `operator_notes`'a yazılır.
- **Resume'da menü çıkmaz** — yarım oturum kendi snapshot'ıyla devam eder; menü
  göstermek, snapshot'ın taşıdığı tasarımla çelişebilecek bir seçim sunardı.
- **`mcgurk/db/database.py`**: `participant_speaker_id(participant_id)` ve
  `speaker_session_counts()` — salt okuma, şema değişmez.
- **`operator_notes`** artık seçimi de taşır (konuşmacı, koşulan modüller).

**Kabul kriterleri:**
- [ ] Menü girişten sonra çıkıyor, **tam tasarım ve config'teki konuşmacı
      önceden seçili**; onaylamak Adım 8 oturumunun aynısını koşuyor
- [ ] Tek modül seçilince yalnız o koşuyor; oturum `completed` bitiyor
- [ ] Kısmi oturumdan sonra aynı katılımcıyla yeni oturum açılınca "kaldığı
      yerden devam?" **sorulmuyor** (kısmi oturum tamamlanmış sayılır)
- [ ] Kısmi oturum yarıda kesilirse resume **yalnız o alt kümeyi** sürdürüyor
- [ ] Menüde **sekiz konuşmacı** etiketleriyle listeleniyor
- [ ] Konuşmacı 2 ve **yeni bir konuşmacı** (ör. 5) seçilince gerçekten o
      konuşmacının kayıtları sunuluyor — 12a'nın hazırladığı set ilk kez
      burada sunulur
- [ ] Farklı konuşmacı seçilince onay isteniyor ve nota yazılıyor
- [ ] Metinler Türkçe; `build_selection` CI-testli

**Manuel test:** ekran + ses gerekir (`TEST_ADIM_12.md`).

### ADIM 12d — Katılımcı düzeyinde analiz + panel + paketleme

**Yapılacaklar:**

- **`mcgurk/analysis/measures.py`**: `participant_measures(db, participant_code)`
  — katılımcının **tüm** oturumlarını modül modül birleştirir, her oturumun kendi
  snapshot'ı ve tohumuyla.
  - **Bir modül birden fazla oturumda varsa havuzlanmaz.** İkisi ayrı raporlanır
    ve tekrar olarak işaretlenir: aynı modülün iki koşumunu sessizce havuzlamak
    alışma etkisini veriye gömer.
- **`mcgurk/analysis/qc_report.py`**: kısmi oturum açıkça işaretlenir (§A12.7) —
  "kısmi oturum: yalnız X, Y koşuldu; katılımcının diğer oturumlarına da bakın".
- **`mcgurk/panel/`**: **"Katılımcı analizi"** düğmesi (`core` sarmalayıcısı +
  Panel sekmesinde buton). Panelin "Oturum başlat"ına **yeni bayrak gerekmiyor** —
  menü zaten her oturumda çıkıyor.
- **`.exe` yeniden derlenir.** Derleme `dist/McGurkSSD/`'yi tamamen sildiği için
  `stimuli/`, `config/`, `logs/`, `backups/` önce taşınır, sonra geri konur
  (Adım 11 dersi, `progress.md`). **`stimuli/` artık ~4 kat büyük** — taşımak
  ve geri koymak da o kadar uzun sürer.
- **`TEST_ADIM_12.md`**, `progress.md`, `CLAUDE.md` güncellenir.

**Kabul kriterleri:**
- [ ] `participant_measures` iki kısmi oturumu tek raporda birleştiriyor — test
- [ ] Aynı modül iki oturumda varsa havuzlanmıyor, işaretleniyor — test
- [ ] QC raporu kısmi oturumu işaretliyor — test
- [ ] Panelde "Katılımcı analizi" çalışıyor (offscreen smoke)
- [ ] `.exe`'de menü çıkıyor, konuşmacı 2 ve tek modül seçimi çalışıyor
- [ ] `ruff` + `mypy` temiz; testler yerel **ve** Qt'siz CI venv'inde yeşil

**Manuel test:** ekran gerekir; paketlenmiş app dahil.

## §D12. Bilinen riskler / açık noktalar

### Konuşmacı setinin genişlemesinden (12a)

- **Konuşmacı 3–8 hakkında cinsiyet dışında bilgi yok.** Cinsiyetler alındı
  (12a tablosu), ama yaş, kayıt koşulları ve mevcut ikisiyle aynı
  stüdyo/mikrofon olup olmadığı bilinmiyor. Dosya biçimleri birebir aynı (640x480,
  29.97 fps, 2.58 s, aac 44.1 kHz), bu da aynı çekim düzeneğine işaret ediyor ama
  kanıtlamıyor. **Danışmana sorulacak:** kayıtlar karşılaştırılabilir mi, ve
  konuşmacı seçimi **yöntem dokümanında** nasıl anlatılacak. Bir konuşmacı
  belirgin biçimde farklı kaydedilmişse, konuşmacı tercihi veriye karışır.
- **Cinsiyet artık bir seçim ekseni.** Sekiz konuşmacının dördü kadın dördü
  erkek; operatör menüden seçtiğinde farkında olmadan gruplar arasında cinsiyet
  dengesizliği yaratabilir (ör. SSD katılımcılarına hep erkek, kontrollere hep
  kadın konuşmacı). Menüdeki oturum sayısı sayacı bunu görünür kılar, ama
  **dengeleme kuralı danışman kararıdır** — `speaker_selection: balanced`
  bugün id sırasına göre döner, cinsiyete göre değil.
- **Hazır set ~4 kat büyüyor** (2 -> 8 konuşmacı). Konuşmacıya bağlı olmayan
  kısımlar (GIN segmentleri, gürültü, tonlar) paylaşılıyor, ama video/token/
  gürültülü/dikotik dosyaları konuşmacı başına çoğalıyor. Sonuçları: hazırlama
  daha uzun sürer, `stimuli/` klasörü operatörün `.exe` yanına kopyalayacağı
  ölçüde büyür ve `.exe` yeniden derlemesinde taşınacak veri artar. **Gerçek
  boyut 12a'da ölçülüp buraya yazılacak.**
- **Bir konuşmacının hazırlığı takılabilir.** Patlama (burst) zamanları her
  konuşmacı için ayrı ölçülüyor ve hat, `burst.alignment_tolerance_ms` ihlalinde
  **durur** (yarım hazırlanmış set diye bir şey yok — §A.12). Yeni bir
  konuşmacıda bu olursa seçenekler: o konuşmacıyı config'e almamak, ya da
  eşiği/kaynağı gözden geçirmek. Toleransı "geçsin diye" gevşetmek **yasak** —
  o eşik hizalamanın doğru yapıldığının tek kanıtı.
- **Deneme sayısı değişmez.** Oturum başına tek konuşmacı kullanıldığı için 797
  deneme / ~58.8 dk aynı kalır; konuşmacı sayısı tasarımı büyütmez, seçeneği
  büyütür.

### Sunum ve tasarım

- **Konuşmacı 2 hazır ama hiçbir oturumda koşulmadı** — 3–8 ise hiç hazırlanmadı
  bile. Sunum yolu bugüne dek yalnız konuşmacı 1 ile denendi; 12c'nin manuel
  testinde konuşmacı 2 **ve** yeni bir konuşmacı ile açık koşu var.
- **Konuşmacı 2'nin token'ları arasında 248 ms patlama farkı var** (Adım 2
  ölçümü). Hizalama düzeltiyor, ama `progress.md`'deki not duruyor: fotodiyot
  ölçümü (`01_av_gecikme_olcumu.md`) yapılırken **konuşmacı 2'nin bir uyumsuz
  denemesiyle de bir kontrol koşulmalı**. Bu adım o notu daha acil kılıyor,
  çünkü artık konuşmacı 2 (ve altı yenisi) gerçekten sunulacak. Yeni
  konuşmacıların patlama yayılımı 12a'da ölçülünce, en geniş yayılımlı olan da
  bu kontrole eklenmeli.
- **Denek-içi konuşmacı karışması.** Kullanıcı kararı: uyar ama izin ver. Bir
  katılımcının modülleri iki farklı konuşmacıyla ölçülürse bu bir tasarım
  sorunudur; kod görünür kılar, kararı operatör verir.
- **Her oturumda bir ekran daha.** Önceden dolu geldiği için maliyeti bir Enter;
  yine de akışa eklenen ilk "operatör kapısı"dır.
- **`balanced` / `random` stratejileri artık son söz değil**, menünün ön
  seçimidir. Dengeleme elle yapılacaksa menüdeki oturum sayısı sayacı buna
  hizmet eder.
- **Kısmi oturum + `data_collection` modu.** Yasaklanmadı: bir katılımcının
  oturumu güne bölmek gerçek bir klinik ihtiyaç. Karşılığı §A12.7'deki
  işaretleme ve katılımcı düzeyinde analiz.
- **§F.1 hâlâ açık.** Modül seçimi, tekrar sayısı kararını (Adım 11'in Ayarlar
  sekmesi) etkilemez; ikisi bağımsız.

## §E12. Kapanış

Adım 12 bitince:
1. Paketlenmiş app'i yeniden derle ve menüyü **paketlenmiş halde** doğrula
   (`dist/` içeriğini önce taşımayı unutma).
2. `progress.md` ve `CLAUDE.md` güncelle.
3. Sonrası değişmedi: **prova oturumu** → varsa düzeltme → `develop → master`
   merge + `git tag v1.0.0`.
