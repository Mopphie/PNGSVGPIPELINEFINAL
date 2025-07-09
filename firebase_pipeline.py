# -*- coding: utf-8 -*-
"""
Firebase Pipeline-Skript für Kategorien und Bilder
==================================================
• Erstellt Hauptkategorien (z.B. "kleinkinder-0-5")
• Erstellt Unterkategorien mit parentCategoryId-Verweis
• Lädt Bilder mit korrekter categoryId-Referenz
• Implementiert die beschriebene Firebase-Datenstruktur
"""
from __future__ import annotations
import os, re, json, time, uuid, hashlib, tempfile, logging, threading, subprocess
import xml.etree.ElementTree as ET
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple, Dict, List, Optional
import http.client
import socket
import urllib3.exceptions
from dotenv import load_dotenv
from PIL import Image, ImageOps
import google.generativeai as genai
from google.api_core import exceptions as google_api_exceptions
import firebase_admin
from firebase_admin import credentials, firestore, storage
import sqlite3

# ───────────────────────── CONFIG ──────────────────────────
load_dotenv()
GEMINI_API_KEY        = os.environ["GEMINI_API_KEY"]
FIREBASE_CREDENTIALS  = os.environ["FIREBASE_CREDENTIALS"]
FIREBASE_BUCKET       = os.environ["FIREBASE_BUCKET"]
INKSCAPE_PATH         = os.getenv("INKSCAPE_PATH", "inkscape")
POTRACE_PATH          = os.getenv("POTRACE_PATH", "potrace")
DEFAULT_DPI           = int(os.getenv("DEFAULT_DPI", "96"))
MAX_PARALLEL          = int(os.getenv("MAX_PARALLEL", "1"))
TARGET_THUMB_WIDTH_PX = int(os.getenv("THUMB_WIDTH", "350"))
TRACE_THRESHOLD       = os.getenv("TRACE_THRESHOLD", "0.5")
THUMB_RATIO_TOLERANCE = float(os.getenv("THUMB_RATIO_TOLERANCE", "0.05"))

A4_WIDTH_MM, A4_HEIGHT_MM = 210, 297

# ERWEITERTE SPRACH-MAP MIT 100 SPRACHEN
LANG_MAP: Dict[str, str] = {
    "Deutsch": "de",
    "Englisch": "en",
    "Spanisch": "es",
    "Französisch": "fr",
    "Italienisch": "it",
    "Portugiesisch": "pt",
    "Niederländisch": "nl",
    "Japanisch": "ja",
    "Koreanisch": "ko",
    "Mandarin": "zh",
    "Russisch": "ru",
    "Arabisch": "ar",
    "Hindi": "hi",
    "Türkisch": "tr",
    "Polnisch": "pl",
    "Schwedisch": "sv",
    "Indonesisch": "id",
    "Vietnamesisch": "vi",
    "Tschechisch": "cs",
    "Ukrainisch": "uk",
    "Bengali": "bn",
    "Punjabi": "pa",
    "Javanese": "jv",
    "Wu": "wuu",
    "Malaiisch": "ms",
    "Telugu": "te",
    "Marathi": "mr",
    "Tamil": "ta",
    "Urdu": "ur",
    "Persisch": "fa",
    "Kantonesisch": "yue",
    "Thai": "th",
    "Gujarati": "gu",
    "Jin": "cjy",
    "Min Nan": "nan",
    "Pashto": "ps",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Sundanesisch": "su",
    "Xiang": "hsn",
    "Hausa": "ha",
    "Burmesisch": "my",
    "Oriya": "or",
    "Hakka": "hak",
    "Bhojpuri": "bho",
    "Tagalog": "tl",
    "Yoruba": "yo",
    "Maithili": "mai",
    "Sindhi": "sd",
    "Suaheli": "sw",
    "Usbekisch": "uz",
    "Amharisch": "am",
    "Fulfulde": "ff",
    "Igbo": "ig",
    "Oromo": "om",
    "Rumänisch": "ro",
    "Aserbaidschanisch": "az",
    "Awadhi": "awa",
    "Gan": "gan",
    "Cebuano": "ceb",
    "Kurdisch": "ku",
    "Serbokroatisch": "sh",
    "Malagasy": "mg",
    "Nepali": "ne",
    "Chittagong": "ctg",
    "Khmer": "km",
    "Singhalesisch": "si",
    "Zhuang": "za",
    "Assamesisch": "as",
    "Maduresisch": "mad",
    "Somali": "so",
    "Ungarisch": "hu",
    "Kasachisch": "kk",
    "Kinyarwanda": "rw",
    "Dhundhari": "dhd",
    "Haitianisch": "ht",
    "Min Dong": "cdo",
    "Ilokano": "ilo",
    "Quechua": "qu",
    "Kirundi": "rn",
    "Hmong": "hmn",
    "Shona": "sn",
    "Hiligaynon": "hil",
    "Uighurisch": "ug",
    "Balochi": "bal",
    "Weißrussisch": "be",
    "Mooré": "mos",
    "Xhosa": "xh",
    "Konkani": "kok",
    "Griechisch": "el",
    "Akan": "ak",
    "Dekkan": "dcc",
    "Zulu": "zu",
    "Sylheti": "syl",
    "Min Bei": "mnp",
    "Chewa": "ny",
    "Chhattisgarhi": "hne",
    "Hebräisch": "he",
    "Finnisch": "fi",
    "Slowakisch": "sk",
    "Dänisch": "da",
    "Norwegisch": "no",
    "Litauisch": "lt",
    "Lettisch": "lv",
    "Estnisch": "et",
    "Slowenisch": "sl",
    "Kroatisch": "hr",
    "Bulgarisch": "bg",
    "Serbisch": "sr",
    "Bosnisch": "bs",
    "Mazedonisch": "mk",
    "Albanisch": "sq",
    "Armenisch": "hy",
    "Georgisch": "ka",
    "Mongolisch": "mn",
    "Laotisch": "lo",
    "Tibetisch": "bo"
}

