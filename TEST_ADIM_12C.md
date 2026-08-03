# Adım 12c Manuel Test — Konuşmacı sekmesi + oturum modül menüsü

İki yer değişti:

1. **Operatör panelinde yeni bir "Konuşmacı" sekmesi** — sekiz konuşmacı
   **fotoğraflarıyla** listeleniyor, config'teki hangisiyse o **tikli** geliyor;
   seçip kaydedince `config/experiment.yaml`'a yazılıyor ve bundan sonraki
   oturumlar o yüzü kullanıyor.
2. **Oturum başında modül menüsü** — girişten sonra, tam ekran açılmadan önce
   koşulacak modüller onay kutularıyla soruluyor. Konuşmacı burada
   **değiştirilemiyor**, yalnız gösteriliyor: bir katılımcının bütün modülleri
   aynı yüzle ölçülmeli.

**Ekran gerekir. Süre ~30 dk** (Test 6 ve 7 ses de ister).

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| `pytest` (yerel, PsychoPy'li) | **1017 passed, 60 skipped** |
| `pytest -m "not psychopy"` (PsychoPy/PyQt6'sız venv) | **968 passed, 59 skipped** |
| `ruff` + `mypy` | temiz — **her iki ortamda** (139 dosya) |
| `verify_stimuli.py` | temiz; `8 konuşmacı küçük resmi yerinde` |
| Yeni/değişen | `mcgurk/config/edit.py` (konuşmacı yazma), `mcgurk/panel/{core,app}.py` (sekme), `mcgurk/ui/setup_dialog.py` (konuşmacı çıkarıldı), `stimuli/thumbnails/` |
| Yeni testler | 8 (config yazma) + 6 (panel sekmesi) + 9 (modül menüsü) + 6 (uyarı akışı) |

## Ön koşullar

```powershell
$PY = "C:\Users\tayla\miniconda3\envs\mcgurk\python.exe"
```

- [ ] Kulaklık takılı ve ses açık (Test 6–7 için).
- [ ] Test verisi karışmasın diye ayrı bir veritabanı: komutlara
      `--db data\test12c.sqlite` ekli.
- [ ] **Config'inizin yedeğini alın** — Test 1 gerçekten dosyayı değiştiriyor:

```powershell
Copy-Item config\experiment.yaml config\experiment.yaml.yedek
```

---

## Test 1: Konuşmacı sekmesi — fotoğraflar ve varsayılan tik (~5 dk)

**Komut:**
```powershell
& $PY -m mcgurk.panel
```

**Kontrol edilecek:**
- [ ] Üç sekme var: **Panel**, **Konuşmacı**, **Ayarlar**.
- [ ] "Konuşmacı" sekmesinde **sekiz** kutu, her birinde bir **yüz fotoğrafı**
      ve altında `Konuşmacı N — Kadın/Erkek  (M oturum)` yazan bir radyo düğmesi.
- [ ] Fotoğraflar kutuya sığıyor, bozulmuyor (en-boy oranı korunuyor).
- [ ] **Konuşmacı 1** tikli (config'teki `fixed_id`). Alt satırda
      `Şu anki konuşmacı: 1. Oturumlar bunu kullanır.` yazıyor.
- [ ] Cinsiyetler doğru: 2, 3, 4, 7 erkek; 1, 5, 6, 8 kadın.

Şimdi **Konuşmacı 5**'i seçip **Konuşmacıyı kaydet**'e basın.

- [ ] Çıktı panelinde `[Konuşmacı] kaydedildi: konuşmacı 5` satırı,
      durum çubuğunda `Konuşmacı kaydedildi - 5`.
- [ ] Alt satır `Şu anki konuşmacı: 5` oldu.

**Dosyaya bakın:**
```powershell
Select-String -Path config\experiment.yaml -Pattern "fixed_id|speaker_id: " | Select-Object -First 6
```
Beklenen: `fixed_id: 5` ve dört modülde `speaker_id: 5`.

```powershell
Select-String -Path config\experiment.yaml -Pattern "reps is PER CELL" | Measure-Object
```
Beklenen: **1** — yorumlar korunmuş.

**Başarısızsa:** fotoğraf yerine "(resim yok)" görüyorsanız hazırlanmış set
eksiktir: `python tools/prepare_stimuli.py --force`.

---

## Test 2: Modül menüsü — konuşmacı gösteriliyor, sorulmuyor (~4 dk)

**Komut:**
```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite --limit 2
```

Girişte: kod `T12C-1`, grup **Kontrol**, yaş 30.

**Kontrol edilecek:**
- [ ] Menü başlığı **"McGurk / SSD - Oturum kurulumu"**.
- [ ] **Katılımcı** = `T12C-1` ve **Konuşmacı (panelden)** = `Konuşmacı 5 — Kadın`
      satırları var ve **ikisi de değiştirilemiyor** (gri).
- [ ] Altı modülün her biri için onay kutusu, **hepsi işaretli**, yanlarında
      deneme sayısı (McGurk 140, AVSR 135, TBW 130, Oddball 300, Dikotik 30,
      GIN 30).
- [ ] **Alıştırma** ve **Çapraz dinleme kontrolü** işaretli.

**Hiçbir şeye dokunmadan OK'a basın** → kontrol listesi ekranı, sonra alıştırma.
Birkaç deneme yapıp **ESC** ile çıkın (onaylayın).

- [ ] Sunulan yüz **konuşmacı 5** (Test 1'de seçtiğiniz).

---

## Test 3: Tek modül seçilince yalnız o koşuyor (~5 dk)

```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite --new-session
```

Giriş: `T12C-2`, Kontrol, 30. Menüde McGurk hariç bütün modüllerin, ayrıca
**Alıştırma** ve **Çapraz dinleme**'nin işaretini kaldırın. OK.

**Kontrol edilecek:**
- [ ] Kontrol listesinden sonra **doğrudan McGurk yönergesi**; alıştırma yok.
- [ ] Birkaç deneme sonra ESC.

**Sonra veriye bakın:**
```powershell
& $PY -c "import sqlite3, json; con=sqlite3.connect('data/test12c.sqlite'); r=con.execute('select session_id, operator_notes, config_snapshot from sessions order by session_id desc limit 1').fetchone(); s=json.loads(r[2]); print('oturum', r[0]); print('not    :', r[1]); print('sıra   :', s['session']['module_order']); print('etkin  :', [k for k,v in s['modules'].items() if v['enabled']]); print('konuşmacı:', s['speaker_selection'])"
```

**Beklenen çıktı:**
```
oturum 2
not    : ui.session konuşmacı=5 iyi_kulak=right | seçim: konuşmacı=(config) modüller=mcgurk
sıra   : ['mcgurk']
etkin  : ['mcgurk']
konuşmacı: {'strategy': 'fixed', 'fixed_id': 5}
```

**Kontrol edilecek:** Seçim hem **snapshot'ta** hem **operatör notunda**.
`konuşmacı=(config)` doğru: menü konuşmacıyı ezmedi, config'inki kullanıldı.

---

## Test 4: Farklı konuşmacı uyarısı (~4 dk)

`T12C-2` konuşmacı 5 ile ölçüldü. Şimdi panelden **konuşmacı 2**'ye geçin
(Test 1'deki gibi), sonra aynı katılımcıyla yeni bir oturum açın:

```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite --new-session
```

Giriş: `T12C-2`.

**Kontrol edilecek:**
- [ ] **Uyarı diyaloğu** çıkıyor: "Bu katılımcı daha önce konuşmacı 5 ile
      ölçüldü; config şu an konuşmacı 2 diyor…" ve panel sekmesini işaret ediyor.
- [ ] Varsayılan cevap **"Hayır, iptal et"**. Onu seçin → **oturum başlamıyor**,
      modül menüsü bile açılmıyor.
- [ ] Tekrar başlatıp bu kez **"Evet, bu konuşmacıyla devam et"** deyin → modül
      menüsü açılıyor. ESC ile çıkın.
- [ ] `logs/` altındaki güncel dosyada
      `Katılımcı daha önce konuşmacı 5 ile ölçülmüştü` uyarısı var.

**Neden iptal:** konuşmacı panelden değiştiriliyor; oturumun ortasında
düzeltilecek bir şey yok.

---

## Test 5: Devam eden oturumda menü çıkmıyor (~4 dk)

Test 4'teki oturum yarıda kaldı. Aynı katılımcıyla tekrar başlatın:

```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite
```

Giriş: `T12C-2` → "Kaldığı yerden devam?" → **Devam et**.

**Kontrol edilecek:**
- [ ] **Menü ÇIKMIYOR**, doğrudan kontrol listesine geçiliyor.
- [ ] Koşan modül, yarım kalan oturumun modülü.
- [ ] ESC ile çıkın.

---

## Ekran/ses gerektiren testler

## Test 6: `--no-ask` ve bayraklar (~4 dk, ses ister)

```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite --new-session --no-ask --modules dichotic --no-practice --no-cross-hearing --limit 4
```

Giriş: `T12C-3`, Kontrol, 30.

**Kontrol edilecek:**
- [ ] **Menü çıkmıyor**, doğrudan kontrol listesine geçiliyor.
- [ ] Yalnız dikotik koşuyor, dört deneme sonunda oturum **kendiliğinden**
      bitiyor (çıkış kodu 0).

**Ayrıca:** aynı bayrakları `--no-ask` **olmadan** verin — menü çıkmalı ve
**yalnız dikotik işaretli** gelmeli.

---

## Test 7: Yeni bir konuşmacı gerçekten sunuluyor (~4 dk, ses ister)

Panelden **konuşmacı 6**'yı seçip kaydedin, sonra:

```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite --new-session --limit 3
```

Giriş: `T12C-4`. Menüde yalnız **AVSR** bırakın.

**Kontrol edilecek:**
- [ ] Menüde `Konuşmacı (panelden)` satırı **Konuşmacı 6 — Kadın** diyor.
- [ ] Video ve ses konuşmacı 6'ya ait, senkron görünüyor/duyuluyor.
- [ ] Ses seviyesi diğer konuşmacılarla benzer.

---

## Test 8: Menü iptali oturum başlatmıyor (~2 dk)

```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite --new-session
```

Giriş: `T12C-5`. Menü açılınca **Cancel / X** ile kapatın.

**Kontrol edilecek:**
- [ ] Program temiz çıkıyor, tam ekran pencere **hiç açılmıyor**.
- [ ] Veritabanında bu katılımcı için oturum yok:

```powershell
& $PY -c "import sqlite3; con=sqlite3.connect('data/test12c.sqlite'); print(con.execute(\"select count(*) from sessions s join participants p on p.participant_id=s.participant_id where p.participant_code='T12C-5'\").fetchone()[0])"
```
Beklenen: `0`

---

## Temizlik

```powershell
Remove-Item data\test12c.sqlite*
Move-Item -Force config\experiment.yaml.yedek config\experiment.yaml
```

(İkincisi config'i test öncesi hâline — konuşmacı 1 — döndürür.)

---

## Kabul kriterleri

- [ ] Panelde "Konuşmacı" sekmesi sekiz konuşmacıyı fotoğrafla listeliyor,
      varsayılan tikli (Test 1)
- [ ] Kaydetmek config'e yazıyor, yorumlar korunuyor (Test 1)
- [ ] Oturum menüsü modülleri soruyor; konuşmacı gösteriliyor ama
      değiştirilemiyor (Test 2)
- [ ] Tek modül seçilince yalnız o koşuyor; seçim snapshot'a ve nota yazılıyor
      (Test 3)
- [ ] Farklı konuşmacıda uyarı çıkıyor; "hayır" oturumu başlatmıyor (Test 4)
- [ ] Devam eden oturumda menü çıkmıyor (Test 5)
- [ ] `--no-ask` menüyü atlıyor; bayraklar menüyü dolduruyor (Test 6)
- [ ] Konuşmacı 5 ve 6 gerçekten sunuluyor (Test 2, 7)
- [ ] İptal oturum başlatmıyor (Test 8)

## Bilerek yapılmayanlar / bilinen sınırlar

- **Fotoğraf karesi 0.15 s'den alınıyor** (`stimulus_prep.thumbnail.time_s`).
  Konuşmacı 3 ve 7 kaydın başında ağzı hafif açık başlıyor; başka bir an
  isterseniz config'ten değiştirip `prepare_stimuli.py --force` koşmak yeterli,
  kod değişmez.
- **Menüde canlı toplam deneme sayısı yok** — `gui.DlgFromDict` alan değişince
  yeniden hesaplayan bir yapı sunmuyor; modül başına sayı kutunun yanında.
- **Kontrol listesi menüden önce çıkıyor**, dolayısıyla seçilen alt kümeyi
  bilmiyor: kurulumu doğruluyor, oturumu değil.
- **Kısmi oturumun QC'de işaretlenmesi ve katılımcı düzeyinde analiz 12d.**
- **Windows'ta seyrek bir ölümcül pytest çökmesi** görüldü (dört tam koşuda bir,
  test hatası değil). CI Linux'ta ve orada hiç görülmedi.

## Sırada ne var

**12d** — katılımcı düzeyinde analiz (`participant_measures`), QC'de kısmi
oturum işareti, panelde "Katılımcı analizi" düğmesi ve `.exe`'nin yeniden
derlenmesi (`stimuli/` artık 186 MB, taşıma adımı uzuyor).
