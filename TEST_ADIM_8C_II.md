# Adım 8c-ii Manuel Test — src emekliliği + master merge

Adım 8'i kapatan tur: Adım 0'ın `src/` ağacı `legacy/`'ye donduruldu, `main.py`
yeni platforma yönlendirildi, ve (onaydan sonra) `develop` → `master` merge +
`git tag adim-8-oturum-akisi` yapılacak. Bu tur çoğunlukla mekanik; manuel test
hafif.

## Otomatik koşulanlar (bilgi için)

| Ne | Sonuç |
|---|---|
| Testler | **773 test yeşil** (CI alt kümesi; silinen 21 src testi düştü, yeni paket etkilenmedi) |
| `ruff` / `mypy` | temiz — `legacy/` hariç tutuldu (107 kaynak dosya) |
| Taşınanlar | `src/`, eski `main.py`, `admin.py`, `config.yaml`, `scripts/generate_*`, `TEST_ADIM_0.md` → `legacy/` (git mv, silinmedi) |
| Silinenler | Adım 0'ın 7 src testi (git rm; geçmiş korunuyor) |
| `main.py` | kök `main.py` artık `python -m mcgurk.ui`'yi çağıran ince shim |

## Ön koşullar
- [ ] Conda ortamı etkin.

---

## Test 1: `main.py` yeni akışa yönleniyor (~10 sn, donanımsız)

```powershell
python main.py --help
```

**Beklenen:** `usage: python -m mcgurk.ui ...` başlığı ve `--limit`, `--db`,
`--device`, `--new-session`, `--config` seçenekleri. (Eski "admin ayarları"
akışı **yok**.)

---

## Test 2 (ekran+ses): `main.py` gerçekten oturumu açıyor (~1 dk)

```powershell
python main.py --limit 2 --db $env:TEMP\mcgurk_8cii.sqlite
```

**Kontrol edilecek:**

1. Katılımcı giriş penceresi açılıyor (yeni form; ad/soyad yok).
2. Checklist onayı → karşılama → alıştırma → modüller (2'şer deneme) → bitiş.
   Yani `python main.py`, `python -m mcgurk.ui` ile **birebir aynı** davranıyor.
3. İstediğiniz an ESC → "emin misiniz?" onayı.

(Bu akışı 8b/8c-i'de zaten doğruladınız; buradaki tek yeni şey `main.py` giriş
noktasının yönlenmesi.)

---

## Test 3 (isteğe bağlı): legacy/ donmuş ve araç zincirinden hariç

```powershell
python -m pytest -m "not psychopy" -q
```

**Beklenen:** yeşil; `legacy/` altındaki hiçbir dosya toplanmıyor/test edilmiyor.
`ruff check .` ve `mypy .` de temiz (legacy hariç).

---

## Kapanış — master merge (onaydan sonra)

Manuel test onaylanınca:
- `develop` → `master` **fast-forward merge** + `git tag adim-8-oturum-akisi`,
  ikisi de push. (Master şimdiye dek initial commit'teydi → çakışma yok.)
- Bu, **"Adım 8 bitti"** dönüm noktasıdır. Adım 8.5 (arayüz cilası + danışman
  gösterimi) ve Adım 9 `develop`'ta sürer; master'ın sonraki güncellemesi
  Adım 9 sonu (`v1.0.0`).

## Kabul kriterleri
- [ ] `python main.py --help` yeni akışın seçeneklerini gösteriyor
- [ ] `python main.py` gerçek oturumu açıyor (mcgurk.ui ile aynı)
- [ ] Testler/ruff/mypy yeşil, `legacy/` hariç tutulmuş
- [ ] (Kapanış) develop → master merge + tag yapıldı ve push edildi
