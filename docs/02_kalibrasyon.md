# Ses Seviyesi Kalibrasyonu

**Amaç:** Dijital ses seviyesi ile kulakta oluşan gerçek ses basıncı arasındaki eşlemeyi ölçmek, sistemi hedef sunum seviyesine ayarlamak.

**Süre:** 45 dk (bir kez).

**Ne zaman tekrarlanır:** Kulaklık, ses arayüzü, sürücü veya kablo değiştiğinde. Ayrıca ayda bir kontrol amaçlı (kulaklıklar zamanla değişir).

---

## 1. Üç farklı "dB" var, karıştırmayın

Yazılımcı için en kafa karıştırıcı kısım bu.

| Birim | Neye göre | Aralık | Nerede |
|---|---|---|---|
| **dBFS** | Dijital tam ölçek | Hep negatif, 0 = maksimum | Kodunuzda |
| **dB SPL** | 20 µPa ses basıncı | 0–120+ | Ses seviyesi ölçerde |
| **dB HL** | Normal işitme eşiği | −10 – 120 | Odyogramda |

**dBFS** dijital bir orandır. `-23 dBFS` demek, sinyalin RMS'inin tam ölçeğin 1/14'ü olması demek. Fiziksel bir karşılığı yoktur — aynı dosya bir sistemde fısıltı, başkasında bağırtı olabilir.

**dB SPL** fiziksel ses basıncıdır, mutlaktır.

**dB HL** odyolojiye özgüdür: her frekansta normal işitenlerin ortalama eşiğine göre ölçülür (bu yüzden odyogramda 0 dB HL "normal", her frekansta farklı SPL karşılığı vardır). Katılımcılarınızın odyogramları bu birimde olacak, ama sizin kalibre edeceğiniz şey SPL.

Kalibrasyon şu sabiti bulmaktır:

```
dB SPL = dBFS + K
```

`K` sisteminizin (DAC + amplifikatör + kulaklık) özelliğidir. Tipik olarak 75–100 dB arası çıkar.

---

## 2. Neden gerekli

**SNR kalibrasyondan bağımsızdır.** +5 dB oran dijital ortamda tam olarak elde edilir; mutlak seviyeyi bilmenize gerek yok.

**Sunum seviyesi bağımsız değildir.** 50 dB SPL'de +5 dB SNR ile 75 dB SPL'de +5 dB SNR aynı görevi üretmez:

- İşitsel sinyalin duyulabilirliği değişir
- Duyusal ağırlıklandırma değişir — işitsel sinyal zayıflarsa beyin görsele daha çok yaslanır
- **Füzyon oranınız doğrudan kayar**

Yani Modül 1'in ana bağımlı değişkeni sunum seviyesine duyarlıdır. Kalibre etmezseniz füzyon oranınızın literatürle karşılaştırılabilirliği kalmaz ve pilot doğrulamanız işlevsiz olur.

**SSD'de ek bir boyut var:** lateralize sunumda "sol kulağa 65 dB SPL" dediğinizde, o kulak 90 dB HL kayıplıysa hiçbir şey duyulmuyor demektir. Seviyenin hangi kulağa referanslandığı protokol kararıdır (bkz. §9).

---

## 3. Malzeme

| Parça | Not |
|---|---|
| Ses seviyesi ölçer | Tip 1 veya Tip 2, oktav bandı analizi tercihen |
| Yapay kulak (coupler) | Kulaklık tipine göre — aşağıya bakın |
| Deneyde kullanacağınız kulaklık | Kalibrasyon kulaklığa özeldir |
| Ses arayüzü | Deneyde kullanacağınız |
| Kalibratör (pistonfon) | Ölçeri doğrulamak için, 94 dB @ 1 kHz |

### Coupler seçimi

| Kulaklık tipi | Coupler | Standart |
|---|---|---|
| Kulak üstü (TDH-39, HDA200) | 6 cc | IEC 60318-1 |
| Kulak içi / insert (ER-3A) | 2 cc | IEC 60318-5 |
| Çevreleyen (HDA300, HD650) | Yapay kulak | IEC 60318-1 |

