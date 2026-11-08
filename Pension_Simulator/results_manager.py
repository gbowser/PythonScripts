"""Streamlit Results Manager window."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from results_store import list_runs, load_run, delete_runs, paired_deltas
from charts import add_percentile_bands


def compact_run_table(rows):
    """Expand lightweight metadata without opening compressed path results."""
    leading = [
        ('gift','Gift',88,'money'),('gift_years','Gift yrs',62,'integer'),
        ('initial_y','Mean y',65,'rate'),('std_y','Std dev',65,'rate'),
        ('inflation','CPI',60,'rate'),('withdrawal','Withdrawal',95,'money'),
        ('crash_enabled','Shock',55,'bool'),('crash_loss','Loss',60,'rate'),
        ('crash_window','Window',62,'integer'),('deterministic_crash_year','Shock yr',68,'integer'),
        ('property_sale_enabled','Sell',50,'bool'),('property_sale_mode','Sale trigger',88,'text'),
        ('property_sale_threshold','Sale level',100,'money'),('property_sale_amount','Sale price',100,'money'),
        ('property_sale_date','Sale date',95,'text'),('starting_balance','Start value',110,'money'),
        ('income_yield','Yield',60,'rate'),('annual_fee','Fee',60,'rate'),
        ('taxes_enabled','Tax',48,'bool'),('withdrawal_strategy','Strategy',80,'text')]
    used={item[0] for item in leading}
    excluded={'years','simulations'}  # Kept out of the list as requested; pairing still validates both.
    parameters=sorted({k for r in rows for k in r.get('Parameters',{})}-used-excluded)
    rates={'earnings_growth','gordon_citibank_growth','dividend_share_gordon','dividend_share_ann',
           'gordon_tax_free_share','ann_tax_free_share','iht_rate','beneficiary_income_tax_rate'}
    integers={'seed','evelyn_scenario','estate_assessment_year'}
    texts={'start_date','tax_rules'}
    booleans={'non_stochastic','ann_contribution_is_net','ann_contribution_requires_relief','ann_contribution_from_portfolio'}
    specs=leading+[(k,k.replace('_',' ').capitalize(),
                    70 if k in rates|integers|booleans else 115,
                    'rate' if k in rates else 'integer' if k in integers else
                    'bool' if k in booleans else 'text' if k in texts else 'money') for k in parameters]
    config={'Name':st.column_config.TextColumn('Scenario',width=310),
            'Saved':st.column_config.TextColumn('Saved',width=120)}
    formats={}
    data=[]
    for row in rows:
        item={'Name':row['Name'],'Saved':pd.Timestamp(row['Saved']).tz_convert('Europe/London').strftime('%d %b %H:%M')}
        item.update({key:row.get('Parameters',{}).get(key) for key,_,_,_ in specs})
        data.append(item)
    for key,label,width,kind in specs:
        help_text=key.replace('_',' ').capitalize()
        if kind=='bool':
            config[key]=st.column_config.CheckboxColumn(label,width=width,help=help_text)
        else:
            config[key]=st.column_config.Column(label,width=width,help=help_text)
            if kind=='money': formats[key]=lambda v:'Auto / CPI' if pd.isna(v) else ('Pension first' if v>=1e12 else f'£{v:,.0f}')
            elif kind=='rate': formats[key]=lambda v:'CPI / auto' if pd.isna(v) else f'{v:.2%}'
            elif kind=='integer': formats[key]=lambda v:'Auto' if pd.isna(v) else f'{v:.0f}'
    return pd.DataFrame(data),config,formats


def render_manager():
    st.title('Simulation Results Manager')
    st.link_button('Open simulation engine', '?', help='Opens the simulator in a new browser tab.')
    rows, errors = list_runs()
    for error in errors:
        st.warning('Could not read saved run: '+error)
    if not rows:
        st.info('No saved runs yet. Run a simulation, enter a name and select Save simulation run.')
        return
    st.caption('Select one row to restore it, or multiple rows to compare. Values are saved snapshots; no simulation is rerun.')
    st.caption(f"{len(rows)} saved runs")
    displayed,config,formats=compact_run_table(rows)
    st.caption('Scroll horizontally for additional inputs. Column headers describe the saved parameters; pairing settings are checked before plotting.')
    selection = st.dataframe(displayed.style.format(formats,na_rep='—'),
                             column_config=config,width='content',
                             hide_index=True,height=min(350,38+28*len(rows)),row_height=28,
                             on_select='rerun',selection_mode='multi-row',key='saved_run_list')
    indices = selection.selection.rows
    selected = [rows[i] for i in indices]
    if not selected:
        return
    ids = [r['id'] for r in selected]
    if st.button(f'Delete selected runs ({len(ids)})', type='secondary'):
        delete_runs(ids)
        st.rerun()
    if len(ids) == 1:
        st.link_button('Restore selected run in simulation engine', '?restore='+ids[0], type='primary')
        run = load_run(ids[0])
        st.json(run['result']['inputs'])
        return
    labels = {r['id']: r['Name'] for r in selected}
    baseline_id = st.selectbox('Main run / baseline', ids, format_func=labels.get)
    baseline = load_run(baseline_id)
    st.link_button('Restore baseline in simulation engine', '?restore='+baseline_id)
    st.caption('Each graph subtracts the main baseline portfolio from the comparison portfolio for each simulation and year, then calculates P10–P90 and the median of those paired differences. Green bands are above the median and pink/red below it, matching the main simulator. Positive values mean the comparison has more money than the baseline. Same seed, path count, horizon, mode, valuation date and model version are required. Changing return assumptions changes returns even with aligned random draws.')
    tables = []
    for run_id in ids:
        if run_id == baseline_id:
            continue
        run = load_run(run_id)
        comparison_title = run['name']+' - '+baseline['name']
        try:
            differences, delta_q = paired_deltas(baseline,run)
        except ValueError as error:
            st.warning(run['name']+': '+str(error)+' Rerun with matching pairing settings to compare these runs.')
            continue
        delta = go.Figure()
        add_percentile_bands(delta,delta_q.year,delta_q)
        delta.update_layout(title=dict(text=comparison_title,automargin=True),height=540,
            xaxis_title='Years from valuation date',yaxis_title='Portfolio difference (£ real)',
            yaxis_tickprefix='£',yaxis_tickformat=',.0f',yaxis_rangemode='tozero',
            hovermode='x unified',margin=dict(t=70,l=20,r=20,b=20),
            legend=dict(orientation='h'))
        # Differences may be negative; do not clamp the vertical axis to zero.
        delta.add_hline(y=0,line_color='grey',line_width=1)
        st.plotly_chart(delta,width='stretch',key='paired_delta_'+run_id)
        tables.append(delta_q.assign(Run=run['name'],Baseline=baseline['name']))
        changed=[]
        left,right=baseline['result']['inputs'],run['result']['inputs']
        for group in ['settings','accounts','gains','model_revision']:
            a,b=left.get(group),right.get(group)
            if isinstance(a,dict) and isinstance(b,dict):
                for key in sorted(a.keys()|b.keys()):
                    if a.get(key)!=b.get(key): changed.append({'Parameter':key,'Baseline':str(a.get(key)),'Comparison':str(b.get(key))})
            elif a!=b:
                changed.append({'Parameter':group,'Baseline':str(a),'Comparison':str(b)})
        with st.expander('Parameter differences: '+run['name']):
            st.dataframe(pd.DataFrame(changed),hide_index=True) if changed else st.write('Identical saved inputs.')
    if tables:
        combined=pd.concat(tables,ignore_index=True)
        st.dataframe(combined.style.format({c:'£{:,.0f}' for c in combined.columns if c not in ['year','Run','Baseline']}),hide_index=True)
        st.download_button('Comparison CSV',combined.to_csv(index=False),'simulation_comparison.csv','text/csv')
