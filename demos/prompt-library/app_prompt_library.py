import re
import json
import time
import boto3
import string
import random
import numpy as np
import streamlit as st

from botocore.config import Config
st.set_page_config(layout="wide", page_title="Prompt Playground")


def initialize_session(filepath):
    """Initializes session state variables for chat history, context, and cost."""
    st.session_state['config'] = get_config(filepath)
    st.session_state["prompt"] = ""
    st.session_state['prompt_id'] = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
    st.session_state['name'] = ""
    st.session_state['description'] = ""
    st.session_state['modality'] = []
    st.session_state['category'] = []
    st.session_state["variables"] = []
    st.session_state['test_payloads'] = [None, None, None]
    st.session_state['test_responses'] = [{}, {}, {}]
    return 0


def get_config(filepath):
    """Loads configuration data from a JSON file including model endpoints, vector database indexes, AWS region, etc."""
    config = json.load(open(filepath, 'r'))
    region = config['region']
    diagram = config['arch_diagram']
    
    models_text = config['models_text']
    datastore = config['datastores']['local']
    categories = config['categories']
    modality = config['modality']
    
    bedrock = boto3.client(service_name='bedrock-runtime', region_name=region, config=Config(read_timeout=240))
    config = {
        'models_text': models_text,
        'region': region,
        'datastore': datastore,
        'bedrock': bedrock,
        'diagram': diagram,
        'modality': modality,
        'categories': categories
    }
    return config


def query_endpoint(payload):
    client = payload['client']
    model = payload['model']
    history = payload['history']
    system = payload['system']
    
    if 'claude-3' in model['endpoint']:
        if 'message' in model['style']:
            messages = []
            for msg in history:
                messages += [{'role': 'user', 'content': [{'type': 'text', 'text': msg['prompt']}]}]
                messages += [{'role': 'assistant', 'content': [{'type': 'text', 'text': msg['response']}]}]
            for i, msg in enumerate(payload['prompt']):
                if i%2 == 0:
                    messages += [{'role': 'user', 'content': [{'type': 'text', 'text': msg}]}]
                else:
                    messages += [{'role': 'assistant', 'content': [{'type': 'text', 'text': msg}]}]
            body = json.dumps({
                "messages": messages,
                'system': system,
                "anthropic_version": model['version'],
                "max_tokens": payload['max_len'],
                "temperature": payload['temp'],
                "top_p": payload['top_p']
                })
            print(messages)
            response, attempts, time_total = call_bedrock(client, body, model['endpoint'])
            try:
                response_body = json.loads(response.get("body").read()).get("content")[0]['text']
            except:
                response_body = '**Failed to generate!**'
    elif 'llama3' in model['endpoint']:
        if len(system) > 0:
            system = f'<|start_header_id|>system<|end_header_id|>\n{system}<|eot_id|>\n'
        prompt = f'<|begin_of_text|>{system}'
        for msg in history:
            prompt += f'<|start_header_id|>user<|end_header_id|>\n{msg["prompt"]}<|eot_id|>\n'
            prompt += f'<|start_header_id|>assistant<|end_header_id|>\n{msg["response"]}<|eot_id|>\n'
        for i, msg in enumerate(payload['prompt']):
            if i%2 == 0:
                prompt += f'<|start_header_id|>user<|end_header_id|>\n{msg}<|eot_id|>\n'
            elif (i%2 == 1) and (i < len(payload['prompt'])-1):
                prompt += f'<|start_header_id|>assistant<|end_header_id|>\n{msg}<|eot_id|>\n'
            else:
                prompt += f'<|start_header_id|>assistant<|end_header_id|>\n{msg}'
        if len(payload['prompt'])%2 == 1:
            prompt += f'<|start_header_id|>assistant<|end_header_id|>\n'
        body = json.dumps({
            "prompt": prompt,
            "max_gen_len": int(min([payload['max_len'], 2048])),
            "temperature": payload['temp'],
            'top_p':payload['top_p']
        })
        print(prompt)
        response, attempts, time_total = call_bedrock(client, body, model['endpoint'])
        try:
            response_body = json.loads(response.get('body').read().decode('utf-8'))['generation']
        except Exception as e:
            print(e)
            response_body = '**Failed to generate!**'
    elif 'mistral' in model['endpoint']:
        if len(system) > 0:
            system = f'<<SYS>>{system}<</SYS>>'
        prompt = f'<s>[INST]{system}'
        for msg in history:
            prompt += f'{msg["prompt"]}[/INST]'
            prompt += f'{msg["response"]}</s><s>[INST]'
        for i, msg in enumerate(payload['prompt']):
            if i%2 == 0:
                prompt += f'{msg}[/INST]'
            elif (i%2 == 1) and (i < len(payload['prompt'])-1):
                prompt += f'{msg}</s><s>[INST]'
            else:
                prompt += f'{msg}'
        body = json.dumps({
            "prompt": prompt,
            "max_tokens": payload['max_len'],
            "temperature": payload['temp'],
            'top_p': payload['top_p']
        })
        print(prompt)
        response, attempts, time_total = call_bedrock(client, body, model['endpoint'])
        try:
            response_body = json.loads(response.get('body').read().decode('utf-8'))['outputs'][0]['text']
        except Exception as e:
            print(e)
            response_body = '**Failed to generate!**'
    tokens = {'tokens_in': response.get('ResponseMetadata').get('HTTPHeaders').get('x-amzn-bedrock-input-token-count'), 'tokens_out':response.get('ResponseMetadata').get('HTTPHeaders').get('x-amzn-bedrock-output-token-count')}
    latency = response.get('ResponseMetadata').get('HTTPHeaders').get('x-amzn-bedrock-invocation-latency')
    return (response_body, attempts, time_total, tokens, latency)


