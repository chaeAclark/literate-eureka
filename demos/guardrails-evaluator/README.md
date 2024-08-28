
# Building a Guardrails Evaluator for AI Models with Amazon Bedrock and Streamlit

In this blog post, we'll explore how to build a Guardrails Evaluator application using Amazon Bedrock and Streamlit. This tool allows users to evaluate AI model outputs against predefined guardrails, ensuring the generated content adheres to specific guidelines or constraints. We'll walk through the key components of the application, providing code examples and explanations to help you implement a similar solution.

## Background

As AI models become more powerful and widely used, it's crucial to ensure their outputs align with ethical standards, brand guidelines, or specific use-case requirements. Amazon Bedrock provides a set of guardrails that can be applied to model outputs, helping to filter or modify content based on predefined rules. Our application leverages these guardrails and provides an interactive interface for testing and evaluating them.

## Key Components

1. Configuration and Initialization
2. Sidebar for User Parameters
3. Guardrail Application
4. Chat Interface
5. Batch Evaluation
6. Results Visualization

Let's dive into each component and see how they work together to create our Guardrails Evaluator.

### 1. Configuration and Initialization

We start by loading configuration data from a JSON file and initializing our session state. This sets up the necessary variables and clients for interacting with Amazon Bedrock.

```python
def load_config(config_filepath):
    with open(config_filepath, "r") as config_file:
        config_data = json.load(config_file)
    
    region = config_data["region"]
    bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=region)
    
    return {
        "models_text": config_data["models_text"],
        "guardrails": config_data["guardrails"],
        "bedrock": bedrock_client,
    }

def initialize_session(config_filepath):
    st.session_state["config"] = load_config(config_filepath)
    st.session_state["prompt"] = ['', '']
    st.session_state["history_1"] = []
    st.session_state["history_2"] = []
    st.session_state["cost"] = [0.0, 0.0]
    st.session_state["tokens_in"] = [0, 0]
    st.session_state["tokens_out"] = [0, 0]
    st.session_state["results"] = []
```

This setup allows us to easily manage different models and guardrails, as well as keep track of conversation history and token usage.

### 2. Sidebar for User Parameters

The sidebar provides users with options to customize their experience, including selecting guardrails, choosing a model, and setting generation parameters.

```python
def sidebar(config):
    st.sidebar.header("User Parameters")
    with st.sidebar.expander("**Guardrails Selection**"):
        guardrail_selections = st.multiselect("Guardrails", [c['name'] for c in config["guardrails"]])
    
    with st.sidebar.expander("**Model Selection**"):
        model_text = st.selectbox("Models", [c['name'] for c in config["models_text"]])
        system_prompt = st.text_area("System Prompt", value="", height=100)
        max_len_text = st.number_input("Max Generation Length", 1000, 5000, 2500, 500)
        temperature = st.slider("Temperature", 0.01, 1.0, 0.01, 0.01)
    
    config.update({
        "system": system_prompt,
        "model_text": next(c for c in config["models_text"] if c['name'] == model_text),
        "max_len_text": max_len_text,
        "temp_text": temperature,
        "guardrail_selections": [c for c in config["guardrails"] if c['name'] in guardrail_selections]
    })
    
    return config
```

This function creates an interactive sidebar where users can select which guardrails to apply, choose a model, and set parameters like maximum token length and temperature.

### 3. Guardrail Application

The core functionality of our application is applying guardrails to user inputs or model outputs. This is handled by the `apply_guardrail` function:

```python
def apply_guardrail(payload, source='INPUT'):
    bedrock_client = payload['bedrock']
    guardrail_selections = payload['guardrail_selections']

    messages = [{"text": {"text": msg}} for msg in payload['prompt']]

    responses = []
    total_latency = 0.0
    for guardrail in guardrail_selections:
        start_time = time.time()
        response = bedrock_client.apply_guardrail(
            guardrailIdentifier=guardrail['guardrailIdentifier'],
            guardrailVersion=guardrail['guardrailVersion'],
            source=source,
            content=messages,
        )
        end_time = time.time()
        total_latency += (end_time - start_time)
        
        if response['action'] == 'NONE':
            if guardrail['complement_text']:
                responses.append(guardrail['complement_text'])
        elif not guardrail['complement_text']:
            responses.append(response['outputs'][0]['text'])

    return responses, total_latency
```

