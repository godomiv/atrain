# atrain/core/path_builder_adapter.py
"""
Адаптер для старого PathBuilder API
"""

from .path_builder import PathBuilder as NewPathBuilder
from .models import TagData, TagType


class PathBuilder:
    """Адаптер для совместимости со старым API"""
    
    def __init__(self):
        self._builder = NewPathBuilder()
        self.tags = []  # Для совместимости
        self.context_vars = {}
        self.dynamic_handlers = {
            'shot name': lambda: self._builder._context.shot_name or 'shot_name',
            'project path': lambda: self._builder._context.project_path or '/project/path',
            'user': lambda: self._builder._context.user_name or 'user',
            '[read_name]': lambda: self._builder._context.read_name or 'read_name',
        }
    
    def clear_tags(self):
        """Очистить все теги"""
        self._builder.clear()
        self.tags.clear()
    
    def add_tag(self, tag_data):
        """Добавить тег (старый формат - словарь)"""
        # Конвертируем старый формат в новый
        if isinstance(tag_data, dict):
            tag = TagData.from_dict(tag_data)
        else:
            tag = tag_data
        
        index = self._builder.add_tag(tag)
        self.tags.append(tag_data)  # Сохраняем для совместимости
        return index
    
    def remove_tag(self, index):
        """Удалить тег по индексу"""
        if self._builder.remove_tag(index):
            if 0 <= index < len(self.tags):
                self.tags.pop(index)
            return True
        return False
    
    def build_path(self, live_preview=False):
        """Построить путь"""
        # Обновляем контекст
        self._builder.update_context(live_preview=live_preview)
        
        # Строим путь
        return self._builder.build_path()
    
    def set_context_var(self, key, value):
        """Установить контекстную переменную"""
        self.context_vars[key] = value
        self._builder.update_context(**{key: value})
    
    def validate_path(self, path):
        """Валидировать путь"""
        return self._builder.validate_path(path)
    
    # Методы для совместимости с UI
    def _evaluate_expression_live(self, expression):
        """Оценка expression"""
        try:
            import nuke
            if '[value root.frame]' in expression:
                return expression.replace('[value root.frame]', str(nuke.frame()))
            return expression
        except:
            return expression
    
    def _get_shot_name(self):
        """Получить имя шота"""
        return self.dynamic_handlers['shot name']()
    
    def _get_project_path(self):
        """Получить путь проекта"""
        return self.dynamic_handlers['project path']()
    
    def _get_user_name(self):
        """Получить имя пользователя"""
        return self.dynamic_handlers['user']()
    
    def _get_read_name(self):
        """Получить имя Read ноды"""
        return self.dynamic_handlers['[read_name]']()


# Для совместимости экспортируем функцию
def build_path_from_tags(tags, live_preview=False):
    """Построить путь из списка тегов"""
    builder = PathBuilder()
    for tag in tags:
        builder.add_tag(tag)
    return builder.build_path(live_preview)
