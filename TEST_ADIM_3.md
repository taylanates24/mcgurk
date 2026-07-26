# Adım 3 Manuel Test — A/V senkron çekirdeği

Otomatik testler (301 → **375 test**, ruff + mypy temiz) zaten koştu ve geçti.
Burada yalnızca **ekran, ses veya donanım gerektiren** ve benim yerinize
yapamayacağım testler var.

Kademe 2 için gereken donanım (ses arayüzü + loopback kablosu) sizde yok;
o testler **"Donanım geldiğinde"** başlığı altında toplandı ve şimdi
yapılmayacak.

---

## Ön koşullar

- [ ] Conda ortamı aktif: `C:\Users\tayla\miniconda3\envs\mcgurk`
      (tam yolla çalıştırmak her koşulda çalışır)
- [ ] `stimuli/` hazır (Adım 2). Değilse: `python tools/prepare_stimuli.py`
- [ ] Kulaklık takılı ve **sağ/sol doğru takılmış** (Test 3 bunu ölçüyor)
- [ ] Ses seviyesi rahat bir düzeyde — kalibrasyon henüz yok, uyaranlar
      −23 dBFS civarında
- [ ] **Test 0 yapıldı** (aşağıda) — aksi hâlde ses hiç duyulmaz

---

## Test 0: Ses çıkış aygıtını seçin (bunu atlarsanız ses duymazsınız)

**Komut:**
```bash
python tools/timing_selftest.py --devices
```

**Bu makinede çıkan liste:**
```
  [6] SPDIF Arabirimi (Realtek USB Audio)
  [7] Kulaklıklar (2- WH-1000XM4)
  [8] ASUS VZ27V -2 (HD Audio Driver for Display Audio)

  config/experiment.yaml -> audio.device: null
  PTB listedeki İLK aygıtı kullanıyor.
```

`audio.device` boş olduğu için PTB **listedeki ilk aygıtı** — hiçbir şeyin
bağlı olmadığı SPDIF dijital çıkışını — seçiyor. Ses bu yüzden duyulmuyor.
Sessizlik burada şanslı sonuç: şanssız olanı, oturumun farkına varılmadan
monitör hoparlöründen toplanmasıydı.

**Yapılacak — iki seçenek:**

