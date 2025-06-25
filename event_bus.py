# atrain/core/event_bus.py
"""
Система событий A-Train
"""

import datetime
from typing import Dict, List, Callable, Any

class EventBus:
    """Простая система событий для A-Train"""
    
    _instance = None
    
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.subscribers = {}
    
    def subscribe(self, event_type: str, callback: Callable):
        """Подписаться на событие"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Отписаться от события"""
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(callback)
            except ValueError:
                pass
    
    def publish(self, event_type: str, data: Any = None):
        """Опубликовать событие"""
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Event callback error: {e}")
