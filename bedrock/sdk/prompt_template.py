from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import boto3
from botocore.exceptions import ClientError
import re


@dataclass
class PromptTemplate:
    """
    A class to manage prompt templates in Amazon Bedrock.
    
    Attributes:
        name (str): Name of the prompt template
        content (str): Content of the prompt with optional variables in {variable} format
        description (Optional[str]): Description of the prompt template
        tags (Dict[str, str]): Tags to attach to the prompt template
        #customer_encryption_key_arn (Optional[str]): ARN of KMS key for encryption
        
    Properties:
        variables: List of variable names found in the content
        prompt_id: Unique identifier of the prompt in Bedrock
        version: Current version of the prompt
    """
    
    name: str
    content: str
    description: Optional[str] = 'NA'
    tags: Dict[str, str] = field(default_factory=dict)
    #customer_encryption_key_arn: Optional[str] = None
    
    # Private fields
    _prompt_id: Optional[str] = field(default=None, init=False)
    _version: Optional[str] = field(default=None, init=False)
    _version_history: List[Dict] = field(default_factory=list, init=False)
    _client: Any = field(init=False)

    def __post_init__(self):
        """Initialize the Bedrock client and load any existing prompt"""
        self._client = boto3.client('bedrock-agent')
        self._load_existing_prompt()
        self._validate()

    @property
    def variables(self) -> List[str]:
        """Get list of variables in the prompt template"""
        return re.findall(r'\{\{(\w+)\}\}', self.content)

    @property
    def prompt_id(self) -> Optional[str]:
        """Get the prompt identifier"""
        return self._prompt_id
    
    @property
    def version(self) -> Optional[str]:
        """Get the current version"""
        return self._version

    def _validate(self):
        """Validate the prompt template configuration"""
        if not self.name or not self.content:
            raise ValueError("Name and content are required")
            
        # Validate tags if present
        if self.tags:
            if not all(isinstance(k, str) and isinstance(v, str) 
                      for k, v in self.tags.items()):
                raise ValueError("Tags must be string key-value pairs")

    def _load_existing_prompt(self):
        """Load existing prompt if it exists with the same name"""
        try:
            # List prompts to find one with matching name
            response = self._client.list_prompts()
            for prompt in response.get('promptSummaries', []):
                if prompt['name'] == self.name:
                    self._prompt_id = prompt['id']
                    # Get full prompt details
                    prompt_details = self._client.get_prompt(
                        promptIdentifier=self._prompt_id
                    )
                    self._version = prompt_details['version']
                    return
        except ClientError as e:
            raise Exception(f"Failed to check existing prompts: {str(e)}")

    def save(self) -> Tuple[str, str]:
        """
        Save the prompt template to Bedrock.
        Creates new prompt or updates existing one.
        
        Returns:
            Tuple[str, str]: Prompt ID and version
        """
        try:
            if not self._prompt_id:
                # Create new prompt
                response = self._client.create_prompt(
                    name=self.name,
                    description=self.description,
                    #customerEncryptionKeyArn=self.customer_encryption_key_arn,
                    tags=self.tags,
                    variants=[{
                        'name': f"{self.name}-variant",
                        'templateType': 'TEXT',
                        'templateConfiguration': {
                            'text': {
                                'text': self.content,
                                'inputVariables': [
                                    {'name': var} for var in self.variables
                                ]
                            }
                        }
                    }]
                )
                self._prompt_id = response['id']
                self._version = response['version']
            else:
                # Update existing prompt
                response = self._client.update_prompt(
                    promptIdentifier=self._prompt_id,
                    name=self.name,
                    description=self.description,
                    variants=[{
                        'name': f"{self.name}-variant",
                        'templateType': 'TEXT',
                        'templateConfiguration': {
                            'text': {
                                'text': self.content,
                                'inputVariables': [
                                    {'name': var} for var in self.variables
                                ]
                            }
                        }
                    }]
                )
                self._version = response['version']
                
            return self._prompt_id, self._version
            
        except ClientError as e:
            raise Exception(f"Failed to save prompt: {str(e)}")

    def create_version(self, description: Optional[str] = 'NA') -> str:
        """
        Create a new version of the prompt
        
        Args:
            description: Optional description for this version
            
        Returns:
            str: Version identifier
        """
        if not self._prompt_id:
            raise ValueError("Cannot create version - prompt not saved")
            
        try:
            response = self._client.create_prompt_version(
                promptIdentifier=self._prompt_id,
                description=description
            )
            self._version = response['version']
            self._version_history.append({
                'version': self._version,
                'content': self.content,
                'timestamp': datetime.now().isoformat()
            })
            return self._version
            
        except ClientError as e:
            raise Exception(f"Failed to create version: {str(e)}")

    def render(self, variables: Dict[str, str]) -> str:
        """
        Render template with variables in {{variable}} format
        
        Args:
            variables: Dictionary of variable names and values
            
        Returns:
            Rendered template with variables replaced
            
        Raises:
            ValueError: If required variables are missing
        """
        text = self.content
        
        # Find all required variables
        required_vars = set(re.findall(r'\{\{(\w+)\}\}', text))
        
        # Check for missing variables
        missing_vars = required_vars - set(variables.keys())
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        # Replace each {{variable}} with its value
        for var, value in variables.items():
            pattern = r'\{\{' + re.escape(var) + r'\}\}'
            text = re.sub(pattern, str(value), text)
        
        return text


    def delete(self):
        """Delete the prompt template from Bedrock"""
        if not self._prompt_id:
            return
            
        try:
            self._client.delete_prompt(
                promptIdentifier=self._prompt_id
            )
            self._prompt_id = None
            self._version = None
        except ClientError as e:
            raise Exception(f"Failed to delete prompt: {str(e)}")

    @classmethod
    def load(cls, prompt_id: str) -> "PromptTemplate":
        """
        Load a prompt template from Bedrock by ID
        
        Args:
            prompt_id: Prompt identifier
            
        Returns:
            PromptTemplate: Loaded template
        """
        client = boto3.client('bedrock-agent')
        try:
            response = client.get_prompt(
                promptIdentifier=prompt_id
            )
            
            variant = response['variants'][0]
            content = variant['templateConfiguration']['text']['text']
            
            return cls(
                name=response['name'],
                content=content,
                description=response.get('description'),
                tags=response.get('tags', {}),
                #customer_encryption_key_arn=response.get('customerEncryptionKeyArn')
            )
            
        except ClientError as e:
            raise Exception(f"Failed to load prompt: {str(e)}")


class FewShotTemplate:
    """Collection of few-shot examples using PromptTemplates"""
    def __init__(self, examples: List[Tuple[PromptTemplate, Dict[str, str]]]):
        """
        Args:
            examples: List of (prompt_template, variables) tuples
        """
        self.examples = examples
    
    def render(self) -> str:
        """Render all examples"""
        return "\n".join(
            template.render(variables) #template.render(variables) template.render(**variables)
            for template, variables in self.examples
        )