# Flexible Pfade
BASE_IMAGE_DIRECTORY = Path(os.getenv("BASE_IMAGE_DIRECTORY", "./images"))
CACHE_DIRECTORY = Path(os.getenv("CACHE_DIRECTORY", "./cache"))

# ──────────────────────── LOGGING ──────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s | %(message)s",
                    handlers=[logging.FileHandler("firebase_pipeline.log", encoding="utf-8"),
                              logging.StreamHandler()])
log = logging.getLogger(__name__)

# ─────────────── FIREBASE / GEMINI INITIALISIERUNG ─────────
_db: firestore.Client | None = None
_bucket: storage.Bucket | None = None
MODEL_IMAGE = None
MODEL_TRANS = None

def _initialize_services() -> None:
    global _db, _bucket, MODEL_IMAGE, MODEL_TRANS
    if _db is not None:
        return
    try:
        if os.path.isfile(FIREBASE_CREDENTIALS):
            cred = credentials.Certificate(FIREBASE_CREDENTIALS)
            log.info("Firebase-Credentials als Dateipfad erkannt und geladen.")
        else:
            cred_dict = json.loads(FIREBASE_CREDENTIALS)
            cred = credentials.Certificate(cred_dict)
            log.info("Firebase-Credentials als JSON-String erkannt und geladen.")
    except (json.JSONDecodeError, ValueError) as e:
        log.error("FEHLER: FIREBASE_CREDENTIALS ist ungültig: %s", e)
        raise SystemExit("Firebase-Initialisierung fehlgeschlagen. Bitte FIREBASE_CREDENTIALS in .env überprüfen.")
    
    firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_BUCKET})
    _db = firestore.client()
    _bucket = storage.bucket()
    genai.configure(api_key=GEMINI_API_KEY)
    MODEL_IMAGE = genai.GenerativeModel("gemini-1.5-flash")
    MODEL_TRANS = genai.GenerativeModel("gemini-1.5-flash")

# ─────────────────── RATE LIMITING & CACHE ─────────────────
class RateLimiter:
    def __init__(self, rpm: int = 60):
        self.rpm = rpm
        self.last_call = 0
        self.lock = threading.Lock()
    
    def wait(self):
        with self.lock:
            now = time.time()
            time_since_last = now - self.last_call
            if time_since_last < 60.0 / self.rpm:
                time.sleep(60.0 / self.rpm - time_since_last)
            self.last_call = time.time()

