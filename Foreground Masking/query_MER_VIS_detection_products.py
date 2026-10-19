import requests
T='https://eas.esac.esa.int/tap-server/tap/sync'
for name,q in [('mer_products',"SELECT * FROM sedm.mer_final_catalogue WHERE tile_index=102023983"),('schema',"SELECT column_name,description FROM TAP_SCHEMA.columns WHERE table_name='sedm.mer_final_catalogue'"),('alltables',"SELECT table_name FROM TAP_SCHEMA.tables WHERE schema_name='sedm'")]:
 r=requests.post(T,data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':q},timeout=100);open('MER_VIS_explanation_work/'+name+'.csv','w').write(r.text);print(name,r.text[:9500])
