# atrain/core/preset_manager_adapter.py
"""
Адаптер для совместимости старого PresetManager с новой архитектурой
"""

from .storage import StorageManager
from .models import TagData, PresetData


class PresetManager:
    """
    Адаптер для старого PresetManager API
    Использует новый StorageManager внутри
    """
    
    def __init__(self):
        self._storage = StorageManager()
        
        # Для совместимости
        self.cache = type('obj', (object,), {
            'invalidate': lambda: None,
            'get': lambda key, func: func()
        })()
    
    def get_all_presets(self):
        """Получить все пресеты в старом формате"""
        presets = {}
        for name, preset in self._storage.get_all_presets().items():
            presets[name] = preset.to_dict()
        return presets
    
    def get_all_tags(self):
        """Получить все теги в старом формате"""
        return [tag.to_dict() for tag in self._storage.get_all_tags()]
    
    def get_all_tags_grouped(self):
        """Получить теги сгруппированные по категориям"""
        grouped = self._storage.get_all_tags_grouped()
        # Конвертируем TagData обратно в словари для совместимости
        result = {}
        for category, tags in grouped.items():
            result[category] = [tag.to_dict() for tag in tags]
        return result
    
    def get_all_presets_grouped(self):
        """Получить пресеты сгруппированные по категориям"""
        return self._storage.get_all_presets_grouped()
    
    def get_tag_categories(self):
        """Получить категории тегов"""
        return self._storage.get_tag_categories()
    
    def get_preset_categories(self):
        """Получить категории пресетов"""
        return self._storage.get_preset_categories()
    
    def save_custom_preset(self, name, tag_names, format_type="exr", category="General"):
        """Сохранить пользовательский пресет"""
        return self._storage.save_custom_preset(name, tag_names, format_type, category)
    
    def add_custom_tag(self, tag_data):
        """Добавить пользовательский тег"""
        return self._storage.add_custom_tag(tag_data)
    
    def delete_custom_preset(self, name):
        """Удалить пользовательский пресет"""
        return self._storage.delete_custom_preset(name)
    
    def save_tag_categories(self, categories):
        """Сохранить категории тегов"""
        return self._storage.save_tag_categories(categories)
    
    def save_preset_categories(self, categories):
        """Сохранить категории пресетов"""
        return self._storage.save_preset_categories(categories)
    
    def move_items_to_general_category(self, old_category, item_type):
        """Переместить элементы в General категорию"""
        return self._storage.move_items_to_general_category(old_category, item_type)
    
    def get_project_info(self):
        """Получить информацию о проекте"""
        return self._storage.get_project_info()
    
    # Методы для совместимости со старым кодом
    def load_defaults(self):
        """Заглушка для совместимости"""
        return {'default_tags': [], 'default_presets': {}}
    
    def load_custom(self):
        """Заглушка для совместимости"""
        return {'custom_tags': [], 'custom_presets': {}}
    
    def save_custom(self, data):
        """Заглушка для совместимости"""
        pass
    
    def load_categories(self):
        """Заглушка для совместимости"""
        return {
            'tag_categories': self.get_tag_categories(),
            'preset_categories': self.get_preset_categories()
        }
    
    def save_categories(self, data):
        """Заглушка для совместимости"""
        pass
