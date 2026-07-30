# Adım 8b-ii Manuel Test — Alıştırma + çapraz dinleme + ESC onayı

Adım 8b'nin ikinci turu. Üç yeni davranış:

1. **ESC onay ekranı** — ESC'ye basınca doğrudan çıkmak yerine "emin misiniz?"
   sorulur.
2. **Alıştırma bloğu** — asıl testten önce uyumlu ısınma denemeleri.
3. **Çapraz dinleme** — SSD katılımcısının sağır kulağına tespit görevi.

**Toplam süre ~4–6 dakika** (`--limit` ile kısaltılmış).

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| Otomatik testler | **783 test yeşil** (CI alt kümesi; 21 yeni), `ruff` + `mypy` temiz |
| Yeni testler | çapraz dinleme tasarımı+atfetme (10), alıştırma tasarımı (4), ESC confirmer mantığı (4) + oddball ton testi güncellendi |
| ESC confirmer | confirmer takılıyken ESC→onay, takılı değilken (harness/testler) anında kes — donanımsız doğrulandı |
| Çapraz dinleme | sinyal/catch dengesi, sağır kulak, tohumdan üretilebilirlik, isabet/yanlış alarm sınıflaması |

## Ön koşullar

- [ ] Conda ortamı etkin veya komutlarda tam yol.
- [ ] Kulaklık/aygıt bağlı (yoksa `--device "<ad>"`).
- [ ] Komutlar **PowerShell**, veritabanı **geçici**.

---

## Test 1: Alıştırma + çapraz dinleme (SSD katılımcısı, ~4 dk)

**Komut:**

```powershell
python -m mcgurk.ui --limit 4 --db $env:TEMP\mcgurk_8bii.sqlite
```

Giriş penceresinde **SSD bir katılımcı** girin (çapraz dinlemenin çalışması için):
kod `TEST-SSD`, yaş `30`, grup **SSD-Sağ**, PTA Sağ `70`, PTA Sol `10`.
(Böylece iyi kulak = sol, **sağır kulak = sağ**.)

**Sırayla ne olmalı:**

1. Checklist onayı → **Karşılama**.
2. **Alıştırma:** önce `practice_intro` ekranı ("kısa bir alıştırma… kaydedilmez")
   → **4 uyumlu deneme** (yüz + aynı hece, McGurk yanıt ızgarası) → `practice_end`
   ekranı ("Alıştırma bitti… hazır olduğunuzda asıl test başlayacak").
3. Ölçüm modülleri (mcgurk → … → gin), her biri yönergesiyle, 4'er deneme.
4. **Çapraz dinleme:** `cross_hearing_intro` ekranı → **4 tespit denemesi**.
   Bir kısmında **sağ (sağır) kulaktan** kısa bir ton gelir, bir kısmı sessizdir
   (catch). Ton duyunca **BOŞLUK**'a basın.
5. **Bitiş ekranı** → yedek + çıkış 0.

**Kontrol edilecek:**

1. **Alıştırma denemeleri uyumlu** (dudak ile ses aynı hece) ve **geri bildirim
   yok**. Alıştırma verisi `practice` bloğuna yazılır (analize girmez).
2. **Çapraz dinleme tonu sağır kulaktan** geliyor (SSD-Sağ girdiyseniz sağdan).
   Catch denemelerinde hiç ses yok.
3. Konsolda çapraz dinleme özeti: **isabet /sinyal**, **yanlış alarm /catch**,
   ve "şans üstü tespit → lateralizasyon geçersiz olabilir" notu.

**Kontrol grubu farkı (isteğe bağlı):** Aynı komutu **Kontrol** grubuyla
çalıştırın. Çapraz dinleme **atlanır** (konsolda "kontrol grubunda atlanıyor…"
loglanır) — kontrol katılımcısının sağır kulağı yoktur.

**Yalnızca çapraz dinlemeyi açıp kulağı teyit etmek (izole):** Tam oturumu
beklemeden yalnızca bu kontrolü koşabilirsiniz. `--ear` = **sağır kulak**:

```powershell
python tools/run_cross_hearing.py --ear right --limit 8 --db $env:TEMP\mcgurk_ch.sqlite
```

Ton **sağ** kanaldan gelmeli (catch denemelerinde tümüyle sessiz). `--ear left`
ile tekrar koşup sesin sola geçtiğini doğrulayın — yön bayrağı takip etmeli.

---

## Test 2: ESC onay ekranı (~1 dk)

Test 1'i tekrar başlatın ve **farklı aşamalarda ESC**'ye basın (yönerge ekranı,
deneme sunumu sırasında, yanıt ekranı, alıştırma).

Her ESC'de şu ekran çıkmalı:

```
Oturumdan çıkmak istediğinize emin misiniz?

Evet, çık: ENTER
İptal, devam et: ESC
```

**Kontrol edilecek:**

1. **ESC (İptal) → oturum kaldığı yerden devam ediyor** (ekran yeniden çiziliyor,
   deneme akışı sürüyor). Oturum kesilmiyor.
2. **ENTER (Evet) → oturum kesiliyor**, konsolda "Oturum ESC ile kesildi.",
   yedek yazılıyor, çıkış kodu **2**.
3. Onay ekranı **uyaran sunumu sırasında da** çıkıyor (video/ton oynarken ESC).
   Bu sırada İptal denirse o deneme kare düşmesiyle işaretlenebilir — beklenen.

Çıkış kodunu görmek için:

```powershell
python -m mcgurk.ui --limit 4 --db $env:TEMP\mcgurk_8bii.sqlite; "EXIT=$LASTEXITCODE"
```

---

## Kabul kriterleri

- [ ] Alıştırma: intro → uyumlu ısınma denemeleri → end ekranı; geri bildirim yok
- [ ] Alıştırma verisi `practice` bloğuna yazılıyor, analize girmiyor
- [ ] Çapraz dinleme SSD'de sağır kulağa sunuluyor (sinyal + catch), BOŞLUK ile
      tespit; konsol özeti isabet/yanlış alarmı gösteriyor
- [ ] Çapraz dinleme kontrol grubunda atlanıyor (loglanıyor)
- [ ] ESC → onay ekranı çıkıyor (her aşamada, sunum dahil)
- [ ] İptal → oturum devam ediyor; Evet → `aborted` + yedek + çıkış 2
