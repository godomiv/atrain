# atrain/core/version_manager.py
"""
Менеджер версий A-Train - ИСПРАВЛЕНО: полная работа с версиями
"""

import os
import re
import glob
from typing import Optional, List

class VersionManager:
    """Статический класс для управления версиями файлов"""
    
    # Паттерны версий
    VERSION_PATTERNS = [
        r'[vV](\d+)',           # v01, V001
        r'_v(\d+)',             # _v01
        r'\.v(\d+)',            # .v01
        r'[vV](\d+)_',          # v01_
        r'[vV](\d+)\.',         # v01.
    ]
    
    @staticmethod
    def extract_version_from_path(path: str) -> Optional[str]:
        """Извлечь версию из пути"""
        if not path:
            return None
        
        for pattern in VersionManager.VERSION_PATTERNS:
            match = re.search(pattern, path, re.IGNORECASE)
            if match:
                version_num = int(match.group(1))
                return f"v{version_num:02d}"
        
        return None
    
    @staticmethod
    def increment_version_in_path(path: str) -> str:
        """Увеличить версию в пути"""
        if not path:
            return path
        
        current_version = VersionManager.extract_version_from_path(path)
        if current_version:
            # Извлекаем номер версии
            version_num = int(current_version[1:])  # убираем 'v'
            new_version = f"v{version_num + 1:02d}"
            
            # Заменяем старую версию на новую
            for pattern in VersionManager.VERSION_PATTERNS:
                new_path = re.sub(pattern, lambda m: new_version, path, flags=re.IGNORECASE)
                if new_path != path:
                    return new_path
        else:
            # Если версии нет, добавляем v01
            name, ext = os.path.splitext(path)
            return f"{name}_v01{ext}"
        
        return path
    
    @staticmethod
    def get_next_available_version(path: str) -> str:
        """Получить следующую доступную версию"""
        if not path:
            return path
        
        directory = os.path.dirname(path)
        if not directory:
            directory = "."
        
        # Если директория не существует, возвращаем исходный путь
        if not os.path.exists(directory):
            return path
        
        current_version = VersionManager.extract_version_from_path(path)
        if not current_version:
            # Нет версии - добавляем v01
            name, ext = os.path.splitext(path)
            base_path = f"{name}_v01{ext}"
        else:
            base_path = path
        
        # Ищем существующие версии
        base_name = os.path.basename(base_path)
        
        # Создаем паттерн для поиска
        for pattern in VersionManager.VERSION_PATTERNS:
            search_pattern = re.sub(pattern, r'*', base_name, flags=re.IGNORECASE)
            if search_pattern != base_name:
                search_path = os.path.join(directory, search_pattern)
                existing_files = glob.glob(search_path)
                
                if existing_files:
                    # Найдены существующие файлы, ищем максимальную версию
                    max_version = 0
                    for file_path in existing_files:
                        version = VersionManager.extract_version_from_path(file_path)
                        if version:
                            version_num = int(version[1:])
                            max_version = max(max_version, version_num)
                    
                    # Создаем следующую версию
                    next_version = f"v{max_version + 1:02d}"
                    return re.sub(pattern, next_version, base_path, flags=re.IGNORECASE)
                break
        
        return base_path
    
    @staticmethod
    def validate_version_format(version_string: str) -> bool:
        """Проверить корректность формата версии"""
        if not version_string:
            return False
        
        return bool(re.match(r'^[vV]\d{1,3}$', version_string))
    
    @staticmethod
    def get_version_history(path: str) -> List[str]:
        """Получить историю версий файла"""
        if not path:
            return []
        
        directory = os.path.dirname(path)
        if not directory:
            directory = "."
        
        if not os.path.exists(directory):
            return []
        
        base_name = os.path.basename(path)
        
        # Создаем паттерн для поиска всех версий
        for pattern in VersionManager.VERSION_PATTERNS:
            search_pattern = re.sub(pattern, r'*', base_name, flags=re.IGNORECASE)
            if search_pattern != base_name:
                search_path = os.path.join(directory, search_pattern)
                existing_files = glob.glob(search_path)
                
                if existing_files:
                    # Сортируем по версиям
                    version_files = []
                    for file_path in existing_files:
                        version = VersionManager.extract_version_from_path(file_path)
                        if version:
                            version_num = int(version[1:])
                            version_files.append((version_num, file_path))
                    
                    version_files.sort(key=lambda x: x[0])
                    return [file_path for _, file_path in version_files]
                break
        
        return []


def test_version_patterns():
    """Тестирование паттернов версий"""
    test_paths = [
        "/path/to/file_v01.exr",
        "/path/to/file.v02.exr", 
        "/path/to/fileV003.exr",
        "/path/to/file_v04_.exr",
        "/path/to/file.v05.%04d.exr",
        "/path/to/file_without_version.exr"
    ]
    
    print("=== Version Manager Tests ===")
    for path in test_paths:
        version = VersionManager.extract_version_from_path(path)
        incremented = VersionManager.increment_version_in_path(path)
        print(f"Path: {path}")
        print(f"  Version: {version}")
        print(f"  Incremented: {incremented}")
        print()
