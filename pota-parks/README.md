# POTA Parks Near Redmond

`redmond-30mi-activations.kml` — every [Parks on the Air](https://pota.app) reference within
30 straight-line miles of 25823 NE 30th Ct, Redmond, WA 98053 (grid CN97ap).

Open it in Google Earth (Pro or web) or any KML viewer. It includes:

- One pin per park, labeled with its activation count. Marker color and size both scale
  with that count (pale/small = few activations, deep green/large = many), so
  low-activation targets stand out at a glance.
- A **Home QTH** pin at the address above.
- Dashed range rings at 10, 20, and 30 miles.
- Click any park pin for its full name, reference code, distance, activation attempts,
  total QSOs, and a link to its page on pota.app.

Source data: the [POTA public API](https://api.pota.app/locations/US-WA), fetched
2026-09-04. Distances are great-circle from the address above; re-run against that
endpoint to refresh counts.
