# AI Research Assistant

### Description

This is a Python program that implements a Streamlit web application to serve as an AI research assistant. The aim is to help users discover and digest the latest academic papers in their field of interest through generated audio podcast episodes.

The key problem this application aims to address is staying current on the immense volume of machine learning papers published, which can be inaccessible due to paywalls, dense technical material, and the time needed to read papers thoroughly. Many readers also prefer asynchronous audio content for learning.

To accomplish this, the web app provides an interface for users to upload or specify PDF papers. It leverages AWS services to extract raw text from the PDFs using Textract OCR. This text is then passed to the Claude API hosted on Amazon Bedrock to generate a long-form summary, as well as metadata like title, authors, categories, and a sample code implementation. The summary text is formatted with SSML tags to optimize it for text-to-speech using Amazon Polly, which converts the text into an audio MP3.

The benefits of this approach include leveraging large language models like Claude to quickly analyze and concisely summarize technical papers with little human input needed. Text-to-speech further adapts the content into an easy-to-consume audio format for passive listening. Showcasing sample code also makes ML concepts more tangible. Architecting the workflow serverlessly on AWS makes the app scalable and cost-effective.

Overall, this AI research assistant web app aims to help users keep up with the latest ML advancements through auto-generated audio podcasts summarizing key papers in their field, lowering the barrier to benefitting from cutting edge research.
