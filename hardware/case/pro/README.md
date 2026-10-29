# Chapter Pro – Gehäuse Variante A „Radio“

224 × 135 × 105 mm (B × H × T). Passt auf das Druckbett des AnkerMake M5 (235 × 235 mm).

![Vorschau](vorschau_chapter_pro.png)

## Hardware

- Raspberry Pi 3 A+ auf PiSugar 3 Plus (5000 mAh), beide 65 × 56 mm
- 3,12″-OLED SSD1322 UN312-5664-7: Platine 100,5 × 33,5 mm, Löcher 95 × 28,5 mm, Pins rechts
- Dayton Audio ND90-4 hinter einem Lochgitter, in einer eigenen, geschlossenen Kammer (≈ 1,3 l Luftvolumen)
  - rechnerisch Qtc ≈ 0,86 und fc ≈ 125 Hz
  - mit etwas Dämmwolle etwas tiefer
- MAX98357A
- 2 × KY-040 oben, beschriftet mit „Menü“ und „Lautstärke“, befestigt wie im Original-Chapter (zwei Dome mit M2,5-Einsätzen je Drehgeber, Knopf in einer 21-mm-Mulde). Unter jeder Halterung steht eine Stützwand bis zur Front: Beim Druck mit der Front nach unten tragen sich Steg und Säulen damit selbst, und die Halterung ist steifer.
- 3,5-mm-Kopfhörerbuchse (YACSEJAO D-Typ-Einbaukabel, 18 cm) an der rechten Seite auf halber Höhe, **von innen** montiert: außen sieht man nur die runde schwarze Front (Loch Ø 20,6 mm), keine Schrauben. Das Kabel steckt in der Klinkenbuchse des Pi 3 A+
- Einschaltknopf oben, mittig hinter den Drehknöpfen (Loch Ø 12,2 mm für einen flachen 12-mm-Edelstahltaster)
- „Franz Pro“ ist klein auf der Unterseite eingraviert

## Teile

| Datei | Anzahl | Druck |
|---|---|---|
| `stl/chapter-pro-gehaeuse.stl` | 1 | Front nach unten, **ohne Stützen** |
| `stl/chapter-pro-rueckwand.stl` | 1 | Außenseite nach unten |
| `stl/chapter-pro-lautsprecherring.stl` | 1 | flache Seite nach unten |
| `stl/chapter-pro-kopfhoererhalter.stl` | 1 | flache Seite nach unten |
| `../stl/chapter-case-knob-v5.stl` | 2 | wie beim Original |

**Empfohlene Einstellungen:**
- PLA oder PETG, 0,2 mm Schichthöhe
- 4 Wände, 20 % Gyroid-Füllung
- Skirt oder Brim höchstens 3 mm: das Gehäuse belegt 224 mm der 235 mm Bettbreite.

## Kleinteile

- **Gewindeeinsätze M2,5** (Ø 3,1 mm Bohrung, wie beim Original-Chapter): 6 Stück – 4 für die Drehgeber, 2 für den Verstärker
- **Gewindeeinsätze M3** (Ø 4,0 mm Bohrung, ca. 5,7 mm lang): 12 Stück
  - 6 in die Säulen für die Rückwand
  - 4 in die Lautsprecher-Dome
  - 2 in die Dome neben der Kopfhörerbuchse
- **Schrauben:**
  - 6 × M3×10 (Zylinderkopf) für die Rückwand
  - 4 × M3×12 für den Lautsprecherring
  - 4 × Blechschraube 2,5 × 6 mm für das Display (in die vorgebohrten Dome)
  - 6 × M2,5×5 für Drehgeber und Verstärker
