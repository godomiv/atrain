# atrain/core/tags/base.py
"""
Базовый класс для стратегий тегов
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from PySide2 import QtWidgets, QtGui

from ..models import TagData


class TagStrategy(ABC):
    """Базовая стратегия обработки тега"""
    
    @abstractmethod
    def get_value(self, tag_data: TagData, context: Dict[str, Any]) -> str:
        """Получить значение тега"""
        pass
    
    @abstractmethod
    def get_display_name(self, tag_data: TagData) -> str:
        """Получить отображаемое имя"""
        pass
    
    @abstractmethod
    def get_display_value(self, tag_data: TagData, context: Dict[str, Any]) -> str:
        """Получить отображаемое значение для UI"""
        pass
    
    @abstractmethod
    def edit_dialog(self, tag_data: TagData, parent: Optional[QtWidgets.QWidget] = None) -> Optional[TagData]:
        """Показать диалог редактирования"""
        pass
    
    @abstractmethod
    def get_node_color(self) -> QtGui.QColor:
        """Получить цвет для отображения в графе"""
        pass
    
    @abstractmethod
    def get_node_shape(self) -> str:
        """Получить форму ноды: rect, rounded_rect, ellipse"""
        pass
    
    def validate(self, tag_data: TagData) -> Tuple[bool, list[str]]:
        """Валидация данных тега"""
        return tag_data.validate()
    
    def format_for_path(self, value: str, prev_part: str, next_part: str) -> str:
        """Форматирование значения для вставки в путь"""
        if not value:
            return ""
        
        # Добавляем разделитель если нужно
        if (prev_part and 
            not prev_part.endswith('/') and 
            not prev_part.endswith('_') and
            not prev_part.endswith('\\')):
            value = '_' + value
        
        return value
