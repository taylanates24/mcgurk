# OPERATÖR EL KİTABI (SOP) — McGurk / SSD Oturumu

> **Bu belge oturumu yürüten kişi içindir; Python bilgisi gerektirmez.**
> Geliştirici belgesi `README.md`'dir. Bu bir **taslaktır**: `[DOLDURULACAK]`
> ile işaretli yerler laboratuvara/donanıma özgü ayrıntılardır ve proje ekibi
> tarafından doldurulacaktır.

> ⚠️ **EN ÖNEMLİ KURAL:** McGurk etkisinin ne olduğu, "dudakla sesin
> çelişmesi", "gördüğünüz sizi yanıltabilir" gibi hiçbir açıklama **oturum
> bitmeden ASLA** katılımcıya söylenmez. Bunu söylemek katılımcının yanıtlarını
> değiştirir (talep karakteristiği) ve o katılımcının verisini geçersiz kılar.
> Açıklama (debriefing) yalnız oturum tamamen bittikten sonra yapılır.

---

## 0. Bir bakışta oturum akışı

```
Kontrol listesi (YEŞİL/KIRMIZI)  →  katılımcı karşılama + kulaklık
   →  yazılımı başlat  →  giriş (anonim kod, grup, yaş...)
   →  kontrol onayı  →  alıştırma  →  modüller (yönerge + molalar)
   →  çapraz dinleme kontrolü (yalnız SSD)  →  bitiş + otomatik yedek
   →  QC raporu  →  debriefing
```

Tahmini süre: **~75–80 dakika** (yönergeler, kulaklık yerleşimi ve modül geçişleri
dahil; yalnız denemelerin kendisi ~59 dk). `[DOLDURULACAK: prova oturumunda ölçülen gerçek süre]`

---

## 1. Oturum öncesi kontrol listesi

Katılımcı gelmeden önce, laboratuvar bilgisayarında oturum öncesi ön-uçuşu
çalıştırın. `[DOLDURULACAK: masaüstündeki kısayolun/komutun adı]`

- Çıktı satır satır **YEŞİL** veya **KIRMIZI** olur.
- **Herhangi bir satır KIRMIZI ise oturum BAŞLATILMAZ.** Sorunu proje ekibine
  bildirin (aşağıdaki *Sorun giderme*).

Kontrol edilenler (özet): config geçerli mi ve `data_collection` modunda mı,
sistem A/V gecikmesi ölçülü mü, ses kalibrasyonu var mı ve **30 günden eski
değil** mi, ses aygıtı doğru (Psychtoolbox) mu, ekran yenileme hızı beklenen mi,
uyaran seti eksiksiz mi, disk ve yedek klasörü yazılabilir mi, son yedeğin tarihi.

**Fiziksel kontrol listesi** `[DOLDURULACAK]`:
- [ ] Sessiz oda, kapı kapalı, telefon sessizde
- [ ] Kulaklık takılı ve doğru aygıt seçili (sol=sol, sağ=sağ — çapraz değil)
- [ ] Ekran parlaklığı/mesafesi `[DOLDURULACAK]`
- [ ] Katılımcı onam formu imzalı `[DOLDURULACAK]`

---

## 2. Katılımcı karşılama ve kulaklık yerleşimi

1. Katılımcıyı karşılayın, rahat oturmasını sağlayın. Ekrana mesafe
   `[DOLDURULACAK: ör. 60 cm]`.
2. **Kulaklığı doğru yerleştirin** — sol kulaklık sol kulağa, sağ sağa. Bu
   çalışmada **kulak yönü bir deney değişkenidir**; ters takılan kulaklık tüm
   uzamsal veriyi bozar.
   - `[DOLDURULACAK: kulaklık modeli ve L/R işaretinin yeri]`
   - Insert kulaklık kullanılıyorsa yerleşim derinliği `[DOLDURULACAK]`.
3. Ses seviyesini **değiştirmeyin** — seviye kalibrasyondan gelir. Katılımcı
   "çok yüksek/alçak" derse not alın, seviyeyi elle oynamayın.
