# -*- coding: utf-8 -*-
"""
Beispiel-Verwendung des Firebase Pipeline-Skripts
=================================================
Zeigt, wie Sie Kategorien und Bilder mit der korrekten Firebase-Datenstruktur erstellen.
"""
from firebase_pipeline import (
    create_main_category, 
    create_subcategory, 
    process_image_with_categories,
    translate_category_name,
    _initialize_services
)
from pathlib import Path
import logging

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def example_create_categories():
    """Beispiel: Erstellt Hauptkategorien und Unterkategorien"""
    log.info("🎯 Beispiel: Erstelle Kategorien")
    
    # 1. Hauptkategorie "Kleinkinder 0-5" erstellen
    main_category_data = {
        'id': 'kleinkinder-0-5',
        'names': translate_category_name('Kleinkinder 0-5'),
        'ageGroup': '0-5',
        'order': 1
    }
    
    create_main_category(**main_category_data)
    
    # 2. Unterkategorien erstellen
    subcategories = [
        {
            'id': 'tiere-kleinkinder',
            'names': translate_category_name('Tiere'),
            'ageGroup': '0-5',
            'order': 1
        },
        {
            'id': 'fahrzeuge-kleinkinder',
            'names': translate_category_name('Fahrzeuge'),
            'ageGroup': '0-5',
            'order': 2
        },
        {
            'id': 'formen-kleinkinder',
            'names': translate_category_name('Formen'),
            'ageGroup': '0-5',
            'order': 3
        },
        {
            'id': 'farben-kleinkinder',
            'names': translate_category_name('Farben'),
            'ageGroup': '0-5',
            'order': 4
        }
    ]
    
    for subcategory in subcategories:
        create_subcategory('kleinkinder-0-5', subcategory)
    
    log.info("✅ Alle Kategorien erstellt")

def example_create_school_kids_categories():
    """Beispiel: Erstellt Kategorien für Schulkinder"""
    log.info("🎯 Beispiel: Erstelle Schulkinder-Kategorien")
    
    # Hauptkategorie "Schulkinder 6-12"
    main_category_data = {
        'id': 'schulkinder-6-12',
        'names': translate_category_name('Schulkinder 6-12'),
        'ageGroup': '6-12',
        'order': 2
    }
    
    create_main_category(**main_category_data)
    
    # Unterkategorien für Schulkinder
    subcategories = [
        {
            'id': 'tiere-schulkinder',
            'names': translate_category_name('Tiere'),
            'ageGroup': '6-12',
            'order': 1
        },
        {
            'id': 'natur-schulkinder',
            'names': translate_category_name('Natur'),
            'ageGroup': '6-12',
            'order': 2
        },
        {
            'id': 'technik-schulkinder',
            'names': translate_category_name('Technik'),
            'ageGroup': '6-12',
            'order': 3
        }
    ]
    
    for subcategory in subcategories:
        create_subcategory('schulkinder-6-12', subcategory)
    
    log.info("✅ Schulkinder-Kategorien erstellt")

def example_process_images():
    """Beispiel: Verarbeitet Bilder mit Kategorie-Referenz"""
    log.info("🎯 Beispiel: Verarbeite Bilder")
    
    # Beispiel-Bilddaten (normalerweise würden Sie echte PNG-Dateien verwenden)
    example_images = [
        {
            'png_path': Path('./example_images/tiere/hund.png'),
            'main_category_id': 'kleinkinder-0-5',
            'subcategory_data': {
                'id': 'tiere-kleinkinder',
                'names': translate_category_name('Tiere'),
                'ageGroup': '0-5',
                'order': 1
            }
        },
        {
            'png_path': Path('./example_images/fahrzeuge/auto.png'),
            'main_category_id': 'kleinkinder-0-5',
            'subcategory_data': {
                'id': 'fahrzeuge-kleinkinder',
                'names': translate_category_name('Fahrzeuge'),
                'ageGroup': '0-5',
                'order': 2
            }
        }
    ]
    
    for image_info in example_images:
        if image_info['png_path'].exists():
            try:
                process_image_with_categories(
                    image_info['png_path'],
                    image_info['main_category_id'],
                    image_info['subcategory_data']
                )
            except Exception as e:
                log.error(f"Fehler bei {image_info['png_path'].name}: {e}")
        else:
            log.warning(f"Bild nicht gefunden: {image_info['png_path']}")

def example_manual_image_upload():
    """Beispiel: Manueller Upload eines Bildes"""
    log.info("🎯 Beispiel: Manueller Bild-Upload")
    
    from firebase_pipeline import upload_image_with_subcategory
    
    # Beispiel-Bilddaten
    image_data = {
        'id': 'hund-001',
        'titles': {
            'de': 'Süßer Hund',
            'en': 'Cute Dog',
            'fr': 'Chien Mignon'
        },
        'tags': ['hund', 'tier', 'haustier', 'dog', 'animal', 'pet'],
        'ageGroup': '0-5'
    }
    
    # Bild in Unterkategorie hochladen
    upload_image_with_subcategory(image_data, 'tiere-kleinkinder')
    
    log.info("✅ Manueller Upload abgeschlossen")

def main():
    """Hauptfunktion - führt alle Beispiele aus"""
    log.info("🚀 Starte Firebase Pipeline Beispiele")
    
    # Firebase initialisieren
    _initialize_services()
    
    try:
        # 1. Kategorien erstellen
        example_create_categories()
        
        # 2. Schulkinder-Kategorien erstellen
        example_create_school_kids_categories()
        
        # 3. Bilder verarbeiten (falls vorhanden)
        example_process_images()
        
        # 4. Manueller Upload
        example_manual_image_upload()
        
        log.info("✅ Alle Beispiele erfolgreich abgeschlossen")
        
    except Exception as e:
        log.error(f"❌ Fehler in den Beispielen: {e}")
        raise

if __name__ == "__main__":
    main()