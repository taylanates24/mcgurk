# Adım 8b-i Manuel Test — Oturum akışı iskeleti

Adım 8b'nin ilk turu: mevcut ölçüm modülleriyle **tam bir oturumu** baştan sona
koşan akış (giriş → checklist onayı → yönergeler → modüller → molalar → bitiş).
Alıştırma bloğu ve çapraz dinleme **8b-ii'de** — akışta yerleri şimdilik
loglanıp atlanıyor.

**Toplam süre ~4–6 dakika** (`--limit` ile kısaltılmış).

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| Otomatik testler | **763 test yeşil** (CI alt kümesi; 22 yeni), `ruff` + `mypy` temiz |
| Yeni testler | `test_ui_login` (12), `test_ui_session` (8, saf kararlar + import güvenliği), `test_block_on_break` (2) |
| Saf kararlar | konuşmacı seçimi (fixed/balanced/random), iyi kulak (PTA/grup), grup+cinsiyet eşlemesi, yaş kriteri — hepsi donanımsız test edildi |
| `run_module` | ortak `runtime.open_hardware`/`start_session`'a taşındı; `--dry-run` doğrulandı |

## Ön koşullar

- [ ] Conda ortamı etkin (`C:\Users\tayla\miniconda3\envs\mcgurk`) veya komutlarda
      tam yol.
- [ ] **Kulaklık/aygıt bağlı** ve `config/experiment.yaml`'daki `audio.device`
      onu gösteriyor. Değilse komuta `--device "<ad>"` ekleyin. Aygıt listesi:
      `python tools/timing_selftest.py --devices`
- [ ] Komutlar **PowerShell** içindir.
- [ ] Testler **geçici bir veritabanına** yazsın ki gerçek `data/` kirlenmesin.

---

## Test 1: Tam akış (kısaltılmış, ~4 dk)

**Komut:**

```powershell
python -m mcgurk.ui --limit 4 --db $env:TEMP\mcgurk_8bi.sqlite
```

**Sırayla ne olmalı:**

1. **Konsolda checklist** basılır (Adım 8a'daki YEŞİL/KIRMIZI satırlar). Dev
   modda KIRMIZI yok, akış durmaz.
2. **Katılımcı giriş penceresi** (ayrı bir diyalog) açılır. Alanlar:
   Katılımcı Kodu, Yaş, Cinsiyet, Grup, Deprivasyon (ay), PTA Sağ, PTA Sol,
   Postlingual, Notlar. **Ad/soyad alanı YOK.**
   - Örnek doldurun: kod `TEST-01`, yaş `30`, cinsiyet `Erkek`, grup `SSD-Sağ`,
     PTA Sağ `70`, PTA Sol `10` (böylece iyi kulak = sol, GIN sola sunulur).
   - **İptal** ederseniz oturum başlamaz (temiz çıkış). Bunu da bir kez deneyin.
3. **Tam ekran pencere** açılır, **operatör checklist onay ekranı** görünür
   (aynı satırlar ekranda). BOŞLUK ile onaylayın.
4. **Karşılama ekranı** → BOŞLUK.
5. Her modül için sırayla: **yönerge ekranı** (BOŞLUK ile geç) → **4 deneme**.
   Modül sırası: practice (atlanır, konsolda loglanır) → mcgurk → avsr → tbw →
   oddball → dichotic → gin → (çapraz dinleme atlanır, loglanır).
6. **Bitiş ekranı** → BOŞLUK.
7. Konsolda **"Yedek: ...backups\mcgurk_...sqlite"** ve çıkış kodu 0.

**Kontrol edilecek — yönerge metinleri (§Don'ts):**

1. **McGurk yönergesi McGurk etkisini ANLATMIYOR** — yalnızca "ne duyduğunuzu"
   sorar, dudak/ses uyuşmasından söz etmez.
2. **Dikotik yönergesi iki hece sunulduğunu SÖYLEMİYOR** ve bir kulağa dikkat
   istemiyor ("Hangi heceyi duydunuz").
3. **GIN yönergesi boşluk sayısı/süresi VERMİYOR** ("kısa bir kesinti duyunca
   basın").
4. **Oddball** hedefin daha tiz olduğunu söyler (bu standart, sorun değil).

**Kontrol edilecek — akış:**

5. **GIN tek kulaktan** geliyor (girişte iyi kulak sol seçildiyse soldan). Kulak
   `--ear` ile değil, **girişten türetiliyor** (PTA/grup).
6. **practice ve çapraz dinleme** konsolda "8b-ii'de gelecek — atlanıyor" diye
   loglanıp geçiliyor (bu turda beklenen).
7. **Hiçbir doğru/yanlış geri bildirimi yok** hiçbir modülde.

**Başarısızsa:** Ses aygıtı açılmıyorsa `HATA: Ses aygıtı açılamadı...` görürsünüz
— kulaklığı açın veya `--device` verin. Bir modül dosya bulamıyorsa
`python tools/verify_stimuli.py` çalıştırın.

---

## Test 2: ESC her aşamada (abort → aborted + yedek)

Test 1'i tekrar başlatın ve **farklı aşamalarda ESC**'ye basın:

- yönerge ekranında,
- bir denemenin sunumu sırasında,
- yanıt ekranında,
- molada (varsa).

**Kontrol edilecek:**

1. ESC basar basmaz oturum **duruyor**, konsolda **"Oturum ESC ile kesildi."**
2. Yine de **yedek yazılıyor** ("Yedek: ...") ve çıkış kodu **2**.
3. Veri kaybı yok — o ana kadarki bloklar veritabanında (durum `aborted`).

Çıkış kodunu görmek için:

```powershell
python -m mcgurk.ui --limit 4 --db $env:TEMP\mcgurk_8bi.sqlite; "EXIT=$LASTEXITCODE"
```

---

## Test 3 (isteğe bağlı): Mola ekranı

`--limit 4` ile mola tetiklenmez (blok sınırı 60). Molayı görmek için geçici
config'te sınırı düşürün:

```powershell
$tmp = Join-Path $env:TEMP 'mcgurk_break.yaml'; (Get-Content config\experiment.yaml -Raw -Encoding utf8) -replace 'break_every_n_trials: 60','break_every_n_trials: 3' | Set-Content $tmp -Encoding utf8; python -m mcgurk.ui --config $tmp --limit 5 --db $env:TEMP\mcgurk_8bi.sqlite; Remove-Item $tmp
```

McGurk modülünde 5 deneme → 3'lük bloklar → **1 mola ekranı** çıkar. BOŞLUK ile
(veya `break_duration_s` sonunda otomatik) devam eder; ESC ile keser.

---

## Kabul kriterleri

- [ ] Giriş penceresi açılıyor, ad/soyad alanı yok; iptal temiz çıkıyor
- [ ] Checklist hem konsolda hem ekranda görünüyor, operatör BOŞLUK ile onaylıyor
- [ ] Karşılama → her modül yönergesi → bitiş ekranları sırayla akıyor
- [ ] Yönergeler §Don'ts'a uygun (McGurk/dikotik/GIN gizli tutuyor)
- [ ] Altı ölçüm modülü de `--limit 4` ile sunuluyor; practice ve çapraz dinleme
      atlanıp loglanıyor
- [ ] GIN kulağı girişten türetiliyor (tek kulak)
- [ ] Oturum tamamlanınca yedek yazılıyor, çıkış kodu 0
- [ ] ESC her aşamada kesiyor, durum `aborted`, yedek yazılıyor, çıkış kodu 2
- [ ] (İsteğe bağlı) Mola ekranı blok sınırında çıkıyor
