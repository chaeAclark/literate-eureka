from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Iterator
import json
import time
import re
import boto3
from botocore.exceptions import ClientError
from bedrock_sdk.prompt_template import PromptTemplate, FewShotTemplate

@dataclass 
class ModelConfig:
    """Configuration for a Bedrock model"""
    model_id: str
    max_tokens: int = 512
    temperature: float = 0.01
    top_p: float = 0.99

class ConversationHistory:
    """Manages conversation history"""
    def __init__(self, max_messages: int = 100):
        self.messages: List[Dict[str, str]] = []
        self.system_message: Optional[str] = None
        self.max_messages = max_messages  # Limit conversation history
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        if role == "system":
            self.system_message = content
        else:
            # Maintain max message limit by removing oldest messages if needed
            while len(self.messages) >= self.max_messages:
                self.messages.pop(0)
            self.messages.append({"role": role, "content": content})
    
    def get_formatted_history(self, model_id: str) -> str:
        """Format history based on model"""
        if not self.messages:
            return ""
            
        if "llama3" in model_id:
            return self._format_llama3()
        elif "mistral" in model_id:
            return self._format_mistral()
        else:
            return self._format_default()

    def _format_llama3(self) -> str:
        formatted = "<|begin_of_text|>"
        if self.system_message:
            formatted += f"<|start_header_id|>system<|end_header_id|>\n{self.system_message}<|eot_id|>\n"
        
        for msg in self.messages:
            formatted += f"<|start_header_id|>{msg['role']}<|end_header_id|>\n{msg['content']}<|eot_id|>\n"
        return formatted

    def _format_mistral(self) -> str:
        formatted = ""
        if self.system_message:
            formatted += f"<<SYS>>{self.system_message}<</SYS>>"
            
        formatted += "<s>[INST]"
        for i, msg in enumerate(self.messages):
            if msg["role"] == "user":
                if i > 0:
                    formatted += "</s><s>[INST]"
                formatted += msg["content"]
            else:
                formatted += "[/INST]" + msg["content"]
        return formatted

    def _format_default(self) -> str:
        formatted = ""
        if self.system_message:
            formatted += f"<<system>>\n{self.system_message}\n"
            
        for msg in self.messages:
            formatted += f"<<{msg['role']}>>\n{msg['content']}\n"
        return formatted

    def get_last_messages(self, n: int = 1) -> List[Dict[str, str]]:
        """Get the last n messages from history"""
        return self.messages[-n:] if self.messages else []

    def clear(self):
        """Clear conversation history"""
        self.messages = []
        self.system_message = None

