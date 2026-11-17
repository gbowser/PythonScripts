# Create your MER VIS galaxy cutouts in ESA Datalabs

1. In the Datalabs application catalogue, search for Euclid and launch the Euclid Datalab. It opens JupyterLab. Menu labels may vary; choose the Euclid application with access to Q1, not an unrelated generic Python instance.
2. Check the file browser for the mounted Euclid Q1 volume. The prepared archive metadata points to /data/euclid_q1/Q1_R1. The official Euclid Datalab normally mounts Q1 automatically. If missing, use the data-collection controls to attach Q1 or consult the Euclid Helpdesk. Do not copy/download the full dataset.
3. In JupyterLab, navigate to the persistent personal workspace. ESA's tutorial uses /media/user. Create a folder called Euclid_MER_VIS. Do not put outputs in /tmp or the read-only source volume.
4. Upload MER_VIS_Datalabs_Cutouts.ipynb, make_MER_VIS_datalabs_cutouts.py and MER_VIS_datalabs_manifest.csv into that folder using the file browser upload button. All three files are provided alongside this guide. These are metadata and code, not images.
5. Open the notebook. Select the euclid-tools or EUCLID-TOOLS kernel, the Python environment supplied with the Euclid application. A notebook is a sequence of code/text cells; click a code cell and press Shift+Enter to run it and advance.
6. Run the first code cell. Check the printed notebook directory and OUTPUT location. Change WORK only if your persistent workspace mount differs from /media/user. It defaults to /media/user/Euclid_MER_VIS; cutouts go in its cutouts subfolder.
7. Run the source-path preflight cell. Expected: 2777 galaxies, 309 mosaics, zero missing mounted paths. Estimated science-only storage is about 23.4 GiB. Check your actual Datalabs user quota; filesystem free space is not the same as your personal quota.
8. If all paths are missing, confirm Q1 is mounted and inspect the official Cutouts tutorial for the current path. Do not run the batch until this is resolved. If mounts have moved, update datalabs_source_file in a copy of the manifest to the confirmed location; do not guess paths or change mosaic filenames.
9. Run the five-galaxy pilot cell. This reads hosted science mosaics and writes five galaxy-centred FITS files; it does not call the HTTP cutout links or download full mosaics. Objects retain the catalogue display size at native pixel scale.
10. Run the image display cell. Confirm that the red cross marks the target, surrounding light fits in the image and PARTIAL is understood. PARTIAL means the requested box exceeds the selected mosaic boundary; NaNs pad that area. It does not alone mean the galaxy is truncated.
11. Open cutouts/MER_VIS_processing_manifest.csv. Confirm five successful rows. Investigate any error before scaling up. The code retains celestial WCS and exact object IDs, and writes FITS checksums. Only science pixels are extracted; RMS, weight, quality and segmentation maps are not included.
12. To process all galaxies, remove the leading # from the full-batch cell so it reads mer.run(MANIFEST, OUTPUT, limit=None), then run that cell. Existing files are checked and skipped. It processes the 2777 targets sequentially, with checkpointing after each object.
13. Keep the Datalab instance running until completion. Closing a notebook view is different from shutting down the kernel or instance. If interrupted, reopen the notebook and rerun the configuration, helper import and full-batch cells. Valid existing cutouts are verified rather than recreated. Do not use Run All blindly before reviewing the configuration and full-batch cell.
14. Run the final report cell. Created plus existing_verified should account for 2777 targets; investigate error rows and inspect partial cutouts. The report records status, dimensions, finite-pixel fraction, errors and output paths.
15. Save the notebook with Ctrl+S. Confirm the files remain in your persistent workspace. You can reopen them for further analysis. If you need a few derived cutouts locally, use the file browser download action, following ESA policy; do not use Datalabs as a bulk export route for full Q1 products.

## What these outputs are

They are native observed-projection cutouts of already combined, background-subtracted Q1 MER VIS SCIENCE mosaics. They have not been rotated, deprojected or foreground-masked. Width is the morphology catalogue display width, not a measured bar size. Geometry fitting remains a subsequent analysis step.

The helper uses Astropy Cutout2D on mounted FITS mosaics. It rejects lookup-table WCS distortion, pads tile-boundary sections with NaN, and logs failures. The complete pipeline has not been executed in your ESA account. Synthetic central/edge cutouts, coordinate recovery, checksums and notebook syntax have been tested locally. Mounted path metadata was retrieved from public Euclid TAP on 16 October 2026.

## Official references

- Euclid Datalabs overview and environment: https://euclid.esac.esa.int/dr/q1/expsup/Ch17.S1.html
- Official Q1 cutout notebook: https://github.com/ESA-Datalabs/Euclid-Q1/blob/main/Notebooks/Cutouts.ipynb
- Datalabs persistent workspace information: https://datalabs.esa.int/web/
