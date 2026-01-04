from groq import AsyncGroq
from config import GROQ_API_KEY, GROQ_MODEL
from typing import Dict, List
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
            logger.error(f"Kitchen Order Error: {e}")
            return ""

    @staticmethod
    def _extract_json(text: str) -> str:
        text = text.replace("```json", "").replace("```", "")
        start_brace = text.find('{')
        start_bracket = text.find('[')
        if start_brace == -1: start = start_bracket
        elif start_bracket == -1: start = start_brace
        else: start = min(start_brace, start_bracket)
        end_brace = text.rfind('}')
        end_bracket = text.rfind(']')
        end = max(end_brace, end_bracket)
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        return text.strip()

    FLAVOR_RULES = """
    🍽 THE ART OF PLATING & TASTE:
    🎭 CONTRAST (The Soul of the Dish):
    • Fat + Acid (Pork + Sauerkraut)
    • Sweet + Salty (Watermelon + Feta)
    • Soft + Crunchy (Cream soup + Croutons)
    ✨ SYNERGY (Flavor Boosting):
    • Tomato + Basil | Fish + Dill + Lemon | Pumpkin + Cinnamon
    👑 THE PROTAGONIST: One "King" ingredient per dish.
    ✅ CHEF'S CLASSICS: Tomato+Basil+Garlic | Lamb+Rosemary/Mint
    ❌ CULINARY TABOOS: Fish + Dairy (hot) | Heavy Protein Overload 🥩+🍗
    """

    @staticmethod
    async def validate_ingredients(text: str) -> bool:
        # Используем {{ }} для JSON, чтобы f-строка не ломалась
        prompt = f"""You are the Head of Food Quality Control. Audit the incoming delivery list for freshness and safety.

📋 INSPECTION CRITERIA:
✅ ACCEPT (Fresh Delivery) if:
- Edible products (meats, veggies, grains, dairy, etc.)
- Minor typos allowed ("patato", "milkk")
- General culinary categories ("herbs", "spices")

❌ REJECT (Hazardous/Spoiled) if:
- Inedible items (gasoline, glass, chemicals)
- Foul language, kitchen slurs, or toxicity
- Gibberish, greeting-only, or empty crates

🎯 REPORT FORMAT (STRICT JSON, language: Russian):
{{
  "valid": true,
  "reason": "короткое пояснение на русском"
}}

🚨 CRITICAL: Response must start with "{{" and end with "}}".
"""
        res = await GroqService._send_groq_request(prompt, f'📝 Batch to inspect: "{text}"', 0.1)
        try:
            clean_json = GroqService._extract_json(res)
            data = json.loads(clean_json)
            return data.get("valid", False)
        except:
            return "true" in res.lower()

    @staticmethod
    async def analyze_categories(products: str) -> List[str]:
        items_count = len(re.split(r'[,;]', products))
        mix_rule = '- "mix" (Full Course)' if items_count >= 5 else '⚠️ "mix" NOT AVAILABLE'
        
        prompt = f"""You are a Menu Architect. Categorize available items.
🛒 CURRENT PANTRY: {products}
📦 STAPLES: salt, sugar, water, oil, spices
📚 SECTIONS: "soup", "main", "salad", "breakfast", "dessert", "drink", "snack", "mix"
{mix_rule}
⚠️ KITCHEN POLICIES: Return 2-4 most logical sections.
🎯 FORMAT: ["section1", "section2"] (JSON ONLY)
"""
        res = await GroqService._send_groq_request(prompt, "Organize the pantry", 0.2)
        try:
            data = json.loads(GroqService._extract_json(res))
            return data if isinstance(data, list) else ["main"]
        except:
            return ["main"]

    @staticmethod
    async def generate_dishes_list(products: str, category: str) -> List[Dict[str, str]]:
        items_count = len(re.split(r'[,]', products))
        target_count = 5 if items_count < 7 else 7

        prompt = f"""You are the Sous-Chef designing Specials for the "{category}" section.
🛒 INGREDIENTS: {products}
{GroqService.FLAVOR_RULES}

🎯 TASK:
- Generate EXACTLY {target_count} appetizing dishes.
- Use only pantry items + staples.
- WRITE NAMES IN INPUT LANGUAGE AND DESCRIPTIONS IN RUSSIAN (на русском языке).

🎯 FORMAT (JSON ONLY):
[
  {{
    "name": "Название блюда",
    "desc": "Аппетитное описание"
  }}
]
"""
        res = await GroqService._send_groq_request(prompt, "Draft the menu", 0.5)
        try:
            return json.loads(GroqService._extract_json(res))
        except:
            return []

    @staticmethod
    async def generate_recipe(dish_name: str, products: str) -> str:
        prompt = f"""You are the Executive Chef. Write a technical recipe card for: "{dish_name}".
🛒 PANTRY: {products}
{GroqService.FLAVOR_RULES}

📋 RECIPE CARD FORMAT (WRITE EVERYTHING IN RUSSIAN):
[Название блюда]
📦 Ингредиенты:
- [продукт] — [количество]
📊 Пищевая ценность: ...
⏱ Время: ...
👨‍🍳 Приготовление:
1. [Шаги приготовления]
💡 CHEF'S SECRET: [Analyze Taste, Aroma and Texture. Recommend ONE missing item for balance]
"""
        res = await GroqService._send_groq_request(prompt, "Start cooking", 0.4, max_tokens=2500)
        return res + "\n\n👨‍🍳 <b>Приятного аппетита!</b>" if not GroqService._is_refusal(res) else res

    @staticmethod
    async def generate_freestyle_recipe(dish_name: str) -> str:
        prompt = f"""You are a Culinary Philosopher. Create a recipe for: "{dish_name}"
🔍 ANALYSIS: Food (standard recipe) vs Metaphor (allegory).
📋 FORMAT: Write EVERYTHING in RUSSIAN.
For food: standard card.
For metaphors: symbolic ingredients and wise cooking steps.
"""
        res = await GroqService._send_groq_request(prompt, "Compose creation", 0.6, max_tokens=2000)
        return res + "\n\n👨‍🍳 <b>Приятного аппетита!</b>" if not GroqService._is_refusal(res) else res

    @staticmethod
    def _is_refusal(text: str) -> bool:
        refusals = ["cannot fulfill", "against policy", "kitchen closed", "не могу"]
        return any(ph in text.lower() for ph in refusals) or "⛔" in text