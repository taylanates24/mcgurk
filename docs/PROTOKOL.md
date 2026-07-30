# PROTOKOL — Yöntem Dokümanı ↔ Kod Eşlemesi

Bu belge, projenin bilimsel spesifikasyonu olan yöntem dokümanı
(`docs/946383_YONTEM (3).docx`) ile bu depodaki kodun **birebir eşlemesidir**.
Amaç: yöntem dokümanındaki her bağımsız ve bağımlı değişkenin, her yordamsal
kararın kodda nerede karşılandığını göstermek — böylece etik kurul, danışman ve
yayın incelemesi "dokümanda yazan şey kodda gerçekten var mı" sorusunu tek
tablodan yanıtlayabilir.

**Sürüm notu.** Yöntem dokümanı üç ana modül (McGurk, AVSR, TBW) + işitsel
dikkat kontrolü (oddball) tanımlar. **Dikotik dinleme (§6.5)** ve **GIN (§6.6)**
yönteme sonradan eklenmek üzere yazılmış taslak bölümlerdir (`docs/EK_*.docx`) ve
**danışman onayı beklemektedir**; kodda gerçeklenmiş olsalar da protokole
eklenmeden veri toplanmamalıdır. Sapmalar aşağıda "Sapma" olarak işaretlenmiştir.

---

## 1. Katılımcılar ve dahil/dışlama (yöntem §4)

| Yöntem dokümanı | Kod karşılığı |
|---|---|
| 18–60 yaş | `participants.age` `CHECK (age BETWEEN 18 AND 60)` (`mcgurk/db/schema.sql`) |
| 20 sağ + 20 sol SSD + 20 kontrol | `participants.group_code` `CHECK (... IN ('SSD_R','SSD_L','CTRL'))` |
| İşitme kaybı süresi ≥ 6 ay | `participants.deprivation_months` (kontrolde NULL); klinik değişken, §8'de kovaryat |
| Postlingual başlangıç | `participants.postlingual` (0/1) |
| Karşı/iki kulak eşikleri | `participants.pta_left_db`, `pta_right_db` (odyometri, dBHL) |
| Demografi girişi | `mcgurk/ui/login.py` (`build_participant` saf; `gui.DlgFromDict`) |

**KVKK (§A.6).** Ad, soyad, doğum tarihi **hiçbir yere yazılmaz**; katılımcı yalnız
anonim `participant_code` ile tanımlanır. Ad sütunu içeren eski bir veritabanı
açılırsa program açık hatayla durur (`SchemaMismatchError`). Yöntem §5.2 de
yalnız "kullanıcı kodu" der — uyumlu.

## 2. Deney platformu (yöntem §5)

| Yöntem dokümanı | Kod karşılığı | Not |
|---|---|---|
| §5.1 Otomatik uyaran üretimi (MoviePy) | `tools/prepare_stimuli.py` + `mcgurk/stimuli/` | **Sapma:** MoviePy yerine ffmpeg (teknik olarak eşdeğer/daha uygun; kayıpsız yeniden kodlama, CFR, hizalama). Çevrimdışı (§A.12). |
| §5.2 Arayüz + katılımcı yönetimi (CustomTkinter) | `mcgurk/ui/login.py`, `mcgurk/ui/screens.py` | **Sapma:** CustomTkinter yerine PsychoPy `gui.Dlg`/`DlgFromDict` (tek süreç, PsychoPy ile aynı olay döngüsü). |
| §5.3 PsychoPy + Psychtoolbox (ptb), rastgele sıra, ms-RT | `mcgurk/engine/` (`audio.require_ptb_backend`, `av_presenter.py`), tohumlu RNG | Ses **yalnız** ptb; sessiz geri düşüş yasak (§A.2). Sıra tohumdan yeniden üretilebilir (`sessions.seed`, §A.11). |
| §5.4 SQLite + Pandas'a aktarım | `mcgurk/db/` (SQLite), `mcgurk/analysis/export.py` (Pandas → CSV/parquet) | İlişkisel altı tablo + `v_trials_flat` VIEW. |

## 3. Bağımsız değişkenler (yöntem §7)

| Bağımsız değişken | Kod karşılığı |
|---|---|
| Grup (sağ SSD / sol SSD / kontrol) | `participants.group_code` |
| Uyarım koşulu (A-only / V-only / AV) | `trials.presentation_mode` (`modules.avsr.presentation_modes`) |
| Gürültü durumu (sessiz / gürültülü +5 dB SNR) | `trials.snr_db`, `trials.noise_condition` (`modules.*.noise_conditions: [null, 5.0]`) |
| İşitsel uyaranın uzamsal yönü (sağ / sol) | `trials.ear` (`modules.*.ears: [left, right]`); motor lateralizasyonu (`engine/audio.py`) |

## 4. Modüller ve bağımlı değişkenler (yöntem §6, §7)

