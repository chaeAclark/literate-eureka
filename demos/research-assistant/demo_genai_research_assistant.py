import os
import io
import re
import json
import time
import boto3
import threading
import numpy as np
import streamlit as st

from queue import Queue
from icecream import ic
from datetime import datetime
from botocore.config import Config
from concurrent.futures import ThreadPoolExecutor
st.set_page_config(layout="wide", page_title="Research Assistant")


def initialize_session(filepath):
    """Initializes session state variables for chat history, context, and cost."""
    st.session_state['config'] = get_config(filepath)
    st.session_state['papers'] = []
    st.session_state['dynamodb_scan'] = []
    st.session_state['papers_new'] = []
    st.session_state['papers_old'] = []
    st.session_state['papers_processed'] = []
    st.session_state['papers_new_selected'] = []
    st.session_state['papers_old_selected'] = []
    return 0

def get_about_me():
    return """This is a demo of an AI research assistant application built with Streamlit and deployed on AWS. The app allows users to upload or select PDF research papers, and will then use AWS services like Textract, Polly, and Bedrock to extract key information like the paper's title, authors, abstract summary, text transcript, and sample code implementations. The app shows how to build an end-to-end ML workflow from ingesting papers, running NLP models like Claude, and synthesizing audio podcast episodes using the generated summaries and code examples. Key features include extracting text from PDFs, querying large language models to analyze papers, converting text to speech with SSML tags, and storing output assets like text, audio, code in S3. The app aims to simplify discovering and summarizing the latest ML research in an engaging audio format."""


def get_arch_details():
    return """The application is built using Streamlit for the UI and AWS services for the ML workflow under the hood. The backend processing leverages AWS Textract to extract text from uploaded PDF papers. It then sends the extracted text as a prompt to Claude, a large language model API from Anthropic, to generate a paper summary, title, authors, and other metadata. The summary text is formatted with SSML tags optimized for text-to-speech using Amazon Polly, which converts the summary to an audio MP3. The application also generates sample code implementations using the Claude API. All the output text, audio, code assets are stored in an S3 bucket. Metadata about each paper is tracked in DynamoDB.

The workflow parallelizes extracting the paper summary, metadata, and code example using Threads. Managing Streamlit caching and sessions state allows fast iterations on the frontend without re-running expensive backend jobs. The application architecture demonstrates an end-to-end machine learning pipeline on AWS leveraging services like S3, DynamoDB, Textract, Polly, and SageMaker in a serverless fashion. Additional features like user upload, audio playback, code rendering are enabled by Streamlit."""


def get_app_details():
    return """This AI Research Digest app enables users to upload academic papers, automatically generate rich summaries, and synthesize audio podcast episodes.

For data ingestion, users can upload PDF papers from their local machine or specify an S3 bucket location. The application uses AWS Textract to extract the raw text from these PDFs. Both the original PDF and text are stored in designated S3 buckets for later retrieval.

Once extracted, the full paper text is sent as a prompt to Claude, a large language model API from Anthropic accessed via Amazon Bedrock. The app runs 3 concurrent threads to generate the paper summary, metadata, and sample code implementation from the text. The summary is formatted using SSML tags to optimize the text for text-to-speech synthesis.

Text-to-speech conversion leverages Amazon Polly. The marked up summary text is split into smaller paragraphs and sentences to avoid Polly service size limits. Synthesis requests are made in parallel using multiple threads. The resulting audio streams are concatenated to produce the final output audio file.

All generated assets including the raw text, marked up transcript, audio file, and code snippet are stored in S3 buckets for persistence. Paper metadata like title, authors, and year are tracked in a DynamoDB table that acts as an index.

The natural language prompts provided to Claude are designed to generate an appropriately formatted response. For example, the paper summary prompt explicitly asks for section headings like Introduction, Methods, and Results to improve structure. It also requests explanatory detail beyond the abstract to create an engaging audio narrative. The prompts are carefully tuned over multiple iterations to produce high quality output. As an illustration, the summary generation prompt is as follows:

<prompt> Read the following research article and write a detailed summary of the paper's findings including background, data, models/algorithms, method/proposed solution, results, and any novel conclusions:
Paper: <paper text>

From the above paper, write a summary of the article's findings including background, data, models/algorithms, method/proposed solution, results, and any novel conclusions in <summary> tags. Be verbose and explain the concepts well. Define any uncommon terms... </prompt>

By optimizing each step of the workflow - ingestion, summarization, synthesis, storage, and prompting - this app allows users to easily create AI-generated audio summaries from the latest academic papers."""


