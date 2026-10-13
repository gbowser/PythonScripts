SELECT TOP 5 f.*
FROM sedm.calibrated_frame AS f
WHERE f.instrument_name = 'VIS'
  AND f.product_type = 'DpdVisCalibratedQuadFrame'
  AND f.fov IS NOT NULL
  AND (
    INTERSECTS(CIRCLE('ICRS', 48.383317699421, -25.725106667731, 0.020860718419), f.fov) = 1
    OR INTERSECTS(CIRCLE('ICRS', 55.904507036012, -35.853040000998, 0.012527695048), f.fov) = 1
    OR INTERSECTS(CIRCLE('ICRS', 60.975574432291, -43.348724161104, 0.059527282745), f.fov) = 1
  )
ORDER BY f.observation_id, f.start_time_mjd, f.calibrated_frame_oid
