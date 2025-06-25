# atrain/core/tags/factory.py
"""
Фабрика стратегий тегов
"""

from typing import Dict, Optional
from ..models import TagType
from .base import TagStrategy
from .strategies import (
    TextTagStrategy,
    SeparatorTagStrategy,
    FormatTagStrategy,
    VersionTagStrategy,
    DynamicTagStrategy,
    ExpressionTagStrategy
)


class TagStrategyFactory:
    """Фабрика для создания стратегий тегов"""
    
    def __init__(self):
        # Создаем экземпляры стратегий (они stateless, можно переиспользовать)
        self._strategies: Dict[TagType, TagStrategy] = {
            TagType.TEXT: TextTagStrategy(),
            TagType.SEPARATOR: SeparatorTagStrategy(),
            TagType.FORMAT: FormatTagStrategy(),
            TagType.VERSION: VersionTagStrategy(),
            TagType.DYNAMIC: DynamicTagStrategy(),
            TagType.EXPRESSION: ExpressionTagStrategy()
        }
    
    def get_strategy(self, tag_type: TagType) -> Optional[TagStrategy]:
        """Получить стратегию для типа тега"""
        return self._strategies.get(tag_type)
    
    def register_strategy(self, tag_type: TagType, strategy: TagStrategy):
        """Зарегистрировать кастомную стратегию"""
        self._strategies[tag_type] = strategy
    
    def get_available_types(self) -> list[TagType]:
        """Получить список доступных типов"""
        return list(self._strategies.keys())


# Глобальная фабрика
_tag_factory_instance = None

def tag_factory() -> TagStrategyFactory:
    """Получить глобальную фабрику стратегий"""
    global _tag_factory_instance
    if _tag_factory_instance is None:
        _tag_factory_instance = TagStrategyFactory()
    return _tag_factory_instance
