"""German user interface for Chapter Player.

The English source strings stay where they are in the code; the program logic
keeps comparing English values (menu options, phases, commands). Translation
happens only where text leaves the program:

- ``display()``  OLED text, called from ``appliance_io.oled_safe_text``
- ``spoken()``   spoken navigation, called from ``spoken_navigation``
- ``html_page()`` / ``json_value()``  setup web page, called from ``setup_server``

The language comes from the environment variable ``CHAPTER_LANGUAGE``
(``de`` or ``en``). Without it the player stays English, so the upstream tests
keep passing unchanged.
"""

from __future__ import annotations

import html
import os
import re
from typing import Callable, Union

Replacement = Union[str, Callable[[re.Match], str]]


def language() -> str:
    return os.environ.get("CHAPTER_LANGUAGE", "en").strip().lower()[:2] or "en"


def active() -> bool:
    return language() == "de"


# ---------------------------------------------------------------------------
# Display (OLED, 256 x 64): keep it short.
# ---------------------------------------------------------------------------

DISPLAY = {
    # Library and playback
    "Home": "Menü",
    "Prev": "Zurück",
    "Play": "Start",
    "Pause": "Pause",
    "Next": "Weiter",
    "Start": "Start",
    "Continue": "Weiterhören",
    "Start over": "Von vorn",
    "Loading": "Lädt",
    "Chapter": "Kapitel",
    "No books": "Keine Bücher",
    "Check connection": "Verbindung prüfen",
    "Check library": "Bibliothek prüfen",
    "Books unavailable": "Bücher nicht verfügbar",
    "Check setup": "Einrichtung prüfen",
    "Grabbing that book": "Ich hole das Buch",
    "from the shelf...": "aus dem Regal ...",
    "Playback stopped": "Wiedergabe gestoppt",
    "Check audio": "Ton prüfen",
    "Could not play": "Abspielen fehlgeschlagen",
    "Playback": "Wiedergabe",
    "Untitled": "Ohne Titel",
    "Latest episode": "Neueste Folge",
    # Volume, prompts
    "Volume": "Lautstärke",
    "Muted": "Stumm",
    "Yes": "Ja",
    "No": "Nein",
    "[Yes]": "[Ja]",
    "Are you sure you want to": "Möchtest du wirklich",
    "You were listening to": "Zuletzt gehört",
    "Screen saver": "Bildschirmschoner",
    # Setup and Wi-Fi
    "Setup address": "Setup-Adresse",
    "IP unavailable": "Keine IP-Adresse",
    "Wi-Fi connected": "WLAN verbunden",
    "Open setup page": "Setup-Seite öffnen",
    "Updating...": "Aktualisiere ...",
    "DO NOT POWER OFF": "NICHT AUSSCHALTEN",
    "OLED error": "Display-Fehler",
    "See log": "Siehe Log",
    # Bluetooth
    "Bluetooth": "Bluetooth",
    "Bluetooth On": "Bluetooth an",
    "Bluetooth Off": "Bluetooth aus",
    "Bluetooth Devices": "Bluetooth-Geräte",
    "Back": "Zurück",
    "Enable": "An",
    "Disable": "Aus",
    "Pair": "Koppeln",
    "Unpair": "Entkoppeln",
    "On": "An",
    "Off": "Aus",
    "Pair Bluetooth": "Bluetooth koppeln",
    "Put device in pair mode": "Gerät in Koppelmodus",
    "Put your device in pairing mode": "Gerät in den Koppelmodus",
    "Choose device": "Gerät wählen",
    "Choose a device": "Gerät wählen",
    "Scroll and click": "Drehen und drücken",
    "Searching": "Suche",
    "Pairing": "Koppeln ...",
    "Unpairing": "Entkoppeln ...",
    "Paired Successfully!": "Erfolgreich gekoppelt!",
    "Bluetooth unpaired": "Bluetooth entkoppelt",
    "Bluetooth device": "Bluetooth-Gerät",
    "Internal speaker": "Interner Lautsprecher",
    "Bluetooth failed": "Bluetooth-Fehler",
    "Bluetooth error": "Bluetooth-Fehler",
    "Pairing error": "Fehler beim Koppeln",
    "Unpairing error": "Fehler beim Entkoppeln",
    "Scan error": "Fehler bei der Suche",
    "No devices found": "Keine Geräte gefunden",
    "Could not connect": "Keine Verbindung",
    "Could not unpair": "Entkoppeln fehlgeschlagen",
    "Bluetooth unavailable": "Bluetooth nicht verfügbar",
    "Pairing failed": "Koppeln fehlgeschlagen",
    "Bluetooth enabled": "Bluetooth an",
    "Bluetooth disabled": "Bluetooth aus",
    "Bluetooth connected": "Bluetooth verbunden",
    "Connected": "Verbunden",
    "Not connected": "Nicht verbunden",
}

