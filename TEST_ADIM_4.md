# Adım 4 Manuel Test — Modül 1: McGurk

Otomatik testler (381 → **451 test**, ruff + mypy temiz; CI alt kümesi 401)
zaten koştu ve geçti. Kendim koşabildiğim şeyleri de koştum:

- `tools/run_module.py --dry-run` — 140 denemelik tasarım, 23 uyaran dosyası,
  hücre tablosu (aşağıda Test 1 aynısını sizde tekrarlıyor).
- `tests/test_modules_block.py` — **gerçek pencere ve gerçek ses aygıtıyla**
  blok döngüsü, betiklenmiş bir klavyeyle: zamanlama kaydı, iki RT, füzyon
  kategorisi, zaman aşımı, blok sınırında commit. Tuşa basmak dışındaki her
  şey burada doğrulandı.
- Canlı yolun bir denemelik dumanı: oturum satırı, yedek, özet
  (`audio_backend: ptb`, `measured_refresh_hz: 74.94`, `actual_soa_ms: 0.04`).
- **Test 8'in insan gerektirmeyen kısmı** — 140 deneme, tam ekran, simüle
  yanıtlarla: süre, blok yapısı, düşen kare ve SOA istatistiği (Test 8'e
  bakın).

**Burada kalan şeyler tuşa basmayı, ekrana bakmayı ve kulakla dinlemeyi
gerektiriyor** — yani sizin yapmanız gerekenler.

---

## Ön koşullar

- [ ] Conda ortamı: `C:\Users\tayla\miniconda3\envs\mcgurk\python.exe`
      (tam yolla çalıştırmak her koşulda çalışır)
- [ ] `stimuli/` hazır (Adım 2). Değilse: `python tools/prepare_stimuli.py`
- [ ] **Kulaklık açık ve bağlı.** `audio.device` artık
      `"Kulaklıklar (2- WH-1000XM4)"` — Bluetooth kapalıysa aygıt listede
      görünmez ve koşu şu hatayla durur:
      ```
      Ses aygıtı açılamadı (aygıt: Kulaklıklar (2- WH-1000XM4), ...)
      Aygıt gerçekten bağlı mı? ...
      ```
      Aygıtları listelemek için (indeksler değişir, isim sabit kalır — config
      bu yüzden isim kullanıyor):
      ```bash
      python tools/timing_selftest.py --devices
      ```
      Tek seferlik başka bir aygıt denemek için her komuta
      `--device "<aygıt adı>"` ekleyebilirsiniz.
- [ ] Kulaklık takılı, sağ/sol doğru
- [ ] Klavyede **1–9** tuşları ve **ESC** çalışıyor

---

## Test 1: Tasarımı denetleyin (ekran gerekmez, en önce bu)

**Komut:**
```bash
python tools/run_module.py --module mcgurk --dry-run --seed 20260726
```

**Beklenen çıktının kritik satırları:**
```
  Deneme sayısı        : 140
  Config'in beklentisi : 140
...
  combination_pair    Vis-ba/Aud-ga         left    5 dB        10
  congruent_ba        Vis-ba/Aud-ba         left    quiet        5
  fusion_pair         Vis-ga/Aud-ba         right   quiet       10
  (20 satır: 5 çift × 2 gürültü × 2 kulak)
...
  23 ayrı dosya, tamamı yerinde.
...
  [1] BA ... [9] DIGER  <-- serbest metin
```

**Kontrol edilecek:**
1. **140 = 140.** İki sayı ayrışırsa üreteç ile config'in hesabı çelişiyor;
   araç bu durumda çıkış kodu 1 veriyor.
2. Hücre tablosunda **20 satır** var ve uyumsuz çiftlerde `n = 10`, uyumlu
   kontrollerde `n = 5`.
3. "İlk 12 deneme" listesinde koşullar **karışık** görünüyor — aynı etiket
   üst üste yığılmıyor, gürültülü/sessiz ve sağ/sol birbirine karışmış.
4. "Örnek" sütununda gürültülü denemelerde 1/2/3 dönüyor, sessizlerde `—`.
5. Aynı komutu ikinci kez koşun: **çıktı birebir aynı** olmalı (aynı tohum).
   `--seed 99` verin: sıra değişmeli, hücre tablosu değişmemeli.