def call_bedrock(client, body, endpoint, attempts=5, accept='application/json', contentType='application/json'):
    for i in range(attempts):
        try:
            tic = time.time()
            response = client.invoke_model(
                body=body,
                modelId=endpoint,
                accept=accept,
                contentType=contentType
            )
            toc = time.time()
            return response, i+1, toc-tic
        except Exception as e:
            print(e)
            time.sleep(2 + np.random.rand()/2.)
            continue
    return None, i+1, 0.


def test_prompt(text):
    def format_json(data):
        prompt = []
        max_length = max(len(data["user"]), len(data["assistant"]))
        for i in range(max_length):
            if i < len(data["user"]):
                prompt.append(data["user"][i])
            if i < len(data["assistant"]):
                prompt.append(data["assistant"][i])
        output_json = {
            "system": data["system"],
            "prompt": prompt
        }
        return output_json
    
    for idx, payload in enumerate(st.session_state['test_payloads']):
        text = fill_variables(text)
        json_prompt = prompt_to_json(text)
        json_prompt = format_json(json_prompt)
        payload['prompt'] = json_prompt['prompt']
        payload['system'] = json_prompt['system']
        (response_body, attempts, time_total, tokens, latency) = query_endpoint(payload)
        #st.write(response_body)
        st.session_state['test_responses'][idx] = {'response':response_body, 'latency':latency, 'tokens':tokens}


def fill_variables(text):
    for var in st.session_state['variables']:
        text = text.replace('{{'+var['var']+'}}', var['var_ex'])
    return text


def save_prompt():
    prompt_data = {
        "prompt_id": st.session_state['prompt_id'],
        "prompt_name": st.session_state['name'],
        "prompt_text": st.session_state["prompt"],
        "prompt_formatted": prompt_to_json(st.session_state["prompt"]),
        "description": st.session_state['description'],
        "modality": st.session_state['modality'],
        "category": st.session_state['category'],
        "variables": st.session_state["variables"],
        "test_results": st.session_state['test_responses']
    }
    json_data = json.dumps(prompt_data, indent=4)
    return json_data

@st.cache_data
def set_metadata(name, description, modality, category):
    st.session_state['name'] = name 
    st.session_state['description'] = description
    st.session_state['modality'] = modality
    st.session_state['category'] = category


@st.cache_data
def set_payload(_client, model, max_len, temp, loc):
    payload = {
        'prompt':'',
        'history':[],
        'system': '',
        'max_len':max_len,
        'temp':temp,
        'top_p':.9,
        'model':model,
        'client':_client
    }
    st.session_state['test_payloads'][loc-1] = payload


@st.cache_data
def prompt_to_json(prompt):
    system_text = re.search(r'<<system>>(.*?)(<<|$)', prompt, re.DOTALL)
    system_text = system_text.group(1).strip() if system_text else ""

    user_texts = re.findall(r'<<user>>(.*?)(<<|$)', prompt, re.DOTALL)
    user_texts = [t.strip() for t, _ in user_texts]

    assistant_texts = re.findall(r'<<assistant>>(.*?)(<<|$)', prompt, re.DOTALL)
    assistant_texts = [t.strip() for t, _ in assistant_texts]

    if not user_texts and not system_text and not assistant_texts:
        user_texts = [prompt.strip()]

    json_data = {
        "system": system_text,
        "user": user_texts,
        "assistant": assistant_texts
    }
    return json_data


@st.cache_data
def set_prompt(prompt):
    st.session_state["prompt"] = prompt


def set_variables(variables):
    st.session_state["variables"] = variables