DIRECTION = {"previous": "vorherige", "next": "nächste"}

DISPLAY_PATTERNS: list[tuple[re.Pattern, Replacement]] = [
    (re.compile(r"^Are you sure you want to listen to the (previous|next) chapter\?$"),
     lambda m: f"Möchtest du wirklich das {DIRECTION[m.group(1)]} Kapitel hören?"),
    (re.compile(r"^listen to the (previous|next) chapter\?$"),
     lambda m: f"das {DIRECTION[m.group(1)]} Kapitel hören?"),
    (re.compile(r"^Are you still listening\? (\d+)$"), r"Hörst du noch zu? \1"),
    (re.compile(r"^You were listening to (.+)$"), r"Zuletzt gehört: \1"),
    (re.compile(r"^Connect to (.+)$"), r"Verbinde mit \1"),
    (re.compile(r"^Browse to (.+)$"), r"Öffne \1"),
    (re.compile(r"^By (.+)$"), r"von \1"),
    (re.compile(r"^Volume (\d+)%$"), r"Lautstärke \1 %"),
]


# ---------------------------------------------------------------------------
# Spoken navigation (espeak-ng, German voice)
# ---------------------------------------------------------------------------

SPOKEN = {
    "Home": "Menü",
    "Play": "Abspielen",
    "Pause": "Pause",
    "Previous chapter": "Vorheriges Kapitel",
    "Next chapter": "Nächstes Kapitel",
    "Muted": "Stumm",
}

SPOKEN_PATTERNS: list[tuple[re.Pattern, Replacement]] = [
    (re.compile(r"^Volume (\d+) percent$"), r"Lautstärke \1 Prozent"),
]

ESPEAK_VOICE_DE = "de"


# ---------------------------------------------------------------------------
# Setup web page
# ---------------------------------------------------------------------------