class TranslationCache:
    def __init__(self, path: str = "translation_cache.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS translations (text TEXT, lang TEXT, trans TEXT, PRIMARY KEY (text, lang))")
    
    def get(self, text: str, lang: str):
        cursor = self.conn.execute("SELECT trans FROM translations WHERE text = ? AND lang = ?", (text, lang))
        result = cursor.fetchone()
        return result[0] if result else None
    
    def set(self, text: str, lang: str, trans: str):
        self.conn.execute("INSERT OR REPLACE INTO translations (text, lang, trans) VALUES (?, ?, ?)", (text, lang, trans))
        self.conn.commit()

# ─────────────────── RETRY DECORATOR ───────────────────────
def smart_retry(max_retry: int = 4):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retry):
                try:
                    return func(*args, **kwargs)
                except (google_api_exceptions.QuotaExceeded, 
                        google_api_exceptions.ResourceExhausted,
                        http.client.HTTPException,
                        socket.error,
                        urllib3.exceptions.HTTPError) as e:
                    if attempt == max_retry - 1:
                        raise
                    wait_time = 2 ** attempt + 1
                    log.warning("API-Fehler (Versuch %d/%d): %s. Warte %ds...", 
                               attempt + 1, max_retry, e, wait_time)
                    time.sleep(wait_time)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ─────────────────── GEMINI FUNCTIONS ──────────────────────
@smart_retry()
def analyze_image(png_path: Path) -> Tuple[str, List[str]]:
    """Analysiert ein Bild mit Gemini und extrahiert Titel und Tags"""
    _initialize_services()
    
    with open(png_path, "rb") as f:
        image_data = f.read()
    
    prompt = """
    Analysiere dieses Ausmalbild für Kinder und gib mir:
    1. Einen kurzen, kindgerechten Titel (max. 5 Wörter)
    2. 3-5 relevante Tags (nur Substantive, auf Deutsch)
    
    Format: JSON mit "title" und "tags" (Array)
    Beispiel: {"title": "Süßer Hund", "tags": ["hund", "haustier", "tier"]}
    """
    
    response = MODEL_IMAGE.generate_content([prompt, {"mime_type": "image/png", "data": image_data}])
    result = json.loads(response.text)
    return result["title"], result["tags"]

@smart_retry()
def translate_batch(title: str, tags: List[str], lang_name: str, lang_code: str) -> Tuple[str, List[str]]:
    """Übersetzt Titel und Tags in eine Zielsprache"""
    _initialize_services()
    
    prompt = f"""
    Übersetze folgende Texte ins {lang_name}:
    Titel: "{title}"
    Tags: {', '.join(tags)}
    
    Gib die Antwort als JSON zurück:
    {{"title": "übersetzter Titel", "tags": ["tag1", "tag2", "tag3"]}}
    """
    
    response = MODEL_TRANS.generate_content(prompt)
    result = json.loads(response.text)
    return result["title"], result["tags"]

# ─────────────────── CATEGORY MANAGEMENT ───────────────────
def create_main_category(category_id: str, names: Dict[str, str], age_group: str, order: int = 0) -> None:
    """
    Erstellt eine Hauptkategorie in Firestore
    
    Args:
        category_id: z.B. 'kleinkinder-0-5'
        names: Dictionary mit Sprachcodes und Namen
        age_group: Altersgruppe (z.B. '0-5')
        order: Sortierreihenfolge
    """
    _initialize_services()
    
    main_category_doc = {
        'id': category_id,
        'names': names,
        'iconUrl': f"https://storage.googleapis.com/{FIREBASE_BUCKET}/icons/{category_id}.png",
        'subcategoryIds': [],  # Wird später mit Unterkategorien gefüllt
        'ageGroup': age_group,
        'order': order,
        'parentCategoryId': ""  # Leer für Hauptkategorien
    }
    
    # In Firestore speichern
    _db.collection('categories').document(category_id).set(main_category_doc)
    log.info(f"✅ Hauptkategorie erstellt: {category_id}")

