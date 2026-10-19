import requests
T='https://eas.esac.esa.int/tap-server/tap/sync'
qs=[('mer_products',"SELECT * FROM sedm.mer_final_catalogue WHERE file_name_list LIKE '%102023983%'"),('auxschema',"SELECT table_name,column_name FROM TAP_SCHEMA.columns WHERE table_name='sedm.aux_mosaic' OR table_name='sedm.files_table'"),('source',"SELECT object_id,right_ascension,declination,position_angle,ellipticity,semimajor_axis,segmentation_map_id FROM catalogue.mer_catalogue WHERE object_id=-619395065457031576")]
for name,q in qs:
 r=requests.post(T,data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':q},timeout=100);open('MER_VIS_explanation_work/'+name+'.csv','w').write(r.text);print(name,r.text[:11000])