**Bunlar Odyoloji bölümünde zaten var.** Klinik personel odyometre kalibrasyonunu rutin yapıyor; aynı ekipman, aynı prosedür. Yardım isteyin — 20 dakikalık iş.

---

## 4. Ses zinciri temizliği (bu adımı atlamayın)

İşletim sistemi araya girip sinyali değiştirirse kalibrasyonunuz geçersiz olur. Kalibrasyondan önce **ve deney sırasında** aynı ayarlar geçerli olmalı.

### Windows

Denetim Masası → Ses → Oynatma → aygıt → Özellikler:

- **Geliştirmeler / Enhancements → "Tüm geliştirmeleri devre dışı bırak"**
- **Loudness Equalization → kapalı**
- **Bass Boost, Virtual Surround, Room Correction → kapalı**
- Gelişmiş → Varsayılan biçim: **24 bit, 48000 Hz**
- Gelişmiş → "Uygulamaların özel denetim almasına izin ver" → **açık**
- Ayarlar → Sistem → Ses → **Spatial sound / Windows Sonic → Kapalı**

Ses arayüzünün kendi kontrol panelinde:
- **Loopback → kapalı**
- **DSP / efekt / limiter → kapalı**
- Direct monitoring → kapalı

### macOS

- Audio MIDI Setup → çıkış aygıtı → 48000 Hz, 24 bit
- Sistem ses seviyesi → **maksimum** (sonra donanım kazancıyla ayarlayın)
- Ses efektleri kapalı

### Linux

- PulseAudio/PipeWire yerine **doğrudan ALSA** kullanın veya `hw:` aygıtını hedefleyin
- `pactl` ile aygıt seviyesini %100'e sabitleyin
- `module-ladspa-sink` gibi efekt modülleri yüklüyse kaldırın

### Her platformda

**Kalibrasyondan sonra hiçbir ses seviyesi ayarına dokunmayın.**

Donanım kazanç düğmesini bantlayın ve konumunu fotoğraflayın. Yazılım ses seviyesini not edin. Deney başlangıcında kontrol listesi olarak doğrulayın.

---

## 5. Kalibrasyon scripti

`kalibrasyon.py` olarak kaydedin. Bağımsızdır, sadece numpy gerektirir (çalma için PsychoPy).

