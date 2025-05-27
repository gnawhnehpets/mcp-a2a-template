import asyncio
import logging
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from typing import AsyncGenerator, Optional
from google.adk.models.registry import LLMRegistry
from google.adk.models.base_llm import BaseLlm
from google.generativeai.types import GenerateContentResponse
from google.api_core import exceptions as google_api_exceptions
import asyncio
import logging

logger = logging.getLogger(__name__)

async def call_llm_with_retry(
    model: BaseLlm,
    *args,
    max_attempts: int = 3,
    **kwargs
) -> GenerateContentResponse:
    """
    Calls a Google LLM's generate_content_async method with retry and backoff.
    """
    attempt = 1
    while True:
        try:
            return await model.generate_content_async(*args, **kwargs)
        except google_api_exceptions.ResourceExhausted as e:
            logger.warning(f"LLM call failed with ResourceExhausted (attempt {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                delay_seconds = 7
                logger.info(f"Retrying LLM call in {delay_seconds} seconds due to ResourceExhausted...")
                await asyncio.sleep(delay_seconds)
                attempt += 1
                continue
            else:
                logger.error(f"LLM call failed permanently after {attempt} attempts due to ResourceExhausted.")
                raise
        except google_api_exceptions.GoogleAPIError as e:
            logger.error(f"LLM call failed with GoogleAPIError (attempt {attempt}/{max_attempts}): {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during LLM call (attempt {attempt}/{max_attempts}): {e}")
            raise

class RetryableGeminiLlm(BaseLlm):
    """
    Subclass of the Gemini LLM that adds retry logic to generate_content_async.
    """
    model: str

    async def generate_content_async(
        self,
        request: LlmRequest,
        timeout_seconds: Optional[int] = None,
        stream: bool = False,
    ) -> AsyncGenerator[LlmResponse, None]:
        """
        Calls the Gemini LLM with retry logic.
        """
        response = await call_llm_with_retry(
            self,
            request,
            timeout_seconds=timeout_seconds,
            stream=stream,
        )
        # Yield a single LlmResponse as async generator
        yield LlmResponse(
            contents=[part for part in response.parts] if response.parts else [],
            candidates=response.candidates,
            prompt_feedback=response.prompt_feedback,
            usage_metadata=response.usage_metadata,
        )
