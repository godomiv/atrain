# atrain/core/utils/cache.py
"""
Система кеширования для A-Train
"""

import time
import functools
from typing import Dict, Any, Optional, Callable
from collections import defaultdict


class CacheManager:
    """Менеджер кеширования с TTL"""
    
    def __init__(self, default_ttl: float = 300.0):
        """
        Args:
            default_ttl: Время жизни кеша по умолчанию (секунды)
        """
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}
        self.ttls: Dict[str, float] = {}
        self.default_ttl = default_ttl
        self.dependencies: Dict[str, set] = defaultdict(set)
    
    def get(self, key: str, loader_func: Optional[Callable] = None, 
            ttl: Optional[float] = None) -> Any:
        """
        Получить значение из кеша или загрузить
        
        Args:
            key: Ключ кеша
            loader_func: Функция загрузки данных
            ttl: Время жизни для этого ключа
            
        Returns:
            Закешированное или загруженное значение
        """
        if ttl is None:
            ttl = self.default_ttl
        
        # Проверяем валидность кеша
        if self.is_valid(key):
            return self.cache[key]
        
        # Загружаем данные если есть loader
        if loader_func is not None:
            data = loader_func()
            self.set(key, data, ttl)
            return data
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """
        Установить значение в кеш
        
        Args:
            key: Ключ
            value: Значение
            ttl: Время жизни
        """
        if ttl is None:
            ttl = self.default_ttl
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
        self.ttls[key] = ttl
    
    def is_valid(self, key: str) -> bool:
        """Проверить валидность кеша"""
        if key not in self.cache:
            return False
        
        ttl = self.ttls.get(key, self.default_ttl)
        age = time.time() - self.timestamps.get(key, 0)
        return age < ttl
    
    def invalidate(self, key: Optional[str] = None):
        """
        Инвалидировать кеш
        
        Args:
            key: Ключ для инвалидации. Если None - очистить весь кеш
        """
        if key is None:
            self.cache.clear()
            self.timestamps.clear()
            self.ttls.clear()
            self.dependencies.clear()
        else:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
            self.ttls.pop(key, None)
            
            # Инвалидируем зависимые ключи
            for dependent_key in self.dependencies.get(key, set()):
                self.invalidate(dependent_key)
            
            self.dependencies.pop(key, None)
    
    def add_dependency(self, key: str, depends_on: str):
        """Добавить зависимость между ключами"""
        self.dependencies[depends_on].add(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кеша"""
        total_keys = len(self.cache)
        valid_keys = sum(1 for key in self.cache if self.is_valid(key))
        
        return {
            'total_keys': total_keys,
            'valid_keys': valid_keys,
            'expired_keys': total_keys - valid_keys,
            'dependencies': {k: len(v) for k, v in self.dependencies.items()}
        }


def timed_cache(seconds: float = 60.0):
    """
    Декоратор для кеширования результатов функции
    
    Args:
        seconds: Время жизни кеша в секундах
        
    Example:
        @timed_cache(seconds=300)
        def expensive_function(param):
            return do_something_expensive(param)
    """
    def decorator(func):
        cache = {}
        timestamps = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Создаем ключ из аргументов
            key = (args, tuple(sorted(kwargs.items())))
            
            # Проверяем кеш
            if key in cache:
                age = time.time() - timestamps[key]
                if age < seconds:
                    return cache[key]
            
            # Вычисляем результат
            result = func(*args, **kwargs)
            
            # Сохраняем в кеш
            cache[key] = result
            timestamps[key] = time.time()
            
            return result
        
        # Добавляем метод для очистки кеша
        def clear_cache():
            cache.clear()
            timestamps.clear()
        
        wrapper.clear_cache = clear_cache
        
        return wrapper
    
    return decorator