```python
#!/usr/bin/env python3
"""
Ses seviyesi kalibrasyonu.

Alt komutlar:
    sinyal     Uyaran korpusundan kalibrasyon gürültüsü üretir
    cal        Kalibrasyon sinyalini çalar (ölçüm sırasında)
    hesap      Ölçülen SPL'den sistem sabitini (K) hesaplar
    lineerlik  Lineerlik kontrolünü değerlendirir
    dogrula    Uyaran dosyalarının seviyelerini kontrol eder

Örnek akış:
    python kalibrasyon.py sinyal --korpus uyaranlar/audio --cikti cal.wav
    python kalibrasyon.py cal --dosya cal.wav --kanal sol
    python kalibrasyon.py hesap --dbfs -23 --spl-sol 58.2 --spl-sag 57.6
"""
import argparse, glob, json, sys, wave
from datetime import datetime
from pathlib import Path

import numpy as np

SR = 48000


# ---------------------------------------------------------------- WAV G/Ç

def read_wav(path):
    with wave.open(str(path), "rb") as w:
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
    return (x.reshape(-1, ch) if ch > 1 else x), sr


def write_wav(path, x, sr=SR):
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    if peak > 1.0:
        raise ValueError(f"kırpma (tepe={peak:.3f})")
    ch = 1 if x.ndim == 1 else x.shape[1]
    q = np.clip(np.round(x * 8388607.0), -8388608, 8388607).astype("<i4")
    b = q.tobytes()
    raw = b"".join(b[i:i+3] for i in range(0, len(b), 4))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch); w.setsampwidth(3); w.setframerate(sr)
        w.writeframes(raw)


# ---------------------------------------------------------------- Seviye

def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2))) if x.size else 0.0


def db(x):
    return 20.0 * np.log10(max(float(x), 1e-12))


def aktif_maske(x, sr, frame_ms=10.0, esik_db=-30.0):
    """Konuşma-aktif çerçeveleri işaretler.

    NEDEN: uyaran dosyalarınızın başında ~1.1 s sessizlik var. Tüm dosya
    RMS'i konuşma seviyesini ~7 dB düşük gösterir. Kalibrasyon ve SNR
    hesabı KONUŞMA-AKTİF bölge üzerinden yapılmalı.
    """
    f = max(1, int(sr * frame_ms / 1000.0))
    n = len(x) // f
    if n == 0:
        return np.ones(len(x), bool)
    fr = np.sqrt(np.mean(x[:n*f].reshape(n, f) ** 2, axis=1) + 1e-20)
    thr = fr.max() * (10 ** (esik_db / 20.0))
    m = np.repeat(fr > thr, f)
    return np.concatenate([m, np.zeros(len(x) - len(m), bool)])


def aktif_rms(x, sr):
    if x.ndim > 1:
        x = x.mean(axis=1)
    m = aktif_maske(x, sr)
    return rms(x[m]) if m.any() else rms(x)


# ---------------------------------------------------------------- Sinyal

def ssn_uret(korpus, sr, sure_s, rng=None, smooth=33):
    """Korpusun uzun dönem ortalama spektrumuna göre gürültü üretir.

    Jenerik beyaz/pembe gürültü KULLANMAYIN. Kalibrasyon sinyali,
    ölçtüğünüz şeyle aynı spektruma sahip olmalı; aksi hâlde ölçer farklı
    bir frekans ağırlığı görür ve okuduğunuz SPL uyaranınkini yansıtmaz.
    """
    rng = rng or np.random.default_rng(20260720)
    n_fft = 1 << int(np.ceil(np.log2(max(len(c) for c in korpus))))

    guc = np.zeros(n_fft // 2 + 1)
    for c in korpus:
        c = np.asarray(c, np.float64)
        if c.ndim > 1:
            c = c.mean(axis=1)
        c = c - c.mean()
        a = c[aktif_maske(c, sr)]
        if a.size < 128:
            a = c
        seg = np.zeros(n_fft)
        k = min(len(a), n_fft)
        seg[:k] = a[:k] * np.hanning(k)
        guc += np.abs(np.fft.rfft(seg)) ** 2
    guc /= len(korpus)

    if smooth > 1:
        guc = np.convolve(guc, np.ones(smooth) / smooth, mode="same")

    mag = np.sqrt(guc)
    mag /= max(mag.max(), 1e-20)

    n_out = int(sure_s * sr)
    n2 = 1 << int(np.ceil(np.log2(n_out)))
    mi = np.interp(np.linspace(0, 1, n2 // 2 + 1),
                   np.linspace(0, 1, len(mag)), mag)
    ph = rng.uniform(-np.pi, np.pi, n2 // 2 + 1)
    ph[0] = 0.0
    if n2 % 2 == 0:
        ph[-1] = 0.0
    y = np.fft.irfft(mi * np.exp(1j * ph), n=n2)[:n_out]
    return y / max(np.abs(y).max(), 1e-20) * 0.5


def rampa(x, sr, ms=100.0):
    n = int(sr * ms / 1000.0)
    if n == 0 or 2 * n >= len(x):
        return x
    r = np.sin(np.linspace(0, np.pi / 2, n)) ** 2
    y = x.copy(); y[:n] *= r; y[-n:] *= r[::-1]
    return y


# ---------------------------------------------------------------- Komutlar

def cmd_sinyal(a):
    files = sorted(glob.glob(str(Path(a.korpus) / "*.wav")))
    files = [f for f in files if "SSN" not in Path(f).name]
    if not files:
        print(f"HATA: {a.korpus} içinde WAV yok"); return 1

    korpus, seviyeler = [], []
    print("Korpus:")
    for f in files:
        x, sr = read_wav(f)
        if sr != a.sr:
            print(f"HATA: {Path(f).name} {sr} Hz, {a.sr} bekleniyor"); return 1
        if x.ndim > 1:
            x = x.mean(axis=1)
        korpus.append(x)
        lv = db(aktif_rms(x, sr))
        seviyeler.append(lv)
        print(f"  {Path(f).name:36s} aktif RMS {lv:7.2f} dBFS")

    yay = max(seviyeler) - min(seviyeler)
    print(f"\nToken seviye yayılımı: {yay:.2f} dB", end="  ")
    print("-> OK" if yay <= 0.5 else "-> UYARI: uyaranları normalize edin")

    hedef_rms = 10 ** (a.dbfs / 20.0)
    y = ssn_uret(korpus, a.sr, a.sure, smooth=33)
    y = y * (hedef_rms / max(rms(y), 1e-20))
    y = rampa(y, a.sr)

    tepe = db(np.abs(y).max())
    print(f"\nKalibrasyon sinyali:")
    print(f"  RMS       : {db(rms(y)):7.2f} dBFS  (hedef {a.dbfs:.1f})")
    print(f"  tepe      : {tepe:7.2f} dBFS")
    print(f"  crest     : {tepe - a.dbfs:7.2f} dB")
    if tepe > -1.0:
        print("  UYARI: tepe 0'a çok yakın. --dbfs değerini düşürün.")

    write_wav(a.cikti, np.column_stack([y, y]), a.sr)
    print(f"\nYazıldı: {a.cikti}  ({a.sure:.0f} s, stereo)")

    meta = {"olusturma": datetime.now().isoformat(timespec="seconds"),
            "kaynak": [Path(f).name for f in files],
            "dbfs": a.dbfs, "sure_s": a.sure, "sample_rate": a.sr,
            "tepe_dbfs": round(tepe, 2)}
    Path(a.cikti).with_suffix(".json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


def cmd_cal(a):
    """Kalibrasyon sinyalini çalar. Deneyle AYNI ses yolunu kullanır."""
    from psychopy import prefs
    prefs.hardware["audioLib"] = ["ptb"]
    prefs.hardware["audioLatencyMode"] = 3
    from psychopy import sound, core

    x, sr = read_wav(a.dosya)
    if x.ndim == 1:
        x = np.column_stack([x, x])

    y = np.zeros_like(x)
    if a.kanal in ("sol", "left", "l"):
        y[:, 0] = x[:, 0]
    elif a.kanal in ("sag", "sağ", "right", "r"):
        y[:, 1] = x[:, 1]
    else:
        y = x

    print(f"Backend  : {getattr(sound, 'audioLib', '?')}")
    print(f"Kanal    : {a.kanal}")
    print(f"RMS      : {db(rms(y[y != 0])):7.2f} dBFS")
    print(f"Süre     : {len(y)/sr:.0f} s, {a.tekrar} tekrar")
    print("\nÖlçeri SLOW / RMS moda, LINEAR (Z) ağırlığa alın.")
    print("Okuma sabitlenene kadar bekleyin (~5 s).\n")
    print("Çalıyor... (Ctrl+C ile durdurun)")

    snd = sound.Sound(value=y, sampleRate=sr, stereo=True,
                      hamming=False, preBuffer=-1, loops=a.tekrar - 1)
    try:
        snd.play()
        core.wait(len(y) / sr * a.tekrar + 0.5)
    except KeyboardInterrupt:
        pass
    finally:
        snd.stop()
    print("Bitti.")
    return 0


def cmd_hesap(a):
    K_sol = a.spl_sol - a.dbfs
    K_sag = a.spl_sag - a.dbfs
    fark = K_sol - K_sag

    print("=" * 56)
    print(f"  Ölçüm seviyesi     : {a.dbfs:7.1f} dBFS")
    print(f"  Ölçülen SPL sol    : {a.spl_sol:7.1f} dB SPL")
    print(f"  Ölçülen SPL sağ    : {a.spl_sag:7.1f} dB SPL")
    print("-" * 56)
    print(f"  K (sol)            : {K_sol:7.2f} dB")
    print(f"  K (sağ)            : {K_sag:7.2f} dB")
    print(f"  Kanal farkı        : {fark:+7.2f} dB", end="  ")
    print("OK" if abs(fark) <= 1.0 else "-> TRİM GEREKLİ")
    print("=" * 56)

    K = (K_sol + K_sag) / 2
    gerekli = a.hedef - K
    print(f"\n  Hedef sunum        : {a.hedef:7.1f} dB SPL")
    print(f"  Gereken dijital sv.: {gerekli:7.2f} dBFS")
    delta = gerekli - a.dbfs
    print(f"  Fark               : {delta:+7.2f} dB")

    if abs(delta) < 0.5:
        print("\n  -> Sistem zaten hedefte. Kazanç düğmesine dokunmayın.")
    elif delta > 0:
        print(f"\n  -> Donanım kazancını {delta:+.1f} dB ARTIRIN, sonra")
        print("     ölçümü tekrarlayın.")
        print("     Dijital seviyeyi yükseltmeyin — tepe payınız yeterli")
        print("     olmayabilir (crest faktörü tipik 15-18 dB).")
    else:
        print(f"\n  -> Donanım kazancını {-delta:.1f} dB AZALTIN, sonra")
        print("     ölçümü tekrarlayın.")

    print(f"\n  Kanal trim (dijital, kalıcı):")
    print(f"    sol : {K - K_sol:+6.2f} dB   (× {10**((K-K_sol)/20):.4f})")
    print(f"    sağ : {K - K_sag:+6.2f} dB   (× {10**((K-K_sag)/20):.4f})")

    out = {"tarih": datetime.now().isoformat(timespec="seconds"),
           "olcum_dbfs": a.dbfs, "spl_sol": a.spl_sol, "spl_sag": a.spl_sag,
           "K_sol": round(K_sol, 2), "K_sag": round(K_sag, 2),
           "K_ortalama": round(K, 2), "kanal_farki_db": round(fark, 2),
           "hedef_spl": a.hedef, "gereken_dbfs": round(gerekli, 2),
           "trim_sol_db": round(K - K_sol, 2), "trim_sag_db": round(K - K_sag, 2)}
    Path(a.cikti).write_text(json.dumps(out, indent=2, ensure_ascii=False),
                             encoding="utf-8")
    print(f"\n  Kaydedildi: {a.cikti}")
    return 0


def cmd_lineerlik(a):
    sv = np.array(a.seviyeler, float)
    sp = np.array(a.spl, float)
    if len(sv) != len(sp):
        print("HATA: seviye ve SPL sayısı eşit olmalı"); return 1
    if len(sv) < 3:
        print("HATA: en az 3 nokta gerekli"); return 1

    egim, kesisim = np.polyfit(sv, sp, 1)
    tahmin = egim * sv + kesisim
    art = sp - tahmin

    print(f"{'dBFS':>8} {'ölçülen':>9} {'model':>8} {'artık':>8}")
    for a_, b_, c_, d_ in zip(sv, sp, tahmin, art):
        print(f"{a_:8.1f} {b_:9.1f} {c_:8.2f} {d_:+8.2f}")

    print(f"\n  eğim     = {egim:.4f}   (1.000 olmalı)")
    print(f"  kesişim  = {kesisim:.2f} dB  (= K)")
    print(f"  maks artık = {np.abs(art).max():.2f} dB")

    if abs(egim - 1.0) > 0.02:
        print("\n  BAŞARISIZ: sistem lineer değil.")
        print("  Zincirde limiter/kompresör var. Ses 'geliştirmelerini',")
        print("  loudness equalization'ı ve arayüz DSP'sini kapatın.")
        return 2
    if np.abs(art).max() > 0.5:
        print("\n  UYARI: artıklar büyük. Ölçümü tekrarlayın.")
    else:
        print("\n  Lineerlik OK.")
    return 0


def cmd_dogrula(a):
    files = sorted(glob.glob(str(Path(a.klasor) / "*.wav")))
    if not files:
        print(f"HATA: {a.klasor} içinde WAV yok"); return 1

    cal = json.loads(Path(a.kalibrasyon).read_text(encoding="utf-8"))
    K = cal["K_ortalama"]
    print(f"K = {K:.2f} dB  (kalibrasyon: {cal['tarih']})\n")
    print(f"{'dosya':38s} {'aktif RMS':>11} {'tepe':>9} {'-> SPL':>9}")
    print("-" * 70)

    seviyeler = []
    for f in files:
        x, sr = read_wav(f)
        if x.ndim > 1:
            x = x.mean(axis=1)
        lv = db(aktif_rms(x, sr))
        pk = db(np.abs(x).max())
        seviyeler.append(lv)
        flag = "  <- KIRPMA" if pk > -0.5 else ""
        print(f"{Path(f).name:38s} {lv:10.2f}  {pk:8.2f}  {lv+K:8.2f}{flag}")

    yay = max(seviyeler) - min(seviyeler)
    print("-" * 70)
    print(f"Seviye yayılımı: {yay:.2f} dB", end="  ")
    print("-> OK" if yay <= 0.5 else "-> UYARI: normalize edin")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sinyal", help="kalibrasyon sinyali üret")
    s.add_argument("--korpus", required=True, help="uyaran WAV'larının klasörü")
    s.add_argument("--cikti", default="kalibrasyon_sinyali.wav")
    s.add_argument("--dbfs", type=float, default=-23.0)
    s.add_argument("--sure", type=float, default=60.0)
    s.add_argument("--sr", type=int, default=SR)
    s.set_defaults(fn=cmd_sinyal)

    c = sub.add_parser("cal", help="kalibrasyon sinyalini çal")
    c.add_argument("--dosya", default="kalibrasyon_sinyali.wav")
    c.add_argument("--kanal", default="ikisi", choices=["sol", "sag", "ikisi"])
    c.add_argument("--tekrar", type=int, default=3)
    c.set_defaults(fn=cmd_cal)

    h = sub.add_parser("hesap", help="K ve gereken seviyeyi hesapla")
    h.add_argument("--dbfs", type=float, required=True)
    h.add_argument("--spl-sol", type=float, required=True)
    h.add_argument("--spl-sag", type=float, required=True)
    h.add_argument("--hedef", type=float, default=65.0)
    h.add_argument("--cikti", default="kalibrasyon.json")
    h.set_defaults(fn=cmd_hesap)

    l = sub.add_parser("lineerlik", help="lineerlik kontrolü")
    l.add_argument("--seviyeler", type=float, nargs="+", required=True)
    l.add_argument("--spl", type=float, nargs="+", required=True)
    l.set_defaults(fn=cmd_lineerlik)

    d = sub.add_parser("dogrula", help="uyaran seviyelerini kontrol et")
    d.add_argument("--klasor", required=True)
    d.add_argument("--kalibrasyon", default="kalibrasyon.json")
    d.set_defaults(fn=cmd_dogrula)

    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
```

