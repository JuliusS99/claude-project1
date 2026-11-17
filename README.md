# Card Slingshot (parametrisch)

Eigenes, editierbares Modell einer Schleuder im Kreditkartenformat (54 × 85,6 mm), angelehnt an den Stil von „card style slingshots“. Es ist **keine** Kopie einer MakerWorld-Datei.

![preview](preview.png)

## Dateien
- `slingshot.scad`: Quelle. In [OpenSCAD](https://openscad.org) öffnen, oben die Werte ändern (oder im Customizer-Panel), dann F6 → Export STL.
- `slingshot.stl`: druckfertige Datei mit den Standardwerten.

## Wichtige Parameter
| Parameter | Standard | Wirkung |
|---|---|---|
| `thickness` | 6 | Dicke; mehr = stabiler |
| `gap_w` / `gap_depth` | 28 / 40 | Gabelöffnung |
| `band_style` | `"groove"` | `"groove"` = umwickeln + binden, `"slot"` = Flachband durchfädeln, `"none"` |
| `finger_d` | 20 | Fingerloch, 0 = keins |
| `lanyard_d` | 4 | Loch für Schlaufe, 0 = keins |
| `label` | `""` | eingravierter Text |

Über die Kommandozeile: `openscad -o out.stl -D 'thickness=8' -D 'band_style="slot"' slingshot.scad`

## Druck
Flach liegend drucken, 100 % Infill oder ≥ 5 Wände, PETG oder PA-CF statt PLA. Mit leichten Bändern anfangen. Nie auf Menschen oder Tiere zielen.

---

# Moshu Card Slingshot – Biss-Designs

Farb- und Biss-Designs für die [Moshu Card-Style Slingshot](https://makerworld.com/de/models/3087259). Die Original-Geometrie stammt vom Designer und ist **nicht** in diesem Repo.

Beim Aufklappen schwenkt der Griff an einem Verbindungsglied weg, und die Kante zwischen Rahmen und Griff öffnet sich wie ein Kiefer. Am Rahmen sitzen echte Zähne. Die passenden Taschen im Griff werden aus der Schwenkbewegung berechnet.

![Konzepte](moshu/designs/concepts.png)

## Bauen
```
pip install numpy trimesh shapely scipy matplotlib manifold3d rtree networkx
python3 moshu/tools/extract_3mf.py <MakerWorld-Download>.3mf moshu/parts
python3 moshu/tools/build.py all        # oder z. B.: build.py MAW
```
Ergebnis in `moshu/out/<design>/` (gitignored): STLs pro Teil und Farbe, `checks.txt` und `preview.png`.

`build.py` bricht mit Fehler ab, wenn eine Prüfung scheitert:
- **Karte:** Außenkontur und Dicke unverändert, nichts steht über.
- **Druckbar:** keine Details oder Wände unter 0,8 mm, Rillen überbrückbar, alle Netze wasserdicht (so geprüft, wie ein Slicer die STL liest).
- **Funktion:** Die Zähne ragen nicht ins Abzugsfenster, und der Griff klappt von der Karte frei bis in die Pistolenstellung.

## In Bambu Studio
1. Alle STLs eines Teils gleichzeitig öffnen (z. B. `frame_*.stl`) und „als ein Objekt mit mehreren Teilen laden?“ mit **Ja** beantworten.
2. Jedem Teil das Filament aus `checks.txt` zuweisen.
3. Die Außenseite liegt bereits unten auf dem Bett. Farbwechsel gibt es nur in den ersten 3 Schichten.

Unverändert aus dem Original drucken: `slider`, `spring`, `cover_plate`, `nut_plate`, `screw_plate`, `knob` (der Knopf in der Augenfarbe). Dazu 2× M3-Senkkopfschraube und 2× M3-Mutter.
