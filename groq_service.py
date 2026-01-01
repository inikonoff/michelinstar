from groq import AsyncGroq
from config import GROQ_API_KEY, GROQ_MODEL
from typing import Dict, List, Union
import json
import re
import logging
import asyncio

client = AsyncGroq(api_key=GROQ_API_KEY)
logger = logging.getLogger(__name__)

class GroqService:
    
    @staticmethod
    async def _send_groq_request(system_prompt: str, user_text: str, temperature: float = 0.5, retries: int = 1) -> str:
        """Retry Logic: если ИИ выдал пустой ответ, пробуем еще раз с нулевой температурой."""
        current_temp = temperature
        for attempt in range(retries + 1):
            try:
                response = await client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_text}
                    ],
                    temperature=current_temp
                )
                res_content = response.choices[0].message.content.strip()
                if res_content:
                    return res_content
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
            
            current_temp = 0.0  # Убираем креативность для стабильности при повторе
            await asyncio.sleep(0.5)
        return ""

    @staticmethod
    def _extract_json(text: str) -> Union[Dict, List, None]:
        if not text: return None
        try:
            match = re.search(r'(?s)(\{.*\}|\[.*\])', text)
            if match:
                return json.loads(match.group())
        except Exception:
            return None
        return None

    @staticmethod
    async def determine_intent(text: str) -> Dict[str, str]:
        """Определяем, хочет пользователь рецепт или вводит продукты."""
        system_prompt = "Analyze input. Return ONLY JSON: {'intent': 'ingredients'} or {'intent': 'recipe', 'dish': 'name'}."
        res = await GroqService._send_groq_request(system_prompt, text, temperature=0.1)
        return GroqService._extract_json(res) or {"intent": "ingredients"}

    @staticmethod
    async def analyze_categories(products: str) -> List[str]:
        """Укрепленная логика категорий (Супы и Напитки)."""
        system_prompt = """Analyze ingredients. Return ONLY a JSON array of keys from: 
        ['soup', 'main', 'salad', 'breakfast', 'dessert', 'drink', 'snack'].
        STRICT RULES:
        1. Base: (water + salt + onion + carrot) = MUST suggest 'soup'.
        2. Liquid base: (fruit/vegetable + milk/water) = MUST suggest 'drink'.
        3. Max 3 most relevant categories."""
        
        res = await GroqService._send_groq_request(system_prompt, products, temperature=0.2)
        data = GroqService._extract_json(res)
        return data if isinstance(data, list) else ["main"]

    @staticmethod
    async def generate_dishes_list(products: str, category: str, lang_code: str = "ru") -> List[Dict[str, str]]:
        """Генерация списка блюд без скобок и переводов."""
        target_lang = "Russian" if lang_code.startswith("ru") else "English"
        
        system_prompt = f"""Suggest 4-6 dishes in category '{category}'.
        STRICT RULES:
        1. 'display_name': Use ONLY the original native name. NO brackets, NO translations.
        2. 'desc': Short tasty description STRICTLY in {target_lang}.
        3. No transliterations. Avoid translations in names.
        Return ONLY JSON: [{{"name": "...", "display_name": "...", "desc": "..."}}]."""
        
        res = await GroqService._send_groq_request(system_prompt, f"Ingredients: {products}", temperature=0.6)
        return GroqService._extract_json(res) or []

    @staticmethod
    async def generate_recipe(dish_name: str, products: str, lang_code: str = "ru") -> str:
        """Полный рецепт с вертикальным КБЖУ и Silent Exclusion."""
        target_lang = "Russian" if lang_code.startswith("ru") else "English"
        
        system_prompt = f"""Write a recipe for '{dish_name}' in {target_lang}.
        STRICT RULES:
        1. HEADER: Use the original native name. Never translate it.
        2. SILENT EXCLUSION: Use only user products + basic (water, salt, pepper, oil, sugar). Never mention what you did not use.
        3. NUTRITION & INFO: Each parameter (Time, Difficulty, Proteins, Fats, etc.) MUST be on a NEW LINE.
        4. No bold in preparation steps.
        
        STRUCTURE:
        🥘 [Original Name]
        
        📦 ИНГРЕДИЕНТЫ:
        [List: - Name - amount]
        
        ⏱ Время: ...
        🎚 Сложность: ...
        👥 Порции: ...
        
        📊 Пищевая ценность на 1 порцию:
        🥚 Белки: ...
        🥑 Жиры: ...
        🌾 Углеводы: ...
        ⚡ Энерг. ценность: ...

        🔪 Приготовление:
        [Steps]

        💡 Совет шеф-повара:
        [Analysis in {target_lang}]"""

        return await GroqService._send_groq_request(system_prompt, f"Dish: {dish_name}. Products: {products}", temperature=0.4)

    @staticmethod
    def get_welcome_message() -> str:
        return "👋 Я ваш ИИ-шеф. Пришлите список продуктов или название блюда."