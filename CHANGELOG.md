# Changelog

All notable changes to Chapter Player for Audiobookshelf are documented here.

## Unreleased

## [0.3.18] - 2026-10-26 (Mgns55/chapter-ger)

- Serien werden im Menü zu einem Eintrag zusammengefasst; Auswahl öffnet die Folgen in Reihenfolge (mit "Zurück").
- Profile: mehrere Audiobookshelf-Logins, Wechsel per langem Druck auf den Menü-Knopf, auf der Setup-Seite oder aus Home Assistant.
- PiSugar-3-Akku: Anzeige im Display, Warnung bei 15 %, sauberes Herunterfahren bei 5 % (sudoers-Regel für poweroff).
- Treiber für 3,12"-OLED mit SSD1322 (auch für den Boot-Splash), zweizeilige Titel auf dem großen Display.
- Verstärker kann im Leerlauf über GPIO 17 abgeschaltet werden (gegen Knacken).
- Home-Assistant-Anbindung per MQTT mit Discovery (eigener Dienst audiobookshelf-player-mqtt).
- Hörzeit-Übersicht für Eltern auf der Setup-Seite.
- Ohne WLAN bleibt das Menü bedienbar, gespeicherte Bücher spielen offline.
- Installer: I2C an, HDMI-Ton aus (dtoverlay=vc4-kms-v3d,noaudio), Pakete i2c-tools und python3-paho-mqtt.

## [0.3.17] - 2026-10-26 (Mgns55/chapter-ger)

- Offline-Speicher: Hörbücher werden beim ersten Abspielen im Hintergrund auf die SD-Karte geladen. Danach startet die Wiedergabe aus der lokalen Datei und funktioniert auch ohne WLAN.
- Ohne Verbindung zum Server spielt Chapter gespeicherte Bücher ab und merkt sich die Position; sie wird beim nächsten Kontakt mit Audiobookshelf nachgetragen.
- Älteste Bücher werden automatisch gelöscht (Grenze 40 GB bzw. mindestens 2 GB frei, einstellbar über CHAPTER_AUDIO_CACHE_MAX_GB).
- Einstellungen: Zeile "Offline-Speicher" mit Belegung und Knopf zum Leeren.

## [0.3.16] - 2026-10-25 (Mgns55/chapter-ger)

- Setup-Seite: Audiobookshelf-Status wird eine Minute zwischengespeichert statt bei jedem Aufruf abgefragt.
- Port-80-Weiterleitung wartet bis zu 30 statt 10 Sekunden auf die Setup-Seite (kein Fehler 502 mehr auf langsamen Boards).

## [0.3.15] - 2026-10-25 (Mgns55/chapter-ger)

- Ist ein Heim-WLAN gespeichert, zeigt das Display beim Start "Verbinde mit WLAN" statt der Hotspot-Anleitung.
- Installer überschreibt beim Update abweichende alte Versionsmarken (fetch --force).

## [0.3.14] - 2026-10-25 (Mgns55/chapter-ger)

- Beim Start bis zu 90 Sekunden auf das gespeicherte WLAN warten, bevor der Setup-Hotspot startet. Langsame Boards landeten sonst unnötig im Hotspot.

## [0.3.13] - 2026-10-25 (Mgns55/chapter-ger)

- Deutsche Oberfläche für Display, Sprachnavigation und Setup-Seite (`CHAPTER_LANGUAGE=de`).
- Bluetooth lässt sich in den Einstellungen der Setup-Seite ganz abschalten (Funk aus, kein Bluetooth-Menü, schnellere Seite).
- Display: unveränderte Bilder werden nicht neu gesendet, schnellere Bildumwandlung, SPI-Takt 4 MHz statt 1 MHz.
- WLAN-Status ohne Funknetz-Suche und nur alle 5 statt 2 Sekunden; Wiedergabestatus wird seltener auf die SD-Karte geschrieben.

## [0.3.12] - 2026-10-14

- Added a configurable `1x`, `1.5x`, or `2x` playback speed setting with live updates and pitch-preserving audio.

## [0.3.11] - 2026-10-04

- Announce Volume-knob adjustments at 10% intervals when spoken navigation is enabled.
- Keep Volume-knob adjustments at or above 10% and ignore the knob's mute press while spoken navigation is enabled.

## [0.3.10] - 2026-10-03

- Install and immediately enable BlueALSA so Bluetooth speakers and headphones work on clean Raspberry Pi OS Lite installations and after software updates.

## [0.3.9] - 2026-10-02

- Shorten the administration page title and heading to `Chapter Player`.

## [0.3.8] - 2026-10-02

- Start new and restored players with an empty podcast list so parents explicitly choose every podcast.
- Preserve resolver compatibility for previously supported podcast links without adding them to the library automatically.
- Reconcile the wiring and enclosure documentation with the released hardware, including USB-C power, fuse, amplifier, speaker, and control placement guidance.
- Expand the public-release safety notes and ignore locally generated promotional images.

## [0.3.7] - 2026-10-02

- Hide the redundant successful-update detail beneath the current software version.

## [0.3.6] - 2026-10-02

- Enlarge the library alphabet jump letter without changing title, author, or series alignment.

## [0.3.5] - 2026-10-02

- Keep the administration page on rapid update polling while services restart.
- Reload the administration page automatically after the new web service reports completion.

## [0.3.4] - 2026-10-02

- Pause playback and show the OLED update warning before installation work begins.
- Wait for an OLED-ready acknowledgement before starting the updater, with a bounded fallback timeout.

## [0.3.3] - 2026-10-02

- Silence paused and muted playback completely while keeping the I2S audio path active for pop-free resume.

## [0.3.2] - 2026-10-02

- Show an `UPDATING / DO NOT POWER OFF` warning on the OLED for the full software update.
- Refresh the administration page automatically when an update completes.

## [0.3.1] - 2026-10-02

- Consolidated update availability and confirmation controls into the Software Version section.

## [0.3.0] - 2026-10-02

- Added System-tab release checks and one-button stable software updates that preserve device settings.

## [0.2.2] - 2026-10-02

- Return from the library to the current playback controls after five seconds of inactivity while audio is playing.
- Refine the lightweight eSpeak NG spoken-navigation pacing and pitch while retaining its smoother default voice.

## [0.2.1] - 2026-10-02

- Documented the trusted-local-network security model and safe deployment boundaries.
- Added GitHub Actions coverage for the test suite, syntax checks, and Raspberry Pi OS Lite installer simulation.
- Made the installer simulation portable across macOS and Linux.

## [0.2.0] - 2026-10-02

- Added a web setting to order the player library by title or by author last name.
- Added optional offline spoken navigation for highlighted book titles and controls.
- Added the Chapter color logo and refined the tabbed administration interface.
- Added CSRF protection to setup-page forms and live player controls.
- Pinned the Raspberry Pi installer to versioned releases for reproducible installs.

## [0.1.0] - 2026-10-01

Initial public release.

- Raspberry Pi Zero 2 W/WH appliance interface with SH1122 OLED and two rotary controls.
- Audiobookshelf login, library browsing, playback, resume, and progress synchronization.
- Internal MAX98357A speaker output and Bluetooth audio support.
- Podcast support, sleep timer, screensavers, and web administration.
- Automated Raspberry Pi OS Lite installer, first-boot setup hotspot, and captive portal support.
- Printable enclosure files, wiring documentation, assembly references, and parts list.
- Shared storage ownership handling and an isolated installer simulation for clean-install validation.
