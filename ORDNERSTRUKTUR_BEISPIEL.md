# Ordnerstruktur-Beispiel für Ihre Ausmalbilder-App

## 📁 **Empfohlene Ordnerstruktur**

### **Format:** `Hauptkategorie_Subkategorie`

```
📁 images/
├── 📂 Tiere_Hunde/
│   ├── 🖼️ golden-retriever.png
│   ├── 🖼️ dackel.png
│   └── 🖼️ schäferhund.png
├── 📂 Tiere_Katzen/
│   ├── 🖼️ perserkatz.png
│   ├── 🖼️ hauskatze.png
│   └── 🖼️ siamkatze.png
├── 📂 Tiere_Wildtiere/
│   ├── 🖼️ löwe.png
│   ├── 🖼️ elefant.png
│   └── 🖼️ tiger.png
├── 📂 Fahrzeuge_Autos/
│   ├── 🖼️ sportwagen.png
│   ├── 🖼️ cabrio.png
│   └── 🖼️ suv.png
├── 📂 Fahrzeuge_Flugzeuge/
│   ├── 🖼️ boeing.png
│   ├── 🖼️ fighter-jet.png
│   └── 🖼️ segelflugzeug.png
├── 📂 Märchen_Prinzessinnen/
│   ├── 🖼️ aschenputtel.png
│   ├── 🖼️ schneewittchen.png
│   └── 🖼️ dornröschen.png
├── 📂 Märchen_Drachen/
│   ├── 🖼️ feuerdrache.png
│   ├── 🖼️ wasserdrache.png
│   └── 🖼️ erddrache.png
├── 📂 Natur_Blumen/
│   ├── 🖼️ rose.png
│   ├── 🖼️ tulpe.png
│   └── 🖼️ sonnenblume.png
└── 📂 Natur_Bäume/
    ├── 🖼️ eiche.png
    ├── 🖼️ birke.png
    └── 🖼️ tanne.png
```

## 🏗️ **Automatische Verarbeitung**

### **Hauptkategorien werden automatisch erkannt:**
- `Tiere` (aus `Tiere_Hunde`, `Tiere_Katzen`, `Tiere_Wildtiere`)
- `Fahrzeuge` (aus `Fahrzeuge_Autos`, `Fahrzeuge_Flugzeuge`)
- `Märchen` (aus `Märchen_Prinzessinnen`, `Märchen_Drachen`)
- `Natur` (aus `Natur_Blumen`, `Natur_Bäume`)

### **Subkategorien werden direkt aus Ordnernamen erstellt:**
- `hunde`, `katzen`, `wildtiere`
- `autos`, `flugzeuge`
- `prinzessinnen`, `drachen`
- `blumen`, `baeume`

## 🌍 **Resultierende Firebase-Struktur**

### **Hauptkategorie "Tiere":**
```json
{
  "id": "tiere",
  "names": {
    "de": "Tiere",
    "en": "Animals",
    "es": "Animales",
    "fr": "Animaux",
    "it": "Animali",
    "pt": "Animais",
    "ja": "動物",
    "ko": "동물",
    "zh": "动物",
    "ru": "Животные",
    "ar": "الحيوانات",
    "hi": "जानवर",
    "tr": "Hayvanlar",
    "...": "weitere 87 Sprachen"
  },
  "iconUrl": "https://storage.googleapis.com/your-bucket/icons/tiere.png",
  "subcategoryIds": ["hunde", "katzen", "wildtiere"],
  "ageGroup": "6-12",
  "parentCategoryId": "",
  "order": 0
}
```

### **Subkategorie "Hunde":**
```json
{
  "id": "hunde",
  "names": {
    "de": "Hunde",
    "en": "Dogs",
    "es": "Perros",
    "fr": "Chiens",
    "it": "Cani",
    "pt": "Cães",
    "ja": "犬",
    "ko": "개",
    "zh": "狗",
    "ru": "Собаки",
    "ar": "كلاب",
    "hi": "कुत्ते",
    "tr": "Köpekler",
    "...": "weitere 87 Sprachen"
  },
  "iconUrl": "https://storage.googleapis.com/your-bucket/icons/hunde.png",
  "subcategoryIds": [],
  "ageGroup": "6-12",
  "parentCategoryId": "tiere",
  "order": 0
}
```

### **Bild-Dokument:**
```json
{
  "id": "golden-retriever-abc123",
  "titles": {
    "de": "Golden Retriever",
    "en": "Golden Retriever",
    "es": "Golden Retriever",
    "fr": "Golden Retriever",
    "...": "weitere 96 Sprachen"
  },
  "categoryId": "hunde",  // Reine Subkategorie-ID
  "ageGroup": "6-12",
  "tags": ["hund", "haustier", "golden", "retriever"],
  "thumbnailPath": "tiere/hunde/golden-retriever-abc123.png",
  "svgPath": "tiere/hunde/golden-retriever-abc123.svg",
  "isNew": true,
  "popularity": 0,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🎯 **Vorteile Ihrer Ordnerstruktur**

1. **Volle Kontrolle**: Sie bestimmen exakt, welche Subkategorien es gibt
2. **Flexibilität**: Neue Subkategorien durch einfaches Erstellen neuer Ordner
3. **Klarheit**: Jeder Ordner = Eine Subkategorie
4. **Skalierbarkeit**: Beliebig viele Hauptkategorien und Subkategorien möglich
5. **Wartbarkeit**: Einfach zu verstehen und zu verwalten

## 🚀 **Ausführung**

```bash
python prepare_images.py
```

**Erwartete Logs:**
```
INFO | Übersetze Subkategorie 'Hunde' in alle 100 Sprachen...
INFO | Subkategorie erstellt: hunde (Hunde)
INFO | Hauptkategorie 'Tiere' erstellt mit Subkategorie: hunde
INFO | Übersetze Subkategorie 'Katzen' in alle 100 Sprachen...
INFO | Subkategorie erstellt: katzen (Katzen)
INFO | Subkategorie 'katzen' zu Hauptkategorie 'tiere' hinzugefügt
INFO | Übersetze Subkategorie 'Wildtiere' in alle 100 Sprachen...
INFO | Subkategorie erstellt: wildtiere (Wildtiere)
INFO | Subkategorie 'wildtiere' zu Hauptkategorie 'tiere' hinzugefügt
INFO | Bild golden-retriever.png wird zu Subkategorie 'hunde' zugeordnet
INFO | Bild löwe.png wird zu Subkategorie 'wildtiere' zugeordnet
```

---

**✅ Ihre Ordnerstruktur bestimmt die Kategorien - maximale Kontrolle und Flexibilität!**