WEB = {
    # Navigation and headings
    "Overview": "Übersicht",
    "Settings": "Einstellungen",
    "Podcasts": "Podcasts",
    "Setup": "Einrichtung",
    "System": "System",
    "Status": "Status",
    "Currently Playing": "Läuft gerade",
    "Player administration": "Player-Verwaltung",
    "Player status": "Player-Status",
    "Wi-Fi": "WLAN",
    "Bluetooth": "Bluetooth",
    "Audiobookshelf": "Audiobookshelf",
    # Player
    "Playing": "Läuft",
    "Paused": "Pausiert",
    "Muted": "Stumm",
    "Play": "Abspielen",
    "Pause": "Pause",
    "Volume": "Lautstärke",
    "Nothing playing": "Gerade läuft nichts",
    "Unknown": "Unbekannt",
    "unknown user": "unbekannter Benutzer",
    "Not configured": "Nicht eingerichtet",
    "Not connected": "Nicht verbunden",
    "No Wi-Fi device was found.": "Kein WLAN-Gerät gefunden.",
    "Connected, SSID unavailable": "Verbunden, Netzname unbekannt",
    # Audiobookshelf login
    "The password is sent only to your Audiobookshelf server. This player stores the returned user token.":
        "Das Passwort geht nur an deinen Audiobookshelf-Server. Der Player speichert nur das zurückgegebene Benutzer-Token.",
    "Audiobookshelf server URL": "Adresse des Audiobookshelf-Servers",
    "Username": "Benutzername",
    "Password": "Passwort",
    "Log In Player": "Player anmelden",
    # Settings
    "Library order": "Sortierung",
    "Title": "Titel",
    "Author (last name)": "Autor",
    "Playback speed": "Tempo",
    "Screen saver": "Bildschirmschoner",
    "Screen saver style": "Art des Bildschirmschoners",
    "Screen saver dim level": "Helligkeit des Bildschirmschoners",
    "Style": "Art",
    "Dim level": "Helligkeit",
    "Chapter word": "Wort „Chapter“",
    "Book titles": "Buchtitel",
    "Digital clock": "Digitaluhr",
    "10% (darkest)": "10 % (am dunkelsten)",
    "50% (brightest)": "50 % (am hellsten)",
    "Sleep timer": "Einschlaf-Timer",
    "Sleep timer minutes": "Minuten bis zur Nachfrage",
    "Ask after": "Nachfragen nach",
    "minutes of listening": "Minuten Hören",
    "Control knob click sound": "Klickgeräusch der Drehknöpfe",
    "Spoken navigation": "Sprachnavigation",
    "Enable control knob click sound": "Klickgeräusch einschalten",
    "Disable control knob click sound": "Klickgeräusch ausschalten",
    "Enable spoken navigation": "Sprachnavigation einschalten",
    "Disable spoken navigation": "Sprachnavigation ausschalten",
    "Enable sleep timer": "Einschlaf-Timer einschalten",
    "Enable Bluetooth": "Bluetooth einschalten",
    "Disable Bluetooth": "Bluetooth ausschalten",
    "Off": "Aus",
    "Disable sleep timer": "Einschlaf-Timer ausschalten",
    "Save": "OK",
    "Cancel": "Abbrechen",
    # Podcasts
    "Podcast URL": "Podcast-Adresse",
    "Add row": "Zeile hinzufügen",
    "Remove": "Entfernen",
    "Save Podcasts": "Podcasts speichern",
    "Paste a show link from podcasts.apple.com": "Link zur Sendung von podcasts.apple.com einfügen",
    "Paste the show link from podcasts.apple.com. RSS feed URLs also work. The player will show each podcast as a title and play the latest episode.":
        "Füge den Link zur Sendung von podcasts.apple.com ein. RSS-Feed-Adressen funktionieren auch. Der Player zeigt jeden Podcast als Titel und spielt die neueste Folge.",
    # Wi-Fi
    "Connect to Wi-Fi": "Mit WLAN verbinden",
    "Wi-Fi network name": "WLAN-Name",
    "Wi-Fi password": "WLAN-Passwort",
    "Forget this WiFi network": "Dieses WLAN vergessen",
    "Forgetting this network will make the device form its own open Wi-Fi network. Connect to":
        "Wenn du dieses WLAN vergisst, öffnet der Player ein eigenes offenes WLAN. Verbinde dich mit",
    "Connect to the open Wi-Fi network": "Verbinde dich mit dem offenen WLAN",
    ", then browse to": " und öffne dann",
    "Connected to": "Verbunden mit",
    # System
    "Software Version": "Softwareversion",
    "Checking for updates...": "Suche nach Updates ...",
    "Update": "Aktualisieren",
    "Install Update": "Update installieren",
    "Install": "Installieren:",
    "the latest release": "die neueste Version",
    "Playback will pause and the player controls may be unavailable for a few minutes. Your Wi-Fi, Audiobookshelf login, podcasts, and settings will be kept.":
        "Die Wiedergabe pausiert, und die Bedienung reagiert einige Minuten lang eventuell nicht. WLAN, Audiobookshelf-Anmeldung, Podcasts und Einstellungen bleiben erhalten.",
    "Reboot": "Neu starten",
    "Restart the Chapter player without changing its settings.": "Den Player neu starten, ohne Einstellungen zu ändern.",
    "Are you sure you want to reboot?": "Wirklich neu starten?",
    "Playback will stop while the device restarts.": "Die Wiedergabe stoppt, während der Player neu startet.",
    "Restore Device to Default Settings": "Auf Werkseinstellungen zurücksetzen",
    "Restore Device": "Zurücksetzen",
    "Restore": "Zurücksetzen",
    "Clear this player and return it to Wi-Fi setup mode.": "Player leeren und zurück in den WLAN-Einrichtungsmodus versetzen.",
    "Are you sure you want to restore the device to default settings?": "Player wirklich auf Werkseinstellungen zurücksetzen?",
    "This clears the Audiobookshelf login, listening state, saved podcasts, and all saved Wi-Fi networks, and restores player settings to defaults. This cannot be undone.":
        "Das löscht die Audiobookshelf-Anmeldung, den gespeicherten Hörstand, die Podcasts und alle gespeicherten WLANs und setzt alle Einstellungen zurück. Das lässt sich nicht rückgängig machen.",
    # Messages
    "This page has expired. Reload the Chapter setup page, then try again.":
        "Diese Seite ist abgelaufen. Lade die Setup-Seite neu und versuch es noch einmal.",
    "Reload setup page": "Setup-Seite neu laden",
    "Invalid request length.": "Ungültige Anfragelänge.",
    "Request is too large.": "Die Anfrage ist zu groß.",
    "Request must use UTF-8 text.": "Die Anfrage muss UTF-8-Text enthalten.",
    "Wi-Fi network name is required.": "Bitte einen WLAN-Namen eingeben.",
    "Wi-Fi change submitted. The player will switch networks in a moment. Hold the volume knob for 10 seconds to show the new setup address.":
        "WLAN-Änderung übernommen. Der Player wechselt gleich das Netz. Halte den Lautstärkeknopf 10 Sekunden gedrückt, um die neue Setup-Adresse zu sehen.",
    "Player login saved. You can close this page and restart the player.":
        "Anmeldung gespeichert. Du kannst diese Seite schließen und den Player neu starten.",
    "Unknown player command.": "Unbekannter Befehl.",
    "Volume must be between 0 and 100.": "Die Lautstärke muss zwischen 0 und 100 liegen.",
    "Sleep timer must be a whole number of minutes.": "Der Einschlaf-Timer braucht eine ganze Zahl an Minuten.",
    "Rebooting the Chapter player. It will be available again shortly.":
        "Der Player startet neu und ist gleich wieder erreichbar.",
    "Preparing the software update.": "Das Software-Update wird vorbereitet.",
    "Software update started. Playback is paused while Chapter installs the latest release and restarts its services.":
        "Software-Update gestartet. Die Wiedergabe pausiert, während Chapter die neueste Version installiert und neu startet.",
    "Software update could not start. Please try again.": "Das Software-Update konnte nicht starten. Bitte versuch es noch einmal.",
    "Installing the software update.": "Das Software-Update wird installiert.",
    "The previous update did not finish. You can try installing it again.":
        "Das letzte Update wurde nicht abgeschlossen. Du kannst es noch einmal installieren.",
    "The previous software update failed.": "Das letzte Software-Update ist fehlgeschlagen.",
    "Unable to reach the Chapter release repository.": "Die Chapter-Versionen sind gerade nicht erreichbar.",
    "No stable Chapter releases were found.": "Keine stabile Chapter-Version gefunden.",
    "Unknown update error.": "Unbekannter Update-Fehler.",
    "Audiobookshelf request timed out.": "Audiobookshelf antwortet nicht (Zeitüberschreitung).",
    "Audiobookshelf login expired. Sign in again from the Chapter admin page.":
        "Die Audiobookshelf-Anmeldung ist abgelaufen. Bitte auf der Setup-Seite neu anmelden.",
    "No accessible libraries were found for this token.": "Für diesen Benutzer ist keine Bibliothek freigegeben.",
    "Podcast URL must start with http:// or https://.": "Die Podcast-Adresse muss mit http:// oder https:// beginnen.",
    "Podcast feed could not be read.": "Der Podcast-Feed konnte nicht gelesen werden.",
    "Podcast feed has no episodes.": "Der Podcast hat keine Folgen.",
    "Podcast feed unavailable.": "Der Podcast-Feed ist nicht erreichbar.",
    "Apple Podcasts lookup failed.": "Die Suche bei Apple Podcasts ist fehlgeschlagen.",
    "Apple Podcasts did not provide an RSS feed for that show.": "Apple Podcasts liefert für diese Sendung keinen RSS-Feed.",
}

