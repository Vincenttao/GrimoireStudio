import json
from typing import List, Dict, Any
from openai import AsyncOpenAI
from app.core.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential

class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_beat(self, prompt: str) -> Dict[str, Any]:
        """
        Calls LLM and returns the parsed JSON.
        """
        response = await self.client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a story generation assistant. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        content = response.choices[0].message.content
        return json.loads(content)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def smooth_transition(self, prev_text: str, next_text: str) -> str:
        """
        Calls LLM to smooth the transition between blocks.
        """
        prompt = f"Rewrite the first sentence of this text to flow naturally from the previous paragraph.\n\nPREVIOUS: {prev_text}\n\nTARGET: {next_text}\n\nReturn ONLY the rewritten text."
        
        response = await self.client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional editor."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()

llm_service = LLMService()