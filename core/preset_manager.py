# atrain/core/preset_manager.py
"""
Менеджер пресетов A-Train - ИСПРАВЛЕНО: JSON в проекте с fallback
"""

import os
import json
import datetime
import getpass
from typing import Dict, List, Any, Optional

try:
    import nuke
    NUKE_AVAILABLE = True
except ImportError:
    nuke = None
    NUKE_AVAILABLE = False

from .event_bus import EventBus

class CachedDataManager:
    """Менеджер кеширования данных с TTL"""
    
    def __init__(self, default_ttl=5.0):
        self.cache = {}
        self.timestamps = {}
        self.default_ttl = default_ttl
    
    def get(self, key, loader_func, ttl=None):
        """Получить данные с кешированием"""
        if ttl is None:
            ttl = self.default_ttl
            
        if self.is_valid(key, ttl):
            return self.cache[key]
        
        data = loader_func()
        self.cache[key] = data
        self.timestamps[key] = datetime.datetime.now().timestamp()
        return data
    
    def is_valid(self, key, ttl):
        """Проверить валидность кеша"""
        if key not in self.cache:
            return False
        
        age = datetime.datetime.now().timestamp() - self.timestamps.get(key, 0)
        return age < ttl
    
    def invalidate(self, key=None):
        """Инвалидировать кеш"""
        if key:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
        else:
            self.cache.clear()
            self.timestamps.clear()