def get_config(filepath):
    """Loads configuration data from a JSON file including model endpoints, vector database indexes, AWS region, etc."""
    config = json.load(open(filepath, 'r'))
    region = config['region']
    diagram = config['arch_diagram']
    
    models_text = {d['name']: d['endpoint'] for d in config['models_text']}
    #models_image = {d['name']: d['endpoint'] for d in md['models_image']}
    #models_embed = {d['name']: d['endpoint'] for d in md['models_embed']}
    
    s3 = boto3.client(service_name='s3', region_name=region)
    bucket = config['datastores']['s3']['bucket']
    prefix = config['datastores']['s3']['prefix']
    pdfs = config['datastores']['s3']['pdfs']
    text = config['datastores']['s3']['text']
    transcripts = config['datastores']['s3']['transcripts']
    audio =  config['datastores']['s3']['audio']
    code =  config['datastores']['s3']['code']
    
    polly = boto3.client(service_name='polly', region_name=region)
    bedrock = boto3.client(service_name='bedrock-runtime', region_name=region, config=Config(read_timeout=240))
    textract = boto3.client(service_name='textract', region_name=region)
    dynamodb = boto3.resource(service_name='dynamodb', region_name=region).Table(config['dynamo_table'])
    config = {
        'models_text': models_text,
        'region': region,
        's3': s3,
        'bucket': bucket,
        'prefix': prefix,
        'pdfs': pdfs,
        'text': text,
        'audio': audio,
        'code': code,
        'transcripts':transcripts,
        'polly': polly,
        'bedrock': bedrock,
        'textract': textract,
        'dynamodb': dynamodb,
        'diagram': diagram,
    }
    return config


def get_model_tags(endpoint):
    """Determines the formatting for user vs. AI prompts based on the model endpoint."""
    if 'claude' in endpoint:
        human_tag = '\n\nHuman:'
        robot_tag = '\n\nAssistant:'
        split_tag = ''
    else:
        human_tag = '\n\n'
        robot_tag = ''
        split_tag = ''
    return human_tag, robot_tag, split_tag


def query_endpoint(client, endpoint, payload):
    """Calls the specified model endpoint on Amazon Bedrock with the given payload."""
    if 'claude' in endpoint:
        body = json.dumps({
            'prompt':payload['prompt'],
            'max_tokens_to_sample':payload['max_len'],
            'temperature':payload['temp'],
            'top_p':payload['top_p'],
        })
        response, attempts, gen_time = call_bedrock(client, body, endpoint)
        try:
            response_body = json.loads(response.get("body").read()).get("completion")
        except:
            response_body = '**Failed to generate!**'
    else:
        raise ValueError(f'You have selected a model endpoint that is not supported ({endpoint}).\nSupported endpoints: titan, claude, llama, cohere.')
    return (response_body, attempts, gen_time)


def call_bedrock(client, body, endpoint, attempts=12, accept='application/json', contentType='application/json'):
    """Makes requests to Bedrock with retries to invoke a model."""
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
            time.sleep(5 + np.random.rand()/2.)
            continue
    return None, i+1, 0.


@st.cache_data
def upload_file_to_s3(file, bucket_name, object_name=None):
    """
    Upload a file to an S3 bucket
    from: https://stackoverflow.com/questions/63965781/how-to-upload-files-to-aws-s3-bucket-using-streamlit
    """
    # If S3 object_name was not specified, use file name
    if object_name is None:
        object_name = file.name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_fileobj(file, bucket_name, object_name)
    except ClientError as e:
        st.error(f"Could not upload file to S3: {e}")
        return False
    st.success(f"Uploaded {file.name} to {bucket_name}/{object_name}.")
    return True


def load_mp3_from_s3(client, bucket, audio_path):
    obj = client.get_object(Bucket=bucket, Key=audio_path)
    audio_bytes = io.BytesIO(obj['Body'].read())
    return audio_bytes


