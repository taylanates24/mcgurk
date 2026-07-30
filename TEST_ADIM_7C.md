# Adım 7c Manuel Test — Modül 6: GIN (Gaps-In-Noise)

Bu dosyada **benim koşamadığım iki test** var; ikisi de kulaklık gerektiriyor.
Geri kalan her şey otomatik koşuldu — tasarım üretimi, segment sırasının
tohumdan yeniden üretilebilirliği, tuş basımının hangi boşluğa atfedildiği,
eşik hesabı, config kapıları, veritabanı yazımı ve akış koşucusunun gerçek
pencere + ses aygıtındaki davranışı.

**Toplam süre ~6 dakika.**

## Otomatik koşulanlar (bilgi için, sizin yapmanıza gerek yok)

| Ne | Sonuç |
|---|---|
| Otomatik testler | **787 test yeşil** (CI'da koşan 716, gerçek pencere + ses aygıtında 71, ffmpeg gerektirdiği için atlanan 19); `ruff` + `mypy` temiz |
| Yeni testler | 68 yeni test: 49'u CI'da tasarım/atfetme/eşik, 7'si veritabanına yazımı (donanımsız), 5'i gerçek donanımda, 7'si `event_index` şeması |
| Akış koşucusu gerçek donanımda | `tests/test_modules_stream_gin.py`: tuş doğru boşluğa düşüyor, cevaplanmayan boşluk satır bırakmıyor, yakalama segmentindeki basım yanlış alarm yazılıyor, pencere dışı basım yanlış alarm, iki segment tek başlangıçtan ardışık akıyor |
| Canlı duman testi (3 segment, tam ekran, 75 Hz) | 3/3 sunuldu, **0 düşen kare**, **0 ses zamanlaması bozulması**, eşik raporu doğru bastı |
| Uyaran ölçümü (aşağıda) | boşluklar gerçek seviye düşüşü, segment seviyesi hedefte |

**Bir gerçek hata bu adımda yakalandı ve düzeltildi.** İlk segment saat
başlatıldıktan *sonra* diskten okunuyordu; altı saniyelik dosyanın okunması
giriş süresini yiyor ve akış zaten geçmiş bir başlangıç anı istiyordu
(`StreamError`). İlk segment artık saat başlamadan önce yükleniyor (oddball'ın
tüm setini önden yüklemesi gibi). İkinci bir hata: bir segmentin kuyruk
bekleyişi bir sonraki segmentin planlama payını yiyordu; bekleyiş artık bir
sonraki segmentten çeyrek saniye önce kesiliyor.

**Uyaran ölçümü** (`stimuli/gin/`, 48 kHz, 6 s segmentler, 30 segment / 60
boşluk):

- Her boşluk **gerçek bir seviye düşüşü**: 12 ms boşlukta −22.9 dB, 4 ms'te
  −21.6 dB, 3 ms'te −15.8 dB. Kısa boşlukta düşüş daha az çünkü boşluğun
  kenar rampaları boşluğun içine giriyor — bu beklenen ve görevin özü: kısa
  boşluk zordur.
- Segment seviyesi −23.2 dBFS (config'in `tones.level_dbfs` hedefiyle uyumlu,
  aynı seviye ailesinden).
- Segment başında yumuşak rampa var (ilk 250 ms tepe orta bölümden ~1 dB
  düşük), Adım 2'de 200 ms'e çıkarılmıştı.

## Ön koşullar

- [ ] Conda ortamı etkin: `C:\Users\tayla\miniconda3\envs\mcgurk`
- [ ] **Kulaklık takılı** ve `audio.device` onu gösteriyor:

```bash
python tools/timing_selftest.py --devices
```

Config'teki aygıt bağlı değilse tek koşuluk ezin: aşağıdaki komutlara
`--device "<aygıt adı>"` ekleyin.

Bluetooth kulaklık bu modül için **yeterli**: ölçülen şey boşluğun ekrana göre
ne zaman geldiği değil, katılımcının onu duyup duymadığı. Kulaklığın sabit
gecikmesi RT'lere sabit bir sayı ekler ve eşik ölçütünü etkilemez.

**GIN tek kulaklıdır.** Hangi kulağa sunulacağı katılımcının iyi kulağına
bağlıdır (SSD'de sağır kulağa sunmak hiçbir şey ölçmez), bu yüzden koşu
komutuna `--ear right` veya `--ear left` **eklenmesi zorunludur**. Kulak
verilmezse araç açık hata verir.

---

## Test 1: Boşluklar duyuluyor mu, kısa/uzun farkı var mı? (~1 dk)

**Komut:**

```bash
python tools/run_module.py --module gin --limit 6 --ear right --seed 11
```

Bu tohumda ilk 6 segmentte farklı sürelerde boşluklar var (3 boşluklu, 1
boşluklu, 2 boşluklu segmentler karışık). Her segment 6 saniye geniş bantlı
gürültüdür; içinde kısa sessizlikler (boşluklar) var.

Ekranda yalnızca sabitleme haçı olacak — yanıt ekranı yok.

**Ne yapacaksınız:** Gürültü akarken **kısa bir kesinti (sessizlik)**
duyduğunuz her an **boşluk tuşuna** basın.

**Kontrol edilecek:**

1. **Ses yalnızca tek kulaktan geliyor** (`--ear right` ise sağdan). Diğer
   kulak sessiz. Ters kulaktan geliyorsa **bildirin**.
2. **Uzun boşluklar (10–20 ms) kolayca duyuluyor** — net bir "kesinti" gibi.
3. **Kısa boşluklar (2–3 ms) zor veya imkânsız.** Hepsini yakalayamamanız
   normal; görevin ölçtüğü şey tam olarak bu eşiktir.
4. **Gürültü sert başlamıyor.** Segment yumuşak giriyor, "pat" diye değil.
5. **Hiçbir görsel ipucu yok.** Ekranda boşluğun ne zaman geldiğine dair bir
   işaret çıkmıyor.
6. **Hiçbir geri bildirim yok.** Doğru/yanlış hiçbir yerde yazmıyor.

**Başarısızsa:** Ses hiç çıkmıyorsa `--device "<ad>"` ile aygıtı ezin. Boşluk
hiç duyulmuyorsa (uzun olanlar bile) seviye ya da kulaklıkla ilgili olabilir,
bildirin.

---

## Test 2: Tam koşu ve eşik (30 segment, ~4 dk)

**Komut:**

```bash
python tools/run_module.py --module gin --ear right --seed 11
```

**Ne yapacaksınız:** Boşluk duyduğunuz her an boşluk tuşuna basın. Emin
olmadığınız kısa boşluklarda da deneyin — ama gürültü sürerken gereksiz yere
basmayın (o basımlar **yanlış alarm** olarak sayılır).

Koşu içinde bilerek:

- **bir segmentte, hiç boşluk yokken bir kez basın** (yanlış alarm üretmek
  için — tohumda bir yakalama segmenti var, orada hiç boşluk yok),
- **en sonda ESC**'ye basıp koşuyu kesin (30 segment bittiyse gerek yok).

**Kontrol edilecek:**

1. **Segmentler ardışık akıyor**, aralarında ~2 sn boşluk (segmentler arası
   ara) var.
2. **ESC her an çalışıyor** — basar basmaz akış duruyor, konsolda "Oturum ESC
   ile kesildi." yazıyor.

**Beklenen çıktı (koşu sonunda):**

```
Koşu özeti
----------------------------------------
Blok sayısı            : 1
Sunulan / planlanan    : 30 / 30
Zaman aşımı            : 0
Kare düşen deneme      : 0
Ses zamanlaması bozulan: 0
Yanıtlar:
  HIT              ...
  FALSE_ALARM      ...

Boşluk saptama (süre başına):
   süre (ms)  saptanan  sunulan    oran
           2         .        6      %..
           3         .        6      %..
           ...
          20         6        6     %100  <-- eşik (örnek)
Eşik                   : X ms  (6 sunumun en az 4'inde saptanan en kısa süre)
Toplam saptama         : %.. (../60)
Yanlış alarm           : ..
Saptama RT             : ... ms (SD ..), n=..
Test edilen kulak      : right
```

Sayılar sizin performansınıza göre değişir. Önemli olan:

- **Sunulan / planlanan = 30 / 30**, tek blok (30 < 60, mola sınırı).
- **Süre başına sunulan hep 6** (her boşluk süresi 6 kez sunulur, toplam 60).
- **Eşik**, 4/6 ölçütünü sağlayan **en kısa** süre. Normal işiten birinde
  tipik olarak 4–8 ms mertebesinde. Eşik satırının yanında **"<-- eşik"**
  işareti o süreyi gösterir.
- **Eşik her zaman yanlış alarm sayısıyla birlikte** basılıyor — çok basan
  biri kısa boşlukları şansla yakalayıp düşük (iyi) bir eşik alır, o yüzden
  ikisi birlikte okunur.
- Hiçbir süre 4/6'yı sağlamazsa eşik **"ulaşılamadı"** yazar (en uzun süreyi
  eşik diye uydurmaz).
- **Kare düşen deneme = 0** ve **Ses zamanlaması bozulan = 0**.
- **Zaman aşımı 0**: bu modülde zaman aşımı diye bir şey yok, satır her zaman
  0 yazar.

**Başarısızsa:**

- "Ses zamanlaması bozulan" 0'dan büyükse hangi sayıyı gördüğünüzü bildirin.
- Yanlış alarm sayısı çok yüksekse (ör. 20+) ya çok basmışsınızdır ya da
  gürültünün kendi dalgalanmalarını boşluk sanıyorsunuzdur — bildirin.
- Eşik "ulaşılamadı" çıkarsa ve uzun boşlukları duyduğunuzu düşünüyorsanız
  bir sorun var demektir, bildirin.

---

## Test 3 (isteğe bağlı, donanımsız, ~10 sn): tasarım özeti

```bash
python tools/run_module.py --module gin --dry-run --ear right
```

**Kontrol edilecek:** "Hücreler" tablosunda boşluk sayısına göre gruplama
(0/1/2/3 boşluklu segmentler); **1 yakalama segmenti** (0 boşluk). "GIN akışı"
başlığı altında 30 segment × 6 s, toplam 60 boşluk (config 60), her süre 6 kez,
akış süresi ~4 dk, yanıt penceresi 100–900 ms, eşik ölçütü 4_of_6. "Dosya
kontrolü" 30 ayrı dosyanın yerinde olduğunu söylüyor.

---

## Kabul kriterleri

- [ ] Ses tek kulaktan geliyor (`--ear` ile seçilen)
- [ ] Uzun boşluklar (10–20 ms) net duyuluyor
- [ ] Kısa boşluklar (2–3 ms) zor — hepsini yakalamak gerekmiyor
- [ ] Gürültü sert başlamıyor (yumuşak rampa)
- [ ] Uyaran sırasında görsel ipucu yok, yalnızca sabitleme haçı
- [ ] Hiçbir doğru/yanlış geri bildirimi yok
- [ ] 30/30 segment sunuluyor, 0 düşen kare, 0 ses zamanlaması bozulması
- [ ] Eşik raporu: en kısa 4/6 süresi, yanlış alarm sayısıyla birlikte
- [ ] Yakalama segmentinde yapılan basım yanlış alarm olarak sayılıyor
- [ ] ESC akışı her an kesiyor