class PresetManager:
    """ИСПРАВЛЕНО: Менеджер пресетов с fallback при ошибке доступа"""
    
    def __init__(self):
        # ИСПРАВЛЕНО: Пытаемся создать в проекте, fallback к пользовательской папке
        self.project_dir, self.atrain_dir = self._get_safe_directories()
        
        self.defaults_file = os.path.join(self.atrain_dir, 'atrain_defaults.json')
        self.custom_file = os.path.join(self.atrain_dir, 'atrain_custom.json')
        self.categories_file = os.path.join(self.atrain_dir, 'atrain_categories.json')
        
        self.cache = CachedDataManager()
        self.event_bus = EventBus.instance()
        
        self.ensure_files()
        print(f"PresetManager: Initialized with directory: {self.atrain_dir}")
    
    def _get_safe_directories(self):
        """ИСПРАВЛЕНО: Получить безопасные директории с fallback"""
        project_dir = self._try_get_project_directory()
        atrain_dir = os.path.join(project_dir, '.atrain')
        
        if self._can_create_directory(atrain_dir):
            print(f"PresetManager: Using project directory: {project_dir}")
            return project_dir, atrain_dir
        
        # Fallback к пользовательской папке
        user_dir = os.path.expanduser('~')
        user_atrain_dir = os.path.join(user_dir, '.nuke', 'atrain')
        
        if self._can_create_directory(user_atrain_dir):
            print(f"PresetManager: Fallback to user directory: {user_dir}")
            return user_dir, user_atrain_dir
        
        # Последний fallback - temp папка
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_atrain_dir = os.path.join(temp_dir, 'atrain_settings')
        
        print(f"PresetManager: Final fallback to temp directory: {temp_dir}")
        return temp_dir, temp_atrain_dir
    
    def _try_get_project_directory(self):
        """Попытка определить папку проекта"""
        try:
            if NUKE_AVAILABLE and nuke.root().name():
                script_path = nuke.root().name()
                script_dir = os.path.dirname(script_path)
                
                # Ищем корень проекта по маркерам
                current_dir = script_dir
                max_levels = 5
                
                for _ in range(max_levels):
                    if not current_dir or current_dir == os.path.dirname(current_dir):
                        break
                    
                    project_markers = [
                        'scenes', 'scripts', 'comp', 'render', 
                        '.project', 'shots', 'sequences', 'assets'
                    ]
                    
                    try:
                        dir_contents = os.listdir(current_dir)
                        if any(marker in dir_contents for marker in project_markers):
                            return current_dir
                    except (OSError, PermissionError):
                        pass
                    
                    current_dir = os.path.dirname(current_dir)
                
                return script_dir
            
            return os.path.expanduser('~')
            
        except Exception as e:
            print(f"PresetManager: Error getting project directory: {e}")
            return os.path.expanduser('~')
    
    def _can_create_directory(self, directory):
        """ИСПРАВЛЕНО: Проверить можем ли создать директорию"""
        try:
            if os.path.exists(directory):
                return os.access(directory, os.W_OK)
            
            os.makedirs(directory, exist_ok=True)
            
            if os.path.exists(directory):
                return os.access(directory, os.W_OK)
            
            return False
            
        except (OSError, PermissionError) as e:
            print(f"PresetManager: Cannot create directory {directory}: {e}")
            return False
    
    def ensure_files(self):
        """ИСПРАВЛЕНО: Создать файлы настроек с обработкой ошибок"""
        try:
            if not os.path.exists(self.atrain_dir):
                os.makedirs(self.atrain_dir, exist_ok=True)
                print(f"PresetManager: Created directory: {self.atrain_dir}")
        except (OSError, PermissionError) as e:
            print(f"PresetManager: Error creating directory {self.atrain_dir}: {e}")
            return
        
        # Создаем defaults.json если не существует
        if not os.path.exists(self.defaults_file):
            defaults_data = {
                "version": "1.5",
                "created": datetime.datetime.now().isoformat(),
                "description": "A-Train default tags and presets",
                "default_tags": [
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
                    }
                ],
                "default_presets": {
                    "Default": {
                        "tags": ["project path", "shot name", "version"],
                        "format": "exr",
                        "category": "System",
                        "created": datetime.datetime.now().isoformat(),
                        "author": "system",
                        "description": "Basic project/shot/version pattern"
                    },
                    "Review": {
                        "tags": ["shot name", "user"],
                        "format": "jpeg", 
                        "category": "System",
                        "created": datetime.datetime.now().isoformat(),
                        "author": "system",
                        "description": "Simple review output"
                    }
                }
            }
            self._safe_save_json(self.defaults_file, defaults_data)
        
        # Создаем custom.json если не существует
        if not os.path.exists(self.custom_file):
            custom_data = {
                "version": "1.5",
                "created": datetime.datetime.now().isoformat(),
                "last_modified": datetime.datetime.now().isoformat(),
                "author": self.get_current_user(),
                "custom_tags": [],
                "custom_expression_tags": [],
                "custom_presets": {}
            }
            self._safe_save_json(self.custom_file, custom_data)
        
        # Создаем categories.json если не существует
        if not os.path.exists(self.categories_file):
            categories_data = {
                "version": "1.5",
                "created": datetime.datetime.now().isoformat(),
                "last_modified": datetime.datetime.now().isoformat(),
                "tag_categories": ["General", "System", "Custom"],
                "preset_categories": ["General", "System", "Custom"]
            }
            self._safe_save_json(self.categories_file, categories_data)
    
    def _safe_save_json(self, file_path, data):
        """ИСПРАВЛЕНО: Безопасное сохранение JSON"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"PresetManager: Created {os.path.basename(file_path)}")
        except (OSError, PermissionError) as e:
            print(f"PresetManager: Error saving {file_path}: {e}")
    
    def get_current_user(self):
        """Получить текущего пользователя"""
        try:
            return getpass.getuser()
        except:
            return "unknown"
    
    def load_defaults(self):
        """Загрузить дефолтные данные"""
        try:
            with open(self.defaults_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"PresetManager: Error loading defaults: {e}")
            return {}
    
    def save_defaults(self, data):
        """Сохранить дефолтные данные"""
        self._safe_save_json(self.defaults_file, data)
    
    def load_custom(self):
        """Загрузить пользовательские данные"""
        try:
            with open(self.custom_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"PresetManager: Error loading custom data: {e}")
            return {
                "custom_tags": [],
                "custom_expression_tags": [],
                "custom_presets": {}
            }
    
    def save_custom(self, data):
        """Сохранить пользовательские данные"""
        try:
            data['last_modified'] = datetime.datetime.now().isoformat()
            self._safe_save_json(self.custom_file, data)
            self.cache.invalidate()
            self.event_bus.publish('data_changed')
        except Exception as e:
            print(f"PresetManager: Error saving custom data: {e}")
    
    def load_categories(self):
        """Загрузить категории"""
        try:
            with open(self.categories_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"PresetManager: Error loading categories: {e}")
            return {
                "tag_categories": ["General"],
                "preset_categories": ["General"]
            }
    
    def save_categories(self, data):
        """Сохранить категории"""
        try:
            data['last_modified'] = datetime.datetime.now().isoformat()
            self._safe_save_json(self.categories_file, data)
            self.cache.invalidate()
            self.event_bus.publish('data_changed')
        except Exception as e:
            print(f"PresetManager: Error saving categories: {e}")
    
    def get_all_tags(self):
        """Получить все теги с кешированием"""
        return self.cache.get('all_tags', self._load_all_tags)
    
    def _load_all_tags(self):
        """Загрузить все теги"""
        defaults = self.load_defaults()
        custom = self.load_custom()
        
        all_tags = []
        
        # Дефолтные теги
        default_tags = defaults.get('default_tags', [])
        for tag in default_tags:
            tag_copy = tag.copy()
            tag_copy['source'] = 'default'
            tag_copy['category'] = tag_copy.get('category', 'System')
            all_tags.append(tag_copy)
        
        # Пользовательские текстовые теги
        custom_tags = custom.get('custom_tags', [])
        for tag in custom_tags:
            tag_copy = tag.copy()
            tag_copy['source'] = 'custom'
            tag_copy['category'] = tag_copy.get('category', 'General')
            all_tags.append(tag_copy)
        
        # Пользовательские expression теги
        custom_expr_tags = custom.get('custom_expression_tags', [])
        for tag in custom_expr_tags:
            tag_copy = tag.copy()
            tag_copy['type'] = 'expression'
            tag_copy['source'] = 'custom'
            tag_copy['category'] = tag_copy.get('category', 'General')
            all_tags.append(tag_copy)
        
        return all_tags
    
    def get_all_presets(self):
        """Получить все пресеты с кешированием"""
        return self.cache.get('all_presets', self._load_all_presets)
    
    def _load_all_presets(self):
        """Загрузить все пресеты"""
        defaults = self.load_defaults()
        custom = self.load_custom()
        
        all_presets = {}
        
        # Дефолтные пресеты
        default_presets = defaults.get('default_presets', {})
        for name, data in default_presets.items():
            preset_copy = data.copy()
            preset_copy['source'] = 'default'
            preset_copy['category'] = preset_copy.get('category', 'System')
            all_presets[name] = preset_copy
        
        # Пользовательские пресеты
        custom_presets = custom.get('custom_presets', {})
        for name, data in custom_presets.items():
            preset_copy = data.copy()
            preset_copy['source'] = 'custom'
            preset_copy['category'] = preset_copy.get('category', 'General')
            all_presets[name] = preset_copy
        
        return all_presets
    
    def get_all_tags_grouped(self):
        """ИСПРАВЛЕНО: Получить теги, сгруппированные по категориям"""
        all_tags = self.get_all_tags()
        categories = self.get_tag_categories()
        
        grouped = {
            "System": []
        }
        
        for category in categories:
            if category not in grouped:
                grouped[category] = []
        
        if 'General' not in grouped:
            grouped['General'] = []
        
        for tag in all_tags:
            tag_source = tag.get('source', 'custom')
            tag_category = tag.get('category', 'General')
            
            if tag_source == 'default':
                grouped['System'].append(tag)
            else:
                if tag_category in categories:
                    grouped[tag_category].append(tag)
                else:
                    grouped['General'].append(tag)
        
        return grouped
    
    def get_all_presets_grouped(self):
        """ИСПРАВЛЕНО: Получить пресеты, сгруппированные по категориям"""
        all_presets = self.get_all_presets()
        categories = self.get_preset_categories()
        
        grouped = {
            "System": []
        }
        
        for category in categories:
            if category not in grouped:
                grouped[category] = []
        
        if 'General' not in grouped:
            grouped['General'] = []
        
        for name, preset_data in all_presets.items():
            preset_source = preset_data.get('source', 'custom')
            preset_category = preset_data.get('category', 'General')
            
            preset_info = {
                'name': name,
                'source': preset_source,
                'category': preset_category,
                'format': preset_data.get('format', 'exr'),
                'tags_count': len(preset_data.get('tags', [])),
                'data': preset_data
            }
            
            if preset_source == 'default':
                grouped['System'].append(preset_info)
            else:
                if preset_category in categories:
                    grouped[preset_category].append(preset_info)
                else:
                    grouped['General'].append(preset_info)
        
        return grouped
    
    def get_tag_categories(self):
        """Получить категории тегов"""
        categories_data = self.load_categories()
        categories = categories_data.get('tag_categories', ['General'])
        return categories
    
    def get_preset_categories(self):
        """Получить категории пресетов"""
        categories_data = self.load_categories()
        categories = categories_data.get('preset_categories', ['General'])
        return categories
    
    def save_custom_preset(self, name, tag_names, format_type="exr", category="General"):
        """Сохранить пользовательский пресет"""
        try:
            custom = self.load_custom()
            custom_presets = custom.get('custom_presets', {})
            
            custom_presets[name] = {
                "tags": tag_names,
                "format": format_type,
                "category": category,
                "created": datetime.datetime.now().isoformat(),
                "author": self.get_current_user(),
                "version": "1.0"
            }
            
            custom['custom_presets'] = custom_presets
            self.save_custom(custom)
            print(f"PresetManager: Saved custom preset '{name}'")
        except Exception as e:
            print(f"PresetManager: Error saving custom preset: {e}")
    
    def add_custom_tag(self, tag_data):
        """Добавить пользовательский тег"""
        if 'category' not in tag_data:
            tag_data['category'] = 'General'
        
        try:
            custom = self.load_custom()
            custom_tags = custom.get('custom_tags', [])
            custom_tags.append(tag_data)
            custom['custom_tags'] = custom_tags
            self.save_custom(custom)
            print(f"PresetManager: Added custom tag '{tag_data.get('name', '')}'")
        except Exception as e:
            print(f"PresetManager: Error adding custom tag: {e}")
    
    def get_project_info(self):
        """Получить информацию о проекте"""
        return {
            'project_directory': self.project_dir,
            'atrain_directory': self.atrain_dir,
            'files': {
                'defaults': self.defaults_file,
                'custom': self.custom_file,
                'categories': self.categories_file
            },
            'files_exist': {
                'defaults': os.path.exists(self.defaults_file),
                'custom': os.path.exists(self.custom_file),
                'categories': os.path.exists(self.categories_file)
            },
            'directory_writable': os.access(self.atrain_dir, os.W_OK) if os.path.exists(self.atrain_dir) else False
        }
