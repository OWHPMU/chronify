import os
import csv
import json
import re

from pathlib import Path
from collections import Counter

from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime, parseaddr

#from pypdf import PdfReader

# =========================================================================================
# Chronify - Turn emails, documents and attachments into a structured, searchable timeline.
# =========================================================================================


# ==========================================
# KONFIGURATION
# ==========================================

SCRIPT_VERSION = "v6.1"

ROOT_DIR = "./01_E-Mails_EML"
PDF_ROOT_DIR = "./02_Anhaenge_PDF"

OUTPUT_CSV = (
    f"./00_Timeline/"
    f"chronify_{SCRIPT_VERSION}.csv"
)

PDF_OUTPUT_CSV = (
    "./00_Timeline/chronify_pdf_attachments.csv"
)

TOPIC_CANDIDATES_FILE = (
    "./00_Timeline/topic_candidates.json"
)

TOPICS_FILE = (
    "./00_Timeline/topics.json"
)

TEXT_PREVIEW_LENGTH = 250
MIN_WORD_LENGTH = 5


# ==========================================
# BLACKLIST - exclude from topic detection
# ==========================================

BLACKLIST_FILE = "blacklist.txt"


# Loads blacklist from file
def load_blacklist(filepath):
    if not os.path.exists(filepath):
        return set() # Create empty blacklist; TODO Create default blacklist if the file is missing

    with open(filepath, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()} # Remove whitespace (\n) and ignore empty lines


# Load the blacklist from the file when the app starts
BLACKLIST = load_blacklist(BLACKLIST_FILE)

# # Convert a wildcard pattern into a regular expression
def wildcard_to_regex(pattern):
    escaped = re.escape(pattern)
    escaped = escaped.replace(r"\*", ".*")
    return f"^{escaped}$"


# Create a regex compatible with the imported set
BLACKLIST_REGEX = [
    re.compile(wildcard_to_regex(pattern), re.IGNORECASE) for pattern in BLACKLIST
]

# Return whether a word is blacklisted
def is_blacklisted(word):
    for regex in BLACKLIST_REGEX:
        if regex.match(word):
            return True
    return False


# ==========================================
# HELPER FUNCTIONS
# ==========================================

# Return a sanitized email header value; question: what exact kind of message is msg? The eml-message? The eml name?
def safe_header(msg, name):
    value = msg.get(name, "")
    return str(value).replace("\n", " ").replace("\r", " ").strip()


# Parse the email date into a local datetime object; question: what kind og message is msg?
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


# Extract the email address from a mail header
def get_email_address(header_value):
    return parseaddr(header_value)[1]


# Returns whether the message was send or received
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

# Extract the plain text body from an email message
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


# Remove signatures, reply threads and boilerplate from the email text; FIXME at least 2 messages contain text after the signature :(
def clean_mail_text(text):
    if not text:
        return ""

    # ----------------------------------
    # Remove URLs
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
    # Trim reply threads
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
    # Trim DATEV / SEPPmail
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
    # Trim the signatures
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


# Create a preview of the EML email text
def create_preview(text):
    text = " ".join(text.split())

    if len(text) <= TEXT_PREVIEW_LENGTH:
        return text

    return text[:TEXT_PREVIEW_LENGTH] + "..."


# ==========================================
# TOPIC CANDIDATES
# ==========================================

# Extract potential topic candidates from the email text
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

# Reads current the topics, removes all newly blacklisted ones and returns cleaned topics
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


# Detect configured topics in the email text
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

topics_dict = {}

eml_rows = []
pdf_rows = []

candidate_word_counts = Counter()