**Başarısızsa:** dosya eksikse `python tools/prepare_stimuli.py`; sayı
uyuşmazsa bana çıktının tamamını gönderin.

---

## Test 2: Yanıt ekranı okunabilir mi (ekran gerekir)

**Komut** (tam ekran, 4 deneme):
```bash
python tools/run_module.py --module mcgurk --limit 4 --seed 20260726
```

Akış her denemede: **sabitleme haçı (1 s) → video + ses → yanıt ekranı**.

**Kontrol edilecek:**
1. Yanıt ekranında üstte **"Ne duydunuz?"**, altında iki satır hâlinde
   dokuz seçenek: `1 BA … 9 DIGER`. Tuş numarası her seçeneğin **üstünde**.
2. Metinler ekranın dışına taşmıyor, üst üste binmiyor (1920×1080'de
   5 + 4 sütun). Taşıyorsa bana ekran görüntüsü gönderin — ızgara
   parametreleri koddan ayarlanabilir.
3. Bir tuşa bastığınızda seçtiğiniz seçenek **kısa süre sarıya** dönüyor ve
   deneme bitiyor. Bu yalnızca "tuş algılandı" demek — **doğru/yanlış geri
   bildirimi yok** ve olmamalı (§A.10, talep karakteristiği).
4. Video **yanıt ekranına taşmıyor**: seçenekler geldiğinde ekranda video
   karesi kalmıyor, ses susmuş oluyor.
5. Sabitleme haçı denemeler arasında görünüyor; ekran video ile yanıt ekranı
   arasında bir an boşalıyor.

---

## Test 3: Uyaran gerçekten lateralize mi (kulak gerekir)

Aynı koşuyu kullanın (Test 2). Dry-run çıktısındaki "Kulak" sütunundan hangi
denemenin hangi kulağa gittiğini önceden biliyorsunuz.

**Kontrol edilecek:**
1. `left` denemesinde ses **yalnızca sol** kulakta, `right` denemesinde
   **yalnızca sağ** kulakta. Karşı kanal tam sessiz (motor karşı kanala tam
   sıfır yazıyor, kısılmış değil).
2. `5 dB` denemelerinde konuşmanın üzerinde gürültü var, `quiet` denemelerinde
   yok. Gürültü **yumuşak** başlıyor (250 ms rampa), tık sesi yok.
