# atrain/core/storage/tag_storage.py
"""
Хранилище тегов
"""

from typing import Dict, List, Optional
from datetime import datetime
import getpass

from .file_storage import FileStorage
from ..models import TagData, TagType
from ..utils import event_bus


class TagStorage(FileStorage):
    """Управление хранением тегов"""
    
    def __init__(self):
        super().__init__('atrain_tags.json')
        self._defaults_storage = FileStorage('atrain_tag_defaults.json')
        self._ensure_defaults()
    
    def _ensure_defaults(self):
        """Создать файл с дефолтными тегами если не существует"""
        if not self._defaults_storage.exists():
            defaults = {
                "version": "1.5",
                "created": datetime.now().isoformat(),
                "description": "A-Train default tags",
                "tags": [
                    {
                        "name": "project path",
                        "type": "dynamic",
                        "default": "[project_path]",
                        "category": "System"
                    },
                    {
                        "name": "shot name",
                        "type": "dynamic",
                        "default": "[shot_name]",
                        "category": "System"
                    },
                    {
                        "name": "version",
                        "type": "version",
                        "version": "v01",
                        "category": "System"
                    },
                    {
                        "name": "/",
                        "type": "separator",
                        "value": "/",
                        "category": "System"
                    },
                    {
                        "name": "_",
                        "type": "separator",
                        "value": "_",
                        "category": "System"
                    },
                    {
                        "name": "user",
                        "type": "dynamic",
                        "default": "[user]",
                        "category": "System"
                    },
                    {
                        "name": "[read_name]",
                        "type": "text",
                        "default": "[read_name]",
                        "category": "System"
                    },
                    {
                        "name": "department",
                        "type": "dynamic",
                        "default": "[department]",
                        "category": "System"
                    },
                    {
                        "name": "task",
                        "type": "dynamic",
                        "default": "[task]",
                        "category": "System"
                    },
                    {
                        "name": "sequence",
                        "type": "dynamic",
                        "default": "[sequence]",
                        "category": "System"
                    }
                ]
            }
            self._defaults_storage.save(defaults)
    
    def get_all_tags(self) -> List[TagData]:
        """Получить все теги (дефолтные + пользовательские)"""
        tags = []
        
        # Загружаем дефолтные
        defaults_data = self._defaults_storage.load()
        for tag_dict in defaults_data.get('tags', []):
            tag = TagData.from_dict(tag_dict)
            tag.source = 'default'
            tags.append(tag)
        
        # Загружаем пользовательские
        custom_data = self.load()
        for tag_dict in custom_data.get('tags', []):
            tag = TagData.from_dict(tag_dict)
            tag.source = 'custom'
            tags.append(tag)
        
        return tags
    
    def get_tag(self, name: str) -> Optional[TagData]:
        """Получить конкретный тег по имени"""
        for tag in self.get_all_tags():
            if tag.name == name:
                return tag
        return None
    
    def save_tag(self, tag: TagData) -> bool:
        """Сохранить пользовательский тег"""
        if tag.source == 'default':
            print("TagStorage: Cannot modify default tags")
            return False
        
        try:
            # Загружаем существующие данные
            data = self.load()
            if 'tags' not in data:
                data['tags'] = []
            
            # Ищем существующий тег
            tag_index = -1
            for i, existing_tag in enumerate(data['tags']):
                if existing_tag.get('name') == tag.name:
                    tag_index = i
                    break
            
            # Обновляем метаданные
            tag.author = tag.author or getpass.getuser()
            tag_dict = tag.to_dict()
            
            # Сохраняем или обновляем
            if tag_index >= 0:
                data['tags'][tag_index] = tag_dict
            else:
                data['tags'].append(tag_dict)
            
            # Обновляем метаданные файла
            data['version'] = "1.5"
            data['last_modified'] = datetime.now().isoformat()
            
            success = self.save(data)
            
            if success:
                event_bus().publish('tag_saved', tag)
            
            return success
            
        except Exception as e:
            print(f"TagStorage: Error saving tag '{tag.name}': {e}")
            return False
    
    def delete_tag(self, name: str) -> bool:
        """Удалить пользовательский тег"""
        tag = self.get_tag(name)
        if not tag:
            return False
        
        if tag.source == 'default':
            print("TagStorage: Cannot delete default tags")
            return False
        
        try:
            data = self.load()
            if 'tags' in data:
                data['tags'] = [
                    t for t in data['tags'] 
                    if t.get('name') != name
                ]
                data['last_modified'] = datetime.now().isoformat()
                
                success = self.save(data)
                
                if success:
                    event_bus().publish('tag_deleted', name)
                
                return success
            
            return False
            
        except Exception as e:
            print(f"TagStorage: Error deleting tag '{name}': {e}")
            return False
    
    def get_tags_by_type(self, tag_type: TagType) -> List[TagData]:
        """Получить теги по типу"""
        return [
            tag for tag in self.get_all_tags()
            if tag.type == tag_type
        ]
    
    def get_tags_by_category(self, category: str) -> List[TagData]:
        """Получить теги по категории"""
        return [
            tag for tag in self.get_all_tags()
            if tag.category == category
        ]
    
    def get_tag_categories(self) -> List[str]:
        """Получить список всех категорий тегов"""
        categories = set()
        
        for tag in self.get_all_tags():
            categories.add(tag.category)
        
        # Гарантируем наличие базовых категорий
        categories.update(['System', 'General', 'Custom'])
        
        return sorted(categories)
    
    def rename_tag(self, old_name: str, new_name: str) -> bool:
        """Переименовать тег"""
        if old_name == new_name:
            return True
        
        tag = self.get_tag(old_name)
        if not tag or tag.source == 'default':
            return False
        
        # Проверяем что новое имя не занято
        if self.get_tag(new_name):
            print(f"TagStorage: Tag '{new_name}' already exists")
            return False
        
        # Обновляем имя
        tag.name = new_name
        
        # Удаляем старый и сохраняем новый
        if self.delete_tag(old_name):
            return self.save_tag(tag)
        
        return False
    
    def create_expression_tag(self, name: str, expression: str, 
                            category: str = "General") -> Optional[TagData]:
        """Создать expression тег"""
        if self.get_tag(name):
            print(f"TagStorage: Tag '{name}' already exists")
            return None
        
        tag = TagData(
            name=name,
            type=TagType.EXPRESSION,
            expression=expression,
            category=category,
            source='custom',
            author=getpass.getuser()
        )
        
        if self.save_tag(tag):
            return tag
        
        return None
    
    def validate_all_tags(self) -> Dict[str, List[str]]:
        """Валидировать все теги"""
        issues = {}
        
        for tag in self.get_all_tags():
            is_valid, errors = tag.validate()
            if not is_valid:
                issues[tag.name] = errors
        
        return issues