for eml_file in Path(ROOT_DIR).rglob("*.eml"):
    try:
        with open(eml_file, "rb") as f:
            msg = BytesParser(
                policy=policy.default
            ).parse(f)

        dt = parse_date(msg)

        mail_subject = safe_header(
            msg,
            "Subject"
        )

        mailtext_raw = extract_text(msg)
        mailtext = clean_mail_text(
            mailtext_raw
        )

        # Collect Words
        candidate_word_counts.update(
            extract_candidate_words(mailtext)
        )

        # Collect pdf attachments
        pdf_attachments = []

        for part in msg.walk():
            filename = part.get_filename()

            if not filename:
                continue

            if filename.lower().endswith(".pdf"):
                pdf_attachments.append(filename)

                pdf_rows.append({
                    "_sort_dt": dt,

                    "Anhang_vom":
                        dt.strftime("%d.%m.%Y"),

                    "Uhrzeit":
                        dt.strftime("%H:%M"),

                    "Richtung":
                        get_direction(
                            str(eml_file.parent)
                        ),

                    "Dateiname":
                        filename,

                    "EML_Dateiname":
                        eml_file.name
                })

        eml_rows.append({
            "_sort_dt": dt,
            "_mailtext": mailtext,

            "E_Mail_vom":
                dt.strftime("%d.%m.%Y")
                if dt else "",

            "Uhrzeit":
                dt.strftime("%H:%M")
                if dt else "",

            "Richtung":
                get_direction(
                    str(eml_file.parent)
                ),

            "Topics": "",

            "Betreff":
                mail_subject,

            "Text_Auszug":
                create_preview(mailtext),

            "PDF_Anhaenge":
                "; ".join(pdf_attachments),

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
                eml_file.name,
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
# SORT EML-CSV
# ==========================================

eml_rows.sort(
    key=lambda r: r["_sort_dt"],
    reverse=True
)


pdf_rows.sort(
    key=lambda r: r["_sort_dt"],
    reverse=True
)


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

for word, count in candidate_word_counts.most_common():
    topic_candidates[word] = count


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
    sorted_candidates = dict(sorted(merged_candidates.items())) # Sort topic candidated alphabetically right before saving

    json.dump(sorted_candidates, f, indent=4, ensure_ascii=False)

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

with open(TOPICS_FILE, "w", encoding="utf-8") as f:
    sorted_topics = dict(sorted(topics.items())) # Sort topics alphabetically right before saving
    json.dump(sorted_topics, f, indent=4, ensure_ascii=False )

topics_dict = load_topics()

for row in eml_rows:
    row["Topics"] = detect_topics(
        row["_mailtext"],
        topics_dict
    )

# ==========================================
# WRITE EML-CSV UND PDF-ATTACHMENTS-CSV
# ==========================================

os.makedirs(
    os.path.dirname(OUTPUT_CSV),
    exist_ok=True
)

# Write EML to CSV
fieldnames = [
    "E_Mail_vom",
    "Uhrzeit",
    "Richtung",
    "Topics",
    "Betreff",
    "Text_Auszug",
    "PDF_Anhaenge",
    "Absender",
    "Empfaenger",
    "Message_ID",
    "In_Reply_To",
    "Dateiname"
]

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
        extrasaction="ignore"
    )

    writer.writeheader()
    writer.writerows(eml_rows)

    # Write PDF attachmenets list to PDF-attachments-CSV
    pdf_fieldnames = [
        "Anhang_vom",
        "Uhrzeit",
        "Richtung",
        "Dateiname",
        "EML_Dateiname"
    ]

    with open("./00_Timeline/chronify_pdf_attachments.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=pdf_fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()
        writer.writerows(pdf_rows)


# ==========================================
# AUSGABE
# ==========================================

print()
print("=" * 80)
print(f"Chronify {SCRIPT_VERSION}")
print("Verwandelt E-Mails, Dokumente und Anhänge in eine strukturierte, durchsuchbare Timeline.")
print("=" * 80)

print()
print(f"EMLs gefunden: {len(eml_rows)}")
print(f"PDFs gefunden: {len(pdf_rows)}")

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
print("PDF CSV erzeugt:")
print(PDF_OUTPUT_CSV)

print()
print("=" * 80)
print()
