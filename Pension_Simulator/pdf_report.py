"""Two-page PDF export with saved-run parameters and native vector charts.

The renderer consumes the same Plotly figures shown by Streamlit. It does not
need Chrome, Kaleido, a network connection or raster screenshots.
"""
from datetime import datetime
from io import BytesIO
import math
import re
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

DARK=colors.HexColor('#243746')
MUTED=colors.HexColor('#596875')
PALE=colors.HexColor('#eef2f4')


def _text(c,x,y,text,size=8.5,color=DARK,font='Helvetica'):
    c.setFont(font,size); c.setFillColor(color); c.drawString(x,y,str(text))


def _wrap(c,text,x,y,width,size=8,leading=11):
    words=str(text).split(); line=''
    for word in words:
        candidate=(line+' '+word).strip()
        if line and c.stringWidth(candidate,'Helvetica',size)>width:
            _text(c,x,y,line,size); y-=leading; line=word
        else: line=candidate
    if line: _text(c,x,y,line,size); y-=leading
    return y


def _money(value,decimals=0):
    return f'£{float(value):,.{decimals}f}'


def _percent(value,decimals=2):
    return f'{float(value):.{decimals}%}'


def _date(value):
    return datetime.fromisoformat(value).strftime('%d %b %Y')


def _sections(settings,requested,real):
    s=settings
    on=lambda value: 'Yes' if value else 'No'
    mode='Non-stochastic' if s['non_stochastic'] else 'Stochastic'
    target=s.get('sipp_income_target')
    if s.get('withdrawal_strategy') == 'annual_tax': target_text='Not used'
    elif target is None: target_text='Automatic'
    elif target >= 1e12: target_text='Pension first'
    else: target_text=('Auto: ' if requested.get('sipp_income_target') is None else '')+_money(target)
    scenario=f"Evelyn S{s['evelyn_scenario']}" if s.get('evelyn_scenario') else 'Custom'
    left=[('Projection',[
        ('Scenario',scenario),('Mode',mode),('Valuation date',_date(s['start_date'])),
        ('Starting portfolio',_money(s['starting_balance'])),('Horizon',f"{s['years']} years"),
        ('Paths / random seed',f"{s['simulations']} / {s['seed']}"),
        ('Portfolio chart view','Real pounds' if real else 'Nominal pounds')]),
      ('Returns',[
        ('Fixed CPI',_percent(s['inflation'])),('Mean and first-year y',_percent(s['initial_y'],3)),
        ('Annual y standard deviation',_percent(s['std_y'],3)),('Reinvested yield',_percent(s['income_yield'])),
        ('Gordon GIA yield',_percent(s.get('gia_income_yield_gordon') if s.get('gia_income_yield_gordon') is not None else s['income_yield'])),
        ('Ann GIA yield',_percent(s.get('gia_income_yield_ann') if s.get('gia_income_yield_ann') is not None else s['income_yield'])),
        ('Additional annual fee',_percent(s.get('annual_fee',0)))]),
      ('Withdrawals and contributions',[
        ('Regular annual amount',_money(s['withdrawal'])+' real'),
        ('Monthly payment weights','11 x 1/15; then 4/15'),('Annual family gift',_money(s['gift'])),
        ('Gift duration',f"{s['gift_years']} years"),('Ann bank payment while eligible',_money(s['ann_pension_contribution'] if s.get('ann_contribution_is_net',False) else s['ann_pension_contribution']*.8)),
        ('Ann gross SIPP contribution',_money(s['ann_pension_contribution']/.8 if s.get('ann_contribution_is_net',False) else s['ann_pension_contribution'])),
        ('Stop when relief ends','Yes' if s.get('ann_contribution_requires_relief',False) else 'No'),
        ('Contribution funding','Portfolio' if s['ann_contribution_from_portfolio'] else 'External bank')]),
      ('Market crisis',[
        ('Include one-off crash',on(s['crash_enabled'])),('Crash loss',_percent(s['crash_loss'])),
        ('Random window',f"Years 1 to {min(s['crash_window'],s['years'])}"),
        ('Fixed stress-case year',str(s['deterministic_crash_year']))]),
      ('Rental property sale',[
        ('Enabled',on(s['property_sale_enabled'])),
        ('Trigger','Portfolio threshold' if s.get('property_sale_mode') == 'threshold' else 'Specified date'),
        ('Portfolio threshold',_money(s.get('property_sale_threshold',1000000))+' real'),
        ('Sale date','Path-dependent' if s.get('property_sale_mode') == 'threshold' else _date(s['property_sale_date'])),
        ('Nominal sale proceeds',_money(s['property_sale_amount']))])]
    right=[('Tax and withdrawal strategy',[
        ('Income tax and CGT enabled',on(s['taxes_enabled'])),
        ('Tax rules','Current law' if s.get('tax_rules') == 'current_law' else 'Legacy 2026/27'),
        ('Withdrawal policy','Estate-aware' if s.get('withdrawal_strategy') == 'estate' else 'Annual tax'),
        ('SIPP income target per owner',target_text),('Marginal IHT rate',_percent(s['iht_rate'])),
        ('Beneficiary income tax rate',_percent(s['beneficiary_income_tax_rate'])),
        ('Estate assessment year',str(s.get('estate_assessment_year') or s['years']))]),
      ('Pension tax-free cash',[
        ('Gordon tax-free share',_percent(s['gordon_tax_free_share'])),
        ('Gordon remaining LSA',_money(s['gordon_lsa_remaining'])),
        ('Ann tax-free share',_percent(s['ann_tax_free_share'])),
        ('Ann remaining LSA',_money(s['ann_lsa_remaining']))]),
      ('External income and pensions',[
        ('Gordon Citibank per year',_money(s['gordon_citibank_pension'],2)),
        ('Citibank annual increase','CPI' if s['gordon_citibank_growth'] is None else _percent(s['gordon_citibank_growth'])),
        ('Gordon bank interest',_money(s['gordon_interest'])),('Ann bank interest',_money(s['ann_interest'])),
        ('Ann rental profit',_money(s['ann_property'])),('Ann State Pension per year',_money(s['ann_state_pension'])),
        ('Gordon State Pension weekly',_money(s['gordon_state_weekly'],2)),
        ('Triple-lock earnings growth',_percent(s['earnings_growth']))]),
      ('GIA yield composition',[
        ('Gordon dividend share',_percent(s['dividend_share_gordon'])),
        ('Ann dividend share',_percent(s['dividend_share_ann']))])]
    return left,right


