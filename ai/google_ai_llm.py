import asyncio
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional

import google.generativeai as genai
from google.generativeai.types import generation_types

from .base_llm import LLMClient
from .prompts import UNIFIED_SYSTEM_PROMPT

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
        conversation: List[Dict[str, str]],
        original_messages: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        if model_name not in self.available_models:
            logger.error(f"Attempted to use unconfigured or filtered Google AI model: {model_name}")
            yield f"Error: Invalid, unavailable, or filtered Google AI model selected: {model_name}"
            return

        logger.info(f"Streaming conversational response from Google AI ({model_name})...")
        try:
            full_model_name = f"models/{model_name}"
            model = genai.GenerativeModel(full_model_name)
            generation_config = genai.types.GenerationConfig(temperature=0.7, top_p=0.9, top_k=40)
            safety_settings = {}

            # The first message is now the system prompt, subsequent are the conversation
            system_prompt = UNIFIED_SYSTEM_PROMPT.format(text_to_summarize=original_messages)
            
            history = []
            # Add all but the last message to history
            if len(conversation) > 1:
                for msg in conversation[:-1]:
                    history.append({'role': msg['role'], 'parts': [{'text': msg['content']}]})

            # The last message is the one we want the model to respond to
            last_message = conversation[-1]['content'] if conversation else ""
            
            # Prepend the system prompt to the last message for context
            full_prompt = f"{system_prompt}\n\n{last_message}"

            model_with_history = model.start_chat(history=history)

            response_stream = await model_with_history.send_message_async(
                full_prompt,
                stream=True
            )

            async for chunk in response_stream:
                try:
                    if chunk.text:
                        yield chunk.text
                except ValueError:
                    logger.warning(f"A chunk was blocked by Google AI safety settings. Full response may be incomplete.")
                    yield "[Content-Blocked-By-AI]"
                except Exception as e:
                    logger.error(f"Error processing a streaming chunk from Google AI: {e}", exc_info=True)
                    yield f"[Error-Processing-Chunk: {e}]"

        except Exception as e:
            logger.error(f"Error calling Google AI streaming API ({model_name}): {e}", exc_info=True)
            yield f"\n\n**Error:** Failed to get a streaming response from the Google AI service. Details: {str(e)}"