WEB_PATTERNS: list[tuple[re.Pattern, Replacement]] = [
    (re.compile(r"^Logged in to (.+) as (.+)$"), r"Angemeldet bei \1 als \2"),
    (re.compile(r"^Logged in to (.+)$"), r"Angemeldet bei \1"),
    (re.compile(r"^Connected to (.+)$"), r"Verbunden mit \1"),
    (re.compile(r"^Login failed: (.+)$"), lambda m: "Anmeldung fehlgeschlagen: " + web_text(m.group(1))),
    (re.compile(r"^Podcast save failed: (.+)$"), lambda m: "Podcast konnte nicht gespeichert werden: " + web_text(m.group(1))),
    (re.compile(r"^Could not reach Audiobookshelf: (.+)$"), r"Audiobookshelf ist nicht erreichbar: \1"),
    (re.compile(r"^Audiobookshelf login failed with (.+)$"), r"Audiobookshelf-Anmeldung fehlgeschlagen: \1"),
    (re.compile(r"^Wi-Fi forget submitted\. In about 5 seconds, connect to (.+), then browse to (.+)$"),
     r"WLAN wird vergessen. Verbinde dich in etwa 5 Sekunden mit \1 und öffne dann \2"),
    (re.compile(r"^Default settings restored\. In about 5 seconds, connect to (.+), then browse to (.+)$"),
     r"Werkseinstellungen wiederhergestellt. Verbinde dich in etwa 5 Sekunden mit \1 und öffne dann \2"),
    (re.compile(r"^Updated successfully to (v?[\d.]+)\.?$"), r"Erfolgreich aktualisiert auf \1."),
    (re.compile(r"^Installing (v?[\d.]+)\. The player will restart when it is ready\.$"),
     r"Installiere \1. Der Player startet neu, sobald er fertig ist."),
    (re.compile(r"^Update failed: (.+)$"), r"Update fehlgeschlagen: \1"),
    (re.compile(r"^Chapter Player (v?[\d.]+) is already up to date\.$"), r"Chapter Player \1 ist schon aktuell."),
    (re.compile(r"^(Playing|Paused|Muted) · (.+)$"), lambda m: f"{WEB[m.group(1)]} · {m.group(2)}"),
]

