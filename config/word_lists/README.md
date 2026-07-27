# AVSR kelime listeleri

Modül 2 (AVSR) hece setiyle bugün çalışıyor. Kelime seti için **kayıt henüz
yapılmadı** (`progress.md` → §F.2, çekim kılavuzu `docs/04_kod_disi_isler.md`
§2). Bu klasör o kaydın geleceği yeri ve dosyanın biçimini tanımlar.

## Dosya biçimi

```yaml
name: tr_pb_50            # zorunlu — listenin adı
language: tr              # varsayılan "tr"
description: >            # serbest metin: kaynak, kim derledi, hangi yayın
  Türkçe fonetik dengeli 50 kelime listesi.
items:                    # zorunlu, en az bir kelime, tekrarsız
  - kitap
  - masa
```

Doğrulama `mcgurk/config/word_lists.py` içinde: bilinmeyen alan, boş girdi,
tekrarlı kelime ve baştaki/sondaki boşluk reddedilir. Tekrar sayısı listede
değil, config'teki `reps` alanında verilir — listede iki kez geçen bir kelime
o kelimeyi sessizce iki katı sunardı.

## Listeyi devreye almak

Kod değişmez, üç şey gerekir:

1. Kelimeler `stimulus_prep.tokens` listesine eklenir ve
   `python tools/prepare_stimuli.py` ile hazırlanır (her kelime için sessiz
   video + hizalanmış ses + gürültülü türevler).
2. Bu klasördeki liste dosyası doldurulur.
3. `config/experiment.yaml` → `modules.avsr.stimulus_sets` içindeki kelime
   setinin `enabled` alanı `true` yapılır.

Sıra önemli: liste `enabled: true` iken dosya yoksa, boşsa veya kelimeler
hazırlanmış sette yoksa config **yüklenirken** açık hata verir — oturumun
ortasında değil.

## Deneme sayısı

`reps` **öğe başına hücre başına**. 50 kelime × `reps: 1`, üç sunum modu, iki
gürültü ve iki kulak ile 50 × (1 + 4 + 4) = 450 deneme eder — hece setinin
üstüne. Listeyi açmadan önce `python -m mcgurk.config` çıktısına bakın (§F.1).
