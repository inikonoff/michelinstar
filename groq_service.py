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
    async def determine_intent(text: str, last_context: str = "") -> Dict[str, str]:
        """Определяет намерение пользователя: продукты или конкретное блюдо."""
        prompt = (
            "Analyze input. Return ONLY JSON: {\"intent\": \"ingredients\"} or {\"intent\": \"recipe\", \"dish\": \"name\"}."
        )
        res = await GroqService._send_groq_request(prompt, text, 0.1)
        try:
            clean_json = re.search(r'\{.*\}', res, re.DOTALL).group()
            return json.loads(clean_json)
        except:
            return {"intent": "ingredients"}

    @staticmethod
    async def validate_ingredients(text: str) -> bool:
        """Модерация ввода: только продукты."""
        prompt = (
            "You are a food safety moderator. Return ONLY JSON: {\"valid\": true} if input is food, "
            "otherwise {\"valid\": false}. Ignore language."
        )
        res = await GroqService._send_groq_request(prompt, text, 0.1)
        return "true" in res.lower()

    @staticmethod
    async def analyze_categories(products: str) -> List[str]:
        """Определяет категории блюд на основе продуктов."""
        prompt = (
            "Analyze ingredients and return ONLY a JSON array of keys: "
            "['soup', 'main', 'salad', 'breakfast', 'dessert', 'drink', 'snack'].\n\n"
            "STRICT RULES:\n"
            "1. Always assume basics: water, salt, oil, sugar, pepper, ice.\n"
            "2. If fruits/berries + (water/milk/sugar/ice) are possible, ALWAYS include 'drink'.\n"
            "3. If flour/eggs/sugar/fruits are present, ALWAYS include 'dessert' and 'breakfast'.\n"
            "4. If you can make 2 or more dishes in any category, then suggest at least 3 categories."
        )
        res = await GroqService._send_groq_request(prompt, products, 0.2)
        try:
            clean_json = re.search(r'\[.*\]', res, re.DOTALL).group()
            return json.loads(clean_json)
        except:
            return ["main", "snack"]

    @staticmethod
    async def generate_dishes_list(products: str, category: str, style: str = "обычный", lang_code: str = "ru") -> List[Dict[str, str]]:
        is_ru = lang_code[:2].lower() == "ru"
        target_lang = "Russian" if is_ru else "the user's interface language"

        system_prompt = (
            f"You are a creative chef. Suggest 4-6 dishes in category '{category}'.\n"
            f"STRICT LANGUAGE RULES:\n"
            f"1. Field 'name': Use the NATIVE language of the dish (e.g., 'Insalata Estiva').\n"
            f"2. Field 'desc': Write strictly in {target_lang}.\n"
            f"3. Field 'display_name': If the user language is Russian and dish is foreign, format as: 'Original Name (Russian Translation)'.\n"
            f"4. Always assume basics (water, salt, oil, sugar, pepper, ice) are available.\n"
            f"Return ONLY JSON list: [{{'name': '...', 'display_name': '...', 'desc': '...'}}]."
        )
        res = await GroqService._send_groq_request(system_prompt, f"Ingredients: {products}, Category: {category}", 0.6)
        try:
            clean_json = re.search(r'\[.*\]', res, re.DOTALL).group()
            return json.loads(clean_json)
        except:
            return []

    @staticmethod
    async def generate_recipe(dish_name: str, products: str, lang_code: str = "ru") -> str:
        """Генерация экспертного рецепта на основе вашей стабильной базы."""
        languages = {"ru": "Russian", "en": "English", "es": "Spanish"}
        target_lang = languages.get(lang_code[:2].lower(), "Russian")

        system_prompt = (
            f"You are a professional chef. Write a detailed recipe strictly in {target_lang}.\n\n"
            f"STRICT RULES:\n"
            f"1. NAME: Always use the ORIGINAL NATIVE name in the header. NEVER translate it.\n"
            f"2. INGREDIENTS (Bilingual): If an ingredient is foreign, use: 'Native (Russian Translation) - amount'. "
            f"If it's already in Russian, just write 'Ингредиент - количество'. No double brackets.\n"
            f"3. SILENT EXCLUSION: Do not mention ingredients that are NOT used. Do not explain why something is excluded.\n"
            f"4. INGREDIENT UNITS: Use: ст. л., ч. л., зубчика, шт., г.\n"
            f"5. NUTRITION: Calculate per serving. Format EXACTLY:\n"
            f"   📊 Пищевая ценность на 1 порцию:\n"
            f"   🥚 Белки: X г\n"
            f"   🥑 Жиры: X г\n"
            f"   🌾 Углеводы: X г\n"
            f"   ⚡ Энерг. ценность: X ккал\n"
            f"6. NO EMOJIS in steps or ingredient list. No '**' in steps.\n"
            f"7. CULINARY TRIAD: Add 'Chef's Advice' (Taste, Aroma, Texture). Recommend EXACTLY ONE missing item from Culinary Trinity or French Mirepoix.\n\n"
            "STRUCTURE:\n"
            "🥘 [Original Native Name]\n\n"
            "📦 Ингредиенты:\n[List]\n\n"
            "📊 Пищевая ценность на 1 порцию:\n"
            "🥚 Белки: X г...\n\n"
            "⏱ Время | 🎚 Сложность | 👥 Порции\n\n"
            "🔪 Приготовление:\n[Steps]\n\n"
            "💡 Совет шеф-повара:\n[Triad Analysis]"
        )

        res = await GroqService._send_groq_request(system_prompt, f"Dish: {dish_name}. Ingredients: {products}", 0.3)
        bon = "Приятного аппетита!" if lang_code == "ru" else "Bon appetite!"
        return f"{res}\n\n👨‍🍳 <b>{bon}</b>"

    @staticmethod
    async def generate_freestyle_recipe(dish_name: str, lang_code: str = "ru") -> str:
        prompt = "Write a recipe. Safety: return '⛔' if unsafe."
        return await GroqService._send_groq_request(prompt, dish_name, 0.7)

    @staticmethod
    def _is_refusal(text: str) -> bool:
        return any(ph in text.lower() for ph in ["cannot fulfill", "извините", "⛔"])