# JavaScript string literals on the setup page. Only display texts:
# never words the script compares against (key names, phases, actions).
WEB_SCRIPT = {
    "Installing update...": "Update wird installiert ...",
    "Installing the latest stable release. Chapter will restart its services when ready.":
        "Die neueste Version wird installiert. Chapter startet danach neu.",
    "Finishing update...": "Update wird abgeschlossen ...",
    "Chapter is restarting with the newly installed version.": "Chapter startet mit der neuen Version neu.",
    "Update failed": "Update fehlgeschlagen",
    "The software update did not finish.": "Das Software-Update wurde nicht abgeschlossen.",
    "Update check needs attention": "Update-Prüfung fehlgeschlagen",
    "Waiting for the Chapter web service to restart.": "Warte auf den Neustart des Chapter-Webdienstes.",
    "Chapter could not check for software updates.": "Chapter konnte nicht nach Updates suchen.",
    "Chapter could not check for software updates. It will try again automatically.":
        "Chapter konnte nicht nach Updates suchen und versucht es automatisch erneut.",
    "A newer stable version of Chapter is ready to install.": "Eine neuere Version von Chapter ist bereit.",
    "Up to date": "Aktuell",
    "Update to ": "Aktualisieren auf ",
    "Update": "Aktualisieren",
    "Installing ": "Installiere ",
    " available": " verfügbar",
    "the latest release": "die neueste Version",
    "Nothing playing": "Gerade läuft nichts",
    "Playing...": "Starte ...",
    "Pausing...": "Pausiere ...",
    "Remove": "Entfernen",
    "Pause": "Pause",
    "Play": "Abspielen",
    "Paste a show link from podcasts.apple.com": "Link zur Sendung von podcasts.apple.com einfügen",
    "Playing": "Läuft",
    "Paused": "Pausiert",
    "Muted": "Stumm",
}


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def _lookup(text: str, table: dict, patterns: list) -> str:
    stripped = text.strip()
    if not stripped:
        return text
    found = table.get(stripped)
    if found is None:
        for pattern, replacement in patterns:
            match = pattern.match(stripped)
            if match:
                found = replacement(match) if callable(replacement) else match.expand(replacement)
                break
    if found is None:
        return text
    lead = text[: len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()):]
    return f"{lead}{found}{trail}"


