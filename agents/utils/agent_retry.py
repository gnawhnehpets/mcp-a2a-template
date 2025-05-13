import asyncio
import logging
from google.generativeai.types import GenerateContentResponse
from google.generativeai.client import GenerativeModel
from google.generativeai.errors import ClientError

logger = logging.getLogger(__name__)

async def call_llm_with_retry(
    model: GenerativeModel,
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
            # Assuming the first positional argument to model.generate_content_async
            # will be the 'contents' (e.g., a prompt string or list of Contents)
            # and other specific params like 'tools', 'tool_config' are in kwargs.
            return await model.generate_content_async(*args, **kwargs)
        except ClientError as e:
            logger.warning(f"LLM call failed (attempt {attempt}/{max_attempts}): {e}")
            if e.reason == "RESOURCE_EXHAUSTED" and attempt < max_attempts:
                # Attempt to parse retryDelay, e.g., "7s"
                retry_delay_str = "7s" # Default
                if e.error and e.error.get("details"):
                    for detail in e.error["details"]:
                        if detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                            retry_delay_str = detail.get("retryDelay", "7s")
                            break
                
                try:
                    delay_seconds = int(retry_delay_str.rstrip("s"))
                except ValueError:
                    logger.error(f"Could not parse retryDelay: {retry_delay_str}. Defaulting to 7s.")
                    delay_seconds = 7
                
                logger.info(f"Retrying LLM call in {delay_seconds} seconds...")
                await asyncio.sleep(delay_seconds)
                attempt += 1
                continue
            else:
                logger.error(f"LLM call failed permanently after {attempt} attempts or due to non-retriable error.")
                raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during LLM call: {e}")
            raise

# ADK Integration for retry
from google.adk.models import GoogleLLM
from google.adk.models.llm import LLMResponse, LLMRequest
from typing import AsyncIterable

class RetryableGoogleLLM(GoogleLLM):
    """
    A GoogleLLM wrapper that adds retry logic to its calls.
    """
    async def generate_content_async(
        self,
        request: LLMRequest,
        timeout_seconds: int | None = None, # Match signature of base
    ) -> AsyncIterable[LLMResponse]:
        """
        Calls the LLM with retry logic for non-streaming.
        For streaming, retry logic would be more complex and is not implemented here.
        This override assumes non-streaming for simplicity with call_llm_with_retry.
        ADK's GoogleLLM internally handles streaming differently.
        A more robust solution would properly handle the AsyncIterable nature.
        
        NOTE: This is a simplified override. The base GoogleLLM's 
        generate_content_async returns an AsyncIterable[LLMResponse].
        Our current call_llm_with_retry expects a single GenerateContentResponse.
        This will need careful adaptation if streaming is used by the Agent.
        For now, we assume the agent's usage pattern results in a single response or
        can be adapted to work with a single aggregated response if streaming was intended.
        """
        # This is where it gets tricky. call_llm_with_retry is designed for a single
        # GenerateContentResponse, but GoogleLLM.generate_content_async returns an
        # AsyncIterable[LLMResponse].
        #
        # If the agent primarily uses non-streaming calls that effectively yield one LLMResponse,
        # we might be able to adapt.
        #
        # A more direct approach for non-streaming:
        # The `request` object in ADK's `GoogleLLM` is an `LLMRequest`.
        # We need to adapt this to what `call_llm_with_retry` expects for `GenerativeModel`.
        # `call_llm_with_retry` expects `model.generate_content_async(contents, **kwargs)`
        
        # This simplified version won't correctly handle streaming from the ADK perspective.
        # It assumes that the underlying call pattern for the agent can be treated as a single call.
        # A full solution would need to wrap the async iterator itself.

        # Let's assume for now the agent's usage pattern with this LLM
        # is primarily for single, non-streamed full responses.
        # The `contents` for `GenerativeModel` would come from `request.contents`.
        # Other parameters like `tools`, `tool_config` are in `request.tool_config`, `request.tools`.

        generative_model_instance = self._model # Access the underlying GenerativeModel

        # Adapt LLMRequest to arguments for GenerativeModel.generate_content_async
        # The `*args` for call_llm_with_retry should be `request.contents`
        # The `**kwargs` for call_llm_with_retry should include `tools`, `tool_config`, etc.
        
        genai_kwargs = {}
        if request.tools:
            genai_kwargs['tools'] = request.tools
        if request.tool_config:
            genai_kwargs['tool_config'] = request.tool_config
        if request.safety_settings:
            genai_kwargs['safety_settings'] = request.safety_settings
        # Add other relevant parameters from LLMRequest to genai_kwargs if needed

        try:
            # This is the part that needs to align with call_llm_with_retry's expectation
            # of a single GenerateContentResponse, not an AsyncIterable.
            # This will likely break if the agent expects streaming.
            # For a non-streaming scenario that ADK might abstract:
            response: GenerateContentResponse = await call_llm_with_retry(
                model=generative_model_instance,
                contents=request.contents, # This is the primary argument
                generation_config=request.generation_config, # Pass generation_config
                safety_settings=request.safety_settings,
                tools=request.tools,
                tool_config=request.tool_config
                # Pass other relevant kwargs from LLMRequest if necessary
            )
            # Now, convert this single GenerateContentResponse back to an AsyncIterable[LLMResponse]
            # containing one item. This is a simplification.
            async def _response_stream():
                yield LLMResponse(
                    contents=[response.parts] if response.parts else [], 
                    candidates=response.candidates,
                    prompt_feedback=response.prompt_feedback,
                    usage_metadata=response.usage_metadata
                    )
            yield LLMResponse(
                contents=[part for part in response.parts] if response.parts else [],
                candidates=response.candidates,
                prompt_feedback=response.prompt_feedback,
                usage_metadata=response.usage_metadata
            )

        except Exception as e:
            logger.error(f"Error in RetryableGoogleLLM.generate_content_async: {e}")
            # Need to yield an LLMResponse that indicates an error or raise appropriately
            # For simplicity, re-raising. A real implementation would yield an error LLMResponse.
            raise
