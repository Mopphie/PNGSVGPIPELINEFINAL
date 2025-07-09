# Firebase Pipeline-Skript für Kategorien und Bilder

## 📋 Übersicht

Das Firebase Pipeline-Skript implementiert die korrekte Datenstruktur für Ihre Flutter-App mit Hauptkategorien und Unterkategorien. Es erstellt die Firebase-Datenstruktur, wie in Ihrer Beschreibung angegeben.

## 🏗️ Firebase-Datenstruktur

### Firestore Collection: `categories`

#### Hauptkategorie (z.B. "kleinkinder-0-5")
```json
{
  "id": "kleinkinder-0-5",
  "names": {
    "de": "Kleinkinder 0-5",
    "en": "Toddlers 0-5",
    "fr": "Tout-petits 0-5"
  },
  "iconUrl": "https://storage.googleapis.com/bucket/icons/kleinkinder-0-5.png",
  "subcategoryIds": ["tiere-kleinkinder", "fahrzeuge-kleinkinder"],
  "ageGroup": "0-5",
  "order": 1,
  "parentCategoryId": ""  // Leer für Hauptkategorien
}
```

#### Unterkategorie (z.B. "tiere-kleinkinder")
```json
{
  "id": "tiere-kleinkinder",
  "names": {
    "de": "Tiere",
    "en": "Animals",
    "fr": "Animaux"
  },
  "iconUrl": "https://storage.googleapis.com/bucket/icons/tiere-kleinkinder.png",
  "subcategoryIds": [],  // Leer für Unterkategorien
  "ageGroup": "0-5",
  "order": 1,
  "parentCategoryId": "kleinkinder-0-5"  // 🔥 WICHTIG: Verweis auf Hauptkategorie
}
```

### Firestore Collection: `images`

#### Bild-Dokument
```json
{
  "id": "hund-001",
  "titles": {
    "de": "Süßer Hund",
    "en": "Cute Dog"
  },
  "categoryId": "tiere-kleinkinder",  // 🔥 WICHTIG: Verweis auf Unterkategorie
  "tags": ["hund", "tier", "haustier"],
  "svgPath": "images/tiere-kleinkinder/hund-001.svg",
  "thumbnailPath": "thumbnails/tiere-kleinkinder/hund-001.png",
  "timestamp": Timestamp.now(),
  "ageGroup": "0-5",
  "popularity": 0,
  "isNew": true
}
```

## 🚀 Installation und Setup

### 1. Dependencies installieren
```bash
pip install -r requirements.txt
```

### 2. Umgebungsvariablen konfigurieren
Erstellen Sie eine `.env` Datei:
```env
GEMINI_API_KEY=your_gemini_api_key
FIREBASE_CREDENTIALS=path/to/firebase-credentials.json
FIREBASE_BUCKET=your-firebase-bucket-name
BASE_IMAGE_DIRECTORY=./images
CACHE_DIRECTORY=./cache
```

### 3. Externe Tools installieren
```bash
# Ubuntu/Debian
sudo apt-get install inkscape potrace imagemagick

# macOS
brew install inkscape potrace imagemagick

# Windows
# Laden Sie Inkscape und Potrace von den offiziellen Websites herunter
```

## 📁 Ordnerstruktur

```
project/
├── firebase_pipeline.py      # Haupt-Pipeline-Skript
├── example_usage.py          # Beispiel-Verwendung
├── images/                   # PNG-Ausmalbilder
│   ├── tiere/
│   │   ├── hund.png
│   │   └── katze.png
│   └── fahrzeuge/
│       ├── auto.png
│       └── flugzeug.png
├── cache/                    # Cache für Übersetzungen
└── .env                      # Umgebungsvariablen
```

## 🔧 Verwendung

### 1. Kategorien erstellen

```python
from firebase_pipeline import create_main_category, create_subcategory, translate_category_name

# Hauptkategorie erstellen
main_category_data = {
    'id': 'kleinkinder-0-5',
    'names': translate_category_name('Kleinkinder 0-5'),
    'ageGroup': '0-5',
    'order': 1
}
create_main_category(**main_category_data)

# Unterkategorien erstellen
subcategory_data = {
    'id': 'tiere-kleinkinder',
    'names': translate_category_name('Tiere'),
    'ageGroup': '0-5',
    'order': 1
}
create_subcategory('kleinkinder-0-5', subcategory_data)
```

### 2. Bilder verarbeiten

```python
from firebase_pipeline import process_image_with_categories
from pathlib import Path

# Bild verarbeiten
png_path = Path('./images/tiere/hund.png')
subcategory_data = {
    'id': 'tiere-kleinkinder',
    'names': translate_category_name('Tiere'),
    'ageGroup': '0-5',
    'order': 1
}

process_image_with_categories(png_path, 'kleinkinder-0-5', subcategory_data)
```

### 3. Manueller Bild-Upload

