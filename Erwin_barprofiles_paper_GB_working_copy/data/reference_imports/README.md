# Parent disc sample reference import

`parent_disc_sample_export.txt` preserves the root file previously named
` + $tempTsv + r`, byte for byte. Its introductory comments identify an Erwin
2018 parent-disc sample and list the source catalogues and measurement fields.
It also contains a parsed-table marker, so it is labelled as an imported/exported
reference artifact rather than adopted as the canonical input catalogue.

The creating command has not been identified. No maintained code referenced its
old literal filename. Programs such as `build_s4g_geometry_manifest.py` use the
separate canonical `data/s4gbars_table.dat`; that file was not replaced.
