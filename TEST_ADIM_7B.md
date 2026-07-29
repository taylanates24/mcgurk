# Adım 7b Manuel Test — Modül 5: Dikotik dinleme

Bu dosyada **benim koşamadığım iki test** var; ikisi de kulaklık gerektiriyor.
Geri kalan her şey otomatik koşuldu — tasarım üretimi, sıralamanın tohumdan
yeniden üretilebilirliği, yanıtın hangi kulağa atfedildiği, kulak avantajı
indeksi, config kapıları, veritabanı yazımı ve deneme döngüsünün gerçek pencere
+ ses aygıtındaki davranışı.

**Toplam süre ~5 dakika.**

## Otomatik koşulanlar (bilgi için, sizin yapmanıza gerek yok)

| Ne | Sonuç |
|---|---|
| Otomatik testler | **721 test yeşil** (CI'da koşan 655, gerçek pencere + ses aygıtında 66, ffmpeg gerektirdiği için atlanan 18); `ruff` + `mypy` temiz |
| Yeni testler | 48 yeni test: 43'ü CI'da (tasarım, atfetme, KAİ, config kapıları), 5'i gerçek donanımda |
| Deneme döngüsü gerçek donanımda | `tests/test_modules_block_dichotic.py`: yanıt doğru kulağa atfediliyor, `is_correct` NULL, iki RT referansı da doluyor, zaman aşımı satır üretmiyor, stereo dosya yönlendirilmeden aygıta gidiyor |
| Canlı duman testi (3 deneme, tam ekran, 75 Hz) | 3/3 sunuldu, **0 düşen kare**, **0 ses zamanlaması bozulması**, zaman aşımları doğru raporlandı |
| Uyaran ölçümü (aşağıdaki tablo) | 6 dosya, kanal içerikleri birebir tutarlı |

**Uyaran dosyalarını yeniden ölçtüm** (`stimuli/dichotic/speaker_1/`, 48 kHz
stereo, 123200 örnek):

- Aynı hece farklı dosyalarda **birebir aynı**: `Left-ba_Right-da` ile
  `Left-ba_Right-ga` dosyalarının sol kanalları örnek örnek özdeş (altı
  hece × kanal kombinasyonunun tamamında).
- Simetrik çiftler **tam kanal takası**: `Left-ba_Right-da`'nın sol kanalı,
  `Left-da_Right-ba`'nın sağ kanalıyla birebir aynı. Yani kulak avantajı ölçümü
  içerik farkından değil yalnızca taraftan geliyor.
- Kanallar arası korelasyon **|r| < 0.06** — iki kanal gerçekten farklı hece
  taşıyor.
- İki kulak arasındaki seviye farkı **≤ 0.2 dB**.

Bunların hiçbiri şunu söyleyemez: **dosyanın 0. kanalı gerçekten sol kulaktan mı
çıkıyor?** Onu ancak kulakla dinleyerek anlarız — Test 1 tam olarak bu.

## Ön koşullar

- [ ] Conda ortamı etkin: `C:\Users\tayla\miniconda3\envs\mcgurk`
- [ ] **Kulaklık takılı ve doğru yönde** (L işareti sol kulakta) ve
      `audio.device` onu gösteriyor:

```bash
python tools/timing_selftest.py --devices
```

Config'teki aygıt bağlı değilse tek koşuluk ezin: aşağıdaki komutlara
`--device "<aygıt adı>"` ekleyin.

Bluetooth kulaklık bu modül için **yeterli**: burada ölçülen şey sesin ekrana
göre ne zaman çıktığı değil, hangi tarafın bildirildiği. Kulaklığın sabit
gecikmesi iki kulağa eşit bindiği için kulak avantajını etkilemez.

---

## Test 1: Kanal yönü — sol kanal gerçekten sol kulakta mı? (~1 dk)

**Komut:**

```bash
python tools/run_module.py --module dichotic --limit 2 --seed 7
```

Bu tohumda ilk iki deneme **bilerek birbirinin aynası**:

| Deneme | Sol kulak | Sağ kulak |
|---|---|---|
| 1 | **ba** | da |
| 2 | **da** | ba |

**Ne yapacaksınız:** Bu tek testte kulaklığı normal takmayın —
**sağ kulaklığı kulağınızdan uzaklaştırın**, yalnızca sol kulaklığı dinleyin.
Her denemede duyduğunuz heceyi ekrandaki seçeneklerden seçin (1=BA, 2=DA,
3=GA, 4=DIGER).

**Beklenen:** 1. denemede **BA**, 2. denemede **DA** duymalısınız.

**Kontrol edilecek:**

1. **Duyduğunuz sıra BA → DA.** Eğer DA → BA duyduysanız kanallar ters
   bağlanmış demektir — **durun ve bildirin**, bu bulgu tüm lateralizasyon
   verisini etkiler.
2. **Sağ kulaklıktan gelen ses net biçimde ayrı bir hece.** Sağ kulaklığı
   kulağınıza geri koyduğunuzda iki farklı hece aynı anda duyuluyor, tek bir
   hece değil.
3. Koşu sonundaki raporda "Sol kulak bildirimi: %100.0 (2)" yazmalı — yani
   yazılım da sizin sol kulağı bildirdiğinizi görmüş olmalı.

**Başarısızsa:** Hiç ses yoksa `--device "<ad>"` ile aygıtı ezin. Sıra ters
geliyorsa bildirin.

---

## Test 2: Tam koşu (30 deneme, ~3 dk)

**Komut:**

```bash
python tools/run_module.py --module dichotic --seed 7
```

**Ne yapacaksınız:** Kulaklığı normal takın. Her denemede **duyduğunuz heceyi**
seçin. Bilerek bir tarafa odaklanmayın — hangisi öne çıkıyorsa onu bildirin;
ölçülen şey tam olarak bu.

Koşu sırasında **bilerek iki şey** yapın:

- bir denemede **hiç yanıt vermeyin** (zaman aşımına bırakın),
- bir denemede **4 (DIGER)** seçip açılan alana bir şey yazıp Enter'a basın.

**Kontrol edilecek:**

1. **Ekranda görsel uyaran yok.** Uyaran sırasında yalnızca sabitleme haçı var;
   hiçbir yerde konuşan yüz görünmüyor.
2. **Soru "Hangi heceyi duydunuz?"** — tekil. İki hece sunulduğu hiçbir yerde
   söylenmiyor, "hangi kulağa odaklanın" denmiyor.
3. **Hiçbir geri bildirim yok.** Doğru/yanlış hiçbir yerde yazmıyor.
4. **DİĞER seçilince metin alanı açılıyor**, yazdığınız kayda giriyor.
5. **Yanıt vermediğiniz denemede** "Yanıt alınamadı" görünüyor ve koşu devam
   ediyor.
6. **ESC her aşamada çalışıyor** (sabitleme, uyaran ve yanıt ekranında).

**Beklenen çıktı (koşu sonunda):**

```
Koşu özeti
----------------------------------------
Blok sayısı            : 1
Sunulan / planlanan    : 30 / 30
Zaman aşımı            : 1
Kare düşen deneme      : 0
Ses zamanlaması bozulan: 0
Yanıtlar:
  RIGHT           ...
  LEFT            ...
  OTHER           ...
  NONE              1

Deneme                 : 30 (29 yanıtlanan, 1 yanıtsız)
Sol kulak bildirimi    : %xx.x (nn)
Sağ kulak bildirimi    : %xx.x (nn)
Karışım yanıtı         : %x.x (n)
Kulak avantajı (KAİ)   : +xx.x  [(Sağ-Sol)/(Sağ+Sol)]x100
Ortalama RT            : xxx ms (patlamadan), xxx ms (yanıt ekranından)
Çift bazında (sol / sağ / karışım / yanıtsız):
  Left-ba/Right-da       ...
  ...
```

Sayılar sizin algınıza göre değişir. Önemli olan:

- **Sunulan / planlanan = 30 / 30**, tek blok (30 < 60, mola sınırı).
- **Zaman aşımı = 1** — bilerek boş bıraktığınız deneme. Bu deneme sol/sağ
  oranlarına **girmiyor**, yalnızca "yanıtsız" olarak sayılıyor.
- **Sol + Sağ + Karışım = 29** (yanıtlanan deneme sayısı).
- **KAİ işareti**: normal işiten birinde sözel uyaranlarda **pozitif** (sağ
  kulak üstünlüğü) beklenir, ama tek kişide ve 30 denemede bu bir beklenti,
  garanti değil. Negatif çıkması bir hata göstergesi **değildir**.
- **Kare düşen deneme = 0** ve **Ses zamanlaması bozulan = 0**.
- **Ortalama RT**: patlamadan ölçülen RT, yanıt ekranından ölçülenden büyük
  olmalı (patlama önce oluyor).

**Başarısızsa:**

- "Ses zamanlaması bozulan" 0'dan büyükse hangi sayıyı gördüğünüzü bildirin.
- Karışım yanıtı oranı çok yüksekse (%50'den fazla), yani sürekli sunulmayan
  bir hece duyuyorsanız, bildirin — uyaran seviyesi veya kulaklık yerleşimiyle
  ilgili olabilir.

---

## Test 3 (isteğe bağlı, donanımsız, ~10 sn): tasarım özeti

```bash
python tools/run_module.py --module dichotic --dry-run
```

**Kontrol edilecek:** "Hücreler" tablosunda **6 satır, her biri n=5**; toplam
30 ve "Config'in beklentisi" ile aynı. "Dikotik sunum" başlığı altında görsel
uyaran yok, kulak "her denemede ikisi de", gürültü koşulu yok, doğru cevap yok.
"Dosya kontrolü" 6 ayrı dosyanın yerinde olduğunu söylüyor.

---

## Kabul kriterleri

- [ ] Sol kanal sol kulaktan çıkıyor (Test 1: BA → DA sırası)
- [ ] İki kulakta aynı anda iki farklı hece duyuluyor
- [ ] Uyaran sırasında ekranda görsel uyaran yok, yalnızca sabitleme haçı
- [ ] Soru tekil ("Hangi heceyi duydunuz?"), iki hece sunulduğu söylenmiyor
- [ ] Hiçbir doğru/yanlış geri bildirimi yok
- [ ] DİĞER serbest metin alanını açıyor
- [ ] 30/30 deneme sunuluyor, 0 düşen kare, 0 ses zamanlaması bozulması
- [ ] Zaman aşımına bırakılan deneme oranlara girmiyor, "yanıtsız" olarak
      görünüyor
- [ ] Rapor: sol + sağ + karışım = yanıtlanan deneme sayısı
- [ ] ESC her aşamada koşuyu kesiyor
