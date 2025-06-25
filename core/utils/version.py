# atrain/core/utils/version.py
"""
Утилиты для работы с версиями файлов
"""

import os
import re
import glob
from typing import Optional, List, Tuple


# Паттерны версий
VERSION_PATTERNS = [
    r'[vV](\d+)',           # v01, V001
    r'_v(\d+)',             # _v01
    r'\.v(\d+)',            # .v01
    r'[vV](\d+)_',          # v01_
    r'[vV](\d+)\.',         # v01.
]


def extract_version(path: str) -> Optional[str]:
    """
    Извлечь версию из пути
    
    Args:
        path: Путь к файлу
        
    Returns:
        Найденная версия в формате vXX или None
    """
    if not path:
        return None
    
    for pattern in VERSION_PATTERNS:
        match = re.search(pattern, path, re.IGNORECASE)
        if match:
            version_num = int(match.group(1))
            return f"v{version_num:02d}"
    
    return None


def increment_version(path: str, padding: int = 2) -> str:
    """
    Увеличить версию в пути
    
    Args:
        path: Путь к файлу
        padding: Количество цифр в версии
        
    Returns:
        Путь с увеличенной версией
    """
    if not path:
        return path
    
    current_version = extract_version(path)
    if current_version:
        # Извлекаем номер версии
        version_num = int(current_version[1:])  # убираем 'v'
        new_version = f"v{version_num + 1:0{padding}d}"
        
        # Заменяем старую версию на новую
        for pattern in VERSION_PATTERNS:
            new_path = re.sub(pattern, lambda m: new_version, path, flags=re.IGNORECASE)
            if new_path != path:
                return new_path
    else:
        # Если версии нет, добавляем v01
        name, ext = os.path.splitext(path)
        return f"{name}_v{1:0{padding}d}{ext}"
    
    return path


def get_next_available_version(path: str, check_exists: bool = True) -> str:
    """
    Получить следующую доступную версию файла
    
    Args:
        path: Базовый путь
        check_exists: Проверять существование файлов
        
    Returns:
        Путь с доступной версией
    """
    if not path:
        return path
    
    if not check_exists:
        return increment_version(path)
    
    directory = os.path.dirname(path)
    if not directory:
        directory = "."
    
    # Если директория не существует, возвращаем исходный путь
    if not os.path.exists(directory):
        current_version = extract_version(path)
        if not current_version:
            # Добавляем v01 если версии нет
            name, ext = os.path.splitext(path)
            return f"{name}_v01{ext}"
        return path
    
    # Ищем существующие версии
    base_name = os.path.basename(path)
    existing_versions = []
    
    for pattern in VERSION_PATTERNS:
        # Создаем паттерн для поиска всех версий
        search_pattern = re.sub(pattern, r'v*', base_name, flags=re.IGNORECASE)
        if search_pattern != base_name:
            search_path = os.path.join(directory, search_pattern)
            existing_files = glob.glob(search_path)
            
            for file_path in existing_files:
                version = extract_version(file_path)
                if version:
                    version_num = int(version[1:])
                    existing_versions.append(version_num)
            
            if existing_versions:
                break
    
    if existing_versions:
        # Находим максимальную версию и увеличиваем
        max_version = max(existing_versions)
        next_version = f"v{max_version + 1:02d}"
        
        # Заменяем версию в пути
        for pattern in VERSION_PATTERNS:
            new_path = re.sub(pattern, next_version, path, flags=re.IGNORECASE)
            if new_path != path:
                return new_path
    
    # Если версий не найдено, добавляем v01
    current_version = extract_version(path)
    if not current_version:
        name, ext = os.path.splitext(path)
        return f"{name}_v01{ext}"
    
    return path


def validate_version_format(version_string: str) -> bool:
    """
    Проверить корректность формата версии
    
    Args:
        version_string: Строка версии
        
    Returns:
        True если формат корректен
    """
    if not version_string:
        return False
    
    return bool(re.match(r'^[vV]\d{1,3}, version_string))


def get_version_history(path: str) -> List[Tuple[str, str]]:
    """
    Получить историю версий файла
    
    Args:
        path: Путь к файлу
        
    Returns:
        Список кортежей (версия, путь) отсортированный по версии
    """
    if not path:
        return []
    
    directory = os.path.dirname(path)
    if not directory:
        directory = "."
    
    if not os.path.exists(directory):
        return []
    
    base_name = os.path.basename(path)
    version_files = []
    
    # Создаем паттерн для поиска всех версий
    for pattern in VERSION_PATTERNS:
        search_pattern = re.sub(pattern, r'v*', base_name, flags=re.IGNORECASE)
        if search_pattern != base_name:
            search_path = os.path.join(directory, search_pattern)
            existing_files = glob.glob(search_path)
            
            for file_path in existing_files:
                version = extract_version(file_path)
                if version:
                    version_num = int(version[1:])
                    version_files.append((version_num, version, file_path))
            
            if version_files:
                break
    
    # Сортируем по номеру версии
    version_files.sort(key=lambda x: x[0])
    
    # Возвращаем только версию и путь
    return [(v[1], v[2]) for v in version_files]


def replace_version(path: str, new_version: str) -> str:
    """
    Заменить версию в пути
    
    Args:
        path: Исходный путь
        new_version: Новая версия (например, "v05")
        
    Returns:
        Путь с новой версией
    """
    if not path or not new_version:
        return path
    
    if not validate_version_format(new_version):
        raise ValueError(f"Invalid version format: {new_version}")
    
    current_version = extract_version(path)
    if current_version:
        # Заменяем существующую версию
        for pattern in VERSION_PATTERNS:
            new_path = re.sub(pattern, lambda m: new_version, path, flags=re.IGNORECASE)
            if new_path != path:
                return new_path
    else:
        # Добавляем версию если её нет
        name, ext = os.path.splitext(path)
        return f"{name}_{new_version}{ext}"
    
    return path


def compare_versions(version1: str, version2: str) -> int:
    """
    Сравнить две версии
    
    Args:
        version1: Первая версия
        version2: Вторая версия
        
    Returns:
        -1 если version1 < version2
         0 если version1 == version2
         1 если version1 > version2
    """
    if not version1 or not version2:
        return 0
    
    try:
        num1 = int(version1.lstrip('vV'))
        num2 = int(version2.lstrip('vV'))
        
        if num1 < num2:
            return -1
        elif num1 > num2:
            return 1
        else:
            return 0
    except:
        return 0
