# Культурная карта: язык → кухня
CUISINE_MAP = {
    # Европа
    "ru": "русской/восточноевропейской",
    "uk": "украинской",
    "be": "белорусской",
    "pl": "польской",
    "de": "немецкой/австрийской",
    "fr": "французской",
    "it": "итальянской",
    "es": "испанской",
    "pt": "португальской",
    "el": "греческой",
    "tr": "турецкой",
    "hu": "венгерской",
    "ro": "румынской",
    "bg": "болгарской",
    "cs": "чешской",
    "sk": "словацкой",
    "nl": "голландской",
    "sv": "шведской",
    "no": "норвежской",
    "da": "датской",
    "fi": "финской",
    
    # Англоязычные
    "en": "англоязычной",
    
    # Азия
    "zh": "китайской",
    "ja": "японской",
    "ko": "корейской",
    "th": "тайской",
    "vi": "вьетнамской",
    "id": "индонезийской",
    "hi": "индийской",
    
    # Ближний Восток
    "ar": "арабской",
    "he": "израильской",
    "fa": "персидской",
}

# Названия языков для промптов (в падеже "на каком языке")
LANG_NAMES = {
    "ru": "русском",
    "uk": "украинском",
    "be": "белорусском",
    "pl": "польском",
    "de": "немецком",
    "fr": "французском",
    "it": "итальянском",
    "es": "испанском",
    "pt": "португальском",
    "el": "греческом",
    "tr": "турецком",
    "hu": "венгерском",
    "ro": "румынском",
    "bg": "болгарском",
    "cs": "чешском",
    "sk": "словацком",
    "nl": "голландском",
    "sv": "шведском",
    "no": "норвежском",
    "da": "датском",
    "fi": "финском",
    "en": "английском",
    "zh": "китайском",
    "ja": "японском",
    "ko": "корейском",
    "th": "тайском",
    "vi": "вьетнамском",
    "id": "индонезийском",
    "hi": "хинди",
    "ar": "арабском",
    "he": "иврите",
    "fa": "персидском",
}

# Переводы категорий блюд
CATEGORY_TRANSLATIONS = {
    "ru": {
        "breakfast": "🍳 Завтраки",
        "soup": "🍲 Супы",
        "main": "🍝 Вторые блюда",
        "salad": "🥗 Салаты",
        "snack": "🥪 Закуски",
        "dessert": "🍰 Десерты",
        "drink": "🥤 Напитки",
        "mix": "🍱 Комплексные обеды",
    },
    "en": {
        "breakfast": "🍳 Breakfast",
        "soup": "🍲 Soups",
        "main": "🍝 Main Dishes",
        "salad": "🥗 Salads",
        "snack": "🥪 Snacks",
        "dessert": "🍰 Desserts",
        "drink": "🥤 Drinks",
        "mix": "🍱 Set Meals",
    },
    "de": {
        "breakfast": "🍳 Frühstück",
        "soup": "🍲 Suppen",
        "main": "🍝 Hauptgerichte",
        "salad": "🥗 Salate",
        "snack": "🥪 Snacks",
        "dessert": "🍰 Desserts",
        "drink": "🥤 Getränke",
        "mix": "🍱 Menüs",
    },
    "fr": {
        "breakfast": "🍳 Petits déjeuners",
        "soup": "🍲 Soupes",
        "main": "🍝 Plats principaux",
        "salad": "🥗 Salades",
        "snack": "🥪 En-cas",
        "dessert": "🍰 Desserts",
        "drink": "🥤 Boissons",
        "mix": "🍱 Menus",
    },
    "it": {
        "breakfast": "🍳 Colazioni",
        "soup": "🍲 Zuppe",
        "main": "🍝 Secondi piatti",
        "salad": "🥗 Insalate",
        "snack": "🥪 Spuntini",
        "dessert": "🍰 Dolci",
        "drink": "🥤 Bevande",
        "mix": "🍱 Menu completi",
    },
    "es": {
        "breakfast": "🍳 Desayunos",
        "soup": "🍲 Sopas",
        "main": "🍝 Platos principales",
        "salad": "🥗 Ensaladas",
        "snack": "🥪 Aperitivos",
        "dessert": "🍰 Postres",
        "drink": "🥤 Bebidas",
        "mix": "🍱 Menús completos",
    },
    "zh": {
        "breakfast": "🍳 早餐",
        "soup": "🍲 汤",
        "main": "🍝 主菜",
        "salad": "🥗 沙拉",
        "snack": "🥪 小吃",
        "dessert": "🍰 甜点",
        "drink": "🥤 饮料",
        "mix": "🍱 套餐",
    },
    "ja": {
        "breakfast": "🍳 朝食",
        "soup": "🍲 スープ",
        "main": "🍝 メイン料理",
        "salad": "🥗 サラダ",
        "snack": "🥪 軽食",
        "dessert": "🍰 デザート",
        "drink": "🥤 飲み物",
        "mix": "🍱 セットメニュー",
    },
}