3. Ses ile dudak hareketi birlikte — belirgin bir kayma yok. (Mutlak gecikme
   ölçümü fotodiyotla yapılacak; burada bakılan şey "gözle görülür kayma
   var mı".)

**Not:** Bluetooth kulaklıkla (WH-1000XM4) ses-dudak yargısı güvenilir değil —
100–300 ms değişken gecikme ekliyor. Kablolu bir kulaklık varsa bu maddeyi
onunla tekrarlayın.

---

## Test 4: DIGER akışı (serbest metin)

**Komut:**
```bash
python tools/run_module.py --module mcgurk --limit 2 --seed 7
```

Her iki denemede de **9** tuşuna basın.

**Kontrol edilecek:**
1. "Duyduğunuz sesi yazıp Enter'a basın:" yazısı çıkıyor, altında yazdığınız
   harfler sarı görünüyor.
2. Harf yazın (`bga` gibi), **backspace** siliyor, **Enter** denemeyi
   bitiriyor.
3. Hiçbir şey yazmadan 5 s beklerseniz deneme yine bitiyor (boş metin).
4. Türkçe karakter (`ğ`, `ş`) **kabul edilmiyor** — bu bilinçli: alan hece
   transkripsiyonu için, PsychoPy'nin Türkçe tuş adları güvenilir değil.

Sonra veritabanını kontrol edin (aşağıdaki Test 7).

---

## Test 5: Zaman aşımı

**Komut:**
```bash
python tools/run_module.py --module mcgurk --limit 1 --seed 3
```
Yanıt ekranında **hiçbir tuşa basmayın.**

**Beklenen:**
```
Zaman aşımı            : 1
Yanıtlar:
  NONE            1  (%100.0)
```

*(Adım 5'te başlık "Kategoriler:" → "Yanıtlar:" oldu: özet artık AVSR'nin
DOĞRU/YANLIŞ sayımını da basıyor ve o bir kategori değil.)*

**Kontrol edilecek:** 5 saniye sonra ekranda kısa süre **"Yanıt alınamadı"**
görünüyor ve deneme bitiyor. Veritabanında bu deneme **yanıt satırı olmadan**
duruyor (Test 7'de görünecek) — Adım 1'in kararı: zaman aşımının kaydı,
satırın yokluğudur.

---

## Test 6: ESC her aşamada çalışıyor

Aynı komutu üç kez koşun ve ESC'ye şu üç yerde basın:

| Ne zaman | Beklenen |
|---|---|
| Sabitleme haçı görünürken | Anında çıkış |
| **Video ortasında** | Anında çıkış, ses de anında susuyor |
| Yanıt ekranında | Anında çıkış |

**Her üçünde de beklenen çıktı:**
```
  Oturum ESC ile kesildi.
```
ve çıkış kodu 2 (`echo $?` / `echo $LASTEXITCODE`).

**Kontrol edilecek:** oturum "tamamlandı" diye raporlanmıyor; veritabanında
`sessions.status = aborted` ve o ana kadarki denemeler **korunmuş** oluyor
(blok `aborted` olarak kapanıp commit ediyor).

---

## Test 7: Veritabanına ne yazıldı

Yukarıdaki koşulardan sonra:

**Oturumlar:**
```bash
python -c "import sqlite3; c=sqlite3.connect('data/mcgurk.sqlite'); c.row_factory=sqlite3.Row; [print(dict(r)) for r in c.execute('SELECT session_id,seed,status,audio_backend,audio_device,round(measured_refresh_hz,2) AS hz FROM sessions ORDER BY session_id')]"
```

**Denemeler ve yanıtlar:**
```bash
python -c "import sqlite3; c=sqlite3.connect('data/mcgurk.sqlite'); c.row_factory=sqlite3.Row; [print(dict(r)) for r in c.execute('SELECT trial_index,condition_label,visual_token,audio_token,ear,snr_db,speaker_id,noise_instance,round(actual_soa_ms,2) AS soa,dropped_frames,raw_response,free_text,category,is_correct,round(rt_from_burst_ms) AS rt_burst,round(rt_from_prompt_ms) AS rt_prompt FROM v_trials_flat ORDER BY trial_id')]"
```

**Kontrol edilecek:**
1. `audio_backend = ptb`, `audio_device` gerçekten kullandığınız aygıt,
   `measured_refresh_hz ≈ 75`.
2. Her denemede `speaker_id = 1`; gürültülü denemelerde `noise_instance`
   1–3 arası, sessizlerde `None`.
3. **`is_correct` her satırda `None`** — uyumlu kontrollerde de (§A.10).
   Herhangi birinde 0/1 görürseniz bu bir hatadır (veritabanı tetikleyicisi
   de reddetmeli).
4. `category`: `1` bastığınız denemede işitsel token `ba` ise `AUDITORY`;
   Vis-ga/Aud-ba denemesinde `2` (DA) bastıysanız **`FUSION`**.
5. `rt_from_prompt_ms` bastığınız süreye makul biçimde yakın (yarım saniye
   civarı), `rt_from_burst_ms` ondan **büyük** (patlamadan sonra videonun
   kalanı da geçiyor). İkisi de negatif olmamalı.
6. Zaman aşımı denemesinde `raw_response`, `category`, iki RT de `None`, ama
   satır **var** ve `actual_soa_ms`/`dropped_frames` dolu.
7. `dropped_frames` çoğunlukla 0. Sürekli 1–2 görüyorsanız bana söyleyin.

---

## Test 8: Tam blok — **çoğu yapıldı, size yalnızca algı kısmı kaldı**

140 denemeyi simüle yanıtlarla (sabit tuş, 700 ms) tam ekran koşturdum. Ölçülen:

| | Sonuç |
|---|---|
| Süre | **11.69 dk** — 5.01 s/deneme (config tahmini 14.0 dk) |
| Bloklar | 60 / 60 / 20, üçü de `completed`, her biri ayrı commit |
| Düşen kare | **0** (en kötü kare aralığı 15.58 ms; kare 13.33 ms, sınır 20.00) |
| `TimeFailed` / `XRuns` | **0** |
| `actual_soa_ms` | ort **−0.061 ms**, SD 0.213, aralık [−1.07, +0.50] |
| Yanıt satırı | 140/140, `is_correct` hepsinde NULL |

Yani madde 1 (blok yapısı), 2 (süre) ve 4 (kare/ses bozulması) kapandı. Süre
tahmini gerçekçi çıktı: gerçek RT 1–1.5 s olacağı için modülü **~12–13.5
dakika** olarak planlayabilirsiniz.

**Size kalan: madde 3 — kategori dağılımı.** Simüle yanıt bir algı değil, o
yüzden füzyonun *size* olup olmadığını ancak siz görebilirsiniz. Bunun için 140
deneme gerekmiyor:

```bash
python tools/run_module.py --module mcgurk --limit 20 --seed 20260726
```

**Kontrol edilecek:** Vis-ga/Aud-ba denemelerinde ("fusion_pair", dry-run
çıktısından hangi sıradakiler olduğunu görebilirsiniz) gerçekten "DA" ya da
"TA" duyuyor musunuz? Duyuyorsanız etki çalışıyor. Bu bir veri noktası değil —
etkiyi bildiğiniz için kendinizde ölçmek zaten mümkün değil; bakılan şey
uyaranların füzyonu **tetikleyebilecek** kalitede olup olmadığı.

Tam 140 denemeyi kendiniz koşmak isterseniz (yorgunluk ve gerçek süreyi
hissetmek için) komut şu — ama yukarıdaki ölçümler zaten elde:

```bash
python tools/run_module.py --module mcgurk --seed 20260726
```

**Not:** Bu koşu `data/mcgurk.sqlite` içine `DEV01` kodlu bir geliştirme
katılımcısı yazar ve kapanışta `backups/` altına yedek alır. Gerçek veri
değil; Adım 8 gerçek giriş ekranını getirecek.

---

## Kabul kriterleri (steps.md §C Adım 4)

- [ ] Config'teki AV çiftleri değiştirilince deneme listesi değişiyor
      *(otomatik test + Test 1)*
- [ ] Aynı seed → aynı deneme sırası *(otomatik test + Test 1.5)*
- [ ] Kategorizasyon tablosu doğrulanmış; Vis-ga/Aud-ba/"DA" → `FUSION`
      *(otomatik test + Test 7.4)*
- [ ] Deneme sayısı ve süre tahmini config'ten doğru hesaplanıyor *(Test 1)*
- [ ] Tüm denemeler DB'ye zamanlama kayıtlarıyla yazılıyor *(Test 7)*
- [ ] Yanıt ekranı okunabilir, video yanıt penceresine taşmıyor *(Test 2)*
- [ ] Lateralizasyon ve gürültü kulakta doğrulandı *(Test 3)*
- [ ] `DIGER` serbest metin akışı çalışıyor *(Test 4)*
- [ ] Zaman aşımı yanıt satırı üretmiyor, deneme kayıtta kalıyor *(Test 5)*
- [ ] ESC üç aşamada da çalışıyor, oturum `aborted` *(Test 6)*

---

## Bunlar bu adımda YAPILMAYACAK

- **Mola ekranı, yönerge, alıştırma bloğu, katılımcı girişi** — Adım 8.
  `tools/run_module.py` bir geliştirme aracı; gerçek oturum akışı o adımda.
- **Fotodiyot ölçümü** (`docs/01`) — tüm kod bittikten sonra.
  `timing.system_av_offset_ms` hâlâ `null`, motor 0 kabul edip uyarı basıyor,
  yani `actual_soa_ms` mutlak gecikmeyi içermiyor.
- **Kalibrasyon** (`docs/02`) — ses seviyesi henüz mutlak SPL'e bağlı değil.
- **Fare ile yanıt** — steps.md'de opsiyonel; klavye ile gidildi
  (gerekçe: `responses.input_device` sütunu duruyor, istenirse eklenir).
