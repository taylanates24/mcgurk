# Adım 12c Manuel Test — Operatör menüsü

Girişten sonra, tam ekran pencere açılmadan önce bir **oturum kurulum menüsü**
çıkıyor: konuşmacı, koşulacak modüller, alıştırma, çapraz dinleme. Menü
**önceden dolu** geliyor — hiçbir şeye dokunmadan Enter'a basmak Adım 8
oturumunun aynısını koşuyor.

**Ekran gerekir. Süre ~30 dk** (Test 5 ve 6 ses de ister).

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| `pytest` (yerel, PsychoPy'li) | **1009 passed, 60 skipped** |
| `pytest -m "not psychopy"` (PsychoPy'siz venv) | **966 passed, 59 skipped** |
| `ruff` + `mypy` | temiz — **her iki ortamda** (139 dosya) |
| Yeni dosyalar | `mcgurk/ui/setup_dialog.py`, `tests/mcgurk/test_ui_setup_dialog.py`, `test_ui_session_menu.py`, `test_db_speaker_history.py` |
| Yeni testler | 14 (menü çekirdeği) + 7 (menü akışı) + 7 (veritabanı geçmişi) + 1 (`--no-ask`) |

## Ön koşullar

```powershell
$PY = "C:\Users\tayla\miniconda3\envs\mcgurk\python.exe"
```

- [ ] Kulaklık takılı ve ses açık (Test 5–6 için).
- [ ] Test verisi karışmasın diye ayrı bir veritabanı kullanın:
      her komuta `--db data\test12c.sqlite` ekleyin (aşağıda ekli).

---

## Test 1: Menü çıkıyor ve önceden dolu (~4 dk)

**Komut:**
```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite --limit 2
```

Girişte: kod `T12C-1`, grup **Kontrol**, yaş 30. Giriş onaylanınca menü açılmalı.

**Kontrol edilecek:**
- [ ] Başlık **"McGurk / SSD - Oturum kurulumu"**.
- [ ] **Katılımcı** satırı `T12C-1` yazıyor ve **değiştirilemiyor** (gri).
- [ ] **Konuşmacı** açılır listesinde **sekiz** konuşmacı var, her birinin
      yanında `(0 oturum)` yazıyor; ilk sırada **Konuşmacı 1 — Kadın** (config'in
      seçtiği) duruyor.
- [ ] Altı modülün her biri için bir onay kutusu var, **hepsi işaretli**, ve
      yanlarında deneme sayısı yazıyor (McGurk 140, AVSR 135, TBW 130, Oddball
      300, Dikotik 30, GIN 30).
- [ ] **Alıştırma** ve **Çapraz dinleme kontrolü** işaretli.
- [ ] Bu ilk oturum olduğu için **"Önceki konuşmacısı"** satırı **yok**.

**Şimdi hiçbir şeye dokunmadan OK'a basın.** Kontrol listesi ekranı gelmeli,
sonra alıştırma. Birkaç deneme yapıp **ESC** ile çıkın (onaylayın).

**Başarısızsa:** menü hiç çıkmıyorsa `ask` bayrağı akışa bağlanmamış demektir.

---

## Test 2: Tek modül seçilince yalnız o koşuyor (~6 dk)

**Komut:**
```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite --new-session
```

Giriş: `T12C-2`, Kontrol, 30. Menüde:
1. **Konuşmacı**: listeden **Konuşmacı 2 — Erkek** seçin.
2. McGurk hariç **bütün modüllerin** işaretini kaldırın.
3. **Alıştırma** ve **Çapraz dinleme** işaretini kaldırın.
4. OK.

**Kontrol edilecek:**
- [ ] Kontrol listesi onayından sonra **doğrudan McGurk yönergesi** geliyor;
      alıştırma yok.
- [ ] Sunulan yüz/ses **konuşmacı 2** (Test 1'deki kadın değil, erkek).
- [ ] Birkaç deneme sonra ESC ile çıkın.

**Sonra veriye bakın:**
```powershell
& $PY -c "import sqlite3, json; con=sqlite3.connect('data/test12c.sqlite'); r=con.execute('select session_id, operator_notes, config_snapshot from sessions order by session_id desc limit 1').fetchone(); s=json.loads(r[2]); print('oturum', r[0]); print('not    :', r[1]); print('sıra   :', s['session']['module_order']); print('etkin  :', [k for k,v in s['modules'].items() if v['enabled']]); print('konuşmacı:', s['speaker_selection'])"
```

**Beklenen çıktı:**
```
oturum 2
not    : ui.session konuşmacı=2 iyi_kulak=right | seçim: konuşmacı=2 modüller=mcgurk
sıra   : ['mcgurk']
etkin  : ['mcgurk']
konuşmacı: {'strategy': 'fixed', 'fixed_id': 2}
```

**Kontrol edilecek:** Seçim hem **snapshot'ta** hem **operatör notunda**. Not,
panelin oturum listesinde ilk okunan yer olduğu için kısmi oturum orada da
görünüyor (§A12.7).

---

## Test 3: Farklı konuşmacı uyarısı (~4 dk)

Aynı katılımcı (`T12C-2`) daha önce **konuşmacı 2** ile ölçüldü.

**Komut:**
```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite --new-session
```

Giriş: yine `T12C-2`. Menüde:

**Kontrol edilecek:**
- [ ] **"Önceki konuşmacısı"** satırı **2** yazıyor.
- [ ] Konuşmacı listesinde `Konuşmacı 2 — Erkek` yanında artık **(1 oturum)**
      yazıyor; **"Konuşmacı başına oturum"** satırı `2: 1` diyor.

Şimdi **Konuşmacı 5 — Kadın** seçip OK'a basın.

- [ ] **Uyarı diyaloğu** çıkıyor: "Bu katılımcı daha önce konuşmacı 2 ile
      ölçüldü…".
- [ ] Varsayılan cevap **"Hayır, menüye dön"**. Onu seçin →
      **menüye dönüyor**, oturum başlamıyor.
- [ ] Menüde tekrar Konuşmacı 5 seçip bu kez **"Evet, bu konuşmacıyla devam et"**
      deyin → oturum başlıyor.
- [ ] Birkaç deneme sonra ESC.

**Sonra:**
```powershell
& $PY -c "import sqlite3; con=sqlite3.connect('data/test12c.sqlite'); print(con.execute('select operator_notes from sessions order by session_id desc limit 1').fetchone()[0])"
```
Notta `seçim: konuşmacı=5 …` yazmalı. `logs/` altındaki güncel log dosyasında da
`Katılımcı daha önce konuşmacı 2 ile ölçülmüştü` uyarısı bulunmalı.

**Başarısızsa:** uyarı hiç çıkmıyorsa katılımcı geçmişi okunmuyor demektir.

---

## Test 4: Devam eden oturumda menü çıkmıyor (~5 dk)

Test 3'teki oturum ESC ile yarıda kaldı. Aynı katılımcıyla tekrar başlatın:

```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite
```

Giriş: `T12C-2`.

**Kontrol edilecek:**
- [ ] "Kaldığı yerden devam?" soruluyor → **Devam et** deyin.
- [ ] **Menü ÇIKMIYOR** — doğrudan kontrol listesi ekranına geçiliyor.
- [ ] Koşan modül, yarım kalan oturumun modülü (konuşmacı 5'li seçim), yeni bir
      tasarım değil.
- [ ] ESC ile çıkın.

**Neden böyle:** yarım oturumun tasarımı kendi snapshot'ında; menü göstermek
onunla çelişebilecek bir seçim sunardı.

---

## Test 5: Menüyü atlamak — `--no-ask` (~4 dk, ses ister)

```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite --new-session --no-ask --modules dichotic --speaker 7 --no-practice --no-cross-hearing --limit 4
```

Giriş: `T12C-3`, Kontrol, 30.

**Kontrol edilecek:**
- [ ] **Menü çıkmıyor**, doğrudan kontrol listesine geçiliyor.
- [ ] Yalnız dikotik koşuyor, konuşmacı **7** (erkek).
- [ ] Dört deneme sonunda oturum kendiliğinden bitiyor (çıkış kodu **0**).

**Ayrıca:** aynı bayrakları `--no-ask` **olmadan** verin — menü çıkmalı ve
**bayraklardaki seçimle önceden dolu** gelmeli (konuşmacı 7 ilk sırada, yalnız
dikotik işaretli). Bu, bayrakların menüyü ezmediğini, doldurduğunu gösterir.

---

## Test 6: Yeni bir konuşmacı gerçekten sunuluyor (~4 dk, ses ister)

12a'nın hazırladığı yeni konuşmacılar ilk kez burada gerçek oturumda sunuluyor.

```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite --new-session --limit 3
```

Giriş: `T12C-4`. Menüde **Konuşmacı 6 — Kadın** ve yalnız **AVSR** seçin.

**Kontrol edilecek:**
- [ ] Video ve ses konuşmacı 6'ya ait, senkron görünüyor/duyuluyor.
- [ ] Ses seviyesi diğer konuşmacılarla benzer (12a'nın seviye eşitlemesi).
- [ ] Görüntü ile sesin patlaması **aynı anda** — gecikme hissi yok.

**Başarısızsa:** A/V kayması varsa konsolda hizalama uyarısı olup olmadığına
bakın ve bana iletin.

---

## Test 7: Menü iptali oturum başlatmıyor (~2 dk)

```powershell
& $PY -m mcgurk.ui --db data\test12c.sqlite --new-session
```

Giriş: `T12C-5`. Menü açılınca **Cancel / X** ile kapatın.

**Kontrol edilecek:**
- [ ] Program temiz çıkıyor, tam ekran pencere **hiç açılmıyor**.
- [ ] Veritabanında bu katılımcı için **oturum satırı yok**:

```powershell
& $PY -c "import sqlite3; con=sqlite3.connect('data/test12c.sqlite'); print(con.execute(\"select count(*) from sessions s join participants p on p.participant_id=s.participant_id where p.participant_code='T12C-5'\").fetchone()[0])"
```
Beklenen: `0`

---

## Temizlik

```powershell
Remove-Item data\test12c.sqlite*
```

(Gerçek veritabanı `data/mcgurk.sqlite` bu testlerden etkilenmedi.)

---

## Kabul kriterleri

- [ ] Menü girişten sonra çıkıyor, tam tasarım ve config'teki konuşmacı önceden
      seçili; onaylamak Adım 8 oturumunun aynısını koşuyor (Test 1)
- [ ] Sekiz konuşmacı etiketleriyle ve oturum sayılarıyla listeleniyor (Test 1, 3)
- [ ] Tek modül seçilince yalnız o koşuyor; seçim snapshot'a ve nota yazılıyor (Test 2)
- [ ] Konuşmacı 2 ve yeni bir konuşmacı (6, 7) gerçekten sunuluyor (Test 2, 5, 6)
- [ ] Farklı konuşmacı seçilince onay isteniyor; "hayır" menüye dönüyor (Test 3)
- [ ] Devam eden oturumda menü çıkmıyor (Test 4)
- [ ] `--no-ask` menüyü atlıyor; bayraklar `--no-ask` olmadan menüyü dolduruyor (Test 5)
- [ ] İptal oturum başlatmıyor (Test 7)

## Bu alt adımda bilerek yapılmayanlar

- **Kısmi oturumdan sonra "kaldığı yerden devam?" sorulması.** Kısmi bir oturum
  `completed` bittiği için resume teklifi zaten çıkmaz; §C12'nin bu kriteri
  Test 2'den sonra yeni bir oturum açarak doğrulanabilir (menü çıkar, devam
  teklifi çıkmaz).
- **Kısmi oturumun QC raporunda işaretlenmesi** ve **katılımcı düzeyinde analiz**
  12d'nin işi. Şimdilik kısmi oturum snapshot'ında ve operatör notunda görünüyor.
- **Menüde canlı toplam deneme sayısı yok.** `gui.DlgFromDict` alan değişince
  yeniden hesaplayan bir yapı sunmuyor; modül başına deneme sayısı onay
  kutusunun yanında yazıyor, toplam log'a yazılıyor.

## Sırada ne var

**12d** — katılımcı düzeyinde analiz (`participant_measures`), QC'de kısmi
oturum işareti, panelde "Katılımcı analizi" düğmesi ve `.exe`'nin yeniden
derlenmesi.