class BedrockClient:
    """Client for AWS Bedrock model interactions"""
    
    def __init__(
        self,
        region_name: str = "us-east-1",
        max_retries: int = 4,
        base_delay: float = 65.0,
        profile_name: Optional[str] = None
    ):
        session = boto3.Session(profile_name=profile_name)
        self.client = session.client('bedrock-runtime', region_name=region_name)
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.conversation_history = ConversationHistory()

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
        """
        Conversation with model using converse API when possible, falling back to invoke_model
        """
        import time

        if isinstance(prompt, str):
            if not(('<<system>>' in prompt) or ('<<user>>' in prompt) or ('<<assistant>>' in prompt)):
                prompt = '<<user>>\n' + prompt
            prompt = PromptTemplate('tmp', prompt)
        
        # Format prompt with variables and few-shot examples
        prompt_text = self._format_prompt(prompt, variables, few_shot_template)
        
        # Parse the new prompt first (without history)
        new_messages = self.prompt_to_json(prompt_text)
        
        # Get formatted conversation history and combine with prompt if needed
        if include_history:
            history = self.conversation_history.get_formatted_history(model_config.model_id)
            if history:
                prompt_text = f"{history}\n{prompt_text}"
    
        # Parse complete prompt (including history) for API formatting
        parsed_prompt = self.prompt_to_json(prompt_text)
        
        # Check if prompt ends with assistant message
        ends_with_assistant = (
            parsed_prompt["assistant"] and 
            len(parsed_prompt["assistant"]) == len(parsed_prompt["user"])
        )
        
        # Use converse API if possible
        if (not ends_with_assistant) or ("anthropic" in model_config.model_id) or (".nova" in model_config.model_id):
            max_retries = self.max_retries if should_rety else 0
            current_retry = 0
            
            while current_retry <= max_retries:
                try:
                    response = self._use_converse_api(
                        parsed_prompt,
                        model_config,
                        stream=stream
                    )
                    # Add assistant response to history if not streaming
                    if not stream:
                        # Add new messages to conversation history
                        if new_messages["system"]:
                            self.conversation_history.add_message("system", new_messages["system"])
                        for i in range(len(new_messages["user"])):
                            self.conversation_history.add_message("user", new_messages["user"][i])
                            if i < len(new_messages["assistant"]):
                                self.conversation_history.add_message("assistant", new_messages["assistant"][i])
                        self.conversation_history.add_message("assistant", response)
                    return response
                except Exception as e:
                    if "ThrottlingException" in str(e) and current_retry < max_retries:
                        print(f"Throttling detected, waiting {self.base_delay} seconds before retry...")
                        time.sleep(self.base_delay)
                        current_retry += 1
                        continue
                    print(f"Converse API failed, falling back to invoke_model: {e}")
                    break
        
        # Fall back to invoke_model with model-specific formatting
        response = self._use_invoke_model(
            parsed_prompt,
            model_config,
            stream=stream
        )
        
        # Add assistant response to history if not streaming
        if not stream:
            self.conversation_history.add_message("assistant", response)
        return response

    def _format_prompt(
        self,
        prompt: Union[str, PromptTemplate],
        variables: Dict[str, str],
        few_shot_template: Optional[FewShotTemplate]
    ) -> str:
        """Format prompt with variables and few-shot examples"""
        # Format prompt with variables
        if isinstance(prompt, str):
            prompt_template = PromptTemplate('tmp', prompt)
            prompt_text = prompt_template.render(variables)
        else:
            prompt_text = prompt.render(variables)
    
        # Add few-shot examples if provided
        if few_shot_template:
            prompt_text = f"{few_shot_template.render()}\n\n{prompt_text}"
            
        return prompt_text

    def _use_converse_api(
        self,
        parsed_prompt: Dict[str, Union[str, List[str]]],
        model_config: ModelConfig,
        stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """Use the Bedrock converse API"""
        
        # Format messages alternating between user/assistant
        messages = []
        # Add system message if present
        if parsed_prompt["system"]:
            system = [{"text": parsed_prompt["system"]}]
        else:
            system = None
        
        # Build message sequence
        for i in range(len(parsed_prompt["user"])):
            # Add user message
            if i < len(parsed_prompt["user"]):
                messages.append({
                    "role": "user",
                    "content": [{"text": parsed_prompt["user"][i]}]
                })
            # Add assistant message if available
            if i < len(parsed_prompt["assistant"]):
                messages.append({
                    "role": "assistant", 
                    "content": [{"text": parsed_prompt["assistant"][i]}]
                })
        # Call converse API
        kwargs = {
            "modelId": model_config.model_id,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": model_config.max_tokens,
                "temperature": model_config.temperature,
                "topP": model_config.top_p
            }
        }
        if system:
            kwargs["system"] = system
        if stream:
            response = self.client.converse_stream(**kwargs)
            return self._handle_stream_response(response)
        else:
            response = self.client.converse(**kwargs)
            return response["output"]["message"]["content"][0]["text"]

    def _use_invoke_model(
        self,
        parsed_prompt: Dict[str, Union[str, List[str]]],
        model_config: ModelConfig, 
        stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """Use invoke_model with model-specific formatting"""
        
        # Format prompt based on model type
        if "llama3" in model_config.model_id:
            formatted_prompt = self._format_llama3_prompt(parsed_prompt)
        elif "mistral" in model_config.model_id:
            formatted_prompt = self._format_mistral_prompt(parsed_prompt)
        elif "anthropic" in model_config.model_id:
            formatted_prompt = self._format_anthropic_prompt(parsed_prompt)
        elif "ai21" in model_config.model_id:
            formatted_prompt = self._format_ai21_prompt(parsed_prompt)
        elif "cohere" in model_config.model_id:
            formatted_prompt = self._format_cohere_prompt(parsed_prompt)
        else:  # amazon models
            formatted_prompt = self._format_amazon_prompt(parsed_prompt)

        # Format request body based on model type
        body = self._format_model_body(formatted_prompt, model_config)
        
        if stream:
            response = self.client.invoke_model_with_response_stream(
                modelId=model_config.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )
            return self._handle_stream_response(response)
        else:
            response = self.client.invoke_model(
                modelId=model_config.model_id,
                body=json.dumps(body),
                contentType="application/json", 
                accept="application/json"
            )
            return self._parse_response(response, model_config.model_id)

    def _format_model_body(self, prompt: str, model_config: ModelConfig) -> Dict:
        """Format request body based on model type"""
        if "llama3" in model_config.model_id:
            return {
                "prompt": prompt,
                "max_gen_len": model_config.max_tokens,
                "temperature": model_config.temperature,
                "top_p": model_config.top_p
            }
        elif "mistral" in model_config.model_id:
            return {
                "prompt": prompt,
                "max_tokens": model_config.max_tokens,
                "temperature": model_config.temperature,
                "top_p": model_config.top_p
            }
        elif "anthropic" in model_config.model_id:
            return {
                "prompt": prompt,
                "max_tokens_to_sample": model_config.max_tokens,
                "temperature": model_config.temperature,
                "top_p": model_config.top_p
            }
        elif "ai21" in model_config.model_id:
            return {
                "prompt": prompt,
                "maxTokens": model_config.max_tokens,
                "temperature": model_config.temperature,
                "topP": model_config.top_p
            }
        elif "cohere" in model_config.model_id:
            return {
                "prompt": prompt,
                "max_tokens": model_config.max_tokens,
                "temperature": model_config.temperature,
                "p": model_config.top_p
            }
        else:  # amazon models
            return {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": model_config.max_tokens,
                    "temperature": model_config.temperature,
                    "topP": model_config.top_p
                }
            }

    def _format_llama3_prompt(self, parsed_prompt: Dict[str, Union[str, List[str]]]) -> str:
        """Format prompt for Llama 3 models"""
        prompt = "<|begin_of_text|>"
        
        if parsed_prompt["system"]:
            prompt += f"<|start_header_id|>system<|end_header_id|>\n{parsed_prompt['system']}<|eot_id|>\n"
            
        for i in range(max(len(parsed_prompt["user"]), len(parsed_prompt["assistant"]))):
            if i < len(parsed_prompt["user"]):
                prompt += f"<|start_header_id|>user<|end_header_id|>\n{parsed_prompt['user'][i]}<|eot_id|>\n"
            if i < len(parsed_prompt["assistant"]):
                prompt += f"<|start_header_id|>assistant<|end_header_id|>\n{parsed_prompt['assistant'][i]}<|eot_id|>\n"
                
        return prompt

    def _format_mistral_prompt(self, parsed_prompt: Dict[str, Union[str, List[str]]]) -> str:
        """Format prompt for Mistral models"""
        prompt = ""
        
        if parsed_prompt["system"]:
            prompt += f"<<SYS>>{parsed_prompt['system']}<</SYS>>"
            
        prompt += "<s>[INST]"
        
        for i in range(max(len(parsed_prompt["user"]), len(parsed_prompt["assistant"]))):
            if i < len(parsed_prompt["user"]):
                if i > 0:
                    prompt += "</s><s>[INST]"
                prompt += parsed_prompt["user"][i]
            if i < len(parsed_prompt["assistant"]):
                prompt += "[/INST]" + parsed_prompt["assistant"][i]
                
        return prompt

    def _format_anthropic_prompt(self, parsed_prompt: Dict[str, Union[str, List[str]]]) -> str:
        """Format prompt for Anthropic models"""
        prompt = ""
        
        if parsed_prompt["system"]:
            prompt += f"\n\nHuman: {parsed_prompt['system']}\n\nAssistant: Understood. I'll follow those instructions.\n\n"
            
        for i in range(max(len(parsed_prompt["user"]), len(parsed_prompt["assistant"]))):
            if i < len(parsed_prompt["user"]):
                prompt += f"Human: {parsed_prompt['user'][i]}\n\n"
            if i < len(parsed_prompt["assistant"]):
                prompt += f"Assistant: {parsed_prompt['assistant'][i]}\n\n"
                
        return prompt

    def _format_ai21_prompt(self, parsed_prompt: Dict[str, Union[str, List[str]]]) -> str:
        """Format prompt for AI21 models"""
        # AI21 specific formatting if needed
        return self._format_default_prompt(parsed_prompt)

    def _format_cohere_prompt(self, parsed_prompt: Dict[str, Union[str, List[str]]]) -> str:
        """Format prompt for Cohere models"""
        # Cohere specific formatting if needed
        return self._format_default_prompt(parsed_prompt)

    def _format_amazon_prompt(self, parsed_prompt: Dict[str, Union[str, List[str]]]) -> str:
        """Format prompt for Amazon models"""
        # Amazon specific formatting if needed
        return self._format_default_prompt(parsed_prompt)

    def _format_default_prompt(self, parsed_prompt: Dict[str, Union[str, List[str]]]) -> str:
        """Default prompt formatting"""
        prompt = ""
        
        if parsed_prompt["system"]:
            prompt += f"<<system>>\n{parsed_prompt['system']}\n\n"
            
        for i in range(max(len(parsed_prompt["user"]), len(parsed_prompt["assistant"]))):
            if i < len(parsed_prompt["user"]):
                prompt += f"<<user>>\n{parsed_prompt['user'][i]}\n\n"
            if i < len(parsed_prompt["assistant"]):
                prompt += f"<<assistant>>\n{parsed_prompt['assistant'][i]}\n\n"
                
        return prompt

    def _handle_stream_response(self, response: Dict) -> Iterator[str]:
        """Handle streaming responses from both APIs"""
        if 'stream' in response:  # converse_stream response
            for event in response['stream']:
                if 'contentBlockDelta' in event:
                    delta = event['contentBlockDelta']
                    if 'delta' in delta and 'text' in delta['delta']:
                        yield delta['delta']['text']
        else:  # invoke_model_with_response_stream response
            for event in response['body']:
                if 'chunk' in event:
                    yield event['chunk']['bytes'].decode()

    def _parse_response(self, response: Dict, model_id: str) -> str:
        """Parse model response based on provider"""
        try:
            response_body = json.loads(response.get('body').read())
            
            if "llama" in model_id:
                return response_body['generation']
            elif "mistral" in model_id:
                return response_body['outputs'][0]['text']
            elif "anthropic" in model_id:
                return response_body['completion']
            elif "ai21" in model_id:
                return response_body['completions'][0]['data']['text']
            elif "cohere" in model_id:
                return response_body['generations'][0]['text']
            else:
                return response_body['results'][0]['outputText']
                
        except Exception as e:
            raise Exception(f"Failed to parse model response: {str(e)}")

    def prompt_to_json(self, prompt: str) -> Dict[str, Union[str, List[str]]]:
        """Parse prompt into system, user, and assistant components"""
        if ('<<system>>' in prompt) or ('<<user>>' in prompt) or ('<<assistant>>' in prompt):
            prompt = prompt + '<<'

        system_text = re.search(r'<<system>>(.*?)(<<|\$)', prompt, re.DOTALL)
        system_text = system_text.group(1).strip() if system_text else ""

        user_texts = re.findall(r'<<user>>(.*?)(<<|\$)', prompt, re.DOTALL)
        user_texts = [t.strip() for t, _ in user_texts]

        assistant_texts = re.findall(r'<<assistant>>(.*?)(<<|\$)', prompt, re.DOTALL)
        assistant_texts = [t.strip() for t, _ in assistant_texts if len(t.strip()) > 0]

        if not user_texts and not system_text and not assistant_texts:
            user_texts = [prompt.strip()]

        return {
            "system": system_text,
            "user": user_texts,
            "assistant": assistant_texts
        }


    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()