Ölçüm matematiği her modülün kendi dosyasındadır (PsychoPy'siz, CI-testli) ve
`mcgurk/analysis/measures.py` tarafından veritabanına bağlanır
(`python tools/analyse.py`).

### Modül 1 — McGurk (yöntem §6.1)

| Ölçülen değişken | Kod karşılığı |
|---|---|
| Birleşme (fusion) oranı | `mcgurk/modules/mcgurk.py` → `McGurkRates.fusion_rate`; kategori `FUSION` |
| Görsel baskınlık (visual capture) oranı | `McGurkRates.visual_rate`; kategori `VISUAL` |
| İşitsel yanıt oranı | `McGurkRates.auditory_rate`; kategori `AUDITORY` |
| Tepki süresi (ms) | `McGurkRates.mean_rt_ms` (`responses.rt_from_burst_ms` — akustik patlamadan) |

- **Uyumsuz denemede doğru cevap yoktur (§A.10).** `responses.is_correct` NULL;
  kategori türetilir (`categorise`), haritalar config'ten (`fusion_map`,
  `combination_map` — §A.9). Vis-/ga/ + Aud-/ba/ → "DA" = `FUSION`, hata değil.
- Uyumlu kontroller (`congruent_*`) füzyon karşılaştırması için; hepsi
  `av_pairs` içinde.

### Modül 2 — AVSR / görsel-işitsel konuşma tanıma (yöntem §6.2)

| Ölçülen değişken | Kod karşılığı |
|---|---|
| Doğruluk oranları (%) | `mcgurk/modules/avsr.py` → `accuracy_by_mode` (`Accuracy.accuracy`) |
| Görsel fayda indeksi (AV − A-only) | `visual_benefit`, `visual_benefit_by_condition` |
| Lipreading performansı (V-only) | `lipreading_accuracy` |

