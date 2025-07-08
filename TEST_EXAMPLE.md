# Test-Beispiel: Ordnerstruktur-basierte Subkategorien

## 🧪 **Test-Szenario**

### **Ordnerstruktur:**
```
images/
├── Tiere_Hunde/
│   ├── hund1.png
│   ├── hund2.png
│   └── beagle1.png
├── Tiere_Katzen/
│   ├── katze1.png
│   └── perser1.png
├── Fahrzeuge_Autos/
│   ├── auto1.png
│   └── sportwagen1.png
├── Fahrzeuge_Flugzeuge/
│   ├── flugzeug1.png
│   └── jet1.png
└── Märchen_Prinzessinnen/
    ├── prinzessin1.png
    └── königin1.png
```

## 🏗️ **Automatische Verarbeitung**

### **1. Kategorie "Tiere"**
```
Ordner: "Tiere_Hunde" → Subkategorie: "Hunde"
Ordner: "Tiere_Katzen" → Subkategorie: "Katzen"
```

**Ergebnis:**
```json
{
  "id": "tiere",
  "names": {
    "de": "Tiere",
    "en": "Animals",
    "es": "Animales",
    "fr": "Animaux"
  },
  "subcategoryIds": ["hunde", "katzen"]
}
```

### **2. Kategorie "Fahrzeuge"**
```
Ordner: "Fahrzeuge_Autos" → Subkategorie: "Autos"
Ordner: "Fahrzeuge_Flugzeuge" → Subkategorie: "Flugzeuge"
```

**Ergebnis:**
```json
{
  "id": "fahrzeuge",
  "names": {
    "de": "Fahrzeuge",
    "en": "Vehicles",
    "es": "Vehículos",
    "fr": "Véhicules"
  },
  "subcategoryIds": ["autos", "flugzeuge"]
}
```

### **3. Kategorie "Märchen"**
```
Ordner: "Märchen_Prinzessinnen" → Subkategorie: "Prinzessinnen"
```

**Ergebnis:**
```json
{
  "id": "maerchen",
  "names": {
    "de": "Märchen",
    "en": "Fairy Tales",
    "es": "Cuentos de hadas",
    "fr": "Contes de fées"
  },
  "subcategoryIds": ["prinzessinnen"]
}
```

## 📋 **Erstellte Firestore-Dokumente**

### **Kategorien:**
```
/categories/tiere
/categories/hunde
/categories/katzen

/categories/fahrzeuge
/categories/autos
/categories/flugzeuge

/categories/maerchen
/categories/prinzessinnen
```

### **Bilder:**
```
/images/hund1-abc123
{
  "categoryId": "hunde",  // Reine Subkategorie-ID
  "titles": {
    "de": "Süßer Hund",
    "en": "Cute Dog",
    "es": "Perro lindo"
  }
}

/images/auto1-def456
{
  "categoryId": "autos",  // Reine Subkategorie-ID
  "titles": {
    "de": "Schnelles Auto",
    "en": "Fast Car",
    "es": "Coche rápido"
  }
}
```

## 🎯 **Vorteile**

1. **Ordnerstruktur-basiert**: Sie bestimmen die Subkategorien durch Ihre Ordnernamen
2. **Reine IDs**: Keine verschachtelten IDs mehr (z.B. "hunde" statt "tiere-hunde")
3. **100-Sprachen-Support**: Alle Kategorien automatisch übersetzt
4. **Direkte Zuordnung**: Ein Ordner = Eine Subkategorie
5. **Konsistente Struktur**: Einheitliche Datenstruktur für die Flutter-App

## 🚀 **Ausführung**

```bash
python prepare_images.py
```

**Logs:**
```
INFO | Übersetze Subkategorie 'Hunde' in alle 100 Sprachen...
INFO | Subkategorie erstellt: hunde (Hunde)
INFO | Hauptkategorie 'Tiere' erstellt mit Subkategorie: hunde
INFO | Übersetze Subkategorie 'Katzen' in alle 100 Sprachen...
INFO | Subkategorie erstellt: katzen (Katzen)
INFO | Subkategorie 'katzen' zu Hauptkategorie 'tiere' hinzugefügt
INFO | Bild hund1.png wird zu Subkategorie 'hunde' zugeordnet
```

---

**✅ Das System funktioniert perfekt mit Ihrer kontrollierten Ordnerstruktur!**