- **2 Klett-Kabelbinder**, bis 12 mm breit, für den Pi/PiSugar-Stapel
- **USB-C-Einbaubuchse mit gewinkeltem Kabel**: Flansch ca. 25 × 8 mm, Gewindelöcher 17 mm Mittenabstand. Der Flansch sitzt außen in einer 2 mm tiefen Mulde, verschraubt wird von innen.
- **Moosgummi-Dichtband** (ca. 3 × 2 mm) auf die hintere Kante der Lautsprecherkammer
- etwas **Dämmwolle** oder Polyesterwatte für die Kammer
- **4 Gummifüße** Ø 10 mm, für die Mulden im Boden
- **Drucktaster 12 mm**, Edelstahl, flacher Kopf, Schließer (optional mit LED-Ring) – parallel an die Taste des PiSugar gelötet
- **2 × M3×12** für den Kopfhörerhalter (die mitgelieferten Schrauben und Muttern der Buchse werden nicht gebraucht)

## Montage

1. **Gewindeeinsätze einschmelzen.**
2. **Lautsprecher:** Den ND90-4 von innen in den Zentrierring über dem Gitter legen. Den Lautsprecherring mit dem Rand zum Lautsprecher aufsetzen und mit 4 × M3×12 festziehen. So spielt der Lochkreis des Lautsprecherkorbs keine Rolle.
3. **Kabel:** Das Lautsprecherkabel durch das Loch in der Trennwand führen und das Loch mit Heißkleber abdichten. Die Kammer locker mit Dämmwolle füllen.
4. **Kopfhörerbuchse:** Den Halter über Kabel und Buchsenkörper schieben, die Buchse von innen mit dem Flansch in die flache Mulde um das runde Loch legen (runde Front zeigt nach außen) und den Halter mit 2 × M3×12 auf die beiden Dome schrauben. Der Rand des Halters drückt den Flansch an die Wand.
5. **Display:** Das Modul mit den Pins nach rechts (von vorn gesehen) auf die 4 Dome legen und mit 4 Blechschrauben festschrauben. Das Fenster sitzt genau über der Leuchtfläche laut Datenblatt.
6. **Verstärker:** Den MAX98357A mit 2 × M2,5×5 auf die zwei Dome an der Trennwand schrauben (Lochabstand 13,2 mm wie im Original-Chapter), Lautsprecherkabel kommt direkt daneben durch die Trennwand.
7. **Drehgeber:** Wie beim Original-Chapter: jeden KY-040 mit 2 × M2,5×5 von unten an die zwei Dome neben seinem Loch schrauben (Achse nach oben durch das Loch), dann die Knöpfe aufstecken. Sie sitzen in einer flachen Mulde im Deckel.
8. **Rückwand bestücken:**
   - Den Pi/PiSugar-Stapel mit dem Akku nach unten zwischen die 4 Eckführungen legen – die Seite mit HDMI- und Klinkenbuchse nach oben und die Klinkenbuchse nach links (zur Trennwand), damit der Stecker nicht an die Kopfhörerbuchse stößt.
   - Mit 2 Klett-Kabelbindern durch die Ösen festzurren. Alle Kanten bleiben frei.
   - Die USB-C-Einbaubuchse in die Rückwand schrauben und das Kabel in den USB-C-Anschluss des PiSugar stecken.
9. **Gehäuse schließen:**
   - Dichtband auf die Kammerkante kleben.
   - Rückwand aufsetzen und mit 6 × M3×10 verschrauben.

## Verbindung durch die Trennwand

Nur der Lautsprecher sitzt in der linken Kammer, alles andere rechts. Durch die Trennwand geht nur das zweiadrige Lautsprecherkabel: ein Ø-6-mm-Loch unten, nah an der Rückseite. Danach das Loch mit Heißkleber dicht machen.

## Noch offen

- **Glasdicke des Displays:** Die Dome sind 2,6 mm hoch. Liegt das Glas zu fest an, die Dome etwas abschleifen. Bleibt ein Spalt, ist das unkritisch.
- **Einschalten:** Wo der Taster am PiSugar sitzt, ist nicht dokumentiert. Der PiSugar 3 kann sich laut Hersteller automatisch einschalten, sobald wieder Strom anliegt.

## Anpassen

Alle Maße stehen oben in `make_chapter_pro.py`.

```bash
python3 make_chapter_pro.py stl
```
