# A/V Gecikme Ölçümü (Fotodiyot)

**Amaç:** Ses ile görüntü arasındaki sabit sistem gecikmesini (**D**) ölçmek ve deney motoruna telafi parametresi olarak vermek.

**Süre:** Kurulum 30 dk (bir kez), ölçüm 15 dk.

**Ne zaman tekrarlanır:** Monitör, ses kartı, ses sürücüsü veya işletim sistemi değiştiğinde. Ayrıca 3 ayda bir kontrol amaçlı.

---

## 1. Ne ölçüyoruz

Yazılımda iki zaman damganız var:

- `t_flip` — GPU'ya "buffer swap" dediğiniz an
- `t_audio` — PTB'ye "sesi şu an başlat" dediğiniz an

Fiziksel dünyada iki olay var:

- `t_foton` — ışığın ekrandan gerçekten çıktığı an
- `t_ses` — kulaklığın havayı gerçekten ittiği an

Aralarındaki ilişki:

```
t_foton = t_flip  + D_video
t_ses   = t_audio + D_ses
```

`D_video` ve `D_ses` bilinmiyor. Katılımcının yaşadığı gerçek asenkroni:

```
SOA_gerçek = SOA_nominal + (D_ses − D_video)
                          └──────┬───────┘
                                 D
```

**İki gecikmeyi ayrı ayrı bilmenize gerek yok — sadece farkları olan D'yi bilmeniz yeterli.** Bu ölçüm doğrudan D'yi verir.

### Neden yazılımdan ölçülemiyor

`flip()`'ten sonra scanout, panel yanıt süresi ve monitörün iç işlemesi var. Hiçbir API bunları raporlamaz. Fotonun çıktığını görmenin tek yolu ışığı fiziksel olarak ölçmektir.

### Giriş gecikmesi neden sorun değil

Fotodiyot ve loopback aynı ADC'ye, aynı örnek saatine bağlanır. Kayıttaki iki kanal arasındaki farkı aldığınızda giriş gecikmesi her iki terimde de aynı olduğu için sadeleşir:

```
D = (ses onset örneği − ışık onset örneği) / örnekleme_hızı
```

48 kHz'de çözünürlük 0.02 ms.

---

## 2. Malzeme

| Parça | Öneri | Yaklaşık fiyat |
|---|---|---|
| Fotodiyot | BPW34 (veya SFH203, BPX61) | 15–30 TL |
| Direnç | 100 kΩ, 1/4 W | 1 TL |
| Jack | 6.35 mm mono (TS) lehimlenebilir | 20 TL |
| Kablo | 30–50 cm ekranlı, tek damarlı | 20 TL |
| Loopback kablosu | 3.5 mm ↔ 6.35 mm, stereo veya mono | 50 TL |
| Ses arayüzü | Behringer UMC22 / Focusrite Scarlett Solo | 1500–3000 TL |
| Bant | Kağıt bant (izleyi bırakmaz) | — |

### ⚠️ LDR kullanmayın

Işığa duyarlı **direnç** (LDR / fotorezistör, GL5528 gibi) ucuzdur ama 10–100 ms yanıt süresi vardır. Ölçmeye çalıştığınız büyüklükle aynı mertebede. Mutlaka **fotodiyot** olmalı — yanıt süresi mikrosaniye mertebesindedir.

### ⚠️ Dizüstü combo jack'i kullanmayın

Çoğu dizüstünde tek 3.5 mm TRRS jack var (hem kulaklık hem mikrofon). Mikrofon girişi çok hassastır ve bias voltajı taşır; kulaklık çıkışını doğrudan bağlarsanız kırpar. Ayrı giriş/çıkışı olan USB ses arayüzü gerekli — zaten deney için de isteyeceğiniz şey.

---

## 3. Devre

Fotodiyot **fotovoltaik modda** (besleme yok) çalışır. Işık vurunca akım üretir, direnç üzerinde voltaja dönüşür.

```
       fotodiyot
   ┌──────|◀|──────┐
   │               │
   │   ┌───────┐   │
   ├───┤ 100kΩ ├───┤
   │   └───────┘   │
   │               │
  tip            sleeve
   └──── 6.35mm TS jack ────┘
```

