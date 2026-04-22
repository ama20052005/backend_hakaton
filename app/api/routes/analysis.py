from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Tuple
import re

from app.services.llama_service import llama_service
from app.services.data_service import data_service

router = APIRouter(prefix="/analysis", tags=["analysis"])

class QueryRequest(BaseModel):
    prompt: str
    model: str = "llama3.2:3b"
    temperature: float = 0.2
    max_tokens: int = 300
    year: int = 2024
    use_cache: bool = True

class QueryResponse(BaseModel):
    answer: str
    model_used: str
    year_used: int
    processing_time: float
    timestamp: datetime
    cached: bool = False


def extract_two_years(prompt: str) -> Tuple[Optional[int], Optional[int]]:
    """Извлекает два года из вопроса (например, 'с 2012 по 2024')"""
    patterns = [
        r'с\s+(\d{4})\s+по\s+(\d{4})',
        r'между\s+(\d{4})\s+и\s+(\d{4})',
        r'(\d{4})\s+-\s+(\d{4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None, None


def extract_single_year(prompt: str) -> Optional[int]:
    """Извлекает один год из вопроса"""
    years = re.findall(r'\b(20[0-2][0-9])\b', prompt)
    for y in years:
        year = int(y)
        if 2012 <= year <= 2024:
            return year
    return None


def extract_region_from_prompt(prompt: str) -> Optional[str]:
    """Извлекает название региона из вопроса"""
    patterns = [
        r'население\s+([А-Яа-я\s]+?)(?:\s+с\s+\d{4}|\s+в\s+\d{4}|$)',
        r'([А-Яа-я\s]+?)\s+с\s+\d{4}\s+по\s+\d{4}',
        r'([А-Яа-я\s]+?)(?:область|республика|край)',
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            region = match.group(1).strip()
            return region
    return None


def find_region_in_df(df, region_name: str):
    """Ищет регион в DataFrame"""
    if df is None or region_name is None:
        return None
    
    region_clean = region_name.lower().strip()
    region_clean = region_clean.replace('республика', '').replace('область', '').replace('край', '').strip()
    
    for _, row in df.iterrows():
        row_clean = row['name'].lower()
        row_clean = row_clean.replace('республика', '').replace('область', '').replace('край', '').strip()
        
        if region_clean in row_clean or row_clean in region_clean:
            return row
    return None


@router.post("/query", response_model=QueryResponse)
async def query_llama(request: QueryRequest):
    from app.services.llama_service import llama_service
    
    # 1. Проверяем, есть ли в вопросе два года
    start_year, end_year = extract_two_years(request.prompt)
    
    # 2. Извлекаем регион
    region_name = extract_region_from_prompt(request.prompt)
    
    context = ""
    target_year = request.year
    
    # 🔥 СЛУЧАЙ 1: ДВА ГОДА (сравнение, процент изменения)
    if start_year is not None and end_year is not None and region_name:
        df_start = data_service.get_all_data(start_year)
        df_end = data_service.get_all_data(end_year)
        
        if df_start is None or df_end is None:
            return QueryResponse(
                answer=f"Нет данных за {start_year} или {end_year} год",
                model_used=request.model,
                year_used=end_year,
                processing_time=0,
                timestamp=datetime.now(),
                cached=False
            )
        
        region_start = find_region_in_df(df_start, region_name)
        region_end = find_region_in_df(df_end, region_name)
        
        if region_start is not None and region_end is not None:
            pop_start = int(region_start['total_population'])
            pop_end = int(region_end['total_population'])
            change = pop_end - pop_start
            change_percent = (change / pop_start) * 100 if pop_start > 0 else 0
            
            context = f"""
ТОЧНЫЕ ДАННЫЕ ИЗ CSV ФАЙЛОВ:

Регион: {region_start['name']}
{start_year} год: {pop_start:,} человек
{end_year} год: {pop_end:,} человек

ИЗМЕНЕНИЕ:
- Абсолютное: {change:+,} человек
- Относительное: {change_percent:+.2f}%
"""
            target_year = end_year
        else:
            context = f"Регион '{region_name}' не найден в данных за {start_year} или {end_year} год.\n"
    
    # 🔥 СЛУЧАЙ 2: ОДИН ГОД
    else:
        target_year = extract_single_year(request.prompt)
        if target_year is None:
            target_year = request.year
        
        df = data_service.get_all_data(target_year)
        
        if df is None:
            return QueryResponse(
                answer=f"Нет данных за {target_year} год. Доступные годы: {data_service.get_available_years()}",
                model_used=request.model,
                year_used=target_year,
                processing_time=0,
                timestamp=datetime.now(),
                cached=False
            )
        
        if region_name:
            region = find_region_in_df(df, region_name)
            
            if region is not None:
                population = int(region['total_population'])
                context = f"""
ТОЧНЫЕ ДАННЫЕ ИЗ CSV ФАЙЛА ЗА {target_year} ГОД:

Регион: {region['name']}
Население: {population:,} человек
"""
            else:
                context = f"Регион '{region_name}' не найден в данных за {target_year} год.\n\nДоступные регионы:\n"
                for _, row in df.head(20).iterrows():
                    context += f"- {row['name']}\n"
        else:
            stats = data_service.get_year_statistics(target_year)
            context = f"""
ДАННЫЕ ЗА {target_year} ГОД:

Общая численность населения России: {stats['total_population']:,} человек
Городское население: {stats['urban_population']:,} человек
Сельское население: {stats['rural_population']:,} человек
"""
    
    # Формируем финальный промпт
    full_prompt = f"""{context}

Вопрос пользователя: {request.prompt}

ПРАВИЛА ОТВЕТА:
1. Используй ТОЛЬКО цифры из раздела "ТОЧНЫЕ ДАННЫЕ ИЗ CSV ФАЙЛА"
2. Если есть изменение — покажи абсолютную разницу и процент
3. НЕ используй свои знания

ОТВЕТ:"""
    
    result = await llama_service.generate(
        prompt=full_prompt,
        model=request.model,
        temperature=0.1,
        max_tokens=request.max_tokens,
        year=target_year,
        use_cache=request.use_cache
    )
    
    return QueryResponse(
        answer=result.get("response", ""),
        model_used=result.get("model", request.model),
        year_used=target_year,
        processing_time=result.get("processing_time", 0),
        timestamp=datetime.now(),
        cached=result.get("cached", False)
    )


@router.get("/suggestions")
async def get_analysis_suggestions():
    return {
        "suggestions": [
            {"question": "Какая численность населения Белгородская область в 2012 году?"},
            {"question": "Процент изменения численности населения Белгородская область с 2012 по 2024"},
            {"question": "Сравни население Чеченская Республика в 2012 и 2024 году"},
            {"question": "Население Республика Дагестан в 2020 году?"}
        ]
    }
