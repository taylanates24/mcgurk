# steps.md — McGurk / SSD Platformu Geliştirme Adımları

Bu dosya Claude Code CLI'nin yürüteceği geliştirme planıdır. Sırayla oku ve uygula.

**Nasıl kullanılır:**
1. Bu dosyanın tamamını oku (§A değişmez kurallar, §B döngü, §C adımlar, §D–F ekler).
2. `progress.md` yoksa §E şablonundan oluştur.
3. `progress.md`'de en son "TAMAMLANDI" işaretli adımı bul. İlk tamamlanmamış adımdan başla.
4. O adım için **önce plan sun, onay bekle** (§B.1).
5. Onaydan sonra uygula, sonra §B.2 kapanış döngüsünü işlet.
6. Sonraki adıma geç.

**Referans dokümanlar** (bu dosyayla aynı `docs/` klasöründe olmalı):
- `01_av_gecikme_olcumu.md` — fotodiyot ölçümü (insan yapacak, kod bittikten sonra)
- `02_kalibrasyon.md` — ses kalibrasyonu (insan yapacak, kod bittikten sonra)
- `04_kod_disi_isler.md` — tasarım kararı, kelime çekimi, pilot (bazı adımlar buna atıf yapar)
- Yöntem dokümanı (projenin bilimsel spesifikasyonu)

---

## §0. Bağlam

**Proje:** Tek taraflı işitme kaybı (SSD) olan yetişkinlerde görsel-işitsel entegrasyonun davranışsal değerlendirmesi. Atılım Üniversitesi Odyoloji Bölümü, etik kurul onaylı, 12 aylık klinik çalışma.

**Katılımcılar:** 20 sağ SSD + 20 sol SSD + 20 kontrol = 60 kişi.

**Dört değerlendirme modülü:**

| Modül | İçerik | Ana bağımlı değişkenler |
|---|---|---|
| 1 — McGurk | Fonem düzeyi, uyumlu/uyumsuz | Füzyon, görsel baskınlık, işitsel yanıt oranı, RT |
| 2 — AVSR | A-only / V-only / AV | Doğruluk, görsel fayda indeksi, lipreading |
| 3 — TBW | −300…+300 ms SOA, eşzamanlılık yargısı | TBW genişliği, PSS |
| 4 — Oddball | İşitsel dikkat kontrolü | Hedef doğruluğu, RT, hata oranı |

Modül 1 ve 2'de iki manipülasyon var: **gürültü** (sessiz / konuşma şekilli gürültü +5 dB SNR) ve **uzamsal yön** (sağ / sol kulak). Bunlar SSD hipotezini taşıyan değişkenlerdir.

**Depo:** `mcgurk_effect` — mevcut hâli 7 adet neredeyse aynı `main*.py`, düz CSV veri yazımı, gömülü sesli video oynatma. Bu plan onu üretime hazır bir platforma dönüştürür.

---

## §A. Değişmez kurallar

Bunlar tüm adımlar boyunca geçerlidir ve tartışmaya kapalıdır. Bir kuralı ihlal etmen gerektiğini düşünüyorsan **kod yazmadan önce dur ve sor.**

1. **Ses ve görüntü asla aynı konteynerde taşınmaz.** Video sessizdir (`noAudio=True`, `autoStart=False`), ses ayrı WAV'dır.
2. **Ses yalnızca PTB backend'i ile çalınır.** Sessiz geri düşüş yasak — PTB yüklenemezse açık hata verip çık.
3. **Ses ekranın flip saatine karşı zamanlanır:** `win.getFutureFlipTime(clock='ptb')` → `snd.play(when=...)`.
4. **Her denemenin gerçekleşen zamanlaması kaydedilir:** nominal SOA, gerçekleşen SOA, video/ses onset, düşen kare sayısı, maks kare süresi.
5. **Veri SQLite'a yazılır.** Deneme içinde disk G/Ç yapılmaz; commit'ler blok sınırlarında.
6. **Katılımcı kimliği anonim koddur.** Ad, soyad, doğum tarihi hiçbir yere yazılmaz (KVKK).
7. **Çıplak `except:` yasak.** Her zaman spesifik istisna, her zaman loglanır.
8. **Veri toplama modunda `fullscr=True`, `waitBlanking=True`.** Geliştirme modu ayrı bir config bayrağıdır.
9. **Deneysel parametreler koda gömülmez.** Deneme sayıları, AV çiftleri, SOA değerleri, SNR, modül sırası, katılımcıya gösterilen tüm metinler — hepsi config'ten.
10. **Uyumsuz denemede "doğru cevap" yoktur.** Ham yanıt saklanır, kategori türetilir.
11. **RNG seed her oturumda loglanır**, trial sırası yeniden üretilebilir olur.
12. **Çalışma anında resample veya ağır DSP yok.** Tüm uyaran hazırlığı deneme arası boşlukta veya offline.
13. **Görsel uyaran merkezde sunulur** (yöntem dokümanı gereği).

**Dil kuralı:**
- Kod, değişken adları, docstring, commit mesajı: **İngilizce**
- `progress.md`, `TEST_ADIM_N.md`, kullanıcıya hitap, özetler: **Türkçe**
- Katılımcıya gösterilen tüm metinler: **Türkçe**, config'ten

---

