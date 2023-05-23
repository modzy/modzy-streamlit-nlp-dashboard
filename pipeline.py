import os
import re
import time
import pandas as pd
from modzy import ApiClient
from pdf2image import convert_from_path
import streamlit as st


st.set_page_config(
    page_title="Document Intelligence App",
    page_icon="imgs/modzy_badge_v4.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Streamlit App Configuration

# link to css file
with open('css/style.css') as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)
st.markdown("# Document Intelligence Pipeline")
st.sidebar.markdown("### Document Intelligence Pipeline")
st.text(" ")
col1, col2 = st.columns(2, gap='large')

# Modzy Model Data Collection & Transformation
MODZY_URL = os.getenv('MODZY_URL')
MODZY_API_KEY = os.getenv('MODZY_API_KEY')

client = ApiClient(base_url=MODZY_URL, api_key=MODZY_API_KEY)

#dependencies
models = {
    "OCR": { # OCR
        'id':'c60c8dbd79',
    },
    "names": { # Name Entities
        'id':'a92fc413b5',
        'version':'0.0.12'
    },
    "summarize": { # Modzy Text Summarization
        'id':'rs2qqwbjwb',
    },
    "topics": { # Text Topic Modeling
        'id':'m8z2mwe3pt',
    },
    "sentiment": { # Sentiment Analysis
        'id': 'g0h96fgwjq'
    },
    "language": { # Language Identification
        'id': '6d1c49595f'
    }
}

for model in models:
    model_info = client.models.get(models[model]['id'])
    if models[model].get('version', None) == None: #let set a version explicitly above
        models[model]['version'] = model_info.latestActiveVersion
    models[model]['name'] = model_info.name
    models[model]['link'] = f"{MODZY_URL}/models/{models[model]['id']}/{models[model]['version']}/overview"

models_df = pd.DataFrame(models).T
models_df = models_df.iloc[:, [2,1,0,3]]
models_df.reset_index(inplace=True)
models_df = models_df.rename(columns={'index': "Model", 'name': "Name", "version": "Version", "id": "Identifier", "link": "Model Page"})

uploaded_file = col1.file_uploader("Choose a file", label_visibility='collapsed')
    
col1.markdown("## NLP Models")
col1.dataframe(models_df)


# Process Uploaded Data File for NLP Pipeline
if uploaded_file:
    source_pdf = str(uploaded_file.name)
    # images = convert_from_path(source_pdf) # Linux or Mac OS    
    images = convert_from_path(source_pdf, poppler_path = r"<path-to-poppler-bin-file>") # Switch bin path if on Windows 

    # save image files 
    image_files = []
    doc_name = source_pdf.split('/')[-1]
    doc_name = doc_name.split('.')[0]
    for image in images:
        img_path = 'data/converted/'+doc_name+'_page'+ str(images.index(image)) +'.jpg'
        with open(img_path, "w", encoding="utf-8") as out:
            image.save(img_path, 'JPEG')
        image_files.append('data/converted/'+doc_name+'_page'+ str(images.index(image)) +'.jpg')

    input_filename = image_files[0]
    input_config = 'data/config.json'

    # create input source for OCR
    inputs = {}
    for page in image_files:
        inputs['page'+ str(image_files.index(page))] = {
            'input':  page,
            'config.json':input_config
        }


# Define Functions required for NLP Pipeline
def run_ocr(models, inputs):
    # submit ocr job
    col2.markdown(":arrow_right: Running OCR Model ...")
    try:
        ocr_job = client.jobs.submit_file(models['OCR']['id'], models['OCR']['version'], inputs)
        time.sleep(0.5)
        # print(MODZY_URL + 'operations/jobs/' + ocr_job['jobIdentifier'])    
        ocr_result = client.results.block_until_complete(ocr_job)
        col2.success("OCR Job Complete!")
    except Exception as e:
        col2.error("Error with OCR Job:\n{}\nView job page for more information:\n{}".format(e, MODZY_URL + '/operations/jobs/' + ocr_job['jobIdentifier']))
        
    # postprocses data
    sorted_results = []
    for result in ocr_result["results"]:
        sorted_results.append(result)
    sorted_results.sort()

    full_text = ""
    text_results = {}
    for result in sorted_results:
        text = ocr_result["results"][result]["results.json"]['text']
        n_text = re.sub('(?<![\r\n])(\r?\n|\n?\r)(?![\r\n])', ' ', text) #remove single line endings from OCR    
        text_results[result] = {'input.txt': n_text}
        full_text += text +"\n\n\n"
    return text_results, full_text

