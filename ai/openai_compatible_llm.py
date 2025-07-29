import json
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional

import httpx

from .base_llm import LLMClient
from .prompts import UNIFIED_SYSTEM_PROMPT, GENERAL_AI_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class OpenAICompatibleLLM(LLMClient):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.url = self.config.get('url')
        self.api_key = self.config.get('api_key')
        self.available_models = []

    async def initialize_models(self) -> None:
        if not self.url:
            logger.warning("OpenAI-compatible URL not configured. Models will not be available.")
            return

        models_url = self.url.replace('/v1/chat/completions', '/v1/models')
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=10, headers=headers) as client:
                logger.info(f"Fetching OpenAI-compatible models from: {models_url}")
                response = await client.get(models_url)
                response.raise_for_status()
                models_data = response.json()
                model_ids = [model['id'] for model in models_data.get('data', []) if 'id' in model]
                self.available_models = sorted(list(set(model_ids)))
                if self.available_models:
                    logger.info(f"Discovered OpenAI-compatible models: {self.available_models}")
                else:
                    # Not all endpoints support /v1/models, so we can use the default as a fallback
                    default_model = self.get_default_model()
                    if default_model:
                        logger.warning(f"Model discovery from {models_url} failed or returned no models. Using configured default model: {default_model}")
                        self.available_models = [default_model]
                    else:
                        logger.warning("OpenAI-compatible query successful but no models found and no default is set.")
        except Exception as e:
            default_model = self.get_default_model()
            if default_model:
                logger.warning(f"Could not fetch models from {models_url} due to error: {e}. Using configured default model: {default_model}")
                self.available_models = [default_model]
            else:
                logger.error(f"Failed to fetch OpenAI-compatible models from {models_url} and no default model configured: {e}", exc_info=True)
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
            logger.error(f"Attempted to use unconfigured OpenAI-compatible model: {model_name}")
            yield f"Error: Invalid or unconfigured OpenAI-compatible model selected: {model_name}"
            return

        if not self.url:
            logger.error(f"OpenAI-compatible URL not available/configured when trying to stream model {model_name}")
            yield "Error: OpenAI-compatible provider URL not configured on the server."
            return

        chat_completions_url = self.url
        logger.info(f"Streaming conversational response from OpenAI-compatible endpoint ({model_name})...")

        if original_messages:
            # Summarizer mode
            system_prompt = UNIFIED_SYSTEM_PROMPT
            user_prompt = f"Here is the chat history:\n---\n{original_messages}\n---"
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}] + conversation
        else:
            # AI mode
            system_prompt = GENERAL_AI_SYSTEM_PROMPT
            messages = [{"role": "system", "content": system_prompt}] + conversation

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "stream": True
        }

        try:
            async with httpx.AsyncClient(timeout=180.0, headers=headers) as client:
                async with client.stream("POST", chat_completions_url, json=payload) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"OpenAI-compatible service returned error {response.status_code}: {error_text.decode()}")
                        yield f"\n\n**Error:** Language model service error ({response.status_code})."
                        return

                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            line_content = line[6:]
                            if line_content.strip() == '[DONE]':
                                break
                            try:
                                chunk_data = json.loads(line_content)
                                if chunk_data['choices'][0]['delta'].get('content'):
                                    yield chunk_data['choices'][0]['delta']['content']
                            except json.JSONDecodeError:
                                logger.warning(f"Could not decode JSON from OpenAI-compatible stream: {line_content}")
                            except (KeyError, IndexError):
                                logger.warning(f"Unexpected structure in OpenAI-compatible stream chunk: {line_content}")
        except httpx.TimeoutException:
            logger.error(f"Request to OpenAI-compatible endpoint ({model_name}) timed out.")
            yield "\n\n**Error:** Request to the language model timed out."
        except Exception as e:
            logger.error(f"Error streaming from OpenAI-compatible endpoint ({model_name}): {e}", exc_info=True)
            yield f"\n\n**Error:** Failed to get a streaming response from the OpenAI-compatible service. Details: {str(e)}"