This function applies each selected guardrail to the input content, measuring the latency and collecting responses. If a guardrail triggers (i.e., the content violates the guardrail), it either returns a predefined message or blocks the content.

### 4. Chat Interface

The chat interface allows users to interact with the AI model while seeing the effects of the applied guardrails in real-time. Here's how we handle user queries:

```python
def process_query(payload):
    payload['prompt'] = st.session_state["prompt"]
    responses, latency_1 = apply_guardrail(payload)
    
    if not responses:
        payload['history'] = st.session_state["history_1"]
        text, tokens_in, tokens_out, latency_2 = query_endpoint(payload)
        update_chat_history("history_1", text, latency_1 + latency_2/1000, payload["model"]["name"])
    else:
        text = responses[0]
        update_chat_history("history_1", text, latency_1, payload["model"]["name"])

    payload['history'] = st.session_state["history_2"]
    text, tokens_in, tokens_out, latency = query_endpoint(payload)
    update_chat_history("history_2", text, latency/1000, payload["model"]["name"])
```

This function first applies the guardrails to the user's input. If the input passes all guardrails, it's sent to the AI model for a response. The function then updates two separate chat histories: one showing the effects of the guardrails, and another showing the unfiltered model responses.

### 5. Batch Evaluation

For evaluating larger datasets, we provide a batch evaluation feature:

```python
def process_uploaded_file(file, config):
    separator = '\t' if file.name.endswith('.tsv') else ','
    df = pd.read_csv(file, sep=separator, header=None)
    df.columns = ['sentence'] + [f'col_{i}' for i in range(1, len(df.columns))]
    
    results = []
    for sentence in df['sentence']:
        payload = {
            "bedrock": config["bedrock"],
            "prompt": [sentence],
            "guardrail_selections": config["guardrail_selections"],
        }
        responses, _ = apply_guardrail(payload)
        passed = len(responses) == 0
        results.append({"sentence": sentence, "passed": passed})
    
    return pd.DataFrame(results)
```

This function processes an uploaded CSV or TSV file, applying the selected guardrails to each sentence and recording whether it passed or was blocked.

### 6. Results Visualization

Finally, we visualize the results of our batch evaluation:

```python
def display_results(results_df):
    passed_count = results_df['passed'].sum()
    total_count = len(results_df)
    completion_percentage = (passed_count / total_count) * 100
    
    st.subheader(f"Guardrails Evaluation Results: {completion_percentage:.2f}%")
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(results_df)
    with col2:
        fig, ax = plt.subplots()
        ax.pie([passed_count, total_count - passed_count], 
               labels=['Passed', 'Blocked'], 
               autopct='%1.1f%%',
               colors=['#66b3ff', '#ff9999'])
        ax.set_title("Guardrails Evaluation Results")
        st.pyplot(fig)
```

This function creates a summary of the evaluation results, displaying both a detailed dataframe and a pie chart for quick visual understanding.

## Putting It All Together

The `main` function ties all these components together:

```python
def main(config):
    st.title("Bedrock Guardrails")
    st.subheader("Evaluate your use-case")
    
    with st.expander("**Active Guardrails**"):
        display_active_guardrails(config["guardrail_selections"])

    payload = create_payload(config)

    with st.expander("**Batch Evaluate Guardrails**"):
        handle_batch_evaluation(config)

    with st.expander("**Chat with your Guardrails**"):
        handle_chat_interface(payload)
```

This creates a structured layout with expandable sections for displaying active guardrails, batch evaluation, and the chat interface.

## Conclusion

This Guardrails Evaluator application provides a powerful tool for testing and validating AI model outputs against predefined guardrails. By leveraging Amazon Bedrock and Streamlit, we've created an interactive and user-friendly interface that allows for both real-time chat evaluation and batch processing of larger datasets.

To implement this solution, you'll need:

1. An Amazon Web Services (AWS) account with access to Amazon Bedrock
2. Python and the required libraries (boto3, streamlit, pandas, matplotlib)
3. A configuration JSON file with your model and guardrail details

Remember to handle your AWS credentials securely and never expose them in your code or version control systems.

By understanding and implementing each component we've discussed, you can create a similar application tailored to your specific use case, helping ensure that your AI model outputs align with your guidelines and requirements.
