SELECT DISTINCT t.object_id, m.mosaic_product_oid, m.tile_index,
m.file_name, m.file_path, m.release_name, m.product_type, m.category
FROM TAP_UPLOAD.targets AS t, sedm.mosaic_product AS m
WHERE m.instrument_name = 'VIS'
AND m.product_type = 'DpdMerBksMosaic'
AND m.category = 'SCIENCE'
AND m.release_name = 'Q1_R1'
AND m.fov IS NOT NULL
AND CONTAINS(POINT('ICRS', t.ra_deg, t.dec_deg), m.fov) = 1
