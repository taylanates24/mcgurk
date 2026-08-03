# Adım 12b Manuel Test — Seçim çekirdeği + komut satırı

Oturuma özel **konuşmacı** ve **modül** seçimi artık mümkün. Bu alt adımda menü
**yok** (o 12c); seçim komut satırından geliyor ve karar mantığı GUI'den ayrı,
CI-testli bir çekirdekte (`mcgurk/config/selection.py`).

**İlk beş test ekran gerektirmez.** Son test ekran + ses ister (~5 dk).

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| `pytest -m "not psychopy"` | **978 passed, 26 skipped** (25 yeni test) |
| `ruff` + `mypy` | temiz (135 dosya) |
| Yeni dosyalar | `mcgurk/config/selection.py`, `tests/mcgurk/test_config_selection.py`, `tests/mcgurk/test_ui_entry_selection.py` |

## Ön koşullar

```powershell
$PY = "C:\Users\tayla\miniconda3\envs\mcgurk\python.exe"
```

**Kavram — seçim nereye yazılıyor?** Seçim config'e *uygulanıyor* (§A12.1):
seçilmeyen modüller `enabled: false`, `session.module_order` kısaltılıyor,
konuşmacı sabitleniyor. Oturum bu türetilmiş tasarımla başlıyor, dolayısıyla
`sessions.config_snapshot`'a yazılan da o. Devam (resume), analiz ve QC zaten
snapshot'ı okuduğu için hiçbiri "seçim" diye bir şey öğrenmek zorunda değil.

---

## Test 1: Varsayılan davranış değişmedi (~1 dk)

En önemli test bu: bayraksız koşu Adım 8 oturumunun **aynısı** olmalı.

**Komut:**
```powershell
& $PY -c "from mcgurk.ui.__main__ import build_parser, _selection_from; from mcgurk.config.loader import load_config; c=load_config(check_filesystem=False); print(_selection_from(build_parser().parse_args([]), c))"
```

**Beklenen çıktı:**
```
None
```

**Kontrol edilecek:** `None` = "operatör hiçbir şey seçmedi" = config'in tasarımı
olduğu gibi koşar. Bayraklardan biri bile verilmezse hiçbir şey değişmiyor.

---

## Test 2: Modül alt kümesi yalnız seçileni sayıyor (~1 dk)

**Komut:**
```powershell
& $PY -c "from mcgurk.config.loader import load_config; from mcgurk.config.selection import SessionSelection, apply; c=load_config(check_filesystem=False); a=apply(c, SessionSelection(modules=('mcgurk','dichotic'), speaker_id=5)); print('modüller:', a.enabled_modules()); print('sıra    :', a.session.module_order); print('sayılar :', a.trial_counts()); print('toplam  :', sum(a.trial_counts().values()))"
```

**Beklenen çıktı:**
```
modüller: ['mcgurk', 'dichotic']
sıra    : ['practice', 'mcgurk', 'dichotic']
sayılar : {'practice': 12, 'mcgurk': 140, 'dichotic': 30, 'cross_hearing': 20}
toplam  : 202
```

**Kontrol edilecek:** Tam tasarım 797 deneme; bu alt küme **202**. Koşmayan
modüller sayıya hiç girmiyor — "koşmayan modül sonuçta yoktur" kuralı burada da
kendiliğinden işliyor.

**Sıra config'ten gelir.** `--modules dichotic,mcgurk` yazsanız da sıra yine
`practice, mcgurk, dichotic` olur: operatör hangi modüllerin koşacağını seçer,
hangi sırada koşacağını değil (modül sırası tasarımın parçası, §A.9).

---

## Test 3: Seçilen konuşmacı her okunacak yere yazılıyor (~1 dk)

**Komut:**
```powershell
& $PY -c "from mcgurk.config.loader import load_config; from mcgurk.config.selection import SessionSelection, apply; c=load_config(check_filesystem=False); a=apply(c, SessionSelection(modules=('mcgurk',), speaker_id=5)); print('strateji:', a.speaker_selection.strategy, a.speaker_selection.fixed_id); print('modüller:', a.modules.mcgurk.speaker_id, a.modules.avsr.speaker_id, a.modules.tbw.speaker_id, a.modules.dichotic.speaker_id); print('gerekli :', a.required_speaker_ids())"
```

**Beklenen çıktı:**
```
strateji: fixed 5
modüller: 5 5 5 5
gerekli : [5]
```

**Kontrol edilecek:** Konuşmacı üç ayrı yerde tutarlı. Oturum akışı ayrı bir yol
kullanmıyor — `select_speaker` artık bu sabitlenmiş değeri geri okuyor.

---

## Test 4: Hatalar katılımcı oturmadan yakalanıyor (~2 dk)

**Komut:**
```powershell
& $PY -m mcgurk.ui --modules dikotik
& $PY -m mcgurk.ui --speaker 99
& $PY -m mcgurk.ui --modules " "
```

**Beklenen çıktı (sırayla, üçü de çıkış kodu 1):**
```
HATA: Bilinmeyen modül: dikotik. Seçilebilecekler: avsr, dichotic, gin, mcgurk, oddball, tbw
HATA: Hazır sette olmayan konuşmacı: 99. Hazır olanlar: 1, 2, 3, 4, 5, 6, 7, 8
HATA: Hiç ölçüm modülü seçilmedi. Yalnız alıştırma ve çapraz dinleme koşan bir oturum veri üretmez.
```