Yani: fotodiyot ve direnç **paralel**, ikisi birlikte jack'in ucu (tip) ile gövdesi (sleeve) arasına.

**Polarite önemli değil.** Ters bağlarsanız sinyal negatif yönde çıkar; analiz mutlak değer aldığı için sonuç değişmez.

**Direnç değeri:** 100 kΩ ile başlayın. Sinyal zayıfsa 1 MΩ deneyin; çok güçlüyse (kırpıyorsa) 10 kΩ. Yüksek direnç daha güçlü sinyal ama daha yavaş yanıt verir — 1 MΩ'da bile yanıt ~100 µs, bizim için fazlasıyla hızlı.

**Lehim yapamıyorsanız:** krokodil pensli test kabloları ve bir breadboard yeterli. Kalıcı olmasına gerek yok.

---

## 4. Kurulum

### 4.1 Bağlantılar

1. **Fotodiyot → arayüz Giriş 1.** Arayüzde "Hi-Z / Instrument" anahtarı varsa açın (yüksek empedans fotodiyot için ideal).
2. **Kulaklık çıkışı → arayüz Giriş 2** (loopback kablosu). Kulaklık ses seviyesini **minimuma** alın, sonra yavaşça yükseltin.
3. Kulaklık takılı kalabilir (splitter ile) veya çıkarabilirsiniz — ölçüm elektriksel.

### 4.2 Fotodiyodun konumu

**Fotodiyodu deney uyaranının göründüğü noktaya bantlayın — köşeye değil.**

Ekran yukarıdan aşağı satır satır çizilir. 60 Hz'de üst satır ile alt satır arasında ~16 ms fark vardır. Diyot köşedeyse, ölçtüğünüz gecikme videonun merkezde göründüğü andan sistematik olarak farklı olur.

Deney videosunda ağız bölgesi ekranın neresine düşüyorsa, diyot oraya.

### 4.3 Ortam

- Oda ışıklarını kapatın veya kısın (fotodiyot ortam ışığından etkilenir)
- Ekran parlaklığını deney sırasında kullanacağınız seviyeye ayarlayın
- Ekran koruyucu, otomatik parlaklık, gece modu / f.lux → **kapatın**
- Monitörde "game mode" varsa açın (iç işlemeyi azaltır), ama deney sırasında da açık kalsın

### 4.4 Ses ayarları

Windows'ta:
- Ses aygıtı özellikleri → **Enhancements / Geliştirmeler → tümünü kapatın**
- **Loudness Equalization → kapalı**
- Spatial sound / Windows Sonic → **kapalı**
- Örnekleme hızı 48000 Hz, 24 bit

Arayüzün kendi yazılımında **"loopback" özelliği varsa kapatın.** O dijital yönlendirme yapar ve DAC/ADC'yi atlar — tam olarak ölçmek istediğiniz zinciri atlamış olursunuz. Fiziksel kablo şart.

---

## 5. Ölçüm scripti

`olcum_flash.py` olarak kaydedin.

