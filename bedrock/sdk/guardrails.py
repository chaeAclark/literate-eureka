from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union, Any, Tuple
import boto3
from botocore.exceptions import ClientError
import json
import time


class ContentFilterType(Enum):
    """Types of content filters available"""
    SEXUAL = "SEXUAL"
    VIOLENCE = "VIOLENCE" 
    HATE = "HATE"
    INSULTS = "INSULTS"
    MISCONDUCT = "MISCONDUCT"
    PROMPT_ATTACK = "PROMPT_ATTACK"

class FilterStrength(Enum):
    """Filter strength levels"""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

@dataclass
class ContentFilter:
    """Configuration for a content filter"""
    filter_type: ContentFilterType
    input_strength: FilterStrength
    output_strength: FilterStrength


class GuardrailAction(Enum):
    """Possible guardrail actions"""
    NONE = "NONE"
    INTERVENED = "GUARDRAIL_INTERVENED"

@dataclass
class TopicAssessment:
    """Assessment results for a topic"""
    name: str
    detected: bool
    action: str

@dataclass
class ContentAssessment:
    """Assessment results for content filtering"""
    type: str
    confidence: str
    strength: str
    action: str

@dataclass
class PIIAssessment:
    """Assessment results for PII detection"""
    type: str
    matches: List[str]
    action: str

@dataclass
class UsageMetrics:
    """Usage metrics for guardrail processing"""
    topic_units: int
    content_units: int
    word_units: int
    sensitive_info_units: int
    sensitive_info_free_units: int
    contextual_grounding_units: int
    processing_latency: Optional[int] = None
    
    @classmethod
    def from_response(cls, usage: Dict[str, int], metrics: Optional[Dict] = None) -> 'UsageMetrics':
        return cls(
            topic_units=usage.get('topicPolicyUnits', 0),
            content_units=usage.get('contentPolicyUnits', 0),
            word_units=usage.get('wordPolicyUnits', 0),
            sensitive_info_units=usage.get('sensitiveInformationPolicyUnits', 0),
            sensitive_info_free_units=usage.get('sensitiveInformationPolicyFreeUnits', 0),
            contextual_grounding_units=usage.get('contextualGroundingPolicyUnits', 0),
            processing_latency=metrics.get('guardrailProcessingLatency') if metrics else None
        )

@dataclass
class GuardrailResult:
    """Structured result from guardrail application"""
    action: GuardrailAction
    output: str
    topics: List[TopicAssessment]
    usage: UsageMetrics
    original_response: Dict[str, Any]  # Keep original response for reference
    
    @classmethod
    def from_response(cls, response: Dict[str, Any]) -> 'GuardrailResult':
        # Extract output text
        outputs = response.get('outputs', [])
        output_text = outputs[0].get('text') if outputs else ""
        if isinstance(output_text, dict):
            output_text = output_text.get('text', "")
            
        # Process topic assessments
        topics = []
        for assessment in response.get('assessments', []):
            topic_policy = assessment.get('topicPolicy', {})
            for topic in topic_policy.get('topics', []):
                topics.append(TopicAssessment(
                    name=topic['name'],
                    detected=topic['action'] == 'BLOCKED',
                    action=topic['action']
                ))
                
        # Get metrics
        metrics = None
        for assessment in response.get('assessments', []):
            if 'invocationMetrics' in assessment:
                metrics = assessment['invocationMetrics']
                break
                
        return cls(
            action=GuardrailAction(response.get('action', 'NONE')),
            output=output_text,
            topics=topics,
            usage=UsageMetrics.from_response(response.get('usage', {}), metrics),
            original_response=response
        )
    
    def __str__(self) -> str:
        """Human-readable string representation"""
        lines = [
            f"Guardrail Action: {self.action.value}",
            f"Output: {self.output}",
            "\nTopic Assessments:"
        ]
        
        for topic in self.topics:
            lines.append(f"  - {topic.name}: {'Detected' if topic.detected else 'Not Detected'}")
            
        lines.extend([
            "\nUsage Metrics:",
            f"  Topic Units: {self.usage.topic_units}",
            f"  Content Units: {self.usage.content_units}",
            f"  Word Units: {self.usage.word_units}",
            f"  Sensitive Info Units: {self.usage.sensitive_info_units}"
        ])
        
        if self.usage.processing_latency:
            lines.append(f"  Processing Latency: {self.usage.processing_latency}ms")
            
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "action": self.action.value,
            "output": self.output,
            "topics": [
                {
                    "name": topic.name,
                    "detected": topic.detected,
                    "action": topic.action
                }
                for topic in self.topics
            ],
            "usage": {
                "topic_units": self.usage.topic_units,
                "content_units": self.usage.content_units,
                "word_units": self.usage.word_units,
                "sensitive_info_units": self.usage.sensitive_info_units,
                "processing_latency": self.usage.processing_latency
            }
        }

class PIIEntityType(Enum):
    """Enumeration of supported PII entity types"""
    ADDRESS = "ADDRESS"
    AGE = "AGE" 
    AWS_ACCESS_KEY = "AWS_ACCESS_KEY"
    AWS_SECRET_KEY = "AWS_SECRET_KEY"
    CA_HEALTH_NUMBER = "CA_HEALTH_NUMBER"
    CA_SOCIAL_INSURANCE_NUMBER = "CA_SOCIAL_INSURANCE_NUMBER"
    CREDIT_DEBIT_CARD_CVV = "CREDIT_DEBIT_CARD_CVV"
    CREDIT_DEBIT_CARD_EXPIRY = "CREDIT_DEBIT_CARD_EXPIRY"
    CREDIT_DEBIT_CARD_NUMBER = "CREDIT_DEBIT_CARD_NUMBER"
    DRIVER_ID = "DRIVER_ID"
    EMAIL = "EMAIL"
    NAME = "NAME"
    PHONE = "PHONE"
    SSN = "US_SOCIAL_SECURITY_NUMBER"
    # ... add other PII types as needed

