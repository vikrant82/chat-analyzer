import json
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional

import httpx

from .base_llm import LLMClient
from .prompts import (
    QUESTION_SYSTEM_PROMPT,
    QUESTION_USER_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_PROMPT,
)

logger = logging.getLogger(__name__)

class LMStudioLLM(LLMClient):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.url = self.config.get('url')
        self.available_models = []

    async def initialize_models(self) -> None:
        if not self.url:
            logger.warning("LM Studio URL not configured. Models will not be available.")
            return

        models_url = self.url.replace('/v1/chat/completions', '/v1/models')
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                logger.info(f"Fetching LM Studio models from: {models_url}")
                response = await client.get(models_url)
                response.raise_for_status()
                models_data = response.json()
                model_ids = [model['id'] for model in models_data.get('data', []) if 'id' in model]
                self.available_models = sorted(list(set(model_ids)))
                if self.available_models:
                    logger.info(f"Discovered LM Studio models: {self.available_models}")
                else:
                    logger.warning("LM Studio query successful but no models found.")
        except Exception as e:
            logger.error(f"Failed to fetch LM Studio models from {models_url}: {e}", exc_info=True)
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
            logger.error(f"Attempted to use unconfigured LM Studio model: {model_name}")
            yield f"Error: Invalid or unconfigured LM Studio model selected: {model_name}"
            return

        if not self.url:
            logger.error(f"LM Studio URL not available/configured when trying to stream model {model_name}")
            yield "Error: LM Studio provider URL not configured on the server."
            return

        chat_completions_url = self.url
        logger.info(f"Streaming from LM Studio ({model_name}) for {'question answering' if question else 'summarization'}...")

        if question:
            system_content = QUESTION_SYSTEM_PROMPT
            user_content = QUESTION_USER_PROMPT.format(
                start_date_str=start_date_str,
                end_date_str=end_date_str,
                text_to_summarize=text_to_summarize,
                question=question
            )
        else:
            system_content = SUMMARY_SYSTEM_PROMPT
            user_content = SUMMARY_USER_PROMPT.format(
                start_date_str=start_date_str,
                end_date_str=end_date_str,
                text_to_summarize=text_to_summarize
            )

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "system", "content": "/nothink"},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.7,
            "stream": True
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream("POST", chat_completions_url, json=payload) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"LM Studio service returned error {response.status_code}: {error_text.decode()}")
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
                                logger.warning(f"Could not decode JSON from LM Studio stream: {line_content}")
                            except (KeyError, IndexError):
                                logger.warning(f"Unexpected structure in LM Studio stream chunk: {line_content}")
        except httpx.TimeoutException:
            logger.error(f"Request to LM Studio ({model_name}) timed out.")
            yield "\n\n**Error:** Request to the language model timed out."
        except Exception as e:
            logger.error(f"Error streaming from LM Studio ({model_name}): {e}", exc_info=True)
            yield f"\n\n**Error:** Failed to get a streaming response from the LM Studio service. Details: {str(e)}"