**Kontrol edilecek:** Üçü de **giriş diyaloğu açılmadan** hata veriyor. Yanlış
yazılmış bir modül adının katılımcı ekranda beklerken keşfedilmemesi gerekiyor.

**Başarısızsa:** giriş diyaloğu açılıyorsa doğrulama yanlış yere konmuş demektir.

---

## Test 5: Türetilen tasarım snapshot turundan geçiyor (~1 dk)

§A12.1'in dayandığı şey bu: alt küme uygulanmış config, şemanın hâlâ kabul
ettiği bir config olmalı — yoksa **denemeler toplandıktan sonra** devam
ettirilirken patlardı.

**Komut:**
```powershell
& $PY -c "import json; from mcgurk.config.loader import load_config, config_from_snapshot; from mcgurk.config.selection import SessionSelection, apply; c=load_config(check_filesystem=False); a=apply(c, SessionSelection(modules=('gin',), speaker_id=2, practice=False, cross_hearing=False)); r=config_from_snapshot(json.dumps(a.model_dump(mode='json'), default=str)); print('geri okundu:', r.enabled_modules(), r.trial_counts())"
```

**Beklenen çıktı:**
```
geri okundu: ['gin'] {'gin': 30}
```

**Kontrol edilecek:** Tek modüllü, alıştırmasız, çapraz dinlemesiz bir tasarım
bile snapshot'tan yeniden kurulabiliyor.

---

## Ekran/ses gerektiren test

## Test 6: Alt küme gerçekten koşuyor (~5 dk)

**Komut:**
```powershell
& $PY -m mcgurk.ui --modules dichotic --speaker 5 --no-practice --no-cross-hearing --limit 4
```

**Yapılacaklar:**
1. Girişte bir test kodu verin (ör. `T12B`), grup **CTRL**, yaş 30.
2. Kontrol listesi ekranını onaylayın.
3. Dört dikotik deneme yanıtlayın.

**Kontrol edilecek:**
- [ ] **Yalnız dikotik** koşuyor — McGurk/AVSR/TBW/oddball/GIN yönergesi hiç
      görünmüyor, alıştırma ve çapraz dinleme de yok.
- [ ] Konsolda `Oturum seçimi: konuşmacı=5 modüller=dichotic` satırı var.
- [ ] Oturum `completed` bitiyor (çıkış kodu **0**).

**Sonra — veriye yazılanı doğrulayın:**
```powershell
& $PY -c "import sqlite3, json; con=sqlite3.connect('data/mcgurk.sqlite'); r=con.execute('select session_id, config_snapshot from sessions order by session_id desc limit 1').fetchone(); s=json.loads(r[1]); print('oturum', r[0]); print('sıra   :', s['session']['module_order']); print('etkin  :', [k for k,v in s['modules'].items() if v['enabled']]); print('konuşmacı:', s['speaker_selection']); print('çapraz :', s['cross_hearing_check']['enabled'])"
```

**Beklenen çıktı:**
```
oturum <N>
sıra   : ['dichotic']
etkin  : ['dichotic']
konuşmacı: {'strategy': 'fixed', 'fixed_id': 5}
çapraz : False
```

**Kontrol edilecek:** Seçim **snapshot'ta** duruyor. Bu, 12d'nin "kısmi oturum"
işaretlemesinin ve katılımcı düzeyinde analizin okuyacağı yer.

**Başarısızsa:** snapshot tam tasarımı gösteriyorsa seçim `start_session`'dan
sonra uygulanmış demektir — sırası önemli.

---

## Kabul kriterleri

- [ ] Bayraksız koşu hiçbir şeyi değiştirmiyor (Test 1)
- [ ] Alt küme yalnız seçileni sayıyor (Test 2)
- [ ] Seçilen konuşmacı üç yere de yazılıyor (Test 3)
- [ ] Hatalı seçim komut satırında, katılımcı oturmadan yakalanıyor (Test 4)
- [ ] Türetilen tasarım snapshot turundan geçiyor (Test 5)
- [ ] Alt küme gerçekten koşuyor ve snapshot'a yazılıyor (Test 6)

## Bu alt adımda bilerek yapılmayanlar

- **Menü yok.** `--no-ask` bayrağı da yok: atlanacak bir soru henüz yok, dolayısıyla
  bayrak 12c'de menüyle birlikte geliyor.
- **`operator_notes` seçimi taşımıyor.** Seçim snapshot'ta duruyor; nota da
  yazmak 12c'nin işi (farklı konuşmacı uyarısıyla birlikte).
- **Kısmi oturum işaretlemesi ve katılımcı düzeyinde analiz** 12d.
- **Kontrol listesi (checklist) seçimi bilmiyor** ve bilerek bilmiyor: kurulumu
  doğruluyor (config, kalibrasyon, uyaran seti, disk), oturumun alt kümesini
  değil. 12c'de menü zaten kontrol listesinden **sonra** çıkacak, yani
  seçim-farkında bir kontrol listesi genel olarak mümkün değil. Sonucu: yalnız
  oddball koşacakken konuşma uyaranları eksikse kontrol listesi yine KIRMIZI
  verir. Bu, olduğundan iyimser olmaktansa tercih edilen taraf.

## Sırada ne var

**12c** — operatör menüsü (`gui.DlgFromDict`), girişten sonra tam ekran
açılmadan önce; önceki konuşmacı uyarısı ve oturum sayacıyla.
