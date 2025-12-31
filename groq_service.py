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
        """Модерация: только еда. Английский промт для точности."""
        prompt = (
            "You are a food safety moderator. Return ONLY JSON: {\"valid\": true} if input contains edible items, "
            "otherwise {\"valid\": false}."
        )
        res = await GroqService._send_groq_request(prompt, text, 0.1)
        return "true" in res.lower()

    @staticmethod
    async def analyze_categories(products: str) -> List[str]:
        """Определяет категории блюд на основе продуктов."""
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
        """Генерирует список блюд с переводом в скобках для RU и чистыми кнопками."""
        is_ru = lang_code[:2].lower() == "ru"
        
        system_prompt = (
            "You are a creative chef. Suggest 4-6 dishes. "
            "RULES FOR NAMES:\n"
            "1. Field 'name': ALWAYS use the NATIVE language of the input ingredients (for buttons).\n"
            f"2. Field 'desc': Use {('Russian' if is_ru else 'the user language')}.\n"
            f"3. SPECIAL RULE: If language is Russian and input is foreign, format the 'display_name' as: 'Original Name (Russian Translation)'.\n"
            "Return ONLY JSON: [{\"name\": \"Native Name\", \"display_name\": \"Name with optional translation\", \"desc\": \"Short description\"}]."
        )
        
        res = await GroqService._send_groq_request(system_prompt, f"Ingredients: {products}, Category: {category}", 0.6)
        try:
            clean_json = re.search(r'\[.*\]', res, re.DOTALL).group()
            return json.loads(clean_json)
        except:
            return []

    @staticmethod
    async def generate_recipe(dish_name: str, products: str, lang_code: str = "ru") -> str:
        """Генерация рецепта с КБЖУ, Триадой и локализацией ингредиентов."""
        languages = {"ru": "Russian", "en": "English", "es": "Spanish", "fr": "French", "de": "German"}
        target_lang = languages.get(lang_code[:2].lower(), "Russian")

        system_prompt = (
            f"You are a professional chef. Write a detailed recipe strictly in {target_lang}.\n\n"
            f"STRICT LOCALIZATION: All fields including ingredient names and the dish title MUST be translated to {target_lang}.\n\n"
            "RULES:\n"
            "1. INGREDIENTS: Use ONLY user products + BASIC items (water, salt, pepper, sugar, oil, flour, vinegar).\n"
            "2. SMART SUBSTITUTES: If a key item is missing, use a logical one from the list (e.g. yogurt for sour cream) and name it as used.\n"
            "3. NO EMOJIS inside ingredients list or steps. No checkmarks. No '*' or '**' in steps.\n"
            "4. KBHU: Estimated Calories, Proteins, Fats, Carbs PER SERVING.\n"
            "5. CULINARY TRIAD: Add 'Chef's Advice' section. Analyze Taste, Aroma, Texture. Explain flavor chemistry. "
            "You may suggest EXACTLY ONE missing item to finish the triad.\n\n"
            f"STRUCTURE IN {target_lang.upper()}:\n"
            "🥘 [Translated Dish Name]\n\n"
            "📦 Ингредиенты:\n[List - NO EMOJIS]\n\n"
            "📊 КБЖУ на порцию:\n[Data]\n\n"
            "⏱ Время: [min] | 📈 Сложность: [level] | 👥 Порции: [num]\n\n"
            "🔪 Приготовление:\n[Steps without formatting]\n\n"
            "💡 Совет шеф-повара:\n[Triad Analysis]"
        )

        res = await GroqService._send_groq_request(system_prompt, f"Dish: {dish_name}. Ingredients: {products}", 0.3)
        
        farewell = {"ru": "Приятного аппетита!", "en": "Bon appétit!", "es": "¡Buen provecho!", "fr": "Bon appétit!"}
        bon = farewell.get(lang_code[:2].lower(), "Приятного аппетита!")

        if GroqService._is_refusal(res): return res
        return f"{res}\n\n👨‍🍳 <b>{bon}</b>"

    @staticmethod
    async def generate_freestyle_recipe(dish_name: str, lang_code: str = "ru") -> str:
        """Метафорические рецепты с учетом языка."""
        languages = {"ru": "Russian", "en": "English", "es": "Spanish"}
        target_lang = languages.get(lang_code[:2].lower(), "Russian")
        
        prompt = (
            f"Write in {target_lang}. Food -> Recipe. Abstraction -> Metaphorical recipe. "
            "Safety: If dangerous, return ONLY: '⛔ Извините, я готовлю только еду.'"
        )
        res = await GroqService._send_groq_request(prompt, dish_name, 0.7)
        return res

    @staticmethod
    def _is_refusal(text: str) -> bool:
        refusals = ["cannot fulfill", "against my policy", "не могу ответить", "извините", "⛔"]
        return any(ph in text.lower() for ph in refusals)