## §B. Her adımda işletilecek döngü

### B.1 — Açılış: plan kapısı

Adıma başlarken **önce plan sun, kod yazma.** Plan şunları içersin:
- Oluşturulacak / değiştirilecek dosyalar
- Anahtar tasarım kararları ve gerekçeleri
- Belirsiz kalan noktalar ve yaptığın varsayımlar
- Test stratejisi

Sonra **kullanıcı onayını bekle.** "Onaylandı" / "devam et" gelmeden implementasyona geçme. Kullanıcı değişiklik isterse planı güncelle, tekrar onaya sun.

### B.2 — Kapanış: doğrula → commit → raporla

Adımın implementasyonu bittiğinde **sırayla** şunları yap:

**1. Otomatik testleri koştur.**
```bash
pytest -v
ruff check .
mypy .    # Faz 1'den itibaren
```
Çıktıyı kullanıcıya göster. Kırmızı varsa düzelt, tekrar koştur. Yeşil olmadan devam etme.

**2. Türkçe özet yaz.** Kullanıcıya: ne yapıldı, hangi kararlar alındı, nelere dikkat edilmeli, hangi varsayımlar yapıldı.

**3. `TEST_ADIM_N.md` dosyası oluştur** (§D şablonu). Kullanıcının elle yapacağı adımlar. Somut olsun: çalıştırılacak komut, beklenen çıktı, neye bakılacağı. "Çalıştığını doğrulayın" gibi belirsiz adım yazma. Ekran/ses gerektiren testleri ayrı başlık altında topla.

**4. Kullanıcı onayını bekle.** Kullanıcı manuel testleri yapıp "onaylandı" diyene kadar commit YAPMA. Kullanıcı sorun bildir  irse düzelt, 1. adıma dön.

**5. `progress.md`'yi güncelle** (§E). O adımın satırını "TAMAMLANDI" yap, tarih, alınan kararlar, bilinen sınırlar, sonraki adıma taşınan notlar. (Commit hash'i bir sonraki adımda gelecek — şimdilik boş bırak.)

**6. Commit + push.**
```bash
git add -A
git commit -m "feat(adim-N): <kısa açıklama>

<gövde: ne yapıldı, hangi kararlar, hangi testler geçti>
"
```
Şimdi commit hash'ini al (`git rev-parse --short HEAD`), `progress.md`'deki o adımın "Commit" alanına yaz, sonra:
```bash
git add progress.md
git commit -m "docs(progress): adim-N kaydı"
git push
```
Böylece hem kod hem progress push edilmiş olur ve progress'te doğru hash bulunur.