# UI-строки (кнопки, сообщения)
UI_STRINGS = {
    "ru": {
        "start_msg": "👋 Здравствуйте.\n\n🎤 <b>Отправьте</b> голосовое или текстовое сообщение с перечнем продуктов и напитков, и я подскажу, что из них можно приготовить.\n📝 Или напишите <b>\"Дай рецепт [блюдо]\"</b>.",
        "author_msg": "👨‍💻 Автор бота: @inikonoff",
        "products_accepted": "✅ Продукты приняты.\nКакой стиль готовки?",
        "style_classic": "🏠 Классический / Домашний",
        "style_exotic": "🌶 Экзотический / Необычный",
        "added_products": "➕ Добавил: <b>{}</b>.",
        "analyzing": "👨‍🍳 Анализирую продукты...",
        "what_cook": "📂 <b>Что будем готовить?</b>",
        "searching_recipe": "⚡️ Ищу: <b>{}</b>...",
        "writing_recipe": "👨‍🍳 Пишу рецепт: <b>{}</b>...",
        "reset": "🗑 Сброс",
        "back_categories": "⬅️ Назад к категориям",
        "another_variant": "🔄 Другой вариант",
        "back_to_categories": "⬅️ Вернуться к категориям",
        "hide": "🗑 Скрыть",
        "listening": "🎧 Слушаю...",
        "not_products": "🤨 <b>\"{}\"</b> — не похоже на продукты.",
        "thanks_reply": "На здоровье! 👨‍🍳",
        "menu_title": "🍽 <b>Меню: {}</b>\n\n",
    },
    "en": {
        "start_msg": "👋 Hello.\n\n🎤 <b>Send</b> a voice or text message with a list of products and drinks, and I'll suggest what you can cook.\n📝 Or write <b>\"Give me recipe [dish]\"</b>.",
        "author_msg": "👨‍💻 Bot creator: @inikonoff",
        "products_accepted": "✅ Products accepted.\nWhat cooking style?",
        "style_classic": "🏠 Classic / Home-style",
        "style_exotic": "🌶 Exotic / Unusual",
        "added_products": "➕ Added: <b>{}</b>.",
        "analyzing": "👨‍🍳 Analyzing products...",
        "what_cook": "📂 <b>What shall we cook?</b>",
        "searching_recipe": "⚡️ Searching: <b>{}</b>...",
        "writing_recipe": "👨‍🍳 Writing recipe: <b>{}</b>...",
        "reset": "🗑 Reset",
        "back_categories": "⬅️ Back to categories",
        "another_variant": "🔄 Another variant",
        "back_to_categories": "⬅️ Back to categories",
        "hide": "🗑 Hide",
        "listening": "🎧 Listening...",
        "not_products": "🤨 <b>\"{}\"</b> — doesn't look like food.",
        "thanks_reply": "You're welcome! 👨‍🍳",
        "menu_title": "🍽 <b>Menu: {}</b>\n\n",
    },
    "de": {
        "start_msg": "👋 Hallo.\n\n🎤 <b>Senden Sie</b> eine Sprach- oder Textnachricht mit einer Liste von Produkten und Getränken, und ich sage Ihnen, was Sie kochen können.\n📝 Oder schreiben Sie <b>\"Gib mir Rezept [Gericht]\"</b>.",
        "author_msg": "👨‍💻 Bot-Ersteller: @inikonoff",
        "products_accepted": "✅ Produkte akzeptiert.\nWelcher Kochstil?",
        "style_classic": "🏠 Klassisch / Hausgemacht",
        "style_exotic": "🌶 Exotisch / Ungewöhnlich",
        "added_products": "➕ Hinzugefügt: <b>{}</b>.",
        "analyzing": "👨‍🍳 Analysiere Produkte...",
        "what_cook": "📂 <b>Was kochen wir?</b>",
        "searching_recipe": "⚡️ Suche: <b>{}</b>...",
        "writing_recipe": "👨‍🍳 Schreibe Rezept: <b>{}</b>...",
        "reset": "🗑 Zurücksetzen",
        "back_categories": "⬅️ Zurück zu Kategorien",
        "another_variant": "🔄 Andere Variante",
        "back_to_categories": "⬅️ Zurück zu Kategorien",
        "hide": "🗑 Ausblenden",
        "listening": "🎧 Höre zu...",
        "not_products": "🤨 <b>\"{}\"</b> — sieht nicht nach Lebensmitteln aus.",
        "thanks_reply": "Gern geschehen! 👨‍🍳",
        "menu_title": "🍽 <b>Menü: {}</b>\n\n",
    },
}

def get_ui_string(key: str, lang: str, *args) -> str:
    """Получить переведённую UI-строку"""
    strings = UI_STRINGS.get(lang, UI_STRINGS["ru"])
    template = strings.get(key, UI_STRINGS["ru"].get(key, ""))
    return template.format(*args) if args else template

def get_category_name(category_key: str, lang: str) -> str:
    """Получить переведённое название категории"""
    translations = CATEGORY_TRANSLATIONS.get(lang, CATEGORY_TRANSLATIONS["ru"])
    return translations.get(category_key, category_key.capitalize())

def get_cuisine_context(products_lang: str, target_lang: str) -> dict:
    """
    Формирует контекст для промпта на основе языков.
    
    Returns:
        dict: {
            "is_cross_cultural": bool,
            "cuisine": str,
            "products_lang_name": str,
            "target_lang_name": str,
        }
    """
    cuisine = CUISINE_MAP.get(products_lang, "домашней")
    products_lang_name = LANG_NAMES.get(products_lang, products_lang)
    target_lang_name = LANG_NAMES.get(target_lang, target_lang)
    
    return {
        "is_cross_cultural": products_lang != target_lang,
        "cuisine": cuisine,
        "products_lang_name": products_lang_name,
        "target_lang_name": target_lang_name,
    }