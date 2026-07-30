# Adım 8c-i Manuel Test — Kesinti/devam (resume)

Adım 8c'nin ilk turu: oturum yarıda kalırsa (ESC → çık, ya da çökme) aynı
katılımcıyla **kaldığı yerden** devam. Kabul kriteri: "kesip devam ettirme
çalışıyor, veri kaybı yok".

**Toplam süre ~5 dakika.**

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| Otomatik testler | **794 test yeşil** (CI alt kümesi; 10 yeni), `ruff` + `mypy` temiz |
| Yeni testler | `test_resume.py`: `remaining_plan` (atla/dilimle/stream-tam), config snapshot round-trip, DB yardımcıları (bellek-içi) |
| Resume mantığı | tamamlanan modül atlanır; forced-choice kısmi modül `plan[K:]`'ten sürer; stream/çapraz-dinleme tam yeniden — hepsi donanımsız doğrulandı |

**Tasarım:** Devam'da **aynı `session_id`, aynı tohum ve oturumun saklı config
snapshot'ı** kullanılır — kalan denemeler, oturum başladığında planlananla
birebir aynı. Tamamlanan modüller (`completed` bloklardaki deneme sayısı = planlanan)
atlanır. Yarım `aborted` bloklar DB'de kalır; analiz onları dışlar.

## Ön koşullar

- [ ] Conda ortamı etkin, kulaklık/aygıt bağlı.
- [ ] **İki koşu da aynı veritabanını kullanmalı** (resume kalan oturumu orada
      bulur) ve **aynı katılımcı kodu** girilmeli (resume katılımcıya göre bulur).
- [ ] Komutlar PowerShell.

---

## Test 1: Yarıda kes, sonra devam et (~4 dk)

**A. İlk koşu — yarıda kes:**

```powershell
python -m mcgurk.ui --limit 4 --db $env:TEMP\mcgurk_8ci.sqlite
```

- Giriş: kod **`RESUME-01`**, grup **SSD-Sağ** (PTA Sağ 70, Sol 10). Kodu not
  edin — ikinci koşuda **aynısını** gireceksiniz.
- Yarım oturum yoksa doğrudan checklist onayına geçer (bu ilk koşuda beklenir).
- Alıştırma → mcgurk → avsr … ilerleyin. **Birkaç modül bittikten sonra** (ör.
  mcgurk ve avsr'den sonra, tbw sırasında) **ESC → ENTER (Evet)** ile çıkın.
- Konsolda "Oturum N ESC ile kesildi." ve yedek. Çıkış kodu 2.

**B. İkinci koşu — devam et:**

```powershell
python -m mcgurk.ui --limit 4 --db $env:TEMP\mcgurk_8ci.sqlite
```

- Giriş: **aynı kod `RESUME-01`**.
- Girişten sonra **"Kaldığı yerden devam?"** diyaloğu çıkar (yarım oturum #N,
  tarih, `aborted`). **"Devam et (kaldığı yerden)"** seçin.
- Konsolda: **"Oturum N DEVAM ediyor. Tamamlanan: {...}"**.

**Kontrol edilecek:**

1. **Tamamlanan modüller atlanıyor** — konsolda her biri için "… zaten
   tamamlanmış — atlanıyor (resume)." Yönerge ekranları o modüller için
   **görünmüyor**.
2. **Kaldığı modülden sürüyor** — ESC'ye bastığınız modül (tbw) baştan koşuyor
   (yarım `aborted` bloğu sayılmaz, forced-choice'ta `plan[K:]`), sonraki
   modüller normal.
3. **Aynı oturum** — konsoldaki oturum numarası ilk koşudakiyle **aynı** (yeni
   oturum açılmadı).
4. Oturum baştan sona tamamlanınca çıkış 0, yedek yazılıyor.

**Başarısızsa:** Diyalog çıkmıyorsa aynı kodu girdiğinizden ve aynı `--db`'yi
kullandığınızdan emin olun. Atlanması gereken modül yeniden koşuyorsa bildirin.

---

## Test 2: "Yeni oturum" ve "İptal" (~1 dk)

İkinci koşuyu tekrar başlatın (yarım oturum hâlâ varsa):

- **"Yeni oturum başlat"** seçin → **yeni** bir oturum numarasıyla baştan başlar
  (eski yarım oturum `aborted` kalır).
- Tekrar başlatıp **"İptal"** seçin → oturum **başlamaz**, program temiz çıkar
  (çıkış 0), pencere açılmaz.
- **`--new-session`** bayrağı → diyalog hiç çıkmaz, doğrudan yeni oturum:

```powershell
python -m mcgurk.ui --limit 4 --db $env:TEMP\mcgurk_8ci.sqlite --new-session
```

---

## Kabul kriterleri

- [ ] Yarıda kesilen oturum ikinci koşuda "devam" olarak teklif ediliyor (aynı
      kod + aynı db)
- [ ] Devam'da tamamlanan modüller atlanıyor (yönergesiz), aynı oturum numarası
- [ ] Kaldığı modülden itibaren sürüyor, oturum tamamlanabiliyor, veri kaybı yok
- [ ] "Yeni oturum" yeni oturum açıyor; "İptal" temiz çıkıyor; `--new-session`
      teklifi atlıyor
