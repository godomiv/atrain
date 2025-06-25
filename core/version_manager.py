# atrain/core/version_manager.py
"""
Редирект на новую систему версий для совместимости
"""

from .utils.version import (
    extract_version,
    increment_version,
    get_next_available_version,
    validate_version_format,
    get_version_history,
    VERSION_PATTERNS
)

# Класс для совместимости со статическими методами
class VersionManager:
    VERSION_PATTERNS = VERSION_PATTERNS
    
    @staticmethod
    def extract_version_from_path(path):
        return extract_version(path)
    
    @staticmethod
    def increment_version_in_path(path):
        return increment_version(path)
    
    @staticmethod
    def get_next_available_version(path):
        return get_next_available_version(path)
    
    @staticmethod
    def validate_version_format(version_string):
        return validate_version_format(version_string)
    
    @staticmethod
    def get_version_history(path):
        return get_version_history(path)


# Для тестов
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
        version = extract_version(path)
        incremented = increment_version(path)
        print(f"Path: {path}")
        print(f"  Version: {version}")
        print(f"  Incremented: {incremented}")
        print()