def get_pdf_list(client, bucket, prefix):
    response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    pdfs = [x['Key'] for x in response['Contents'] if x['Key'].endswith('.pdf')]
    return pdfs

def extract_text(data):
    client = data['client']
    bucket = data['bucket']
    filepath = data['paper']
    response = client.start_document_text_detection(
        DocumentLocation={'S3Object': {'Bucket': bucket, 'Name': filepath}})
    job_id = response['JobId']
    
    text = client.get_document_text_detection(JobId=response['JobId'])
    i = 0
    while text['JobStatus'] != 'SUCCEEDED':
        time.sleep(1)
        i += 1
        text = client.get_document_text_detection(JobId=response['JobId'])
        if i >= 120:
            text = ''
            break
    
    if type(text) is dict:
        full_text = '\n'.join([t['Text'] for t in text['Blocks'] if t['BlockType']=='LINE'])
    else:
        full_text = ''
    while('NextToken' in text and text['NextToken'] != None):
        text = client.get_document_text_detection(JobId=response['JobId'], NextToken=text['NextToken'])
        if type(text) is dict:
            full_text = full_text + '\n'.join([t['Text'] for t in text['Blocks'] if t['BlockType']=='LINE'])
        else:
            full_text = full_text + ''
    return full_text


def polly_tag_examples():
    tags = """
Amazon Polly supports the following SSML tags:
1. Adding a Pause-<break>-Full availability
2. Emphasizing Words-<emphasis>-Not available
3. Specifying Another Language for Specific Words-<lang>-Full availability
4. Placing a Custom Tag in Your Text-<mark>-Full availability
5. Adding a Pause Between Paragraphs-<p>-Full availability
6. Using Phonetic Pronunciation-<phoneme>-Full availability
7. Controlling Volume, Speaking Rate, and Pitch-<prosody>-Partial availability
8. Setting a Maximum Duration for Synthesized Speech-<prosody amazon:max-duration>-Not available
9. Adding a Pause Between Sentences-<s>-Full availability
10. Controlling How Special Types of Words Are Spoken-<say-as>-Partial availability
11. Identifying SSML-Enhanced Text-<speak>-Full availability
12. Pronouncing Acronyms and Abbreviations-<sub>-Full availability
13. Improving Pronunciation by Specifying Parts of Speech-<w>-Full availability
14. Adding the Sound of Breathing-<amazon:auto-breaths>-Not available
15. Newscaster speaking style-<amazon:domain name="news">-Select neural voices only
16. Adding Dynamic Range Compression-<amazon:effect name="drc">-Full availability
17. Speaking Softly-<amazon:effect phonation="soft">-Not available
18. Controlling Timbre-<amazon:effect vocal-tract-length>-Not available
19. Whispering-<amazon: effect name="whispered">-Not available
"""
    return tags


def get_polly_tags():
    try:
        with open('amazon_polly_tags.txt', 'r') as fp:
            tags = fp.read()
    except:
        tags = polly_tag_examples()
    return tags


def get_paper_metadata(client, endpoint, payload, input_paper, q=None):
    human_tag = payload['human_tag']
    robot_tag = payload['robot_tag']
    split_tag = payload['split_tag']
    
    prompt_template_pre = 'You are an AI Researcher whose goal is the analyze articles and extact requested content.'
    prompt_template = """Read the following article and extract:
1. Title - the given or inferred title of the article\n2. Year - the given or inferred year of the article\n3. Authors - the authors of the article if present\n4. Categories - write the list of categories that would help readers understand the content of the paper
\n<article>INPUT_PAPER</article>\n
From the above article extract the title, year, author, and category information and write the results as a JSON (e.g. {"title":"...", "year":"...", "authors":["...", "...", ...], "categories":["...", "...", ...]})."""
    prompt_template_post = 'Sure. Here is the extracted infomration with the correct title, year, authors, and categories as a valid JSON:\n'
    prompt_template_end = '{"title":"'
    prompt = human_tag + prompt_template_pre + prompt_template + robot_tag + prompt_template_post + prompt_template_end
    prompt = prompt.replace('INPUT_PAPER', input_paper)
    
    payload['prompt'] = prompt
    response = query_endpoint(client, endpoint, payload)
    metadata = prompt_template_end + response[0].split('}')[0] + '}'
    metadata = json.loads(metadata)
    title            = metadata["title"]
    title_polly      = f'<p>The title of this paper is:</p> <p>{title}</p>'
    year             = metadata["year"]
    year_polly       = f'<p>This paper was relased in {year}.</p>'
    authors          = metadata["authors"]
    authors_polly    = f"<p>There are {len(authors)} authors of this paper, with the lead author being {authors[0]}.</p>"
    categories       = metadata["categories"]
    categories_polly = "<p>The most relevant categories for this paper are: </p><p>" + '</p>,<p> '.join(categories[:-1]) + '</p>' + ', and <p>' + categories[-1] + '</p>'
    if q is not None:
        q.put(('title', title, title_polly))
        q.put(('year', year, year_polly))
        q.put(('authors', authors, authors_polly))
        q.put(('categories', categories, categories_polly))
    return title, title_polly, year, year_polly, authors, authors_polly, categories, categories_polly


