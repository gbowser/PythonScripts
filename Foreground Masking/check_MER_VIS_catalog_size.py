import requests,csv
for r in csv.DictReader(open('MER_VIS_explanation_work/files.csv')):
 if 'FINAL-CAT_TILE' in r['file_name']:
  h=requests.head('https://eas.esac.esa.int/sas-dd/data',params={'RETRIEVAL_TYPE':'FILE','FILE_NAME':r['file_name'],'RELEASE':'sedm'},timeout=90);print(r['file_name'],h.status_code,h.headers.get('Content-Length'))
