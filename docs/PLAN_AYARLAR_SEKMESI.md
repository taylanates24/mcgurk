# Plan — Operatör paneline "Ayarlar" sekmesi (düzenlenebilir tekrar sayıları)

> **Durum:** PLANLANDI, başka session'da yapılacak (kullanıcı kararı 2026-08-02).
> Adım 10 tamamlandıktan sonra eklenen panel özelliği. `docs/steps.md` §A/§B
> döngüsü geçerli: önce plan-onay → uygula → test → commit. Türkçe konuş, kod
> İngilizce.

## Amaç
Operatör/araştırmacı, modül başına **tekrar sayılarını** (dolayısıyla toplam
deneme sayısı ve süreyi) panelin **"Ayarlar" sekmesinden** görüp değiştirebilsin.
Bugün bunlar yalnızca `config/experiment.yaml` elle düzenlenerek ve
`python -m mcgurk.config` ile görülerek ayarlanıyor (§F.1 tekrar sayıları hâlâ
danışman kararına açık).

Kullanıcı kararı (2026-08-02): **panelde düzenlenebilir alanlar** (salt-okunur
özet değil).

## Mevcut tasarım (referans, `python -m mcgurk.config`)
| Modül | Deneme | Süre |
|---|---|---|
| practice | 12 | — |
| mcgurk | 140 | 14.0 dk |
| avsr | 135 | 15.8 dk |
| tbw | 130 | 10.8 dk |
| oddball | 300 | 5.2 dk |
| dichotic | 30 | 2.5 dk |
| gin | 30 | 4.0 dk |
| cross_hearing | 20 | — |
| **TOPLAM** | **797** | **~58.8 dk** |

"Tekrar" tek sayı değil; her modülün kendi yapısı var (mcgurk'te her AV-çifti
`reps` × gürültü(2) × kulak(2); oddball'da `n_trials`; tbw'de `reps_per_soa`…).

## Bağımlılık
- **`ruamel.yaml`** — `requirements.txt` **ve** `requirements-ci.txt`'e (edit
  mantığı CI-testli). YAML'ı **yorumları koruyarak** round-trip düzenlemek için
  şart: `experiment.yaml` yoğun açıklama yorumu içeriyor; pyyaml ile yeniden
  yazmak (dump) hepsini siler. ruamel round-trip modu yalnızca değişen değeri
  değiştirir, yorum/biçimi korur. Kesin sürüm pinle.

## Oluşturulacak / değiştirilecek dosyalar
- **`mcgurk/config/edit.py`** (yeni, saf, PsychoPy'siz, CI-testli):
  - `read_reps(config: ExperimentConfig) -> list[RepField]` — düzenlenebilir
    alanların (etiket, mevcut değer, YAML yol anahtarı, min/max) listesi.
  - `write_reps(config_path: Path, project_root: Path, changes: dict[str, int])
    -> None` — ruamel ile yükle, yalnız değişen anahtarları set et, dump et
    (yorumlar korunur), sonra **`load_config` ile doğrula**. Geçersizse (ör.
    Pydantic kısıtı, oddball rampa/aralık kuralı) **eski içeriği geri yaz** ve
    `ConfigError` fırlat — bozuk config asla diskte kalmaz.
  - Alanların YAML yolları (ruamel için): 
    - mcgurk: `modules.mcgurk.av_pairs[i].reps` (5 çift: fusion_pair,
      combination_pair, congruent_ba/da/ga)
    - avsr: hece `stimulus_sets` içindeki `type: syllable` girdisinin `reps`'i
    - tbw: `modules.tbw.reps_per_soa`
    - oddball: `modules.oddball.n_trials`
    - dichotic: `modules.dichotic.reps`
    - practice: `session.practice_trials`
    - cross_hearing: `cross_hearing_check.n_trials`
  - gin **düzenlenmez** (segmentler hazır setten gelir; basit tekrar knob'u
    değil) — salt-okunur gösterilebilir.
- **`mcgurk/panel/core.py`**: ince sarmalayıcılar
  - `design_rows(config) -> list[...]` (modül → deneme sayısı; `config.trial_counts()`)
  - `save_reps(config_path, project_root, changes) -> None` → `edit.write_reps`.
- **`mcgurk/panel/app.py`**: ana pencere `QTabWidget`'a alınır:
  - **"Panel"** sekmesi = mevcut içerik (aksiyon çubuğu + sonuç tablosu + çıktı).
  - **"Ayarlar"** sekmesi = modüle göre gruplu `QSpinBox`'lar + canlı
    "Toplam: N deneme / ~X dk" etiketi + **"Kaydet"** butonu.
  - **Dikkat:** `test_panel_app.py` offscreen smoke testi mevcut layout'a bağlı
    (buton kümesi kontrolü); QTabWidget'a geçişte güncellenmeli.

## Davranış
- Spinbox değiştikçe **canlı** toplam/süre yeniden hesaplanır (config'in bellek
  içi kopyasında; **kaydetmeden**). `config.trial_counts()` + `estimated_duration_s()`.
- **Kaydet** → `save_reps` → yaz + doğrula → başarılıysa config'i yeniden yükle,
  özeti tazele, durum çubuğunda onay; başarısızsa hata diyaloğu, disk değişmez.
- **Not (kullanıcıya gösterilecek):** değişiklik yalnız **sonraki** oturumları
  etkiler; her oturum kendi config'ini `sessions.config_snapshot`'a yazar, yani
  geçmiş oturumlar etkilenmez.

## Alternatif (değerlendirildi, seçilmedi)
- Sekme yerine butonla açılan **modal iletişim kutusu**: mevcut paneli daha az
  değiştirir (QTabWidget restructure yok) ama kullanıcı "sekme" istedi. Uygulayan
  session bunu tercih ederse app.py değişimi küçülür.

## Test stratejisi
- `tests/mcgurk/test_config_edit.py` (yeni): reps değiştir → dosyada değer
  değişti **ve yorumlar korundu** (dosya metninde bir yorum satırının hâlâ
  varlığını doğrula); geçersiz değer (ör. Pydantic min ihlali) → `ConfigError`
  ve dosya **değişmeden** geri yüklendi.
- `test_panel_core.py`'ye `save_reps`/`design_rows` testleri.
- `test_panel_app.py` QTabWidget'a göre güncellenir; PySide6/PyQt6 yok → CI'da
  atlanır (mevcut desen).
- ruff/mypy yeşil (yerel **ve** PyQt-siz CI venv'inde — 10b/10c dersleri:
  `no-any-return`, cp1254-güvenli metinler).
- Manuel (ekran): spinbox'lar, canlı toplam, Kaydet+doğrula, yorumların korunması.

## Gotcha'lar (10b/10c'den öğrenilenler)
- **cp1254-güvenli** metinler (panelde `−`/`→`/`≠` yok — Türkçe Windows konsolu).
- Panel PsychoPy import etmez (§A10.2, sınır testi). `config/edit.py` saf.
- Donmuş app'te config **writable_root/config/experiment.yaml**'dır
  (`ensure_writable_config`); Ayarlar sekmesi de o yolu düzenlemeli
  (`ensure_writable_config(runtime)` ile alınan yol).
- ruamel dump'ı frozen'da veri dosyası olarak sorun çıkarmaz (saf Python), ama
  PyInstaller `collect_all('ruamel.yaml')` gerekebilir — build'de doğrula.