def get_summary_polly(client, endpoint, payload, input_summary):
    human_tag = payload['human_tag']
    robot_tag = payload['robot_tag']
    split_tag = payload['split_tag']
    
    prompt_template_pre = ''
    prompt_template = """The following paper summary will be passed to Amazon Polly to be turned into speech for podcast audio.
    Read and re-write the summary to be read by a speech to text service (e.g. "This paper focuses on...").
    Use the relevant Amazon Polly tags:\n\nINPUT_POLLY:<polly-tags>\n\nSummary:<summary>INPUT_SUMMARY<summary>
    \nFrom the above text, adapt the summary to be read by Amazon Polly speech to text service in <summary_polly></summary_polly> tags.
    For every section in the summary add any additional context that the listener needs to understand the goal and the results.
    Use Speech Synthesis Markup Language (SSML) where relevant.
    Be creative, this will be used to create a podcast, so also be verbose and specific.
    Don't use non-supported tags like <emphasis>."""
    prompt_template_post = '''Sure! Happy to help. I will convert the paper summary above into valid Amazon Polly text following these guidelines:
<guidelines>
1. Simplify language and define terms
- Avoid complex academic jargon and industry-specific terminology. Explain abbreviations/acronyms.
- Define technical terms in simple language on first use. For example, "Reinforcement learning (RL) is a type of machine learning that..."
2. Improve flow and structure
- Use clear section headings (Introduction, Methods, Results, Discussion) and topic sentences.
- Break up dense paragraphs into shorter 2-3 sentence chunks.
- Use transitional phrases to guide the listener between ideas.
3. Emphasize key points  
- Identify 3-5 main takeaways and highlight using bold font or bullet point lists.
- Rephrase main findings using strong declarative language and subject-verb sentence structure.
4. Add explanatory detail  
- Imagine you are explaining concepts to someone unfamiliar with the field. 
- Elaborate on the real-world significance of technical details. 
5. Use conversational language
- Refer directly to the listener using "we", "you", "us" phrases.
- Pose rhetorical questions to engage the listener.
6. Check for common TTS errors
- Read draft aloud, verify pronunciation of names/terms.
- Check for misplaced pauses (incorrect commas).
</guidelines>\n\n
    '''
    prompt_template_end = '<summary_polly><speak>'
    prompt = human_tag + prompt_template_pre + prompt_template + robot_tag + prompt_template_post + prompt_template_end
    prompt = prompt.replace('INPUT_POLLY', get_polly_tags())
    prompt = prompt.replace('INPUT_SUMMARY', input_summary)
    
    payload['prompt'] = prompt
    response = query_endpoint(client, endpoint, payload)
    summary_polly = response[0].split('</speak></summary_polly>')[0]
    return summary_polly


