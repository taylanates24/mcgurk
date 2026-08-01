# Adım 10c-i Manuel Test — Donmuş-farkında yol katmanı + `--run` dağıtıcısı

Paketlemenin (10c-ii) kod temeli: tek yol-çözümleme otoritesi (`mcgurk/paths.py`),
donmuş exe için `--run` altkomut dağıtıcısı (`mcgurk/app_entry.py`) ve giriş
noktalarının yazılabilir köke bağlanması. **Kaynaktan davranış değişmez.**

**Ekran gerekmez. Toplam süre ~3 dakika.**

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| Yerel testler | **889 test yeşil**, `ruff` + `mypy` temiz |
| CI taklidi (PySide6'sız venv) | ruff + mypy + pytest **yeşil** (854 passed, 58 skipped) — CI geçecek |
| Yeni dosyalar | `mcgurk/paths.py`, `mcgurk/app_entry.py`, `test_paths.py`, `test_app_entry.py` |
| Bağlanan giriş noktaları | `ui/__main__`, `checklist`, `panel/__main__`, `tools/verify_stimuli` → `paths.detect_runtime()` |

## Ön koşullar

```powershell
$PY = "C:\Users\tayla\miniconda3\envs\mcgurk\python.exe"
```

---

## Test 1: Otomatik testler yeşil (~1 dk)

```powershell
& $PY -m pytest tests/mcgurk/test_paths.py tests/mcgurk/test_app_entry.py tests/mcgurk/test_package_boundaries.py -q
```
**Beklenen:** son satırda `... passed` (26 skip beklenen). Kırmızı yok.

---

## Test 2: `--run` dağıtıcısı doğrudan çağrıyla özdeş (~1 dk)

Donmuş exe'nin kullanacağı dağıtıcı, kaynaktan da aynı işi yapmalı:

```powershell
& $PY -m mcgurk.app_entry --run checklist --no-hardware
```
**Beklenen:** kontrol listesi raporu (development modunda UYARI satırları normal).

```powershell
& $PY -m mcgurk.checklist --no-hardware
```
**Kontrol edilecek:** iki komutun çıktısı ve çıkış kodu **aynı** — dağıtıcı
checklist'i birebir aynı çalıştırıyor.

---

## Test 3: Kaynaktan regresyon yok (~1 dk)

```powershell
& $PY -m mcgurk.ui --help
```
**Beklenen:** kullanım (usage) metni, hata yok — config/yol çözümlemesi kaynaktan
sorunsuz.

Yolların hâlâ proje köküne çözüldüğünü doğrulayın (yanlışlıkla başka yere
taşınmadı):
```powershell
@'
from mcgurk.paths import detect_runtime, ensure_writable_config
rt = detect_runtime()
print("frozen:", rt.frozen)
print("resource == writable:", rt.resource_root == rt.writable_root)
print("config:", ensure_writable_config(rt))
'@ | & $PY -
```
**Beklenen:**
```
frozen: False
resource == writable: True
config: ...\mcgurk\config\experiment.yaml
```
**Kontrol edilecek:** kaynaktan iki kök özdeş ve config repo'daki dosya —
davranış değişmemiş.

---

## Ekran/ses gerektiren testler

Yok. Paketlenmiş `.exe`'nin çift-tık/oturum/yazılabilir-yol testleri **10c-ii**'de
(`TEST_ADIM_10C.md`, Windows + ekran + ses).

## Kabul kriterleri

- [ ] Otomatik testler yeşil (Test 1) — `paths` + `app_entry` + sınır testi
- [ ] `--run` dağıtıcısı doğrudan çağrıyla özdeş (Test 2)
- [ ] Kaynaktan hiçbir davranış değişmiyor (Test 3)
- [ ] `ruff` + `mypy` temiz; `pytest -m "not psychopy"` yeşil (yerel + PySide6'sız CI taklidi)
