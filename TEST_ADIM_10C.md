# Adım 10c-ii Manuel Test — PyInstaller ile Windows `.exe`

Operatör panelini + deneyi tek çift-tıklanan Windows uygulamasına paketler.
**Bu adım doğası gereği makine-yinelemeli** (§D10: PyInstaller + PsychoPy kötü
şöhretli) — ilk derleme büyük olasılıkla birkaç düzeltme ister; çıkan hataları
bana iletin, `packaging/mcgurk.spec` üzerinden düzeltelim.

**Windows + ekran + ses gerekir.** Bu test aynı zamanda paketlenmiş panelin
davranışını (Adım 10b) da doğrular.

## Ön koşullar

- [ ] Windows (gerçek makine, WSL değil).
- [ ] `requirements.txt`'in tamamı kurulu mcgurk conda ortamı + PyInstaller:

```powershell
$PY = "C:\Users\tayla\miniconda3\envs\mcgurk\python.exe"
& $PY -m pip install -r requirements-dev.txt
```
- [ ] `stimuli/` seti hazır (proje kökünde; `python tools/verify_stimuli.py` yeşil).

---

## Test 1: `.exe` derleniyor

**Komut:**
```powershell
& $PY tools\build_exe.py --clean
```
**Beklenen çıktı (son satırlar):**
```
Derleme tamam.
  Uygulama : ...\dist\McGurkSSD\McGurkSSD.exe
```
**Kontrol edilecek:** `dist\McGurkSSD\McGurkSSD.exe` oluştu.
**Başarısızsa:** PyInstaller çıktısındaki hata (eksik import/veri dosyası) satırlarını
bana iletin — `packaging/mcgurk.spec`'te `hiddenimports`/`datas`'a ekleyerek
çözeriz (`packaging/README.md` → "Bilinen sorunlar").

---

## Test 2: Uyaranları yerleştir + panel çift-tıkla açılıyor

**Adım:**
1. `stimuli/` klasörünü uygulamanın yanına kopyalayın:
   `dist\McGurkSSD\stimuli\`
2. `dist\McGurkSSD\McGurkSSD.exe`'ye **çift tıklayın**.

**Beklenen:** Operatör paneli penceresi açılır (başlıkta "McGurk / SSD Operatör
Paneli"). `console=True` derlendiği için bir de terminal penceresi açılır — bu
**bilerek** (başlangıç hatalarını görmek için); v1.0.0'da pencereli yapılabilir.
**Kontrol edilecek:** panel açılıyor, çökmüyor. Terminalde traceback yok.
**Başarısızsa:** terminal penceresindeki hata metnini iletin.

---

## Test 3: Panel butonları (Adım 10b, paketlenmiş) (~2 dk)

**Kontrol edilecek:**
- **Kontrol listesi** → çıktı panelinde YEŞİL/KIRMIZI rapor (development'ta UYARI
  satırları normal). Panel donmuyor.
- **Uyaranları doğrula** → `verify_stimuli` raporu akıyor.
- **Sonuçlar** tablosu **anonim** (kod/grup/tarih/durum/deneme) — ad-soyad yok.
- Metinlerin tamamı Türkçe.

---

## Test 4: "Oturum başlat" — deney ayrı süreçte, exe içinde PsychoPy

**Adım:** **Oturum başlat** butonuna basın.
**Beklenen:**
- Çıktı panelinde `Oturum ayri surecte basladi (PID ...)`.
- **Ayrı bir PsychoPy penceresi/diyaloğu** açılır (aynı exe, `--run session`).
- Panel açık ve kullanılabilir kalır.
- Girişi doldurup birkaç deneme yapın, sonra ESC ile çıkın (veya kısa tutun).

**Kontrol edilecek:**
- Deney **exe içinde** çalışıyor (ayrı Python kurulumu yok).
- Panel donmuyor/kapanmıyor (deney detached).
**Başarısızsa:** terminal + deney penceresi davranışını iletin.

---

## Test 5: Yazmalar yazılabilir konuma gidiyor (`_MEIPASS`'a değil)

**Adım:** Test 4'teki kısa oturumdan sonra `dist\McGurkSSD\` klasörüne bakın.
**Beklenen — exe'nin yanında oluşmuş olmalı:**
```
dist\McGurkSSD\
├── config\experiment.yaml    (ilk çalıştırmada kopyalandı)
├── data\mcgurk.sqlite        (oturum verisi)
├── logs\                     (oturum logu)
└── backups\                  (oturum sonu yedeği — oturum tamamlan/kesilince)
```
**Kontrol edilecek:**
- Veritabanı/log/yedek **`dist\McGurkSSD\` altında** — geçici `_MEIPXXXXXX`
  klasöründe **değil**.
- `config\experiment.yaml` düzenlenip panel yeniden açılınca **eziLMİYOR**
  (düzenleme kalıcı).

---

## Test 6: Kısa oturum + dışa aktarım uçtan uca

**Adım:**
1. Panelde **Sonuçlar**'dan Test 4'teki oturumu seçin → **Dışa aktar...** → bir
   klasör seçin.
2. **Analiz** ve **QC raporu** butonlarını deneyin.

**Beklenen:** seçilen klasörde `trials_flat.csv` oluşur; Analiz/QC çıktı
panelinde okunur metin verir.
**Kontrol edilecek:** uçtan uca (oturum → veri → export/analiz) paketlenmiş app'te
çalışıyor.

---

## Test 7: Kaynaktan regresyon yok

Paketleme kaynaktan çalıştırmayı bozmamalı:
```powershell
& $PY -m mcgurk.panel      # panel açılır
& $PY main.py --help       # deney giriş noktası
```
**Kontrol edilecek:** ikisi de eskisi gibi çalışıyor.

---

## Kabul kriterleri (§C10 10c)

- [ ] Windows'ta `.exe` derleniyor (Test 1)
- [ ] Çift-tıkla panel açılıyor; "Oturum başlat" deneyi açıyor, PsychoPy exe içinde çalışıyor (Test 2, 4)
- [ ] Yazmalar (DB, yedek, log, export) yazılabilir konuma gidiyor; salt-okunur `_MEIPASS`'a değil (Test 5, 6)
- [ ] Kaynaktan çalıştırma hâlâ çalışıyor — regresyon yok (Test 7)
- [ ] Kısa oturum + export paketlenmiş app üzerinde uçtan uca çalışıyor (Test 4, 6)

## Not

Bu test geçince **Adım 10 biter**. Sonrası: **prova oturumu** (bu paketlenmiş app
üzerinde, `TEST_ADIM_9C.md`), bug düzeltme, ardından `develop → master` merge +
`git tag v1.0.0` (kullanıcı onayıyla) = **dağıtılabilir Windows uygulaması**.