def get_summary(client, endpoint, payload, input_paper, q=None):
    human_tag = payload['human_tag']
    robot_tag = payload['robot_tag']
    split_tag = payload['split_tag']
    
    prompt_template_pre = ''
    prompt_template = """Read the following research article and write a detailed summary of the paper's findings including background, data,
    models/algorithms, method/proposed solution, results, and any novel conclusions:\n\nPaper:<article>INPUT_PAPER</article>\n\n
    From the above paper, write a summary of the articles findings including background, data, models/algorithms,
    method/proposed solution, results, and any novel conclusions in <summary></summary> tags.
    Be verbose and explain the concepts well. Define any uncommon terms.
    This summary should go above and beyond the abstract including limitations as well as avenues for future exploration.
    There should also be detailed examples and specifics where applicable."""
    prompt_template_post = ''
    prompt_template_end = '<summary>'
    prompt = human_tag + prompt_template_pre + prompt_template + robot_tag + prompt_template_end
    prompt = prompt.replace('INPUT_PAPER', input_paper)
    
    payload['prompt'] = prompt
    response = query_endpoint(client, endpoint, payload)
    summary = response[0].split('</summary>')[0]
    summary_polly = get_summary_polly(client, endpoint, payload, summary)
    if q is not None:
        q.put(('summary', summary, summary_polly))
    return summary, summary_polly


def get_code(client, endpoint, payload, input_paper, q=None):
    human_tag = payload['human_tag']
    robot_tag = payload['robot_tag']
    split_tag = payload['split_tag']
    
    prompt_template_pre = 'You are an AI Researcher whose goal is to analyze articles and produce robust and understandable Python code examples.'
    prompt_template = """Read the following research paper and implement a well formatted and well documented code example,
that impliments the models and/or algorithms precented in the paper. This can use sample data, but the explanation should be clear in the code:
\nPaper:<paper>INPUT_PAPER</paper>\n\nFrom the above paper, implement a well formatted and well documented code example in <code></code> tags,
that impliments the models and/or algorithms precented in the paper. This can use sample data, but the explanation should be clear in the code.
Before writing the code, list a detailed outline of what models/algorithms you plan to impliment and then what functions you would need to either impliment or use from a library."""
    prompt_template_post = 'Certainly. I will write well-documented and error free code. I will also detail all functions. My outline is:\nOutline:\n<outline>\n'
    prompt_template_end = '1. '
    prompt = human_tag + prompt_template_pre + prompt_template + robot_tag + prompt_template_post + prompt_template_end
    prompt = prompt.replace('INPUT_PAPER', input_paper)
    
    payload['prompt'] = prompt
    response = query_endpoint(client, endpoint, payload)
    try:
        code = response[0].split('</code>')[0].split('<code>')[1]
    except:
        code = prompt_template_end + response[0]
    code_polly = ""
    if q is not None:
        q.put(('code', code, code_polly))
    return code, code_polly


def fix_polly_text(data):
    client = data['client']
    endpoint = data['endpoint']
    payload = data['payload']
    input_text = data['text']
    
    human_tag = payload['human_tag']
    robot_tag = payload['robot_tag']
    split_tag = payload['split_tag']
    
    prompt_template_pre = ''
    prompt_template = """Read the following text prepared for Amazon Polly and correct any errors in the SSML tags used.\n\nPolly Text:INPUT_TEXT\n
    From the above Amazon Polly text, correct any errors in the text.
    This includes ensuring all tags are opened and closed correctly, as well as only using supported tags (e.g. remove <emphasis> tags)."""
    prompt_template_post = ''
    prompt_template_end = '<speak>'
    prompt = human_tag + prompt_template_pre + prompt_template + robot_tag + prompt_template_end
    prompt = prompt.replace('INPUT_TEXT', input_text)
    
    payload['prompt'] = prompt
    response = query_endpoint(client, endpoint, payload)
    transcript_polly = prompt_template_end + response[0].split('</speak>')[0] + '</speak>'
    return transcript_polly