```python
from firebase_pipeline import upload_image_with_subcategory

image_data = {
    'id': 'hund-001',
    'titles': {
        'de': 'Süßer Hund',
        'en': 'Cute Dog'
    },
    'tags': ['hund', 'tier', 'haustier'],
    'ageGroup': '0-5'
}

upload_image_with_subcategory(image_data, 'tiere-kleinkinder')
```

## 🎯 Vollständiges Beispiel

Führen Sie das Beispiel-Skript aus:

```bash
python example_usage.py
```

Dies erstellt:
- Hauptkategorie "Kleinkinder 0-5"
- Unterkategorien: Tiere, Fahrzeuge, Formen, Farben
- Hauptkategorie "Schulkinder 6-12"
- Unterkategorien: Tiere, Natur, Technik
- Verarbeitet vorhandene Bilder
- Führt manuellen Upload durch

## 📊 Datenfluss

```
Landing Page → Klick auf "Kleinkinder 0-5"
Navigation → /category/kleinkinder-0-5
GalleryScreen → Erkennt: "Das ist eine Hauptkategorie"
Firebase Query → categories.where('parentCategoryId', '==', 'kleinkinder-0-5')
Unterkategorien anzeigen → "Tiere", "Fahrzeuge", "Formen", etc.
Klick auf Unterkategorie → /category/tiere-kleinkinder
GalleryScreen → Erkennt: "Das ist eine Unterkategorie"
Firebase Query → images.where('categoryId', '==', 'tiere-kleinkinder')
Bilder anzeigen → Alle Bilder der Unterkategorie
```

## 🔍 Wichtige Funktionen

### `create_main_category()`
Erstellt eine Hauptkategorie in Firestore.

### `create_subcategory()`
Erstellt eine Unterkategorie mit `parentCategoryId`-Verweis.

### `process_image_with_categories()`
Verarbeitet ein PNG-Bild und lädt es mit korrekter `categoryId`-Referenz hoch.

### `upload_image_with_subcategory()`
Lädt Bild-Metadaten mit Unterkategorie-Referenz hoch.

## 🛠️ Konfiguration

### Umgebungsvariablen
- `GEMINI_API_KEY`: API-Schlüssel für Gemini AI
- `FIREBASE_CREDENTIALS`: Pfad zu Firebase-Credentials
- `FIREBASE_BUCKET`: Firebase Storage Bucket-Name
- `BASE_IMAGE_DIRECTORY`: Verzeichnis mit PNG-Bildern
- `CACHE_DIRECTORY`: Cache-Verzeichnis

### Optionale Einstellungen
- `INKSCAPE_PATH`: Pfad zu Inkscape
- `POTRACE_PATH`: Pfad zu Potrace
- `DEFAULT_DPI`: DPI für SVG-Konvertierung (Standard: 96)
- `THUMB_WIDTH`: Thumbnail-Breite (Standard: 350px)

## 📝 Logging

Das Skript erstellt detaillierte Logs in `firebase_pipeline.log`:
- Kategorie-Erstellung
- Bild-Verarbeitung
- Upload-Status
- Fehler und Warnungen

## 🔄 Automatisierung

Das Skript kann automatisch:
- PNG-Dateien aus der Ordnerstruktur erkennen
- Kategorien basierend auf Ordnernamen erstellen
- Bilder mit Gemini AI analysieren
- Übersetzungen in 100+ Sprachen generieren
- SVG und Thumbnails erstellen
- Dateien zu Firebase Storage hochladen
- Metadaten in Firestore speichern

## ⚠️ Wichtige Hinweise

1. **parentCategoryId**: Unterkategorien MÜSSEN eine `parentCategoryId` haben
2. **categoryId**: Bilder MÜSSEN eine `categoryId` (Unterkategorie-ID) haben
3. **Ordnerstruktur**: Verwenden Sie `maincat/subcat/` für automatische Kategorisierung
4. **Übersetzungen**: Alle Kategorienamen werden automatisch in 100+ Sprachen übersetzt
5. **Duplikate**: Das Skript verhindert doppelte Verarbeitung durch Hash-Prüfung

## 🐛 Fehlerbehebung

### Häufige Probleme

1. **Inkscape/Potrace nicht gefunden**
   - Installieren Sie die Tools oder setzen Sie die Pfade in `.env`

2. **Firebase-Credentials-Fehler**
   - Überprüfen Sie den Pfad in `FIREBASE_CREDENTIALS`
   - Stellen Sie sicher, dass die Datei gültig ist

3. **Gemini API-Fehler**
   - Überprüfen Sie Ihren `GEMINI_API_KEY`
   - Prüfen Sie API-Limits

4. **Bild-Verarbeitungsfehler**
   - Stellen Sie sicher, dass PNG-Dateien gültig sind
   - Überprüfen Sie die Bildgröße und das Format

## 📞 Support

Bei Fragen oder Problemen:
1. Überprüfen Sie die Logs in `firebase_pipeline.log`
2. Stellen Sie sicher, dass alle Dependencies installiert sind
3. Überprüfen Sie die Umgebungsvariablen
4. Testen Sie mit dem Beispiel-Skript