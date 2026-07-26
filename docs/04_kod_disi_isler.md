# Kod Dışında Kalan İşler

Yazılım bittiğinde platform hazır olmaz. Bu doküman aradaki farkı kapatır.

Altı iş var. Üçü karar, üçü prosedür. Hiçbiri kodla çözülmez.

| # | İş | Ne zaman | Kim | Süre |
|---|---|---|---|---|
| 1 | Deneysel tasarım kararı | Faz 4'ten önce | Siz + danışman | 1 toplantı |
| 2 | Modül 2 kelime çekimi | Faz 5'ten önce başlasın | Siz + konuşmacı | 1 gün + kurgu |
| 3 | Yedekleme düzeni | Faz 1'de | Siz | 2 saat |
| 4 | Operatör kılavuzu (SOP) | Faz 8'de | Siz | 3 saat |
| 5 | Prova oturumu | Kod bitince | Siz + 1 kişi | Yarım gün |
| 6 | Pilot çalışma | Kalibrasyondan sonra | Siz + 5–10 kişi | 1–2 hafta |

---

## 1. Deneysel tasarım kararı

### Sorun

Yöntem dokümanındaki tasarımı olduğu gibi uygularsanız oturum bir katılımcının tolere edebileceğinden uzun sürer. Küçültmeniz gerekiyor — ama neyi keseceğiniz bilimsel bir karar.

**Tam faktöriyel Modül 1:**

```
3 görsel × 3 işitsel × 2 gürültü × 2 kulak = 36 hücre
36 × 20 tekrar = 720 deneme
720 × 5.1 saniye ≈ 61 dakika
```

Sadece Modül 1 için bir saat. Üstüne üç modül daha binecek. Sığmaz.

### Deneme süresi nereden geliyor

Bir McGurk denemesinin bileşenleri:

| Aşama | Süre |
|---|---|
| Fiksasyon (+ işareti) | 500 ms |
| Uyaran (video) | ~2600 ms |
| Yanıt penceresi (ortalama) | ~1200 ms |
| Denemeler arası boşluk | 800 ms |
| **Toplam** | **~5100 ms** |

Bu sayı tasarım hesabınızın temel birimi. Pilotta ölçüp güncelleyin.

### Ne kesilebilir

**Bilgi taşımayan AV çiftlerini atın.** 3×3 çaprazlamanın dokuz hücresinin hepsi eşit değerde değil:

| Çift | Ne ölçüyor | Tutulmalı mı |
|---|---|---|
| Aud-/ba/ + Vis-/ga/ | **Füzyon** — klasik McGurk | Kesinlikle |
| Aud-/ga/ + Vis-/ba/ | **Kombinasyon** algısı | Kesinlikle |
| Uyumlu çiftler (ba-ba, da-da, ga-ga) | Kontrol: uyaran duyulabilir mi | Evet, ama az tekrarla |
| Aud-/da/ + Vis-/ba/ vb. | Zayıf veya öngörülemeyen etki | Atılabilir |

Uyumlu denemeler **kontroldür.** İşlevleri "katılımcı uyaranı doğru duyabiliyor mu" sorusunu cevaplamak. Bunun için 20 tekrar gerekmez, 10 yeter — çünkü beklenen doğruluk %95+ ve tavan etkisi var, varyans zaten düşük.

Uyumsuz denemeler **asıl ölçümdür.** Beklenen oran %50 civarında olabilir, varyans maksimum. Tekrar sayısı burada kritik.

### Tekrar sayısı neden önemli

Her katılımcının füzyon oranı bir oran kestirimidir. Kestirimin belirsizliği tekrar sayısına bağlı:

| Tekrar | Kişi başı standart hata (p≈0.5) |
|---|---|
| 5 | 0.22 |
| 10 | 0.16 |
| 20 | 0.11 |
| 30 | 0.09 |
| 50 | 0.07 |

Mevcut kodda **tekrar = 1**. Kişi başı oran ya 0 ya 1 çıkar; hiçbir istatistik anlamlı olmaz.