def _parameter_column(c,sections,x,y,width):
    for title,rows in sections:
        c.setFillColor(PALE); c.rect(x,y-4,width,17,stroke=0,fill=1)
        _text(c,x+5,y+1,title,9,font='Helvetica-Bold'); y-=19
        for label,value in rows:
            _text(c,x+3,y,label,8)
            c.setFont('Helvetica',8); c.setFillColor(DARK)
            c.drawRightString(x+width-3,y,str(value))
            y-=13
        y-=7
    return y


def _color(value):
    value=str(value or '#246b47')
    if value.startswith('rgb'):
        parts=re.findall(r'[\d.]+',value)
        return colors.Color(float(parts[0])/255,float(parts[1])/255,float(parts[2])/255,
                            alpha=float(parts[3]) if len(parts)>3 else 1)
    return colors.toColor(value)


def _ticks(low,high,count=5):
    span=high-low
    if span <= 0: span=max(1,abs(high)*.1)
    raw=span/count; power=10**math.floor(math.log10(raw))
    step=next((k*power for k in (1,2,2.5,5,10) if k*power >= raw),10*power)
    start=math.floor(low/step)*step; end=math.ceil(high/step)*step
    return [start+k*step for k in range(round((end-start)/step)+1)]


def _points(trace):
    return [(float(x),float(y)) for x,y in zip(trace.x,trace.y)
            if x is not None and y is not None and math.isfinite(float(x)) and math.isfinite(float(y))]


def _legend_name(name):
    if name.startswith('Evelyn S'):
        return name.split(':')[0]+' (approx.)'
    return {'Our model: fixed y, no crash':'Fixed y, no crash',
            'Median net annual income':'Median net income',
            'Net annual income after tax':'Net annual income'}.get(name,name)