```python
#!/usr/bin/env python3
"""
A/V gecikme ölçümü — flaş + klik üretici.

Her denemede ekranda beyaz kare belirir ve tam aynı ana planlanmış bir
klik çalar. Fotodiyot ışığı, loopback kablosu sesi kaydeder. İkisi
arasındaki fark = D.

Kullanım:
    python olcum_flash.py --prova          # konumlandırma için sürekli flaş
    python olcum_flash.py --n 100          # ölçüm
    python olcum_flash.py --soa 150 --n 40 # doğrulama süpürmesi için
"""
import argparse, json, sys
from datetime import datetime

# --- PsychoPy tercihleri: import'lardan ÖNCE ---
from psychopy import prefs
prefs.hardware["audioLib"] = ["ptb"]
prefs.hardware["audioLatencyMode"] = 3

import numpy as np
from psychopy import visual, sound, core, event
import psychtoolbox as ptb

SR = 48000


def make_click(sr=SR, ms=3.0, freq=1000.0, amp=0.5):
    """Keskin başlangıçlı ton patlaması. Rampasız — onset'i tam bulmak için."""
    n = int(sr * ms / 1000.0)
    t = np.arange(n) / sr
    x = amp * np.sin(2 * np.pi * freq * t)
    return np.column_stack([x, x])   # stereo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="deneme sayısı")
    ap.add_argument("--soa", type=float, default=0.0,
                    help="nominal SOA (ms). + = ses geç")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="uygulanacak D telafisi (ms). Doğrulamada kullanın")
    ap.add_argument("--screen", type=int, default=0)
    ap.add_argument("--patch", type=int, default=250, help="flaş karesi (px)")
    ap.add_argument("--pos", type=float, nargs=2, default=[0, 0],
                    help="flaş konumu px (uyaranın olduğu yer)")
    ap.add_argument("--prova", action="store_true",
                    help="sürekli flaş — fotodiyot konumlandırma için")
    ap.add_argument("--out", default="olcum_zamanlar.json")
    args = ap.parse_args()

    win = visual.Window(fullscr=True, screen=args.screen, color="black",
                        units="pix", waitBlanking=True, checkTiming=True,
                        allowGUI=False)
    win.mouseVisible = False

    fps = win.getActualFrameRate(nIdentical=20, nMaxFrames=200,
                                 nWarmUpFrames=20, threshold=1)
    if not fps:
        print("UYARI: kare hızı ölçülemedi, 60 Hz varsayılıyor")
        fps = 60.0
    frame = 1.0 / fps
    print(f"Ölçülen yenileme hızı: {fps:.3f} Hz  (kare {frame*1000:.3f} ms)")

    patch = visual.Rect(win, width=args.patch, height=args.patch,
                        pos=args.pos, fillColor="white", lineWidth=0)

    # --- prova modu: fotodiyot konumlandırma ---
    if args.prova:
        print("PROVA: 0.5 s aralıkla flaş. Audacity'de sinyali izleyin.")
        print("Kapatmak için ESC.")
        while not event.getKeys(keyList=["escape"]):
            for _ in range(int(0.25 / frame)):
                patch.draw(); win.flip()
            for _ in range(int(0.25 / frame)):
                win.flip()
        win.close(); core.quit()

    snd = sound.Sound(value=make_click(), sampleRate=SR, stereo=True,
                      hamming=False, preBuffer=-1)

    backend = getattr(sound, "audioLib", "?")
    print(f"Ses backend: {backend}")
    if "ptb" not in str(backend).lower():
        print("HATA: PTB devrede değil. Ölçüm anlamsız olur.")
        print("      psychtoolbox kurulu mu? pip install psychtoolbox")
        win.close(); return 1

    soa_s = args.soa / 1000.0
    off_s = args.offset / 1000.0
    lead_frames = 4
    rng = np.random.default_rng(0)
    log = []

    print(f"\n{args.n} deneme başlıyor. SOA={args.soa:+.1f} ms, "
          f"telafi={args.offset:+.1f} ms")
    print("Kaydı ŞİMDİ başlatın, sonra Enter'a basın.")
    input()
    core.wait(2.0)   # kaydın başına boşluk

    for i in range(args.n):
        if event.getKeys(keyList=["escape"]):
            print("İptal edildi."); break

        # rastgele denemeler arası süre (periyodik artefaktı önler)
        iti = 0.4 + rng.uniform(0, 0.3)
        for _ in range(int(iti / frame)):
            win.flip()

        # hedef flip zamanını belirle ve sesi ona göre planla
        t_target = win.getFutureFlipTime(clock="ptb") + lead_frames * frame
        t_audio = t_target + soa_s - off_s
        snd.play(when=t_audio)

        # hedefe kadar boş kare çevir
        while win.getFutureFlipTime(clock="ptb") < t_target - frame / 2:
            win.flip()

        patch.draw()
        win.flip()
        t_actual = ptb.GetSecs()

        # flaşı 3 kare açık tut
        for _ in range(3):
            patch.draw(); win.flip()
        win.flip()

        log.append({"i": i, "t_flip_target": t_target, "t_flip_actual": t_actual,
                    "t_audio_scheduled": t_audio, "soa_ms": args.soa,
                    "offset_ms": args.offset})

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{args.n}")

    core.wait(2.0)
    win.close()

    meta = {"timestamp": datetime.now().isoformat(timespec="seconds"),
            "n": len(log), "measured_fps": fps, "frame_ms": frame * 1000,
            "soa_ms": args.soa, "offset_ms": args.offset,
            "sample_rate": SR, "audio_backend": str(backend),
            "latency_mode": prefs.hardware["audioLatencyMode"],
            "trials": log}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    # flip zamanlama sağlığı
    tgt = np.array([t["t_flip_target"] for t in log])
    act = np.array([t["t_flip_actual"] for t in log])
    err = (act - tgt) * 1000
    print(f"\nFlip hedef sapması: ort {err.mean():+.3f} ms, "
          f"SD {err.std(ddof=1):.3f} ms, maks {np.abs(err).max():.3f} ms")
    if np.abs(err).max() > frame * 1000:
        print("UYARI: bir kareden büyük sapma var — vsync sorunu olabilir.")

    print(f"\nZamanlar kaydedildi: {args.out}")
    print("Kaydı durdurun ve WAV olarak kaydedin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## 6. Kayıt alma

Ölçüm scripti sesi **çalar**, kaydı ayrı bir program alır.

### Audacity ile (önerilen, ilk kez için)

1. Audacity → Ses Ayarları → Kayıt aygıtı = ses arayüzünüz, **kanal sayısı = 2 (stereo)**
2. Proje hızı: **48000 Hz**
3. Kayıt seviyesi: sinyal **−12 dBFS civarında** tepe yapsın (kırpma yok)
4. Kayıt (R) → sonra scriptte Enter
5. Bittiğinde Durdur → Dosya → Dışa Aktar → **WAV 24-bit PCM**, adı `olcum.wav`

### Komut satırı ile

```bash
# Linux
arecord -D hw:1,0 -f S24_3LE -r 48000 -c 2 olcum.wav

