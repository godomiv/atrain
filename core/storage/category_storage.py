# atrain/core/storage/category_storage.py
"""
Хранилище категорий
"""

from typing import List, Dict, Any
from datetime import datetime

from .file_storage import FileStorage
from ..utils import event_bus


class CategoryStorage(FileStorage):
    """Управление категориями для тегов и пресетов"""
    
    def __init__(self):
        super().__init__('atrain_categories.json')
        self._ensure_defaults()
    
    def _ensure_defaults(self):
        """Создать файл с дефолтными категориями если не существует"""
        if not self.exists():
            defaults = {
                "version": "1.5",
                "created": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat(),
                "tag_categories": ["System", "General", "Custom", "VFX", "Pipeline"],
                "preset_categories": ["System", "General", "Custom", "Daily", "Delivery"]
            }
            self.save(defaults)
    
    def get_tag_categories(self) -> List[str]:
        """Получить категории для тегов"""
        data = self.load()
        categories = data.get('tag_categories', [])
        
        # Гарантируем базовые категории
        base_categories = ['System', 'General', 'Custom']
        for cat in base_categories:
            if cat not in categories:
                categories.append(cat)
        
        return categories
    
    def get_preset_categories(self) -> List[str]:
        """Получить категории для пресетов"""
        data = self.load()
        categories = data.get('preset_categories', [])
        
        # Гарантируем базовые категории
        base_categories = ['System', 'General', 'Custom']
        for cat in base_categories:
            if cat not in categories:
                categories.append(cat)
        
        return categories
    
    def add_tag_category(self, category: str) -> bool:
        """Добавить категорию для тегов"""
        if not category or category.strip() == '':
            return False
        
        try:
            data = self.load()
            categories = data.get('tag_categories', [])
            
            if category not in categories:
                categories.append(category)
                data['tag_categories'] = categories
                data['last_modified'] = datetime.now().isoformat()
                
                success = self.save(data)
                
                if success:
                    event_bus().publish('tag_category_added', category)
                
                return success
            
            return True  # Уже существует
            
        except Exception as e:
            print(f"CategoryStorage: Error adding tag category: {e}")
            return False
    
    def add_preset_category(self, category: str) -> bool:
        """Добавить категорию для пресетов"""
        if not category or category.strip() == '':
            return False
        
        try:
            data = self.load()
            categories = data.get('preset_categories', [])
            
            if category not in categories:
                categories.append(category)
                data['preset_categories'] = categories
                data['last_modified'] = datetime.now().isoformat()
                
                success = self.save(data)
                
                if success:
                    event_bus().publish('preset_category_added', category)
                
                return success
            
            return True  # Уже существует
            
        except Exception as e:
            print(f"CategoryStorage: Error adding preset category: {e}")
            return False
    
    def remove_tag_category(self, category: str) -> bool:
        """Удалить категорию тегов"""
        # Не позволяем удалять системные категории
        if category in ['System', 'General']:
            print(f"CategoryStorage: Cannot remove system category '{category}'")
            return False
        
        try:
            data = self.load()
            categories = data.get('tag_categories', [])
            
            if category in categories:
                categories.remove(category)
                data['tag_categories'] = categories
                data['last_modified'] = datetime.now().isoformat()
                
                success = self.save(data)
                
                if success:
                    event_bus().publish('tag_category_removed', category)
                
                return success
            
            return False
            
        except Exception as e:
            print(f"CategoryStorage: Error removing tag category: {e}")
            return False
    
    def remove_preset_category(self, category: str) -> bool:
        """Удалить категорию пресетов"""
        # Не позволяем удалять системные категории
        if category in ['System', 'General']:
            print(f"CategoryStorage: Cannot remove system category '{category}'")
            return False
        
        try:
            data = self.load()
            categories = data.get('preset_categories', [])
            
            if category in categories:
                categories.remove(category)
                data['preset_categories'] = categories
                data['last_modified'] = datetime.now().isoformat()
                
                success = self.save(data)
                
                if success:
                    event_bus().publish('preset_category_removed', category)
                
                return success
            
            return False
            
        except Exception as e:
            print(f"CategoryStorage: Error removing preset category: {e}")
            return False
    
    def rename_tag_category(self, old_name: str, new_name: str) -> bool:
        """Переименовать категорию тегов"""
        if old_name == new_name:
            return True
        
        if old_name in ['System', 'General']:
            print(f"CategoryStorage: Cannot rename system category '{old_name}'")
            return False
        
        try:
            data = self.load()
            categories = data.get('tag_categories', [])
            
            if old_name in categories and new_name not in categories:
                index = categories.index(old_name)
                categories[index] = new_name
                data['tag_categories'] = categories
                data['last_modified'] = datetime.now().isoformat()
                
                success = self.save(data)
                
                if success:
                    event_bus().publish('tag_category_renamed', {
                        'old_name': old_name,
                        'new_name': new_name
                    })
                
                return success
            
            return False
            
        except Exception as e:
            print(f"CategoryStorage: Error renaming tag category: {e}")
            return False
    
    def rename_preset_category(self, old_name: str, new_name: str) -> bool:
        """Переименовать категорию пресетов"""
        if old_name == new_name:
            return True
        
        if old_name in ['System', 'General']:
            print(f"CategoryStorage: Cannot rename system category '{old_name}'")
            return False
        
        try:
            data = self.load()
            categories = data.get('preset_categories', [])
            
            if old_name in categories and new_name not in categories:
                index = categories.index(old_name)
                categories[index] = new_name
                data['preset_categories'] = categories
                data['last_modified'] = datetime.now().isoformat()
                
                success = self.save(data)
                
                if success:
                    event_bus().publish('preset_category_renamed', {
                        'old_name': old_name,
                        'new_name': new_name
                    })
                
                return success
            
            return False
            
        except Exception as e:
            print(f"CategoryStorage: Error renaming preset category: {e}")
            return False
    
    def set_tag_categories(self, categories: List[str]) -> bool:
        """Установить полный список категорий тегов"""
        # Обязательно включаем системные
        required = ['System', 'General']
        for cat in required:
            if cat not in categories:
                categories.insert(0, cat)
        
        try:
            data = self.load()
            data['tag_categories'] = categories
            data['last_modified'] = datetime.now().isoformat()
            
            success = self.save(data)
            
            if success:
                event_bus().publish('tag_categories_updated', categories)
            
            return success
            
        except Exception as e:
            print(f"CategoryStorage: Error setting tag categories: {e}")
            return False
    
    def set_preset_categories(self, categories: List[str]) -> bool:
        """Установить полный список категорий пресетов"""
        # Обязательно включаем системные
        required = ['System', 'General']
        for cat in required:
            if cat not in categories:
                categories.insert(0, cat)
        
        try:
            data = self.load()
            data['preset_categories'] = categories
            data['last_modified'] = datetime.now().isoformat()
            
            success = self.save(data)
            
            if success:
                event_bus().publish('preset_categories_updated', categories)
            
            return success
            
        except Exception as e:
            print(f"CategoryStorage: Error setting preset categories: {e}")
            return False
