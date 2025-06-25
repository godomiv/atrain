# atrain/core/models/preset_models.py
"""
Модели данных для пресетов
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class PresetData:
    """Модель данных пресета"""
    name: str
    tags: List[str] = field(default_factory=list)
    format: str = "exr"
    category: str = "General"
    source: str = "custom"
    
    # Метаданные
    created: Optional[str] = None
    modified: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    version: str = "1.0"
    
    def __post_init__(self):
        """Инициализация после создания"""
        if not self.created:
            self.created = datetime.now().isoformat()
        if not self.modified:
            self.modified = self.created
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'tags': self.tags,
            'format': self.format,
            'category': self.category,
            'source': self.source,
            'created': self.created,
            'modified': self.modified,
            'author': self.author,
            'description': self.description,
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'PresetData':
        """Создание из словаря"""
        return cls(name=name, **data)
    
    def validate(self) -> tuple[bool, list[str]]:
        """Валидация пресета"""
        errors = []
        
        if not self.name:
            errors.append("Preset name is required")
        
        if not self.tags:
            errors.append("Preset must contain at least one tag")
        
        if not self.format:
            errors.append("Output format is required")
        
        return len(errors) == 0, errors
    
    def update_modified(self):
        """Обновить время модификации"""
        self.modified = datetime.now().isoformat()


@dataclass
class PresetInfo:
    """Информация о пресете для UI"""
    name: str
    category: str
    tags_count: int
    format: str
    source: str
    created: str
    author: str = ""
    description: str = ""
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    
    @classmethod
    def from_preset_data(cls, preset: PresetData) -> 'PresetInfo':
        """Создание из PresetData"""
        is_valid, errors = preset.validate()
        
        return cls(
            name=preset.name,
            category=preset.category,
            tags_count=len(preset.tags),
            format=preset.format,
            source=preset.source,
            created=preset.created or "",
            author=preset.author or "",
            description=preset.description or "",
            is_valid=is_valid,
            validation_errors=errors
        )
