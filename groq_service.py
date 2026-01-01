from groq import AsyncGroq
from config import GROQ_API_KEY, GROQ_MODEL
import json, re, logging, asyncio

client = AsyncGroq(api_key=GROQ_API_KEY)
logger = logging.getLogger(__name__)

class GroqService:
    @staticmethod
    async def _send_request(prompt: str, user_text: str, temp: float) -> str:
        try:
            resp = await client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_text}],
                temperature=temp
            )
            return resp.choices[0].message.content.strip() or ""
        except Exception as e:
            logger.error(f"Groq Error: {e}")
            return ""

    @staticmethod
    def _extract_json(text: str):
        try:
            match = re.search(r'(?s)(\{.*\}|\[.*\])', text)
            return json.loads(match.group()) if match else None
        except: return None

    @staticmethod
    async def determine_intent(text: str):
        res = await GroqService._send_request("Return JSON: {'intent': 'recipe' or 'ingredients', 'dish': 'name'}", text, 0.1)
        return GroqService._extract_json(res) or {"intent": "ingredients"}

    @staticmethod
    async def analyze_categories(products: str):
        prompt = "Return ONLY JSON array of keys: ['soup', 'main', 'salad', 'breakfast', 'dessert', 'drink', 'snack']"
        res = await GroqService._send_request(prompt, products, 0.2)
        return GroqService._extract_json(res) or ["main"]

    @staticmethod
    async def generate_dishes_list(products: str, category: str, lang: str):
        prompt = f"Suggest 4 dishes in {category}. JSON: [{{'display_name': 'Original Name', 'desc': 'In {lang}'}}]. NO BRACKETS."
        res = await GroqService._send_request(prompt, products, 0.6)
        return GroqService._extract_json(res) or []

    @staticmethod
    async def generate_recipe(dish: str, products: str, lang: str):
        prompt = f"Write recipe for {dish} in {lang}. Header: Original Name. Nutrition and Info: EACH ON NEW LINE. No bold in steps."
        return await GroqService._send_request(prompt, f"Dish: {dish}, Products: {products}", 0.4)