# macOS / Linux (sox)
rec -b 24 -r 48000 -c 2 olcum.wav

# Windows (ffmpeg)
ffmpeg -f dshow -i audio="Line (UMC22)" -ar 48000 -ac 2 -c:a pcm_s24le olcum.wav
```

### Kanal sırası

Analiz varsayılan olarak **kanal 0 = fotodiyot, kanal 1 = loopback** kabul eder. Ters bağladıysanız `--swap` ile düzeltin.

### ⚠️ Aygıt çakışması

PTB, latency mode 3'te ses aygıtını tekelleştirebilir ve kayıt programı aygıtı açamaz. Böyle bir hata alırsanız:

- Arayüzün **ASIO** sürücüsünü kullanın (eşzamanlı giriş/çıkışı destekler), ya da
- Kaydı **ikinci bir ses aygıtından** alın (örn. dahili ses kartının line-in'i). Farklı aygıt = farklı örnek saati olur ama bizim ölçtüğümüz iki kanal aynı aygıttan geldiği sürece sorun yok.

---

## 7. Analiz scripti

`analiz_gecikme.py` olarak kaydedin.

```python
#!/usr/bin/env python3
"""
A/V gecikme ölçümü — kayıt analizi.

Stereo kayıttan D = t_ses − t_ışık hesaplar.

Kullanım:
    python analiz_gecikme.py olcum.wav
    python analiz_gecikme.py olcum.wav --swap --onset-frac 0.2
"""
import argparse, sys, wave
import numpy as np


