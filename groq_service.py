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
    async def _send_groq_request(system_prompt: str, user_text: str, temperature: float = 0.5, max_tokens: int = 1000) -> str:
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
        """Модерация ввода: только продукты и съедобное."""
        prompt = (
            "You are a content moderator for a cooking app. Your task is to validate a list of ingredients. "
            "Return ONLY a JSON object: {\"valid\": true} if the text contains edible food items or ingredients. "
            "Return {\"valid\": false} if the text is gibberish, greetings, non-edible objects, or dangerous items. "
            "Ignore minor typos. Logic: Is it possible to cook with this?"
        )
        res = await GroqService._send_groq_request(prompt, f"Input: \"{text}\"", 0.1)
        return "true" in res.lower()

    @staticmethod
    async def analyze_categories(products: str) -> List[str]:
        """Определяет подходящие категории блюд на основе триггеров из en.py"""
        prompt = (
            "You are an experienced chef. Analyze the ingredients and determine which dish categories can be cooked. "
            "Rules: 2+ vegetables/meat -> 'soup'. Fresh veg -> 'salad'. Eggs/flour/milk -> 'breakfast'. "
            "Sugar/fruit -> 'dessert'. Fruit/berries -> 'drink'. "
            "Available categories: ['soup', 'main', 'salad', 'breakfast', 'dessert', 'drink', 'snack']. "
            "Return ONLY a JSON array of keys. If very few ingredients, pick the most relevant one."
        )
        res = await GroqService._send_groq_request(prompt, f"Ingredients: {products}", 0.2)
        try:
            clean_json = res.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            return data if isinstance(data, list) else ["main"]
        except:
            return ["main"]

    @staticmethod
    async def generate_dishes_list(products: str, category: str, style: str = "обычный") -> List[Dict[str, str]]:
        """Генерирует список названий блюд с учетом стиля."""
        prompt = (
            f"You are a creative chef. Suggest 4-6 dishes in the category '{category}' using the provided ingredients. "
            f"Style: {style}. Focus on making them appetizing. "
            "Return ONLY a JSON list of objects: [{\"name\": \"Dish Name\", \"desc\": \"Short tasty description\"}]. "
            "No conversational text."
        )
        res = await GroqService._send_groq_request(prompt, f"Ingredients: {products}", 0.5)
        try:
            clean_json = res.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except:
            return []

    @staticmethod
    async def generate_recipe(dish_name: str, products: str) -> str:
        """Основной метод генерации экспертного рецепта."""
        system_prompt = (
            "You are a professional culinary instructor and nutritionist. Write a detailed recipe in RUSSIAN. "
            "\n\nSTRICT RULES:\n"
            "1. INGREDIENTS: Use ONLY the products provided by the user. "
            "Exception: You may assume BASIC items (water, salt, pepper, sugar, vegetable oil, flour, vinegar) are always available. "
            "2. SUBSTITUTIONS: If a key ingredient is missing but a logical substitute exists in the user's list (e.g., yogurt instead of sour cream), "
            "use the substitute in the recipe steps but name it as the substitute. "
            "3. NO EMOJIS: Do not use checkmarks or any icons in the ingredients list or steps. "
            "4. NO FORMATTING: Do not use '*' or '**' inside the preparation steps. "
            "5. KBHU: Provide estimated Calories, Proteins, Fats, and Carbohydrates PER SERVING. "
            "6. CHEF'S TRIAD: At the end, add a section 'Совет шеф-повара'. Analyze the dish using the 'Culinary Triad' (Taste, Aroma, Texture). "
            "Explain the chemistry of flavor. You may recommend EXACTLY ONE missing ingredient to complete the triad. "
            "\n\nOUTPUT STRUCTURE (RUSSIAN):\n"
            "Название блюда\n\n"
            "Ингредиенты (с граммовкой):\n[List]\n\n"
            "КБЖУ на порцию:\n[Data]\n\n"
            "Параметры:\nВремя: [min], Сложность: [level], Порции: [num]\n\n"
            "Приготовление:\n[Steps]\n\n"
            "Совет шеф-повара:\n[Triad Analysis]"
        )

        user_input = f"Dish: {dish_name}. Available ingredients: {products}"
        res = await GroqService._send_groq_request(system_prompt, user_input, 0.3, 1500)
        
        if GroqService._is_refusal(res): 
            return res
        return res + "\n\n👨‍🍳 <b>Приятного аппетита!</b>"

    @staticmethod
    async def generate_freestyle_recipe(dish_name: str) -> str:
        """Метафорические или свободные рецепты с фильтром безопасности"""
        prompt = (
            "You are a creative chef. If the request is FOOD, write a recipe. "
            "If it is an ABSTRACTION (love, happiness), write a metaphorical recipe. "
            "If it is DANGEROUS/PROHIBITED, return ONLY: '⛔ Извините, я готовлю только еду.' "
            "Write in RUSSIAN."
        )
        res = await GroqService._send_groq_request(prompt, f"Request: {dish_name}", 0.6)
        if GroqService._is_refusal(res): return res
        return res + "\n\n👨‍🍳 <b>Приятного аппетита!</b>"

    @staticmethod
    async def determine_intent(user_message: str, dish_list: str) -> Dict:
        """Определение намерения пользователя через JSON"""
        prompt = (
            "Analyze the user message and context. Determine intent: "
            "1. 'add_products' (changing list), 2. 'select_dish' (naming a dish), 3. 'unclear'. "
            "Return JSON: {\"intent\": \"...\", \"products\": \"...\", \"dish_name\": \"...\"}"
        )
        res = await GroqService._send_groq_request(prompt, f"Context: {dish_list}\nMessage: {user_message}", 0.1)
        try:
            start, end = res.find('{'), res.rfind('}')
            if start != -1 and end != -1:
                return json.loads(res[start : end + 1])
        except:
            pass
        return {"intent": "unclear"}

    @staticmethod
    def _is_refusal(text: str) -> bool:
        """Проверка на отказ модели"""
        if "⛔" in text: return True
        refusals = ["cannot fulfill", "against my policy", "не могу ответить", "нарушает правила"]
        return any(ph in text.lower() for ph in refusals)