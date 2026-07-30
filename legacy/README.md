# legacy/ — Adım 0 taban çizgisi (donmuş)

Bu klasör, projenin **Adım 0** hâlini (tek dosyalı, `src/` tabanlı ilk çalışan
sürüm) tarihsel referans olarak saklar. Adım 8 sonunda (8c-ii, 2026-07-30) yeni
`mcgurk/` platformu tek çalışan sürüm oldu ve buradaki her şey emekliye ayrıldı.

**Buradaki kod çalıştırılmaz ve test edilmez.** İçerik olduğu gibi dondurulmuştur;
importlar (`from src...`) artık kök `src/` yerine `legacy/src/`'i işaret ettiği
için doğrudan koşmaz. Amaç, o günkü kararların ve uygulamanın kaydını korumaktır
(silmek yerine — kullanıcı kararı).

## İçindekiler
- `src/` — Adım 0 paketi (config, data, dialogs, experiment, admin, utils).
- `main.py` — eski PsychoPy deney yürütücüsü (yeni akış kök `main.py`'de).
- `admin.py` — eski PySide6 admin paneli.
- `config.yaml` — eski deney yapılandırması (yeni: `config/experiment.yaml`).
- `scripts/generate_noisy_stimuli.py`, `generate_dichotic_stimuli.py` — eski
  asset üreticileri (Adım 2 offline hazırlık boru hattıyla değiştirildi).
- `TEST_ADIM_0.md` — Adım 0 manuel test dosyası.

## Bugünkü karşılıkları
| Eski (legacy/) | Yeni |
|---|---|
| `src/` | `mcgurk/` paketi |
| `main.py` | kök `main.py` → `python -m mcgurk.ui` |
| `admin.py` | (Adım 9'da yeni analiz/dışa aktarım) |
| `config.yaml` | `config/experiment.yaml` |
| `scripts/generate_*` | `tools/prepare_stimuli.py` (Adım 2) |
| `data/mcgurk.db` | `data/mcgurk.sqlite` (ayrı, uyumsuz şema) |

Araç zinciri (`ruff`, `mypy`, `pytest`) bu klasörü **hariç tutar**.
