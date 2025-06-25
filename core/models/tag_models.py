# atrain/core/models/tag_models.py
"""
Модели данных для тегов
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any


class TagType(Enum):
    """Типы тегов"""
    TEXT = "text"
    SEPARATOR = "separator"
    FORMAT = "format"
    VERSION = "version"
    DYNAMIC = "dynamic"
    EXPRESSION = "expression"


@dataclass
class TagData:
    """Модель данных тега"""
    name: str
    type: TagType
    category: str = "General"
    source: str = "custom"
    
    # Значения для разных типов
    default: Optional[str] = None
    value: Optional[str] = None
    expression: Optional[str] = None
    
    # Для format тегов
    format: Optional[str] = None
    padding: str = "%04d"
    
    # Для version тегов
    version: str = "v01"
    
    # Метаданные
    created: Optional[str] = None
    author: Optional[str] = None
    
    def __post_init__(self):
        """Преобразование типа если передан как строка"""
        if isinstance(self.type, str):
            self.type = TagType(self.type)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для сохранения"""
        data = {
            'name': self.name,
            'type': self.type.value,
            'category': self.category,
            'source': self.source
        }
        
        # Добавляем только непустые поля
        optional_fields = [
            'default', 'value', 'expression', 'format', 
            'padding', 'version', 'created', 'author'
        ]
        
        for field_name in optional_fields:
            field_value = getattr(self, field_name, None)
            if field_value is not None:
                data[field_name] = field_value
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TagData':
        """Создание из словаря"""
        # Копируем данные чтобы не изменять оригинал
        tag_data = data.copy()
        
        # Преобразуем тип в enum
        if 'type' in tag_data:
            tag_data['type'] = TagType(tag_data['type'])
        
        return cls(**tag_data)
    
    def get_display_value(self) -> str:
        """Получить отображаемое значение тега"""
        if self.type == TagType.SEPARATOR:
            return self.value or '/'
        elif self.type == TagType.FORMAT:
            return self.format or 'exr'
        elif self.type == TagType.VERSION:
            return self.version
        elif self.type == TagType.EXPRESSION:
            return self.expression or ''
        else:
            return self.default or self.name
    
    def validate(self) -> tuple[bool, list[str]]:
        """Валидация тега"""
        errors = []
        
        if not self.name:
            errors.append("Tag name is required")
        
        # Валидация по типу
        if self.type == TagType.SEPARATOR and not self.value:
            self.value = '/'
        
        elif self.type == TagType.FORMAT and not self.format:
            errors.append("Format type is required for format tags")
        
        elif self.type == TagType.EXPRESSION and not self.expression:
            errors.append("Expression is required for expression tags")
        
        return len(errors) == 0, errors
