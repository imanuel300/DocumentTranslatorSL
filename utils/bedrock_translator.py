import json
import logging
import boto3
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class BedrockTranslator:
    """Handles translation requests using AWS Bedrock's Claude model"""
    
    def __init__(self):
        """Initialize the Bedrock client"""
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-east-1'
        )
        
        # Language codes mapping for better prompting
        self.language_names = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'nl': 'Dutch',
            'pl': 'Polish',
            'ru': 'Russian',
            'ja': 'Japanese',
            'zh': 'Chinese',
            'ko': 'Korean'
        }
        
    def translate_text(self, 
                      text: str, 
                      source_lang: str, 
                      target_lang: str, 
                      context: Optional[str] = None) -> str:
        """
        Translate text using AWS Bedrock's Claude model
        
        Args:
            text (str): Text to translate
            source_lang (str): Source language code
            target_lang (str): Target language code
            context (str, optional): Additional context for translation
            
        Returns:
            str: Translated text
            
        Raises:
            TranslationError: If translation fails
        """
        try:
            source_name = self.language_names.get(source_lang, source_lang)
            target_name = self.language_names.get(target_lang, target_lang)
            
            # Construct prompt with context if provided
            context_str = f"\nContext: {context}" if context else ""
            
            prompt = f"""You are a professional translator. Translate the following text from {source_name} to {target_name}.
            Maintain the same tone, style, and formatting of the original text.
            Only return the translated text without any additional comments or explanations.
            
            Original text ({source_name}):
            "{text}"{context_str}
            
            Translation ({target_name}):"""

            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                body=json.dumps({
                    "prompt": prompt,
                    "max_tokens": 4096,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "stop_sequences": ["\n\n"]
                })
            )
            
            response_body = json.loads(response['body'].read())
            translated_text = response_body['completion'].strip()
            
            # Remove quotes if they were included in the response
            translated_text = translated_text.strip('"')
            
            return translated_text

        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            raise TranslationError(f"Failed to translate text: {str(e)}")
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get dictionary of supported language codes and names
        
        Returns:
            Dict[str, str]: Dictionary mapping language codes to names
        """
        return self.language_names
    
    def validate_language_pair(self, source_lang: str, target_lang: str) -> bool:
        """
        Validate if a language pair is supported
        
        Args:
            source_lang (str): Source language code
            target_lang (str): Target language code
            
        Returns:
            bool: True if language pair is supported
        """
        return (source_lang in self.language_names and 
                target_lang in self.language_names and 
                source_lang != target_lang)

class TranslationError(Exception):
    """Custom exception for translation errors"""
    pass
