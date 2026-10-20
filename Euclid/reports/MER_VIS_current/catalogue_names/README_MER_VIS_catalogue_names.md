# MER VIS catalogue cross-identifications

Queried 20 October 2026 using the CDS X-Match bulk service.

Sources:
- SIMBAD: https://simbad.cds.unistra.fr/simbad/
- VizieR HyperLEDA VII/237/pgc: https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=VII/237
- CDS X-Match: https://cdsxmatch.cds.unistra.fr/

The search used Euclid catalogue ICRS RA/Dec, a 5-arcsec candidate radius, galaxy object types and SIMBAD aliases. PGC and LEDA identifiers with the same number were treated as the same identity. Familiar Messier, NGC, IC, UGC and ESO identifiers were preferred when available; otherwise PGC or the SIMBAD identifier was retained.

Only unique galaxy identities within the full candidate radius and separated by <=2 arcsec were annotated. This gives 227 adopted names (224 SIMBAD; 3 additional VizieR), one ambiguous target and 13 outside the secure radius. No Messier, NGC or IC name was returned among the accepted identifications. A secure positional match is not independent confirmation of morphology or of a physical bar.

MER_VIS_catalogue_name_matches.csv includes all 2777 targets. The JSON includes candidates for unassigned cases. Raw service responses and SIMBAD aliases preserve provenance. A non-match means no secure identity in these particular searches, not that the target is uncatalogued everywhere.