20'nin altına inmeyin. 30'un üstüne çıkmanın getirisi azalır çünkü o noktadan sonra **kişiler arası** değişkenlik baskın gelir — McGurk etkisinde bireysel farklar çok büyüktür, bazı insanlar hiç etkilenmez, bazıları her denemede etkilenir.

### Modül 2'de mantıksal tasarruf

Modül 2'de üç sunum modu var: A-only, V-only, AV. Burada gözden kaçan bir nokta var:

**V-only koşulunda ses yoktur.** Dolayısıyla:
- Gürültü koşulu anlamsız (gürültü de sestir)
- Kulak koşulu anlamsız (hiçbir kulağa bir şey verilmiyor)

Yani V-only hücrelerini gürültü ve kulakla çaprazlamayın. Bu tek başına Modül 2'nin dörtte birini siler.

### Üç seçenek

**A — Asgarî (tek oturum, ~60 dk)**

| Modül | Hücreler | Deneme | Süre |
|---|---|---|---|
| 1 McGurk | 2 uyumsuz × 20 + 3 uyumlu × 10 = 70, × 2 gürültü × 2 kulak | 280 | 24 dk |
| 2 AVSR | Yalnızca hece, gürültü koşulu tek (sadece gürültülü) | 150 | 13 dk |
| 3 TBW | 9 SOA × 12 tekrar | 108 | 8 dk |
| 4 Oddball | 250 deneme | 250 | 4 dk |
| | | | **49 dk** |
| + yönerge, alıştırma, molalar | | | **~65 dk** |

**B — Orta (tek uzun oturum, ~95 dk)**

| Modül | Deneme | Süre |
|---|---|---|
| 1 McGurk (yukarıdaki gibi) | 280 | 24 dk |
| 2 AVSR: A ve AV × 2 gürültü × 2 kulak × 3 token × 10 = 120+120, V-only 3 × 10 = 30 | 270 | 23 dk |
| 3 TBW: 13 SOA × 15 | 195 | 14 dk |
| 4 Oddball | 300 | 5 dk |
| | | **66 dk** |
| + yönerge, alıştırma, 4 mola, kurulum | | **~95 dk** |

**C — Tam (iki oturum)**

Yöntem dokümanına en yakın. Oturum 1: Modül 1 + oddball. Oturum 2: Modül 2 + 3 + oddball tekrarı. Her biri ~60 dk.

Avantajı: yorgunluk etkisi az, daha çok tekrar. Dezavantajı: katılımcı kaybı riski iki katına çıkar (klinik popülasyonda ikinci randevuya gelmeme oranı yüksektir), 60 kişi × 2 randevu lojistik yük.

### Karar için toplantı gündemi

Danışmanınıza götüreceğiniz sorular:

1. Hangi AV çiftleri **hipotez açısından** zorunlu? (füzyon ve kombinasyon dışında bir şey var mı)
2. Gürültü koşulu her modülde gerekli mi, yoksa sadece Modül 1'de mi?
3. Uzamsal yön (sağ/sol) her modülde gerekli mi? TBW'de anlamlı mı?
4. Tek oturum mu, iki oturum mu? Klinik popülasyonda ikinci randevu gerçekçi mi?
5. Uyumlu kontroller kaç tekrar?

**Toplantıya bu tabloyla gidin.** "Ne yapalım" diye sormak yerine "şu üç seçenek var, hangisi" diye sormak kararı hızlandırır.

Karar verildiğinde config'teki `av_pairs`, `reps`, `noise_conditions`, `ears` alanlarını doldurursunuz. Kod değişmez.

---

## 2. Modül 2 kelime çekimi

### Neden gerekli

Yöntem dokümanı 6.2: "Fonem/hece **ve tek heceli fonetik dengeli Türkçe kelimeler**". Elinizde sadece /ba/ /da/ /ga/ var. Hece kısmı bugün çalışır, kelime kısmı çekim gerektirir.

### "Fonetik dengeli" ne demek

Bir kelime listesinin fonetik dengeli olması, listedeki seslerin dağılımının **o dildeki doğal konuşmanın ses dağılımına** benzemesi demektir. Yani liste, dilin tipik bir örneklemi olur.

