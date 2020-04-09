## GIS Data Standards for Sagehen Meadows

### Coordinate System for Sagehen Data

EPSG:3491 (NAD83 NSRS 2008 / California Zone 2 State Plane Coordinate System)

*Note* California State Plane Coordinate System uses a Lambert Conformal Conic projection. Error must not exceed 0.01%.
Zone 2: Sierra / Nevada / Placer counties (Sagehen)
Zone 3: Mariposa / Madera / Mono

##### About Projections
Using conformal projection preserves correct shapes of small areas because graticule lines intersect at 90-degree angles and at all points, the scale is the same in all directions. Ex. Lambert conformal.

Note: Use equal-area / equivalent projection to preserve area so that all areas over the map have the same proportional relationship to areas on Earth that they represent. Ex. California Albers.

##### About Datums
Use NAD83 if in N America, collecting raw data. It’s the same as WGS84. WGS84 allows comparison with GPS data collected elsewhere in the world.


### File Types
###### Raster: geotiff
GeoTiff is a cross-platform compatible, uncompressed, industry standard for raster data (pixels or grid cells).

###### Vector: geojson
[GeoJSON](https://geojson.org/) is an open-source geospatial data interchange format based on javascript object notation that encodes geographic data structures (i.e. features, properties and spatial extent). The [RFC 1746](https://tools.ietf.org/html/rfc7946) (Aug 2016) is the most recent GeoJSON format (as of April 2020). GeoJSON is text-editable and supports web mapping.

###### Geodatabase:  need to confirm
*Need to confirm if cross-compatible with everyone's GIS setup*
[OGC GeoPackage](https://www.geopackage.org/) is an open stardard, server-less and self-contained SQLite db that can contain vectors, rasters, tiles, attributes and extensions. It appears to be compatible across platforms (e.g. QGIS, ESRI 10.2.2 ArcGIS desktop, GDAL, SpatialLite). Extension: .gpkg

### Naming Conventions
`Sagehen_<ContentDescription>_<OwnerLastName>_<EPSGCode>`

### Our Needs
- Cross-compatibility (e.g. QGIS/ArcGIS/APIs)
- Open-source standards

### Yet to Define
- Standards for Metadata

### Command-line Cheatsheet

gdaltransform transforms coordinate systems of a file
`gdaltransform -s_srs EPSG:XXXX -t_srs EPSG:3491 srcfilename Sagehen_<DESC>_Natali_3491.geojson`

ogr2ogr converts between file formats
`ogr2ogr -f GeoJSON filename.geojson filename.shp -lco RFC7496=YES`

ogr2ogr can convert file formats + transform  coordinate systems
`ogr2ogr -s_srs EPSG:XXXX -t_srs EPSG:3491 -f GEOJSON Sagehen_<DESC>_Natali_3491.geojson inputfilename`

`ogr2ogr -s_srs EPSG:1022423 -t_srs EPSG:3491 -f GEOJSON /Users/jnat/Box/gradSchool/Projects/SierraMeadows_Research/2018_ISEECI_Meadows/Data/Sagehen/Data/GIS/Sagehen_FieldChannels_Natali_3491.geojson /Users/jnat/Box/gradSchool/Projects/SierraMeadows_Research/2018_ISEECI_Meadows/Data/Sagehen/Data/GIS/Sagehen_Channels.geojson`

For 102243 PROJ.4 definition

`ogr2ogr -s_srs '+proj=lcc +lat_1=37.06666666666667 +lat_2=38.43333333333333 +lat_0=36.5 +lon_0=-120.5 +x_0=2000000 +y_0=500000 +ellps=GRS80 +units=m +no_defs 3' -t_srs EPSG:3491 -f GEOJSON /Users/jnat/Box/gradSchool/Projects/SierraMeadows_Research/2018_ISEECI_Meadows/Data/Sagehen/Data/GIS/Sagehen_Wells_Natali_3491.geojson /Users/jnat/Box/gradSchool/Projects/SierraMeadows_Research/2018_ISEECI_Meadows/Data/Sagehen/Data/GIS/Sagehen_Wells.gpkg`