def display(text: str) -> str:
    if not active() or not isinstance(text, str):
        return text
    return _lookup(text, DISPLAY, DISPLAY_PATTERNS)


def spoken(text: str) -> str:
    if not active():
        return text
    result = _lookup(text, SPOKEN, SPOKEN_PATTERNS)
    if result is text:
        result = _lookup(text, DISPLAY, DISPLAY_PATTERNS)
    return result


def espeak_voice(default: str) -> str:
    return ESPEAK_VOICE_DE if active() else default


def web_text(text: str) -> str:
    if not active():
        return text
    return _lookup(text, WEB, WEB_PATTERNS)


def json_value(data: dict, keys: tuple[str, ...] = ("state", "message")) -> dict:
    """Translate display fields of a JSON payload (never titles or codes)."""
    if not active():
        return data
    result = dict(data)
    for key in keys:
        value = result.get(key)
        if isinstance(value, str) and value:
            result[key] = web_text(value)
    return result


_SCRIPT_BLOCK = re.compile(r"(<script\b[^>]*>)(.*?)(</script>)", re.S | re.I)
_STYLE_BLOCK = re.compile(r"(<style\b[^>]*>.*?</style>)", re.S | re.I)
_TEXT_NODE = re.compile(r">([^<>]+)<")
_ATTRIBUTE = re.compile(r'\b(aria-label|placeholder|title|alt)="([^"]*)"')
_JS_STRING = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
_JS_TEXT_ASSIGNMENT = re.compile(r"(textContent\s*=|innerText\s*=|placeholder\s*=|\?|:|\+|\|\|)\s*$")


def _translate_text_node(match: re.Match) -> str:
    raw = match.group(1)
    unescaped = html.unescape(raw)
    translated = web_text(unescaped)
    if translated is unescaped or translated == unescaped:
        return match.group(0)
    return ">" + html.escape(translated, quote=False) + "<"


def _translate_attribute(match: re.Match) -> str:
    value = html.unescape(match.group(2))
    translated = web_text(value)
    if translated == value:
        return match.group(0)
    return f'{match.group(1)}="{html.escape(translated, quote=True)}"'


def _translate_script(script: str) -> str:
    def replace(match: re.Match) -> str:
        literal = match.group(1)
        translated = WEB_SCRIPT.get(literal)
        if translated is None:
            return match.group(0)
        # Only literals that are displayed, never ones that are compared.
        before = script[max(0, match.start() - 40):match.start()]
        if "===" in before[-6:] or "!==" in before[-6:] or "==" in before[-4:]:
            return match.group(0)
        if not _JS_TEXT_ASSIGNMENT.search(before):
            return match.group(0)
        escaped = translated.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    return _JS_STRING.sub(replace, script)


def html_page(page: str) -> str:
    """Translate a rendered setup page: text nodes, a few attributes, script texts."""
    if not active():
        return page
    styles: list[str] = []

    def keep_style(match: re.Match) -> str:
        styles.append(match.group(1))
        return f"\x00STYLE{len(styles) - 1}\x00"

    scripts: list[str] = []

    def keep_script(match: re.Match) -> str:
        scripts.append(match.group(1) + _translate_script(match.group(2)) + match.group(3))
        return f"\x00SCRIPT{len(scripts) - 1}\x00"

    page = _STYLE_BLOCK.sub(keep_style, page)
    page = _SCRIPT_BLOCK.sub(keep_script, page)
    page = _TEXT_NODE.sub(_translate_text_node, page)
    page = _ATTRIBUTE.sub(_translate_attribute, page)
    page = page.replace('<html lang="en"', '<html lang="de"')
    for index, script in enumerate(scripts):
        page = page.replace(f"\x00SCRIPT{index}\x00", script)
    for index, style in enumerate(styles):
        page = page.replace(f"\x00STYLE{index}\x00", style)
    return page
