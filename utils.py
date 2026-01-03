import os
import asyncio
import speech_recognition as sr
from pydub import AudioSegment
from config import TEMP_DIR, SPEECH_LANGUAGE
from enum import Enum

class VoiceProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
    
    async def convert_ogg_to_wav(self, ogg_path: str) -> str:
        wav_path = ogg_path.replace('.ogg', '.wav')
        # Pydub использует FFmpeg, это блокирующая операция, выносим в тред
        await asyncio.to_thread(self._convert, ogg_path, wav_path)
        return wav_path

    def _convert(self, input_path, output_path):
        audio = AudioSegment.from_ogg(input_path)
        audio.export(output_path, format='wav')
    
    async def recognize_speech(self, wav_path: str) -> str:
        # Google API - синхронный запрос. Оборачиваем в to_thread
        return await asyncio.to_thread(self._recognize_sync, wav_path)

    def _recognize_sync(self, wav_path):
        try:
            with sr.AudioFile(wav_path) as source:
                audio_data = self.recognizer.record(source)
                return self.recognizer.recognize_google(audio_data, language=SPEECH_LANGUAGE)
        except sr.UnknownValueError:
            raise Exception("Речь не распознана")
        except sr.RequestError:
            raise Exception("Ошибка сервиса Google")

    async def process_voice(self, voice_file_path: str) -> str:
        ogg_path = None
        wav_path = None
        try:
            # Копируем файл в нужную структуру (если нужно) или используем как есть
            ogg_path = voice_file_path
            wav_path = await self.convert_ogg_to_wav(ogg_path)
            text = await self.recognize_speech(wav_path)
            return text
        finally:
            # Чистим
            for path in [ogg_path, wav_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

# --- НОВЫЕ УТИЛИТЫ ДЛЯ КОМПЛЕКСНЫХ ОБЕДОВ ---

class MealComplexity(str, Enum):
    SIMPLE = "simple"      # 2 блюда
    STANDARD = "standard"  # 3 блюда
    FULL = "full"          # 4+ блюда

class CourseType(str, Enum):
    SOUP = "soup"
    MAIN = "main"
    SALAD = "salad"
    DRINK = "drink"
    APPETIZER = "appetizer"
    DESSERT = "dessert"

# Emoji mapping
COURSE_EMOJIS = {
    CourseType.SOUP: "🍲",
    CourseType.MAIN: "🍛",
    CourseType.SALAD: "🥗",
    CourseType.DRINK: "🥤",
    CourseType.APPETIZER: "🥢",
    CourseType.DESSERT: "🍰"
}

COMPLEXITY_EMOJIS = {
    MealComplexity.SIMPLE: "🍽️",
    MealComplexity.STANDARD: "🍽️✨",
    MealComplexity.FULL: "🍽️🌟"
}

def format_complex_meal_display(complex_meal: dict) -> str:
    """Форматирует комплексный обед для отображения"""
    courses = complex_meal.get("courses", [])
    complexity = complex_meal.get("complexity", "standard")
    
    emoji = COMPLEXITY_EMOJIS.get(complexity, "🍽️")
    name = complex_meal.get("name", "Комплексный обед")
    
    # Формируем список блюд
    courses_text = ""
    for course in courses:
        course_emoji = COURSE_EMOJIS.get(course.get("type", ""), "•")
        courses_text += f"{course_emoji} <b>{course.get('name', 'Блюдо')}</b>\n<i>{course.get('description', '')}</i>\n\n"
    
    # Добавляем общую информацию
    total_time = complex_meal.get("total_time", "")
    servings = complex_meal.get("servings", "")
    
    if total_time or servings:
        courses_text += "📊 <b>Общая информация:</b>\n"
        if total_time:
            courses_text += f"⏱ Время: {total_time}\n"
        if servings:
            courses_text += f"👥 Порции: {servings}\n"
    
    return f"{emoji} <b>{name}</b>\n\n{courses_text}"

def format_complex_meal_for_buttons(complex_meal: dict, index: int = 0) -> str:
    """Форматирует название для кнопки"""
    complexity = complex_meal.get("complexity", "standard")
    emoji = COMPLEXITY_EMOJIS.get(complexity, "🍽️")
    name = complex_meal.get("name", f"Обед {index+1}")
    
    # Укорачиваем если длинное
    if len(name) > 30:
        name = name[:27] + "..."
    
    return f"{emoji} {name}"

def get_course_type_name(course_type: str) -> str:
    """Получает русское название типа блюда"""
    names = {
        "soup": "Суп",
        "main": "Основное блюдо",
        "salad": "Салат",
        "drink": "Напиток",
        "appetizer": "Закуска",
        "dessert": "Десерт"
    }
    return names.get(course_type, "Блюдо")

def get_complexity_description(complexity: str) -> str:
    """Получает описание сложности комплекса"""
    descriptions = {
        "simple": "Простой обед (2 блюда)",
        "standard": "Стандартный обед (3 блюда)",
        "full": "Полный обед (4+ блюда)"
    }
    return descriptions.get(complexity, "Комплексный обед")