---

## 6. Prosedür

### Adım 0 — Ölçeri doğrulayın

Kalibratörü (pistonfon) ölçere takın, 94 dB @ 1 kHz okumalı. Sapma varsa ölçeri ayarlayın. Bu adım atlanırsa tüm ölçüm kayar.

### Adım 1 — Kalibrasyon sinyalini üretin

```bash
python kalibrasyon.py sinyal --korpus uyaranlar/audio --dbfs -23 --sure 60
```

Sinyal, uyaranlarınızın **uzun dönem ortalama spektrumuyla** üretilir ve **aynı aktif RMS'e** ölçeklenir. Yani ölçtüğünüz SPL, doğrudan uyaranlarınızın SPL'idir.

Çıktıdaki token seviye yayılımına bakın — 0.5 dB'den büyükse uyaranlarınız normalize edilmemiş demektir, önce onu düzeltin.

### Adım 2 — Kulaklığı couplera yerleştirin

- Kulak üstü: kulaklığı couplerin üzerine, üretici spesifikasyonundaki bastırma kuvvetiyle (tipik 4.5 N) yerleştirin
- Insert: kulaklık ucunu 2 cc couplera tam oturtun, kaçak olmadığından emin olun

Kaçak varsa özellikle düşük frekanslarda okuma düşer. Birkaç kez yerleştirip tekrarlayın; okumalar 1 dB içinde tutarlı olmalı.

