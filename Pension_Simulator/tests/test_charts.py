import pandas as pd
import plotly.graph_objects as go
from charts import add_percentile_bands


def rgb(value):
    return tuple(int(value[k:k+2],16) for k in (1,3,5))


def test_percentile_bands_are_red_below_green_above_and_lighten_outward():
    q=pd.DataFrame({f'p{n}':[n,n+1] for n in range(10,100,10)})
    fig=add_percentile_bands(go.Figure(),[1,2],q)
    assert len(fig.data) == 10
    assert [t.fill for t in fig.data[1:9]] == ['tonexty']*8
    for trace in fig.data[1:5]:
        r,g,b=rgb(trace.fillcolor); assert r > g
    for trace in fig.data[5:9]:
        r,g,b=rgb(trace.fillcolor); assert g > r
    assert sum(rgb(fig.data[1].fillcolor)) > sum(rgb(fig.data[4].fillcolor))
    assert sum(rgb(fig.data[8].fillcolor)) > sum(rgb(fig.data[5].fillcolor))
    assert fig.data[-1].showlegend is False
    assert list(fig.data[-1].y) == [50,51]
