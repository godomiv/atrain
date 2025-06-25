# atrain/core/preset_manager.py
"""
Редирект на адаптер для совместимости
"""

# Импортируем адаптер вместо старого кода
from .preset_manager_adapter import PresetManager

# Для обратной совместимости экспортируем также старые классы если они использовались
__all__ = ['PresetManager']