Neden önemli: eğer listeniz tesadüfen çok fazla yüksek frekanslı ünsüz içeriyorsa, işitme kaybı olan katılımcılar (yüksek frekans kaybı yaygındır) yapay olarak düşük skor alır. Denge bunu önler.

**Bu listeleri siz üretmeyin.** Türkçe konuşma odyometrisinde kullanılan standartlaştırılmış listeler var. Odyoloji bölümünüzde hangisinin kullanıldığını sorun — klinik rutinde zaten kullanılıyordur. Danışmanınız hangi listeyi kullanacağınıza karar versin.

### Konuşmacı

**Fonem uyaranlarınızdaki konuşmacılardan birini kullanın.** Farklı konuşmacı kullanırsanız Modül 1 ile Modül 2 arasındaki karşılaştırma konuşmacı farkıyla karışır.

Bulamıyorsanız (kaynak veri seti dışarıdan geldiyse), yeni bir konuşmacıyla çekin ama bunu yöntem bölümünde belirtin ve mümkünse Modül 1'i de aynı konuşmacıyla tekrarlayın.

Konuşmacı özellikleri:
- Anadili Türkçe
- Standart İstanbul Türkçesi telaffuzu (bölgesel aksan konuşma tanımayı etkiler)
- Net artikülasyon, abartısız
- Sakal/bıyık **yok** — dudak hareketini gizler, lipreading koşulunu bozar
- Gözlük tercihen yok (yansıma)

### Çekim kurulumu

**Kamera:**
- Sabit tripod, hareket yok
- Yüz kareyi doldursun ama çene ve alın kesilmesin
- Göz hizası, hafif yukarıdan veya aşağıdan değil
- Kare hızı: **50 veya 60 fps** (30'dan iyi — görsel olayın zamansal çözünürlüğü artar; sonra 30'a indirebilirsiniz ama tersi mümkün değil)
- Çözünürlük: en az 1080p
- Otomatik odak **kapalı** (çekim ortasında odak arayışı görüntüyü bozar)
- Otomatik pozlama **kapalı**

**Işık:**
- Yumuşak, iki taraflı (ağız bölgesinde gölge olmasın)
- Ağız içi görünür olmalı — dilin konumu /ga/ gibi seslerde görsel ipucudur
- Titreşimsiz (LED panel; floresan lamba kamerayla girişim yapabilir)

**Arka plan:**
- Düz, tek renk, dikkat dağıtmayan (açık gri veya yeşil)
- Desen, obje, hareket yok

**Ses:**
- Kondansatör mikrofon, kardioid
- Ağızdan 20–30 cm, **eksen dışında** (patlamalı seslerde hava darbesi mikrofona vurmasın)
- Pop filtresi
- 48 kHz, 24 bit
- Sessiz oda — mümkünse odyoloji bölümünün ses yalıtımlı kabini
- Kayıt seviyesi: tepe −12 dBFS civarı (kırpma yok)

### Senkron — kritik nokta

**Kamera ve mikrofon aynı cihazda kayıt yapmalı**, ya da harici ses kaydı yapılıyorsa her çekimde bir **senkron işareti** (el çırpma) olmalı.

Neden: Modül 2'nin tüm uyaranları AV'dir ve doğal senkronun korunması gerekir. Kamera ve mikrofon ayrı cihazlarsa saatleri sürüklenir; 10 dakikalık bir kayıtta 20–50 ms kayma birikebilir.

En basit çözüm: kameranın kendi mikrofonuyla da kayıt alın (kalitesiz olması önemli değil), sonra kurguda harici sesi ona hizalayın.

### Kayıt protokolü

Her kelime için:

1. Konuşmacı nötr ifadeyle bekler, ağız kapalı
2. **En az 1 saniye** hareketsiz bekleme
3. Kelimeyi söyler
4. Nötr ifadeye döner
5. **En az 1 saniye** hareketsiz bekleme
6. Kes