### Adım 3 — Ölçer ayarları

- Ağırlık: **Linear / Z** (geniş bant gürültü için)
- Yanıt: **Slow** (1 s zaman sabiti) veya **RMS**
- Aralık: 40–100 dB

dB(A) da kullanılabilir ama **tutarlı olun ve yayında hangisini kullandığınızı belirtin.** İkisi arasında geniş bant gürültü için tipik olarak 1–3 dB fark olur.

### Adım 4 — Sol kanalı ölçün

```bash
python kalibrasyon.py cal --kanal sol
```

Okuma sabitlendikten sonra (~5 s) değeri not edin.

### Adım 5 — Sağ kanalı ölçün

```bash
python kalibrasyon.py cal --kanal sag
```

### Adım 6 — Hesaplayın

```bash
python kalibrasyon.py hesap --dbfs -23 --spl-sol 58.2 --spl-sag 57.6 --hedef 65
```

Script size donanım kazancını kaç dB değiştirmeniz gerektiğini söyler.

### Adım 7 — Kazancı ayarlayın, tekrarlayın

Donanım kazanç düğmesini önerilen kadar çevirin, **Adım 4–6'yı tekrarlayın.** Hedefin ±0.5 dB içine girene kadar devam edin. Genellikle 2–3 tur yeter.

