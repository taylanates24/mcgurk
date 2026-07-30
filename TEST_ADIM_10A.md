# Adım 10a Manuel Test — Panel çekirdeği (GUI'siz)

Operatör panelinin **PySide6'sız ve PsychoPy'siz** çekirdeği: subprocess komut
kurucuları, salt-okunur/anonim sonuç listeleme, analiz sarmalayıcıları ve
kaynak/donmuş yol çözümleme. Qt penceresi (10b) ve `.exe` (10c) bunun üzerine
oturacak.

**Ekran/ses gerekmez. Toplam süre ~3 dakika.**

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| Otomatik testler | **864 test yeşil** (CI alt kümesi; 25 yeni panel testi + sınır testi güncellendi), `ruff` + `mypy` temiz |
| Yeni paket | `mcgurk/panel/` — `core.py` (çekirdek mantık) + `__init__.py` (kamu API) |
| Sınır | `mcgurk.panel.core` PsychoPy import etmiyor (`test_package_boundaries.py` + `PURE_LAYERS`) |
| Yeni testler | `test_panel_core.py`: komut kurucular (kaynak + donmuş-taklit), yol çözümleme, salt-okunur/anonim tarama, analiz sarmalayıcıları |

## Ön koşullar

- [ ] Komutlar **PowerShell**'de çalıştırılıyor.
- [ ] Doğru Python yorumlayıcısı. **Bu oturumda `python` base ortama düşebiliyor**
  (conda aktivasyonu terminal yeniden açılınca etkin olur — bkz. progress notları).
  Bu yüzden aşağıdaki tüm komutlar mcgurk ortamının **tam yolunu** kullanır.
  Önce bir değişkene atayın:

```powershell
$PY = "C:\Users\tayla\miniconda3\envs\mcgurk\python.exe"
```

Doğru olduğunu teyit edin (Python **3.10.20** yazmalı):
```powershell
& $PY -c "import sys; print(sys.version)"
```

> Conda ortamını aktive ettiyseniz (`conda activate mcgurk`) düz `python` de
> çalışır; o hâlde `& $PY` yerine `python` yazabilirsiniz.

---

## Test 1: Otomatik testler yeşil (~1 dk)

**Komut:**
```powershell
& $PY -m pytest tests/mcgurk/test_panel_core.py tests/mcgurk/test_package_boundaries.py -q
```
**Beklenen çıktı:** son satırda `68 passed, 26 skipped` (26 skip,
`engine/`/`ui/`/`modules/` sunum katmanlarının atlanması — beklenen).
**Kontrol edilecek:** kırmızı yok.
**Başarısızsa:** çıktıyı bildirin.

---

## Test 2: Komut kurucular + anonim liste (~1 dk)

Panelin deneyi/checklist'i/araçları hangi komutla başlatacağını ve sonuç
listesinin anonim olduğunu tek seferde doğrulayın. Aşağıdaki bloğu **olduğu gibi**
PowerShell'e yapıştırın (kod stdin'den okunur, satır-içi tırnak sorunu olmaz):

```powershell
@'
from mcgurk.panel import core
rt = core.detect_runtime()
print("frozen:", rt.frozen)
print("oturum :", core.session_command(rt, limit=8))
print("kontrol:", core.checklist_command(rt, no_hardware=True))
print("uyaran :", core.verify_stimuli_command(rt, quick=True))
try:
    rows = core.list_sessions("data/mcgurk.sqlite")
    print("oturum sayisi:", len(rows))
    for r in rows:
        print(" ", r.session_id, r.participant_code, r.group_code, r.status, r.n_trials)
except core.PanelError as e:
    print("DB yok (sorun degil):", e)
'@ | & $PY -
```
**Beklenen çıktı (yollar sizin makinenizdeki mutlak yollar olur):**
```
frozen: False
oturum : [...'python.exe', '-m', 'mcgurk.ui', '--limit', '8']
kontrol: [...'python.exe', '-m', 'mcgurk.checklist', '--no-hardware']
uyaran : [...'python.exe', '...\tools\verify_stimuli.py', '--quick']
oturum sayisi: 1
   1 DEV01 CTRL completed 12
```
**Kontrol edilecek:**
- `frozen: False` (kaynaktan çalışıyoruz).
- Oturum/kontrol `-m mcgurk.ui` / `-m mcgurk.checklist`; uyaran doğrulama
  `tools/verify_stimuli.py` script yolunu içeriyor.
- Liste satırlarında **yalnız anonim kod** (DEV01 gibi), grup, durum, deneme
  sayısı — **hiçbir yerde ad-soyad yok** (KVKK, §A10.4). DB boşsa
  `oturum sayisi: 0` görürsünüz, sorun değil.

**Başarısızsa:** çıktıyı bildirin.

---

## Test 3: Tarama salt-okunur (yazma reddediliyor) (~1 dk)

> `data/mcgurk.sqlite` yoksa bu testi atlayın — otomatik test aynı şeyi geçici
> bir DB ile zaten doğruluyor.

```powershell
@'
from mcgurk.panel import core
c = core.open_readonly("data/mcgurk.sqlite")
try:
    c.execute("CREATE TABLE zzz (a)")
    print("HATA: yazma engellenmedi!")
except Exception as e:
    print("Beklenen ret:", type(e).__name__, "-", e)
'@ | & $PY -
```
**Beklenen çıktı:**
```
Beklenen ret: OperationalError - attempt to write a readonly database
```
**Kontrol edilecek:** yazma girişimi reddediliyor (§A10.5). "HATA: yazma
engellenmedi!" **görünmemeli**.

**Başarısızsa:** çıktıyı bildirin.

---

## Ekran/ses gerektiren testler

Yok — 10a tamamen GUI'siz ve donanımsız. Panel penceresi 10b'de, `.exe` 10c'de
test edilecek.

## Kabul kriterleri

- [ ] Komut kurucular doğru argümanı üretiyor (kaynaktan ve donmuş-taklit halde) — Test 1 (otomatik) + Test 2 (elle)
- [ ] Oturum/katılımcı listesi anonim, salt-okunur — Test 1 (otomatik) + Test 2/3 (elle)
- [ ] Yol çözümleme kaynaktan doğru; donmuş dal `sys.frozen`/`_MEIPASS` taklidiyle test — Test 1 (otomatik)
- [ ] `mcgurk.panel.core` PsychoPy import etmiyor — Test 1 (sınır testi)
- [ ] `ruff` + `mypy` temiz; `pytest -m "not psychopy"` yeşil