def create_subcategory(main_category_id: str, subcategory_data: Dict) -> str:
    """
    Erstellt eine Unterkategorie in Firestore
    
    Args:
        main_category_id: z.B. 'kleinkinder-0-5'
        subcategory_data: Dictionary mit Unterkategorie-Daten
    """
    _initialize_services()
    
    subcategory_doc = {
        'id': subcategory_data['id'],
        'names': subcategory_data['names'],
        'iconUrl': subcategory_data.get('iconUrl', f"https://storage.googleapis.com/{FIREBASE_BUCKET}/icons/{subcategory_data['id']}.png"),
        'subcategoryIds': [],  # Leer für Unterkategorien
        'ageGroup': subcategory_data['ageGroup'],
        'order': subcategory_data.get('order', 0),
        'parentCategoryId': main_category_id  # 🔥 WICHTIG: Verweis auf Hauptkategorie
    }
    
    # In Firestore speichern
    _db.collection('categories').document(subcategory_data['id']).set(subcategory_doc)
    log.info(f"✅ Unterkategorie erstellt: {subcategory_data['id']}")
    
    # Hauptkategorie aktualisieren - Unterkategorie hinzufügen
    main_cat_ref = _db.collection('categories').document(main_category_id)
    main_cat_ref.update({
        'subcategoryIds': firestore.ArrayUnion([subcategory_data['id']])
    })
    log.info(f"✅ Unterkategorie {subcategory_data['id']} zu Hauptkategorie {main_category_id} hinzugefügt")
    
    return subcategory_data['id']

def translate_category_name(category_name: str) -> Dict[str, str]:
    """Übersetzt einen Kategorienamen in alle verfügbaren Sprachen"""
    translations = {}
    translations["de"] = category_name  # Deutsch als Basis
    
    # Übersetze in alle verfügbaren Sprachen
    for lang_name, lang_code in LANG_MAP.items():
        if lang_code == "de":
            continue
            
        try:
            translated_name, _ = translate_batch(category_name, [], lang_name, lang_code)
            translations[lang_code] = translated_name
        except Exception as e:
            log.warning("Übersetzung von '%s' nach %s fehlgeschlagen: %s", category_name, lang_name, e)
            translations[lang_code] = category_name  # Fallback
    
    return translations

# ─────────────────── IMAGE PROCESSING ──────────────────────
def upload(local: Path, blob_name: str, mime: str) -> str:
    """Lädt eine Datei zu Firebase Storage hoch"""
    _initialize_services()
    blob = _bucket.blob(blob_name)
    blob.upload_from_filename(str(local), content_type=mime)
    return blob.public_url

def sha256(path: Path) -> str:
    """Berechnet SHA256-Hash einer Datei"""
    hash_sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def upload_image_with_subcategory(image_data: Dict, subcategory_id: str) -> None:
    """
    Lädt ein Bild mit Unterkategorie-Referenz hoch
    
    Args:
        image_data: Dictionary mit Bilddaten
        subcategory_id: ID der Unterkategorie
    """
    _initialize_services()
    
    # Bild-Metadaten
    image_doc = {
        'id': image_data['id'],
        'titles': image_data['titles'],
        'categoryId': subcategory_id,  # 🔥 WICHTIG: Verweis auf Unterkategorie
        'tags': image_data['tags'],
        'svgPath': f"images/{subcategory_id}/{image_data['id']}.svg",
        'thumbnailPath': f"thumbnails/{subcategory_id}/{image_data['id']}.png",
        'timestamp': firestore.SERVER_TIMESTAMP,
        'ageGroup': image_data['ageGroup'],
        'popularity': 0,
        'isNew': True
    }
    
    # In Firestore speichern
    _db.collection('images').document(image_data['id']).set(image_doc)
    log.info(f"✅ Bild hochgeladen: {image_data['id']} in Kategorie {subcategory_id}")

