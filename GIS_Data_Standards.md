## GIS Data Standards for Sagehen Meadows

### Coordinate System for Sagehen Data

EPSG:3491 (NAD83 NSRS 2008 / California Zone 2 State Plane Coordinate System)

*Note* California State Plane Coordinate System uses a Lambert Conformal Conic projection. Error must not exceed 0.01%.
Zone 2: Sierra / Nevada / Placer counties (Sagehen)
Zone 3: Mariposa / Madera / Mono

#### Projections
Using conformal projection preserves correct shapes of small areas because graticule lines intersect at 90-degree angles and at all points, the scale is the same in all directions. Ex. Lambert conformal.

Note: Use equal-area / equivalent projection to preserve area so that all areas over the map have the same proportional relationship to areas on Earth that they represent. Ex. California Albers.

#### Datums
Use NAD83 if in N America, collecting raw data. It’s the same as WGS84. WGS84 allows comparison with GPS data collected elsewhere in the world.

### File Types
Raster: geotiff
Vector: geojson
Geodatabase:  <need to determine>

### Naming Conventions
`Sagehen_<ContentDescription>_<OwnerLastName>_<EPSGCode>`

### Our Needs
Cross-compatibility (e.g. QGIS/ArcGIS/APIs)
Open-source standards

### Yet to Define
- Standards for Metadata