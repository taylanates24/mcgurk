# Adım 7 Manuel Test — Modül 4: Oddball (işitsel dikkat kontrolü)

Bu dosyada **yalnızca benim koşamadığım tek bir test** var: tonları kulakla
duymak ve gerçek klavyeyle yanıt vermek. Geri kalan her şey otomatik koşuldu —
tasarım üretimi, hedef yerleşimi, tuş atfetme, d′ ve kriter hesabı, ton
üretimi ve rampası, config kapıları, veritabanı yazımı ve akış koşucusunun
gerçek donanımdaki davranışı.

**Test ~2 dakika sürüyor.**

## Otomatik koşulanlar (bilgi için, sizin yapmanıza gerek yok)

| Ne | Sonuç |
|---|---|
| Uyaran seti yeniden üretildi ve denetlendi | 123 dosya, `verify_stimuli.py` tamamı YEŞİL — "2 oddball tonu: frekans, süre, seviye ve rampa beklendiği gibi" |
| Otomatik testler | **688 test yeşil** (CI'da koşan 610, gerçek pencere + ses aygıtında 61, ffmpeg gerektirdiği için atlanan 17); `ruff` + `mypy` temiz |
| Akış gerçek donanımda | `tests/test_modules_stream.py` (4 test): tonlar tasarlanan aralıklarla geliyor, tuş basımı doğru tona düşüyor, bloğu kapanmış bir tona gelen geç basım bile kaydediliyor, pencere dışı basım kaydediliyor ama puanlanmıyor |
| Tam uzunlukta dayanıklılık koşusu (300 ton, tam ekran, 75.0 Hz, simüle gözlemci) | 300/300 sunuldu, **5.06 dk**, 5 blok, **0 düşen kare**, **0 ses zamanlaması bozulması** |
| Bilinen gözlemciden geri kestirim (gerçek isabet %90, yanlış alarm %2) | isabet %92.6, yanlış alarm %2.4, **d′ 3.33**, kriter +0.27, isabet RT 344 ms (SD 71) |

Bir noktayı olduğu gibi söylemek gerekiyor: `trials.audio_onset_s` **planlanan**
onset'i taşır, ölçüleni değil (Adım 3 kararı — PTB bu makinede kendisine
söylenen zamanı aynen geri bildiriyor, bu bir ölçüm değildir). Yani "aralıklar
tam tutuyor" cümlesi aritmetiğin doğru olduğunu söyler, sesin kartın çıkışından
o anda çıktığını değil. Bunu söyleyen şey **`TimeFailed`/`XRuns` = 0**: 300
tonun hiçbirinde PsychPortAudio istenen zamanı kaçırmadı.

Aşağıdaki test iki şeyi ekliyor: tonların **kulağa** nasıl geldiği (klik var mı,
iki frekans ayırt edilebiliyor mu) ve **gerçek bir parmağın** verdiği yanıtın
raporda doğru görünmesi.

## Ön koşullar

- [ ] Conda ortamı etkin: `C:\Users\tayla\miniconda3\envs\mcgurk`
- [ ] **Kulaklık takılı** ve `audio.device` onu gösteriyor:

```bash
python tools/timing_selftest.py --devices
```

Config'teki aygıt bağlı değilse tek koşuluk ezin: aşağıdaki komuta
`--device "<aygıt adı>"` ekleyin.

Bluetooth kulaklık bu modül için **yeterli**: ölçülen şey tonun ekrana göre ne
zaman çıktığı değil, katılımcının ne zaman tepki verdiği. Kulaklığın sabit
gecikmesi RT'lere sabit bir sayı ekler ve gruplar arası karşılaştırmayı
etkilemez.

---

## Test 1: Akış ve yanıt (ses + klavye, ~2 dk)

**Komut:**

```bash
python tools/run_module.py --module oddball --limit 60 --seed 7
```

60 ton = yaklaşık **1 dakikalık** akış. Bu tohumda ilk 60 tonun **13'ü hedef**.

Ekranda yalnızca sabitleme haçı olacak — yanıt ekranı yok, bu modülde
katılımcı bir seçenek seçmiyor, sadece tepki veriyor.

**Ne yapacaksınız:** **tiz (1500 Hz) tonu** duyduğunuzda **boşluk tuşuna**
basın. Pes (1000 Hz) tonlarda hiçbir şey yapmayın.

Ayrıca akış sırasında **bilerek iki şey** yapın:

