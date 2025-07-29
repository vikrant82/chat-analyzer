import asyncio
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional

import google.generativeai as genai
from google.generativeai.types import generation_types

from .base_llm import LLMClient
from .prompts import UNIFIED_SYSTEM_PROMPT, GENERAL_AI_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

DEPRECATED_GOOGLE_MODELS = {"gemini-1.0-pro-vision-latest"}

class GoogleAILLM(LLMClient):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = self.config.get('api_key')
        self.available_models = []
        if self.api_key:
            genai.configure(api_key=self.api_key)

    async def initialize_models(self) -> None:
        if not self.api_key:
            logger.warning("Google AI API key not configured. Models will be unavailable.")
            return
        try:
            logger.info("Asynchronously listing Google AI models...")
            models_iterator = await asyncio.to_thread(genai.list_models)
            supported_models = []
            for m in models_iterator:
                model_name = m.name.replace("models/", "")
                if 'generateContent' in m.supported_generation_methods and model_name not in DEPRECATED_GOOGLE_MODELS:
                    supported_models.append(model_name)
            self.available_models = sorted(supported_models)
            logger.info(f"Discovered usable Google AI models: {self.available_models}")
        except Exception as e:
            logger.error(f"Failed to list models from Google AI: {e}", exc_info=True)
            self.available_models = []

    def get_available_models(self) -> List[str]:
        return self.available_models

    def get_default_model(self) -> Optional[str]:
        return self.config.get("default_model")

    async def call_conversational(
        self,
        model_name: str,
        conversation: List[Dict[str, Any]],
        original_messages: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        if model_name not in self.available_models:
            logger.error(f"Attempted to use unconfigured or filtered Google AI model: {model_name}")
            yield f"Error: Invalid, unavailable, or filtered Google AI model selected: {model_name}"
            return

        logger.info(f"Streaming conversational response from Google AI ({model_name})...")
        try:
            history = []
            system_instruction = None

            if original_messages:
                # Summarizer Mode: The original_messages now contain the full, structured history
                system_instruction = UNIFIED_SYSTEM_PROMPT
                history.extend(original_messages)
                # Add the user's latest query from the conversation object
                if conversation:
                    history.append(conversation[-1])
            else:
                # AI Mode: The conversation object contains the history
                system_instruction = GENERAL_AI_SYSTEM_PROMPT
                history.extend(conversation)

            # Convert our standard format to Google's format
            google_history = []
            for msg in history:
                role = "model" if msg["role"] == "assistant" else msg["role"]
                
                # The content can be a list of parts (text/image) or a simple string
                content = msg.get("content", "")
                if isinstance(content, str):
                    google_history.append({'role': role, 'parts': [{'text': content}]})
                elif isinstance(content, list):
                    parts = []
                    for part in content:
                        if part['type'] == 'text':
                            parts.append({'text': part['text']})
                        elif part['type'] == 'image':
                            source = part['source']
                            parts.append({
                                'inline_data': {
                                    'mime_type': source['media_type'],
                                    'data': source['data']
                                }
                            })
                    google_history.append({'role': role, 'parts': parts})

            model = genai.GenerativeModel(
                f"models/{model_name}",
                system_instruction=system_instruction
            )
            
            # The last message is sent as the new content, the rest is history
            last_message_parts = google_history.pop()['parts'] if google_history else []
            
            chat = model.start_chat(history=google_history)
            response_stream = await chat.send_message_async(
                content=last_message_parts,
                stream=True
            )

            async for chunk in response_stream:
                try:
                    if chunk.text:
                        yield chunk.text
                except ValueError:
                    logger.warning("A chunk was blocked by Google AI safety settings.")
                    yield "[Content-Blocked-By-AI]"
                except Exception as e:
                    logger.error(f"Error processing a streaming chunk from Google AI: {e}", exc_info=True)
                    yield f"[Error-Processing-Chunk: {e}]"

        except Exception as e:
            logger.error(f"Error calling Google AI streaming API ({model_name}): {e}", exc_info=True)
            yield f"\n\n**Error:** Failed to get a streaming response from the Google AI service. Details: {str(e)}"
