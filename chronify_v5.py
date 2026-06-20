import os
import csv
import json
import re

from pathlib import Path
from collections import Counter

from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime, parseaddr


# =========================================================================================
# Chronify - Turn emails, documents and attachments into a structured, searchable timeline.
# =========================================================================================


# ==========================================
# KONFIGURATION
# ==========================================

SCRIPT_VERSION = "v5"

ROOT_DIR = "./01_E-Mails_EML"

OUTPUT_CSV = (
    f"./00_Timeline/"
    f"chronify_{SCRIPT_VERSION}.csv"
)

TOPIC_CANDIDATES_FILE = (
    "./00_Timeline/topic_candidates.json"
)

TOPICS_FILE = (
    "./00_Timeline/topics.json"
)

TEXT_PREVIEW_LENGTH = 250

MIN_WORD_LENGTH = 5
MIN_OCCURRENCES = 2
MAX_CANDIDATES = 100


# ==========================================
# BLACKLIST - exclude from topic detection
# ==========================================

BLACKLIST_FILE = "blacklist.txt"


def load_blacklist(filepath):
    # Lädt die Blacklist aus einer Textdatei und entfernt leere Zeilen.
    if not os.path.exists(filepath):
        # Falls die Datei fehlt, wird eine leere Blacklist genutzt; todo: fallback to default blacklist?
        return set()

    with open(filepath, "r", encoding="utf-8") as f:
        # Liest Zeilen, entfernt Whitespace (\n) und ignoriert leere Zeilen
        return {line.strip() for line in f if line.strip()}


# Blacklist beim App-Start aus der Datei einlesen
BLACKLIST = load_blacklist(BLACKLIST_FILE)


def wildcard_to_regex(pattern):
    escaped = re.escape(pattern)
    escaped = escaped.replace(r"\*", ".*")
    return f"^{escaped}$"


# Regex-Kompatibilität direkt aus der eingelesenen Menge erstellen
BLACKLIST_REGEX = [
    re.compile(wildcard_to_regex(pattern), re.IGNORECASE) for pattern in BLACKLIST
]


def is_blacklisted(word):
    for regex in BLACKLIST_REGEX:
        if regex.match(word):
            return True
    return False


# ==========================================
# HILFSFUNKTIONEN
# ==========================================

def safe_header(msg, name):
    value = msg.get(name, "")
    return str(value).replace("\n", " ").replace("\r", " ").strip()


def parse_date(msg):
    try:
        date_str = msg.get("Date")

        if not date_str:
            return None

        dt = parsedate_to_datetime(date_str)

        if dt.tzinfo:
            dt = dt.astimezone()

        return dt

    except Exception:
        return None


def get_email_address(header_value):
    return parseaddr(header_value)[1]


def get_direction(path_str):
    path_lower = path_str.lower()

    if "gesendet" in path_lower:
        return "gesendet"

    if "empfangen" in path_lower:
        return "empfangen"

    return "Unbekannt"


# ==========================================
# MAILTEXT
# ==========================================

def extract_text(msg):
    try:
        if msg.is_multipart():

            parts = []

            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        text = part.get_content()

                        if text:
                            parts.append(str(text))

                    except Exception:
                        pass

            return "\n".join(parts).strip()

        else:
            try:
                return str(msg.get_content()).strip()
            except Exception:
                return ""

    except Exception:
        return ""


def clean_mail_text(text):
    if not text:
        return ""

    # ----------------------------------
    # URLs entfernen
    # ----------------------------------

    text = re.sub(
        r'https?://\S+',
        ' ',
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r'mailto:\S+',
        ' ',
        text,
        flags=re.IGNORECASE
    )

    # ----------------------------------
    # Antwortketten abschneiden
    # ----------------------------------

    reply_markers = [
        "-----Original-Nachricht-----",
        "Von:",
        "Gesendet:",
        "An:",
        "Betreff:"
    ]

    lines = text.splitlines()

    cleaned_lines = []

    for line in lines:
        if any(
            marker in line
            for marker in reply_markers
        ):
            break

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    # ----------------------------------
    # DATEV / SEPPmail abschneiden
    # ----------------------------------

    disclaimer_markers = [
        "SEPPmail",
        "Viewer",
        "Vertraulichkeit",
        "Verschlüsselung",
        "Diese Nachricht ist vertraulich"
    ]

    for marker in disclaimer_markers:
        pos = text.lower().find(
            marker.lower()
        )

        if pos >= 0:
            text = text[:pos]

    # ----------------------------------
    # Signaturen abschneiden
    # ----------------------------------

    signature_markers = [
        "Mit freundlichen Grüßen",
        "Mit freundlichem Gruß",
        "Freundliche Grüße",
        "Viele Grüße"
    ]

    for marker in signature_markers:
        pos = text.lower().find(
            marker.lower()
        )

        if pos >= 0:
            text = text[:pos]

    return text.strip()


def create_preview(text):
    text = " ".join(text.split())

    if len(text) <= TEXT_PREVIEW_LENGTH:
        return text

    return text[:TEXT_PREVIEW_LENGTH] + "..."


# ==========================================
# TOPIC-KANDIDATEN
# ==========================================

def extract_candidate_words(text):
    words = re.findall(
        r"[A-Za-zÄÖÜäöüß]{5,}",
        text
    )

    result = []

    for word in words:
        if len(word) < MIN_WORD_LENGTH:
            continue

        if not word[0].isupper():
            continue

        if is_blacklisted(word):
            continue

        result.append(word)

    return result