4. Genel yönergeyi verin (McGurk'ü AÇIKLAMADAN): "Ekranda bir yüz görecek ve/veya
   ses duyacaksınız. Her denemeden sonra ne algıladığınızı seçeceksiniz. Hızlı
   ama doğru yanıt verin." `[DOLDURULACAK: onaylanmış tam karşılama metni]`

---

## 3. Ne söylenir / ne söylenmez

**Söylenir:**
- "Ne duyduğunuzu / gördüğünüzü seçin."
- "Emin değilseniz size en yakın geleni seçin; 'DİĞER' varsa yazabilirsiniz."
- "Ara vermek isterseniz mola ekranlarında dinlenebilirsiniz."

**ASLA söylenmez (oturum bitene kadar):**
- McGurk etkisinin ne olduğu, dudak ile sesin çelişebileceği.
- "Doğru" ya da "yanlış" yaptığı — bu bir **algı** görevidir, sınav değil.
  Yazılım da başarı yüzdesi göstermez (bilinçli).
- Belirli bir yanıtın beklendiği ("çoğu insan şunu duyar" vb.).
- Dikotik/çapraz dinlemede "iki farklı hece var" veya "şu kulağa dikkat edin" —
  serbest bildirim ölçümün kendisidir.

Katılımcı doğru cevabı sorarsa: "Doğru/yanlış yok; sadece ne algıladığınız
önemli. Sonunda çalışmayı anlatacağım." deyin.

---

## 4. Oturum sırasında operatör davranışı

- Yazılımı başlatın `[DOLDURULACAK: kısayol]`, giriş ekranını **operatör**
  doldurur: **anonim kod**, grup (sağ SSD / sol SSD / kontrol), yaş, cinsiyet,
  deprivasyon süresi, PTA sağ/sol. **Ad-soyad alanı yoktur ve sorulmaz (KVKK).**
  - Kod şeması `[DOLDURULACAK: ör. SSD-R-007]`. Kod ↔ kimlik eşleşme listesi
    **ayrı, güvenli** tutulur; bu bilgisayarda/bulutta tutulmaz.
- Giriş sonrası **oturum öncesi kontrol onayı** ekranı çıkar; ön-uçuş çıktısını
  bir kez daha görürsünüz, onaylayıp devam edin.
- Katılımcı yanıt verirken **yorum yapmayın**, yönlendirmeyin, ekrana bakıp tepki
  vermeyin. Sessiz kalın.
- **Molalar** modüller arasında otomatik gelir; katılımcı hazır olunca devam eder.
- İlerleme göstergesi **operatöre** görünür (katılımcıya değil).
- **Acil durdurma:** her aşamada `ESC` çalışır ve "çıkmak istediğinize emin
  misiniz?" onayı sorar. Onaylanırsa oturum güvenle `aborted` kaydedilir, o ana
  kadarki veri **korunur** ve yedek alınır.
- Oturum yarıda kaldıysa aynı katılımcı koduyla yeniden başlatıldığında
  **kaldığı yerden devam** teklif edilir (tamamlanan modüller atlanır).

---

## 5. Çapraz dinleme kontrolü (yalnız SSD)

SSD katılımcılarında oturumun sonuna doğru kısa bir tespit görevi çalışır
(sağır kulağa ses var/yok). Bu bir **geçerlilik kontrolüdür**: sağır kulakta ses
şans üstü duyuluyorsa lateralizasyon o kişide geçerli değildir. Katılımcıya bunu
açıklamayın; yalnız "bazı denemelerde ses olmayabilir, duyduğunuzda basın" deyin.
`[DOLDURULACAK: onaylanmış yönerge metni]`

---

## 6. Oturum sonrası

1. **Otomatik yedek** oturum kapanışında alınır (kesilen oturumda da). Ek olarak
   `[DOLDURULACAK: haftalık harici disk kopyası prosedürü — 3-2-1 kuralı]`.
2. **QC (kalite kontrol) raporunu** çalıştırın `[DOLDURULACAK: komut/kısayol]` ve
   bakın:
   - Düşen kare / SOA sapması makul mü, işaretlenen deneme sayısı,
   - Zaman aşımı oranı aşırı yüksek mi,
   - (SSD) çapraz dinleme "şans üstü" çıktı mı — çıktıysa bu katılımcının uzamsal
     verisi analizde işaretlenir. Not alın.
3. **Debriefing (açıklama).** Şimdi — ve yalnız şimdi — çalışmayı anlatabilirsiniz:
   McGurk etkisi, çalışmanın amacı. `[DOLDURULACAK: onaylanmış debriefing metni]`
4. Oturum notlarını kaydedin `[DOLDURULACAK: not formu]`.

---

## 7. Sorun giderme

| Belirti | Ne yapılır |
|---|---|
| Kontrol listesinde KIRMIZI satır | Oturumu **başlatma**. Satırı not al, proje ekibine bildir. Kalibrasyon 30 günden eskiyse yeniden kalibrasyon gerekir. |
| Ses gelmiyor / yanlış kulaktan | Oturumu durdur (`ESC`). Kulaklık L/R ve aygıt seçimini kontrol et. `[DOLDURULACAK: doğru aygıt adı]` |
| "Ses aygıtı uygun değil" hatası | Kulaklık bağlı/açık mı? Bluetooth ise bağla. Doğru aygıt seçili mi? |
| Program açılışta hata veriyor | Ekran görüntüsü al, proje ekibine ilet. Katılımcıyı bekletme, yeniden randevu. `[DOLDURULACAK: iletişim]` |
| Katılımcı doğru cevabı soruyor | "Doğru/yanlış yok; sadece algınız önemli." (Bkz. §3.) |
| Oturum çöktü / bilgisayar kapandı | Veri `aborted` olarak korunur. Aynı kodla yeniden başlat → "kaldığı yerden devam". |
| Katılımcı yorulursa | Mola ekranlarında dinlenebilir; gerekirse `ESC` ile durdur, sonra devam et. |

---

## 8. Kesinlikle yapılmayacaklar

- ❌ McGurk etkisini/çalışmanın amacını oturum bitmeden anlatmak.
- ❌ Ses seviyesini elle değiştirmek (kalibrasyondan gelir).
- ❌ Kulaklığı ters takmak (L/R).
- ❌ Katılımcı adını/soyadını hiçbir yere yazmak (KVKK — yalnız anonim kod).
- ❌ KIRMIZI kontrol satırıyla oturum başlatmak.
- ❌ Yanıt sırasında katılımcıyı yönlendirmek veya tepki vermek.
