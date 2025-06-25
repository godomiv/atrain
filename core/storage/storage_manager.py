# atrain/core/storage/storage_manager.py
"""
Централизованный менеджер хранилищ
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import shutil
import zipfile

from .preset_storage import PresetStorage
from .tag_storage import TagStorage
from .category_storage import CategoryStorage
from ..models import PresetData, TagData
from ..utils import event_bus


class StorageManager:
    """Фасад для работы со всеми хранилищами"""
    
    def __init__(self):
        self.presets = PresetStorage()
        self.tags = TagStorage()
        self.categories = CategoryStorage()
        
        # Кеш для оптимизации
        self._cache_valid = False
        self._preset_cache = {}
        self._tag_cache = []
        
        # Подписываемся на события изменения данных
        event_bus().subscribe('preset_saved', self._invalidate_cache)
        event_bus().subscribe('preset_deleted', self._invalidate_cache)
        event_bus().subscribe('tag_saved', self._invalidate_cache)
        event_bus().subscribe('tag_deleted', self._invalidate_cache)
    
    def _invalidate_cache(self, data=None):
        """Инвалидировать кеш"""
        self._cache_valid = False
    
    # =====================
    # Пресеты
    # =====================
    
    def get_all_presets(self) -> Dict[str, PresetData]:
        """Получить все пресеты с кешированием"""
        if not self._cache_valid:
            self._preset_cache = self.presets.get_all_presets()
            self._cache_valid = True
        return self._preset_cache
    
    def get_preset(self, name: str) -> Optional[PresetData]:
        """Получить конкретный пресет"""
        return self.get_all_presets().get(name)
    
    def save_custom_preset(self, name: str, tags: List[str], 
                          format_type: str = "exr", 
                          category: str = "General") -> bool:
        """Сохранить пользовательский пресет"""
        preset = PresetData(
            name=name,
            tags=tags,
            format=format_type,
            category=category,
            source='custom'
        )
        return self.presets.save_preset(preset)
    
    def delete_custom_preset(self, name: str) -> bool:
        """Удалить пользовательский пресет"""
        return self.presets.delete_preset(name)
    
    def get_preset_categories(self) -> List[str]:
        """Получить категории пресетов"""
        return self.categories.get_preset_categories()
    
    def save_preset_categories(self, categories: List[str]) -> bool:
        """Сохранить категории пресетов"""
        return self.categories.set_preset_categories(categories)
    
    # =====================
    # Теги
    # =====================
    
    def get_all_tags(self) -> List[TagData]:
        """Получить все теги с кешированием"""
        if not self._cache_valid:
            self._tag_cache = self.tags.get_all_tags()
            self._cache_valid = True
        return self._tag_cache
    
    def get_tag(self, name: str) -> Optional[TagData]:
        """Получить конкретный тег"""
        for tag in self.get_all_tags():
            if tag.name == name:
                return tag
        return None
    
    def add_custom_tag(self, tag_data: Dict[str, Any]) -> bool:
        """Добавить пользовательский тег"""
        tag = TagData.from_dict(tag_data)
        tag.source = 'custom'
        return self.tags.save_tag(tag)
    
    def delete_custom_tag(self, name: str) -> bool:
        """Удалить пользовательский тег"""
        return self.tags.delete_tag(name)
    
    def get_tag_categories(self) -> List[str]:
        """Получить категории тегов"""
        return self.categories.get_tag_categories()
    
    def save_tag_categories(self, categories: List[str]) -> bool:
        """Сохранить категории тегов"""
        return self.categories.set_tag_categories(categories)
    
    # =====================
    # Группированные данные
    # =====================
    
    def get_all_tags_grouped(self) -> Dict[str, List[TagData]]:
        """Получить теги, сгруппированные по категориям"""
        all_tags = self.get_all_tags()
        categories = self.get_tag_categories()
        
        grouped = {'System': []}
        for category in categories:
            if category not in grouped:
                grouped[category] = []
        
        for tag in all_tags:
            if tag.source == 'default':
                grouped['System'].append(tag)
            else:
                category = tag.category if tag.category in categories else 'General'
                grouped[category].append(tag)
        
        return grouped
    
    def get_all_presets_grouped(self) -> Dict[str, List[Dict[str, Any]]]:
        """Получить пресеты, сгруппированные по категориям"""
        all_presets = self.get_all_presets()
        categories = self.get_preset_categories()
        
        grouped = {'System': []}
        for category in categories:
            if category not in grouped:
                grouped[category] = []
        
        for name, preset in all_presets.items():
            preset_info = {
                'name': name,
                'source': preset.source,
                'category': preset.category,
                'format': preset.format,
                'tags_count': len(preset.tags),
                'data': preset
            }
            
            if preset.source == 'default':
                grouped['System'].append(preset_info)
            else:
                category = preset.category if preset.category in categories else 'General'
                grouped[category].append(preset_info)
        
        return grouped
    
    # =====================
    # Перемещение между категориями
    # =====================
    
    def move_items_to_general_category(self, old_category: str, item_type: str):
        """Переместить элементы из удаленной категории в General"""
        if item_type == 'tag':
            all_tags = self.tags.get_all_tags()
            for tag in all_tags:
                if tag.category == old_category and tag.source == 'custom':
                    tag.category = 'General'
                    self.tags.save_tag(tag)
        
        elif item_type == 'preset':
            all_presets = self.presets.get_all_presets()
            for name, preset in all_presets.items():
                if preset.category == old_category and preset.source == 'custom':
                    preset.category = 'General'
                    self.presets.save_preset(preset)
    
    # =====================
    # Импорт/Экспорт
    # =====================
    
    def backup_all_settings(self, backup_dir: Optional[Path] = None) -> List[Path]:
        """
        Создать резервную копию всех настроек
        
        Returns:
            Список созданных файлов бэкапа
        """
        if backup_dir is None:
            backup_dir = self.presets.storage_dir / 'backups' / datetime.now().strftime('%Y%m%d_%H%M%S')
        
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_files = []
        
        # Копируем все файлы настроек
        for storage in [self.presets, self.tags, self.categories]:
            if storage.exists():
                dest = backup_dir / storage.filename
                shutil.copy2(storage.file_path, dest)
                backup_files.append(dest)
        
        # Создаем также zip архив
        zip_path = backup_dir.parent / f"{backup_dir.name}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for file in backup_files:
                zf.write(file, file.name)
        
        backup_files.append(zip_path)
        
        event_bus().publish('settings_backed_up', str(backup_dir))
        
        return backup_files
    
    def restore_from_backup(self, backup_path: Path) -> bool:
        """Восстановить настройки из резервной копии"""
        backup_path = Path(backup_path)
        
        try:
            if backup_path.is_file() and backup_path.suffix == '.zip':
                # Восстановление из zip архива
                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir:
                    with zipfile.ZipFile(backup_path, 'r') as zf:
                        zf.extractall(temp_dir)
                    
                    # Восстанавливаем файлы
                    for storage in [self.presets, self.tags, self.categories]:
                        temp_file = Path(temp_dir) / storage.filename
                        if temp_file.exists():
                            shutil.copy2(temp_file, storage.file_path)
            
            elif backup_path.is_dir():
                # Восстановление из папки
                for storage in [self.presets, self.tags, self.categories]:
                    backup_file = backup_path / storage.filename
                    if backup_file.exists():
                        shutil.copy2(backup_file, storage.file_path)
            
            else:
                print(f"StorageManager: Invalid backup path: {backup_path}")
                return False
            
            # Инвалидируем кеш
            self._invalidate_cache()
            
            event_bus().publish('settings_restored', str(backup_path))
            
            return True
            
        except Exception as e:
            print(f"StorageManager: Error restoring from backup: {e}")
            return False
    
    def export_settings(self, export_path: Path) -> bool:
        """Экспортировать все настройки в один файл"""
        try:
            export_data = {
                'version': '1.5',
                'exported': datetime.now().isoformat(),
                'presets': {},
                'tags': [],
                'categories': {
                    'tag_categories': self.get_tag_categories(),
                    'preset_categories': self.get_preset_categories()
                }
            }
            
            # Экспортируем пресеты
            for name, preset in self.get_all_presets().items():
                if preset.source == 'custom':
                    export_data['presets'][name] = preset.to_dict()
            
            # Экспортируем теги
            for tag in self.get_all_tags():
                if tag.source == 'custom':
                    export_data['tags'].append(tag.to_dict())
            
            # Сохраняем
            with open(export_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"StorageManager: Error exporting settings: {e}")
            return False
    
    def import_settings(self, import_path: Path, merge: bool = True) -> bool:
        """
        Импортировать настройки из файла
        
        Args:
            import_path: Путь к файлу импорта
            merge: True - объединить с существующими, False - заменить
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import json
                import_data = json.load(f)
            
            success = True
            
            # Импортируем категории
            if 'categories' in import_data:
                if 'tag_categories' in import_data['categories']:
                    categories = import_data['categories']['tag_categories']
                    if merge:
                        existing = self.get_tag_categories()
                        categories = list(set(existing + categories))
                    success &= self.save_tag_categories(categories)
                
                if 'preset_categories' in import_data['categories']:
                    categories = import_data['categories']['preset_categories']
                    if merge:
                        existing = self.get_preset_categories()
                        categories = list(set(existing + categories))
                    success &= self.save_preset_categories(categories)
            
            # Импортируем теги
            if 'tags' in import_data:
                for tag_dict in import_data['tags']:
                    tag = TagData.from_dict(tag_dict)
                    tag.source = 'custom'
                    
                    if not merge or not self.get_tag(tag.name):
                        success &= self.tags.save_tag(tag)
            
            # Импортируем пресеты
            if 'presets' in import_data:
                for name, preset_dict in import_data['presets'].items():
                    preset = PresetData.from_dict(name, preset_dict)
                    preset.source = 'custom'
                    
                    if not merge or not self.get_preset(name):
                        success &= self.presets.save_preset(preset)
            
            # Инвалидируем кеш
            self._invalidate_cache()
            
            event_bus().publish('settings_imported', str(import_path))
            
            return success
            
        except Exception as e:
            print(f"StorageManager: Error importing settings: {e}")
            return False
    
    # =====================
    # Информация о проекте
    # =====================
    
    def get_project_info(self) -> Dict[str, Any]:
        """Получить информацию о проекте и настройках"""
        storage_dir = self.presets.storage_dir
        
        info = {
            'project_directory': str(storage_dir.parent),
            'atrain_directory': str(storage_dir),
            'files': {
                'presets': str(self.presets.file_path),
                'tags': str(self.tags.file_path),
                'categories': str(self.categories.file_path)
            },
            'files_exist': {
                'presets': self.presets.exists(),
                'tags': self.tags.exists(),
                'categories': self.categories.exists()
            },
            'directory_writable': storage_dir.exists() and os.access(storage_dir, os.W_OK),
            'statistics': {
                'total_presets': len(self.get_all_presets()),
                'custom_presets': sum(1 for p in self.get_all_presets().values() if p.source == 'custom'),
                'total_tags': len(self.get_all_tags()),
                'custom_tags': sum(1 for t in self.get_all_tags() if t.source == 'custom'),
                'tag_categories': len(self.get_tag_categories()),
                'preset_categories': len(self.get_preset_categories())
            }
        }
        
        return info
    
    def validate_all(self) -> Dict[str, Any]:
        """Валидировать все данные"""
        results = {
            'valid': True,
            'preset_issues': {},
            'tag_issues': {},
            'file_issues': []
        }
        
        # Валидация пресетов
        for name, preset in self.get_all_presets().items():
            is_valid, errors = preset.validate()
            if not is_valid:
                results['preset_issues'][name] = errors
                results['valid'] = False
        
        # Валидация тегов
        tag_issues = self.tags.validate_all_tags()
        if tag_issues:
            results['tag_issues'] = tag_issues
            results['valid'] = False
        
        # Проверка файлов
        for storage in [self.presets, self.tags, self.categories]:
            if not storage.exists():
                results['file_issues'].append(f"Missing file: {storage.filename}")
                results['valid'] = False
        
        return results
