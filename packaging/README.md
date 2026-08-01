# Paketleme — Windows `.exe` (Adım 10c-ii)

Operatör panelini ve deneyi tek bir çift-tıklanan Windows uygulamasına paketler.
Panel varsayılan; deney, kontrol listesi ve doğrulama araçları aynı exe'nin
`--run` bayrağıyla **ayrı süreç** olarak açılır (§A10.1, `mcgurk/app_entry.py`).

## Ön koşullar

- Windows (gerçek makine — derleme burada yapılır, WSL değil).
- `requirements.txt`'in **tamamı** kurulu conda ortamı (Python 3.10, PsychoPy vb.).
- PyInstaller: `pip install -r requirements-dev.txt`

## Derleme

```bash
python tools/build_exe.py
```
veya doğrudan:
```bash
pyinstaller packaging/mcgurk.spec
```
Temiz derleme için: `python tools/build_exe.py --clean`

**Çıktı:** `dist/McGurkSSD/McGurkSSD.exe` (onedir — tek klasör).

## Uyaranlar ve ilk çalıştırma

`stimuli/` **exe'ye gömülmez** (yüzlerce MB). Derlemeden sonra `stimuli/`
klasörünü uygulamanın yanına kopyalayın:

```
dist/McGurkSSD/
├── McGurkSSD.exe
├── stimuli/            <-- buraya kopyalayın
├── config/             <-- ilk çalıştırmada varsayılan experiment.yaml buraya kopyalanır
├── data/               <-- ilk çalıştırmada oluşur (veritabanı)
├── backups/            <-- oturum sonu yedekleri
└── logs/
```

Yazılabilir her şey (`data/`, `backups/`, `logs/`, `config/`, `stimuli/`)
**exe'nin yanında** durur; kod salt-okunur bir geçici dizinde (`_MEIPASS`) açılır.
Bunu `mcgurk/paths.py` çözer (§A10.6). `data_collection` modu için operatör
`config/experiment.yaml`'ı düzenler ve `config/kalibrasyon.json`'ı yerleştirir;
ilk çalıştırmada kopyalanan varsayılan config bir sonraki çalıştırmada **ezilmez**.

## onedir neden (onefile değil)

PsychoPy + Qt + ffmpeg yükü birkaç yüz MB'dir; onefile her açılışta bunu temp'e
açar (yavaş, kırılgan) ve yazılabilir yerleşimi zorlaştırır. onedir'de exe bir
klasörde durur ve veri dosyaları yanına yerleşir.

## Bilinen sorunlar / yineleme (§D10)

**PyInstaller + PsychoPy kötü şöhretlidir.** İlk derleme büyük olasılıkla eksik
gizli import veya veri dosyası yüzünden çalışma anında hata verir. Tipik çözümler
`packaging/mcgurk.spec` içinde işaretli:

- Eksik modül → `hiddenimports`'a ekleyin (veya ilgili paket için `collect_all`).
- Eksik veri dosyası (ör. bir `.json`/`.txt`) → `datas`'a ekleyin.
- Ses backend (`ptb`/portaudio) yüklenmiyor → `psychtoolbox`/`sounddevice`
  `collect_all` çıktısını ve DLL'leri kontrol edin.
- `console=True` derleme sırasında bırakıldı ki başlangıç hataları görünsün;
  kararlı sürümde (v1.0.0) `console=False` (pencereli) yapılabilir.

`console=True` iken exe'yi bir terminalden çalıştırıp hata mesajlarını okuyun.

## Lisans

Panel **PyQt6** kullanır (PSychoPy'nin `psychopy.gui`'si yalnız PyQt destekler ve
PyInstaller tek exe'de iki Qt binding'i bundle'layamaz — bu yüzden PySide6 değil
PyQt6). PyQt6 **GPL v3** (veya ticari) lisanslıdır; PsychoPy de GPL olduğundan bu
akademik araç GPL ile uyumludur. Dağıtımda PyQt6/Qt ve PsychoPy lisans metinleri
bulundurulmalıdır. Kapalı kaynak dağıtım gerekirse PyQt6 ticari lisansı gerekir.

## Kod imzalama

Kapsam dışı. İmzasız exe'de Windows SmartScreen uyarı gösterebilir; gerekirse
ayrı bir iş olarak kod imzalama sertifikası eklenir.
