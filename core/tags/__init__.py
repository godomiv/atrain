# atrain/core/tags/__init__.py
"""
Система обработки тегов
"""

from .base import TagStrategy
from .strategies import (
    TextTagStrategy,
    SeparatorTagStrategy,
    FormatTagStrategy,
    VersionTagStrategy,
    DynamicTagStrategy,
    ExpressionTagStrategy
)
from .factory import TagStrategyFactory, tag_factory

__all__ = [
    'TagStrategy',
    'TextTagStrategy',
    'SeparatorTagStrategy',
    'FormatTagStrategy',
    'VersionTagStrategy',
    'DynamicTagStrategy',
    'ExpressionTagStrategy',
    'TagStrategyFactory',
    'tag_factory'
]