# ==========================================
# TOPIC MATCHING
# ==========================================

def load_topics():
    if not os.path.exists(TOPICS_FILE):
        return {}

    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Filter the loaded topics directly using the blacklist
    cleaned_topics = {
        word: count for word, count in data.items() if not is_blacklisted(word)
    }

    # If any words have been deleted, save the cleaned-up version right away
    if len(cleaned_topics) != len(data):
        with open(TOPICS_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned_topics, f, ensure_ascii=False, indent=4)

    return cleaned_topics


def detect_topics(text, topics_dict):
    found = []

    text_lower = text.lower()

    for topic, keywords in topics_dict.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                found.append(topic)
                break

    return "; ".join(sorted(found))


# ==========================================
# EML EINLESEN
# ==========================================

topics_dict = load_topics()

rows = []

all_words = Counter()

for eml_file in Path(ROOT_DIR).rglob("*.eml"):
    try:
        with open(eml_file, "rb") as f:
            msg = BytesParser(
                policy=policy.default
            ).parse(f)

        dt = parse_date(msg)

        betreff = safe_header(
            msg,
            "Subject"
        )

        mailtext_raw = extract_text(msg)
        mailtext = clean_mail_text(
            mailtext_raw
        )

        # Wörter sammeln
        all_words.update(
            extract_candidate_words(mailtext)
        )

        rows.append({
            "Datum":
                dt.strftime("%Y-%m-%d")
                if dt else "",

            "Zeit":
                dt.strftime("%H:%M:%S")
                if dt else "",

            "Richtung":
                get_direction(
                    str(eml_file.parent)
                ),

            "Topics":
                detect_topics(
                    mailtext,
                    topics_dict
                ),

            "Betreff":
                betreff,

            "Text_Auszug":
                create_preview(mailtext),

            "Pfad":
                str(eml_file.parent),

            "Absender":
                get_email_address(
                    msg.get("From", "")
                ),

            "Empfaenger":
                get_email_address(
                    msg.get("To", "")
                ),

            "Message_ID":
                safe_header(
                    msg,
                    "Message-ID"
                ),

            "In_Reply_To":
                safe_header(
                    msg,
                    "In-Reply-To"
                ),

            "Dateiname":
                eml_file.name
        })

    except Exception as ex:
        print()
        print("=" * 80)
        print("FEHLER BEIM EINLESEN")
        print(eml_file)
        print(ex)
        print("=" * 80)
        print()

# ==========================================
# SORTIEREN
# ==========================================

rows.sort(
    key=lambda r: (
        r["Datum"],
        r["Zeit"]
    ),
    reverse=True
)

# ==========================================
# CSV SCHREIBEN
# ==========================================

os.makedirs(
    os.path.dirname(OUTPUT_CSV),
    exist_ok=True
)

fieldnames = [
    "Datum",
    "Zeit",
    "Richtung",
    "Topics",
    "Betreff",
    "Text_Auszug",
    "Pfad",
    "Absender",
    "Empfaenger",
    "Message_ID",
    "In_Reply_To",
    "Dateiname"
]

with open(
    OUTPUT_CSV,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(rows)

# ==========================================
# topic_candidates.json
# ==========================================

existing_candidates = {}


if os.path.exists(TOPIC_CANDIDATES_FILE):
    with open(
        TOPIC_CANDIDATES_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        existing_candidates = json.load(f)


topic_candidates = {}

for word, count in all_words.most_common():
    if count < MIN_OCCURRENCES:
        continue

    topic_candidates[word] = count

    if len(topic_candidates) >= MAX_CANDIDATES:
        break


merged_candidates = dict(existing_candidates)

merged_candidates.update(topic_candidates)


merged_candidates = {
    word: count

    for word, count in merged_candidates.items()

    if not is_blacklisted(word)
}

# Update topic_candidates.json
with open(
    TOPIC_CANDIDATES_FILE,
    "w",
    encoding="utf-8"
) as f:
    # Sort topic candidated alphabetically right before saving
    sorted_candidates = dict(sorted(merged_candidates.items()))

    json.dump(
        sorted_candidates,
        f,
        indent=4,
        ensure_ascii=False
    )

# ==========================================
# topics.json
# ==========================================

topics = {}

if os.path.exists(TOPICS_FILE):
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        topics = json.load(f)

for word in merged_candidates.keys():
    if word not in topics:
        topics[word] = [word]

with open(
    TOPICS_FILE,
    "w",
    encoding="utf-8"
) as f:
    # Sort topics alphabetically right before saving
    sorted_topics = dict(sorted(topics.items()))

    json.dump(
        sorted_topics, # topics
        f,
        indent=4,
        ensure_ascii=False
    )

# ==========================================
# AUSGABE
# ==========================================

print()
print("=" * 80)
print(f"Chronify {SCRIPT_VERSION}")
print("Verwandelt E-Mails, Dokumente und Anhänge in eine strukturierte, durchsuchbare Timeline.")
print("=" * 80)

print()
print(f"EMLs gefunden: {len(rows)}")

print()
print("Topic-Kandidaten:")
print(TOPIC_CANDIDATES_FILE)

if os.path.exists(TOPICS_FILE):
    print()
    print("Topics:")
    print(TOPICS_FILE)

print()
print("CSV erzeugt:")
print(OUTPUT_CSV)

print()
print("=" * 80)
print()