def _chart(c,figure,title,x,y,width,height):
    traces=[(trace,_points(trace)) for trace in figure.data
            if trace.visible not in (False,'legendonly')]
    traces=[(t,p) for t,p in traces if p]
    _text(c,x,y+height-12,title,12,font='Helvetica-Bold')
    if not traces:
        _text(c,x+15,y+height/2,'No chart data. Run the simulation before exporting.'); return
    left,bottom=x+55,y+77
    pw,ph=width-69,height-111
    xmin=min(v[0] for _,p in traces for v in p); xmax=max(v[0] for _,p in traces for v in p)
    if xmin == xmax: xmin-=.5; xmax+=.5
    ymin=min(0,min(v[1] for _,p in traces for v in p)); ymax=max(0,max(v[1] for _,p in traces for v in p))
    yticks=_ticks(ymin,ymax if ymax>ymin else ymin+1000)
    ymin,ymax=yticks[0],yticks[-1]
    sx=lambda n:left+(n-xmin)/(xmax-xmin)*pw
    sy=lambda n:bottom+(n-ymin)/(ymax-ymin)*ph
    for value in yticks:
        c.setStrokeColor(colors.HexColor('#dfe5e8')); c.setLineWidth(.4)
        c.line(left,sy(value),left+pw,sy(value))
        c.setFont('Helvetica',7); c.setFillColor(MUTED)
        c.drawRightString(left-6,sy(value)-2,f'£{value:,.0f}')
    xticks=sorted(set([math.ceil(xmin),math.floor(xmax)]+[n for n in _ticks(xmin,xmax,7) if xmin<=n<=xmax and math.isclose(n,round(n))]))
    for value in xticks:
        c.setFont('Helvetica',7); c.setFillColor(MUTED)
        c.drawCentredString(sx(value),bottom-12,f'{value:g}')
    c.setStrokeColor(MUTED); c.setLineWidth(.5)
    c.line(left,bottom,left+pw,bottom); c.line(left,bottom,left,bottom+ph)
    _text(c,left+pw/2-49,bottom-25,'Years from valuation date',7.5,MUTED)
    label=str(figure.layout.yaxis.title.text or '')
    unit=('Net annual income (£ real)' if 'income' in label.lower() else
          'Portfolio (£ nominal)' if 'nominal' in label.lower() else 'Portfolio (£ real)')
    c.saveState(); c.translate(x+8,bottom+ph/2); c.rotate(90)
    c.setFont('Helvetica',8); c.setFillColor(MUTED); c.drawCentredString(0,0,unit); c.restoreState()
    previous=None
    for trace,points in traces:
        mapped=[(sx(px),sy(py)) for px,py in points]
        c.saveState()
        clip=c.beginPath(); clip.rect(left,bottom,pw,ph); c.clipPath(clip,stroke=0)
        if trace.fill == 'tonexty' and previous:
            fill=c.beginPath(); polygon=mapped+list(reversed(previous))
            fill.moveTo(*polygon[0])
            for point in polygon[1:]: fill.lineTo(*point)
            fill.close()
            shade=_color(trace.fillcolor or 'rgba(36,107,71,0.12)')
            c.setFillColor(shade); c.setFillAlpha(shade.alpha)
            c.drawPath(fill,stroke=0,fill=1); c.setFillAlpha(1)
        line=c.beginPath(); line.moveTo(*mapped[0])
        for point in mapped[1:]: line.lineTo(*point)
        c.setStrokeColor(_color(trace.line.color)); c.setLineWidth((trace.line.width or 1)*.7)
        dash=str(trace.line.dash or 'solid')
        if dash in ('dash','longdash'): c.setDash(5,3)
        elif dash == 'dot': c.setDash(1,2)
        else: c.setDash()
        c.drawPath(line,stroke=1,fill=0)
        if len(mapped)==1:
            c.setFillColor(_color(trace.line.color)); c.circle(*mapped[0],1.7,stroke=0,fill=1)
        c.restoreState(); previous=mapped
    # Compact legends keep all screen traces identifiable on paper.
    lx,ly=x+8,y+35
    for trace,_ in traces:
        if trace.showlegend is False: continue
        name=_legend_name(trace.name or '')
        needed=c.stringWidth(name,'Helvetica',7)+30
        if lx+needed>x+width-3: lx=x+8; ly-=12
        c.setStrokeColor(_color(trace.line.color)); c.setLineWidth(1.5)
        c.setDash(5,3) if trace.line.dash == 'dash' else c.setDash()
        c.line(lx,ly+2,lx+16,ly+2); c.setDash()
        _text(c,lx+21,ly,name,7); lx+=needed