Kurallar:
- Her kelime için **en az 3 tekrar** çekin, sonra en iyisini seçin
- Baş hareketi yok — konuşmacı bir noktaya sabit baksın
- Göz kırpma kaçınılmaz ama kelime söylenirken olmasın
- Kaş kaldırma, gülümseme gibi ifadeler yok (ek görsel ipucu olur)
- Konuşma hızı ve şiddeti tutarlı olsun

Başta ve sonda 1 saniyelik boşluk şart: uyaran hazırlama pipeline'ı bu boşluğu kullanarak hizalama ve gürültü giriş rampası yapıyor.

### Çekim sonrası

Çekim bittiğinde ham dosyaları `raw_recordings/` altına koyun ve pipeline'ı çalıştırın:

```bash
python tools/prepare_stimuli.py --input raw_recordings/words --output stimuli/words --speaker 1
```

Pipeline her kelimenin akustik patlama anını ölçer, hizalar, normalize eder, manifest'e yazar. Kalite kontrol başarısız olursa hangi kelimenin sorunlu olduğunu söyler — o kelimenin alternatif çekimini kullanın.

Sonra config'te:

```yaml
- {type: word, list: config/word_lists/tr_pb_50.yaml, reps: 1, enabled: true}
```

**Kod değişmez.**

---

## 3. Yedekleme

### Risk

12 ay, 60 katılımcı, tek bir SQLite dosyası. Dosya bozulursa ya da disk giderse çalışma biter. Etik kurul onaylı bir çalışmada veriyi tekrar toplama şansınız yok.

### Üç kural

**3-2-1:** verinin **3** kopyası, **2** farklı ortamda, **1** tanesi fiziksel olarak başka yerde.

### Uygulama

**Oturum sonunda otomatik yedek.** Faz 1'de koda ekleyin:

```sql
VACUUM INTO 'backups/mcgurk_2026-07-21_143022.sqlite';
```

`VACUUM INTO` çalışan veritabanının tutarlı bir kopyasını alır. Dosyayı kopyalamaktan güvenlidir — WAL modunda ham dosya kopyası eksik olabilir.

**Haftalık harici kopya.** Şifreli harici disk veya kurumun sunucusu.

**KVKK notu:** veriniz anonim kodlarla tutulsa bile, kod↔kimlik eşleşme dosyası kişisel veridir. Bunu **asla** bulut senkronizasyonuna koymayın (Dropbox, Google Drive, iCloud). Etik kurul onayınızda veri saklama koşulları yazıyordur — okuyun, uyun.

### Geri yükleme testi

**Yedeği test etmeden yedeğiniz yok.**

Ayda bir: rastgele bir yedeği alın, boş bir klasöre açın, analiz scriptini çalıştırın, beklenen katılımcı sayısını gördüğünüzü doğrulayın. 10 dakika sürer, bir kez işe yaradığında çalışmayı kurtarır.

### Sürüm kontrolü

Kod git'te olsun ama **veri git'te olmasın.** `.gitignore`:

```
data/
backups/
*.sqlite
*.sqlite-wal
*.sqlite-shm
raw_recordings/
```

Uyaranlar için Git LFS veya harici depolama kullanın; 9 MB'lık zip'i repoya koymak yanlıştı.

Her veri toplama oturumunda kullanılan kod sürümü DB'ye yazılıyor (`sessions.git_commit`). Bir yıl sonra "bu veri hangi kodla toplandı" sorusunun cevabı orada olacak.

---

## 4. Operatör kılavuzu (SOP)

### Neden ayrı bir belge

README geliştirici içindir. Oturumu yürüten kişi siz olmayabilirsiniz — bir lisansüstü öğrencisi, bir odyolog, bir asistan olabilir. O kişi Python bilmek zorunda değil.

Ayrıca: **aynı prosedürün her katılımcıda aynı şekilde uygulanması** bilimsel bir gerekliliktir. Yazılı olmayan prosedür her seferinde biraz farklı uygulanır.

### İçerik

**A. Oturum öncesi kontrol listesi**

