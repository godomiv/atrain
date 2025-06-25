# atrain/core/storage/preset_storage.py
"""
Хранилище пресетов
"""

from typing import Dict, List, Optional
from datetime import datetime
import getpass

from .file_storage import FileStorage
from ..models import PresetData
from ..utils import event_bus


class PresetStorage(FileStorage):
    """Управление хранением пресетов"""
    
    def __init__(self):
        super().__init__('atrain_presets.json')
        self._defaults_storage = FileStorage('atrain_defaults.json')
        self._ensure_defaults()
    
    def _ensure_defaults(self):
        """Создать файл с дефолтными пресетами если не существует"""
        if not self._defaults_storage.exists():
            defaults = {
                "version": "1.5",
                "created": datetime.now().isoformat(),
                "description": "A-Train default presets",
                "presets": {
                    "Default": {
                        "tags": ["project path", "shot name", "version"],
                        "format": "exr",
                        "category": "System",
                        "created": datetime.now().isoformat(),
                        "author": "system",
                        "description": "Basic project/shot/version pattern"
                    },
                    "Review": {
                        "tags": ["shot name", "user"],
                        "format": "jpeg", 
                        "category": "System",
                        "created": datetime.now().isoformat(),
                        "author": "system",
                        "description": "Simple review output"
                    },
                    "Dailies": {
                        "tags": ["project path", "shot name", "department", "version"],
                        "format": "mov",
                        "category": "System",
                        "created": datetime.now().isoformat(),
                        "author": "system",
                        "description": "Dailies output with department"
                    }
                }
            }
            self._defaults_storage.save(defaults)
    
    def get_all_presets(self) -> Dict[str, PresetData]:
        """Получить все пресеты (дефолтные + пользовательские)"""
        presets = {}
        
        # Загружаем дефолтные
        defaults_data = self._defaults_storage.load()
        for name, data in defaults_data.get('presets', {}).items():
            preset = PresetData.from_dict(name, data)
            preset.source = 'default'
            presets[name] = preset
        
        # Загружаем пользовательские
        custom_data = self.load()
        for name, data in custom_data.get('presets', {}).items():
            preset = PresetData.from_dict(name, data)
            preset.source = 'custom'
            presets[name] = preset
        
        return presets
    
    def get_preset(self, name: str) -> Optional[PresetData]:
        """Получить конкретный пресет"""
        all_presets = self.get_all_presets()
        return all_presets.get(name)
    
    def save_preset(self, preset: PresetData) -> bool:
        """Сохранить пользовательский пресет"""
        if preset.source == 'default':
            print("PresetStorage: Cannot modify default presets")
            return False
        
        try:
            # Загружаем существующие данные
            data = self.load()
            if 'presets' not in data:
                data['presets'] = {}
            
            # Обновляем метаданные
            preset.modified = datetime.now().isoformat()
            preset.author = preset.author or getpass.getuser()
            
            # Сохраняем пресет
            data['presets'][preset.name] = preset.to_dict()
            
            # Обновляем метаданные файла
            data['version'] = "1.5"
            data['last_modified'] = datetime.now().isoformat()
            
            success = self.save(data)
            
            if success:
                event_bus().publish('preset_saved', preset)
            
            return success
            
        except Exception as e:
            print(f"PresetStorage: Error saving preset '{preset.name}': {e}")
            return False
    
    def delete_preset(self, name: str) -> bool:
        """Удалить пользовательский пресет"""
        preset = self.get_preset(name)
        if not preset:
            return False
        
        if preset.source == 'default':
            print("PresetStorage: Cannot delete default presets")
            return False
        
        try:
            data = self.load()
            if 'presets' in data and name in data['presets']:
                del data['presets'][name]
                data['last_modified'] = datetime.now().isoformat()
                
                success = self.save(data)
                
                if success:
                    event_bus().publish('preset_deleted', name)
                
                return success
            
            return False
            
        except Exception as e:
            print(f"PresetStorage: Error deleting preset '{name}': {e}")
            return False
    
    def get_presets_by_category(self, category: str) -> Dict[str, PresetData]:
        """Получить пресеты по категории"""
        all_presets = self.get_all_presets()
        return {
            name: preset for name, preset in all_presets.items()
            if preset.category == category
        }
    
    def get_preset_categories(self) -> List[str]:
        """Получить список всех категорий пресетов"""
        categories = set()
        
        for preset in self.get_all_presets().values():
            categories.add(preset.category)
        
        # Гарантируем наличие базовых категорий
        categories.update(['System', 'General', 'Custom'])
        
        return sorted(categories)
    
    def rename_preset(self, old_name: str, new_name: str) -> bool:
        """Переименовать пресет"""
        if old_name == new_name:
            return True
        
        preset = self.get_preset(old_name)
        if not preset or preset.source == 'default':
            return False
        
        # Проверяем что новое имя не занято
        if self.get_preset(new_name):
            print(f"PresetStorage: Preset '{new_name}' already exists")
            return False
        
        try:
            data = self.load()
            if 'presets' in data and old_name in data['presets']:
                # Переносим данные
                data['presets'][new_name] = data['presets'][old_name]
                del data['presets'][old_name]
                
                data['last_modified'] = datetime.now().isoformat()
                
                success = self.save(data)
                
                if success:
                    event_bus().publish('preset_renamed', {
                        'old_name': old_name,
                        'new_name': new_name
                    })
                
                return success
            
            return False
            
        except Exception as e:
            print(f"PresetStorage: Error renaming preset: {e}")
            return False
    
    def duplicate_preset(self, name: str, new_name: str) -> Optional[PresetData]:
        """Дублировать пресет"""
        preset = self.get_preset(name)
        if not preset:
            return None
        
        # Создаем копию
        new_preset = PresetData(
            name=new_name,
            tags=preset.tags.copy(),
            format=preset.format,
            category=preset.category,
            source='custom',
            author=getpass.getuser(),
            description=f"Copy of {preset.name}"
        )
        
        if self.save_preset(new_preset):
            return new_preset
        
        return None
    
    def export_presets(self, preset_names: List[str], export_path: str) -> bool:
        """Экспортировать выбранные пресеты"""
        try:
            export_data = {
                'version': '1.5',
                'exported': datetime.now().isoformat(),
                'presets': {}
            }
            
            for name in preset_names:
                preset = self.get_preset(name)
                if preset:
                    export_data['presets'][name] = preset.to_dict()
            
            with open(export_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"PresetStorage: Error exporting presets: {e}")
            return False
    
    def import_presets(self, import_path: str, overwrite: bool = False) -> int:
        """
        Импортировать пресеты из файла
        
        Returns:
            Количество импортированных пресетов
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import json
                import_data = json.load(f)
            
            imported_count = 0
            
            for name, preset_data in import_data.get('presets', {}).items():
                # Проверяем существование
                existing = self.get_preset(name)
                if existing and not overwrite:
                    continue
                
                # Создаем пресет
                preset = PresetData.from_dict(name, preset_data)
                preset.source = 'custom'
                preset.modified = datetime.now().isoformat()
                
                if self.save_preset(preset):
                    imported_count += 1
            
            if imported_count > 0:
                event_bus().publish('presets_imported', imported_count)
            
            return imported_count
            
        except Exception as e:
            print(f"PresetStorage: Error importing presets: {e}")
            return 0