**Neden donanım kazancı:** dijital seviyeyi yükseltmek tepe payınızı yer. Konuşma sinyalinin crest faktörü tipik 15–18 dB; aktif RMS'i −16 dBFS'e çıkarırsanız tepeler 0 dBFS'i aşar ve kırpma olur.

### Adım 8 — Düğmeyi kilitleyin

Kazanç düğmesini bantlayın, konumunu fotoğraflayın.

---

## 7. Lineerlik kontrolü

Sistemde gizli bir limiter/kompresör varsa kalibrasyonunuz sadece tek bir seviyede geçerli olur — ve SNR manipülasyonunuz bozulur.

Üç seviyede ölçün:

```bash
python kalibrasyon.py sinyal --dbfs -23 --cikti c23.wav --korpus uyaranlar/audio
python kalibrasyon.py sinyal --dbfs -33 --cikti c33.wav --korpus uyaranlar/audio
python kalibrasyon.py sinyal --dbfs -43 --cikti c43.wav --korpus uyaranlar/audio
```

Her birini çalıp ölçün, sonra:

```bash
python kalibrasyon.py lineerlik --seviyeler -23 -33 -43 --spl 58.2 48.3 38.1
```

**Eğim 1.000 ± 0.02 olmalı.** Değilse zincirde bir şey sinyali sıkıştırıyor — §4'teki ayarları tekrar gözden geçirin.

