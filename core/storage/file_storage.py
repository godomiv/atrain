# atrain/core/storage/file_storage.py
"""
Базовый класс для работы с файловым хранилищем
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..nuke import nuke_bridge


class FileStorage:
    """Базовый класс для работы с JSON файлами"""
    
    def __init__(self, filename: str):
        """
        Args:
            filename: Имя файла (например, 'atrain_presets.json')
        """
        self.filename = filename
        self._storage_dir = None
        self._file_path = None
        
    @property
    def storage_dir(self) -> Path:
        """Получить директорию хранилища"""
        if self._storage_dir is None:
            self._storage_dir = self._find_storage_directory()
        return self._storage_dir
    
    @property
    def file_path(self) -> Path:
        """Получить полный путь к файлу"""
        if self._file_path is None:
            self._file_path = self.storage_dir / self.filename
        return self._file_path
    
    def _find_storage_directory(self) -> Path:
        """Найти или создать директорию для хранения настроек"""
        bridge = nuke_bridge()
        
        # Приоритеты:
        # 1. Папка проекта/.atrain
        # 2. Домашняя папка/.nuke/atrain
        # 3. Временная папка
        
        # Пробуем папку проекта
        project_root = bridge.find_project_root()
        if project_root:
            project_dir = Path(project_root) / '.atrain'
            if self._try_create_directory(project_dir):
                return project_dir
        
        # Пробуем домашнюю папку
        home_dir = Path.home() / '.nuke' / 'atrain'
        if self._try_create_directory(home_dir):
            return home_dir
        
        # Fallback к временной папке
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / 'atrain_settings'
        self._try_create_directory(temp_dir)
        return temp_dir
    
    def _try_create_directory(self, path: Path) -> bool:
        """Попытаться создать директорию"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            # Проверяем что можем писать
            test_file = path / '.test'
            test_file.touch()
            test_file.unlink()
            return True
        except (OSError, PermissionError):
            return False
    
    def exists(self) -> bool:
        """Проверить существование файла"""
        return self.file_path.exists()
    
    def load(self) -> Dict[str, Any]:
        """Загрузить данные из файла"""
        try:
            if self.exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"FileStorage: Error loading {self.filename}: {e}")
        
        return {}
    
    def save(self, data: Dict[str, Any]) -> bool:
        """Сохранить данные в файл"""
        try:
            # Создаем резервную копию если файл существует
            if self.exists():
                self._create_backup()
            
            # Сохраняем во временный файл
            temp_file = self.file_path.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Атомарная замена
            temp_file.replace(self.file_path)
            
            return True
            
        except Exception as e:
            print(f"FileStorage: Error saving {self.filename}: {e}")
            return False
    
    def _create_backup(self) -> Optional[Path]:
        """Создать резервную копию файла"""
        try:
            backup_dir = self.storage_dir / 'backups'
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{self.file_path.stem}_{timestamp}{self.file_path.suffix}"
            backup_path = backup_dir / backup_name
            
            shutil.copy2(self.file_path, backup_path)
            
            # Удаляем старые бэкапы (оставляем последние 10)
            self._cleanup_old_backups(backup_dir, keep=10)
            
            return backup_path
            
        except Exception as e:
            print(f"FileStorage: Error creating backup: {e}")
            return None
    
    def _cleanup_old_backups(self, backup_dir: Path, keep: int = 10):
        """Удалить старые резервные копии"""
        try:
            pattern = f"{self.file_path.stem}_*{self.file_path.suffix}"
            backups = sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime)
            
            if len(backups) > keep:
                for backup in backups[:-keep]:
                    backup.unlink()
                    
        except Exception as e:
            print(f"FileStorage: Error cleaning backups: {e}")
    
    def get_backup_list(self) -> List[Path]:
        """Получить список резервных копий"""
        backup_dir = self.storage_dir / 'backups'
        if not backup_dir.exists():
            return []
        
        pattern = f"{self.file_path.stem}_*{self.file_path.suffix}"
        return sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    
    def restore_from_backup(self, backup_path: Path) -> bool:
        """Восстановить из резервной копии"""
        try:
            if backup_path.exists():
                shutil.copy2(backup_path, self.file_path)
                return True
        except Exception as e:
            print(f"FileStorage: Error restoring from backup: {e}")
        
        return False
    
    def merge_data(self, new_data: Dict[str, Any], 
                   strategy: str = 'update') -> Dict[str, Any]:
        """
        Объединить данные с существующими
        
        Args:
            new_data: Новые данные
            strategy: Стратегия слияния ('update', 'replace', 'merge_lists')
            
        Returns:
            Объединенные данные
        """
        existing_data = self.load()
        
        if strategy == 'replace':
            return new_data
        
        elif strategy == 'update':
            existing_data.update(new_data)
            return existing_data
        
        elif strategy == 'merge_lists':
            # Для списков объединяем, для остального - обновляем
            for key, value in new_data.items():
                if isinstance(value, list) and key in existing_data:
                    if isinstance(existing_data[key], list):
                        # Объединяем списки, убирая дубликаты
                        existing_data[key] = list(set(existing_data[key] + value))
                    else:
                        existing_data[key] = value
                else:
                    existing_data[key] = value
            
            return existing_data
        
        return existing_data
    
    def export_to_file(self, export_path: Path) -> bool:
        """Экспортировать данные в указанный файл"""
        try:
            data = self.load()
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"FileStorage: Error exporting to {export_path}: {e}")
            return False
    
    def import_from_file(self, import_path: Path, 
                        strategy: str = 'update') -> bool:
        """Импортировать данные из файла"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            merged_data = self.merge_data(import_data, strategy)
            return self.save(merged_data)
            
        except Exception as e:
            print(f"FileStorage: Error importing from {import_path}: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """Получить информацию о хранилище"""
        info = {
            'filename': self.filename,
            'storage_dir': str(self.storage_dir),
            'file_path': str(self.file_path),
            'exists': self.exists(),
            'size': 0,
            'modified': None,
            'backup_count': len(self.get_backup_list())
        }
        
        if self.exists():
            stat = self.file_path.stat()
            info['size'] = stat.st_size
            info['modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        return info
