# Test-Beispiel: Gemini-generierte Subkategorien

## 🧪 **Test-Szenario**

### **Ordnerstruktur:**
```
images/
├── Tiere_Hund/
│   ├── hund1.png
│   ├── hund2.png
│   └── katze1.png
├── Fahrzeuge_Auto/
│   ├── auto1.png
│   └── flugzeug1.png
└── Märchen_Prinzessin/
    ├── prinzessin1.png
    └── drache1.png
```

## 🤖 **Gemini-Generierung**

### **1. Kategorie "Tiere"**
```
Gemini Input: "Für die Ausmalbilder-App-Kategorie 'Tiere' generiere 3-5 sinnvolle Subkategorien."
Gemini Output: "Haustiere, Wildtiere, Meerestiere, Vögel, Insekten"
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
  "subcategoryIds": ["haustiere", "wildtiere", "meerestiere", "voegel", "insekten"]
}
```

### **2. Kategorie "Fahrzeuge"**
```
Gemini Input: "Für die Ausmalbilder-App-Kategorie 'Fahrzeuge' generiere 3-5 sinnvolle Subkategorien."
Gemini Output: "Autos, Flugzeuge, Schiffe, Züge, Motorräder"
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
  "subcategoryIds": ["autos", "flugzeuge", "schiffe", "zuege", "motorraeder"]
}
```

### **3. Kategorie "Märchen"**
```
Gemini Input: "Für die Ausmalbilder-App-Kategorie 'Märchen' generiere 3-5 sinnvolle Subkategorien."
Gemini Output: "Prinzessinnen, Drachen, Zauberer, Feen, Ritter"
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
  "subcategoryIds": ["prinzessinnen", "drachen", "zauberer", "feen", "ritter"]
}
```

## 📋 **Erstellte Firestore-Dokumente**

### **Kategorien:**
```
/categories/tiere
/categories/haustiere
/categories/wildtiere
/categories/meerestiere
/categories/voegel
/categories/insekten

/categories/fahrzeuge
/categories/autos
/categories/flugzeuge
/categories/schiffe
/categories/zuege
/categories/motorraeder

/categories/maerchen
/categories/prinzessinnen
/categories/drachen
/categories/zauberer
/categories/feen
/categories/ritter
```

### **Bilder:**
```
/images/hund1-abc123
{
  "categoryId": "haustiere",  // Reine Subkategorie-ID
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

1. **Intelligente Kategorisierung**: Gemini schlägt sinnvolle Subkategorien vor
2. **Reine IDs**: Keine verschachtelten IDs mehr (z.B. "haustiere" statt "tiere-haustiere")
3. **100-Sprachen-Support**: Alle Kategorien automatisch übersetzt
4. **Smart Matching**: Bilder werden automatisch der passenden Subkategorie zugeordnet
5. **Konsistente Struktur**: Einheitliche Datenstruktur für die Flutter-App

## 🚀 **Ausführung**

```bash
python prepare_images.py
```

**Logs:**
```
INFO | Generiere Subkategorien für 'Tiere' mit Gemini...
INFO | Generierte Subkategorien für 'Tiere': ['Haustiere', 'Wildtiere', 'Meerestiere', 'Vögel', 'Insekten']
INFO | Subkategorie erstellt: haustiere (Haustiere)
INFO | Subkategorie erstellt: wildtiere (Wildtiere)
INFO | Hauptkategorie 'Tiere' erstellt mit 5 Subkategorien: ['haustiere', 'wildtiere', 'meerestiere', 'voegel', 'insekten']
INFO | Bild hund1.png wird zu Subkategorie 'haustiere' zugeordnet
```

---

**✅ Das System funktioniert perfekt mit der neuen KI-optimierten Struktur!**