# ─────────────────── UTILITY FUNCTIONS ─────────────────────
def check_inkscape():
    """Prüft ob Inkscape verfügbar ist"""
    try:
        result = subprocess.run([INKSCAPE_PATH, "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            log.info("✅ Inkscape gefunden: %s", result.stdout.strip().split('\n')[0])
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    log.error("❌ Inkscape nicht gefunden. Bitte installieren oder INKSCAPE_PATH setzen.")
    return False

def check_potrace():
    """Prüft ob Potrace verfügbar ist"""
    try:
        result = subprocess.run([POTRACE_PATH, "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            log.info("✅ Potrace gefunden: %s", result.stdout.strip())
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    log.error("❌ Potrace nicht gefunden. Bitte installieren oder POTRACE_PATH setzen.")
    return False

def _ensure_black_fill_and_stroke(svg_content: str) -> str:
    """Stellt sicher, dass SVG-Pfade schwarze Füllung und Strich haben"""
    def _replace_style(match: re.Match) -> str:
        style = match.group(1)
        if 'fill:' not in style:
            style += ';fill:#000000'
        if 'stroke:' not in style:
            style += ';stroke:#000000'
        return f'style="{style}"'
    
    return re.sub(r'style="([^"]*)"', _replace_style, svg_content)

def preprocess_png(src: Path, dest: Path) -> None:
    """Bereitet PNG für Vektorisierung vor"""
    with Image.open(src) as img:
        img = img.convert('L')  # Graustufen
        img = ImageOps.invert(img)  # Invertieren für Potrace
        img.save(dest, 'PNG')

def _get_svg_bounds(svg_path: Path) -> Tuple[float, float, float, float]:
    """Ermittelt die Bounds eines SVG"""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    # Versuche viewBox zu finden
    viewbox = root.get('viewBox')
    if viewbox:
        parts = viewbox.split()
        if len(parts) == 4:
            return float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
    
    # Fallback: width/height
    width = float(root.get('width', 100))
    height = float(root.get('height', 100))
    return 0, 0, width, height

def _validate_svg(svg_path: Path) -> bool:
    """Validiert ein SVG"""
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # Prüfe auf SVG-Element
        if root.tag != '{http://www.w3.org/2000/svg}svg':
            log.error("❌ Ungültiges SVG: Kein SVG-Root-Element")
            return False
        
        # Prüfe auf Pfade oder andere Vektorelemente
        paths = root.findall('.//{http://www.w3.org/2000/svg}path')
        if not paths:
            log.error("❌ Ungültiges SVG: Keine Pfade gefunden")
            return False
        
        # Prüfe Dateigröße
        if svg_path.stat().st_size < 100:
            log.error("❌ Ungültiges SVG: Datei zu klein")
            return False
        
        log.info("✅ SVG validiert: %d Pfade, %d Bytes", len(paths), svg_path.stat().st_size)
        return True
        
    except ET.ParseError as e:
        log.error("❌ Ungültiges SVG: Parse-Fehler: %s", e)
        return False

def _validate_thumbnail(png_path: Path) -> bool:
    """Validiert ein Thumbnail"""
    try:
        with Image.open(png_path) as img:
            width, height = img.size
            
            # Prüfe Mindestgröße
            if width < 100 or height < 100:
                log.error("❌ Thumbnail zu klein: %dx%d", width, height)
                return False
            
            # Prüfe A4-Verhältnis (210:297 ≈ 0.707)
            ratio = width / height
            expected_ratio = A4_WIDTH_MM / A4_HEIGHT_MM
            if abs(ratio - expected_ratio) > THUMB_RATIO_TOLERANCE:
                log.error("❌ Thumbnail-Verhältnis falsch: %.3f (erwartet: %.3f)", ratio, expected_ratio)
                return False
            
            log.info("✅ Thumbnail validiert: %dx%d (Ratio: %.3f)", width, height, ratio)
            return True
            
    except Exception as e:
        log.error("❌ Thumbnail-Validierung fehlgeschlagen: %s", e)
        return False

# ─────────────────── SVG PROCESSING ────────────────────────
def trace_png_to_svg(png_path: Path, svg_out: Path):
    """Konvertiert PNG zu SVG mit Potrace"""
    log.info("Konvertiere PNG zu SVG: %s", png_path.name)
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pgm_path = tmp_path / "temp.pgm"
        
        # PNG zu PGM konvertieren
        subprocess.run([
            "convert", str(png_path), "-threshold", "50%", str(pgm_path)
        ], check=True, capture_output=True)
        
        # PGM zu SVG mit Potrace
        subprocess.run([
            POTRACE_PATH, str(pgm_path), 
            "-s", "-o", str(svg_out),
            "--turdsize", "2",
            "--alphamax", "1",
            "--opttolerance", "0.2"
        ], check=True, capture_output=True)
    
    # SVG-Inhalt optimieren
    with open(svg_out, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = _ensure_black_fill_and_stroke(content)
    
    with open(svg_out, 'w', encoding='utf-8') as f:
        f.write(content)
    
    log.info("✅ PNG zu SVG konvertiert: %s", svg_out.name)

def create_a4_canvas(svg_in: Path, svg_a4_out: Path):
    """Erstellt ein A4-SVG mit dem Vektorbild zentriert"""
    log.info("Erstelle A4-Canvas für: %s", svg_in.name)
    
    # SVG-Bounds ermitteln
    x, y, width, height = _get_svg_bounds(svg_in)
    
    # A4-Dimensionen in Pixeln (96 DPI)
    a4_width_px = int(A4_WIDTH_MM * DEFAULT_DPI / 25.4)
    a4_height_px = int(A4_HEIGHT_MM * DEFAULT_DPI / 25.4)
    
    # Skalierung berechnen (mit 10mm Rand)
    margin_px = int(10 * DEFAULT_DPI / 25.4)
    max_width = a4_width_px - 2 * margin_px
    max_height = a4_height_px - 2 * margin_px
    
    scale_x = max_width / width
    scale_y = max_height / height
    scale = min(scale_x, scale_y)
    
    # Neue Dimensionen
    new_width = width * scale
    new_height = height * scale
    
    # Position (zentriert)
    pos_x = (a4_width_px - new_width) / 2
    pos_y = (a4_height_px - new_height) / 2
    
    # A4-SVG erstellen
    a4_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{a4_width_px}" height="{a4_height_px}" 
     viewBox="0 0 {a4_width_px} {a4_height_px}">
  <style>
    path {{ fill: #000000; stroke: #000000; stroke-width: 0.5; }}
  </style>
  <g transform="translate({pos_x}, {pos_y}) scale({scale})">
    {open(svg_in, 'r', encoding='utf-8').read().split('<svg')[1].split('>', 1)[1].rsplit('</svg>', 1)[0]}
  </g>
</svg>'''
    
    with open(svg_a4_out, 'w', encoding='utf-8') as f:
        f.write(a4_svg)
    
    log.info("✅ A4-Canvas erstellt: %s", svg_a4_out.name)

def create_thumbnail(svg_path: Path, thumb_out: Path):
    """Erstellt ein Thumbnail aus SVG"""
    log.info("Erstelle Thumbnail für: %s", svg_path.name)
    
    # SVG zu PNG mit Inkscape
    subprocess.run([
        INKSCAPE_PATH, str(svg_path),
        "--export-filename", str(thumb_out),
        "--export-width", str(TARGET_THUMB_WIDTH_PX),
        "--export-background", "white"
    ], check=True, capture_output=True)
    
    log.info("✅ Thumbnail erstellt: %s", thumb_out.name)

# ─────────────────── MAIN PIPELINE ─────────────────────────
def process_image_with_categories(png_path: Path, main_category_id: str, subcategory_data: Dict) -> None:
    """
    Verarbeitet ein Bild und lädt es mit korrekter Kategorie-Referenz hoch
    
    Args:
        png_path: Pfad zur PNG-Datei
        main_category_id: ID der Hauptkategorie (z.B. 'kleinkinder-0-5')
        subcategory_data: Dictionary mit Unterkategorie-Daten
    """
    log.info("Starte Verarbeitung von Bild: %s", png_path.name)
    _initialize_services()
    
    # Prüfe ob bereits verarbeitet
    file_hash = sha256(png_path)
    if _db.collection("processed_files").document(file_hash).get().exists:
        log.info("%s wurde bereits verarbeitet (Hash: %s) – übersprungen.", png_path.name, file_hash)
        return
    
    try:
        # 1. Bild validieren
        Image.open(png_path).verify()
        
        # 2. Gemini-Analyse
        log.info("Analysiere Bild mit Gemini...")
        motif_de, tags_de = analyze_image(png_path)
        log.info("Analyse abgeschlossen: Motiv='%s', Tags='%s'", motif_de, tags_de)
        
        # 3. Übersetzungen
        log.info("Übersetze Metadaten...")
        translations = {}
        for lang_name, lang_code in LANG_MAP.items():
            if lang_code == "de":
                translations[lang_code] = {"title": motif_de, "tags": tags_de}
            else:
                translated_title, translated_tags = translate_batch(motif_de, tags_de, lang_name, lang_code)
                translations[lang_code] = {"title": translated_title, "tags": translated_tags}
        
        # 4. SVG und Thumbnail erstellen
        log.info("Erstelle SVG und Thumbnail...")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            svg_raw = tmp_path / "raw.svg"
            svg_a4 = tmp_path / "a4.svg"
            thumb_png = tmp_path / "thumb.png"
            
            trace_png_to_svg(png_path, svg_raw)
            create_a4_canvas(svg_raw, svg_a4)
            create_thumbnail(svg_a4, thumb_png)
            
            # Qualitätsprüfung
            if not (_validate_svg(svg_a4) and _validate_thumbnail(thumb_png)):
                raise ValueError("Qualitätsprüfung fehlgeschlagen")
            
            # 5. Dateien hochladen
            log.info("Lade Dateien zu Firebase Storage hoch...")
            svg_blob_name = f"images/{subcategory_data['id']}/{png_path.stem}.svg"
            thumb_blob_name = f"thumbnails/{subcategory_data['id']}/{png_path.stem}.png"
            
            upload(svg_a4, svg_blob_name, "image/svg+xml")
            upload(thumb_png, thumb_blob_name, "image/png")
        
        # 6. Unterkategorie erstellen
        log.info("Erstelle Unterkategorie...")
        subcategory_id = create_subcategory(main_category_id, subcategory_data)
        
        # 7. Bild-Metadaten in Firestore speichern
        log.info("Speichere Metadaten in Firestore...")
        
        # Tags in allen Sprachen sammeln
        all_tags = set()
        for lang_code, translation_data in translations.items():
            all_tags.update(translation_data["tags"])
        combined_tags = list(all_tags)
        
        # Bild-Metadaten
        image_data = {
            'id': png_path.stem,
            'titles': {lc: d["title"] for lc, d in translations.items()},
            'categoryId': subcategory_id,  # 🔥 WICHTIG: Verweis auf Unterkategorie
            'tags': combined_tags,
            'svgPath': f"images/{subcategory_id}/{png_path.stem}.svg",
            'thumbnailPath': f"thumbnails/{subcategory_id}/{png_path.stem}.png",
            'timestamp': firestore.SERVER_TIMESTAMP,
            'ageGroup': subcategory_data['ageGroup'],
            'popularity': 0,
            'isNew': True
        }
        
        # In Firestore speichern
        _db.collection('images').document(png_path.stem).set(image_data)
        
        # Als verarbeitet markieren
        _db.collection("processed_files").document(file_hash).set({"ts": firestore.SERVER_TIMESTAMP})
        
        log.info("✅ Bild %s vollständig verarbeitet und hochgeladen", png_path.name)
        
    except Exception as e:
        log.error("❌ Fehler bei der Verarbeitung von %s: %s", png_path.name, e)
        raise

def main():
    """Hauptfunktion des Pipeline-Skripts"""
    log.info("🚀 Starte Firebase Pipeline-Skript")
    
    # Dependencies prüfen
    if not check_inkscape():
        return
    if not check_potrace():
        return
    
    _initialize_services()
    
    # Beispiel: Hauptkategorie erstellen
    main_category_data = {
        'id': 'kleinkinder-0-5',
        'names': translate_category_name('Kleinkinder 0-5'),
        'ageGroup': '0-5',
        'order': 1
    }
    
    create_main_category(**main_category_data)
    
    # Beispiel: Unterkategorien erstellen
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
        }
    ]
    
    for subcategory in subcategories:
        create_subcategory('kleinkinder-0-5', subcategory)
    
    # Beispiel: Bilder verarbeiten (falls vorhanden)
    if BASE_IMAGE_DIRECTORY.exists():
        log.info("Verarbeite Bilder aus: %s", BASE_IMAGE_DIRECTORY)
        
        for png_file in BASE_IMAGE_DIRECTORY.glob("**/*.png"):
            # Kategorie aus Ordnerstruktur ableiten
            relative_path = png_file.relative_to(BASE_IMAGE_DIRECTORY)
            parts = relative_path.parts
            
            if len(parts) >= 2:
                main_cat = parts[0]
                sub_cat = parts[1]
                
                # Unterkategorie-Daten erstellen
                subcategory_data = {
                    'id': f"{sub_cat}-kleinkinder",
                    'names': translate_category_name(sub_cat),
                    'ageGroup': '0-5',
                    'order': 1
                }
                
                try:
                    process_image_with_categories(png_file, 'kleinkinder-0-5', subcategory_data)
                except Exception as e:
                    log.error("Fehler bei %s: %s", png_file.name, e)
                    continue
    
    log.info("✅ Pipeline-Skript abgeschlossen")

if __name__ == "__main__":
    main()