```
[ ] Bilgisayar açık, başka program çalışmıyor
[ ] Ses arayüzü bağlı, kazanç düğmesi bantlı konumda
[ ] Kulaklık sağlam, doğru jack'te
[ ] Ekran parlaklığı standart konumda
[ ] Oda ışığı standart
[ ] python -m mcgurk.checklist  -> tüm satırlar YEŞİL
[ ] Kalibrasyon tarihi 30 günden eski değil
[ ] Onam formu hazır
```

**B. Katılımcı karşılama**

- Onam alma
- Dahil etme kriterlerinin doğrulanması (odyogram, nörolojik öykü, görme)
- Kulaklık yerleşimi (sağ/sol doğru takıldığından emin olun — **bu çalışmada kritik**)
- Oturma mesafesi ve göz hizası

**C. Ne söylenir, ne söylenmez**

Bu bölüm en önemlisi.

**Söylenmez:**
- McGurk etkisinin ne olduğu
- Bazı videolarda ses ve görüntünün uyuşmadığı
- "Doğru" cevap diye bir şey olduğu
- Katılımcının nasıl performans gösterdiği

Katılımcı manipülasyonu bilirse yanıt stratejisi değişir. Bu **talep karakteristiği** (demand characteristics) denen klasik bir yanlılık kaynağıdır ve verinizi geri dönülmez şekilde bozar.

**Söylenir:**
- Ne duyduğunu bildirmesi (ne gördüğünü değil)
- Emin olmasa da bir seçenek işaretlemesi
- Hızlı ama aceleci olmaması
- İstediği zaman ara verebileceği

Yönerge metinleri config'te. Operatör kendi cümleleriyle açıklamasın, **ekrandaki metni okusun.**

**D. Oturum sırasında**

- Operatör katılımcının arkasında veya yan tarafında dursun, ekranı görmesin
- Yanıtlara tepki vermesin (yüz ifadesi dahil)
- Katılımcı "doğru mu yaptım" diye sorarsa: "Doğru cevap yok, sadece ne duyduğunuzu işaretleyin"
- Mola sırasında deneyle ilgili konuşulmasın

**E. Oturum sonrası**

```
[ ] Veri kaydedildi mi (ekranda onay)
[ ] python -m mcgurk.qc --last-session  -> rapor incelendi
[ ] Düşen kare oranı %1'in altında
[ ] Zaman aşımı oranı %5'in altında
[ ] Yedek alındı
[ ] Katılımcı bilgilendirmesi (debriefing) yapıldı
```

**Debriefing:** oturum bittikten sonra katılımcıya McGurk etkisi anlatılabilir. Etik olarak beklenen budur — katılımcı neye katıldığını öğrenmeli. Ama **oturum bitmeden asla.**

**F. Sorun giderme**

| Durum | Ne yapılır |
|---|---|
| Program çöktü | Oturumu `aborted` olarak kapat, kaldığı yerden devam et |
| Katılımcı ara istedi | Modül sonunu bekle, gerekiyorsa ortasında duraklat |
| Ses gelmiyor | Oturumu durdur, kontrol listesini baştan çalıştır, kalibrasyonu doğrula |
| Katılımcı manipülasyonu fark etti | Not düş, veriyi işaretle, analiz aşamasında ayrı değerlendir |

---

## 5. Prova oturumu

### Amaç

Kodun çalıştığını otomatik testler gösterir. Prova oturumu **prosedürün** çalıştığını gösterir.

### Kim

Bir laboratuvar üyesi veya arkadaşınız. Gerçek katılımcı değil. Tercihen deneyi bilmeyen biri — yönergelerin anlaşılır olup olmadığını ancak o söyler.

### Ne yapılır

Gerçek oturumun aynısı, baştan sona, hiçbir adım atlanmadan. SOP'u elinizde tutun ve **yazdığınız gibi** uygulayın.

Ölçün:
- Toplam süre (tahmininizle uyuşuyor mu)
- Her modülün süresi
- Katılımcının yorulduğu nokta
- Anlaşılmayan yönerge var mı

### Sonra kasten bozun

Bunlar gerçek oturumda başınıza gelecek. Şimdi başınıza gelsin:

