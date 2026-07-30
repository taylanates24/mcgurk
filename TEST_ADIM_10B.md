# Adım 10b Manuel Test — PySide6 Operatör Paneli

10a çekirdeği üzerine **buton temelli Qt penceresi**. Python bilmeyen operatör
hiçbir komut yazmadan oturumu başlatır, kontrol listesini koşar, sonuçları
görür, dışa aktarır, analiz/QC raporu alır.

**Ekran gerekir.** "Oturum başlat" ayrıca ses/deney penceresi açar. **Süre ~10 dk.**

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| Otomatik testler | **872 test yeşil** (CI alt kümesi), `ruff` + `mypy` temiz |
| Yeni dosyalar | `mcgurk/panel/app.py` (Qt kabuğu), `mcgurk/panel/__main__.py` (giriş), `test_panel_app.py` (offscreen smoke) |
| Smoke testi | PySide6 kuruluysa offscreen çalışır; **CI'da PySide6 yok → atlanır** (Qt UI CI bağımlılığı değil) |
| Benim açılış denemem | Panel offscreen gerçek config + `data/mcgurk.sqlite` ile açıldı; 8 buton, 1 oturum satırı, başlık doğru |

## Ön koşullar

- [ ] Komutlar **PowerShell**'de. Doğru yorumlayıcı (10a'daki gibi):

```powershell
$PY = "C:\Users\tayla\miniconda3\envs\mcgurk\python.exe"
```

- [ ] Ekran bağlı; ses aygıtı bağlı (yalnız "Oturum başlat" için).
- [ ] En az bir oturum verisi olsun (yoksa `Sonuçlar` boş görünür — sorun değil).
  İsterseniz kısa bir veri üretin: `& $PY tools\run_module.py --module mcgurk --limit 6`

---

## Test 1: Panel açılıyor (~1 dk)

**Komut:**
```powershell
& $PY -m mcgurk.panel
```
**Beklenen:** Bir pencere açılır. Başlıkta `McGurk / SSD Operatör Paneli`.
Üstte dört buton (**Oturum başlat**, **Kontrol listesi**, **Uyaranları doğrula**,
**Yedek doğrula...**); solda **Sonuçlar (anonim)** tablosu + altında **Yenile**,
**Analiz**, **QC raporu**, **Dışa aktar...**; sağda **Çıktı** paneli.
**Kontrol edilecek:** pencere açılıyor, tüm metinler **Türkçe**.
**Başarısızsa:** terminaldeki hatayı bildirin.

---

## Test 2: Sonuç listesi anonim (~1 dk)

**Kontrol edilecek:**
- Sonuçlar tablosunda sütunlar: **Oturum, Katılımcı, Grup, Başlangıç, Durum,
  Deneme**.
- Katılımcı sütununda **yalnız anonim kod** (P001 / DEV01 gibi) — **hiçbir yerde
  ad-soyad yok** (KVKK).
- `Yenile`'ye basınca liste yeniden yükleniyor, kayıp/çökme yok.

**Başarısızsa:** ekran görüntüsü + açıklama bildirin.

---

## Test 3: Kontrol listesi (checklist) panelde (~1 dk)

**Adım:** **Kontrol listesi** butonuna basın.
**Beklenen:** Çıktı panelinde YEŞİL/KIRMIZI satırlar akar; işlem bitince
`[Kontrol listesi] bitti: ...` satırı görünür. Süre boyunca butonlar kilitli,
durum çubuğunda "Çalışıyor: Kontrol listesi".
**Kontrol edilecek:**
- Rapor panelde okunuyor (ayrı konsol gerekmiyor).
- `development` modunda bazı satırlar KIRMIZI/UYARI olabilir (kalibrasyon/offset
  yok) — bu **beklenen**; önemli olan **KIRMIZI'nın panelde net görünmesi**.
- İşlem sırasında panel **donmuyor** (pencere sürüklenebiliyor).

**Başarısızsa:** çıktı panelindeki metni bildirin.

---

## Test 4: Uyaranları doğrula (~1 dk)

**Adım:** **Uyaranları doğrula** butonuna basın.
**Beklenen:** `verify_stimuli` raporu çıktı paneline akar; bitişte çıkış kodu
satırı. Uyaran seti tamsa `tamam (0)`.
**Kontrol edilecek:** rapor görünüyor, panel donmuyor.

---

## Test 5: Analiz / QC / Dışa aktar (seçili oturum) (~2 dk)

**Adım:**
1. Sonuçlar tablosundan bir **satır seçin**.
2. **Analiz** → çıktı panelinde oturum ölçümleri (katılımcı kodu + modül
   özetleri).
3. **QC raporu** → çıktı panelinde kalite kontrol raporu.
4. **Dışa aktar...** → bir klasör seçin → `[Dışa aktarım ...] yazıldı:` ve
   `trials_flat.csv` yolu görünür; klasörde dosya oluşmuş olmalı.

**Kontrol edilecek:**
- Satır seçmeden Analiz/QC/Dışa aktar'a basınca "Önce listeden bir oturum
  seçin." uyarısı çıkıyor.
- Üç işlem de panel donmadan sonuç veriyor; metinler Türkçe, anonim.

**Başarısızsa:** hangi adımda ne olduğunu bildirin.

---

## Test 6: Yedek doğrula (~1 dk)

**Adım:** **Yedek doğrula...** → `backups/` altından bir `.sqlite` seçin.
**Beklenen:** yedek doğrulama raporu çıktı paneline akar (canlı DB ile
karşılaştırma dahil), bitişte çıkış kodu.
> `backups/` boşsa önce panelden bir oturum koşup kapatın (oturum sonunda yedek
> alınır) ya da bu testi atlayın.

---

## Test 7: Oturum başlat — deney ayrı süreçte (~2 dk)

**Adım:** **Oturum başlat** butonuna basın.
**Beklenen:**
- Çıktı panelinde `Oturum ayri surecte basladi (PID ...)`.
- **Ayrı bir deney penceresi** (PsychoPy) açılır; giriş diyaloğu gelir.
- **Panel açık ve kullanılabilir kalır** (deney ayrı süreçte, detached).
- Deneyi ESC ile veya girişten çıkarak kapatabilirsiniz; panel etkilenmez.

**Kontrol edilecek:**
- Deney **panelin süreci içinde değil**, ayrı pencerede açılıyor (§A10.1).
- Panel donmuyor, kapanmıyor.
- (İsterseniz) deneyi kapatıp panelden **Yenile** ile yeni oturumun listede
  belirdiğini görün.

**Başarısızsa:** panelin ve deney penceresinin davranışını bildirin.

---

## Kabul kriterleri

- [ ] Panel açılıyor, her buton ilgili işi tetikliyor (Test 1, 3–7)
- [ ] "Oturum başlat" deneyi ayrı süreç olarak açıyor, panel donmuyor (Test 7)
- [ ] Checklist KIRMIZI'yı panelde net gösteriyor (Test 3)
- [ ] Sonuç listesi anonim; hiçbir yerde ad yok (Test 2, 5)
- [ ] Operatöre gösterilen metinler Türkçe (tüm testler)