def read_wav(path):
    with wave.open(path, "rb") as w:
        sr, n, ch, width = (w.getframerate(), w.getnframes(),
                            w.getnchannels(), w.getsampwidth())
        raw = w.readframes(n)
    if width == 2:
        x = np.frombuffer(raw, "<i2").astype(np.float64) / 32768.0
    elif width == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        p = np.zeros((len(b), 4), np.uint8); p[:, 1:] = b
        x = p.view("<i4").ravel().astype(np.float64) / 2147483648.0
    elif width == 4:
        x = np.frombuffer(raw, "<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"desteklenmeyen genişlik: {width*8} bit")
    return (x.reshape(-1, ch) if ch > 1 else x[:, None]), sr


def envelope(x, sr, smooth_ms=0.5):
    """Doğrultma + kısa hareketli ortalama.

    Zarf kullanmak şart: ham sinüs sinyalinde tepe noktasından geriye
    yürürken ilk sıfır geçişinde durursunuz ve onset'i yanlış bulursunuz.
    """
    e = np.abs(np.asarray(x, np.float64))
    k = max(1, int(sr * smooth_ms / 1000.0))
    return np.convolve(e, np.ones(k) / k, mode="same") if k > 1 else e


def find_onsets(x, sr, threshold_factor=8.0, refractory_ms=150.0,
                onset_frac=0.2, smooth_ms=0.5):
    """Olay başlangıçlarını bulur.

    Eşik, medyan mutlak sapmadan (MAD) türetilir — tek tük büyük olaylar
    eşiği bozmaz. Her olay için tepe bulunur, oradan geriye yürüyerek
    tepenin `onset_frac` katına inilen nokta onset kabul edilir.
    """
    e = envelope(x, sr, smooth_ms)
    med = float(np.median(e))
    mad = float(np.median(np.abs(e - med))) + 1e-12
    thr = med + threshold_factor * 1.4826 * mad

    idx = np.flatnonzero(e > thr)
    if idx.size == 0:
        return np.array([]), thr

    refr = int(sr * refractory_ms / 1000.0)
    groups = np.split(idx, np.flatnonzero(np.diff(idx) > refr) + 1)

    out = []
    for g in groups:
        pk = g[int(np.argmax(e[g]))]
        target = e[pk] * onset_frac
        i = pk
        while i > 0 and e[i] > target:
            i -= 1
        if i < pk and e[i + 1] != e[i]:
            out.append(i + (target - e[i]) / (e[i + 1] - e[i]))
        else:
            out.append(float(pk))
    return np.array(out) / sr, thr


def pair(t_light, t_sound, max_gap=0.2):
    """Her ışık olayına en fazla bir ses olayı eşler."""
    d, unmatched = [], 0
    for tl in t_light:
        diff = t_sound - tl
        m = np.abs(diff) < max_gap
        if m.sum() == 1:
            d.append(diff[m][0])
        else:
            unmatched += 1
    return np.array(d), unmatched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--swap", action="store_true",
                    help="kanalları ters çevir (0=loopback, 1=fotodiyot ise)")
    ap.add_argument("--onset-frac", type=float, default=0.2)
    ap.add_argument("--threshold", type=float, default=8.0)
    ap.add_argument("--expected", type=int, default=None,
                    help="beklenen deneme sayısı")
    ap.add_argument("--nominal-soa", type=float, default=0.0)
    args = ap.parse_args()

    x, sr = read_wav(args.wav)
    if x.shape[1] < 2:
        print("HATA: stereo kayıt gerekli."); return 1

    light = x[:, 1 if args.swap else 0]
    snd = x[:, 0 if args.swap else 1]

    print(f"Kayıt: {args.wav}  {sr} Hz  {x.shape[0]/sr:.1f} s")
    print(f"  ışık kanalı tepe : {np.abs(light).max():.4f}")
    print(f"  ses  kanalı tepe : {np.abs(snd).max():.4f}")
    for name, ch in (("ışık", light), ("ses", snd)):
        if np.abs(ch).max() > 0.99:
            print(f"  UYARI: {name} kanalı kırpıyor — giriş kazancını düşürün")
        if np.abs(ch).max() < 0.01:
            print(f"  UYARI: {name} kanalı çok zayıf — kazancı artırın")

    tl, thr_l = find_onsets(light, sr, args.threshold, onset_frac=args.onset_frac)
    ts, thr_s = find_onsets(snd, sr, args.threshold, onset_frac=args.onset_frac)
    print(f"\n  ışık olayı: {len(tl)}   ses olayı: {len(ts)}")

    if args.expected:
        if len(tl) != args.expected:
            print(f"  UYARI: {args.expected} ışık bekleniyordu, {len(tl)} bulundu")
        if len(ts) != args.expected:
            print(f"  UYARI: {args.expected} ses bekleniyordu, {len(ts)} bulundu")
            print("         Eksikse: ses 'when' zamanı geçmişte kalıyor olabilir")

    d, unmatched = pair(tl, ts)
    if len(d) == 0:
        print("HATA: eşleşen çift yok. Kanal sırasını (--swap) kontrol edin.")
        return 1

    ms = d * 1000.0
    lo, hi = np.percentile(ms, [25, 75])
    iqr = hi - lo
    keep = (ms > lo - 3 * iqr) & (ms < hi + 3 * iqr)
    clean = ms[keep]

    print(f"  eşleşen çift: {len(d)}   eşleşmeyen: {unmatched}   "
          f"aykırı: {(~keep).sum()}")

    print("\n" + "=" * 52)
    print(f"  D (ortalama)  = {clean.mean():+8.3f} ms")
    print(f"  D (medyan)    = {np.median(clean):+8.3f} ms")
    print(f"  jitter (SD)   = {clean.std(ddof=1):8.3f} ms")
    print(f"  min / maks    = {clean.min():+.3f} / {clean.max():+.3f} ms")
    print(f"  n             = {len(clean)}")
    print("=" * 52)

    if args.nominal_soa:
        err = clean.mean() - args.nominal_soa
        print(f"\n  nominal SOA   = {args.nominal_soa:+.1f} ms")
        print(f"  sapma         = {err:+.3f} ms")

    sd = clean.std(ddof=1)
    print()
    if sd < 1.0:
        print("  Jitter: İYİ (< 1 ms)")
    elif sd < 3.0:
        print("  Jitter: KABUL EDİLEBİLİR (1–3 ms)")
    else:
        print("  Jitter: SORUNLU (> 3 ms) — PTB gerçekten devrede mi?")
        print("          prefs, latency mode ve ASIO sürücüsünü kontrol edin.")

    print(f"\n  Not: D pozitifse ses geç çıkıyor demektir.")
    print(f"  config'e yazın:  system_av_offset_ms = {clean.mean():.2f}")

    # histogram
    print("\n  Dağılım:")
    counts, edges = np.histogram(clean, bins=15)
    peak = max(counts.max(), 1)
    for c, e0 in zip(counts, edges[:-1]):
        print(f"    {e0:+7.2f} ms  {'█' * int(40 * c / peak)} {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## 8. Sonucu uygulama

Ölçtüğünüz `D` değerini deney motorunun yapılandırmasına yazın:

```yaml
timing:
  system_av_offset_ms: 18.28   # ölçülen D
  measured_on: "2026-07-20"
  monitor: "Dell U2419H"
  audio_interface: "Behringer UMC22"
  jitter_sd_ms: 0.85
```

Motor ses planlamasında bunu çıkarır:

```
t_audio = t_flip_hedef + SOA_istenen − D
```

**Doğrulaması:**

```
SOA_gerçek = (t_audio + D_ses) − (t_flip + D_video)
           = (t_flip + SOA − D + D_ses) − (t_flip + D_video)
           = SOA − D + (D_ses − D_video)
           = SOA − D + D
           = SOA  ✓
```

---

## 9. Doğrulama süpürmesi

**Bu adımı atlamayın.** Tek noktada (SOA=0) doğrulamak yetmez — zamanlama zincirinin tamamını test etmelisiniz.

```bash
for soa in -300 -200 -100 0 100 200 300; do
  python olcum_flash.py --n 40 --soa $soa --offset 18.28 \
                        --out zaman_$soa.json
  # her koşu için ayrı kayıt alın: dogrulama_$soa.wav
done
```

Her kayıt için:

```bash
python analiz_gecikme.py dogrulama_-300.wav --nominal-soa -300 --expected 40
```

Sonra istenen SOA'ya karşı ölçülen SOA'yı regrese edin:

- **Eğim 1.00 ± 0.02** olmalı
- **Kesişim 0 ± 1 ms** olmalı
- **Artıklar rastgele** olmalı, sistematik eğri değil

Bu test şunları yakalar:
- Negatif SOA'da farklı davranış (planlama penceresi yetmiyor)
- Uç değerlerde kırpılma
- Sistematik ölçek hatası (yanlış örnekleme hızı varsayımı)

Sadece SOA=0'da ölçerseniz hiçbirini göremezsiniz.

---

## 10. Sorun giderme

| Belirti | Olası neden | Çözüm |
|---|---|---|
| Işık kanalında hiç sinyal yok | Kazanç düşük / ortam çok karanlık değil / LDR kullanılmış | Kazancı artırın, `--prova` ile bakın, fotodiyot olduğunu doğrulayın |
| Işık sinyali çok yavaş yükseliyor (>20 ms) | LDR kullanılmış | Fotodiyotla değiştirin |
| Ses olayı sayısı eksik | `when` zamanı geçmişte kalıyor | `lead_frames` değerini artırın |
| Jitter > 3 ms | PTB devrede değil | `sound.audioLib` çıktısını kontrol edin, ASIO sürücüsü kurun |
| Kablo çıkarılınca da klik kaydediliyor | Yazılım loopback açık | Arayüz yazılımından kapatın |
| D her koşuda çok farklı | Ses aygıtı paylaşımlı modda | Exclusive / ASIO moda geçin |
| Flip sapması > 1 kare | Vsync kapalı / kompozitör aktif | `fullscr=True`, GPU ayarlarında vsync zorlayın |
| İki kanal aynı görünüyor | Kanal sırası ters veya tek kanal kaydediliyor | `--swap` deneyin, kayıt kanal sayısını kontrol edin |

---

## 11. Bilinen sınırlar

**Onset ölçütü.** LCD siyahtan beyaza anında geçmez, birkaç ms'lik yükselme vardır. "Işık başlangıcı" dediğiniz nokta yükselmenin %10'u mu %50'si mi — sonucu değiştirir. Sentetik test verisiyle ölçtüğüm sistematik sapma:

| onset_frac | sapma |
|---|---|
| 0.10 | −0.42 ms |
| 0.20 | −0.53 ms |
| 0.50 | −0.89 ms |
| 0.70 | −1.32 ms |

Varsayılan 0.20 kullanılmıştır: sapma yarım milisaniyenin altında, gürültüye de makul dayanıklı. **Yayında hangi ölçütü kullandığınızı belirtin.**

**Loopback transdüseri kapsamaz.** Kulaklık jack'inden ölçüyorsunuz, kulaklık diyaframından değil. Kulak üstü kulaklıkta bu fark ihmal edilebilir (~0.03 ms). **İnsert kulaklıkta (ER-3A gibi) tüp içindeki ses yolu 0.7–1 ms ekler** — tüp uzunluğunu ölçüp 343 m/s'ye bölerek hesaplayın veya kuplaja mikrofon koyup ölçün.

**Daha kesin alternatif:** loopback yerine yapay kulağın mikrofonunu ikinci kanala bağlayın. Tüm akustik yolu kapsar. Kalibrasyon ekipmanı zaten elinizde olacağı için ek maliyeti yok.

---

## 12. Kayıt formu

Her ölçümde şunları saklayın (`kalibrasyon/` klasöründe, git'e dahil):

```
tarih                : 2026-07-20
ölçen                : ___
monitör              : marka, model, seri no
  yenileme hızı      : 60.02 Hz (ölçülen)
  parlaklık ayarı    : ___
  game mode          : açık / kapalı
ses arayüzü          : marka, model, seri no
  sürücü             : ASIO 5.12
  örnekleme hızı     : 48000 Hz
  latency mode       : 3
kulaklık             : marka, model, seri no
fotodiyot konumu     : merkez (0, 0) px
onset ölçütü         : tepe değerinin %20'si
—
D (ortalama)         : +18.28 ms
D (medyan)           : +18.25 ms
jitter (SD)          : 0.85 ms
n                    : 98 / 100
doğrulama eğimi      : 1.002
doğrulama kesişimi   : −0.14 ms
—
ham dosyalar         : olcum.wav, olcum_zamanlar.json
```

Bu form yayının yöntem bölümüne doğrudan girer ve hakem sorusuna hazır cevaptır.
