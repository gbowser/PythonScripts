import requests
T='https://eas.esac.esa.int/tap-server/tap/sync'
qs=[('files',"SELECT * FROM sedm.files_table WHERE file_name LIKE '%102023983%'"),('aux_mosaics',"SELECT * FROM sedm.aux_mosaic WHERE tile_index=102023983"),('seg',"SELECT * FROM sedm.mer_segmentation_map WHERE tile_index=102023983")]
for name,q in qs:
 r=requests.post(T,data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':q},timeout=100);open('MER_VIS_explanation_work/'+name+'.csv','w').write(r.text);print(name,r.text[:18000])