def split_polly_text(client, endpoint, payload, summary_polly, title_polly, authors_polly, categories_polly, year_polly, max_workers=20):
    paper_polly = fix_polly_text({'client':client, 'endpoint':endpoint, 'payload':payload, 'text':summary_polly})
    if '</p>' in paper_polly:
        paper_polly_list = [t + '</p>' for t in paper_polly.replace('<speak>','').replace('</speak>','').split('</p>')[:-1]]
    elif '</s>' in paper_polly:
        paper_polly_list = [t + '</s>' for t in paper_polly.replace('<speak>','').replace('</speak>','').split('</s>')[:-1]]
    else:
        paper_polly_list = [t for t in paper_polly.replace('<speak>','').replace('</speak>','').replace('\n\n\n','\n').replace('\n\n','\n').split('\n')[:-1]]
    
    data_list = [{'client':client, 'endpoint':endpoint, 'payload':payload, 'text':text} for text in paper_polly_list]
    with ThreadPoolExecutor(max_workers) as pool:
        paper_polly_list = pool.map(fix_polly_text, data_list)
    paper_polly_list = [p for p in paper_polly_list]
    polly_start = '<speak>'
    polly_end = '</speak>'
    paper_polly_list = [polly_start+title_polly+polly_end, polly_start+year_polly+polly_end, polly_start+authors_polly+polly_end, polly_start+categories_polly+polly_end] + paper_polly_list
    return paper_polly_list


def call_polly(data):
    def remove_xml_tags(text):
        cleaned_text = ""  
        xml_tag = re.compile(r"<[^>]*>")
        fragments = xml_tag.split(text)
        for fragment in fragments:
            if not re.match("<[^>]*>", fragment):
                cleaned_text += fragment
        return cleaned_text
    
    client = data['client']
    text = data['text']
    try:
        response = client.synthesize_speech(Engine='neural', OutputFormat='mp3', Text=text, TextType='ssml', VoiceId='Joanna')
    except:
        try:
            text = remove_xml_tags(text).replace('&','&amp;').replace("'","&apos;").replace('"','&quot;').replace("<","&lt;").replace(">","&gt;")
            response = client.synthesize_speech(Engine='neural', OutputFormat='mp3', Text='<speak><p>'+text+'</p></speak>', TextType='ssml', VoiceId='Joanna')
        except:
            response = client.synthesize_speech(Engine='neural', OutputFormat='mp3', Text='<speak><p></p></speak>', TextType='ssml', VoiceId='Joanna')
    return response


def text_to_speech(client, text_list, max_workers=20):
    data_list = [{'client':client, 'text':text} for text in text_list]
    with ThreadPoolExecutor(max_workers) as pool:
        responses = pool.map(call_polly, data_list)
    
    audio_stream = None
    for audio in responses:
        if audio_stream is None:
            audio_stream = audio['AudioStream'].read()
        else:
            audio_stream += audio['AudioStream'].read()
    return audio_stream


def store_files(client, bucket, folder, filename, data, mode):
    if mode == 'audio':
        ext = '.mp3'
    elif mode == 'code':
        ext = '.py'
    elif mode == 'paper' or mode == 'transcripts':
        ext = '.txt'
    else:
        raise ValueError('Unknown mode')
    key = folder + '/' + filename.split('.pdf')[0] + ext
    client.put_object(Bucket=bucket, Key=key, Body=data)
    return 's3://' + bucket + '/' + key


def get_dynamodb_scan_full(table):
    return table.scan()['Items']


def get_dynamodb_scan(table):
    response = get_dynamodb_scan_full(table)
    paper_names = [item['PaperName'] for item in response]
    return paper_names


def get_item(table, paper_name, processed_timestamp=None):
    if processed_timestamp is None:
        response = table.get_item(
            Key={'PaperName': paper_name},
            KeyConditionExpression='PaperName = :name',
            ExpressionAttributeValues={':name': paper_name}
        )
    else:
        response = table.get_item(Key={'PaperName': paper_name, 'ProcessTimestamp': processed_timestamp})
    return 'Item' in response


def put_item(table, item):
    # TODO: Impliment and error handling or correction checks
    table.put_item(Item=item)
    return


