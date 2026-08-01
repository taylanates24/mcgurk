# ADIM 11 — Operatör panelinde "Ayarlar" sekmesi (düzenlenebilir tekrar sayıları)

> **Bu bir Adım 11 promptudur.** `docs/steps.md` §A (değişmez kurallar) ve §B
> (her adımda işletilecek döngü: **önce plan-onay → uygula → doğrula → manuel
> test → commit**) bu adım için de aynen geçerlidir. Alt adımlara böl (11a/11b),
> her birinde ayrı plan-onay/test/commit. `progress.md`'yi her kapanışta
> güncelle. **Türkçe konuş, kod/commit İngilizce.**
>
> **Önce oku:** `docs/PLAN_AYARLAR_SEKMESI.md` (ayrıntılı teknik plan — dosya
> listesi, alanlar, ruamel, doğrula-geri-al akışı, gotcha'lar). Bu prompt o planı
> kapsayan üst çerçevedir; çeliştikleri yerde bu prompt geçerli.

## §0. Bağlam ve amaç

Adım 10'da üretilen operatör paneli (`mcgurk/panel/`, PyQt6, `python -m
mcgurk.panel` / donmuş `.exe`) bugün oturum başlatma, checklist, uyaran/yedek
doğrulama, sonuç tarama, analiz/QC/dışa aktarım ve **oturum silme** yapıyor.
Ama modül başına **tekrar sayıları** yalnızca `config/experiment.yaml` elle
düzenlenerek ayarlanıyor.

**Amaç:** Panele bir **"Ayarlar" sekmesi** — araştırmacı modül başına tekrar
sayılarını görüp değiştirsin, canlı toplam deneme/süre görsün, kaydetsin ve bir
**"Varsayılana dön"** butonuyla fabrika değerlerine dönebilsin. Python veya YAML
bilmek gerekmesin.

Kullanıcı kararları (2026-08-02): (1) **panelde düzenlenebilir alanlar** (salt-
okunur özet değil); (2) **"Varsayılana dön" butonu** olacak.

Bu adım Adım 10'dan sonra, kullanıcı isteğiyle eklendi (`steps.md` kapsamı
dışı). Prova oturumu ve `v1.0.0` bu adımdan **bağımsız** ilerleyebilir; Ayarlar
sekmesi tamamlanınca paketlenmiş app yeniden derlenip doğrulanır.

## §A11. Bu adıma özel değişmez kurallar

`steps.md` §A ve Adım 10'un §A10'una **ek olarak**:

1. **Config yorumları korunur.** `experiment.yaml` yoğun açıklama yorumu içerir;
   yazma **ruamel.yaml round-trip** ile yapılır (yalnız değişen anahtar değişir).
   `pyyaml` ile yeniden dump ederek yorumları silmek **yasak**.
2. **Doğrula-yoksa-geri-al.** Yazdıktan sonra config `load_config` ile
   doğrulanır; geçersizse (Pydantic kısıtı, oddball rampa/aralık kuralı vb.)
   **eski içerik geri yazılır** ve açık hata verilir. Diskte asla bozuk config
   bırakılmaz.
3. **Panel çekirdeği GUI'den ayrı ve CI-testli** (§A10.3). Config okuma/yazma
   mantığı PyQt6'sız, PsychoPy'siz, testli (`mcgurk/config/edit.py` saf).
4. **Parametreler config'ten** (§A.9). Sekme değerleri config'i düzenler; tasarım
   koda gömülmez. **"Varsayılan" değerler de** koda gömülmez — kanonik bir config
   kaynağından okunur (bkz. §C11 11a, "varsayılan kaynağı").
5. **Değişiklik yalnız sonraki oturumları etkiler.** Her oturum config'ini
   `sessions.config_snapshot`'a yazar; geçmiş veriler etkilenmez. Bu, sekmede
   kullanıcıya da belirtilir.
6. **cp1254-güvenli** metinler (`test_console_encoding.py`); panelde renkli/özel
   karakter gerekiyorsa HTML entity (Adım 10'daki `&#9679;` deseni gibi).
7. **PyQt6** (tek Qt binding — Adım 10c kararı). Panel PsychoPy import etmez.

## §C11. Alt adımlar

### ADIM 11a — Config-düzenleme çekirdeği (GUI'siz, CI-testli)

**Yapılacaklar:**
- **`ruamel.yaml`** ekle: `requirements.txt` **ve** `requirements-ci.txt` (edit
  mantığı CI'da test edilecek). Kesin sürüm pinle. PyInstaller için not: 11b/
  yeniden derlemede `collect_all('ruamel.yaml')` gerekebilir.
- **`mcgurk/config/edit.py`** (yeni, saf):
  - `read_reps(config) -> list[RepField]` — düzenlenebilir alanlar (etiket,
    değer, min/max, YAML yol anahtarı). Alanlar: mcgurk 5 AV-çifti `reps`; avsr
    hece `reps`; tbw `reps_per_soa`; oddball `n_trials`; dichotic `reps`;
    `session.practice_trials`; `cross_hearing_check.n_trials`. (gin salt-okunur.)
  - `write_reps(config_path, project_root, changes)` — ruamel ile yükle, yalnız
    değişen anahtarları set et, dump et (yorum korunur), `load_config` ile
    **doğrula**; geçersizse eski içeriği geri yaz + `ConfigError`.
  - **Varsayılan kaynağı** (§A11.4): önerilen çözüm salt-okunur
    `config/experiment.defaults.yaml` (git'te, mevcut tasarımdan üretilir);
    `default_reps() -> dict` oradan okur. Alternatifler ve gerekçeler
    `PLAN_AYARLAR_SEKMESI.md` §Açık nokta'da — plan aşamasında karar ver.
- **`mcgurk/panel/core.py`**: ince sarmalayıcılar (`design_rows`, `save_reps`,
  `default_reps`).
- Testler (`tests/mcgurk/test_config_edit.py` + `test_panel_core.py`): reps
  değişince dosyada değer değişir **ve bir yorum satırı hâlâ durur**; geçersiz
  değer → `ConfigError` ve dosya **değişmeden** geri yüklenir; `default_reps`
  kanonik değerleri döndürür.

**Kabul kriterleri:**
- [ ] `read_reps`/`write_reps`/`default_reps` doğru — test
- [ ] Yorumlar round-trip'te korunuyor — test (dosya metninde yorum aranır)
- [ ] Geçersiz değer diski bozmuyor (doğrula-geri-al) — test
- [ ] `ruff` + `mypy` temiz; `pytest -m "not psychopy"` yeşil (yerel **ve**
      Qt'siz CI venv'inde — 10b/c dersi: `no-any-return`, cp1254)

**Manuel test:** ekran gerekmez.

### ADIM 11b — PyQt6 "Ayarlar" sekmesi (GUI kabuğu)

**Yapılacaklar:**
- **`mcgurk/panel/app.py`**: ana pencere `QTabWidget`'a alınır — **"Panel"**
  sekmesi (mevcut: aksiyon çubuğu + sonuç tablosu + çıktı) ve **"Ayarlar"**
  sekmesi. **`test_panel_app.py` offscreen smoke** buna göre güncellenir.
- Ayarlar sekmesi: modüle göre gruplu `QSpinBox`'lar (11a alan listesi) + canlı
  **"Toplam: N deneme / ~X dk"** etiketi (değiştikçe bellek-içi hesap,
  kaydetmeden) + **"Kaydet"** + **"Varsayılana dön"** butonları.
  - **Kaydet** → `core.save_reps` → yaz+doğrula → config yeniden yükle, özet
    tazele, durum bildir; hata olursa diyalog, disk değişmez.
  - **"Varsayılana dön"** → onay iste → spinbox'ları `core.default_reps`
    değerlerine getir (henüz kaydetme; kullanıcı Kaydet'e basınca yazılır).
  - Donmuş app'te config yolu `ensure_writable_config(runtime)` ile alınır.

**Kabul kriterleri:**
- [ ] Ayarlar sekmesi açılıyor, alanlar mevcut config değerleriyle dolu
- [ ] Değer değişince toplam/süre canlı güncelleniyor
- [ ] Kaydet config'e yazıyor (yorumlar korunuyor), geçersizde disk bozulmuyor
- [ ] "Varsayılana dön" alanları fabrika değerlerine getiriyor (onaylı)
- [ ] Metinler Türkçe; panel PyQt6, PsychoPy import etmiyor (sınır testi)

**Manuel test:** ekran gerekir (`TEST_ADIM_11.md`). Qt UI CI'da test edilmez.

## §D11. Bilinen riskler / açık noktalar

- **"Varsayılan"ın kaynağı** — `PLAN_AYARLAR_SEKMESI.md` §Açık nokta; plan
  aşamasında netleşir (önerilen: `config/experiment.defaults.yaml`).
- **ruamel + PyInstaller** — donmuş derlemede `collect_all('ruamel.yaml')`
  gerekebilir; 11b sonrası paketlenmiş app'te doğrulanmalı.
- **QTabWidget geçişi** mevcut çalışan paneli ve smoke testini etkiler; dikkatli
  refactor.
- **Tasarım bütünlüğü:** veri toplama başladıktan sonra tekrar sayısını
  değiştirmek oturumları tutarsızlaştırır — ama her oturum kendi snapshot'ını
  tutar (§A11.5). Sekmeye bu uyarı yazılır.

## §E11. Kapanış

Adım 11 bitince:
1. Paketlenmiş app'i yeniden derle (`tools/build_exe.py --clean`), Ayarlar
   sekmesini ve "Varsayılana dön"ü **paketlenmiş halde** doğrula (`ruamel`
   bundle'landı mı, config yazımı writable konumda mı).
2. `progress.md` güncelle. Gerekirse `v1.x` etiketi (kullanıcı onayıyla).
