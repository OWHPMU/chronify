import os
import csv
import json
import re

from pathlib import Path
from collections import Counter

from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime, parseaddr

# ==========================================
# KONFIGURATION
# ==========================================

SCRIPT_VERSION = "v4"

ROOT_DIR = "./01_EML"

OUTPUT_CSV = (
    f"./00_Chronologie/"
    f"Kommunikationschronologie_{SCRIPT_VERSION}.csv"
)

TOPIC_CANDIDATES_FILE = (
    "./00_Chronologie/topic_candidates.json"
)

TOPICS_FILE = (
    "./00_Chronologie/topics.json"
)

TEXT_PREVIEW_LENGTH = 250

MIN_WORD_LENGTH = 5
MIN_OCCURRENCES = 2
MAX_CANDIDATES = 100

# ==========================================
# STOPWÖRTER
# ==========================================

STOPWORDS = {

    # Allgemein
    "und", "oder", "aber", "dass", "nicht",
    "wurde", "werden", "bereits", "sowie",
    "vielen", "danke", "bitte", "heute",
    "morgen", "gestern",

    # Anrede
    "sehr", "geehrte", "geehrter",
    "frau", "herr",

    # Häufige Verwaltungsbegriffe
    "mitteilung",
    "informationen",
    "unterlagen",
    "nachweise",
    "rechnung",
    "rechnungen",
    "steuererklärung",
    "steuererklaerung",

    # Namen
    "forne",
    "forné",
    "betzler"
}

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

    if "betzler_an_forne" in path_lower:
        return "Betzler → Forne"

    if "forne_an_betzler" in path_lower:
        return "Forne → Betzler"

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


def create_preview(text):

    text = " ".join(text.split())

    if len(text) <= TEXT_PREVIEW_LENGTH:
        return text

    return text[:TEXT_PREVIEW_LENGTH] + "..."


# ==========================================
# TOPIC-KANDIDATEN
# ==========================================

def extract_candidate_words(text):

    text = text.lower()

    words = re.findall(
        r"[a-zA-ZäöüÄÖÜß]{5,}",
        text
    )

    result = []

    for word in words:

        if len(word) < MIN_WORD_LENGTH:
            continue

        if word in STOPWORDS:
            continue

        result.append(word)

    return result


# ==========================================
# EML EINLESEN
# ==========================================

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

        mailtext = extract_text(msg)

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
    )
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

topic_candidates = {}

for word, count in all_words.most_common():

    if count < MIN_OCCURRENCES:
        continue

    topic_candidates[word] = count

    if len(topic_candidates) >= MAX_CANDIDATES:
        break

with open(
    TOPIC_CANDIDATES_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        topic_candidates,
        f,
        indent=4,
        ensure_ascii=False
    )

# ==========================================
# topics.json
# ==========================================

if not os.path.exists(TOPICS_FILE):

    topics = {}

    for word in topic_candidates.keys():

        topics[word] = [word]

    with open(
        TOPICS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            topics,
            f,
            indent=4,
            ensure_ascii=False
        )

# ==========================================
# AUSGABE
# ==========================================

print()
print("=" * 80)
print(f"Kommunikationschronologie {SCRIPT_VERSION}")
print(f"EMLs gefunden: {len(rows)}")
print("=" * 80)

print()
print("CSV erstellt:")
print(OUTPUT_CSV)

print()
print("Topic-Kandidaten:")
print(TOPIC_CANDIDATES_FILE)

if os.path.exists(TOPICS_FILE):
    print("Topics:")
    print(TOPICS_FILE)

print()
print("=" * 80)
print()