def process_paper(config, endpoint, payload, paper_text, paper_path):
    tic = time.time()
    filename = os.path.basename(paper_path)
    q = Queue()
    t1 = threading.Thread(target=get_paper_metadata, args=(config['bedrock'], endpoint, payload, paper_text, q))
    t2 = threading.Thread(target=get_summary, args=(config['bedrock'], endpoint, payload, paper_text, q))
    t3 = threading.Thread(target=get_code, args=(config['bedrock'], endpoint, payload, paper_text, q))
    t1.start(); t2.start(); t3.start()
    t1.join(); t2.join(); t3.join()
    toc = time.time() - tic
    print(toc)
    
    title,title_polly,authors,authors_polly,categories,categories_polly,year,year_polly = '','','','','','','',''
    for _ in range(q.qsize()):
        tup = q.get()
        if tup[0] == 'title':
            title, title_polly = tup[1], tup[2]
        elif tup[0] == 'authors':
            authors, authors_polly = tup[1], tup[2]
        elif tup[0] == 'categories':
            categories, categories_polly = tup[1], tup[2]
        elif tup[0] == 'year':
            year, year_polly = tup[1], tup[2]
        elif tup[0] == 'summary':
            summary, summary_polly = tup[1], tup[2]
        elif tup[0] == 'code':
            code, code_polly = tup[1], tup[2]
    
    tic = time.time()
    paper_polly_list = split_polly_text(config['bedrock'], endpoint, payload, summary_polly, title_polly, authors_polly, categories_polly, year_polly)
    try:
        paper_polly_stream = text_to_speech(config['polly'], paper_polly_list)
    except Exception as e:
        _ = [print(t) for t in paper_polly_list]
        paper_polly_stream = text_to_speech(config['polly'], ["<speak><p>Unfortunately, I was unable to convert the transcript into speech.</p><p> Please look at the output transcript to determine any issues.</p></speak>"])
    toc = time.time() - tic
    print(toc)
    
    s3_paper_text = store_files(config['s3'], config['bucket'], config['prefix']+'/'+config['text'], filename, paper_text, mode='paper')
    s3_paper_transcript = store_files(config['s3'], config['bucket'], config['prefix']+'/'+config['transcripts'], filename, summary_polly, mode='transcripts')
    s3_paper_audio = store_files(config['s3'], config['bucket'], config['prefix']+'/'+config['audio'], filename, paper_polly_stream, mode='audio')
    s3_paper_code = store_files(config['s3'], config['bucket'], config['prefix']+'/'+config['code'], filename, code, mode='code')
    item = {
        'PaperName':filename,
        'ProcessTimestamp':str(datetime.now().strftime("%Y")),
        'PaperLocation':'s3://'+config['bucket']+'/'+paper_path,
        'FullTextLocation':s3_paper_text,
        'TranscriptLocation':s3_paper_transcript,
        'CodeLocation':s3_paper_code,
        'AudioLocation':s3_paper_audio,
        'FoundationModel':endpoint,
        'Title':title,
        'Authors':authors,
        'Year':year,
        'Categories':categories,
        'Summary':summary,
        'Code':code,
        'KeyReferences':'Not suported currently.',
        'ResearchIdeas':'Not suported currently.',
    }
    put_item(config['dynamodb'], item)
    return item, paper_polly_stream


def sidebar(config):
    st.sidebar.header('About the App')
    st.sidebar.write(get_about_me())
    st.sidebar.header('User Parameters')
    with st.sidebar.expander('**Data Input/Output**'):
        config['bucket'] = st.text_input('Bucket name', config['bucket'], disabled=False)
        config['prefix'] = st.text_input('Data Folder', config['prefix'], disabled=False)
        config['pdfs'] = st.text_input('Input PDF Location', config['pdfs'], disabled=False)
        config['text'] = st.text_input('Output Text Location', config['text'], disabled=False)
        config['audio'] = st.text_input('Output Audio Location', config['audio'], disabled=False)
        config['code'] = st.text_input('Output Code Location', config['code'], disabled=False)
        config['transcripts'] = st.text_input('Output Transcripts Location', config['transcripts'], disabled=False)
    with st.sidebar.expander('**Model Parameters**'):
        model_text = st.selectbox('Model', config['models_text'].keys())
        max_len_text = st.number_input('Max Generation Length', 1000, 5000, 2500, 500) 
        temp_text = st.slider('Temperature', 0.01, 1., 0.01, .01)
    with st.sidebar.expander('**File Upload**'):
        local_file = st.file_uploader('You can upload a local PDF here', type=['pdf'])
        if local_file is not None:
            upload_file_to_s3(
                local_file,
                config['bucket'],
                object_name="/".join([config['prefix'], config['pdfs'], local_file.name])
            )
    config['model_text'] = model_text
    config['max_len_text'] = max_len_text
    config['temp_text'] = temp_text
    config['model_text_endpoint'] = config['models_text'][model_text]
    return config


