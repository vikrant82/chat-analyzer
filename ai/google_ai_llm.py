import asyncio
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional

import google.generativeai as genai
from google.generativeai.types import generation_types

from .base_llm import LLMClient
from .prompts import GOOGLE_AI_QUESTION_PROMPT, GOOGLE_AI_SUMMARY_PROMPT

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

    async def call_streaming(
        self,
        model_name: str,
        text_to_summarize: str,
        start_date_str: str,
        end_date_str: str,
        question: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        if model_name not in self.available_models:
            logger.error(f"Attempted to use unconfigured or filtered Google AI model: {model_name}")
            yield f"Error: Invalid, unavailable, or filtered Google AI model selected: {model_name}"
            return

        logger.info(f"Streaming from Google AI ({model_name}) for {'question answering' if question else 'summarization'}...")
        try:
            full_model_name = f"models/{model_name}"
            model = genai.GenerativeModel(full_model_name)
            generation_config = genai.types.GenerationConfig(temperature=0.7, top_p=0.9, top_k=40)
            safety_settings = {}

            if question:
                prompt = GOOGLE_AI_QUESTION_PROMPT.format(
                    start_date_str=start_date_str,
                    end_date_str=end_date_str,
                    text_to_summarize=text_to_summarize,
                    question=question
                )
            else:
                prompt = GOOGLE_AI_SUMMARY_PROMPT.format(
                    start_date_str=start_date_str,
                    end_date_str=end_date_str,
                    text_to_summarize=text_to_summarize
                )

            response_stream = await model.generate_content_async(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings,
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