- Oturumu ortasında ESC ile kesin → DB durumu doğru mu, devam edilebiliyor mu
- Yanıt vermeden bekleyin → zaman aşımı çalışıyor mu, kayda `NONE` düşüyor mu
- Rastgele tuşlara basın → program çöküyor mu
- Kulaklığı çıkarın → program devam ediyor mu (etmeli), kayda not düşüyor mu
- Bilgisayarı uyku moduna sokun → ne oluyor
- Ses arayüzünün kablosunu çekin → açık hata mı, sessiz bozulma mı

Son madde önemli: **sessiz bozulma en tehlikeli hata türüdür.** Program çökmüyor, veri geliyor, ama veri yanlış. Her başarısızlık modu görünür olmalı.

### Kontrol edilecek

```bash
python -m mcgurk.qc --session <id>
```

Raporda:
- Her denemenin zamanlama kaydı dolu mu
- Nominal ve gerçekleşen SOA arasındaki sapma kabul edilebilir mi
- Düşen kare var mı
- Yanıt kategorileri doğru atanmış mı
- Bloklar, modüller, katılımcı doğru ilişkilendirilmiş mi

Sonra veriyi analiz hattından geçirin. Sahte veri anlamsız çıkacak (rastgele yanıtlar) ama **boru hattının uçtan uca çalıştığını** görmüş olursunuz.

---

## 6. Pilot çalışma

### Bu en kritik adım

Kodun çalışması, geçerli veri ürettiği anlamına gelmez. Pilot bunu test eder.

**Kalibrasyondan ve fotodiyot ölçümünden sonra yapılır.** Kalibre olmayan bir sistemde pilot yapmanın anlamı yok — sonuç beklenenden saparsa uyaranlarınız mı bozuk yoksa seviyeniz mi yanlış ayırt edemezsiniz.

### Kim

**5–10 normal işiten yetişkin.** Yaş aralığınıza (18–60) yakın olsunlar. Deneyi bilmesinler.

Bunlar çalışmanın kontrol grubu değil; ayrı bir ön test. Pilot verisini asıl analize dahil etmeyin (kurulum değişebilir).

### Ne aranıyor

Pilotta iki tür kontrol var. **İçsel kontroller literatür karşılaştırmasından daha güvenilirdir** — çünkü literatürdeki mutlak değerler uyarana, dile ve popülasyona göre çok değişir.

#### İçsel kontroller (bunlar kesin olmalı)

| Kontrol | Beklenen | Sağlanmazsa |
|---|---|---|
| **Uyumlu denemelerde doğruluk** | %95 üstü | Uyaran veya seviye sorunu. Entegrasyonla ilgisi yok — katılımcı sesi doğru duyamıyor. Önce bunu çözün. |
| **A-only doğruluk, sessiz** | %90 üstü | Aynı. |
| **V-only doğruluk (lipreading)** | Şans üstü ama düşük | Şans düzeyindeyse görsel uyaran işe yaramıyor: kadraj, ışık veya çözünürlük sorunu. |
| **Gürültünün etkisi** | Gürültüde doğruluk sessizden düşük | Fark yoksa SNR uygulanmıyor demektir. Kodu kontrol edin. |
| **AV > A-only, gürültüde** | Görsel fayda pozitif | Değilse görsel bilgi entegre edilmiyor: senkron sorunu olabilir. |
| **Uyumsuz denemelerde işitsel dışı yanıt oranı** | Uyumlu denemelerdeki hata oranından açıkça yüksek | Değilse McGurk etkisi oluşmuyor. En olası nedenler: A/V senkron kayması, uyaran kalitesi, yanıt seti. |
| **TBW eğrisi** | Tepe noktası olan, kenarlara doğru düşen bir eğri | Düz çıkarsa görev anlaşılmamış veya SOA uygulanmıyor. |
| **Oddball hedef doğruluğu** | %90 üstü | Görev çok zor veya tonlar duyulmuyor. |

#### Dışsal kontroller (yaklaşık, geniş aralıklarla)

Bunlarda kesin bir hedef vermeyin. Literatürdeki değerler uyarana ve konuşmacıya göre çok değişir — McGurk füzyon oranları farklı çalışmalarda %20 ile %90 arasında raporlanmıştır.

