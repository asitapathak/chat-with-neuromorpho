"""Automatic chart selection and styling."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PALETTE = ["#7C9CFF", "#5EEAD4", "#F0ABFC", "#FCD34D", "#FDA4AF", "#86EFAC"]
COUNT_NAMES = {"n", "count", "count_star()", "neurons"}
px.defaults.color_discrete_sequence = PALETTE


def style_fig(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13, color="#C9D1E3"),
        colorway=PALETTE, margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.12)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.12)")
    return fig


def split_columns(df):
    cat = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not c.lower().endswith("_id")]
    count = [c for c in num if c.lower() in COUNT_NAMES or c.lower().startswith("n_")]
    values = [c for c in num if c not in count]
    if not values:
        values, count = count, []
    return cat, values, count


def drop_id_like(df):
    keep = []
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            keep.append(c)
        elif c.lower().startswith("neuron") or c.lower().endswith(("_id", "_name")):
            continue
        else:
            keep.append(c)
    return df[keep]


def _build(df, title):
    cat, values, count = split_columns(df)
    if not values:
        return None
    n_col = count[0] if count else None
    if n_col is not None and df[n_col].min() < 20:
        title = (title + "  " if title else "") + "⚠ some groups have fewer than 20 neurons"

    is_raw = (n_col is None and len(df) > 30
              and not any(df[c].nunique() == len(df) for c in cat))
    if is_raw:
        color = next((c for c in cat if 1 < df[c].nunique() <= 8), None)
        if len(values) >= 2:
            skewed = lambda c: df[c].max() / max(df[c].median(), 1e-9) > 20
            return px.scatter(df, x=values[0], y=values[1], color=color, opacity=0.7,
                              log_x=bool(skewed(values[0])), log_y=bool(skewed(values[1])), title=title)
        return px.histogram(df, x=values[0], color=color, title=title)

    if len(cat) == 1:
        d = df.sort_values(values[0], ascending=False).head(25)
        horiz = len(d) > 8
        cols = values[:4]
        fig = make_subplots(rows=1, cols=len(cols), subplot_titles=cols)
        label_ax, value_ax = ("y", "x") if horiz else ("x", "y")
        for i, v in enumerate(cols, start=1):
            hover = "%{" + label_ax + "}<br>" + v + ": %{" + value_ax + ":,.1f}"
            if n_col:
                hover += "<br>n: %{customdata}"
            fig.add_trace(go.Bar(
                x=d[v] if horiz else d[cat[0]],
                y=d[cat[0]] if horiz else d[v],
                orientation="h" if horiz else "v",
                customdata=d[n_col] if n_col else None,
                hovertemplate=hover + "<extra></extra>",
                showlegend=False), row=1, col=i)
        if horiz:
            fig.update_yaxes(autorange="reversed")
        fig.update_layout(title=title, height=max(420, 28 * len(d) + 150) if horiz else 420)
        return fig

    if len(cat) == 2:
        long = df.melt(id_vars=cat + count, value_vars=values[:2],
                       var_name="measure", value_name="value")
        fig = px.bar(long, x=cat[0], y="value", color=cat[1], facet_col="measure",
                     barmode="group", hover_data=count or None, title=title)
        fig.update_yaxes(matches=None, showticklabels=True)
        return fig
    return None


def make_chart(df, title=""):
    if df is None or len(df) < 2:
        return None
    fig = _build(drop_id_like(df), title)
    return style_fig(fig) if fig is not None else None
    #charts
