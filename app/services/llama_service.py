import httpx
import asyncio
import hashlib
import json
from typing import Optional, Dict, Any, List
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
    
    async def generate_forecast(
        self,
        historical_data: List[Dict],
        years_ahead: int,
        region_name: str = "Россия",
        model: str = None
    ) -> Dict[str, Any]:
        """
        Использует LLaMA для генерации прогноза численности населения
        
        Args:
            historical_data: Список словарей с ключами 'year' и 'value'
            years_ahead: Количество лет для прогноза (5-15)
            region_name: Название региона
            model: Модель LLaMA
        """
        
        # Формируем исторические данные для промпта
        years = [item['year'] for item in historical_data]
        values = [item['value'] for item in historical_data]
        
        # Создаем детальный промпт для LLaMA
        prompt = f"""Ты - эксперт по демографическому прогнозированию. Проанализируй исторические данные о численности населения и сделай прогноз на {years_ahead} лет вперед.

РЕГИОН: {region_name}

ИСТОРИЧЕСКИЕ ДАННЫЕ (год: население):
"""
        for year, value in zip(years, values):
            prompt += f"{year}: {value:,} человек\n"
        
        # Добавляем расчет тренда
        if len(values) >= 2:
            total_change = values[-1] - values[0]
            years_span = years[-1] - years[0]
            avg_annual_change = total_change / years_span if years_span > 0 else 0
            avg_growth_rate = (avg_annual_change / values[0]) * 100 if values[0] > 0 else 0
            
            prompt += f"""
СТАТИСТИЧЕСКИЙ АНАЛИЗ:
- Период: {years[0]}-{years[-1]} гг. ({years_span} лет)
- Абсолютное изменение: {total_change:+,} человек
- Среднегодовое изменение: {avg_annual_change:+,.0f} человек
- Средний темп роста: {avg_growth_rate:+.2f}% в год
- Последнее значение ({years[-1]}): {values[-1]:,} человек

"""

        prompt += f"""
ЗАДАНИЕ:
Сделай прогноз численности населения на {years_ahead} лет вперед (до {years[-1] + years_ahead} года).

ОТВЕТЬ СТРОГО В СЛЕДУЮЩЕМ JSON-ФОРМАТЕ (без лишнего текста, только JSON):

{{
    "methodology": "краткое описание метода прогнозирования (2-3 предложения)",
    "forecast_type": "оптимистичный/пессимистичный/реалистичный",
    "reasoning": "обоснование прогноза (3-5 предложений с факторами влияния)",
    "forecast_years": [
        {{"year": ГОД, "value": ЧИСЛО, "confidence_lower": НИЖНЯЯ_ГРАНИЦА, "confidence_upper": ВЕРХНЯЯ_ГРАНИЦА}},
        ...
    ],
    "total_change": ОБЩЕЕ_ИЗМЕНЕНИЕ_ЗА_ПЕРИОД,
    "total_change_percent": ПРОЦЕНТ_ИЗМЕНЕНИЯ,
    "annual_growth_rate": СРЕДНЕГОДОВОЙ_ТЕМП_РОСТА_В_ПРОЦЕНТАХ,
    "risks": ["риск 1", "риск 2"],
    "recommendations": ["рекомендация 1", "рекомендация 2"]


ВАЖНЫЕ ПРАВИЛА:
1. Численность населения должна быть реалистичной (не может быть отрицательной)
2. Учитывай демографические тренды: рождаемость, смертность, миграцию
3. Для России учитывай: естественную убыль, миграционный прирост, старение населения
4. Доверительные интервалы должны расширяться с каждым годом
5. Ответь ТОЛЬКО JSON, без пояснений до или после

ПРОГНОЗ:"""

        try:
            result = await self.generate(
                prompt=prompt,
                model=model,
                temperature=0.3,  # Низкая температура для более точных прогнозов
                max_tokens=2000,
                use_cache=False  # Не кэшируем прогнозы
            )
            
            response_text = result.get("response", "")
            
            # Пытаемся извлечь JSON из ответа
            try:
                # Ищем JSON в ответе
                import re
                json_match = re.search(r'\{.*\}$', response_text, re.DOTALL)
                if json_match:
                    forecast_data = json.loads(json_match.group())
                else:
                    forecast_data = json.loads(response_text)
                
                # Валидируем прогноз
                if 'forecast_years' in forecast_data and len(forecast_data['forecast_years']) == years_ahead:
                    # Округляем значения
                    for item in forecast_data['forecast_years']:
                        item['value'] = max(0, int(item['value']))
                        if 'confidence_lower' in item:
                            item['confidence_lower'] = max(0, int(item['confidence_lower']))
                        if 'confidence_upper' in item:
                            item['confidence_upper'] = int(item['confidence_upper'])
                    
                    # Добавляем метаданные
                    forecast_data['model_used'] = model or settings.DEFAULT_MODEL
                    forecast_data['generated_at'] = datetime.now().isoformat()
                    forecast_data['success'] = True
                    
                    return forecast_data
                else:
                    # Если JSON некорректен, создаем fallback прогноз
                    return self._create_fallback_forecast(years, values, years_ahead, region_name)
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLaMA forecast JSON: {e}")
                logger.debug(f"Raw response: {response_text[:500]}")
                return self._create_fallback_forecast(years, values, years_ahead, region_name)
                
        except Exception as e:
            logger.error(f"LLaMA forecast generation failed: {e}")
            return self._create_fallback_forecast(years, values, years_ahead, region_name)
    
    def _create_fallback_forecast(self, years: List[int], values: List[int], years_ahead: int, region_name: str) -> Dict:
        """Создает fallback прогноз на основе линейной регрессии (если LLaMA недоступен)"""
        import numpy as np
        from sklearn.linear_model import LinearRegression
        
        X = np.array(years).reshape(-1, 1)
        y = np.array(values)
        
        model = LinearRegression()
        model.fit(X, y)
        
        last_year = years[-1]
        forecast_years = list(range(last_year + 1, last_year + years_ahead + 1))
        forecast_values = model.predict(np.array(forecast_years).reshape(-1, 1))
        
        residuals = y - model.predict(X)
        std_residuals = np.std(residuals)
        confidence_interval = 1.96 * std_residuals
        
        forecast_list = []
        for i, year in enumerate(forecast_years):
            value = max(0, int(forecast_values[i]))
            forecast_list.append({
                "year": year,
                "value": value,
                "confidence_lower": max(0, int(forecast_values[i] - confidence_interval)),
                "confidence_upper": int(forecast_values[i] + confidence_interval)
            })
        
        total_change = forecast_list[-1]['value'] - values[-1]
        total_change_percent = (total_change / values[-1]) * 100 if values[-1] > 0 else 0
        annual_growth_rate = ((forecast_list[-1]['value'] / values[-1]) ** (1 / years_ahead) - 1) * 100 if values[-1] > 0 else 0
        
        return {
            "success": True,
            "methodology": "Линейная регрессия (LLaMA недоступна, использован fallback метод)",
            "forecast_type": "реалистичный",
            "reasoning": f"Прогноз построен на основе экстраполяции исторического тренда за {years[0]}-{years[-1]} гг.",
            "forecast_years": forecast_list,
            "total_change": total_change,
            "total_change_percent": round(total_change_percent, 2),
            "annual_growth_rate": round(annual_growth_rate, 2),
            "risks": ["Демографические изменения", "Экономические факторы", "Миграционные потоки"],
            "recommendations": [
                "Мониторинг демографических показателей",
                "Адаптация социальной политики",
                "Развитие инфраструктуры"
            ],
            "model_used": "linear_regression_fallback",
            "generated_at": datetime.now().isoformat(),
            "llama_unavailable": True
        }
    
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