- **Füzyon oranı:** geniş bir aralıkta olabilir; önemli olan sıfıra yakın olmaması ve kişiler arası değişkenliğin makul olması
- **TBW genişliği:** yetişkinlerde konuşma uyaranıyla tipik olarak birkaç yüz milisaniye mertebesinde
- **PSS:** genellikle hafif pozitif (sesin geç gelmesi tercih edilir — doğal, çünkü ışık her zaman önce varır)

Sonuçlarınız literatür aralıklarının **çok** dışındaysa kurulumunuzu şüpheyle karşılayın. İçindeyse rahatlayın ama içsel kontrolleri yine de geçmiş olmalı.

### Ayrıca ölçün

- **Süre:** gerçek oturum ne kadar sürdü, tahmininizle uyuşuyor mu
- **Yorgunluk:** son bloktaki performans ilk bloktan belirgin düşük mü (düşükse molalar yetersiz)
- **Anlaşılabilirlik:** katılımcıya sorun — hangi yönerge belirsizdi
- **Yanıt seti:** `DIGER` seçeneği ne sıklıkta seçildi, serbest metinlerde ne yazıldı. Sık tekrarlanan bir yanıt varsa onu ayrı seçenek yapın.
- **Zaman aşımı oranı:** %5'i geçiyorsa yanıt penceresi kısa

### Çapraz dinleme kontrolü

Pilot normal işitenlerle yapıldığı için bu kontrolü **ilk SSD katılımcılarında** yapacaksınız.

Sağır kulağa sunumda basit bir tespit görevi çalıştırın: ses var mı yok mu. Performans şans düzeyinde olmalı. Şans üstündeyse ses kafatası yoluyla iyi kulağa ulaşıyor demektir ve lateralizasyon manipülasyonunuz geçersizdir.

Bu kontrol her katılımcıda çalışsın ve kaydedilsin. Yayında raporlanacak bir kontroldür.

### Pilot sonrası

Bulgulara göre düzeltin, sonra **tekrar pilot yapın.** İlk pilotta hiçbir şey değiştirmeden geçmek nadirdir.

İkinci pilot temizse gerçek veri toplamaya başlayın. Bu noktadan sonra **kurulumu değiştirmeyin** — kod, config, kalibrasyon, donanım dondurulur. Değiştirmek zorunda kalırsanız DB'ye not düşün ve analiz aşamasında dönem etkisini kontrol edin.

---

## 7. Sıralama

```
Faz 0–2   kod
   │
Faz 3     kod  ──►  [loopback testi]  ◄── ucuz, kritik
   │
Faz 4–7   kod
   │              ┌── tasarım kararı toplantısı (Faz 4'ten önce)
   │              └── kelime çekimi (Faz 5'ten önce başlasın)
Faz 8–9   kod
   │
   ├──► fotodiyot ölçümü
   ├──► ses kalibrasyonu
   ├──► operatör kılavuzu
   │
   ▼
prova oturumu (1 kişi)
   │
   ▼
pilot 1 (5–10 normal işiten)
   │
   ├── içsel kontroller geçti mi? ──► hayır ──► düzelt ──┐
   │                                                     │
   ▼ evet                                                │
pilot 2 ◄────────────────────────────────────────────────┘
   │
   ▼
KURULUMU DONDUR
   │
   ▼
gerçek veri toplama (60 katılımcı, ~12 ay)
```

---

## 8. Zaman tahmini

| İş | Süre |
|---|---|
| Kod (Faz 0–9) | Claude Code'la birkaç gün–1 hafta yoğun çalışma |
| Tasarım kararı | 1 toplantı |
| Kelime çekimi | 1 gün çekim + 1 gün kurgu/pipeline |
| Fotodiyot + kalibrasyon | Yarım gün |
| Operatör kılavuzu | 3 saat |
| Prova | Yarım gün |
| Pilot 1 + düzeltme + Pilot 2 | 2–3 hafta |
| **Veri toplamaya hazır** | **~4–6 hafta** |

Kod bu sürenin küçük kısmı. Planlamanızı buna göre yapın.
