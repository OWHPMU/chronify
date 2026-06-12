import os
import csv
from pathlib import Path
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime

# ==========================================
# KONFIGURATION
# ==========================================

ROOT_DIR = r"./01_EML"
OUTPUT_CSV = r"./00_Chronologie/Kommunikationschronologie.csv"

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

# ==========================================
# EML EINLESEN
# ==========================================

rows = []

for eml_file in Path(ROOT_DIR).rglob("*.eml"):

    try:
        with open(eml_file, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)

        dt = parse_date(msg)

        rows.append({
            "Datum": dt.strftime("%Y-%m-%d") if dt else "",
            "Zeit": dt.strftime("%H:%M:%S") if dt else "",
            "Absender": safe_header(msg, "From"),
            "Empfaenger": safe_header(msg, "To"),
            "Betreff": safe_header(msg, "Subject"),
            "Dateiname": eml_file.name,
            "Pfad": str(eml_file),
            "Message_ID": safe_header(msg, "Message-ID"),
            "In_Reply_To": safe_header(msg, "In-Reply-To")
        })

    except Exception as ex:
        print(f"FEHLER: {eml_file}")
        print(ex)

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

os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

with open(
    OUTPUT_CSV,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "Datum",
            "Zeit",
            "Absender",
            "Empfaenger",
            "Betreff",
            "Dateiname",
            "Pfad",
            "Message_ID",
            "In_Reply_To"
        ]
    )

    writer.writeheader()
    writer.writerows(rows)

print()
print("=" * 60)
print(f"EMLs gefunden: {len(rows)}")
print(f"CSV erstellt: {OUTPUT_CSV}")
print("=" * 60)
