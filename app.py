"""Chat with NeuroMorpho: Streamlit front end."""
import inspect

import plotly.express as px
import streamlit as st

from src.charts import make_chart, style_fig
from src.engine import ROOT, Engine, RateLimited

st.set_page_config(page_title="Chat with NeuroMorpho", page_icon="🧠", layout="wide")
st.markdown(f"<style>{(ROOT / 'assets' / 'style.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)


def stretch(fn):
    """Full-width keyword that works on older and newer Streamlit versions."""
    if "width" in inspect.signature(fn).parameters:
        return {"width": "stretch"}
    return {"use_container_width": True}


@st.cache_resource(show_spinner="Loading the database and reference notes…")
def get_engine():
    return Engine()


@st.cache_data(show_spinner=False)
def get_overview():
    return get_engine().overview()


def hero(eyebrow, title, sub):
    st.markdown(f'<div class="hero"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{sub}</p></div>',
                unsafe_allow_html=True)


def card(title, text):
    return f'<div class="card"><h4>{title}</h4><p>{text}</p></div>'


def safe_chart(df):
    try:
        return make_chart(df)
    except Exception:
        return None


# ------------------------------------------------------------------ Chat
MAX_QUESTIONS = 20

STARTERS = [
    ("Compare", "Compare the median total length of human and mouse neurons in the neocortex."),
    ("Overview", "Show the top 10 species by number of neurons."),
    ("Understand", "What does fractal dimension tell me about a neuron?"),
    ("Relationship", "Show the relationship between total length and branch count for human neurons."),
]


def render_assistant(m, idx):
    st.markdown(m["answer"].replace("$", "\\$"))
    if m.get("fig") is not None:
        st.plotly_chart(m["fig"], key=f"chart_{idx}", **stretch(st.plotly_chart))
    if m.get("sql") or m.get("df") is not None or m.get("notes"):
        with st.expander("SQL, data and sources"):
            if m.get("sql"):
                st.code(m["sql"], language="sql")
            if m.get("df") is not None:
                st.dataframe(m["df"].head(200), hide_index=True)
            if m.get("notes"):
                st.caption("Reference notes used: " + " · ".join(dict.fromkeys(m["notes"])))


def chat_page():
    engine = get_engine()
    t = get_overview()["totals"]
    hero("NEUROMORPHO.ORG  ·  NATURAL-LANGUAGE EXPLORER", "Ask the neurons anything.",
         f"Plain-English questions over {t['neurons']:,} reconstructed cells across {t['species']} species. "
         "Every answer comes with its chart, the SQL and the sources behind it.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    typed = st.chat_input("Ask about neuron shapes, species or brain regions…")
    question = typed or st.session_state.pop("pending", None)

    if not st.session_state.messages and not question:
        cols = st.columns(len(STARTERS), gap="medium")
        for i, (col, (label, text)) in enumerate(zip(cols, STARTERS)):
            col.markdown(f'<div class="card-eyebrow">{label}</div>', unsafe_allow_html=True)
            if col.button(text, key=f"starter_{i}", **stretch(st.button)):
                st.session_state.pending = text
                st.rerun()
        st.caption("Each question is answered on its own, so follow-ups don't remember earlier ones.")

    for i, m in enumerate(st.session_state.messages):
        if m["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(m["content"])
        else:
            with st.chat_message("assistant", avatar="🧠"):
                render_assistant(m, i)

    if question and st.session_state.get('asked', 0) >= MAX_QUESTIONS:
        st.warning(f'This public demo allows {MAX_QUESTIONS} questions per session to protect a free API quota. Reload the page to start a new session.')
        question = None

    if question:
        st.session_state.asked = st.session_state.get('asked', 0) + 1
        idx = len(st.session_state.messages) + 1
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user", avatar="👤"):
            st.markdown(question)
        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Querying the data and reading the notes…"):
                try:
                    out = engine.ask(question)
                    msg = {"role": "assistant", "answer": out["answer"], "sql": out["sql"],
                           "df": out["df"], "notes": out["notes"], "fig": safe_chart(out["df"])}
                except RateLimited:
                    msg = {"role": "assistant",
                           "answer": "The free Gemini tier is rate-limited right now. Please wait a minute and ask again."}
                except Exception as e:
                    msg = {"role": "assistant", "answer": f"Something went wrong: {str(e)[:200]}"}
            render_assistant(msg, idx)
        st.session_state.messages.append(msg)

    if st.session_state.messages:
        if st.button("Clear conversation", key="clear"):
            st.session_state.messages = []
            st.rerun()
        st.caption("AI-generated answers can be wrong: check the SQL and data under each answer. Questions are sent to Google's Gemini API, so please do not enter personal information.")


# --------------------------------------------------------------- Dataset
def dataset_page():
    ov = get_overview()
    t = ov["totals"]
    hero("DATASET", "What the assistant can see",
         "A snapshot of the reconstructions in this project and, just as importantly, what is not in it.")
    cols = st.columns(4, gap="medium")
    cols[0].metric("Reconstructions", f"{t['neurons']:,}")
    cols[1].metric("Species", t["species"])
    cols[2].metric("Brain regions", t["regions"])
    cols[3].metric("Contributing archives", t["archives"])
    st.write("")

    tab1, tab2, tab3 = st.tabs(["Species", "Composition", "Read before comparing"])

    with tab1:
        left, right = st.columns([3, 2], gap="large")
        with left:
            search = st.text_input("Filter species", placeholder="Filter species, e.g. mouse",
                                   label_visibility="collapsed")
            sp = ov["species"]
            if search:
                sp = sp[sp["species"].str.contains(search, case=False, na=False)]
            st.dataframe(sp, hide_index=True, height=430, column_config={
                "species": "Species",
                "neurons": st.column_config.ProgressColumn(
                    "Reconstructions", min_value=0, max_value=int(ov["species"]["neurons"].max()), format="%d"),
                "dendrites_only": st.column_config.NumberColumn("Dendrite-only", format="%d"),
                "regions": st.column_config.NumberColumn("Regions", format="%d"),
            })
        with right:
            missing = ov["missing"]
            if missing is None:
                st.info("Add data/knowledge/all_species.json (Part A) to see which NeuroMorpho species are missing.")
            else:
                st.markdown(card(f"{len(missing)} species not included",
                                 "Most failed to download because the API rejected multi-word species names; "
                                 "a few had no usable measurements. The assistant knows nothing about them."),
                            unsafe_allow_html=True)
                with st.expander("Show the list"):
                    st.write(", ".join(missing))

    with tab2:
        a, b = st.columns(2, gap="large")
        with a:
            st.markdown("##### Most represented species")
            fig = px.bar(ov["species"].head(12), x="neurons", y="species", orientation="h")
            fig.update_yaxes(autorange="reversed", title=None)
            fig.update_xaxes(title=None)
            fig.update_layout(height=380, showlegend=False)
            st.plotly_chart(style_fig(fig), key="comp_species", **stretch(st.plotly_chart))
        with b:
            st.markdown("##### What was traced")
            fig = px.pie(ov["trace"], names="trace_type", values="neurons", hole=0.62)
            fig.update_traces(textinfo="percent", sort=False)
            fig.update_layout(height=380)
            st.plotly_chart(style_fig(fig), key="comp_trace", **stretch(st.plotly_chart))
        st.markdown("##### Most represented brain regions")
        fig = px.bar(ov["regions"], x="brain_region", y="neurons")
        fig.update_xaxes(title=None)
        fig.update_yaxes(title=None)
        fig.update_layout(height=340)
        st.plotly_chart(style_fig(fig), key="comp_regions", **stretch(st.plotly_chart))

    with tab3:
        tr = ov["trace"].set_index("trace_type")["neurons"]
        pct = lambda k: 100 * tr.get(k, 0) / tr.sum()
        n_missing = f"{len(ov['missing'])} NeuroMorpho species" if ov["missing"] is not None else "Some NeuroMorpho species"
        items = [
            ("Not a random sample", "Reconstructions come from many labs. Species, regions and cell types are unevenly represented, so groups with few neurons give unreliable averages."),
            ("What was traced differs", f"{pct('with axon'):.0f}% include an axon and {pct('undifferentiated'):.0f}% are labelled only as processes or neurites. Size comparisons in the app default to dendrite-only reconstructions."),
            ("Means can mislead", "A few very large reconstructions inflate averages, so the assistant leads with medians for size measures."),
            ("Not only neurons", "The cell type field also includes glia. Unless a question filters cell type, results describe all reconstructed cells."),
            ("Some species are missing", f"{n_missing} are not in this project's table, mostly small ones. See the Species tab."),
            ("Descriptive, not causal", "Differences between groups reflect biology and lab methods together. They do not show that a species or region causes a morphology difference."),
        ]
        for row in [items[i:i + 2] for i in range(0, len(items), 2)]:
            for col, (title, text) in zip(st.columns(2, gap="medium"), row):
                col.markdown(card(title, text), unsafe_allow_html=True)


# ----------------------------------------------------------------- About
FLOW = """digraph G {
  rankdir=LR; bgcolor="transparent"; nodesep=0.35; ranksep=0.45;
  node [shape=box, style="rounded,filled", fillcolor="#151B2C", color="#2A3350", fontcolor="#E6EAF2", fontname="Helvetica", fontsize=11, margin="0.18,0.10"];
  edge [color="#5B6B99", arrowsize=0.7];
  Q [label="Your question"];
  L [label="Gemini\\nfunction calling"];
  S [label="query_neurons\\nread-only SQL"];
  D [label="DuckDB\\nreconstructions"];
  N [label="lookup_biology\\nsemantic search"];
  C [label="ChromaDB\\nreference notes"];
  A [label="Answer, chart,\\nSQL and sources"];
  Q -> L; L -> S; S -> D; L -> N; N -> C; L -> A;
}"""
STACK = ["Python", "pandas", "DuckDB", "ChromaDB", "Gemini API", "Plotly", "Streamlit", "NeuroMorpho.Org API"]


def about_page():
    t = get_overview()["totals"]
    hero("ABOUT", "How this was built",
         "A portfolio project that puts a conversational layer on top of a public neuroscience archive.")
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("##### How a question is answered")
        st.graphviz_chart(FLOW)
        st.markdown(
            "1. The model reads your question and decides what it needs.\n"
            "2. For numbers, it writes read-only SQL that runs against the database. Only SELECT statements are accepted.\n"
            "3. For definitions and caveats, it searches a small library of reference notes.\n"
            "4. The answer comes back with an automatic chart, the SQL, the data and the notes used.")
        st.markdown("##### Design choices")
        st.markdown(
            "- The database is opened read-only.\n"
            "- Every average is shown with its sample size.\n"
            "- Medians lead for size measures, because a few huge reconstructions inflate means.\n"
            "- Size comparisons default to dendrite-only reconstructions, like with like.\n"
            "- Answers rest on query results and notes, not on the model's memory.")
    with right:
        st.markdown(card("Built by Asita",
                         "A master's student in data science and big data analytics with an applied research "
                         "interest in neuroscience and neuroimaging."), unsafe_allow_html=True)
        st.markdown(card("Data", f"{t['neurons']:,} reconstructions across {t['species']} species from the public "
                                  "NeuroMorpho.Org archive (CC BY 4.0, RRID:SCR_002145). Each reconstruction's original publication is listed in the source data; see the README for full credit. This is an independent demonstration project, not affiliated with NeuroMorpho.Org and not a peer-reviewed analysis."),
                    unsafe_allow_html=True)
        st.markdown("##### Built with")
        st.markdown("".join(f'<span class="pill">{s}</span>' for s in STACK), unsafe_allow_html=True)


# ------------------------------------------------------------------ Main
try:
    get_engine()
except Exception as e:
    st.error(f"Could not start the app: {e}")
    st.info("Check that GEMINI_API_KEY is in .env, that data/neuromorpho.duckdb exists, "
            "and that no notebook still has the database open.")
    st.stop()

pages = [
    st.Page(chat_page, title="Chat", icon="💬", url_path="chat", default=True),
    st.Page(dataset_page, title="Dataset", icon="📊", url_path="dataset"),
    st.Page(about_page, title="About", icon="🧬", url_path="about"),
]
try:
    nav = st.navigation(pages, position="top")
except TypeError:
    nav = st.navigation(pages)
nav.run()
#app.py
