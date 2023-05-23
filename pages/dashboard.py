import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Document Intelligence App",
    page_icon="modzy_badge_v4.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Streamlit App Configuration
# link to css file
with open('css/style.css') as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

st.markdown("# NLP Analysis Dashboard ")
st.sidebar.markdown("### NLP Analysis Dashboard")

tab1, tab2 = st.tabs(["Summary", "NER Analysis"])
tab1.markdown("## High Level Document Analysis")
tab1.write("This tab provides qualitative outputs from three NLP models: (1) Language Identification, (2) Text Summarization, and (3) Text Topic Model")


# Extract NLP Model Results   
if 'l_id' in st.session_state:
    lang = st.session_state['l_id']
if 'summ' in st.session_state:
    text_summary = st.session_state['summ']
if 'tps' in st.session_state:
    topics = st.session_state['tps']
if 'entities' in st.session_state:
    entities = st.session_state['entities']
    entity_df = pd.DataFrame(entities, columns=['entity', 'category'])
    cat_counts = entity_df['category'].value_counts().to_frame()
    cat_counts.reset_index(inplace=True)
    cat_counts_filtered = cat_counts[1:]



# Display results on dashboard page
if 'l_id' in st.session_state and 'summ' in st.session_state and 'tps' in st.session_state and 'entities' in st.session_state:
    # tab 1
    tab1.markdown("### Language")
    tab1.write(lang)
    tab1.markdown("### Summary")
    tab1.write(text_summary)
    tab1.markdown("### Top Topics")
    tab1.write(topics)

    # tab 2
    tab2.bar_chart(cat_counts_filtered, x='category', y='count', use_container_width=True)
    