**7. Sonraki adıma geç** (B.1'den başla).

### B.3 — Genel kurallar

- **Bir adımı yarım bırakıp sonrakine geçme.** Kapanış döngüsü tamamlanmadan ilerleme yok.
- **Kapsam dışına çıkma.** Bir adımın işi o adımda; sonraki adımların işini önden yapma.
- **Şüphede kal, sor.** §F'deki açık kararlarla veya §A kısıtlarıyla çatışan bir durum çıkarsa varsayımla ilerleme.
- **`git tag` ile dönüm noktalarını işaretle** (Faz 0'da `baseline-original` gibi).

---

## §C. Adımlar

### ADIM 0 — Baseline: mevcut kodun düzeltilmesi ve doğrulanması

**Amaç:** Çalışan, tek dosyalı, hatasız bir referans nokta. Mimariyi HENÜZ değiştirme — bu adım *bug* düzeltmesidir, yeniden yazım değil. Yeniden yazım Adım 3'te.

**Önce: mevcut koddaki tespit edilmiş sorunları doğrula.** Liste eksiksiz değil, bulduklarını ekle:

*Mimari (bunlar Adım 3'te çözülecek, şimdi sadece belgele):*
- `visual.MovieStim` gömülü sesi ffpyplayer→SDL2 yolundan çalar. `prefs.hardware['audioLatencyMode']` ve `audioLib=['ptb',...]` yalnızca `psychopy.sound.Sound`'u etkiler; MovieStim sesine **hiçbir etkisi yoktur**. Koddaki aksi yöndeki yorumlar yanlıştır.
- Ses videonun içinde olduğu için SOA manipülasyonu, gürültü ekleme ve lateralizasyon imkânsız.
- Uyaranlar AAC ile sıkıştırılmış (kayıplı + kodlayıcı priming gecikmesi).

*Ölçülmüş uyaran sorunları:*
- Konuşmacı-1 token'larının akustik patlama gecikmeleri: /ba/ 1105 ms, /da/ 1119 ms, /ga/ 1108 ms — 14 ms yayılım. `video_create.py` sesi t=0'a yapıştırıyor, hizalama doğrulaması yok. Token seviyeleri 2.07 dB farklı. (Bu Adım 2'de çözülecek.)
- Video 29.97 fps — 60 Hz'de kare başına 2.002 yenileme, periyodik kare tekrarı.

*Kavramsal:*
- `expected_sound = aud.upper()` + `DogruMu` sütunu: uyumsuz denemede doğru cevap yoktur. Vis-/ga/ + Aud-/ba/ → "DA" klasik füzyondur, kod bunu hata sayıyor. (Kategorizasyon Adım 4'te.)
- Yanıt seti BA/DA/GA — kombinasyon algısı ("bga") ifade edilemiyor.
- Toplam 9 deneme, hücre başına 1 tekrar.

**Yapılacaklar (bu adımda gerçekten düzeltilecekler):**
- 7 main dosyasını incele, en olgun olanı seç (`main_ver2.py` aday), gerekçeni yaz.
- Silmeden önce `git tag baseline-original` at ki tarih kaybolmasın.
- Diğer main dosyalarını sil. Seçileni `legacy/mcgurk_legacy.py` olarak taşı, şu kod düzeyi hataları düzelt:
  - Video süresi manifest/dosyadan okunsun, sabit `2.0` s kalksın
  - Yanıt ekranına geçmeden `movie.stop()` + `win.flip()` (video yanıt penceresine taşmasın)
  - `show_launcher()` iptal durumu (`None` dönsün, çağıran temiz çıksın)
  - Çıplak `except:` → spesifik istisna + log
  - `event.getKeys()` döngü başına tek çağrı
  - CSV dosya tutamağı açık kalsın (her denemede aç/kapa yok)
  - `win.size` yerine `win.clientSize` (HiDPI framebuffer sorunu)
  - Video merkeze
  - RNG seed loglansın
  - Katılımcı adı yerine anonim kod
  - Yol sanitizasyonu
- `conditions.csv` sil (kullanılmıyor, isimlendirme uyumsuz).
- `requirements.txt` düzelt: tekrarları kaldır, `pillow` ve `ffpyplayer` ekle, **kesin sürüm pinle**.
- `.gitignore` düzelt; `assets.zip` git geçmişinden çıkarılsın (Git LFS veya harici depolama notu düş).
- `README.md` yaz: ne olduğu, nasıl çalıştırılacağı, bilinen sınırları.

**Kabul kriterleri:**
- [ ] Depoda tek bir çalıştırılabilir legacy dosya var
- [ ] `python -m legacy.mcgurk_legacy` hatasız çalışıyor, 9 deneme tamamlanıyor
- [ ] Yanıt ekranında video görünmüyor, ses duyulmuyor
- [ ] Launcher X ile kapatılınca çökmüyor
- [ ] ESC her aşamada çalışıyor
- [ ] CSV çıktısında seed ve anonim kod var
- [ ] `pip install -r requirements.txt` temiz bir venv'de çalışıyor

**Manuel test:** ekran gerektirir. `TEST_ADIM_0.md`.

---

### ADIM 1 — Proje iskeleti

**Yapılacaklar:**
- Paket yapısı: `mcgurk/` altında `config/`, `db/`, `engine/`, `modules/`, `analysis/`, `ui/`.
- Pydantic config modeli + doğrulama + mod bazlı ek kontroller (şema §G'de).
- SQLite şeması ve veri erişim katmanı. Tablolar: `participants`, `calibrations`, `sessions`, `blocks`, `trials`, `responses`. Analiz için düz tablo veren bir `VIEW`.
  - `participants`: anonim kod, grup (`SSD_R`/`SSD_L`/`CTRL`), yaş, cinsiyet, **deprivasyon süresi**, PTA sağ/sol, postlingual bayrağı
  - `sessions`: seed, config snapshot, PsychoPy sürümü, OS, ses backend, ölçülen yenileme hızı, `system_av_offset_ms`, kalibrasyon referansı, durum, git commit
  - `trials`: tasarım alanları + gerçekleşen zamanlama alanları
  - `responses`: ham yanıt, kategori, iki farklı RT referansı
  - WAL modu, `PRAGMA foreign_keys = ON`
- **Yedekleme katmanı.** 12 aylık bir çalışmada tek SQLite dosyası kabul edilemez risk.
  - `db.backup()`: `VACUUM INTO 'backups/mcgurk_<ISO8601>.sqlite'`. Ham dosya kopyalama **kullanma** — WAL modunda tutarsız kopya üretir.
  - Her oturum kapanışında otomatik çağrılır (`aborted` durumunda da).
  - `tools/verify_backup.py`: bir yedeği açar, tablo bütünlüğünü ve katılımcı/deneme sayılarını doğrular. Test edilmemiş yedek yedek değildir.
  - `.gitignore`: `data/`, `backups/`, `*.sqlite*`, `raw_recordings/`
  - README'ye 3-2-1 kuralı ve haftalık harici kopya notu. Kod↔kimlik eşleşme dosyası bulut senkronizasyonuna konulmaz (KVKK).
- Yapılandırılmış loglama (dosya + konsol, farklı seviyeler).
- `pytest` altyapısı, `pyproject.toml`, `ruff` + `mypy` yapılandırması.
- CI: lint + test (GitHub Actions).

**Kabul kriterleri:**
- [ ] `pytest` yeşil, config ve DB için anlamlı test kapsamı
- [ ] Geçersiz config açık hata mesajı veriyor
- [ ] `data_collection` modunda eksik kalibrasyon → başlatma reddediliyor
- [ ] DB oluşturuluyor, yabancı anahtar kısıtları çalışıyor
- [ ] Oturum kapanışında yedek üretiliyor; `verify_backup.py` yedeği doğruluyor (test)
- [ ] `ruff check` ve `mypy` temiz

**Manuel test:** ekran gerekmez.

---

### ADIM 2 — Uyaran hazırlama ve kalite kontrol

**Yapılacaklar:**
- `tools/prepare_stimuli.py`:
  - Ham videodan **sessiz** video üret (CFR, hedef fps config'ten, 29.97→30 dönüşümü).
  - Ses kanalını **48 kHz 24-bit PCM WAV** olarak çıkar.
  - Her token'ın akustik patlama anını otomatik ölç (1 ms çözünürlük, zarf tabanlı).
  - **Hizalama:** Vis-X videosuna monte edilecek her ses, X'in **kendi orijinal patlama gecikmesine** hizalanır. Global tek hedefe zorlama YAPMA — her video kendi doğal ilişkisini korur. (Bunun nedeni: kaynak kayıt zaten senkron; görsel jestin nerede başladığını ölçmeye gerek yok, X'in orijinal ses kanalı o bilgiyi zaten taşıyor.)
  - Token'ları eşit konuşma-aktif RMS'e normalize et (tüm dosya RMS'i değil; dosyaların %43'ü sessizlik, fark ~7 dB).
  - Korpusun uzun dönem ortalama spektrumundan (LTAS) **konuşma şekilli gürültü** üret.
  - `manifest.json`: her uyaran için yol, süre, fps, patlama anı, seviye, QC sonucu.
  - Tolerans dışı durumda **hata verip çık**, sessizce geçme.
- `tools/verify_stimuli.py`: mevcut uyaran setini denetle, rapor bas.

**Kabul kriterleri:**
- [ ] 8 konuşmacı × 3 token pipeline'dan geçiyor
- [ ] Manifest'teki patlama anları bağımsız ölçümle uyuşuyor
- [ ] Üretilen videolarda ses akışı **yok** (`ffprobe` ile doğrula)
- [ ] SSN'in LTAS'ı korpusunkiyle eşleşiyor (test)
- [ ] Bozuk/hizasız girdi verildiğinde pipeline hata veriyor (test)

**Manuel test:** üretilen WAV'ları dinle, videoları izle, manifest'i incele.

---

### ADIM 3 — A/V senkron çekirdeği

**Yapılacaklar:**
- `engine/av_presenter.py`:
  - `TrialSpec` (video, ses, SOA, kulak, SNR, token'lar) ve `TimingRecord` (nominal/gerçekleşen SOA, onset'ler, kare istatistikleri).
  - `prepare()` / `present()` ayrımı — hazırlık deneme arasında, sunumda G/Ç yok.
  - Ses zamanlaması: ortak patlama anı üzerinden hesap. Video yalnızca flip ızgarasında başlayabilir; ses örnek hassasiyetinde planlanır. **Tüm SOA manipülasyonu ses tarafında yapılır.**
  - Negatif SOA'da ses videodan önce başlamalı — yeterli pay hesabı.
  - `system_av_offset_ms` telafisi.
  - Video kendi süresi boyunca oynar, sabit süre yok.
  - Sunum sonrası ekran temizlenir.
  - A-only (video yok) ve V-only (ses yok) yolları.
- `engine/audio.py`: SNR karıştırma (aktif RMS üzerinden), lateralizasyon (stereo kanal), kalibrasyon trim uygulaması.
- `engine/window.py`: pencere kurulumu, gerçek yenileme hızı ölçümü, kare aralığı kaydı.
- **`tools/timing_selftest.py` — mimarinin doğrulama aracı.** Üç kademe, ayrı çalıştırılabilir (`--level 1|2|3`):
  1. **Donanımsız.** `sound.audioLib` gerçekten `'ptb'` mi; PTB makul çıkış gecikmesi raporluyor mu; planlanan ve gerçekleşen flip zamanları tutuyor mu; N sesi geleceğe planla, hiçbirinin düşmediğini doğrula. Hiçbir kablo gerektirmez.
  2. **Loopback (bir kablo).** Kulaklık çıkışı → ses girişi. Klik dizisi çalıp kaydı analiz eder, jitter raporlar. **Mimari riskin asıl testi:** PTB sessizce geri düşerse veya `when=` yok sayılırsa burada ortaya çıkar.
  3. **Fotodiyot.** Ekran tarafını da kapsar, mutlak `D` değerini verir. `01_av_gecikme_olcumu.md` scriptleri kullanılır; **yeniden yazma.**

  Kademe 1 ve 2 bu adımda çalıştırılır. **Kademe 3 tüm kod bittikten sonra yapılır** — mutlak `D` modüllerin mimarisini etkilemez, config'e yazılan tek sayıdır.

**Kabul kriterleri:**
- [ ] SOA hesabı birim testleriyle doğrulanmış (sentetik zaman damgalarıyla, PsychoPy'sız)
- [ ] PTB yüklenemezse program açık hatayla çıkıyor
- [ ] `timing_selftest.py --level 1` her makinede çalışıyor ve backend'i doğruluyor
- [ ] `timing_selftest.py --level 2` jitter raporu üretiyor
- [ ] SNR ve lateralizasyon fonksiyonları test kapsamında
- [ ] Kare düşmesi tespiti çalışıyor
- [ ] `system_av_offset_ms` `null` iken `development` modunda çalışıyor, `data_collection` modunda reddediyor

**Manuel test:** ekran + ses gerektirir. `TEST_ADIM_3.md` kademe 1 ve 2'yi kapsasın. Kademe 3 için "bu ölçüm tüm kod bittikten sonra yapılacak" notu düşsün.

---

### ADIM 4 — Modül 1: McGurk

**Yapılacaklar:**
- `modules/mcgurk.py`: config'teki `av_pairs` × `noise_conditions` × `ears` × `reps` çaprazlamasından deneme listesi üret.
- Blok yapısı ve randomizasyon (seed'e bağlı, yeniden üretilebilir).
- Yanıt toplama: config'teki `response_set`'ten buton ızgarası. Yanıt **klavye** ile (RT hassasiyeti); fare opsiyonel ve ayrı loglanır.
- `DIGER` seçildiğinde serbest metin alanı.
- İki RT referansı kaydedilir: akustik patlamadan ve yanıt ekranından itibaren.
- Yanıt kategorizasyonu: `AUDITORY` / `VISUAL` / `FUSION` / `COMBINATION` / `OTHER` / `NONE`.
  - Füzyon ve kombinasyon haritaları **config'ten** gelsin, koda gömülmesin.
- Zaman aşımı yönetimi.

**Kabul kriterleri:**
- [ ] Config'teki AV çiftleri değiştirilince deneme listesi değişiyor (test)
- [ ] Aynı seed → aynı deneme sırası (test)
- [ ] Kategorizasyon tablosu testlerle doğrulanmış; Vis-ga/Aud-ba/"DA" → `FUSION`
- [ ] Deneme sayısı ve süre tahmini config'ten doğru hesaplanıyor
- [ ] Tüm denemeler DB'ye zamanlama kayıtlarıyla yazılıyor

**Not:** Deneme sayıları/AV çiftleri henüz kesinleşmedi (§F.1). Kod config'ten gelen her tasarımı desteklesin; sayıyı sabitleme.

---

### ADIM 5 — Modül 2: AVSR

**Yapılacaklar:**
- `modules/avsr.py`: `presentation_modes` (A/V/AV) × `stimulus_sets` × `noise_conditions` × `ears`.
- **Uyaran seti veri odaklı olmalı.** Hece seti bugün çalışır; kelime seti config'te `enabled: false`. Kayıt geldiğinde bayrak açılır ve manifest'e satır eklenir — **kod değişmez.**
- `config/word_lists/` şeması ve örnek/şablon dosya (boş).
- Doğruluk skorlaması (Modül 1'den farklı: burada doğru cevap **vardır**).
- `response_mode: closed_set` bugün çalışsın; `open_set` için arayüz tanımlansın ama net `NotImplementedError` versin.
- V-only'de ses yok, A-only'de video yok — motorun bu yollarını kullan.
- **V-only hücrelerini gürültü ve kulakla ÇAPRAZLAMA** (V-only'de ses yok, ikisi de anlamsız). Bu Modül 2 deneme sayısını önemli ölçüde azaltır.

**Kabul kriterleri:**
- [ ] Üç sunum modu da mevcut hece uyaranlarıyla çalışıyor
- [ ] Kelime seti `enabled: true` yapıldığında manifest'te karşılığı yoksa açık hata veriyor
- [ ] Görsel fayda indeksi (AV − A) ve lipreading (V) hesabı test kapsamında
- [ ] `open_set` seçilirse net `NotImplementedError`
- [ ] V-only gürültü/kulakla çaprazlanmıyor (test)

**Not:** Kelime çekimi henüz yapılmadı (§F.2, ayrıntı `04_kod_disi_isler.md` §2). Şema hazır, içerik boş.

---

### ADIM 6 — Modül 3: TBW

**Yapılacaklar:**
- `modules/tbw.py`: sabit uyaranlar yöntemi (method of constant stimuli), config'teki SOA listesi.
- İki alternatifli eşzamanlılık yargısı.
- Gauss psikometrik fonksiyon uydurma → PSS, sigma, TBW (FWHM = 2.355σ).
- Bootstrap güven aralıkları.
- **TBW tanımını config'e yaz ve rapora bas** (FWHM mi, ±1σ mı) — literatürde farklı tanımlar var.
- Gerçekleşen SOA kaydı: nominal ile arasındaki fark analiz aşamasında kullanılacak.

**Kabul kriterleri:**
- [ ] Bilinen parametreli simüle veriden PSS ve TBW doğru kestiriliyor (test)
- [ ] Uydurma başarısız olursa (yetersiz veri, dejenere eğri) açık hata veriyor
- [ ] Gerçekleşen SOA her denemede kaydediliyor

---

### ADIM 7 — Modül 4: Oddball

**Yapılacaklar:**
- `modules/oddball.py`: config'ten standart/hedef frekans, olasılık, ISI aralığı.
- Ton üretimi: rampa uygulanmış, klik yok.
- **Ardışık hedef kısıtı:** iki hedef arasında en az N standart (config'ten).
- Tuş basımı toplama, RT, isabet / yanlış alarm / kaçırma.
- Süre ~5–6 dakika (config'ten deneme sayısıyla, hesaplanıp yazdırılır).

**Kabul kriterleri:**
- [ ] Hedef oranı config'tekiyle eşleşiyor (test)
- [ ] Ardışık hedef kısıtı uygulanıyor (test)
- [ ] d′ ve kriter hesabı test kapsamında
- [ ] Ton dosyalarında klik yok (onset/offset rampası doğrulanmış)

---

### ADIM 8 — Oturum akışı ve arayüz

**Yapılacaklar:**
- Katılımcı giriş ekranı: **anonim kod**, grup, yaş, cinsiyet, deprivasyon süresi, PTA sağ/sol. Ad/soyad alanı **yok**.
- **`python -m mcgurk.checklist` komutu.** Operatörün her oturum öncesi çalıştıracağı, Python bilmeyen birinin okuyabileceği YEŞİL/KIRMIZI çıktı:
  - Config geçerli mi, mod `data_collection` mı
  - `system_av_offset_ms` dolu mu, ölçüm tarihi ne
  - Kalibrasyon dosyası var mı, **30 günden eski mi** (eskiyse KIRMIZI)
  - Ses backend gerçekten PTB mi, aygıt bekleneni mi
  - Ölçülen yenileme hızı config'teki `expected_refresh_hz` ile uyuşuyor mu
  - Uyaran manifest'i eksiksiz mi, dosyalar yerinde mi
  - Disk alanı ve yedek klasörü yazılabilir mi
  - Son yedeğin tarihi

  Herhangi bir satır KIRMIZI ise `data_collection` modunda oturum başlatılamaz.
- Oturum öncesi kontrol listesi ekranı: yukarıdaki çıktı arayüzde de görünsün, operatör onaylasın.
- Yönerge ekranları (metinler config'ten, Türkçe).
- **Alıştırma bloğu** ve anlama kontrolü.
- **Çapraz dinleme kontrolü.** SSD katılımcılarında, sağır kulağa sunumda basit tespit görevi (ses var/yok, ~20 deneme). Şans düzeyi beklenir; üstündeyse ses kafatası yoluyla iyi kulağa ulaşıyor ve lateralizasyon geçersiz demektir. Sonuç DB'ye yazılır, QC raporunda görünür. Config'ten açılıp kapanabilir. (Gerekçe: §F.3.)
- Modül sıralaması config'ten; molalar.
- İlerleme göstergesi (operatöre, katılımcıya değil).
- Kesinti/devam: oturum yarıda kalırsa DB durumu `aborted`, kaldığı yerden devam edebilme.
- Acil çıkış her aşamada.

**Kabul kriterleri:**
- [ ] Tam oturum baştan sona çalışıyor
- [ ] Kesip devam ettirme çalışıyor, veri kaybı yok
- [ ] `mcgurk.checklist` eksik/eski kalibrasyonda KIRMIZI veriyor ve oturumu engelliyor (test)
- [ ] Çapraz dinleme kontrolü çalışıyor, sonucu DB'ye yazılıyor
- [ ] Katılımcıya gösterilen hiçbir metin koda gömülü değil

---

### ADIM 9 — Analiz, dışa aktarım ve entegrasyon

**Yapılacaklar:**
- `analysis/export.py`: DB → pandas → CSV/parquet.
- `analysis/measures.py`: Modül 1 oranları, Modül 2 fayda indeksleri, Modül 3 PSS/TBW, Modül 4 d′.
- `analysis/qc_report.py`: oturum kalite raporu — düşen kare sayısı, SOA sapmaları, zaman aşımı oranı, yanıt dağılımı. **Bozuk denemeler nesnel ölçütle işaretlensin**, post-hoc gerekçe uydurulmasın.
- Uçtan uca entegrasyon testi: sahte katılımcı, tüm modüller, DB'den analiz çıktısına kadar.
- **Başarısızlık modu testleri.** Her biri **açık hata** vermeli, sessizce bozulmamalı:
  - Oturum ortasında kesme → DB durumu `aborted`, veri korunuyor, devam edilebiliyor
  - Yanıt verilmemesi → zaman aşımı, kayda `NONE`
  - Uyaran dosyası eksik → başlatmadan önce yakalanıyor
  - Ses aygıtı kayboluyor → açık hata
  - Disk dolu → açık hata
- `README.md` güncellemesi: kurulum, kalibrasyon adımları, oturum yürütme, analiz.
- `docs/PROTOKOL.md`: yöntem dokümanı ile kod arasındaki eşleme tablosu.
- **`docs/OPERATOR_SOP.md` taslağı.** README geliştirici içindir; bu belge oturumu yürüten kişi içindir, Python bilgisi varsaymaz. Şu bölümleri iskele olarak oluştur, içeriği kullanıcı dolduracak:
  - Oturum öncesi kontrol listesi (`mcgurk.checklist` çıktısına bağlı)
  - Katılımcı karşılama ve kulaklık yerleşimi
  - **Ne söylenir / ne söylenmez** — McGurk etkisi katılımcıya oturum bitmeden ASLA anlatılmaz (talep karakteristiği)
  - Oturum sırasında operatör davranışı
  - Oturum sonrası: QC raporu, yedek, debriefing
  - Sorun giderme tablosu

**Kabul kriterleri:**
- [ ] Uçtan uca test geçiyor
- [ ] Başarısızlık modu testleri geçiyor
- [ ] QC raporu anlamlı çıktı veriyor
- [ ] Yöntem dokümanındaki her bağımlı değişkenin kod karşılığı var
- [ ] Yeni bir makinede README takip edilerek kurulum yapılabiliyor
- [ ] **Prova oturumu kapısı:** gerçek bir kişiyle, SOP takip edilerek, baştan sona tam oturum koşulmuş; süre ölçülmüş; QC raporu incelenmiş. Otomatik uçtan uca test bunun yerine geçmez. `TEST_ADIM_9.md` bu oturumun adımlarını ve kasıtlı bozma senaryolarını içersin (ayrıntı: `04_kod_disi_isler.md` §5).

**Bu adım bittiğinde kod tarafı tamamlanmış olur.** Geriye kalan: fotodiyot ölçümü (`01`), kalibrasyon (`02`), ve kod dışı işler (`04`: tasarım kararı, kelime çekimi, prova, pilot).

---

## §D. Manuel test dosyası şablonu

Her adımda `TEST_ADIM_N.md` bu formatta:

```markdown
# Adım N Manuel Test

## Ön koşullar
- [ ] ...

## Test 1: <ne test ediliyor>
**Komut:**
```bash
...
```
**Beklenen çıktı:**
```
...
```
**Kontrol edilecek:** ...
**Başarısızsa:** ...

## Test 2: ...

## Ekran/ses gerektiren testler
(PsychoPy penceresi açan testler burada toplanır)

## Kabul kriterleri
- [ ] ...
```

Testler somut olsun: komut, beklenen çıktı, neye bakılacağı. Belirsiz adım yazma.

---

## §E. progress.md şablonu

İlk çalıştırmada bu dosyayı oluştur. Her adım kapanışında güncelle.

```markdown
# İlerleme Raporu — McGurk / SSD Platformu

Son güncelleme: <tarih>
Aktif adım: <N>

## Durum tablosu

| Adım | Başlık | Durum | Tarih | Commit |
|---|---|---|---|---|
| 0 | Baseline düzeltme | BEKLİYOR | | |
| 1 | Proje iskeleti | BEKLİYOR | | |
| 2 | Uyaran hazırlama | BEKLİYOR | | |
| 3 | A/V senkron çekirdeği | BEKLİYOR | | |
| 4 | Modül 1: McGurk | BEKLİYOR | | |
| 5 | Modül 2: AVSR | BEKLİYOR | | |
| 6 | Modül 3: TBW | BEKLİYOR | | |
| 7 | Modül 4: Oddball | BEKLİYOR | | |
| 8 | Oturum akışı ve arayüz | BEKLİYOR | | |
| 9 | Analiz ve entegrasyon | BEKLİYOR | | |

Durum değerleri: BEKLİYOR / PLAN ONAYINDA / GELİŞTİRİLİYOR / TESTTE / TAMAMLANDI

## Adım kayıtları

### Adım 0 — <başlık>
- **Durum:** BEKLİYOR
- **Tamamlanma:** —
- **Commit:** —
- **Ne yapıldı:** (adım bitince doldur)
- **Alınan kararlar:** (örn. hangi main dosyası seçildi ve neden)
- **Bilinen sınırlar:** (bu adımda çözülmeyen, sonraki adıma taşınan)
- **Sonraki adıma not:** 

### Adım 1 — ...
(aynı yapı, her adım için)

## Açık kararlar (kullanıcı + danışman verecek)
Bunlar §F'den gelir. Karşılaşıldığında burada işaretlenir, karar gelince güncellenir.
- [ ] Deneysel tasarım / deneme sayıları (Adım 4'ten önce netleşmeli)
- [ ] Modül 2 kelime listesi (Adım 5, çekim gerekiyor)
- [ ] Kulaklık tipi (donanım, çapraz dinleme kontrolünü etkiler)
- [ ] Konuşmacı seçim stratejisi

## Kullanıcıya bekleyen aksiyonlar
(Claude'un ilerlemek için kullanıcıdan beklediği şeyler buraya)
```

**Kural:** `progress.md` her zaman gerçeği yansıtsın. Bir adım yarıda kalırsa durumu doğru işaretle ki sonraki oturum kaldığın yeri bulabilsin.

---

## §F. Bilinen açık kararlar

Bunlar henüz netleşmedi. Karşılaşınca **varsayım yapıp devam etme, sor** ve `progress.md`'de işaretle:

1. **Deneme sayıları.** Config'teki değerler örnektir. Tam faktöriyel tasarım 720+ deneme eder, bir oturuma sığmaz. Kullanıcı danışmanıyla karar verecek. Kod, config'ten gelen her tasarımı desteklemeli ve **tahmini süreyi hesaplayıp yazdırmalı** — karar bu çıktıya bakarak verilecek. (Ayrıntılı seçenekler: `04_kod_disi_isler.md` §1.)

2. **Modül 2 kelime listesi.** Kayıt seansı yapılmadı. Şema hazır olsun, içerik boş. (Çekim kılavuzu: `04_kod_disi_isler.md` §2.)

3. **Kulaklık tipi.** Kulak üstü kulaklıkta kulaklar arası zayıflama ~40 dB; SSD'de sağır kulağa sunumda ses iyi kokleaya ulaşıp lateralizasyon manipülasyonunu geçersiz kılabilir. Insert kulaklık (~70 dB) gerekebilir. Donanım kararı ama koda etkisi var: **her katılımcıda sağır kulağa sunumda çapraz dinleme kontrolü** çalışmalı (Adım 8). (Ayrıntı: `02_kalibrasyon.md` §9.)

4. **Konuşmacı seçimi.** 8 konuşmacı var, oturumda biri kullanılıyor. Katılımcılar arası sabit mi, dengelenecek mi, randomize mi — belirsiz. Config'ten gelsin, üç strateji de desteklensin.

---

## §G. Config şeması

`config/experiment.yaml` — tek doğruluk kaynağı. Aşağıdaki iskelet asgarî kapsamdır; eksik gördüğün alanı ekle, gerekçeni yaz.

```yaml
experiment:
  name: mcgurk_ssd
  version: 1.0.0
  mode: development          # development | data_collection

paths:
  stimuli: stimuli/
  data: data/
  logs: logs/

timing:
  # 01_av_gecikme_olcumu.md ölçümünden gelir. Kod bitene kadar null.
  # data_collection modunda null ise program başlamaz.
  system_av_offset_ms: null
  measured_on: null
  audio_latency_mode: 3
  lead_frames: 6
  dropped_frame_tolerance: 1.5

display:
  fullscreen: true
  screen: 0
  size: [1920, 1080]
  background: black
  video_position: [0, 0]     # merkez — değiştirme
  expected_refresh_hz: 60

audio:
  sample_rate: 48000
  target_spl_db: 65.0
  # 02_kalibrasyon.md çıktısı. Kod bitene kadar null. data_collection'da zorunlu.
  calibration_file: config/kalibrasyon.json

session:
  module_order: [practice, mcgurk, avsr, tbw, oddball]
  break_every_n_trials: 60
  break_duration_s: 30
  practice_trials: 12

# ---- AV ÇİFTİ SEÇİMİ: deneysel tasarımın merkezi ----
modules:
  mcgurk:
    enabled: true
    speaker_id: 1
    av_pairs:
      - {visual: ga, audio: ba, label: fusion_pair,      reps: 20}
      - {visual: ba, audio: ga, label: combination_pair, reps: 20}
      - {visual: ba, audio: ba, label: congruent_ba,     reps: 10}
      - {visual: da, audio: da, label: congruent_da,     reps: 10}
      - {visual: ga, audio: ga, label: congruent_ga,     reps: 10}
    noise_conditions: [null, 5.0]     # null = sessiz, sayı = SNR dB
    ears: [left, right]
    response_set: [BA, DA, GA, TA, PA, KA, BGA, DIGER]
    response_timeout_s: 5.0
    randomization: block_shuffle
    # kategorizasyon haritaları — koda gömülmez
    fusion_map:
      "ga|ba": [da, ta]
      "ga|pa": [ta, ka]
    combination_map:
      "ba|ga": [bga, bda]
      "ba|da": [bda]

  avsr:
    enabled: true
    speaker_id: 1
    stimulus_sets:
      - {type: syllable, tokens: [ba, da, ga], reps: 10, enabled: true}
      # Kayıt geldiğinde açılacak. Kod değişmeyecek.
      - {type: word, list: config/word_lists/tr_pb_50.yaml, reps: 1, enabled: false}
    presentation_modes: [A, V, AV]
    noise_conditions: [null, 5.0]
    ears: [left, right]
    response_mode: closed_set          # closed_set | open_set
    response_timeout_s: 6.0

  tbw:
    enabled: true
    speaker_id: 1
    stimulus: {visual: ba, audio: ba}
    soa_values_ms: [-300, -250, -200, -150, -100, -50, 0, 50, 100, 150, 200, 250, 300]
    reps_per_soa: 15
    ears: [both]
    tbw_definition: fwhm               # fwhm | sigma1 — rapora yazılır
    response_labels: {same: "Aynı anda", different: "Farklı zamanda"}
    response_timeout_s: 4.0

  oddball:
    enabled: true
    standard_hz: 1000
    target_hz: 1500
    target_probability: 0.18
    min_standards_between_targets: 2
    n_trials: 300
    tone_duration_ms: 50
    tone_ramp_ms: 10
    isi_ms: [900, 1100]
    ears: [both]
    response_key: space

speaker_selection:
  strategy: fixed      # fixed | balanced | random
  fixed_id: 1

cross_hearing_check:
  enabled: true
  n_trials: 20
```

**Config kuralları:**
- Şema **Pydantic** ile doğrulanır. Bilinmeyen alan → hata. Eksik zorunlu alan → hata.
- `data_collection` modunda ek doğrulamalar: `system_av_offset_ms` dolu, `calibration_file` var ve okunabilir, `fullscreen: true`.
- Config, oturum başında **olduğu gibi** DB'ye yazılır (`sessions.config_snapshot`). Sonradan config değişse bile hangi ayarla toplandığı belli olur.
- Toplam deneme sayısı ve tahmini süre config yüklendiğinde hesaplanıp yazdırılır. Bu, tasarım kararını verirken kullanıcının aracıdır.

---

## §H. Şimdi ne yap

1. `progress.md` yoksa §E'den oluştur.
2. Depoyu incele, §C Adım 0'daki tespitleri doğrula, ek bulduklarını listele.
3. **Adım 0 planını sun** (§B.1) — dosya listesi, kararlar, belirsizlikler, test stratejisi.
4. Onay bekle.
