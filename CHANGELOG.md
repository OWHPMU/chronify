# Chronify

## v6.0 - 2026-06-21
New features
- Import PDF attachments
- Generate chronify_pdf_attachments.csv
- Build EML ↔ PDF attachment mapping
- Add PDF_Anhaenge column to timeline CSV
- Add EML_Dateiname column to PDF attachment CSV
Changes
- Read PDF attachment information directly from EML files
- Display date and time in German format (DD.MM.YYYY, HH:MM)
- Use the associated email date and time for PDF attachments

## v5 - 2026-06-20
- Split blacklist to separate file
- Update existing topic candidates if new topics with new EMLs have been added
- Merge updated topic candidates into topics.json
- Apply blacklist to topics
- Update and dump topic candidates and topics when blacklist changes
- Sort topic candidates and topics
- Revert sort order when writing csv 

## v4.2 - 2026-06-13
Refactoring
- Renamed project to Chronify
- Added output directory
- Introduced generic folder structure (gesendet / empfangen)
- Updated direction detection
- Updated README
- Updated CHANGELOG
- Added .gitignore

## v4.1 - 2026-06-12
- Preserved original word casing during topic extraction
- Added noun-oriented topic detection (capitalized words)
- Replaced stopword filtering with wildcard-enabled blacklist
- Added case-insensitive blacklist matching
- Added mail cleanup:
  - URL removal
  - reply-chain truncation
  - signature removal
  - DATEV / SEPPmail disclaimer removal
- Improved topic candidate quality

## v4 - 2026-06-12
- Added CSV export
- Added Message-ID extraction
- Added In-Reply-To extraction
- Added sender/recipient extraction
- Added path information
- Improved EML parsing
- Added chronology output

## v3 - 2026-06-11
- Extraktion des Mailtexts aus EML-Dateien
- Neue Spalte `Text_Auszug`
- Vorschau der ersten 250 Zeichen des Mailtexts
- Entfernung automatische Themenklassifikation aus dem Betreff
Begründung
Die Betreffzeilen erwiesen sich als ungeeignet für eine zuverlässige
Themenbestimmung, da viele Nachrichten innerhalb desselben Threads
unterschiedliche Sachverhalte behandelten.

## v2 - 2026-06-11
- Versionsnummer im Ausgabedateinamen
- Neue CSV-Datei `Kommunikationschronologie_v2.csv`
- Spaltenreihenfolge optimiert
- Änderung: Dateiname an das Ende der CSV verschoben

## v1 - 2026-06-11
Erstversion
- Einlesen von EML-Dateien
- Extraktion von Datum, Zeit, Betreff
- Ermittlung der Kommunikationsrichtung
- Ausgabe als CSV
