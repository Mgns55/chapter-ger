# Chapter Pro – Gehäuse Variante A „Radio“

224 × 135 × 105 mm (B × H × T). Passt auf das Druckbett des AnkerMake M5 (235 × 235 mm).

![Vorschau](vorschau_chapter_pro.png)

## Hardware

- Raspberry Pi 3 A+ auf PiSugar 3 Plus (5000 mAh)
- 3,12″-OLED SSD1322 (256 × 64 px), Modul bis 102 × 35 mm
- Dayton Audio ND90-4 hinter einem Lochgitter, in einer eigenen, geschlossenen Kammer (≈ 1,3 l Luftvolumen)
  - rechnerisch Qtc ≈ 0,86 und fc ≈ 125 Hz
  - mit etwas Dämmwolle etwas tiefer
- MAX98357A
- 2 × KY-040 oben, beschriftet mit „Menü“ und „Lautstärke“

## Teile

| Datei | Anzahl | Druck |
|---|---|---|
| `stl/chapter-pro-gehaeuse.stl` | 1 | Front nach unten, **ohne Stützen** |
| `stl/chapter-pro-rueckwand.stl` | 1 | Außenseite nach unten |
| `stl/chapter-pro-lautsprecherring.stl` | 1 | flache Seite nach unten |
| `stl/chapter-pro-displayklemmen.stl` | 1 (= 4 Klemmen) | flach |
| `../stl/chapter-case-knob-v5.stl` | 2 | wie beim Original |

**Empfohlene Einstellungen:**
- PLA oder PETG, 0,2 mm Schichthöhe
- 4 Wände, 20 % Gyroid-Füllung
- Skirt oder Brim höchstens 3 mm: das Gehäuse belegt 224 mm der 235 mm Bettbreite.

## Kleinteile

- **Gewindeeinsätze M3** (Ø 4,0 mm Bohrung, ca. 5,7 mm lang): 10 Stück
  - 6 in die Säulen für die Rückwand
  - 4 in die Lautsprecher-Dome
- **Gewindeeinsätze M2,5** (Ø 3,1 mm Bohrung, wie beim Original-Chapter): 8 Stück
  - 4 für die Display-Klemmen
  - 4 für die Pi-Abstandshalter
- **Schrauben:**
  - 6 × M3×10 (Zylinderkopf) für die Rückwand
  - 4 × M3×12 für den Lautsprecherring
  - 4 × M2,5×6 für die Display-Klemmen
  - M2,5 für den Pi/PiSugar-Stapel: die Länge passend zu den PiSugar-Abstandsbolzen wählen
- **USB-C-Einbaubuchse mit kurzem Kabel** (Panel-Mount): Öffnung 12,5 × 6,5 mm, Langlöcher für 25–32 mm Schraubabstand
- **Moosgummi-Dichtband** (ca. 3 × 2 mm) auf die hintere Kante der Lautsprecherkammer
- etwas **Dämmwolle** oder Polyesterwatte für die Kammer
- **4 Gummifüße** Ø 10 mm, für die Mulden im Boden

## Montage

1. **Gewindeeinsätze einschmelzen.**
2. **Lautsprecher:** Den ND90-4 von innen in den Zentrierring über dem Gitter legen. Den Lautsprecherring mit dem Rand zum Lautsprecher aufsetzen und mit 4 × M3×12 festziehen. So spielt der Lochkreis des Lautsprecherkorbs keine Rolle.
3. **Kabel:** Das Lautsprecherkabel durch das Loch in der Trennwand führen und das Loch mit Heißkleber abdichten. Die Kammer locker mit Dämmwolle füllen.
4. **Display:**
   - Das Display von innen vor das Fenster halten und durch die Front ausrichten.
   - Mit den 4 Klemmen festschrauben. Die Langlöcher gleichen die Lage aus.
5. **Drehgeber:**
   - Die KY-040 von innen durch die Löcher oben stecken und mit Unterlegscheibe und Mutter festziehen.
   - Die Wand dort ist auf 2 mm verdünnt.
6. **Rückwand bestücken:**
   - Den Pi/PiSugar-Stapel auf die Abstandshalter der Rückwand schrauben. Der Akku zeigt zur Rückwand, die Abstandshalter sind 18 mm hoch.
   - Die USB-C-Buchse einbauen.
7. **Gehäuse schließen:**
   - Dichtband auf die Kammerkante kleben.
   - Rückwand aufsetzen und mit 6 × M3×10 verschrauben.

## Vor dem Druck prüfen

- **Display:** Die genauen Maße des Moduls UN312-5664-7 sind nicht verifiziert. Ausgelegt ist das Gehäuse für Module bis 102 × 35 mm mit einer Sichtfläche von ca. 77–79 × 19–21 mm.
- **PiSugar 3 Plus:** Die Akkudicke und die Lage von USB-C-Buchse und Taste sind nicht verifiziert. Die Rückwand ist ein kurzer Druck und lässt sich leicht anpassen.

## Anpassen

Alle Maße stehen oben in `make_chapter_pro.py`.

```bash
python3 make_chapter_pro.py stl
```
