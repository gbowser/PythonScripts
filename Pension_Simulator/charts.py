"""Shared percentile styling for portfolio and household-income projections."""
import plotly.graph_objects as go

# Each fill belongs to the interval ending at its percentile. Lower bands
# are pink/red, upper bands green, with increasing lightness towards P10/P90.
BAND_COLORS={20:'#fce8ec',30:'#f5ccd4',40:'#e8a5b3',50:'#d77f95',
             60:'#79bc96',70:'#a5d1b8',80:'#cce5d6',90:'#e9f5ed'}
LINE_COLORS={10:'#ebbdc6',20:'#e6acb9',30:'#db91a3',40:'#cb748c',
             50:'#263d47',60:'#589c74',70:'#88ba9c',80:'#aed3bd',90:'#cee6d7'}


def add_percentile_bands(figure,years,quantiles):
    for percentile in range(10,100,10):
        figure.add_trace(go.Scatter(x=years,y=quantiles[f'p{percentile}'],mode='lines',
            name='Median (50th percentile)' if percentile == 50 else f'{percentile}th percentile',
            fill='tonexty' if percentile > 10 else None,
            fillcolor=BAND_COLORS.get(percentile),
            line=dict(color=LINE_COLORS[percentile],width=3 if percentile == 50 else .7),
            hovertemplate=f'Year %{{x}} · P{percentile}: £%{{y:,.0f}}<extra></extra>'))
    # Paint the median on top of the fills, without duplicating its legend/hover.
    figure.add_trace(go.Scatter(x=years,y=quantiles['p50'],mode='lines',name='Median',
        line=dict(color=LINE_COLORS[50],width=3),showlegend=False,hoverinfo='skip'))
    return figure
