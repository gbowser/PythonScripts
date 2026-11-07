"""Streamlit Results Manager window."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from results_store import list_runs, load_run, delete_runs, paired_deltas
from charts import add_percentile_bands


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
    table = pd.DataFrame(rows)
    displayed=table.drop(columns=['id','Size_KB'])
    displayed['Saved']=pd.to_datetime(displayed['Saved'],utc=True).dt.tz_convert('Europe/London').dt.strftime('%d %b %y %H:%M')
    selection = st.dataframe(displayed.style.format({'Gift':'£{:,.0f}', 'Mean_y':'{:.2%}', 'Std_dev':'{:.2%}'},na_rep='—'),
                             column_config={
                                 'Name':st.column_config.TextColumn('Scenario',width='medium'),
                                 'Saved':st.column_config.TextColumn('Saved',width='small'),
                                 'Gift':st.column_config.NumberColumn('Gift (£)',width='small'),
                                 'Gift_years':st.column_config.NumberColumn('Gift years',width='small',format='%d'),
                                 'Mean_y':st.column_config.NumberColumn('Mean y',width='small',help='Base-case growth above CPI; also the annual stochastic mean.'),
                                 'Std_dev':st.column_config.NumberColumn('Std dev',width='small',help='Annual standard deviation of y.'),
                                 'Shock':st.column_config.CheckboxColumn('Shock',width='small'),
                                 'Property_sale':st.column_config.CheckboxColumn('Sell property',width='small')},
                             hide_index=True, height=350,row_height=30,
                             on_select='rerun', selection_mode='multi-row', key='saved_run_list')
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
