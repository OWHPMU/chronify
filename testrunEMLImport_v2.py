import os
import csv
from pathlib import Path
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime, parseaddr

# ==========================================
# KONFIGURATION
# ==========================================

SCRIPT_VERSION = "v2"

ROOT_DIR = "./01_EML"

OUTPUT_CSV = (
    f"./00_Chronologie/"
    f"Kommunikationschronologie_{SCRIPT_VERSION}.csv"
)

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
# EML EINLESEN
# ==========================================

rows = []

for eml_file in Path(ROOT_DIR).rglob("*.eml"):

    try:
        with open(eml_file, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)

        dt = parse_date(msg)

        absender = get_email_address(msg.get("From", ""))
        empfaenger = get_email_address(msg.get("To", ""))

        rows.append({
            "Datum": dt.strftime("%Y-%m-%d") if dt else "",
            "Zeit": dt.strftime("%H:%M:%S") if dt else "",
            "Richtung": get_direction(str(eml_file.parent)),
            "Themen": "",
            "Betreff": safe_header(msg, "Subject"),
            "Pfad": str(eml_file.parent),
            "Absender": absender,
            "Empfaenger": empfaenger,
            "Message_ID": safe_header(msg, "Message-ID"),
            "In_Reply_To": safe_header(msg, "In-Reply-To"),
            "Dateiname": eml_file.name
        })

    except Exception as ex:
        print()
        print("=" * 80)
        print(f"FEHLER BEIM EINLESEN:")
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
# TESTAUSGABE
# ==========================================

print()
print("=" * 80)
print(f"Kommunikationschronologie {SCRIPT_VERSION}")
print(f"EMLs gefunden: {len(rows)}")
print("=" * 80)

print()
print("Erste 5 Datensätze:")
print()

for row in rows[:5]:
    print(
        f'{row["Datum"]} '
        f'{row["Zeit"]} | '
        f'{row["Richtung"]} | '
        f'{row["Betreff"]}'
    )

# ==========================================
# CSV SCHREIBEN
# ==========================================

os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

fieldnames = [
    "Datum",
    "Zeit",
    "Richtung",
    "Themen",
    "Betreff",
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
# ABSCHLUSS
# ==========================================

print()
print("=" * 80)
print(f"CSV erstellt:")
print(OUTPUT_CSV)
print("=" * 80)
print()
