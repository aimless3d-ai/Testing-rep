# Vinted Auto Listing Tool V2

Windows-Desktop-App, die aus Produktfotos in wenigen Sekunden eine fertige
Vinted-Anzeige vorbereitet: Bilder importieren → KI-Analyse → Titel,
Beschreibung, Kategorie, Größe, Farbe, Zustand und Preisvorschlag prüfen →
Anzeige exportieren und im Browser veröffentlichen.

> **Grundregel der App:** Es wird nichts erfunden. Jede Angabe stammt aus einem
> Bild, aus deiner Eingabe oder aus einer nachvollziehbaren Berechnung. Was die
> KI nicht sicher erkennt, bleibt leer und wird als
> „Nicht sicher erkannt – bitte auswählen.“ markiert.

---

## 0. Download

Die fertige Anwendung wird nicht im Repository abgelegt – kompilierte Dateien
gehören nicht in die Versionsverwaltung. Es gibt zwei Bezugswege:

**Releases (empfohlen, dauerhafter Link):**
[github.com/aimless3d-ai/Testing-rep/releases/latest](https://github.com/aimless3d-ai/Testing-rep/releases/latest)

| Datei | Beschreibung |
| --- | --- |
| `VintedAutoListingTool-Setup.exe` | Installer mit Startmenü-Eintrag |
| `VintedAutoListingTool-portable.zip` | Entpacken und direkt starten |

Ein Release entsteht durch einen Tag `v*` oder über *Actions → Release → Run
workflow*.

**Actions-Artefakte (bei jedem Push, 90 Tage haltbar):**
[Actions → Tests und Windows-Build](https://github.com/aimless3d-ai/Testing-rep/actions/workflows/build.yml)
→ obersten Lauf öffnen → ganz unten unter *Artifacts*
`VintedAutoListingTool-Setup` herunterladen. Dafür muss man bei GitHub
angemeldet sein.

Beim ersten Start warnt Windows SmartScreen, weil die Datei nicht signiert
ist: *Weitere Informationen* → *Trotzdem ausführen*.

---

## 1. Schnellstart

### Fertige Anwendung (empfohlen)

1. `VintedAutoListingTool-Setup.exe` ausführen und dem Assistenten folgen.
2. App über das Startmenü oder das Desktop-Symbol starten.
3. Beim ersten Start unter **Einstellungen** einen KI-Anbieter samt API-Key
   eintragen und auf **API-Verbindung testen** klicken. *(Optional – ohne Key
   arbeitet die App im Offline-Modus, siehe Abschnitt 5.)*

Python muss dafür **nicht** installiert sein – die EXE bringt alles mit.

### Aus dem Quellcode starten (Entwicklung)

```powershell
git clone <repo-url>
cd Testing-rep
scripts\run_dev.bat          # Windows
```

```bash
./scripts/run_dev.sh         # Linux/macOS
```

Manuell:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip
PYTHONPATH=src .venv/bin/python -m vinted_tool
```

---

## 2. Die EXE selbst bauen

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Das Skript legt die virtuelle Umgebung an, installiert die Abhängigkeiten,
führt die Tests aus und baut anschließend:

| Ergebnis | Pfad |
| --- | --- |
| Anwendung | `packaging\dist\VintedAutoListingTool\VintedAutoListingTool.exe` |
| Installer | `installer_output\VintedAutoListingTool-Setup.exe` |

Für den Installer wird [Inno Setup 6](https://jrsoftware.org/isdl.php)
benötigt. Fehlt es, entsteht trotzdem die lauffähige EXE (mit Hinweis).

**Ohne Windows-Rechner:** Der GitHub-Actions-Workflow
`.github/workflows/build.yml` baut EXE und Installer bei jedem Push und legt
beide als Artefakte ab (`VintedAutoListingTool-exe`,
`VintedAutoListingTool-Setup`). Eine Windows-EXE lässt sich technisch nicht
unter Linux erzeugen – deshalb dieser Weg.

---

## 3. Funktionsumfang

### Bilder
* Drag & Drop einzelner Dateien, mehrerer Dateien oder ganzer Ordner
* Vorschau, Sortieren, Löschen, Hauptbild festlegen
* EXIF-Orientierung wird ausgewertet, das Bild automatisch gedreht
* Automatische Optimierung (Größe begrenzen, JPEG-Konvertierung, Thumbnails)
* Sprechende Dateinamen aus dem Anzeigentitel (`nike-hoodie-schwarz-01.jpg`)

### KI-Analyse
Aus allen Bildern gemeinsam werden erkannt: Produktart, Marke, Modell, Farbe
(inkl. Nebenfarben), Muster, Material, Größe, Zustand, sichtbare
Beschädigungen, besondere Merkmale und Suchbegriffe. Jedes Kernfeld bekommt
eine Confidence; alles unter 0,55 wird verworfen statt geraten.

### Anzeigenerstellung
* Titel nach Vinted-Muster (Marke → Produkt → Modell → Farbe → Größe, max. 100 Zeichen)
* Beschreibung aus einer Vorlage mit `{{variablen}}`
* Kategorie-Vorschlag samt Alternativen aus einem gepflegten Katalog (65 Kategorien)
* Drei Preise: **Schnellverkauf**, **Empfohlen**, **Höherer Startpreis** –
  jeweils mit einer nachvollziehbaren Begründung
* Passende Größenliste je Kategorie (Kleidung, Schuhe, Kindergrößen)

### Arbeiten mit vielen Artikeln
* **Batch-Modus:** Ordner mit 20 Fotos importieren, drei Gruppierungsarten
  (ein Bild = ein Produkt, nach Dateiname, nach Bildähnlichkeit), Fortschritt
  und Abbruch, ein Entwurf pro Produkt
* **Entwürfe** bleiben dauerhaft erhalten
* **Verlauf** mit Suche, Statusfilter, Sammelexport und Löschen
* **Duplikaterkennung** über SHA-256 (identische Datei) und Difference-Hash
  (ähnliches Foto) – warnt beim Import und im Batch

### Qualitätsprüfung
Vor dem Erstellen läuft ein Validator (Titel, Beschreibung, Bild, Kategorie,
Preis, Zustand, Größe bei Kleidung, Widersprüche wie „neu“ + Mängel):

* 🟢 **Bereit** – alles vorhanden
* 🟡 **Überprüfung empfohlen** – nur Hinweise
* 🔴 **Informationen fehlen** – „Anzeige erstellen“ bleibt gesperrt

---

## 4. Vinted-Veröffentlichung

Vinted stellt **keine** öffentliche API zum Einstellen von Artikeln bereit.
Die App umgeht deshalb bewusst **nichts**: kein automatisierter Login, keine
Captcha-Behandlung, keine versteckten Requests. Stattdessen übernimmt sie
alles, was ohne Schutzmechanismen möglich ist:

1. **Export:** Ordner mit nummerierten Bildern in Upload-Reihenfolge plus
   `anzeige.txt`, `anzeige.json` und `anzeige.csv` (Semikolon, Excel-tauglich).
2. **Assistent:** öffnet die offizielle Seite „Artikel einstellen“ im eigenen
   Browser, öffnet den Bilderordner und legt jedes Feld auf Knopfdruck in die
   Zwischenablage – Schritt für Schritt, in der Reihenfolge des Formulars.
3. **Status:** Nach dem Hochladen lässt sich die Anzeige als „Veröffentlicht“
   markieren und liegt im Verlauf.

Zusätzlich öffnet **„Ähnliche Artikel auf Vinted ansehen“** eine normale
Vinted-Suche, damit du deinen Preis selbst gegen echte Angebote prüfen kannst.

---

## 5. KI-Anbieter und API-Keys

In den Einstellungen wählbar:

| Provider | Standardmodell | Key nötig |
| --- | --- | --- |
| OpenRouter | `google/gemini-2.5-flash` | ja (`OPENROUTER_API_KEY`) |
| OpenAI | `gpt-4.1-mini` | ja (`OPENAI_API_KEY`) |
| Anthropic | `claude-sonnet-4-5` | ja (`ANTHROPIC_API_KEY`) |
| Lokales Modell (OpenAI-kompatibel, z. B. Ollama) | `llava` | meist nein |
| **Offline-Analyse** | – | **nein** |

Der Key wird entweder in der App gespeichert (verschlüsselt, siehe Abschnitt 8)
oder als Umgebungsvariable gesetzt – Vorlage: `.env.example`. Ein Key in der
App hat Vorrang vor der Umgebungsvariable.

**Empfehlung:** OpenRouter mit einem günstigen Vision-Modell. Eine Analyse
kostet dort typischerweise deutlich unter einem Cent.

### Offline-Analyse
Ohne Key ist die App vollständig nutzbar. Die Offline-Analyse ermittelt, was
lokal wirklich messbar ist: die dominanten Farben aus den Bildpixeln sowie
Produktart- und Markenhinweise aus den Dateinamen. Alle übrigen Felder bleiben
leer und werden zur Auswahl angeboten – geraten wird nichts.

### Kosten niedrig halten
* Ergebnisse werden gecacht (Schlüssel = Bild-Hashes + Provider + Modell + Hinweis);
  dieselben Bilder kosten nie zweimal
* Standardmäßig gehen nur die ersten 3 Bilder an das Modell (einstellbar 1–8)
* Bilder werden vor dem Versand verkleinert (Standard 1600 px)
* Strikte JSON-Ausgabe, `max_tokens` begrenzt, `temperature` 0.1
* Automatische Wiederholung nur bei Timeout, 429 und 5xx – niemals bei 4xx

---

## 6. Vorlagen

Beschreibungsvorlagen unterstützen:

| Syntax | Bedeutung |
| --- | --- |
| `{{brand}}` | Wert einsetzen, sonst leer |
| `{{condition\|bitte erfragen}}` | Ersatztext, wenn der Wert fehlt |
| `{{#size}}Größe {{size}}{{/size}}` | Block nur ausgeben, wenn gefüllt |

Verfügbare Variablen: `brand`, `product`, `title`, `size`, `condition`,
`color`, `material`, `category`, `price`, `currency`, `keywords`, `features`,
`damages`, `shipping`. Drei Vorlagen sind vorinstalliert; die Vorlagenseite
zeigt eine Live-Vorschau mit Beispieldaten und warnt vor Tippfehlern in
Variablennamen.

---

## 7. Tech-Stack – und warum

**Python 3.10+ mit PySide6 (Qt 6).**

* **Windows-Kompatibilität:** Qt ist auf Windows nativ und wird von
  PyInstaller sauber gebündelt – eine EXE ohne Python-Installation.
* **Wenige Abhängigkeiten:** fünf Laufzeitpakete (PySide6, Pillow, httpx,
  cryptography, platformdirs). Ein Electron-Stack hätte Node, Chromium und
  einen zweiten Sprach-Stack für die Bildverarbeitung bedeutet – bei ~100 MB
  mehr Installationsgröße.
* **Bildverarbeitung:** EXIF, Rotation, Thumbnails und perzeptuelle Hashes
  liegen mit Pillow direkt neben der Anwendungslogik.
* **Stabilität:** Qt-Threads halten KI- und Batch-Läufe aus dem UI-Thread;
  die GUI friert nie ein.
* **Tests:** Kern-Logik ist Qt-frei und damit schnell testbar; die UI wird
  headless über Qts `offscreen`-Plugin geprüft.

Gegen Tauri sprach die zusätzliche Rust-Toolchain, gegen Electron die Größe
und der doppelte Sprach-Stack.

---

## 8. Daten und Sicherheit

Alles liegt lokal unter `%APPDATA%\VintedAutoListingTool`
(überschreibbar mit `VINTED_TOOL_DATA_DIR`):

```
vinted_tool.sqlite3   Anzeigen, Entwürfe, Vorlagen, Einstellungen, Analyse-Cache
images/               importierte, optimierte Produktbilder
thumbnails/           Vorschaubilder
exports/              vorbereitete Anzeigen-Ordner
logs/app.log          rotierendes Log (max. 3 × 2 MB)
secret.key            lokaler Schlüssel für die API-Key-Verschlüsselung
```

* API-Keys werden mit Fernet (AES) verschlüsselt gespeichert; der Schlüssel
  liegt in `secret.key` mit Benutzerrechten (0600). Das schützt vor
  beiläufigem Mitlesen der Datenbank – es ersetzt keinen Passwortmanager und
  keine Festplattenverschlüsselung.
* Das Logging filtert Keys grundsätzlich heraus (Muster für `sk-…`,
  `Bearer …`, `api_key: …` plus alle im Lauf bekannten Keys) – Tests sichern
  das ab.
* An die KI gehen ausschließlich die ausgewählten Produktfotos und dein
  optionaler Hinweistext. Keine Zugangsdaten, keine Vinted-Session, keine
  Telemetrie.
* `.env`, `*.key` und alle lokalen Daten stehen in `.gitignore`.

---

## 9. Projektstruktur

```
src/vinted_tool/
├── app/           Einstiegspunkt, Kontext, Pfade, Logging
├── ai/            Provider-Abstraktion, JSON-Schema, Prompts, Cache
│   └── providers/ openai_compatible (OpenAI/OpenRouter/lokal), anthropic, offline
├── automation/    Vinted-Export und Veröffentlichungs-Assistent
├── core/          Kategorien, Preise, Vorlagen, Duplikate, Validierung, Secrets
├── database/      SQLite-Schema, Verbindung, Repositories
├── models/        Listing, Bilder, Analyse, Vorlagen, Enums
├── services/      Bild-, Analyse-, Listing-, Batch-, Settings-Service
├── ui/            Theme, Hauptfenster, Seiten, Widgets, Worker-Threads
└── utils/         Hashes, Dateien, Text
tests/             118 Tests
packaging/         PyInstaller-Spec, Inno-Setup-Skript
scripts/           Build- und Startskripte
```

---

## 10. Tests

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src .venv/bin/python -m pytest
```

Abgedeckt: Bildimport (inkl. EXIF-Rotation und defekter Dateien), Datenbank,
KI-Parsing (Code-Fences, Prosa, kaputtes JSON, niedrige Confidence),
Provider-Fehlerfälle (401/429/5xx/Timeout) mit gestubbtem HTTP, Preislogik,
Kategoriezuordnung, Vorlagen, Duplikate, Validierung, Batch-Läufe, Export,
Verschlüsselung, Log-Redaktion und ein headless UI-Durchlauf.

---

## 11. Tastenkürzel

`Strg+N` neue Anzeige · `Strg+1` Dashboard · `Strg+B` Batch ·
`Strg+D` Entwürfe · `Strg+H` Verlauf · `Strg+,` Einstellungen

---

## 12. Fehlerbehandlung

Jeder Fehler wird abgefangen, protokolliert und auf Deutsch erklärt. Schlägt
eine KI-Analyse fehl, bietet der Dialog **Erneut versuchen**, **Ohne KI
ausfüllen** und **Manuell ausfüllen** an. Ein defektes Bild bricht weder den
Import noch einen Batch-Lauf ab; Timeouts und Serverfehler werden mit
exponentiellem Backoff wiederholt, Authentifizierungsfehler dagegen sofort
gemeldet.

## 13. Lizenz

MIT