class PIIAction(Enum):
    """Actions for PII detection"""
    BLOCK = "BLOCK"
    ANONYMIZE = "ANONYMIZE"

@dataclass
class TopicDefinition:
    """Definition of a topic for guardrails"""
    name: str
    definition: str
    examples: List[str]
    is_allowed_topic: bool = False  # If True, complement logic will be applied
    complement_message: Optional[str] = None

@dataclass
class GuardrailConfig:
    """Configuration for a guardrail"""
    name: str
    description: Optional[str] = None
    topics: List[TopicDefinition] = field(default_factory=list)
    pii_entities: List[Tuple[PIIEntityType, PIIAction]] = field(default_factory=list)
    content_filters: List[ContentFilter] = field(default_factory=list)
    blocked_input_message: str = "This input is not allowed."
    blocked_output_message: str = "This output is not allowed."
    
class Guardrail:
    """Manages guardrails for responsible AI"""
    
    def __init__(self, 
                 config: GuardrailConfig,
                 region_name: str = "us-east-1",
                 profile_name: Optional[str] = None):
        """
        Initialize guardrail
        
        Args:
            config: Guardrail configuration
            region_name: AWS region
            profile_name: AWS profile name
        """
        self.config = config
        session = boto3.Session(profile_name=profile_name)
        self.client = session.client('bedrock', region_name=region_name)
        self.runtime = session.client('bedrock-runtime', region_name=region_name)
        self._guardrail_id = None
        self._version = None

    def create(self) -> Tuple[str, str]:
        """Create guardrail in Bedrock"""
        try:
            # Create request parameters with required fields
            params = {
                "name": self.config.name,
                "description": self.config.description or "",
                "blockedInputMessaging": self.config.blocked_input_message,
                "blockedOutputsMessaging": self.config.blocked_output_message
            }

            # Add topic policy config if topics defined
            if self.config.topics:
                params["topicPolicyConfig"] = {
                    "topicsConfig": [
                        {
                            "name": topic.name,
                            "definition": topic.definition,
                            "examples": topic.examples,
                            "type": "DENY"
                        }
                        for topic in self.config.topics
                    ]
                }

            # Add content filter config if filters defined
            if self.config.content_filters:
                params["contentPolicyConfig"] = {
                    "filtersConfig": [
                        {
                            "type": filter.filter_type.value,
                            "inputStrength": filter.input_strength.value,
                            "outputStrength": filter.output_strength.value
                        }
                        for filter in self.config.content_filters
                    ]
                }

            # Add PII config if entities defined
            if self.config.pii_entities:
                params["sensitiveInformationPolicyConfig"] = {
                    "piiEntitiesConfig": [
                        {
                            "type": entity.value,
                            "action": action.value
                        }
                        for entity, action in self.config.pii_entities
                    ]
                }

            response = self.client.create_guardrail(**params)

            self._guardrail_id = response["guardrailId"]
            self._version = response["version"]
            
            return self._guardrail_id, self._version

        except ClientError as e:
            raise Exception(f"Failed to create guardrail: {str(e)}")

    def apply(self,
        content: Union[str, List[str]],
        source: str = "INPUT",
        qualifiers: Optional[List[str]] = None) -> GuardrailResult:
        """
        Apply guardrail to content
        
        Args:
            content: Text content to guard
            source: Whether checking input or output
            qualifiers: Optional qualifiers for the content
            
        Returns:
            GuardrailResult: Structured result object
        """
        if not self._guardrail_id:
            raise ValueError("Guardrail not created")
    
        # Format content
        if isinstance(content, str):
            content = [content]
            
        messages = []
        for i, text in enumerate(content):
            msg = {
                "text": {
                    "text": text
                }
            }
            if qualifiers and i < len(qualifiers):
                msg["text"]["qualifiers"] = [qualifiers[i]]
            messages.append(msg)
    
        try:
            response = self.runtime.apply_guardrail(
                guardrailIdentifier=self._guardrail_id,
                guardrailVersion=self._version,
                source=source,
                content=messages
            )
    
            # Handle complement logic for allowed topics
            for topic in self.config.topics:
                if topic.is_allowed_topic:
                    # Check if topic was detected (BLOCKED means topic was found)
                    topic_blocked = False
                    for assessment in response.get('assessments', []):
                        topic_policy = assessment.get('topicPolicy', {})
                        for assessed_topic in topic_policy.get('topics', []):
                            if assessed_topic['name'] == topic.name and assessed_topic['action'] == 'BLOCKED':
                                topic_blocked = True
                                break
    
                    if topic_blocked:
                        # Topic was detected, so we should ALLOW it
                        response['action'] = 'NONE'
                        response['outputs'] = messages  # Pass through original content
                    else:
                        # Topic was not detected, so we should BLOCK it
                        response['action'] = 'GUARDRAIL_INTERVENED'
                        response['outputs'] = [{'text': topic.complement_message}]
    
            return GuardrailResult.from_response(response)
    
        except ClientError as e:
            raise Exception(f"Failed to apply guardrail: {str(e)}")

    def delete(self):
        """Delete the guardrail"""
        if not self._guardrail_id:
            return
            
        try:
            self.client.delete_guardrail(
                guardrailIdentifier=self._guardrail_id
            )
            self._guardrail_id = None
            self._version = None
        except ClientError as e:
            raise Exception(f"Failed to delete guardrail: {str(e)}")