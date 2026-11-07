import base64
from dataclasses import asdict
import re
import zlib

import pandas as pd
import plotly.graph_objects as go

from simulation import Settings,ACCOUNT_NAMES
from pdf_report import build_pdf_report


def streams(pdf):
    blocks=[]
    for block in re.findall(rb'stream\r?\n(.*?)endstream',pdf,re.S):
        try:
            blocks.append(zlib.decompress(base64.a85decode(block.strip(),adobe=True)).decode('latin1'))
        except (ValueError,zlib.error):
            pass
    return '\n'.join(blocks)


def test_pdf_has_saved_parameters_then_two_vector_charts():
    requested=Settings(years=3,starting_balance=500000,withdrawal=70000)
    effective=asdict(requested); effective['sipp_income_target']=50270
    accounts=[20000,30000,200000,50000,100000,100000]
    result=dict(settings=effective,inputs={'settings':asdict(requested),'accounts':accounts,
                'gains':[1234,5678],'model_revision':'1234567890abcdef'},
                source=None,base=pd.DataFrame([dict(zip(ACCOUNT_NAMES,accounts))]))
    portfolio=go.Figure()
    portfolio.add_trace(go.Scatter(x=[0,1,2,3],y=[500000,480000,470000,450000],
        name='Our model: fixed y, no crash',line=dict(color='#d47724')))
    portfolio.add_trace(go.Scatter(x=[0,1,2,3],y=[500000,460000,420000,400000],
        name='Evelyn S1: original chart (approx.)',line=dict(color='#0072b2',dash='dash')))
    portfolio.update_layout(yaxis_title='Portfolio (£, nominal)')
    income=go.Figure()
    income.add_trace(go.Scatter(x=[1,2,3],y=[40000,30000,-1000],name='10th percentile',line_color='#8cbba4'))
    income.add_trace(go.Scatter(x=[1,2,3],y=[50000,40000,30000],name='90th percentile',
        fill='tonexty',fillcolor='rgba(36,107,71,0.14)',line_color='#8cbba4'))
    income.update_layout(yaxis_title='Net annual income (£, valuation-date purchasing power)')
    before=portfolio.to_json()
    pdf=build_pdf_report(result,portfolio,income,real=False)
    assert pdf.startswith(b'%PDF-')
    assert re.search(rb'/Count\s+2\b',pdf)
    text=streams(pdf)
    for value in ['Pension simulation report','Starting portfolio','500,000','70,000',
                  'Auto:','50,270','Opening accounts and GIA gain assumptions','1,234','5,678',
                  'Portfolio projection','Net annual income after tax','Evelyn S1','nominal',
                  'Ann bank payment while eligible','Ann gross SIPP contribution','2,880','3,600']:
        assert value in text
    assert '[5 3]' in text  # dashed Evelyn reference remains dashed in PDF
    assert len(re.findall(r'BT.*?Portfolio projection',text,re.S)) > 0
    assert result['settings']['sipp_income_target'] == 50270
    assert result['inputs']['settings']['sipp_income_target'] is None
    assert portfolio.to_json() == before


def test_zero_and_one_point_income_forecasts_export_without_axis_errors():
    settings=asdict(Settings(years=1,starting_balance=0))
    result={'settings':settings,'inputs':{'accounts':[0]*6,'gains':[0,0]},'source':None}
    portfolio=go.Figure(go.Scatter(x=[0,1],y=[0,0],name='Forecast'))
    income=go.Figure(go.Scatter(x=[1],y=[0],name='Net annual income after tax'))
    pdf=build_pdf_report(result,portfolio,income)
    assert pdf.startswith(b'%PDF-') and re.search(rb'/Count\s+2\b',pdf)
