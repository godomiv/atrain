# atrain/core/storage/__init__.py
"""
Система хранения данных A-Train
"""

from .file_storage import FileStorage
from .preset_storage import PresetStorage
from .tag_storage import TagStorage
from .category_storage import CategoryStorage
from .storage_manager import StorageManager

__all__ = [
    'FileStorage',
    'PresetStorage',
    'TagStorage',
    'CategoryStorage',
    'StorageManager'
]
