# -*- coding: utf-8 -*-
"""
Printable Content-Pipeline (KORRIGIERT)
---------------------------------------
• Wandelt PNG-Ausmalbilder in **echte SVG-Vektoren** über *potrace*
• Erzeugt A4-SVGs mit Rand (Verhältnis 210:297) inklusive Style-Block
• Erzeugt A4-Thumbnails (Breite fest, Höhe A4-Verhältnis)
• Prüft automatisch die Qualität von SVG und Thumbnail
• Analysiert Motive & Tags mit **Gemini Flash 1.5**
• Übersetzt Titel + Tags in 20 Sprachen (Cache in SQLite)
• Lädt SVG & Thumbnail nach Firebase Storage und legt Metadaten in Firestore ab
• KORRIGIERT: Kompatibel mit Flutter-App Datenstruktur
"""
from __future__ import annotations
import os, re, json, time, uuid, hashlib, tempfile, logging, threading, subprocess
import xml.etree.ElementTree as ET
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple, Dict, List
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

# ERWEITERTE SPRACH-MAP MIT 100 SPRACHEN (basierend auf den meist gesprochenen Sprachen der Welt)
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

# KORRIGIERT: Flexible Pfade
BASE_IMAGE_DIRECTORY = Path(os.getenv("BASE_IMAGE_DIRECTORY", "./images"))
CACHE_DIRECTORY = Path(os.getenv("CACHE_DIRECTORY", "./cache"))
# ──────────────────────── LOGGING ──────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s | %(message)s",
                    handlers=[logging.FileHandler("processing.log", encoding="utf-8"),
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
# ────────────────────── HILFSKLASSEN ───────────────────────
class RateLimiter:
    def __init__(self, rpm: int = 60):
        self.rpm = rpm
        self._lock = threading.Lock()
        self._times: List[dt.datetime] = []
    def wait(self):
        with self._lock:
            now = dt.datetime.now()
            self._times = [t for t in self._times if (now - t).seconds < 60]
            if len(self._times) >= self.rpm:
                sleep_duration = 60 - (now - self._times[0]).seconds + 1
                log.warning("Rate-Limit erreicht – warte %.1fs", sleep_duration)
                time.sleep(sleep_duration)
            self._times.append(dt.datetime.now())
rate = RateLimiter()
class TranslationCache:
    def __init__(self, path: str = "translation_cache.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS tcache (
                                orig TEXT, lang TEXT, trans TEXT,
                                PRIMARY KEY(orig, lang))""")
        self.lock = threading.Lock()
    def get(self, text: str, lang: str):
        with self.lock:
            cur = self.conn.execute("SELECT trans FROM tcache WHERE orig=? AND lang=?", (text, lang))
            row = cur.fetchone()
            return row[0] if row else None
    def set(self, text: str, lang: str, trans: str):
        with self.lock:
            self.conn.execute("INSERT OR REPLACE INTO tcache VALUES (?,?,?)", (text, lang, trans))
            self.conn.commit()
# KORRIGIERT: Flexible Cache-Pfade
os.makedirs(CACHE_DIRECTORY, exist_ok=True)
cache = TranslationCache(CACHE_DIRECTORY / "translation_cache.db")
# ────────────────────── GEMINI CALLS ───────────────────────
def smart_retry(max_retry: int = 4):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retry):
                try:
                    rate.wait()
                    return func(*args, **kwargs)
                except (
                    google_api_exceptions.ResourceExhausted,
                    google_api_exceptions.InternalServerError,
                    google_api_exceptions.ServiceUnavailable,
                    http.client.RemoteDisconnected,
                    socket.timeout,
                    TimeoutError,
                    urllib3.exceptions.ProtocolError
                ) as e:
                    log.warning("%s fehlgeschlagen (%s). Versuch %d/%d", func.__name__, e, attempt+1, max_retry)
                    time.sleep(2 ** attempt)
                except Exception as e:
                    log.error("%s unerwarteter Fehler: %s.", func.__name__, e, exc_info=True)
                    raise
            raise RuntimeError(f"{func.__name__} permanent fehlgeschlagen nach {max_retry} Versuchen.")
        return wrapper
    return decorator
@smart_retry()
def analyze_image(png_path: Path) -> Tuple[str, List[str]]:
    with Image.open(png_path) as img:
        prompt = (
            "Analysiere das gezeigte Ausmalbild für eine Ausmalbilder-Druck-App. "
            "Gib mir **nur** maximal 5 präzise Begriffe, die das Motiv beschreiben, "
            "ohne generische Wörter wie 'Ausmalbild', 'schwarz-weiss', 'Illustration' oder 'Zeichnung'. "
            "Antworte exakt in folgendem Format:\n"
            "MOTIV: <kurze, konkrete Phrase>\n"
            "TAGS: <kommagetrennte, nur relevante Kategorien>"
        )
        resp = MODEL_IMAGE.generate_content([prompt, img])
        text_content = resp.text.strip()
        motif_match = re.search(r"MOTIV:(.*)", text_content, re.I)
        tags_match = re.search(r"TAGS:(.*)", text_content, re.I)
        motif = motif_match.group(1).strip() if motif_match else "Unbekanntes Motiv"
        tags = [t.strip() for t in tags_match.group(1).split(',') if t.strip()] if tags_match else []
        if not motif or not tags:
            log.warning("Gemini Analyse für %s unvollständig: Motiv='%s', Tags='%s'. Antwort: %s", png_path.name, motif, tags, text_content)
        return motif, tags
@smart_retry()
def translate_batch(title: str, tags: List[str], lang_name: str, lang_code: str) -> Tuple[str, List[str]]:
    cached_title = cache.get(title, lang_code)
    cached_tags = [cache.get(t, lang_code) for t in tags]
    if cached_title and all(cached_tags):
        return cached_title, cached_tags
    prompt = (
        f"Übersetze folgenden Titel und die Tags ins {lang_name}.\n"
        "Antwortformat GENAU so:\nTITEL: <...>\nTAGS: <tag1, tag2, ...>\n\n"
        f"Titel: {title}\nTags: {', '.join(tags)}"
    )
    resp = MODEL_TRANS.generate_content(prompt).text.strip()
    m_title = re.search(r"TITEL:\s*(.+)", resp, re.I)
    m_tags = re.search(r"TAGS:\s*(.+)", resp, re.I)
    tr_title = m_title.group(1).strip() if m_title else title
    tr_tags = [t.strip() for t in m_tags.group(1).split(',')] if m_tags else tags
    cache.set(title, lang_code, tr_title)
    for o, n in zip(tags, tr_tags):
        cache.set(o, lang_code, n)
    return tr_title, tr_tags
# ──────────────── INKSCAPE-HILFSFUNKTIONEN ────────────────
def check_inkscape():
    log.info("Prüfe Inkscape 1.2-Kompatibilität...")
    try:
        result = subprocess.run(
            [INKSCAPE_PATH, "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            text=True
        )
        version_output = result.stdout
        if "1.2" not in version_output:
            log.warning("Inkscape-Version ist nicht 1.2: %s. Skript ist für 1.2 optimiert.", version_output)
    except FileNotFoundError:
        log.error("FEHLER: Inkscape nicht gefunden. Installiere Inkscape 1.2 oder setze INKSCAPE_PATH in .env.")
        raise SystemExit("Inkscape nicht gefunden.")
    except subprocess.CalledProcessError as e:
        log.error("FEHLER: Inkscape --version fehlgeschlagen: %s", e.stderr)
        raise SystemExit("Inkscape --version fehlgeschlagen.")
def check_potrace():
    try:
        subprocess.run(
            [POTRACE_PATH, "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except FileNotFoundError:
        log.error("FEHLER: potrace nicht gefunden. Installiere es oder setze POTRACE_PATH.")
        raise SystemExit("potrace nicht gefunden.")
    except subprocess.CalledProcessError as e:
        log.error("FEHLER: potrace --version fehlgeschlagen: %s", e.stderr.decode())
        raise SystemExit("potrace --version fehlgeschlagen.")

# ──────────────── SVG PROCESSING FUNKTIONEN ────────────────
def _ensure_black_fill_and_stroke(svg_content: str) -> str:
    def _replace_style(match: re.Match) -> str:
        style = match.group(1)
        pairs = [s.strip() for s in style.split(";") if ":" in s]
        style_dict = {k.strip(): v.strip() for k, v in (p.split(":", 1) for p in pairs)}
        style_dict["fill"] = "#000000"
        style_dict["stroke"] = "none"
        return 'style="' + ";".join(f"{k}:{v}" for k, v in style_dict.items()) + '"'

    svg_content = re.sub(r'style="([^"]*)"', _replace_style, svg_content)
    svg_content = re.sub(r'fill="[^"]*"', 'fill="#000000"', svg_content)
    svg_content = re.sub(r'stroke="[^"]*"', 'stroke="none"', svg_content)
    log.info("Erzwungene schwarze Füllung und keine Striche in SVG.")
    return svg_content

def preprocess_png(src: Path, dest: Path) -> None:
    img = Image.open(src).convert("L")
    img = ImageOps.autocontrast(img)
    bbox = ImageOps.invert(img).getbbox()
    if bbox:
        img = img.crop(bbox)
    img.save(dest)

def _get_svg_bounds(svg_path: Path) -> Tuple[float, float, float, float]:
    """
    Liefert (x, y, w, h) des Koordinatensystems des importierten SVGs.
    Für die meisten von potrace erzeugten Dateien genügt die viewBox.
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()

    if "viewBox" in root.attrib:
        x, y, w, h = map(float, root.attrib["viewBox"].split())
    else:  # Fallback, sollte kaum noch vorkommen
        x = y = 0.0
        w = float(root.get("width", "0").replace("px", "") or 1)
        h = float(root.get("height", "0").replace("px", "") or 1)
    return x, y, w, h

def _validate_svg(svg_path: Path) -> bool:
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
    except ET.ParseError as e:
        log.error("SVG-Parsing-Fehler: %s", e)
        return False
    expected_w = int(A4_WIDTH_MM * DEFAULT_DPI / 25.4)
    expected_h = int(A4_HEIGHT_MM * DEFAULT_DPI / 25.4)
    width = root.get("width", "0").replace("px", "")
    height = root.get("height", "0").replace("px", "")
    try:
        if int(float(width)) != expected_w or int(float(height)) != expected_h:
            log.error("SVG hat unerwartete Dimensionen: %sx%s", width, height)
            return False
    except ValueError:
        log.error("SVG width/height nicht numerisch: %s/%s", width, height)
        return False
    target_tags = {"path", "rect", "circle", "ellipse", "polygon", "polyline", "line"}
    if not any(elem.tag.split('}')[-1] in target_tags for elem in root.iter()):
        log.error("SVG enthält keine Vektorelemente")
        return False
    svg_content = Path(svg_path).read_text(encoding="utf-8")
    if "fill:#000" not in svg_content and "fill:#000000" not in svg_content:
        log.error("SVG nicht schwarz gefärbt")
        return False
    for elem in root.iter():
        if elem.get('fill') and elem.get('fill') != '#000000':
            log.error("SVG enthält nicht-schwarze Füllungen: %s", elem.get('fill'))
            return False
        if elem.get('stroke') and elem.get('stroke') != 'none':
            log.error("SVG enthält Striche: %s", elem.get('stroke'))
            return False
    return True

def _validate_thumbnail(png_path: Path) -> bool:
    try:
        img = Image.open(png_path)
    except Exception as e:
        log.error("Thumbnail konnte nicht geöffnet werden: %s", e)
        return False
    if img.width != TARGET_THUMB_WIDTH_PX:
        log.error("Thumbnail-Breite falsch: %d", img.width)
        return False
    expected_ratio = A4_HEIGHT_MM / A4_WIDTH_MM
    actual_ratio = img.height / img.width
    if abs(actual_ratio - expected_ratio) > THUMB_RATIO_TOLERANCE:
        log.error("Thumbnail-Seitenverhältnis abweichend: %.3f", actual_ratio)
        return False
    lo, hi = img.convert("L").getextrema()
    if hi - lo < 20:
        log.error("Thumbnail-Kontrast zu niedrig")
        return False
    return True

# Tools prüfen
check_inkscape()
check_potrace()
# ──────────────── STORAGE & KATEGORIEN ────────────────────
def upload(local: Path, blob_name: str, mime: str) -> str:
    log.info("Hochladen von %s zu Firebase Storage (%s)...", local.name, blob_name)
    blob = _bucket.blob(blob_name)
    blob.upload_from_filename(str(local), content_type=mime)
    log.info("Hochladen erfolgreich: %s", blob_name)
    return blob.name

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def translate_category_name(category_name: str) -> Dict[str, str]:
    """
    Übersetzt einen Kategorienamen in alle verfügbaren Sprachen
    """
    translations = {"de": category_name}  # Deutsch als Ausgangssprache
    
    # Auswahl der wichtigsten Sprachen für Kategorien
    priority_languages = {
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
        "Türkisch": "tr"
    }
    
    for lang_name, lang_code in priority_languages.items():
        try:
            # Verwende die bestehende Übersetzungsfunktion
            translated_name, _ = translate_batch(category_name, [], lang_name, lang_code)
            translations[lang_code] = translated_name
        except Exception as e:
            log.warning("Übersetzung von '%s' nach %s fehlgeschlagen: %s", category_name, lang_name, e)
            translations[lang_code] = category_name  # Fallback zur ursprünglichen Sprache
    
    return translations
# KORRIGIERT: Kategorien für Flutter-App kompatible Struktur
def create_categories(main_cat: str, sub_cat: str) -> str:
    """
    Erstellt Kategorien in flacher Struktur für Flutter-App Kompatibilität
    """
    _initialize_services()
    
    # Hauptkategorie erstellen/aktualisieren
    main_cat_id = re.sub(r"[^a-z0-9]+", "-", main_cat.lower())
    
    # Multi-language names für Hauptkategorie mit echten Übersetzungen
    main_cat_names = translate_category_name(main_cat)
    
    # Altersgruppe basierend auf Kategorie bestimmen
    if "kleinkinder" in main_cat.lower() or "0-5" in main_cat:
        age_group = "0-5"
    elif "schulkinder" in main_cat.lower() or "6-12" in main_cat:
        age_group = "6-12"
    elif "erwachsene" in main_cat.lower() or "jugendliche" in main_cat.lower() or "13-99" in main_cat:
        age_group = "13-99"
    else:
        age_group = "6-12"  # Standard-Altersgruppe
    
    main_cat_doc = {
        "id": main_cat_id,
        "names": main_cat_names,  # KORRIGIERT: names statt nameKey
        "iconUrl": f"https://storage.googleapis.com/{FIREBASE_BUCKET}/icons/{main_cat_id}.png",  # KORRIGIERT: iconUrl hinzugefügt
        "subcategoryIds": [],  # KORRIGIERT: subcategoryIds hinzugefügt (wird später gefüllt)
        "ageGroup": age_group,  # KORRIGIERT: ageGroup hinzugefügt
        "parentCategoryId": "",  # KORRIGIERT: leerer String statt None
        "order": 0
    }
    
    # Nur setzen wenn noch nicht existiert
    main_cat_ref = _db.collection("categories").document(main_cat_id)
    if not main_cat_ref.get().exists:
        main_cat_ref.set(main_cat_doc)
        log.info("Hauptkategorie erstellt: %s", main_cat)
    
    # Subkategorie erstellen/aktualisieren
    sub_cat_id = f"{main_cat_id}_{re.sub(r'[^a-z0-9]+', '-', sub_cat.lower())}"
    
    # Multi-language names für Subkategorie mit echten Übersetzungen
    sub_cat_names = translate_category_name(sub_cat)
    
    sub_cat_doc = {
        "id": sub_cat_id,
        "names": sub_cat_names,  # KORRIGIERT: names statt nameKey
        "iconUrl": f"https://storage.googleapis.com/{FIREBASE_BUCKET}/icons/{sub_cat_id}.png",  # KORRIGIERT: iconUrl hinzugefügt
        "subcategoryIds": [],  # KORRIGIERT: subcategoryIds hinzugefügt (leer für Subkategorien)
        "ageGroup": age_group,  # KORRIGIERT: ageGroup hinzugefügt
        "parentCategoryId": main_cat_id,  # KORRIGIERT: String statt None
        "order": 0
    }
    
    # Nur setzen wenn noch nicht existiert
    sub_cat_ref = _db.collection("categories").document(sub_cat_id)
    if not sub_cat_ref.get().exists:
        sub_cat_ref.set(sub_cat_doc)
        log.info("Subkategorie erstellt: %s", sub_cat)
        
        # Subkategorie-ID zur Hauptkategorie hinzufügen
        main_cat_ref.update({
            "subcategoryIds": firestore.ArrayUnion([sub_cat_id])
        })
        log.info("Subkategorie %s zur Hauptkategorie %s hinzugefügt", sub_cat_id, main_cat_id)
    
    return sub_cat_id
# ───────────────────────── WORKER ───────────────────────────
def process_png(png_path: Path, main_cat: str, sub_cat: str):
    log.info("Starte Verarbeitung von Bild: %s (Kategorie: %s/%s)", png_path.name, main_cat, sub_cat)
    _initialize_services()
    
    file_hash = sha256(png_path)
    if _db.collection("processed_files").document(file_hash).get().exists:
        log.info("%s wurde bereits verarbeitet (Hash: %s) – übersprungen.", png_path.name, file_hash)
        return "skipped"
    
    try:
        Image.open(png_path).verify()
    except Exception as e:
        raise ValueError(f"Ungültige oder beschädigte PNG-Datei: {e}")
    
    log.info("Schritt 1: Starte Gemini-Analyse für %s...", png_path.name)
    motif_de, tags_de = analyze_image(png_path)
    log.info("Analyse abgeschlossen: Motiv='%s', Tags='%s'", motif_de, tags_de)
    log.info("Schritt 2: Übersetze Metadaten...")
    translations = {}
    for lang_name, lang_code in LANG_MAP.items():
        if lang_code == "de":
            translations[lang_code] = {"title": motif_de, "tags": tags_de}
        else:
            translated_title, translated_tags = translate_batch(motif_de, tags_de, lang_name, lang_code)
            translations[lang_code] = {"title": translated_title, "tags": translated_tags}
    log.info("Übersetzungen abgeschlossen.")
    log.info("Schritt 3: Erstelle SVG und Thumbnail...")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        svg_raw = tmp_path / "raw.svg"
        svg_a4 = tmp_path / "a4.svg"
        thumb_png = tmp_path / "thumb.png"

        # SVG-Verarbeitung (vereinfacht für Beispiel)
        # SVG-Verarbeitung mit Kontrast-Boost und Qualitätsprüfung
        trace_png_to_svg(png_path, svg_raw)
        create_a4_canvas(svg_raw, svg_a4)
        create_thumbnail(svg_a4, thumb_png)

        # Qualitätsprüfung der erzeugten Dateien
        if not (_validate_svg(svg_a4) and _validate_thumbnail(thumb_png)):
            raise ValueError("Qualitätsprüfung fehlgeschlagen")

        # Slug für eindeutige Dateinamen
        slug = re.sub(r"[^a-z0-9]+", "-", motif_de.lower())
        slug = slug[:50].strip('-') or "bild"
        slug += "-" + uuid.uuid4().hex[:6]
        
        svg_blob_name = f"{main_cat}/{sub_cat}/{slug}.svg"
        png_blob_name = f"{main_cat}/{sub_cat}/{slug}.png"
        
        log.info("Schritt 4: Lade Dateien zu Firebase Storage hoch...")
        upload(svg_a4, svg_blob_name, "image/svg+xml")
        upload(thumb_png, png_blob_name, "image/png")
        
        log.info("Schritt 5: Erstelle Kategorien...")
        category_id = create_categories(main_cat, sub_cat)
        
        log.info("Schritt 6: Speichere Metadaten in Firestore...")
        
        # Altersgruppe basierend auf Kategorie bestimmen
        if "kleinkinder" in main_cat.lower() or "0-5" in main_cat:
            age_group = "0-5"
        elif "schulkinder" in main_cat.lower() or "6-12" in main_cat:
            age_group = "6-12"
        elif "erwachsene" in main_cat.lower() or "jugendliche" in main_cat.lower() or "13-99" in main_cat:
            age_group = "13-99"
        else:
            age_group = "6-12"  # Standard-Altersgruppe
        
        # Tags in ALLEN 100 Sprachen sammeln
        all_tags = set()
        for lang_code, translation_data in translations.items():
            all_tags.update(translation_data["tags"])
        combined_tags = list(all_tags)
        
        # KORRIGIERT: Bild-Metadaten für Flutter-App kompatible Struktur
        image_doc = {
            "id": slug,
            "titles": {lc: d["title"] for lc, d in translations.items()},  # KORRIGIERT: title → titles
            "ageGroup": age_group,  # KORRIGIERT: ageGroup hinzugefügt
            "tags": combined_tags,  # KORRIGIERT: tags als Liste statt Dictionary
            "thumbnailPath": png_blob_name,  # Pfad für Flutter-App
            "svgPath": svg_blob_name,        # Pfad für Flutter-App
            "categoryId": category_id,       # Direkte Referenz zur Kategorie
            "isNew": True,
            "popularity": 0,
            "timestamp": firestore.SERVER_TIMESTAMP,  # KORRIGIERT: korrekte Timestamp-Verwendung
        }
        
        # KORRIGIERT: Bild in flacher collection speichern
        _db.collection("images").document(slug).set(image_doc)
        
        # Hash als verarbeitet markieren
        _db.collection("processed_files").document(file_hash).set({"ts": firestore.SERVER_TIMESTAMP})
        
        log.info("Metadaten in Firestore gespeichert.")
        png_path.unlink(missing_ok=True)
        log.info("Bild %s vollständig verarbeitet und hochgeladen. Original-PNG gelöscht.", png_path.name)
        return "processed"
# ─────────────────────────── MAIN ──────────────────────────
def main():
    log.info("Starte Bildverarbeitung von Basis-Verzeichnis: %s", BASE_IMAGE_DIRECTORY)
    files_to_process: List[Tuple[Path, str, str]] = []
    
    if not BASE_IMAGE_DIRECTORY.is_dir():
        log.error("FEHLER: Basis-Ordner nicht gefunden: %s", BASE_IMAGE_DIRECTORY)
        return
    
    for folder in BASE_IMAGE_DIRECTORY.iterdir():
        if folder.is_dir():
            parts = folder.name.split("_")
            main_cat = parts[0].strip() if parts else ""
            sub_cat = parts[1].strip() if len(parts) >= 2 else "Allgemein"
            
            if not main_cat:
                log.warning("Ungültiger Ordnername '%s'. Übersprungen.", folder.name)
                continue
            
            png_files_in_folder = list(folder.glob("*.png"))
            if not png_files_in_folder:
                log.info("Keine PNGs in Ordner '%s'.", folder.name)
                continue
            
            for p in png_files_in_folder:
                files_to_process.append((p, main_cat, sub_cat))
            
            log.info("Gefunden: %d PNGs in Ordner '%s' (Kategorie: %s/%s)", 
                    len(png_files_in_folder), folder.name, main_cat, sub_cat)
        else:
            log.info("'%s' ist kein Verzeichnis. Übersprungen.", folder.name)
    
    if not files_to_process:
        log.info("Keine PNGs gefunden. Beende.")
        return
    
    log.info("Beginne Verarbeitung von %d Bildern mit %d parallelen Prozessen...", 
             len(files_to_process), MAX_PARALLEL)
    
    stats = {"processed": 0, "skipped": 0, "failed": 0}
    
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futures = {pool.submit(process_png, p, mc, sc): p.name for p, mc, sc in files_to_process}
        for fut in as_completed(futures):
            png_name = futures[fut]
            try:
                res = fut.result()
                stats[res] += 1
                log.info("Status für %s: %s", png_name, res.upper())
            except Exception as e:
                stats["failed"] += 1
                log.error("Unerwarteter Fehler für %s: %s", png_name, e)

    log.info("VERARBEITUNG ABGESCHLOSSEN – Statistik: %s", stats)

# Hilfsfunktionen bleiben gleich (vereinfacht für Beispiel)
def trace_png_to_svg(png_path: Path, svg_out: Path):
    """Vereinfachte Funktion - Implementation aus Original verwenden"""
    log.info("SVG-Erstellung für %s...", png_path.name)
    # Hier würde die Original-Implementation stehen

    log.info("Vektorisierung von %s mit potrace...", png_path.name)
    with tempfile.TemporaryDirectory() as tdir:
        prep = Path(tdir) / "pre.png"
        preprocess_png(png_path, prep)
        pgm = Path(tdir) / "pre.pgm"
        Image.open(prep).convert("L").save(pgm)
        cmd = [
            POTRACE_PATH,
            str(pgm),
            "-s",
            "-o",
            str(svg_out),
            "-k",
            str(TRACE_THRESHOLD),
        ]
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if not svg_out.exists() or svg_out.stat().st_size == 0:
                log.error("potrace hat keine SVG-Datei erstellt oder sie ist leer: %s. stdout: %s, stderr: %s",
                          svg_out, result.stdout, result.stderr)
                raise RuntimeError(f"potrace hat keine SVG-Datei erstellt oder sie ist leer: {svg_out}")
        except subprocess.CalledProcessError as e:
            log.error("potrace Vektorisierung fehlgeschlagen für %s: %s (stdout: %s, stderr: %s)",
                      png_path.name, e, e.stdout, e.stderr)
            raise
    log.info("Vektorisierung erfolgreich: %s", svg_out.name)

def create_a4_canvas(svg_in: Path, svg_a4_out: Path):
    """Vereinfachte Funktion - Implementation aus Original verwenden"""
    log.info("A4-Canvas für %s...", svg_in.name)
    # Hier würde die Original-Implementation stehen

    log.info("Erstelle exakte A4-Version von %s …", svg_in.name)

    dpi = DEFAULT_DPI
    a4_w_px = int(A4_WIDTH_MM * dpi / 25.4)
    a4_h_px = int(A4_HEIGHT_MM * dpi / 25.4)

    vb_x, vb_y, vb_w, vb_h = _get_svg_bounds(svg_in)

    max_w = 0.9 * a4_w_px
    max_h = 0.9 * a4_h_px
    scale = min(max_w / vb_w, max_h / vb_h)

    tx = (a4_w_px - vb_w * scale) / 2 - vb_x * scale
    ty = (a4_h_px - vb_h * scale) / 2 - vb_y * scale

    style_block = (
        "<style>path,rect,circle,ellipse,polygon,polyline,line"
        "{fill:#000000;stroke:none}</style>"
    )

    svg_text = svg_in.read_text(encoding="utf-8")
    match = re.search(r"<svg[^>]*?>(.*?)</svg>", svg_text, re.S)
    inner_svg = match.group(1).strip() if match else svg_text
    inner_svg = _ensure_black_fill_and_stroke(inner_svg)

    result = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{a4_w_px}px" height="{a4_h_px}px"
     viewBox="0 0 {a4_w_px} {a4_h_px}"
     xmlns="http://www.w3.org/2000/svg"
     preserveAspectRatio="xMidYMid meet">
  {style_block}
  <g transform="translate({tx:.3f},{ty:.3f}) scale({scale:.6f})">
    {inner_svg}
  </g>
</svg>"""

    svg_a4_out.write_text(result, encoding="utf-8")
    log.info("A4-SVG geschrieben: %s", svg_a4_out.name)

def create_thumbnail(svg_path: Path, thumb_out: Path):
    """Vereinfachte Funktion - Implementation aus Original verwenden"""
    log.info("Thumbnail für %s...", svg_path.name)
    # Hier würde die Original-Implementation stehen
    log.info("Thumbnail für %s erstellen...", svg_path.name)
    cmd = [INKSCAPE_PATH, str(svg_path),
           "--export-type=png",
           f"--export-width={TARGET_THUMB_WIDTH_PX}",
           "--export-area-page",
           "--export-background=white",
           "--export-filename", str(thumb_out)]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if not thumb_out.exists() or thumb_out.stat().st_size == 0:
            log.error("Inkscape hat keine Thumbnail-Datei erstellt oder sie ist leer: %s. stdout: %s, stderr: %s",
                      thumb_out, result.stdout, result.stderr)
            raise RuntimeError(f"Inkscape hat keine Thumbnail-Datei erstellt oder sie ist leer: {thumb_out}")
        img = Image.open(thumb_out)
        img = ImageOps.autocontrast(img.convert("L")).convert("RGB")
        img.save(thumb_out, optimize=True, compress_level=9)
    except subprocess.CalledProcessError as e:
        log.error("Inkscape Thumbnail-Erstellung fehlgeschlagen für %s: %s (stdout: %s, stderr: %s)",
                  svg_path.name, e, e.stdout, e.stderr)
        raise
    log.info("Thumbnail erfolgreich: %s", thumb_out.name)

if __name__ == "__main__":
    main()