def build_pdf_report(result,portfolio_figure,income_figure,*,real=True):
    """Return a complete PDF without changing saved inputs or simulation data."""
    output=BytesIO(); c=canvas.Canvas(output,pagesize=A4,pageCompression=1)
    c.setTitle('Pension Simulator - Parameters and projections')
    c.setAuthor('Pension Simulator')
    w,h=A4; margin=36; usable=w-2*margin
    s=result['settings']; inputs=result.get('inputs',{})
    requested=inputs.get('settings',s)
    _text(c,margin,h-43,'Pension simulation report',20,font='Helvetica-Bold')
    _text(c,margin,h-61,'Gordon and Ann Bowser | Saved simulation parameters',9,MUTED)
    now=datetime.now(ZoneInfo('Europe/London'))
    _text(c,margin,h-77,'Exported '+now.strftime('%d %b %Y %H:%M')+' London time',8,MUTED)
    left,right=_sections(s,requested,real)
    cw=(usable-18)/2
    ly=_parameter_column(c,left,margin,h-105,cw)
    ry=_parameter_column(c,right,margin+cw+18,h-105,cw)
    y=min(ly,ry)-12
    _text(c,margin,y,'Opening accounts and GIA gain assumptions',10,font='Helvetica-Bold'); y-=19
    c.setFillColor(PALE); c.rect(margin,y-4,usable,17,stroke=0,fill=1)
    _text(c,margin+5,y+1,'Account',8,font='Helvetica-Bold')
    _text(c,margin+210,y+1,'Opening balance',8,font='Helvetica-Bold')
    _text(c,margin+374,y+1,'GIA starting gain',8,font='Helvetica-Bold'); y-=16
    names=['Gordon GIA','Gordon ISA','Gordon SIPP','Ann GIA','Ann ISA','Ann SIPP']
    accounts=inputs.get('accounts',[]); gains=inputs.get('gains',[])
    for k,name in enumerate(names):
        value=accounts[k] if len(accounts)==6 else result['base'].iloc[0][name]
        _text(c,margin+5,y,name,8)
        _text(c,margin+210,y,_money(value),8)
        gain=gains[k//3] if k in (0,3) and len(gains)==2 else None
        _text(c,margin+374,y,_money(gain) if gain is not None else '-',8)
        y-=13
    source=result.get('source') or {}
    if source.get('workbook'):
        y=_wrap(c,'Source workbook: '+str(source['workbook']),margin,y-9,usable,7.2,10)
    _wrap(c,'Regular payments are inflated from Day 0. Tax is paid from bank receipts; no extra portfolio tax withdrawal. '
          'LSA and annual ISA limits are fixed nominal amounts.',margin,y-8,usable,7.2,10)
    revision=inputs.get('model_revision','')[:12]
    _text(c,margin,24,'Model '+revision if revision else 'Pension Simulator',7,MUTED)
    _text(c,w-margin-36,24,'1 of 2',7,MUTED)
    c.showPage()
    _chart(c,portfolio_figure,'Portfolio projection',margin,435,usable,365)
    _chart(c,income_figure,'Net annual income after tax',margin,70,usable,350)
    _wrap(c,'Net income includes regular portfolio receipts and external pensions, rent and interest, less full income tax and CGT. '
          'Real values use valuation-date purchasing power. Shaded ranges show annual simulated percentiles.',
          margin,55,usable,7.2,10)
    _text(c,w-margin-36,24,'2 of 2',7,MUTED)
    c.save(); return output.getvalue()
