# Adım 5 Manuel Test — Modül 2: AVSR

Bu dosyada **yalnızca benim koşamadığım testler** var: gözle ve kulakla
yargılanması gereken şeyler ve gerçek klavyeyle yanıt verme. Tasarım üretimi,
skorlama, ölçüt hesapları, kelime listesi hata yolları ve blok döngüsü otomatik
testlerle kapsandı (556 test yeşil) ve tam uzunlukta bir dayanıklılık koşusu
simüle yanıtlarla ayrıca yapıldı — özet aşağıda.

## Ön koşullar

- [ ] Conda ortamı etkin: `C:\Users\tayla\miniconda3\envs\mcgurk`
- [ ] **Kulaklık takılı** ve `audio.device` onu gösteriyor. Kulak
      lateralizasyonu bu testin yarısı; monitör hoparlöründen yargılanamaz.
      Aygıtları listelemek için:

```bash
python tools/timing_selftest.py --devices
```

Config'teki aygıt bağlı değilse tek koşuluk ezin: aşağıdaki komuta
`--device "<aygıt adı>"` ekleyin.

### Bluetooth kulaklıkla koşuyorsanız

Yedi kontrol maddesinin **altısı** Bluetooth'la geçerli. Yalnızca **madde 3
(AV'de dudak–ses eşzamanlılığı) kablolu kulaklık gerektirir**: WH-1000XM4
100–300 ms **değişken** gecikme ekliyor, yani ses dudaktan sonra gelir ve bu
kodun değil kulaklığın davranışıdır. O maddeyi atlayın; `progress.md` aynı
maddeyi Adım 3'ten beri zaten "kablolu ile tekrar bakılmalı" diye taşıyor
(§F.3) ve ikisi birlikte kapatılacak.

Adım 5'i bloklamaz: A/V senkronu yazılım tarafında **ölçüldü**
(`actual_soa_ms` ort +0.028 ms, SD 0.118 ms, 60 AV denemesi) ve mutlak
gecikme yalnızca fotodiyot ölçümüyle doğrulanabilir — o da tasarım gereği
tüm kod bittikten sonra (`docs/01_av_gecikme_olcumu.md`).

Bluetooth'ta "Ses zamanlaması bozulan" satırı 0'dan büyük çıkabilir; bu
kulaklığın kendisidir, not düşün yeter.

---

## Test 1: Üç sunum modunun canlı kontrolü (ekran + ses gerektirir)

**Komut:**

```bash
python tools/run_module.py --module avsr --limit 12 --seed 3
```

Bu tohumla ilk 12 denemede üç mod da, iki kulak da, sessiz ve gürültülü koşul
da geçiyor. Deneme sırası: `A V V AV V AV A A AV AV A A`.

**Yanıt verme:** her denemede ekranda üç seçenek görürsünüz — `[1] BA`,
`[2] DA`, `[3] GA`. Ne duyduğunuzu (V-only'de: ne söylediğini gördüğünüzü)
tuşlayın. **Bir denemede kasten hiç tuşa basmayın** (zaman aşımını görmek için).
ESC her aşamada oturumu keser.

**Kontrol edilecek:**

1. **A-only denemesi (1., 7., 8., 11., 12.):** ekranda yalnızca sabitleme haçı
   var, video **yok**; ses geliyor.
2. **V-only denemesi (2., 3., 5.):** video oynuyor, **hiç ses yok**; soru
   metni **"Ne söyledi?"** — "Ne duydunuz?" değil.
3. **AV denemesi (4., 6., 9., 10.):** video ve ses birlikte, dudak ile ses
   eşzamanlı. *(**Kablolu kulaklık gerektirir** — Bluetooth'la koşuyorsanız bu
   maddeyi atlayın, yukarıdaki nota bakın.)*
4. **Kulak:** A ve AV denemelerinde ses **yalnızca tek kulaktan** geliyor,
   denemeden denemeye taraf değişiyor. Diğer kulakta hiçbir şey duyulmuyor.
5. **Gürültü:** bazı A/AV denemelerinde konuşmanın üstünde gürültü var,
   bazılarında yok. Gürültü konuşma başlamadan önce başlıyor (ani girmiyor).
6. **Zaman aşımı:** yanıt vermediğiniz denemede ekranda "Yanıt alınamadı"
   yazısı beliriyor ve deneme atlanıyor.
7. Video yanıt ekranına taşmıyor; yanıt verince kısa bir sarı onay yanıp
   sönüyor ve **doğru/yanlış geri bildirimi verilmiyor**.

**Beklenen çıktı (koşu sonunda):**

```
Koşu özeti
----------------------------------------
Blok sayısı            : 1
Sunulan / planlanan    : 12 / 12
Zaman aşımı            : 1
Kare düşen deneme      : 0
Ses zamanlaması bozulan: 0
Doğruluk (yanıtlanan)  : 10 / 11 (%90.9)
Yanıtlar:
  DOĞRU          10  (%83.3)
  YANLIŞ          1  (%8.3)
  NONE            1  (%8.3)

Doğruluk (mod):
  A   %... (n/n)
  V   %... (n/n), 1 yanıtsız
  AV  %... (n/n)
Görsel fayda (AV - A)  : %+...
Lipreading (V)         : %...
Görsel fayda (gürültü × kulak):
  5 dB      left    %+...
  sessiz    right   %+...
```

Sayılar sizin yanıtlarınıza göre değişir; **kontrol edilecek olan yapı**:
"Kare düşen deneme" ve "Ses zamanlaması bozulan" satırları **0**, üç mod da
tabloda görünüyor, "Görsel fayda" ve "Lipreading" satırları basılıyor.

**Başarısızsa:**
- V-only'de ses duyuyorsanız → durun, bildirin (§A.1 ihlali olurdu).
- Ses iki kulaktan geliyorsa → kulaklık gerçekten stereo mu, `--device` doğru
  aygıtı mı gösteriyor kontrol edin.
- "Kare düşen deneme" 0'dan büyükse → başka bir program ekranı paylaşıyor
  olabilir; kapatıp tekrar koşun, sürerse bildirin.

---

## Kabul kriterleri

- [ ] A-only'de video yok, V-only'de ses yok, AV'de ikisi de var (madde 1–3)
- [ ] Kulak lateralizasyonu çalışıyor (madde 4)
- [ ] V-only'de soru metni "Ne söyledi?" (madde 2)
- [ ] Zaman aşımı mesajı görünüyor ve deneme kayboluyor değil, yanıtsız
      kaydediliyor (madde 6)
- [ ] Özet çıktısında doğruluk, görsel fayda ve lipreading satırları var
- [ ] *(kablolu kulaklık geldiğinde)* AV'de dudak ile ses eşzamanlı — Adım 3'ün
      `TEST_ADIM_3.md` Test 2 madde 7'siyle birlikte

---

## Bilgi: benim koştuğum ölçümler (tekrarlamanıza gerek yok)

**Tam uzunlukta koşu, 135 deneme, tam ekran, 75 Hz, simüle yanıtlarla**
(scratchpad'de; `data/mcgurk.sqlite`'a hiçbir şey yazılmadı):

| Ölçüm | Sonuç |
|---|---|
| Süre | **11.18 dk** (4.97 s/deneme) — config'in tahmini 15.8 dk |
| Bloklar | 60 / 60 / 15, üçü de `completed`, her biri ayrı commit |
| Düşen kare | **0** (en kötü kare aralığı 17.85 ms; kare 13.33 ms, sınır 20.00 ms) |
| `TimeFailed` / `XRuns` | **0** |
| `actual_soa_ms` | yalnızca 60 AV denemesinde; ort **+0.028 ms**, SD 0.118 |
| A-only | 60/60 `video_onset` **boş**, `audio_onset` dolu |
| V-only | 15/15 `audio_onset` **boş**, `video_onset` dolu, `rt_from_burst` **dolu** |
| Gürültü varyantı | 60 gürültülü denemede 23/19/18 — hücre içinde dengeli |

Süre tahmini gerçekçi: 700 ms'lik bir yanıtla deneme 4.97 s sürüyor; gerçek RT
1–1.5 s olacağı için 5.3–5.8 s, yani config'in 7.0 s'i **rahat bir üst sınır**.
AVSR modülü için ~12–13 dk planlanabilir.

**Bu koşunun bulduğu bir hata:** özet çıktısındaki "Görsel fayda (AV − A)"
satırı U+2212 eksi işareti içeriyordu ve Windows'un Türkçe konsolu (cp1254) onu
basamıyor — koşunun **sonunda**, veri toplandıktan sonra `UnicodeEncodeError`
veriyordu. Aynı karakter sınıfı kodda yedi yerde daha vardı (GIN ve yedek
doğrulama hata mesajları dahil, yani hata mesajının yerine başka bir hata
geçiyordu). Hepsi ASCII'ye çevrildi ve `tests/mcgurk/test_console_encoding.py`
her koşuda tekrarını engelliyor.

**Otomatik testler:** 556 test yeşil (451 → 556), `ruff` + `mypy` temiz.
Yeni olanlar: 42 AVSR tasarım/skorlama/ölçüt testi, 4 donanım testi,
42 konsol kodlama testi.

**Sonraki adıma kalan:** kelime seti (§F.2) hâlâ boş —
`config/word_lists/tr_pb_50.yaml` şablonu hazır, `enabled: true` yapıldığında
config yüklenirken açık hata veriyor. `open_set` yanıt modu `NotImplementedError`
veriyor.
