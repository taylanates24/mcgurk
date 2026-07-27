# Adım 6 Manuel Test — Modül 3: TBW (zamansal bağlama penceresi)

Bu dosyada **yalnızca benim koşamadığım testler** var: gözle ve kulakla
yargılanması gereken şeyler ve gerçek klavyeyle yanıt verme. Tasarım üretimi,
yargı eşlemesi, psikometrik uydurma, bootstrap güven aralıkları, hata yolları,
veritabanı kısıtı ve blok döngüsü otomatik testlerle kapsandı (**599 test
yeşil**: 542'si donanımsız, 57'si gerçek pencere ve ses aygıtında; 15 test
ffmpeg gerektirdiği için atlandı) ve tam
uzunlukta bir dayanıklılık koşusu simüle yanıtlarla ayrıca yapıldı — özeti
aşağıda.

**Tek bir test var ve ~4 dakika sürüyor.** Geri kalan her şey otomatik.

## Otomatik koşulanlar (bilgi için, sizin yapmanıza gerek yok)

| Ne | Sonuç |
|---|---|
| Tam uzunlukta koşu (130 deneme, tam ekran, 74.8 Hz, simüle yanıt) | 130/130, 11.13 dk (5.14 s/deneme), bloklar 60/60/10 hepsi `completed` |
| Düşen kare / ses zamanlaması bozulması | 1 deneme (en uzun kare 20.23 ms, sınır 20.1 ms) / **0** |
| `actual_soa_ms` − `nominal_soa_ms` | ort **+0.389 ms**, SD 0.732, aralık [−1.24, +2.39] |
| Bilinen gözlemciden geri kestirim (gerçek PSS +40 ms, sigma 90 ms) | PSS **+44.8** ms (GA [28.0, 62.8]), sigma **96.8** ms (GA [83.3, 109.9]) — ikisi de gerçek değeri kapsıyor |
| Negatif ve pozitif SOA gerçek donanımda sunuldu | `tests/test_modules_block_tbw.py` (3 test) |

Yani "ses gerçekten videodan önce/sonra başlıyor mu" sorusu **yazılım
zaman damgalarıyla** zaten doğrulandı. Aşağıdaki test aynı şeyi **kulakla**
doğruluyor — çünkü zaman damgası, sesin hoparlörden ne zaman çıktığını değil,
ne zaman çıkması istendiğini söyler.

## Ön koşullar

- [ ] Conda ortamı etkin: `C:\Users\tayla\miniconda3\envs\mcgurk`
- [ ] **Kulaklık takılı** ve `audio.device` onu gösteriyor. Aygıtları
      listelemek için:

```bash
python tools/timing_selftest.py --devices
```

Config'teki aygıt bağlı değilse tek koşuluk ezin: aşağıdaki komuta
`--device "<aygıt adı>"` ekleyin.

### Bluetooth kulaklıkla koşuyorsanız

Beş kontrol maddesinin dördü Bluetooth'la geçerli. **Madde 3 (SOA 0'da
eşzamanlılık) kablolu kulaklık ister**: WH-1000XM4 100–300 ms *değişken*
gecikme ekliyor, yani SOA 0 denemesi bile "ses sonra geldi" diye duyulur ve bu
kodun değil kulaklığın davranışıdır. O maddeyi atlayın.

Madde 2 (±300 ms yönü) Bluetooth'la **yargılanabilir**: iki uç arasındaki fark
600 ms ve kulaklığın gecikmesi ikisine de aynı yönde eklenir.

`progress.md` aynı sınırı Adım 3'ten beri taşıyor (§F.3); kablolu kulaklık
geldiğinde `TEST_ADIM_3.md` Test 2 madde 7, `TEST_ADIM_5.md` Test 1 madde 3 ve
buradaki madde 3 birlikte kapatılacak.

---

## Test 1: SOA gerçekten duyuluyor mu (ekran + ses, ~4 dk)

**Komut:**

```bash
python tools/run_module.py --module tbw --limit 26 --seed 6
```