- bir kez, hiçbir ton yokken (iki ton arasında) boşluğa basın,
- **en sonda ESC**'ye basıp koşuyu kesin (60 ton bittiyse gerek yok).

**Kontrol edilecek:**

1. **İki ton açıkça farklı.** Tiz ton pes tondan ayırt edilebiliyor; ikisini
   karıştırmak için dikkat gerekmiyor.
2. **Tıklama yok.** Tonlar "tık" diye başlamıyor/bitmiyor; yumuşak giriyor ve
   çıkıyorlar. (Bir tık duyarsanız **bildirin** — rampa uygulanmamış demektir
   ve o durumda hedefi frekanstan değil tıktan ayırt etmek mümkün olur.)
3. **Ritim yok.** Tonlar arası aralık sabit değil, hafifçe değişiyor.
4. **Hiçbir geri bildirim yok.** Doğru/yanlış hiçbir yerde yazmıyor, ekranda
   basımınıza dair bir işaret çıkmıyor.
5. **ESC her an çalışıyor.** Basar basmaz akış duruyor, konsolda "Oturum ESC
   ile kesildi." yazıyor.

**Beklenen çıktı (koşu sonunda):**

```
Koşu özeti
----------------------------------------
Blok sayısı            : 1
Sunulan / planlanan    : 60 / 60
Zaman aşımı            : 0
Kare düşen deneme      : 0
Ses zamanlaması bozulan: 0
Yanıtlar:
  HIT              ...
  OUTSIDE_WINDOW   ...

Sinyal tespiti:
  Isabet                 12 / 13
  Kaçırma                 1
  Yanlış alarm            0 / 47
  Doğru ret              47
  Pencere dışı basım      1
Isabet oranı           : %92.3
Yanlış alarm oranı     : %0.0
d'                     : 3.xx
Kriter (c)             : +0.xx
  (d' ve c log-lineer düzeltmeli: paylara +0.5, toplamlara +1)
Isabet RT (ort)        : 4xx ms (SD xx), n=12
```

Sayılar sizin performansınıza göre değişir. Önemli olan:

- **Isabet + Kaçırma = 13** (hedef sayısı), **Yanlış alarm + Doğru ret = 47**.
- **Pencere dışı basım ≥ 1** — ton yokken bastığınız o basım. Kaydedildi ama
  hiçbir orana girmedi: isabet oranı ve yanlış alarm oranı ondan etkilenmedi.
- **d′ 2'nin üstünde** olmalı (görev kolay). 1'in altındaysa ya tonları
  ayırt edemediniz ya da bir sorun var — bildirin.
- **Zaman aşımı 0**: bu modülde zaman aşımı diye bir şey yok, satır her zaman
  0 yazar.

**Başarısızsa:**

- Ses hiç çıkmıyorsa: `python tools/timing_selftest.py --devices` ile aygıt
  adını kontrol edin, `--device "<ad>"` ile ezin.
- "Ses zamanlaması bozulan" 0'dan büyükse: hangi sayıyı gördüğünüzü bildirin.
  Bluetooth'ta tek tük görülebilir; kabloluda görülüyorsa sorun vardır.
- Bastığınız hâlde "Isabet" 0 çıkıyorsa **durun ve bildirin** — tuş yakalama
  ya da atfetme hatası olur.

---

## Test 2 (isteğe bağlı, donanımsız, ~10 sn): tasarım özeti

```bash
python tools/run_module.py --module oddball --dry-run
```

**Kontrol edilecek:** "Akış" başlığı altında hedef sayısı 54 (%18.0), config'in
beklentisiyle aynı; "Hedefler arası standart: en az 2" (kısıt sağlanıyor); ISI
900–1100 ms aralığında; akış süresi ~5.0 dk; yanıt penceresi 100–800 ms.
"Hücreler" tablosunda iki satır: 246 standart (1000 Hz), 54 hedef (1500 Hz).

---

## Kabul kriterleri

- [ ] İki ton kulakla açıkça ayırt ediliyor
- [ ] Tonlarda tıklama yok
- [ ] Tonlar arası aralık değişken (ritim yok)
- [ ] Hiçbir doğru/yanlış geri bildirimi yok
- [ ] Rapor: isabet + kaçırma = hedef sayısı, yanlış alarm + doğru ret =
      standart sayısı
- [ ] Ton yokken yapılan basım "Pencere dışı basım" olarak görünüyor ve
      oranlara girmiyor
- [ ] ESC akışı her an kesiyor
