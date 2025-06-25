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
        if key not in self.cache
