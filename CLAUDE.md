# Projekt-Notizen

## Design-Vorlieben (vom Nutzer)
- Kreative Designs, die die **Mechanik ausnutzen**: z. B. die Klapp-/„Clap“-Funktion der Slingshot wird zu einem Zähne-/Beiß-Design. Nicht nur Muster auf Flächen.
- Spannweite Sci-Fi bis Fantasy, gern „tactical“ (fühlbare Strukturen), Farbaufteilung für Mehrfarbdruck.
- Body darf verändert werden, wo es Funktion und Stabilität nicht betrifft.
- Erst Vorschläge mit Bild zeigen, dann bauen.
- Muss **druckbar** bleiben (A1, 0,4er Düse) und das **Grunddesign der Karte** darf nicht kaputtgehen (Kontur/Dicke gleich). `moshu/tools/build.py` prüft das automatisch, Designs nur ausliefern, wenn alle Checks OK sind.

## Moshu Slingshot – Fakten
- Originalteile sind nicht im Repo (öffentlich, fremde Lizenz) → `moshu/parts/` ist gitignored, per `moshu/tools/extract_3mf.py` erzeugen.
- Griff hängt über 12,2-mm-Glied (nut_plate/screw_plate) an Rahmen-Achse (28, 6). Zugeklappt füllt er die freie Rahmenecke → Karte 68×106.
- Mundlinie = Rahmenkante x=34, y≈6–56. Rahmenwand neben Abzugsfenster nur ~1 mm → Zähne nur ANsetzen, nicht hineinschneiden.
- Über dem Kugelkanal im Griff nur ~1 mm Haut → keine Gravur dort (`load()` berechnet sichere Zonen).
- Drucker: Bambu Lab A1, Außenseite liegt auf dem Druckbett.