@st.cache_resource
def apply_papers(papers_new, papers_old):
    st.session_state['papers_new_selected'] = [p for p in st.session_state['papers'] if os.path.basename(p) in papers_new]
    st.session_state['papers_old_selected'] = [p for p in st.session_state['papers'] if os.path.basename(p) in papers_old]


def main(config, max_workers=20):
    st.title("AI Research Digest - Discover the latest papers")
    st.subheader('Your daily AI research podcast')
    with st.expander('How It Works'):
        tab1, tab2 = st.tabs(['**Architecture**', '**App Details**'])
        with tab1:
            st.image(config['diagram'])
            st.write(get_arch_details())
        with tab2:
            st.write(get_app_details())
    
    endpoint = config['model_text_endpoint']
    payload = {
        'prompt':'',
        'max_len':config['max_len_text'],
        'temp':config['temp_text'],
        'top_p':.9
    }
    human_tag, robot_tag, split_tag = get_model_tags(endpoint)
    payload['human_tag'] = human_tag
    payload['robot_tag'] = robot_tag
    payload['split_tag'] = split_tag
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Today's Top Papers")
        with st.expander('**Selected Papers**'):
            btn1, btn2 = st.columns(2)
            with btn1:
                if st.button('Load Available Papers'):
                    st.session_state['papers'] = sorted(get_pdf_list(config['s3'], config['bucket'], config['prefix'] + '/' + config['pdfs']))
                    st.session_state['dynamodb_scan'] = get_dynamodb_scan(config['dynamodb'])
                    st.session_state['papers_new'] = [os.path.basename(p) for p in st.session_state['papers'] if os.path.basename(p) not in st.session_state['dynamodb_scan']]
                    st.session_state['papers_old'] = [os.path.basename(p) for p in st.session_state['papers'] if os.path.basename(p) in st.session_state['dynamodb_scan']]
            
            # Set the selected papers
            papers_selected_new = st.multiselect('Select from unprocessed papers', st.session_state['papers_new'])
            papers_selected_old = st.multiselect('Select from processed papers', st.session_state['papers_old'])
            
            with btn2:
                if st.button('Summarize Papers'):
                    apply_papers(papers_selected_new, papers_selected_old)
                    
                    # Process Old Papers
                    paper_names = [os.path.basename(p) for p in st.session_state['papers_old_selected']]
                    paper_items = [i for i in get_dynamodb_scan_full(config['dynamodb']) if i['PaperName'] in paper_names]
                    for item in paper_items:
                        audio = load_mp3_from_s3(config['s3'], item['AudioLocation'].split('/')[2],  "/".join(item['AudioLocation'].split('/')[3:]))
                        st.session_state['papers_processed'].append({'title':item['Title'], 'audio':audio, 'summary':item['Summary'], 'code':item['Code']})
                    
                    # Process New Papers
                    paper_data = [{'client':config['textract'], 'bucket':config['bucket'], 'paper':paper} for paper in st.session_state['papers_new_selected']]
                    with ThreadPoolExecutor(max_workers) as pool:
                        paper_list = pool.map(extract_text, paper_data)
                    for paper, text in zip(st.session_state['papers_new_selected'], paper_list):
                        item, audio = process_paper(config, endpoint, payload, text, os.path.basename(paper))
                        st.session_state['papers_processed'].append({'title':item['Title'], 'audio':audio, 'summary':item['Summary'], 'code':item['Code']})
                        time.sleep(5)
    
    
    with col2:
        st.subheader('Paper Breakdown')
        for paper in st.session_state['papers_processed']:
            with st.expander(f'**{paper["title"]}**'):
                st.write('Here is the audio session:')
                st.audio(paper['audio'])
                tab1, tab2 = st.tabs(['**Paper Summary**', '**Code Example**'])
                with tab1:
                    st.write(paper['summary'])
                with tab2:
                    st.code(paper['code'])
    return


if __name__ == '__main__':
    FILEPATH = './config_demo_genai_research_assistant.json'
    if 'config' not in st.session_state:
        initialize_session(FILEPATH)
    config = sidebar(st.session_state['config'])
    main(config)