def main(config=None):
    st.title("Prompt Developer")
    st.subheader("Build your prompt library for production")
    
    with st.expander("Application Information"):
        tab1,tab2 = st.tabs(["Architecture", "Intructions"])
        with tab1:
            st.header("Architecture")
        with tab2:
            st.header("Instructions")
    
    with st.container(border=True):
        col1,col2 = st.columns(2)
        with col1:
            prompt = st.text_area("Prompt Draft", value="", height=400)
            set_prompt(prompt)
            btn1,btn2,btn3 = st.columns(3)
            with btn1:
                if st.button("Test Prompt"):
                    test_prompt(st.session_state["prompt"])
            with btn2:
                if st.download_button("Save Prompt", save_prompt(), file_name='prompt_'+st.session_state['prompt_id']+'.json'):
                    pass
            with btn3:
                if st.button("New Prompt"):
                    st.session_state['prompt_id'] = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
        
        with col2:
            st.write(f"**Prompt ID:** {st.session_state['prompt_id']}")
            name = st.text_input("Prompt Name", "")
            description = st.text_area("Description", value="", height=25)
            modality = st.multiselect("Modality", config['modality'])
            category = st.multiselect("Category", config['categories'])
            set_metadata(name, description, modality, category)
    
    with st.container(border=True):
        variables = list(set(list(re.findall('{{\s*([^}]+)\s*}}', st.session_state["prompt"]))))
        var_store = []
        
        if len(variables) > 0:
            num_cols = min(3, len(variables))
            cols = st.columns(num_cols)
            col_idx = 0
            for i, var in enumerate(variables):
                with cols[col_idx]:
                    st.write(f"**{var}**")
                    var_desc = st.text_input("Variable Description", "", key=(var + "1"))
                    var_ex = st.text_input("Test Example", "", key=(var + "2"))
                    st.write("---")
                    var_store.append({"var": var, "var_desc": var_desc, "var_ex": var_ex})
                col_idx = (col_idx + 1) % num_cols
            set_variables(var_store)

            if len(variables) > 9:
                st.warning("Only the first 9 variables are displayed due to space constraints.")
    
    with st.container(border=True):
        col1,col2,col3 = st.columns(3)
        with col1:
            model_text = st.selectbox('Model', [m['name'] for m in config['models_text']], key='col11')
            max_len_text = st.number_input('Max Generation Length', 100, 10000, 300, 100, key='col12') 
            temp_text = st.slider('Temperature', 0.01, 1., 0.01, .01, key='col13')
            set_payload(config['bedrock'], [m for m in config['models_text'] if m['name'] == model_text][0], max_len_text, temp_text, 1)
            msg = st.session_state['test_responses'][0]
            if len(msg) > 0:
                st.write('**Latency:** ' + str(int(msg['latency'])/1000) + 's')
                st.write('**Tokens in:** ' + str(msg['tokens']['tokens_in']))
                st.write('**Tokens out:** ' + str(msg['tokens']['tokens_out']))
                st.write(msg['response'])
        with col2:
            model_text = st.selectbox('Model', [m['name'] for m in config['models_text']], key='col21')
            max_len_text = st.number_input('Max Generation Length', 100, 10000, 300, 100, key='col22') 
            temp_text = st.slider('Temperature', 0.01, 1., 0.01, .01, key='col23')
            set_payload(config['bedrock'], [m for m in config['models_text'] if m['name'] == model_text][0], max_len_text, temp_text, 2)
            msg = st.session_state['test_responses'][1]
            if len(msg) > 0:
                st.write('**Latency:** ' + str(int(msg['latency'])/1000) + 's')
                st.write('**Tokens in:** ' + str(msg['tokens']['tokens_in']))
                st.write('**Tokens out:** ' + str(msg['tokens']['tokens_out']))
                st.write(msg['response'])
        with col3:
            model_text = st.selectbox('Model', [m['name'] for m in config['models_text']], key='col31')
            max_len_text = st.number_input('Max Generation Length', 100, 10000, 300, 100, key='col32') 
            temp_text = st.slider('Temperature', 0.01, 1., 0.01, .01, key='col33')
            set_payload(config['bedrock'], [m for m in config['models_text'] if m['name'] == model_text][0], max_len_text, temp_text, 3)
            msg = st.session_state['test_responses'][2]
            if len(msg) > 0:
                st.write('**Latency:** ' + str(int(msg['latency'])/1000) + 's')
                st.write('**Tokens in:** ' + str(msg['tokens']['tokens_in']))
                st.write('**Tokens out:** ' + str(msg['tokens']['tokens_out']))
                st.write(msg['response'])


if __name__ == '__main__':
    FILEPATH = './config_prompt_library.json'
    if 'config' not in st.session_state:
        initialize_session(FILEPATH)
    #config = sidebar(st.session_state['config'])
    config = st.session_state['config']
    main(config)
