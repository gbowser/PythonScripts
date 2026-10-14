# Q1 barred spiral candidate shortlist

Selected the first 25 qualifying entries in catalogue order after
streaming 2902 rows of Zenodo record 15106473; this is not an exhaustive
census or a ranking of the best/largest galaxies. 25 have verified
public individual calibrated VIS FITS metadata in release Q1_R1.

Selection: expected vote fractions >=0.8 for featured/disc, not edge-on,
spiral arms, and strong+weak bar. The catalogue training-cut warning must be
false. These are automated Galaxy Zoo/Zoobot morphology candidates, not
independently visually confirmed classifications. Conditional fractions must
not be interpreted as unconditional probabilities of a galaxy being barred.

Files: verified_barred_spirals.csv holds the available list and one example
calibrated exposure per object; availability_checks.csv includes all checks.
galaxy_cones.csv can be passed to build_euclid_VIS_NISP_frame_query.py --targets-csv.
manual_download_top5.sql returns at most five exposure rows across all targets.
No FITS images have been downloaded; example frame files may be shared by many
galaxies. Footprint coverage includes the galaxy centre but does not prove the
entire galaxy is covered, or exclude detector gaps/bad pixels. Full exposures
are multi-extension files, not galaxy-centred cutouts.

The radius is half the catalogue display cutout width, converted to arcminutes;
it is NOT a measured galaxy or bar radius and is not deprojected. Object IDs
are retained as exact strings, including negative signs. No NGC/IC aliases
have been asserted. Centres are catalogue barycentres in ICRS decimal degrees.

Morphology data: https://zenodo.org/records/15106473
Morphology paper: https://doi.org/10.1051/0004-6361/202555140
VIS FITS format: https://doi.org/10.1051/0004-6361/202554594
Archive: https://eas.esac.esa.int/sas/
Verified UTC: 2026-10-13T09:54:10.234961+00:00
