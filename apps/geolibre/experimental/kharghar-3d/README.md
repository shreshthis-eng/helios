# Kharghar 3D sandbox

This scene is also Helios's first visible application shell. It can be deployed
to the shared Vercel preview so every teammate can inspect the same map from a
phone or laptop. The next UI step is rectangle and custom-polygon AOI drawing;
the selected GeoJSON will later be sent to the analysis API. Keep ranking logic
out of this page, preserve layer attribution, and label every proxy dataset.

This is an exploratory GeoLibre/MapLibre scene for the hackathon demo. It is
intentionally isolated from the official Helios pipeline, but uses a bounded
OpenStreetMap building extract with real OSM way IDs and height/level tags,
alongside the checked-in Person 1 Google Open Buildings and Copernicus layers.
It must not be used for site selection, engineering, or public claims.

The default viewer now uses the public OpenFreeMap vector-tile source for
worldwide OSM buildings, so it also works from the `file:///` URL and does not
depend on a local GeoJSON fetch. OpenFreeMap exposes `render_height` and
`render_min_height`, which are used for the 3D extrusion.

Serve this directory over HTTP when you also want the yellow Person 1 overlay
(the local GeoJSON source is intentionally kept as a real file rather than
embedded in the page):

```powershell
python -m http.server 8765
```

Then open `http://localhost:8765/`. The scene uses MapLibre GL JS,
OpenStreetMap raster tiles, and public AWS Terrain Tiles for the live DEM
surface. The local Copernicus GeoTIFF is retained as the offline provenance
artifact for a future native GeoLibre project; browsers do not render GeoTIFF
files as MapLibre terrain tiles directly.

The live terrain tiles are displayed with attribution to AWS Terrain Tiles and
the underlying elevation providers. OSM building data is licensed under ODbL;
the exact bounded extract URL and height fallback policy are stored in the
GeoJSON metadata. Person 1 footprints are drawn as yellow reference outlines,
while OSM buildings provide the main 3D model. Terrain exaggeration is
deliberately independent: it never scales or relocates buildings. Building
bases are clamped to the terrain datum, so no height control can lift them.

This is still LoD1 geometry, so it will look like clean extruded solids rather
than the textured, roof-detailed photogrammetry in the reference image. That
appearance requires a Kharghar-specific textured 3D Tiles/mesh dataset (for
example a licensed photogrammetry capture or a locally generated tileset from
LiDAR/mesh data). To replace the sample later, swap the building layer in
`index.html` for that validated GeoLibre 3D-Tiles source.

For a true GeoLibre 3D-Tiles test, the official public example project is
available at `https://share.geolibre.app/giswqs/3d-tiles`; a Kharghar-specific
photogrammetry tileset would require a separate licensed 3D capture or a
locally generated tileset.

## Google Photorealistic 3D Tiles

The viewer can load Google Photorealistic 3D Tiles directly through
GeoLibre's `maplibre-gl-3d-tiles` integration. These tiles are visual context
only; Helios analysis continues to use its own building and solar datasets.
At deploy time, define `window.HELIOS_GOOGLE_MAPS_API_KEY` before this module
loads. Enable the Map Tiles API and restrict the key to the Helios domains.
Never commit a key to this repository. Google attribution must remain visible
in the tiles control.

## Digital-twin interaction pattern

The viewer follows the useful visual pattern from God's Eye View without
copying its unrelated intelligence layers: a realistic globe is the backdrop,
the selected AOI becomes the active scene, and Helios overlays remain separate,
identified, and source-labeled. Selecting a polygon now automatically focuses
the 3D camera on that AOI. Building rankings, rooftop annotations, and solar
factors are then rendered as Helios-owned analytical layers over the physical
context.

## Person 3 handoff

Person 3's open PR (#11) was checked before consolidating this scene. It
contains deterministic solar-yield and screening-economics features keyed by
`candidate_id`, including usable area, shading factor, annual POA resource,
capacity, annual yield, capex, energy value, payback, confidence, and
provenance. It does **not** contain 3D geometry, LiDAR, roof meshes, or a
3D-Tiles source, so it cannot supply the building models shown in the viewer.
Those remain a Person 1/Person 2 spatial-data concern; Person 3's fields should
be joined later in the candidate popup or ranking output, not duplicated into
the visualization source layer.
