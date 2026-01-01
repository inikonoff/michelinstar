from groq import AsyncGroq
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS
from typing import Dict, List, Union, Optional
import json
import re
import logging

client = AsyncGroq(api_key=GROQ_API_KEY)
logger = logging.getLogger(__name__)

class GroqService:
    
    @staticmethod
    async def _send_groq_request(system_prompt: str, user_text: str, temperature: float = 0.5, max_tokens: int = 1500) -> str:
        """Отправляет запрос к Groq API с обработкой ошибок."""
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
    def _extract_json(text: str) -> Union[Dict, List, None]:
        """Безопасное извлечение JSON из любого места в тексте."""
        if not text:
            return None
        
        # Ищем первый символ { или [
        json_chars = ['{', '[']
        positions = [text.find(char) for char in json_chars if text.find(char) != -1]
        
        if not positions:
            return None
        
        start_idx = min(positions)
        start_char = text[start_idx]
        end_char = '}' if start_char == '{' else ']'
        
        # Ищем закрывающий символ с конца
        end_idx = text.rfind(end_char)
        if end_idx == -1 or end_idx <= start_idx:
            return None
        
        json_str = text[start_idx:end_idx + 1]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Попробуем найти JSON с помощью регулярок
            pattern = r'(\{.*\})|(\[.*\])'
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                for group in match:
                    if group:
                        try:
                            return json.loads(group)
                        except json.JSONDecodeError:
                            continue
        return None

    @staticmethod
    async def determine_intent(text: str) -> Dict[str, str]:
        """Определяет: список продуктов это или запрос конкретного рецепта."""
        prompt = (
            "Analyze input. Return ONLY JSON: "
            "{\"intent\": \"ingredients\"} or {\"intent\": \"recipe\", \"dish\": \"name\"}."
        )
        res = await GroqService._send_groq_request(prompt, text, 0.1, 500)
        data = GroqService._extract_json(res)
        
        # Fallback на случай ошибки AI или формата
        if not data or "intent" not in data:
            text_l = text.lower()
            recipe_keywords = ['рецепт', 'recipe', 'как приготовить', 'приготовь', 'сделай', 'how to make', 'how to cook']
            if any(kw in text_l for kw in recipe_keywords):
                dish = text
                for kw in recipe_keywords:
                    dish = dish.replace(kw, "")
                return {"intent": "recipe", "dish": dish.strip()}
            return {"intent": "ingredients"}
        return data

    @staticmethod
    async def validate_ingredients(text: str) -> bool:
        """Проверка, что на входе именно еда."""
        prompt = "Return ONLY JSON: {\"valid\": true} if input is food/ingredients, else {\"valid\": false}."
        res = await GroqService._send_groq_request(prompt, text, 0.1, 300)
        data = GroqService._extract_json(res)
        return data.get("valid", True) if data else True

    @staticmethod
    async def analyze_categories(products: str) -> List[str]:
        """Определяет подходящие категории блюд."""
        prompt = (
            "Analyze ingredients. Return ONLY a JSON array of keys: "
            "['soup', 'main', 'salad', 'breakfast', 'dessert', 'drink', 'snack'].\n"
            "Rule: If broth possible (water+vegetables), include 'soup'."
        )
        res = await GroqService._send_groq_request(prompt, products, 0.2, 800)
        data = GroqService._extract_json(res)
        return data if isinstance(data, list) else ["main", "snack"]

    @staticmethod
    async def generate_dishes_list(products: str, category: str, style: str = "обычный", lang_code: str = "ru") -> List[Dict[str, str]]:
        """Генерирует список из 4-6 вариантов блюд."""
        target_lang = "Russian" if lang_code[:2].lower() == "ru" else "English"
        system_prompt = (
            f"Chef mode. Suggest 4-6 dishes in category '{category}' for style '{style}'.\n"
            f"RULES: 1. Field 'name': Native language. 2. Field 'desc': {target_lang}.\n"
            f"3. Field 'display_name': 'Original (Translation)' ONLY if original is not {target_lang}.\n"
            f"4. Dishes MUST be possible with given ingredients.\n"
            f"Return ONLY JSON: [{{'name': '...', 'display_name': '...', 'desc': '...'}}]."
        )
        res = await GroqService._send_groq_request(system_prompt, f"Ingredients: {products}", 0.6, 1200)
        data = GroqService._extract_json(res)
        
        if isinstance(data, list):
            # Ограничиваем максимум 6 блюдами
            return data[:6]
        return []

    @staticmethod
    async def generate_recipe(dish_name: str, products: str, lang_code: str = "ru") -> str:
        """Генерация детального рецепта с КБЖУ и Триадой Шефа."""
        target_lang = "Russian" if lang_code[:2].lower() == "ru" else "English"
        
        system_prompt = (
            f"Professional chef. Write a recipe in {target_lang}.\n"
            f"STRICT RULES:\n"
            f"1. NAME: Original Native name.\n"
            f"2. SILENT EXCLUSION: Use ONLY user products + BASICS (water, salt, oil, sugar, pepper). "
            f"NEVER mention what you DID NOT use.\n"
            f"3. INGREDIENTS: Format '- Item - Amount'. Bilingual ONLY if original is not {target_lang}.\n"
            f"4. NUTRITION: Calculate per serving. Use emojis: 📊, 🥚, 🥑, 🌾, ⚡.\n"
            f"5. CULINARY TRIAD: End with 'Chef's Advice' analyzing Taste, Aroma, Texture.\n"
            f"6. NO EMOJIS in steps. No bold '**' in steps.\n\n"
            "STRUCTURE: 🥘 [Name]\n\n📦 Ингредиенты:\n[List]\n\n📊 Пищевая ценность...\n\n⏱ Время | 🎚 Сложность | 👥 Порции\n\n🔪 Приготовление:\n[Steps]\n\n💡 Совет шеф-повара:"
        )

        res = await GroqService._send_groq_request(system_prompt, f"Dish: {dish_name}. Products: {products}", 0.3, GROQ_MAX_TOKENS)
        
        # Проверка отказа ДО добавления бон-аппетита
        if GroqService._is_refusal(res):
            if lang_code == "ru":
                return "⛔ <b>Не могу предложить рецепт</b>\n\nК сожалению, я не могу предложить рецепт для этого блюда по соображениям безопасности или корректности.\n\nПопробуйте другой запрос или уточните ингредиенты. 🔄"
            else:
                return "⛔ <b>Cannot provide recipe</b>\n\nSorry, I cannot provide a recipe for this dish for safety or appropriateness reasons.\n\nPlease try a different request or clarify ingredients. 🔄"
        
        # Проверка, что ответ не пустой
        if not res or len(res.strip()) < 50:
            if lang_code == "ru":
                return "🍳 <b>Рецепт не найден</b>\n\nНе удалось найти подходящий рецепт для этого блюда с указанными ингредиентами.\n\nПопробуйте добавить больше продуктов или выбрать другое блюдо. 📝"
            else:
                return "🍳 <b>Recipe not found</b>\n\nCould not find a suitable recipe for this dish with the given ingredients.\n\nTry adding more ingredients or choosing a different dish. 📝"
        
        bon = "Приятного аппетита!" if lang_code == "ru" else "Bon appétit!"
        return f"{res}\n\n👨‍🍳 <b>{bon}</b>"

    @staticmethod
    async def generate_freestyle_recipe(dish_name: str, lang_code: str = "ru") -> str:
        """Генерация свободного рецепта (без ограничения ингредиентами)."""
        target_lang = "Russian" if lang_code[:2].lower() == "ru" else "English"
        prompt = f"Write a detailed recipe for '{dish_name}' in {target_lang}. Include ingredients and steps."
        res = await GroqService._send_groq_request(prompt, "", 0.7, 1500)
        
        if GroqService._is_refusal(res):
            if lang_code == "ru":
                return "⛔ Не могу предоставить этот рецепт по соображениям безопасности."
            else:
                return "⛔ Cannot provide this recipe for safety reasons."
        
        return res

    @staticmethod
    def _is_refusal(text: str) -> bool:
        """Определяет, является ли ответ AI отказом."""
        if not text:
            return False
        
        text_lower = text.lower()
        
        refusal_phrases = [
            "cannot fulfill", "i cannot", "i'm unable", "i am unable", "unable to",
            "sorry, i", "apologize", "i apologize", "i'm sorry", "i am sorry",
            "извинит", "не могу", "не имею", "не могу предоставить", "не могу предложить",
            "отказать", "противопоказан", "не рекомендуется", "не следует",
            "опасно", "unsafe", "inappropriate", "harmful", "dangerous",
            "against policy", "ethical", "content policy", "violates",
            "refuse", "decline", "reject", "отказ"
        ]
        
        # Проверяем наличие фраз отказа
        if any(phrase in text_lower for phrase in refusal_phrases):
            return True
        
        # Проверяем на слишком короткие/общие ответы, которые могут быть отказами
        if len(text.strip()) < 100 and any(word in text_lower for word in ["cannot", "unable", "извин", "отказ"]):
            return True
            
        return False

    @staticmethod
    async def get_recipe_variations(dish_name: str, count: int = 3, lang_code: str = "ru") -> List[str]:
        """Генерирует несколько вариаций одного блюда."""
        target_lang = "Russian" if lang_code[:2].lower() == "ru" else "English"
        prompt = f"Give {count} different variations of '{dish_name}' recipe in {target_lang}. Return as bullet points."
        res = await GroqService._send_groq_request(prompt, "", 0.8, 1000)
        
        if GroqService._is_refusal(res):
            return []
        
        # Разделяем на вариации
        variations = []
        lines = res.split('\n')
        for line in lines:
            if line.strip() and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                variations.append(line.strip())
        
        return variations[:count]
