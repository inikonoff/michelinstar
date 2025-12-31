from groq import AsyncGroq
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS
from typing import Dict, List, Union
import json
import re
import logging

client = AsyncGroq(api_key=GROQ_API_KEY)
logger = logging.getLogger(__name__)

class GroqService:
    
    @staticmethod
    async def _send_groq_request(system_prompt: str, user_text: str, temperature: float = 0.5, max_tokens: int = 1500) -> str:
        try:
            response = await client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            return ""

    @staticmethod
    async def validate_ingredients(text: str) -> bool:
        """Модерация входящего текста на предмет съедобности."""
        prompt = (
            "You are a food safety moderator. Return ONLY JSON: {\"valid\": true} if input contains edible items, "
            "otherwise {\"valid\": false}. Ignore language."
        )
        res = await GroqService._send_groq_request(prompt, text, 0.1)
        return "true" in res.lower()

    @staticmethod
    async def analyze_categories(products: str) -> List[str]:
        """Определяет категории блюд на основе набора продуктов."""
        prompt = (
            "Analyze ingredients. Determine dish categories: ['soup', 'main', 'salad', 'breakfast', 'dessert', 'drink', 'snack']. "
            "Return ONLY a JSON array of relevant keys."
        )
        res = await GroqService._send_groq_request(prompt, products, 0.2)
        try:
            clean_json = re.search(r'\[.*\]', res, re.DOTALL).group()
            return json.loads(clean_json)
        except:
            return ["main"]

    @staticmethod
    async def generate_dishes_list(products: str, category: str, style: str = "обычный", lang_code: str = "ru") -> List[Dict[str, str]]:
        """Генерирует список блюд. Реализует 'Название (Перевод)' для RU и чистый оригинал для кнопок."""
        is_ru = lang_code[:2].lower() == "ru"
        
        system_prompt = (
            "You are a creative chef. Suggest 4-6 dishes. "
            "STRICT RULES FOR FIELDS:\n"
            "1. 'name': ALWAYS use the NATIVE language of the provided ingredients (e.g., if input is 'Pollo', name is 'Pollo al Horno'). This is for buttons.\n"
            f"2. 'desc': Write description strictly in {('Russian' if is_ru else 'the user language')}.\n"
            f"3. 'display_name': If the user language is Russian and the input is foreign, you MUST format it as: 'Native Name (Russian Translation)'. If input is already Russian, just use the Russian name.\n"
            "Return ONLY JSON: [{\"name\": \"Native Name\", \"display_name\": \"Original (Translation)\", \"desc\": \"Tasty description\"}]."
        )
        
        res = await GroqService._send_groq_request(system_prompt, f"Ingredients: {products}, Category: {category}", 0.6)
        try:
            clean_json = re.search(r'\[.*\]', res, re.DOTALL).group()
            return json.loads(clean_json)
        except:
            return []

    @staticmethod
    async def generate_recipe(dish_name: str, products: str, lang_code: str = "ru") -> str:
        """Генерация рецепта с 'Silent Exclusion', КБЖУ и Триадой."""
        languages = {"ru": "Russian", "en": "English", "es": "Spanish", "fr": "French", "de": "German"}
        target_lang = languages.get(lang_code[:2].lower(), "Russian")

        system_prompt = (
            f"You are a professional chef. Write a detailed recipe strictly in {target_lang}.\n\n"
            "STRICT OPERATIONAL RULES:\n"
            "1. SILENT EXCLUSION: Only include ingredients actually used in the recipe steps. "
            "If a user product is NOT used, do not list it and DO NOT mention its exclusion. "
            "No phrases like 'I didn't use chocolate'. Just remain silent about unused items.\n"
            f"2. LOCALIZATION: All text, labels, and ingredient names MUST be translated to {target_lang}.\n"
            "3. INGREDIENTS: Use only user products + BASIC items (water, salt, pepper, sugar, oil, flour, vinegar).\n"
            "4. NO EMOJIS in ingredient list or steps. No checkmarks. No formatting like '**' in steps.\n"
            "5. CULINARY TRIAD: End with 'Chef's Advice' (Taste, Aroma, Texture). Recommend EXACTLY ONE missing item to complete the triad.\n\n"
            f"STRUCTURE IN {target_lang.upper()}:\n"
            "🥘 [Translated Dish Name]\n\n"
            "📦 Ингредиенты:\n[Item list - NO EMOJIS]\n\n"
            "📊 КБЖУ на порцию:\n[Data]\n\n"
            "⏱ Время | 📈 Сложность | 👥 Порции\n\n"
            "🔪 Приготовление:\n[Steps without formatting]\n\n"
            "💡 Совет шеф-повара:\n[Triad Analysis]"
        )

        res = await GroqService._send_groq_request(system_prompt, f"Dish: {dish_name}. Ingredients: {products}", 0.3)
        
        farewell = {"ru": "Приятного аппетита!", "en": "Bon appétit!", "es": "¡Buen provecho!"}
        bon = farewell.get(lang_code[:2].lower(), "Приятного аппетита!")

        if GroqService._is_refusal(res): return res
        return f"{res}\n\n👨‍🍳 <b>{bon}</b>"

    @staticmethod
    async def generate_freestyle_recipe(dish_name: str, lang_code: str = "ru") -> str:
        """Метафорические рецепты (счастье, любовь и т.д.)."""
        languages = {"ru": "Russian", "en": "English", "es": "Spanish"}
        target_lang = languages.get(lang_code[:2].lower(), "Russian")
        
        prompt = (
            f"Write in {target_lang}. If food -> recipe. If abstraction -> metaphorical recipe. "
            "Safety: If dangerous/illegal, return ONLY: '⛔ Извините, я готовлю только еду.'"
        )
        res = await GroqService._send_groq_request(prompt, dish_name, 0.7)
        return res

    @staticmethod
    def _is_refusal(text: str) -> bool:
        refusals = ["cannot fulfill", "against my policy", "не могу ответить", "извините", "⛔"]
        return any(ph in text.lower() for ph in refusals)