26 deneme = tam iki tur, yani **13 SOA'nın her biri tam iki kez** sunulur.
`--seed 6` ile sıra sabittir; deneme numaraları (1'den başlayarak):

| Deneme | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SOA (ms) | −50 | **−300** | +150 | −250 | −200 | +100 | +250 | **0** | +200 | **+300** | −150 | −100 | +50 |

| Deneme | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SOA (ms) | +150 | −200 | **−300** | **0** | **+300** | +250 | −50 | +200 | −100 | −250 | −150 | +100 | +50 |

Negatif SOA = **ses önce**, pozitif = **ses sonra**.

**Kontrol edilecek:**

1. **Yanıt ekranı okunabiliyor.** Soru: "Ses ve görüntü aynı anda mıydı?",
   altında iki seçenek: `1 / Aynı anda` ve `2 / Farklı zamanda`. İkisi
   üst üste binmiyor, ekrandan taşmıyor.
2. **Yön duyuluyor.** 2. ve 16. denemede (−300 ms) ses **dudaklar
   kıpırdamadan önce** geliyor; 10. ve 18. denemede (+300 ms) ses
   **dudaklar durduktan sonra** geliyor. İkisi birbirinden açıkça farklı.
3. **(Kablolu kulaklık gerekir)** 8. ve 17. denemede (SOA 0) ses ve dudak
   birlikte. Bluetooth'la bu madde atlanır.
4. **Tuş basımı onaylanıyor, doğruluk geri bildirimi yok.** Seçilen seçenek
   kısa süre sarıya dönüyor; hiçbir yerde "doğru/yanlış" yazmıyor.
5. **Zaman aşımı ve ESC.** Bir denemede (örneğin 20.) hiç tuşa basmayın:
   4 saniye sonra "Yanıt alınamadı" yazıp bir sonrakine geçmeli. Sonra
   herhangi bir denemenin **ortasında ESC**: koşu hemen durmalı, konsolda
   "Oturum ESC ile kesildi." yazmalı.

**Beklenen çıktı (koşu sonunda, ESC'ye basmadan tamamlarsanız):**

```
Koşu özeti
----------------------------------------
Blok sayısı            : 1
Sunulan / planlanan    : 26 / 26
Zaman aşımı            : 1
Kare düşen deneme      : 0
Ses zamanlaması bozulan: 0
Yanıtlar:
  SAME  ...
  DIFFERENT ...

Psikometrik fonksiyon:
   SOA (ms)    aynı   yanıt   p(aynı)  yanıtsız
       -300       ...
       ...
Uydurma yapılamadı: ...      <-- 26 denemede BEKLENEN
```

**"Uydurma yapılamadı" burada bir hata değildir:** SOA başına 2 yanıtla eğri
kestirilemez ve kod bunu sessizce uydurmak yerine söylüyor. Tam modülde
(130 deneme) uydurma çalışıyor — dayanıklılık koşusunda doğrulandı.

**Başarısızsa:**
- Ses hiç çıkmıyorsa: `python tools/timing_selftest.py --devices` ile aygıt
  adını kontrol edin, `--device "<ad>"` ile ezin.
- "Ses zamanlaması bozulan" 0'dan büyükse ve Bluetooth kullanıyorsanız: bu
  kulaklığın kendisidir, not düşün yeter. Kabloluda çıkarsa bildirin.
- Yön ters duyuluyorsa (negatif SOA'da ses sonra geliyorsa) **durun ve
  bildirin** — bu bir kod hatası olur.

---

## Test 2 (isteğe bağlı, donanımsız, ~10 sn): tasarım özeti

```bash
python tools/run_module.py --module tbw --dry-run
```

**Kontrol edilecek:** "SOA sunumu" başlığı altında 13 nokta, −300…+300 ms,
"En geniş negatif SOA : 320 ms pay gerektiriyor" ve pencere tanımı `fwhm`;
"Hücreler" tablosunda 13 satır, her birinde n = 10.

---

## Kabul kriterleri

- [ ] Yanıt ekranı okunabiliyor, iki seçenek de görünüyor
- [ ] −300 ms'te ses önce, +300 ms'te ses sonra duyuluyor
- [ ] (kablolu kulaklıkla) SOA 0'da ses ve dudak birlikte
- [ ] Zaman aşımı mesajı çıkıyor, ESC her aşamada çalışıyor
- [ ] Doğru/yanlış geri bildirimi hiçbir yerde yok
