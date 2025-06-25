# atrain/core/models/__init__.py
"""
Модели данных A-Train
"""

from .tag_models import TagData, TagType
from .preset_models import PresetData, PresetInfo
from .path_models import PathContext, PathResult
from .batch_models import BatchOperation, BatchResult

__all__ = [
    'TagData',
    'TagType', 
    'PresetData',
    'PresetInfo',
    'PathContext',
    'PathResult',
    'BatchOperation',
    'BatchResult'
]
