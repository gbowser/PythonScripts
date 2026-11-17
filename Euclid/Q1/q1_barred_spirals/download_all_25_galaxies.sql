SELECT TOP 5 f.*
FROM sedm.calibrated_frame AS f
WHERE f.instrument_name = 'VIS'
  AND f.product_type = 'DpdVisCalibratedQuadFrame'
  AND f.release_name = 'Q1_R1'
  AND f.calibrated_frame_oid IN (1925, 1958, 1966, 1973, 2641)
ORDER BY f.calibrated_frame_oid
