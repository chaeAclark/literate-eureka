# Bedrock SDK: README

Welcome to the Bedrock SDK, a Python library designed to simplify the interaction with Amazon Bedrock for data scientists and machine learning engineers. This SDK provides a high-level abstraction over the boto3 client for Amazon Bedrock, making it easier to create, manage, and utilize prompt templates.

## Table of Contents
1. [Installation](#installation)
2. [Prompt Template](#prompt-template)
   - [Description](#description)
   - [Input Variables](#input-variables)
   - [Creation](#creation)
   - [Simple Example](#simple-example)
   - [Advanced Example](#advanced-example)
   - [Decorators](#decorators)
3. [Few-Shot Template](#few-shot-template)
4. [API Reference](#api-reference)

## Installation
To install the Bedrock SDK, use pip:
```bash
pip install bedrock-sdk
```

## Prompt Template

### Description
The `PromptTemplate` class is designed to manage and interact with prompt templates in Amazon Bedrock. It allows you to create, save, update, render, and delete prompt templates with ease.

### Input Variables
Input variables in the prompt content are denoted using double curly brackets `{{variable}}`. These variables must be provided when rendering the template.

### Creation
Creating a `PromptTemplate` instance does not save it to Bedrock until you explicitly call the `save` method.

### Simple Example
```python
from bedrock_sdk import PromptTemplate

simple_example = PromptTemplate(
    name="greeting_template",
    content="Hello, {{name}}!",
    description="A simple greeting template",
    tags={"purpose": "greeting"}
)
```

### Advanced Example
```python
from bedrock_sdk import PromptTemplate

advanced_example = PromptTemplate(
    name="data_analysis_template",
    content="""
<<system>>
You are a helpful data analyst. You will be given CSVs and must perform detailed analysis of the data and find any data quality issues.

<<user>>
{{CSV}}

Read the above CSV and write a detailed markdown report discussing any data quality issues found.

<<assistant>>
<markdown>
# Data Quality Report
...
""",
    description="A template for data analysis tasks",
    tags={"purpose": "data_analysis"}
)
```

### Decorators
The `PromptTemplate` class supports several decorators to enhance the prompt content.

#### Variables Decorators
Any text within double curly brackets `{{variable}}` is considered a variable and must be provided when calling a Bedrock model.

#### System/User/Assistant Decorators
You can structure conversations within your prompts using double angled brackets `<<>>`. These tags help designate system messages, user inputs, and assistant responses.

- `<<system>>`: System-level instructions or context.
- `<<user>>`: User input or query.
- `<<assistant>>`: Assistant's response.

**Note:** Conversations must begin with a `<<user>>` tag, and you must alternate between `<<user>>` and `<<assistant>>` tags.

## Few-Shot Template
The `FewShotTemplate` class allows you to create a collection of few-shot examples using `PromptTemplate` instances.

### Example
```python
from bedrock_sdk import PromptTemplate, FewShotTemplate

example1 = PromptTemplate(
    name="example1",
    content="Hello, {{name}}!",
    description="Example 1"
)

example2 = PromptTemplate(
    name="example2",
    content="How are you today, {{name}}?",
    description="Example 2"
)

few_shot_examples = FewShotTemplate([
    (example1, {"name": "Alice"}),
    (example2, {"name": "Bob"})
])

print(few_shot_examples.render())
```

## API Reference

### PromptTemplate
```python
@dataclass
class PromptTemplate:
    name: str
    content: str
    description: Optional[str] = 'NA'
    tags: Dict[str, str] = field(default_factory=dict)
    
    @property
    def variables(self) -> List[str]:
        return re.findall(r'\{\{(\w+)\}\}', self.content)
    
    @property
    def prompt_id(self) -> Optional[str]:
        return self._prompt_id
    
    @property
    def version(self) -> Optional[str]:
        return self._version
    
    def save(self) -> Tuple[str, str]:
        ...
    
    def create_version(self, description: Optional[str] = 'NA') -> str:
        ...
    
    def render(self, variables: Dict[str, str]) -> str:
        ...
    
    def delete(self):
        ...
    
    @classmethod
    def load(cls, prompt_id: str) -> "PromptTemplate":
        ...
```

### FewShotTemplate
```python
class FewShotTemplate:
    def __init__(self, examples: List[Tuple[PromptTemplate, Dict[str, str]]]):
        ...
    
    def render(self) -> str:
        ...
```

This README provides a comprehensive guide to using the Bedrock SDK for managing prompt templates and creating few-shot examples. For more detailed information, refer to the [API Reference](#api-reference).


# Bedrock SDK: BedrockClient README

Welcome to the Bedrock SDK documentation for the `BedrockClient` class. This class provides a high-level interface for interacting with AWS Bedrock models, handling conversation history, and managing model interactions. Below, you'll find detailed information on how to use the `BedrockClient` class, including examples and API references.

## Table of Contents
1. [Installation](#installation)
2. [BedrockClient](#bedrockclient)
   - [Initialization](#initialization)
   - [Converse with Model](#converse-with-model)
   - [Conversation History](#conversation-history)
   - [Clear History](#clear-history)
3. [API Reference](#api-reference)

## Installation
To install the Bedrock SDK, use pip:
```bash
pip install bedrock-sdk
```

## BedrockClient

### Initialization
The `BedrockClient` class is designed to interact with AWS Bedrock models. It manages conversation history and provides methods to converse with models.

```python
from bedrock_sdk import BedrockClient, ModelConfig

# Initialize BedrockClient
client = BedrockClient(
    region_name="us-east-1",
    max_retries=3,
    base_delay=2.0,
    profile_name="your_profile_name"
)
```

### Converse with Model
The `converse` method allows you to interact with a Bedrock model, handling conversation history and formatting prompts based on the model type.

```python
from bedrock_sdk import BedrockClient, ModelConfig, PromptTemplate, FewShotTemplate

# Initialize BedrockClient
client = BedrockClient()

# Define model configuration
model_config = ModelConfig(
    model_id="amazon.titan-text-express-v1",
    max_tokens=512,
    temperature=0.7,
    top_p=0.9
)

# Create a prompt template
prompt = PromptTemplate(
    name="example_prompt",
    content="<<user>>Hello, how can I assist you today?<<assistant>>"
)

# Converse with the model
response = client.converse(
    prompt=prompt,
    model_config=model_config,
    variables={},
    few_shot_template=None,
    stream=False,
    include_history=True,
    should_rety=True
)

print(response)
```

### Conversation History
The `ConversationHistory` class manages the conversation history, allowing you to add messages, format history based on the model, and clear the history.

```python
# Add messages to conversation history
client.conversation_history.add_message("user", "Hello, how are you?")
client.conversation_history.add_message("assistant", "I'm doing well, thank you!")

# Get formatted conversation history
formatted_history = client.conversation_history.get_formatted_history(model_config.model_id)
print(formatted_history)

# Get the last message
last_message = client.conversation_history.get_last_messages(1)
print(last_message)
```

### Clear History
You can clear the conversation history using the `clear` method.

```python
# Clear conversation history
client.clear_history()
```

## API Reference

### BedrockClient
```python
class BedrockClient:
    def __init__(
        self,
        region_name: str = "us-east-1",
        max_retries: int = 3,
        base_delay: float = 2.0,
        profile_name: Optional[str] = None
    ):
        ...
    
    def converse(
        self,
        prompt: Union[str, PromptTemplate],
        model_config: ModelConfig,
        variables: Dict[str, str] = {},
        few_shot_template: Optional[FewShotTemplate] = None,
        stream: bool = False,
        include_history: bool = True,
        should_rety: bool = True,
    ) -> Union[str, Iterator[str]]:
        ...
    
    def clear_history(self):
        ...
```

### ConversationHistory
```python
class ConversationHistory:
    def __init__(self, max_messages: int = 100):
        ...
    
    def add_message(self, role: str, content: str):
        ...
    
    def get_formatted_history(self, model_id: str) -> str:
        ...
    
    def get_last_messages(self, n: int = 1) -> List[Dict[str, str]]:
        ...
    
    def clear(self):
        ...
```

This README provides a comprehensive guide to using the `BedrockClient` class for managing interactions with AWS Bedrock models. For more detailed information, refer to the [API Reference](#api-reference).

# Bedrock SDK: Guardrails README

Welcome to the Bedrock SDK documentation for the `Guardrails` module. This module provides tools to manage and apply guardrails for responsible AI interactions. Below, you'll find detailed information on how to use the `Guardrail` class, including examples and API references.

## Table of Contents
1. [Installation](#installation)
2. [Guardrails](#guardrails)
   - [Initialization](#initialization)
   - [Create Guardrail](#create-guardrail)
   - [Apply Guardrail](#apply-guardrail)
   - [Delete Guardrail](#delete-guardrail)
3. [API Reference](#api-reference)

## Installation
To install the Bedrock SDK, use pip:
```bash
pip install bedrock-sdk
```

## Guardrails

### Initialization
The `Guardrail` class is designed to manage guardrails for responsible AI interactions. It allows you to create, apply, and delete guardrails.

```python
from bedrock_sdk import Guardrail, GuardrailConfig, TopicDefinition, ContentFilter, ContentFilterType, FilterStrength, PIIEntityType, PIIAction

# Define topic definitions
topics = [
    TopicDefinition(
        name="violence",
        definition="Content involving violence",
        examples=["gun", "fight", "war"],
        is_allowed_topic=False
    ),
    TopicDefinition(
        name="medical",
        definition="Content related to medical advice",
        examples=["doctor", "medicine", "treatment"],
        is_allowed_topic=True,
        complement_message="Please consult a healthcare professional for medical advice."
    )
]

# Define content filters
content_filters = [
    ContentFilter(
        filter_type=ContentFilterType.VIOLENCE,
        input_strength=FilterStrength.MEDIUM,
        output_strength=FilterStrength.HIGH
    )
]

# Define PII entities
pii_entities = [
    (PIIEntityType.EMAIL, PIIAction.ANONYMIZE),
    (PIIEntityType.PHONE, PIIAction.BLOCK)
]

# Create guardrail configuration
config = GuardrailConfig(
    name="example_guardrail",
    description="Example guardrail configuration",
    topics=topics,
    pii_entities=pii_entities,
    content_filters=content_filters,
    blocked_input_message="This input is not allowed.",
    blocked_output_message="This output is not allowed."
)

# Initialize Guardrail
guardrail = Guardrail(config, region_name="us-east-1", profile_name="your_profile_name")
```

### Create Guardrail
The `create` method allows you to create a guardrail in AWS Bedrock.

```python
# Create guardrail
guardrail_id, version = guardrail.create()
print(f"Guardrail ID: {guardrail_id}, Version: {version}")
```

### Apply Guardrail
The `apply` method allows you to apply the guardrail to content.

```python
# Apply guardrail to content
content = "This is a test message containing violence."
result = guardrail.apply(content, source="INPUT")

print(result)
```

### Delete Guardrail
The `delete` method allows you to delete the guardrail.

```python
# Delete guardrail
guardrail.delete()
```

## API Reference

### Guardrail
```python
class Guardrail:
    def __init__(
        self,
        config: GuardrailConfig,
        region_name: str = "us-east-1",
        profile_name: Optional[str] = None
    ):
        ...
    
    def create(self) -> Tuple[str, str]:
        ...
    
    def apply(
        self,
        content: Union[str, List[str]],
        source: str = "INPUT",
        qualifiers: Optional[List[str]] = None
    ) -> GuardrailResult:
        ...
    
    def delete(self):
        ...
```

### GuardrailConfig
```python
@dataclass
class GuardrailConfig:
    name: str
    description: Optional[str] = None
    topics: List[TopicDefinition] = field(default_factory=list)
    pii_entities: List[Tuple[PIIEntityType, PIIAction]] = field(default_factory=list)
    content_filters: List[ContentFilter] = field(default_factory=list)
    blocked_input_message: str = "This input is not allowed."
    blocked_output_message: str = "This output is not allowed."
```

### TopicDefinition
```python
@dataclass
class TopicDefinition:
    name: str
    definition: str
    examples: List[str]
    is_allowed_topic: bool = False
    complement_message: Optional[str] = None
```

### ContentFilter
```python
@dataclass
class ContentFilter:
    filter_type: ContentFilterType
    input_strength: FilterStrength
    output_strength: FilterStrength
```

### GuardrailResult
```python
@dataclass
class GuardrailResult:
    action: GuardrailAction
    output: str
    topics: List[TopicAssessment]
    usage: UsageMetrics
    original_response: Dict[str, Any]
    
    @classmethod
    def from_response(cls, response: Dict[str, Any]) -> 'GuardrailResult':
        ...
    
    def __str__(self) -> str:
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        ...
```

This README provides a comprehensive guide to using the `Guardrail` class for managing guardrails in AWS Bedrock. For more detailed information, refer to the [API Reference](#api-reference).
