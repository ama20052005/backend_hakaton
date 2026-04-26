# app/services/llama_service.py
import httpx
import asyncio
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime

from app.config import settings
from app.core.logging import logger

try:
    from tenacity import retry, stop_after_attempt, wait_exponential
except ImportError:
    def retry(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    def stop_after_attempt(*args, **kwargs):
        return None

    def wait_exponential(*args, **kwargs):
        return None

class LlamaService:
    """Сервис для работы с LLaMA через Ollama API"""
    
    def __init__(self):
        self.ollama_url = f"{settings.OLLAMA_HOST}/api/generate"
        self.cache: Dict[str, Dict] = {}
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate(
        self,
        prompt: str,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        year: int = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Генерация ответа от LLaMA"""
        
        model = model or settings.DEFAULT_MODEL
        temperature = temperature or settings.LLAMA_TEMPERATURE
        max_tokens = max_tokens or settings.LLAMA_MAX_TOKENS
        
        # Кэширование
        cache_key = self._get_cache_key(prompt, model, year)
        
        if use_cache and cache_key in self.cache:
            logger.info(f"Cache hit for key: {cache_key[:50]}...")
            cached = self.cache[cache_key]
            return {
                "response": cached["response"],
                "cached": True,
                "model": model,
                "timestamp": cached["timestamp"]
            }
        
        # Запрос к LLaMA
        start_time = datetime.now()
        
        try:
            async with httpx.AsyncClient(timeout=settings.LLAMA_TIMEOUT) as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": model,
                        "prompt": prompt,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": False
                    }
                )
                response.raise_for_status()
                result = response.json()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            output = {
                "response": result.get("response", ""),
                "cached": False,
                "model": model,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
            # Сохраняем в кэш
            if use_cache:
                self.cache[cache_key] = output
            
            logger.info(f"LLaMA response generated in {processing_time:.2f}s")
            return output
            
        except httpx.TimeoutException:
            logger.error("LLaMA request timeout")
            return {
                "response": "Превышено время ожидания ответа от модели. Пожалуйста, попробуйте позже.",
                "error": "timeout",
                "cached": False,
                "model": model
            }
        except Exception as e:
            logger.error(f"LLaMA request failed: {e}")
            return {
                "response": f"Ошибка при обращении к LLaMA: {str(e)}",
                "error": str(e),
                "cached": False,
                "model": model
            }
    
    def _get_cache_key(self, prompt: str, model: str, year: int = None) -> str:
        """Генерирует ключ для кэша"""
        data = f"{prompt}_{model}_{year}"
        return hashlib.md5(data.encode()).hexdigest()
    
    async def analyze_with_context(
        self,
        question: str,
        context: str,
        year: int = 2024,
        model: str = None
    ) -> str:
        """Анализирует вопрос с предоставленным контекстом"""
        
        prompt = f"""Ты - эксперт по демографической статистике России.
        
КОНТЕКСТ ДАННЫХ (год: {year}):
{context}

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{question}

Пожалуйста, ответь на вопрос, используя предоставленные данные.
Будь точным, используй конкретные цифры из контекста.
Если данных недостаточно для полного ответа, укажи это.

ОТВЕТ:"""
        
        result = await self.generate(prompt, model=model, year=year)
        return result.get("response", "Не удалось получить ответ")

# Глобальный экземпляр
llama_service = LlamaService()