---

## 8. Kanal dengesi

Sol ve sağ arasında 0.5–2 dB fark normaldir (kulaklık üretim toleransı). Ama **lateralizasyon sizin bağımsız değişkeniniz**, dengesizlik doğrudan karıştırıcı olur.

`hesap` komutu size dijital trim katsayılarını verir. Bunları config'e yazın ve motor her uyarana uygulasın:

```yaml
kalibrasyon:
  K_ortalama: 81.20
  trim_sol_db: -0.30
  trim_sag_db: +0.30
  hedef_spl: 65.0
```

Fark 3 dB'yi aşıyorsa kulaklıkta veya kablolamada bir sorun var — trim ile kapatmayın, kaynağı bulun.

---

## 9. SSD'ye özel: çapraz dinleme

**Bu, protokolünüzü doğrudan etkileyen bir konu ve danışmanınızla konuşmanız gerekiyor.**

Bir kulağa verilen ses, kafatası yoluyla diğer kulağın kokleasına da ulaşır. Aradaki zayıflamaya **kulaklar arası zayıflama** (interaural attenuation, IA) denir:

| Kulaklık tipi | IA (yaklaşık) |
|---|---|
| Kulak üstü (TDH-39, HDA200) | 40–50 dB |
| Çevreleyen | 45–55 dB |
| Kulak içi / insert (ER-3A) | 70–100 dB |

