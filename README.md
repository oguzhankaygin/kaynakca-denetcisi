# Kaynakça Tutarlılık ve Doğrulama Denetçisi

Ödev ve tez kaynakçalarındaki eksik alanları, biçim ve sıra sorunlarını bulur. İsteğe bağlı olarak metin içi atıfları kaynakçayla eşleştirir ve her kaynak için elle doğrulama kontrol listesi oluşturur.

Komut satırı ve yerel web arayüzü için Python 3.10 veya üstü yeterlidir. Uygulama yalnızca standart kütüphaneyi kullanır.

## Tarayıcıda kullan

[Kaynakça Denetçisi’ni aç](https://oguzhankaygin.github.io/kaynakca-denetcisi/). Araç ücretsizdir ve kurulum gerektirmez. Kaynakçayı yapıştırıp **Denetle**’ye basın. İlk denetimde tarayıcı [Pyodide 0.27.7’yi jsDelivr’dan](https://pyodide.org/en/0.27.7/usage/downloading-and-deploying.html) yükler ve aynı Python paketini çalıştırır. Raporu Markdown olarak indirebilir veya yazdırabilirsiniz.

Telefonda tarayıcı menüsündeki **Ana ekrana ekle** (iPhone’da Paylaş → Ana Ekrana Ekle) seçeneğiyle uygulama gibi açabilirsiniz; ilk denetimden sonra internetsiz de çalışır.

Kaynakça metni denetim sırasında hiçbir sunucuya gönderilmez. Varsayılan olarak kapalı olan **DOI’leri Crossref ile karşılaştır** seçeneğini açarsanız tarayıcı yalnızca geçerli DOI’leri doğrudan Crossref’e gönderir. Bir elle doğrulama bağlantısını açarsanız bağlantıdaki arama terimi ilgili hizmete gider.

GitHub Pages yayın kaynağı için **Settings → Pages** bölümünde **Deploy from a branch**, ardından `main` ve `/docs` seçeneklerini belirleyin. Python veya ortak arayüz dosyalarını değiştirdiğinizde repo kökünde `python3 -m kaynakca build-site` çalıştırarak yayın kopyalarını güncelleyin. [GitHub Pages yayın kaynağı belgeleri](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

## Kullanım

Komutları repo kökünde çalıştırın.

```sh
python3 -m kaynakca ornekler/kaynakca.txt
python3 -m kaynakca ornekler/kaynakca.txt --metin ornekler/odev.txt --md
python3 -m kaynakca ornekler/kaynakca.bib --json
python3 -m kaynakca - < ornekler/kaynakca.txt
python3 -m kaynakca kendi-kaynakcaniz.bib --crossref
python3 -m kaynakca web
```

UTF-8 düz metinde her kaynağı ayrı satıra yazın. Paragrafları boş satırla ayırabilirsiniz. Aynı kaynağın devam satırlarını girintileyin. `[1]`, `1.` ve madde işaretleri desteklenir. BibTeX, dosya uzantısından veya girişin başındaki kayıttan tanınır. Örnek künyeler, DOI’ler ve ödev metni kurgusaldır.

Terminal çıktısı renksizdir. `--md` özet tablosu ve işaretlenebilir kontrol listeleri üretir. `--json` ayrıştırılan alanları, bulguları, bağlantıları ve varsa Crossref sonucunu içerir. Çıkış kodu **1** hata düzeyinde bulgu veya okuma/ayrıştırma hatası, **0** ise hata düzeyinde bulgu olmadığını gösterir. Crossref sonuçları ayrı bir alanda raporlanır ve çıkış kodunu etkilemez.

Web komutu [yerel arayüzü](http://127.0.0.1:8791) açabileceğiniz adresi terminale yazar. Kaynakçayı veya BibTeX içeriğini kutuya yapıştırıp **Denetle** düğmesine basın. Web arayüzü çevrimdışı çalışır. `POST /api/denetle` UTF-8 düz metin veya `{"kaynakca":"..."}` biçiminde JSON kabul eder. `X-Kaynakca-Request: 1` olmadan 403, 200 KB (204.800 bayt) üzerinde 413 döner.

### Örnek terminal çıktısı

```text
5 kaynak · Baskın stil: APA 7 · 0 hata, 8 uyarı, 3 bilgi

Belge bulguları

- [uyari] ATIF_KARSILIKSIZ — Kaynakçada karşılığı yok: (Kurgu, 2021) Öneri: Kaynakçayı veya metindeki atfı düzeltin.
```

## Kurallar

| Kod | Önem | Kontrol |
| --- | --- | --- |
| `EKSIK_YEAR`, `EKSIK_TITLE`, `EKSIK_AUTHORS`, `EKSIK_SOURCE` | Hata | Yıl, başlık, yazar, dergi/yayınevi/site adı |
| `DOI_BICIMI` | Hata | DOI dizgesinin biçimi |
| `DOI_TEKRARI` | Uyarı | Ayrı DOI ile aynı DOI çözümleyici URL’sinin birlikte verilmesi |
| `GELECEK_YIL` | Hata | Yayın yılının içinde bulunulan yıldan büyük olması |
| `SAYFA_TERS`, `SAYFA_BICIMI` | Uyarı | Ters veya okunamayan sayfa aralığı |
| `KARISIK_STIL` | Uyarı | Baskın APA 7, IEEE, MLA veya Chicago (yazar-tarih) tahmininden sapan künye |
| `YINELENEN` | Uyarı | Normalleştirilmiş başlık ve yılın yinelenmesi |
| `DOI_YINELENEN` | Uyarı | Farklı künyelerde aynı DOI (uydurma kaynağın sık belirtisi) |
| `YAZAR_KISALTMASI` | Uyarı | Aynı kaynakçada “et al.” ve “ve ark.” kullanımı |
| `ERISIM_TARIHI` | Uyarı | URL’li web kaynağında erişim tarihi |
| `ALFABETIK_SIRA` | Uyarı | Baskın APA 7 veya MLA kaynakçada ilk yazarın soyadına göre sıralama |
| `NUMARA_SIRASI` | Uyarı | IEEE kaynak numaralarının 1’den başlayarak ardışık ilerlemesi |
| `ATIF_KARSILIKSIZ` | Uyarı | Metin içi atfın kaynakçada karşılığı |
| `ATIF_YOK` | Bilgi | Kaynakçadaki kaydın metinde kullanımı |

## Neyi yapmaz?

Araç bir kaynağın gerçekliğini veya ödevdeki iddiayı desteklediğini kanıtlamaz. Çevrimdışı denetimde bağlantılar yalnızca hazırlanır. Google Scholar, Crossref ve varsa DOI bağlantısı sunulur. Türkçe olduğu tahmin edilen kaynaklar için TR Dizin ve YÖK Ulusal Tez Merkezi de listelenir. Bağlantıları açıp künyeyi ve içeriği elle kontrol edin.

`--crossref` yalnızca DOI meta verisindeki başlığı, yılı ve ilk yazarı künye ile karşılaştırır. 404, ağ hatası ve karşılaştırılamayan alanlar ayrıca belirtilir. Bir DOI kaydının uyumlu görünmesi, kaynağın içeriği veya niteliği hakkında hüküm vermez.

## Gizlilik

Varsayılan CLI ve web arayüzü herhangi bir dış istek yapmaz. Web sunucusu yalnızca `127.0.0.1` üzerinde dinler. Gönderilen metin bellekte işlenir ve kaydedilmez. Bir arama bağlantısını açtığınızda bağlantıdaki arama terimi ilgili hizmete gider. `--crossref` kullanırsanız geçerli biçimdeki DOI’ler, genel bir User-Agent ile ve e-posta adresi gönderilmeden Crossref’e iletilir. Sorgu zaman aşımı 10 saniyedir ve saniyede en fazla iki istek başlatılır.

## Sınırlamalar

Ayrıştırma ve stil puanları sezgiseldir. Düz metinde italik bilgisi kaybolur. Kaynak türü, birleşik soyadı, kurumsal yazar veya olağandışı tarih ve sayfa gösterimleri yanlış yorumlanabilir. Eşit sayıda stil tahmini olduğunda baskın stil bilinmeyen olarak kalır. BibTeX alanları okunur, BibTeX girdisine basılı bir stil atanmaz ve LaTeX komutları işlenmez. Metin içi eşleştirme `(Yazar, Yıl)` ve `[n]` biçimlerini kapsar. Dipnotlar ve `[1–3]` gibi numara aralıkları kapsam dışıdır.

## Testler

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
node --test
node --check kaynakca/static/app.js
for script in docs/*.js; do node --check "$script"; done
```

Crossref yanıtları taklit edilir ve HTTP işleyicisi ağ bağlantısı açılmadan sınanır.