def run_language_id(full_text):
    # language id
    col2.markdown(":arrow_right: Running Language ID Model ...")
    try:
        lang_id_job = client.jobs.submit_text(models['language']['id'], models['language']['version'], {'input.txt': full_text})
        time.sleep(0.5)
        # print(MODZY_URL + 'operations/jobs/' + lang_id_job['jobIdentifier'])
        lang_id_result = client.results.block_until_complete(lang_id_job)['results']['job']['results.json']['data']['result']['classPredictions'][0]['class']   
        col2.success("Language ID Job Complete!")
    except Exception as e:
        col2.error("Error with Language ID Job:\n{}\nView job page for more information:\n{}".format(e, MODZY_URL + '/operations/jobs/' + lang_id_job['jobIdentifier']))

    return lang_id_result

def run_text_summary(full_text):
    # text summary
    col2.markdown(":arrow_right: Running Text Summary Model ...")
    try:
        text_summ_job = client.jobs.submit_text(models['summarize']['id'], models['summarize']['version'], {'input.txt': full_text})
        time.sleep(0.5)
        # print(MODZY_URL + 'operations/jobs/' + text_summ_job['jobIdentifier'])
        text_summ_result = client.results.block_until_complete(text_summ_job, timeout=None)
        summary = text_summ_result['results']['job']['results.json']["summary"]
        col2.success("Text Summary Job Complete!")
    except Exception as e:
        col2.error("Error with Text Summary Job:\n{}\nView job page for more information:\n{}".format(e, MODZY_URL + '/operations/jobs/' + text_summ_job['jobIdentifier']))
        
    return summary

def run_topics(full_text):
    # text topic modeling
    col2.markdown(":arrow_right: Running Topic Model ...")
    try:
        topic_job = client.jobs.submit_text(models['topics']['id'], models['topics']['version'], {'input.txt': full_text})
        time.sleep(0.5)
        # print(MODZY_URL + 'operations/jobs/' + topic_job['jobIdentifier'])
        topics_result = client.results.block_until_complete(topic_job, timeout=None)
        topics = topics_result['results']['job']['results.json']
        col2.success("Text Topic Job Complete!")
    except Exception as e:
        col2.error("Error with Text Topic Modeling Job:\n{}\nView job page for more information:\n{}".format(e, MODZY_URL + '/operations/jobs/' + topic_job['jobIdentifier']))
    
    return topics    

def run_ner(text_results):
    # NER
    col2.markdown(":arrow_right: Running NER Model ...")
    try:
        ner_job = client.jobs.submit_text(models['names']['id'], models['names']['version'], text_results)
        time.sleep(0.5)
        ner_result = client.results.block_until_complete(ner_job, timeout=600)
        # time.sleep(8)
        # ner_result = client.results.get("6d335851-5cdc-454f-8137-dfa46f11e31f") # for testing purposes
        all_entities = []
        for result in ner_result['results']:
            entities = ner_result['results'][result]['results.json']
            all_entities.extend(entity for entity in entities)
        col2.success("NER Job Complete!")
    except Exception as e:
        col2.error("Error with NER Job:\n{}\nView job page for more information:\n{}".format(e, MODZY_URL + '/operations/jobs/' + ner_job['jobIdentifier']))
        print(e.with_traceback())
    
    return all_entities


# Kick off Pipeline based on button activity
if col2.button("Start Analysis", use_container_width=True):
    txt_results, full_text = run_ocr(models, inputs)
    l_id = run_language_id(full_text)
    if 'l_id' not in st.session_state:
        st.session_state['l_id'] = l_id
    else:
        st.session_state['l_id'] = l_id    
    summ = run_text_summary(full_text)
    if 'summ' not in st.session_state:
        st.session_state['summ'] = summ
    else:
        st.session_state['summ'] = summ    
    tps = run_topics(full_text)
    if 'tps' not in st.session_state:        
        st.session_state['tps'] = tps
    else:
        st.session_state['tps'] = tps        
    entities = run_ner(txt_results)
    if 'entities' not in st.session_state:    
        st.session_state['entities'] = entities
    else:
        st.session_state['entities'] = entities          