- **Burada doğru cevap vardır** (Modül 1'in tersine): `responses.is_correct`
  yazılır, `category` NULL. Zaman aşımı **yanlış** sayılır (`Accuracy.n_missing`
  ayrıca taşınır) — dışlamak zamanı yetmeyen katılımcıyı kayırırdı.
- **V-only gürültü ve kulakla çaprazlanmaz** (sessiz videonun SNR'ı ve yönü
  yoktur): `snr_db`/`noise_condition`/`ear` NULL.
- Kelime seti (§6.2 "tek heceli fonetik dengeli Türkçe kelimeler") **veri
  odaklı, şu an boş** (§F.2, aşağıdaki "Açık uçlar").

### Modül 3 — TBW / temporal binding window (yöntem §6.3)

| Ölçülen değişken | Kod karşılığı |
|---|---|
| TBW genişliği | `mcgurk/modules/tbw.py` → `TBWFit.width_ms` (`tbw_definition`: FWHM=2.355σ / ±1σ) |
| Öznel eşzamanlılık noktası (PSS) | `TBWFit.pss_ms` |
| SOA −300…+300 ms | `modules.tbw.soa_values_ms`; SOA ses tarafında üretilir (`engine/scheduling.py`) |

- Eşzamanlılık yargısı; **doğru cevap yoktur** (§A.10 tetikleyicisi `tbw`'yi de
  reddeder). Zaman aşımı eksik gözlem (kategori değil). Gauss psikometrik uydurma
  (binomial MLE) + bootstrap GA; uydurulamayan durum **hata** (`FitError`), sayı değil.

### İşitsel dikkat kontrolü — Oddball (yöntem §6.4)

| Ölçülen değişken | Kod karşılığı |
|---|---|
| Hedef doğruluğu | `mcgurk/modules/oddball.py` → `Counts.hits`/`n_targets`, `DetectionMeasures.hit_rate` |
| Tepki süresi | `DetectionMeasures.mean_rt_ms` |
| Hata oranı | `false_alarm_rate`; ayrıca `d_prime`, `criterion` (log-lineer düzeltmeli, Hautus 1995) |
| Kovaryat rolü (§8) | Dikkat ölçütleri karma modelde kovaryat — analiz aşaması (dışa aktarımdan sonra) |

- Sürekli ton akışı; standart (%80–85) / hedef (%15–20) config'ten
  (`target_probability`). Ardışık hedef kısıtı `min_standards_between_targets`.
  Süre ~5–6 dk (config'ten hesaplanır).

### Modül 5 — Dikotik dinleme (taslak §6.5, `docs/EK_DIKOTIK_DINLEME.docx`)

| Ölçülen değişken | Kod karşılığı |
|---|---|
| Kulak avantajı indeksi (KAİ) | `mcgurk/modules/dichotic.py` → `EarAdvantage.laterality_index` = [(Sağ−Sol)/(Sağ+Sol)]×100 |
| Karışım (intrusion) oranı | `EarAdvantage.intrusion_rate` (kategori `OTHER`) |

- **Sapma/eklenti:** yöntem dokümanında henüz yok; §6.5 taslak, danışman onayı
  bekliyor. Doğru cevap yoktur; zaman aşımı eksik gözlem. SSD gruplarında sunum
  işlevsel olarak monotiktir (§6.5 bunu belirtmeyi şart koşar).

### Modül 6 — GIN / Gaps-In-Noise (taslak §6.6, `docs/EK_GIN.docx`)

| Ölçülen değişken | Kod karşılığı |
|---|---|
| Boşluk saptama eşiği | `mcgurk/modules/gin.py` → `GINMeasures.threshold_ms` (4/6 ölçütü; ulaşılamazsa `None`) |
| Yanlış alarm sayısı | `GINMeasures.n_false_alarms` (eşik hep bununla birlikte okunur) |

- **Sapma/eklenti:** yöntem dokümanında henüz yok; §6.6 taslak, danışman onayı
  bekliyor. TBW ölçütü için kontrol (düşük düzeyli işitsel zamansal keskinlik).
  Monaural; iyi kulak Adım 8'den geçer.

## 5. Geçerlilik kontrolü — Çapraz dinleme (§F.3, §6.5)

| Amaç | Kod karşılığı |
|---|---|
| SSD'de sağır kulağa sunumun geçerliliği | `mcgurk/modules/cross_hearing.py` (tespit görevi, ses var/yok) |
| "Şans üstü tespit → lateralizasyon geçersiz" yargısı | `mcgurk/analysis/qc_report.py` → tek yönlü binomial, `qc.cross_hearing_alpha` |
| Rapor | `python tools/qc_report.py` — şans üstü çıkarsa o katılımcının Modül 1–2 uzamsal verisi işaretlenir |

## 6. İstatistiksel analiz (yöntem §8) — yazılım sınırı

Yöntem §8 (karma ANOVA / doğrusal karma modeller, kovaryatlar, p<0,05)
**yazılımın kapsamı dışındadır**: platform veriyi toplar ve düz dosyaya aktarır;
model kurma analiz ortamında (R/Python) yapılır.

| §8 unsuru | Kod karşılığı |
|---|---|
| Pandas'a veri aktarımı | `mcgurk/analysis/export.py` → `v_trials_flat` + ham tablolar (CSV/parquet) |
| Modül ölçütleri (analiz girdisi) | `mcgurk/analysis/measures.py` (`python tools/analyse.py`) |
| Deprivasyon süresi (klinik değişken/kovaryat) | `participants.deprivation_months` |
| Dikkat kovaryatı | Oddball `d_prime` (Modül 4) |
| Kalite kontrol (bozuk deneme, zaman aşımı, SOA sapması) | `mcgurk/analysis/qc_report.py` (`python tools/qc_report.py`), eşikler `config.qc` |

## 7. Zamanlama ve doğruluk güvenceleri (§5.3 ruhu)

| Güvence | Kod karşılığı |
|---|---|
| Ses ekranın flip saatine planlanır | `engine/av_presenter.py` (`Sound.play(when=getFutureFlipTime('ptb'))`) |
| Ses ve görüntü ayrı konteyner (§A.1) | Sessiz video + ayrı WAV (`stimuli/`) |
| Gerçekleşen zamanlama kaydı (§A.4) | `trials.actual_soa_ms`, `dropped_frames`, `max_frame_interval_ms`, onset'ler |
| Sistem A/V gecikmesi telafisi | `sessions.system_av_offset_ms` (fotodiyot, `docs/01`) |
| Ses kalibrasyonu | `calibrations` tablosu (`docs/02`); `data_collection` modunda zorunlu |
| Config anlık görüntüsü | `sessions.config_snapshot` — veri toplandığı tasarımla yorumlanır |

## 8. Açık uçlar (danışman / kod dışı)

Ayrıntı `progress.md` → *Açık kararlar* ve *Kullanıcıya bekleyen aksiyonlar*.

- **Dikotik (§6.5) ve GIN (§6.6) yönteme eklenmeli** — taslaklar hazır, danışman
  onayı bekliyor. Protokole girmeden bu iki modülün verisi kullanılmamalı.
- **Deneme sayıları (§F.1)** config'ten; danışman kararı. `python -m mcgurk.config`
  tahmini süreyi basar.
- **AVSR kelime seti (§F.2)** — kayıt seansı yapılmadı; şema hazır, içerik boş.
- **Kulaklık tipi (§F.3)** — insert kulaklık gerekebilir; çapraz dinleme kontrolü kodda hazır.
- **QC eşikleri ve çapraz duyma α'sı** — `config.qc`, geçici değerler, danışman onaylamalı.
- **Fotodiyot (`docs/01`) ve kalibrasyon (`docs/02`)** — tüm kod bittikten sonra;
  yapılmadan `data_collection` modu başlamaz.
