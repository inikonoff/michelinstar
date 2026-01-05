from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from database import async_session, UserSession, User
from config import MAX_HISTORY_MESSAGES
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

class StateManager:
    """
    Теперь все методы асинхронные (async), так как мы делаем запросы в БД.
    """
    
    async def _get_session(self, user_id: int):
        """Внутренний метод: получает или создает сессию пользователя"""
        async with async_session() as session:
            result = await session.execute(select(UserSession).where(UserSession.user_id == user_id))
            user_session = result.scalar_one_or_none()
            
            if not user_session:
                # Если сессии нет, создаем пользователя и сессию
                # Сначала User (из-за Foreign Key)
                await session.merge(User(user_id=user_id))
                user_session = UserSession(user_id=user_id, dialog_history=[])
                session.add(user_session)
                await session.commit()
                # Перезапрашиваем, чтобы объект был привязан
                result = await session.execute(select(UserSession).where(UserSession.user_id == user_id))
                user_session = result.scalar_one()
            
            return user_session

    async def check_user_exists(self, user_id: int, username: str = None, full_name: str = None):
        """Обновляет данные пользователя при старте"""
        async with async_session() as session:
            stmt = insert(User).values(
                user_id=user_id, 
                username=username, 
                full_name=full_name
            ).on_conflict_do_update(
                index_elements=['user_id'],
                set_={"username": username, "full_name": full_name}
            )
            await session.execute(stmt)
            
            # Создаем пустую сессию, если нет
            stmt_sess = insert(UserSession).values(user_id=user_id).on_conflict_do_nothing()
            await session.execute(stmt_sess)
            await session.commit()

    # --- ИСТОРИЯ ---
    async def get_history(self, user_id: int) -> List[dict]:
        async with async_session() as session:
            result = await session.execute(select(UserSession.dialog_history).where(UserSession.user_id == user_id))
            history = result.scalar_one_or_none()
            return history if history else []

    async def add_message(self, user_id: int, role: str, text: str):
        async with async_session() as session:
            # Получаем текущую историю
            result = await session.execute(select(UserSession.dialog_history).where(UserSession.user_id == user_id))
            history = result.scalar_one_or_none() or []
            
            # Обновляем
            history.append({"role": role, "text": text})
            if len(history) > MAX_HISTORY_MESSAGES:
                history = history[-MAX_HISTORY_MESSAGES:]
            
            await session.execute(
                update(UserSession).where(UserSession.user_id == user_id).values(dialog_history=history)
            )
            await session.commit()

    async def get_last_bot_message(self, user_id: int) -> Optional[str]:
        hist = await self.get_history(user_id)
        for msg in reversed(hist):
            if msg["role"] == "bot":
                return msg["text"]
        return None

    # --- ПРОДУКТЫ ---
    async def set_products(self, user_id: int, products: str):
        async with async_session() as session:
            await session.execute(
                update(UserSession).where(UserSession.user_id == user_id).values(products=products)
            )
            await session.commit()

    async def get_products(self, user_id: int) -> Optional[str]:
        async with async_session() as session:
            result = await session.execute(select(UserSession.products).where(UserSession.user_id == user_id))
            return result.scalar_one_or_none()

    async def append_products(self, user_id: int, new_products: str):
        current = await self.get_products(user_id)
        if current:
            updated = f"{current}, {new_products}"
        else:
            updated = new_products
        await self.set_products(user_id, updated)

    # --- СТАТУСЫ ---
    async def set_state(self, user_id: int, state: str):
        async with async_session() as session:
            await session.execute(
                update(UserSession).where(UserSession.user_id == user_id).values(state=state)
            )
            await session.commit()

    async def get_state(self, user_id: int) -> Optional[str]:
        async with async_session() as session:
            result = await session.execute(select(UserSession.state).where(UserSession.user_id == user_id))
            return result.scalar_one_or_none()

    async def clear_state(self, user_id: int):
        await self.set_state(user_id, None)

    # --- КАТЕГОРИИ И БЛЮДА ---
    async def set_categories(self, user_id: int, categories: List[str]):
        async with async_session() as session:
            await session.execute(
                update(UserSession).where(UserSession.user_id == user_id).values(available_categories=categories)
            )
            await session.commit()

    async def get_categories(self, user_id: int) -> List[str]:
        async with async_session() as session:
            result = await session.execute(select(UserSession.available_categories).where(UserSession.user_id == user_id))
            data = result.scalar_one_or_none()
            return data if data else []

    async def set_generated_dishes(self, user_id: int, dishes: List[dict]):
        async with async_session() as session:
            await session.execute(
                update(UserSession).where(UserSession.user_id == user_id).values(generated_dishes=dishes)
            )
            await session.commit()

    async def get_generated_dishes(self, user_id: int) -> List[dict]:
        async with async_session() as session:
            result = await session.execute(select(UserSession.generated_dishes).where(UserSession.user_id == user_id))
            data = result.scalar_one_or_none()
            return data if data else []

    async def get_generated_dish(self, user_id: int, index: int) -> Optional[str]:
        dishes = await self.get_generated_dishes(user_id)
        if 0 <= index < len(dishes):
            return dishes[index]['name']
        return None

    async def set_current_dish(self, user_id: int, dish_name: str):
        async with async_session() as session:
            await session.execute(
                update(UserSession).where(UserSession.user_id == user_id).values(current_dish=dish_name)
            )
            await session.commit()

    async def get_current_dish(self, user_id: int) -> Optional[str]:
        async with async_session() as session:
            result = await session.execute(select(UserSession.current_dish).where(UserSession.user_id == user_id))
            return result.scalar_one_or_none()

    # --- МУЛЬТИЯЗЫЧНОСТЬ ---
    async def set_user_lang(self, user_id: int, lang: str):
        async with async_session() as session:
            await session.execute(update(UserSession).where(UserSession.user_id == user_id).values(user_lang=lang))
            await session.commit()

    async def get_user_lang(self, user_id: int) -> str:
        async with async_session() as session:
            result = await session.execute(select(UserSession.user_lang).where(UserSession.user_id == user_id))
            return result.scalar_one_or_none() or 'ru'

    # --- ОЧИСТКА ---
    async def clear_session(self, user_id: int):
        """Сброс сессии в исходное состояние (кроме языка пользователя)"""
        async with async_session() as session:
            await session.execute(
                update(UserSession)
                .where(UserSession.user_id == user_id)
                .values(
                    products=None,
                    dialog_history=[],
                    state=None,
                    generated_dishes=[],
                    available_categories=[],
                    current_dish=None,
                    products_lang=None
                )
            )
            await session.commit()

state_manager = StateManager()