import requests,json
T='https://eas.esac.esa.int/tap-server/tap/sync'
qs={'products':"SELECT * FROM sedm.mosaic_product WHERE tile_index=102023983 AND release_name='Q1_R1'",'tables':"SELECT table_name,description FROM TAP_SCHEMA.tables WHERE table_name LIKE '%detect%' OR table_name LIKE '%catalog%'"}
for name,q in qs.items():
 r=requests.post(T,data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':q},timeout=120);open('MER_VIS_explanation_work/'+name+'.csv','w',encoding='utf8').write(r.text);print(name,r.status_code,r.text[:10000])
f='EUC_MER_BGSUB-MOSAIC-VIS_TILE102023983-8D3C9A_20241018T181958.121344Z_00.00.fits'
r=requests.head('https://eas.esac.esa.int/sas-dd/data',params={'RETRIEVAL_TYPE':'FILE','FILE_NAME':f,'RELEASE':'sedm'},timeout=120,allow_redirects=True);print('HEAD',r.status_code,dict(r.headers),r.url)