Tek seferlik denemek için (config'e dokunmadan):
```bash
python tools/timing_selftest.py --demo --device "Kulaklıklar (2- WH-1000XM4)"
```

Kalıcı olarak — `config/experiment.yaml`:
```yaml
audio:
  device: "Kulaklıklar (2- WH-1000XM4)"
```

**Kontrol edilecek:** komutu tekrar koşunca seçtiğiniz aygıtın yanında
`<-- config` işareti çıkmalı.

> **Veri toplamada bu boş bırakılamaz.** `mode: data_collection` config kapısı
> `audio.device` doluluğunu zaten şart koşuyor (Adım 1), yani gerçek oturumda
> bu hata oluşamaz. Sorun yalnızca `development` modunda görünür.

> ⚠️ **WH-1000XM4 Bluetooth'tur ve gerçek veri toplama için uygun değildir.**
> Bluetooth 100–300 ms gecikme ekler ve bu gecikme **sabit değildir**; TBW
> modülünün ölçtüğü şey tam olarak ±50 ms mertebesinde farklardır. Ayrıca
> kulaklığın kendi DSP'si (gürültü engelleme, DSEE, EQ) seviyeyi ve spektrumu
> değiştirir, yani `02_kalibrasyon.md` ölçümü anlamını yitirir. Kablolu
> kulaklık gerekiyor — kulaklık tipi kararı zaten açık (`steps.md` §F.3,
> insert kulaklık öneriliyor). **Bugünkü testler için** Bluetooth yeterlidir,
> ama aşağıda hangi kontrollerin geçerli kalmadığı işaretlendi.

---

## Test 1: Kademe 1 — zamanlama zincirinin yazılım tarafı

**Komut:**
```bash
python tools/timing_selftest.py --level 1 --n 20 --device "Kulaklıklar (2- WH-1000XM4)"
```

Tam ekran siyah bir pencere açılır, birkaç saniye sürer, kendiliğinden kapanır.
Kısa klikler duyulur.

**Beklenen çıktı (bu makinede alınan gerçek değerlerle):**
```
Kademe 1 — donanımsız kontroller
  Ses backend'i    : ptb (doğrulandı)
  Aygıt            : Kulaklıklar (2- WH-1000XM4)
  Örnekleme hızı   : 48000 Hz
  Kanal            : 2
  Gecikme sınıfı   : 3
  Ölçülen yenileme : 75.006 Hz (kare 13.332 ms)

Flip zamanlaması
  Hedeften sapma: ort +0.181 ms, SD 0.199 ms, maks |0.447| ms, n=10

Ses planlaması
  Bildirilenden sapma: ort +0.000 ms, SD 0.000 ms, maks |0.000| ms, n=10
  Zaman bildirmeyen: 0/10
  Kaçırılan zamanlama (TimeFailed): 0
  Buffer under-run (XRuns)        : 0

Sonuç
  Tüm kontroller geçti.
```

**Kontrol edilecek:**
1. **`Ses backend'i : ptb (doğrulandı)`** — başka bir şey yazıyorsa deney
   çalıştırılamaz, program zaten durur.
2. **`Örnekleme hızı : 48000 Hz`.** 44100 çıkarsa program açık hatayla durur:
   Windows > Ses > Aygıt özellikleri > Gelişmiş'ten aygıtı 48000 Hz'e alın.
   Aksi hâlde PsychoPy her uyaranı yeniden örneklerdi.
3. **Flip sapması** bir kareden (13.3 ms) küçük olmalı. Değilse vsync kapalı
   ya da arka planda kompozitör var.
4. **TimeFailed ve XRuns sıfır olmalı.** Sıfır değilse ses aygıtı paylaşımlı
   modda ya da sistem yükü fazla — o denemelerin ses onset'i kayıtta yazandan
   farklıdır.
5. **`Tüm kontroller geçti`** ve çıkış kodu 0.

> Yenileme hızı uyuşmazlığı **çözüldü**: monitör 75 Hz ölçülüyordu, config 60
> diyordu; `display.expected_refresh_hz: 75` yapıldı. Deney başka bir
> monitörde koşacaksa bu değer o makineye göre güncellenmeli — kontrol ölçüm
> yaptığı için yanlış değer kendini gösterir.

**Başarısızsa:** çıktıdaki "SORUN" satırlarını bana iletin.

---

## Test 2: Demo — gerçek uyaranlarla altı deneme

**Komut** (Test 0'da config'e aygıt yazdıysanız `--device` kısmı gereksiz):
```bash
python tools/timing_selftest.py --demo --device "Kulaklıklar (2- WH-1000XM4)"
```

Tam ekran, altı deneme arka arkaya sunulur (~30 saniye). ESC ile her an
kesebilirsiniz.

**Sırasıyla görecekleriniz:**

| # | Deneme | Ne görmeli / duymalısınız |
|---|---|---|
| 1 | AV uyumlu | Kadın konuşmacı "ba" der, ses ve dudak **birlikte** |
| 2 | McGurk, sol kulak | Dudak "ga", ses "ba" — ses **yalnızca sol kulaktan** |
| 3 | SOA −200 ms | Ses, dudak hareketinden **belirgin biçimde önce** gelir |
| 4 | SOA +200 ms | Ses, dudak hareketinden **belirgin biçimde sonra** gelir |
| 5 | A-only, sağ kulak | Ekranda yalnızca **haç**, ses **yalnızca sağ kulaktan** |
| 6 | V-only | Video oynar, **hiç ses yok** |

**Beklenen özet tablosu:**
```
  Deneme                                Mod   Gerçekleşen   Nominal     Düşen kare / maks
  AV uyumlu (SOA 0)                     AV           -5.0         —           0 / 13.8 ms
  McGurk (Vis-ga / Aud-ba), sol kulak   AV           +0.3         —           0 / 13.8 ms
  AV, SOA −200 ms (ses önce)            AV         -201.0    -200.0           0 / 13.6 ms
  AV, SOA +200 ms (ses sonra)           AV         +197.7    +200.0           0 / 13.6 ms
  A-only, sağ kulak                     A               —         —           0 / 13.9 ms
  V-only                                V               —         —           0 / 13.9 ms
```

**Kontrol edilecek — kulakla (Bluetooth kulaklıkta da geçerli):**
1. **Deneme 2'de ses yalnızca SOL kulakta.** Sağ kulakta hiçbir şey
   duyulmamalı (kısık değil, **hiç**). Duyuyorsanız ya kulaklık ters takılı ya
   da lateralizasyon bozuk — bana bildirin.
2. **Deneme 5'te ses yalnızca SAĞ kulakta.** Aynı kontrol.
3. **Deneme 6'da hiç ses yok** ve video normal oynuyor.
4. Videolar **ekranın tam ortasında** (§A.13).
5. Deneme 5'te ekranda haç var ve deneme **sesin süresi kadar** sürüyor
   (~2.6 s), daha uzun değil.
6. **Deneme 3 ile deneme 4 arasında belirgin fark var.** İkisi 400 ms
   ayrıdır; aynı geliyorsa SOA hiç uygulanmıyor demektir.

**Kontrol edilecek — yalnızca KABLOLU kulaklıkta anlamlı:**
7. Deneme 1'de ses ve dudak hareketi **birlikte**; deneme 3'te ses dudaktan
   **önce**, deneme 4'te **sonra**. Bluetooth kulaklıkta üçü de geç gelir
   (kulaklık 100–300 ms ekler) ve bu yargı yazılım hakkında bir şey söylemez.
   Kablolu kulaklık geldiğinde bu üç maddeyi tekrar bakın.

**Kontrol edilecek — tabloda (kulaklık tipinden bağımsız):**
8. **"Gerçekleşen" ile "Nominal" arası fark bir kareden (13.3 ms) küçük
   olmalı.** Yukarıdaki gerçek koşuda −201.0 / −200.0 ve +197.7 / +200.0
   çıktı, ikisi de sınırın içinde. Bu tablo yazılımın ne yaptığını gösterir;
   kulaklığın eklediği gecikme buraya girmez (o, fotodiyot ölçümünün işi).
9. **Düşen kare 0 olmalı.**
10. İlk denemede "flip sapması" birkaç ms çıkabilir (yukarıda +5.13 ms oldu).
   Bu ilk video çözümlemesinin ısınma maliyetidir ve tabloda −5.0 ms olarak
   görünür. Sonraki denemelerde 1–2 ms'e iner. Gerçek oturumda alıştırma
   bloğu (Adım 8) bu ısınmayı zaten karşılayacak. **Her denemede** birkaç ms
   sapma varsa bu normal değil, bildirin.

**Başarısızsa:** hangi denemede ne olduğunu ve tabloyu iletin.

---

## Test 3: Kulaklık tarafı doğru mu (30 saniye)

Test 2'nin 2. ve 5. denemeleri lateralizasyonu ölçer, ama yalnızca kulaklığın
**doğru takılı olduğunu** varsayarak. Kulaklığı ters takarsanız test yine
"geçer" ve sonuçlar sessizce ters çıkar.

**Yapılacak:** Test 2'yi bir kez daha koşun (aynı komut), bu sefer kulaklığı
**bilerek ters takarak**. Deneme 2'nin sağ kulağınızda, deneme 5'in sol
kulağınızda çıkması gerekir.

**Neden:** SSD çalışmasında kulak yönü bağımsız değişkendir; ters takılmış bir
kulaklık, hipotezi taşıyan değişkeni tersine çevirir ve veriden bu asla
anlaşılmaz. Adım 8'in çapraz dinleme kontrolü bunu her oturumda kontrol
edecek, ama şimdilik elle doğrulanmalı.

---

## Test 4: ESC her aşamada çalışıyor mu

**Komut:**
```bash
python tools/timing_selftest.py --demo --device "Kulaklıklar (2- WH-1000XM4)"
```

**Yapılacak:** video oynarken (deneme 1 veya 2'nin ortasında) **ESC**'ye basın.

**Beklenen:**
```
  Demo kullanıcı tarafından kesildi (ESC).
```
Pencere kapanır, ses **anında** susar, çıkış kodu 0.

**Kontrol edilecek:** ses ESC'den sonra çalmaya devam etmemeli. Adım 0'da bu
bir hataydı; motor artık `finally` bloğunda sesi durduruyor.

---

## Test 5: Kademe 3 yönergesi okunabiliyor mu

**Komut:**
```bash
python tools/timing_selftest.py --level 3
```

**Beklenen:** fotodiyot ölçümünün **yapılmadığı**, `docs/01_av_gecikme_olcumu.md`
scriptlerine yönlendirdiği ve tüm kod bittikten sonra yapılacağı yazan bir
metin. Ekran açılmaz, ses çıkmaz.

**Kontrol edilecek:** metnin sonundaki projeye özel not — doğrulama koşusuna
konuşmacı 2'nin bir uyumsuz denemesinin de eklenmesi gerektiği (Adım 2'nin
248 ms bulgusu).

---

## Donanım geldiğinde: Kademe 2 (loopback)

**Şimdi yapılmayacak.** Kod yazıldı ve analiz tarafı sentetik kayıtlarla test
edildi (bilinen 3 ms jitter enjekte edilip geri okunuyor); eksik olan tek şey
kablo.

**Gerekenler:** ayrı giriş/çıkışı olan bir USB ses arayüzü (Behringer UMC22,
Focusrite Scarlett Solo) ve kulaklık çıkışını girişe bağlayan bir kablo.
Ayrıntı: `docs/01_av_gecikme_olcumu.md` §2 ve §4.

**Yordam:**
```bash
python tools/timing_selftest.py --level 2 --play --n 20
```
Script "Kaydı ŞİMDİ başlatın" der; Audacity'de 48 kHz stereo kayda basıp
Enter'a basın. 20 klik çalar. Kaydı durdurup 24-bit PCM WAV olarak kaydedin.

```bash
python tools/timing_selftest.py --level 2 --analyze kayit.wav
```

**Beklenen çıktı:**
```
  Klik             : 20/20
  Sabit gecikme    : +XXX.XXX ms (kayıt başlangıcı + çıkış/giriş gecikmesi)
  Jitter (SD)      : 0.XXX ms
  Değerlendirme    : İYİ (< 1 ms)
```

**Kabul ölçütü** (`docs/01` §7 ile aynı): SD < 1 ms iyi, 1–3 ms kabul
edilebilir, > 3 ms sorunlu.

**Neden bu test önemli:** kademe 1 yazılıma "doğru şeyi yapıyor musun?" diye
sorar ve yazılım "evet" der. Bu makinede PTB'nin bildirdiği başlangıç zamanı,
istenen zamanın **birebir aynısı** çıkıyor — yani bağımsız bir ölçüm değil,
isteğin yankısı. PTB sessizce geri düşerse veya `when=` yok sayılırsa kademe 1
bunu göremez; kademe 2 görür.

---

## Kabul kriterleri

- [ ] Test 0: `audio.device` seçildi (config'e yazıldı ya da `--device` ile
      verildi); Bluetooth'un yalnızca test için olduğu not edildi
- [ ] Test 1: backend ptb, aygıt 48 kHz, flip sapması < 1 kare, TimeFailed 0
- [ ] Test 1: `expected_refresh_hz` kararı verildi (75'e çekildi ya da bu
      makinede uyuşmazlık bilinçli olarak bırakıldı)
- [ ] Test 2: sol/sağ kulak doğru, deneme 3 ile 4 duyulabilir biçimde farklı,
      V-only sessiz, düşen kare 0
- [ ] Test 2: gerçekleşen SOA nominalden bir kareden az sapıyor
- [ ] Test 3: kulaklık yönü doğrulandı
- [ ] Test 4: ESC video ortasında çalışıyor, ses anında susuyor
- [ ] Test 5: kademe 3 yönergesi okunabiliyor
- [ ] Kademe 2: donanım geldiğinde yapılacak (şimdi değil)
