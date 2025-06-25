# atrain/core/event_bus.py
"""
Редирект на новую систему событий для совместимости
"""

from .utils.events import EventBus, event_bus

# Экспортируем для обратной совместимости
__all__ = ['EventBus', 'event_bus']

# Создаём instance метод для совместимости
EventBus.instance = classmethod(lambda cls: EventBus())