**Sorun:** SSD katılımcısında sağır kulağa 65 dB SPL verdiğinizde:

- Kulak üstü kulaklıkla: iyi kokleaya ~20–25 dB SPL ulaşır → **duyulabilir olabilir**
- Insert kulaklıkla: ~−5 dB SPL → güvenle duyulmaz

Yani kulak üstü kulaklıkla "sağır kulağa sunum" koşulunuz aslında "iyi kulağa zayıf sunum" olabilir. Bu, Modül 1'in lateralizasyon manipülasyonunu tamamen geçersiz kılar.

**Üç seçenek:**

1. **Insert kulaklık kullanın** (önerilen). IA yeterli, ayrıca coupler'ı 2 cc olur.
2. **Karşı kulağa maskeleme** uygulayın. Klinik standart ama deneyi karmaşıklaştırır ve maskeleyici gürültü kendisi bir değişken olur.
3. **Ampirik doğrulama:** her katılımcıda, sağır kulağa sunumda basit bir tespit görevi çalıştırın. Performans şans düzeyindeyse çapraz dinleme yok demektir. Bu her hâlükârda yapılmalı — kayıt altına alınacak bir kontrol.

**Not:** insert kulaklık kullanırsanız A/V gecikme ölçümünde tüp gecikmesini de hesaba katın (bkz. `01_av_gecikme_olcumu.md` §11).

---

## 10. Kayıt formu

```
tarih                 : 2026-07-20
ölçen                 : ___
—
ölçer                 : marka, model, seri no
  son doğrulama       : 94.0 dB @ 1 kHz, sapma +0.1 dB
  ağırlık             : Linear (Z)
  yanıt               : Slow
coupler               : IEC 60318-1, 6 cc
kulaklık              : marka, model, seri no
ses arayüzü           : marka, model, seri no
  kazanç düğmesi      : saat 2 yönü (fotoğraf: kazanc_2026-07-20.jpg)
  yazılım seviyesi    : %100
—
kalibrasyon sinyali   : kalibrasyon_sinyali.wav, -23.0 dBFS
ölçülen SPL sol       : 65.1 dB SPL
ölçülen SPL sağ       : 64.8 dB SPL
K (ortalama)          : 88.05 dB
kanal farkı           : +0.30 dB
dijital trim          : sol -0.15 dB, sağ +0.15 dB
—
lineerlik eğimi       : 1.005
maks artık            : 0.10 dB
—
hedef sunum seviyesi  : 65.0 dB SPL
gürültü koşulu SNR    : +5 dB
  -> konuşma          : 65.0 dB SPL
  -> gürültü          : 60.0 dB SPL
```

Bu form yayının yöntem bölümüne doğrudan girer.

---

## 11. Her oturum öncesi kontrol listesi

Kalibrasyon bir kez yapılır ama **her oturumda doğrulanmalı** — 30 saniyelik iş:

- [ ] Kazanç düğmesi bantlı ve fotoğraftaki konumda
- [ ] Yazılım ses seviyesi %100
- [ ] Ses geliştirmeleri kapalı (Windows güncellemesi bunları geri açabilir)
- [ ] Örnekleme hızı 48000 Hz
- [ ] Kulaklık kablosu sağlam, doğru jack'te
- [ ] `python kalibrasyon.py dogrula --klasor uyaranlar/audio` çıktısı beklenen SPL'i veriyor

Bu değerler oturum kaydına (`sessions` tablosu → `calibration_id`) bağlanmalı; hangi katılımcının hangi kalibrasyonla test edildiği geriye dönük belli olsun.
