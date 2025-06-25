# atrain/core/utils/events.py
"""
Система событий для A-Train
"""
import functools  # Добавьте в начало файла

from typing import Dict, List, Callable, Any, Optional
import weakref
from collections import defaultdict


class EventBus:
    """
    Централизованная шина событий
    Поддерживает слабые ссылки для автоматической очистки
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._subscribers: Dict[str, List[weakref.ref]] = defaultdict(list)
        self._event_history: List[Dict[str, Any]] = []
        self._max_history = 100
        
        print("EventBus: Initialized")
    
    @classmethod
    def instance(cls) -> 'EventBus':
        """Получить singleton экземпляр"""
        return cls()
    
    def subscribe(self, event_type: str, callback: Callable, 
                  weak: bool = True) -> None:
        """
        Подписаться на событие
        
        Args:
            event_type: Тип события
            callback: Функция обработчик
            weak: Использовать слабую ссылку (рекомендуется)
        """
        if weak:
            # Для методов объектов создаем специальный weakref
            if hasattr(callback, '__self__'):
                ref = weakref.WeakMethod(callback)
            else:
                ref = weakref.ref(callback)
        else:
            # Сильная ссылка (обернутая для совместимости)
            ref = lambda: callback
        
        self._subscribers[event_type].append(ref)
        
        # Очистка мертвых ссылок
        self._cleanup_dead_refs(event_type)
    
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """
        Отписаться от события
        
        Args:
            event_type: Тип события
            callback: Функция обработчик
        """
        if event_type not in self._subscribers:
            return
        
        # Удаляем все ссылки на этот callback
        self._subscribers[event_type] = [
            ref for ref in self._subscribers[event_type]
            if ref() != callback
        ]
    
    def publish(self, event_type: str, data: Any = None) -> int:
        """
        Опубликовать событие
        
        Args:
            event_type: Тип события
            data: Данные события
            
        Returns:
            Количество вызванных обработчиков
        """
        # Сохраняем в историю
        self._add_to_history(event_type, data)
        
        if event_type not in self._subscribers:
            return 0
        
        # Очищаем мертвые ссылки перед вызовом
        self._cleanup_dead_refs(event_type)
        
        called_count = 0
        
        for ref in self._subscribers[event_type][:]:  # Копия для безопасности
            callback = ref()
            if callback is not None:
                try:
                    callback(data)
                    called_count += 1
                except Exception as e:
                    print(f"EventBus: Error in callback for '{event_type}': {e}")
        
        return called_count
    
    def publish_async(self, event_type: str, data: Any = None) -> None:
        """
        Опубликовать событие асинхронно (в следующем цикле событий Qt)
        
        Args:
            event_type: Тип события
            data: Данные события
        """
        try:
            from PySide2 import QtCore
            QtCore.QTimer.singleShot(0, lambda: self.publish(event_type, data))
        except ImportError:
            # Fallback к синхронной публикации
            self.publish(event_type, data)
    
    def has_subscribers(self, event_type: str) -> bool:
        """Проверить есть ли подписчики на событие"""
        self._cleanup_dead_refs(event_type)
        return len(self._subscribers.get(event_type, [])) > 0
    
    def get_subscriber_count(self, event_type: str) -> int:
        """Получить количество подписчиков"""
        self._cleanup_dead_refs(event_type)
        return len(self._subscribers.get(event_type, []))
    
    def clear_event(self, event_type: str) -> None:
        """Удалить всех подписчиков события"""
        self._subscribers.pop(event_type, None)
    
    def clear_all(self) -> None:
        """Очистить все подписки"""
        self._subscribers.clear()
        self._event_history.clear()
    
    def get_event_types(self) -> List[str]:
        """Получить список всех типов событий с подписчиками"""
        return [
            event_type for event_type in self._subscribers
            if self.has_subscribers(event_type)
        ]
    
    def get_history(self, event_type: Optional[str] = None, 
                    limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получить историю событий
        
        Args:
            event_type: Фильтр по типу события
            limit: Максимальное количество записей
            
        Returns:
            Список событий в обратном хронологическом порядке
        """
        history = self._event_history
        
        if event_type:
            history = [e for e in history if e['type'] == event_type]
        
        return history[-limit:][::-1]
    
    def _cleanup_dead_refs(self, event_type: str) -> None:
        """Очистить мертвые слабые ссылки"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                ref for ref in self._subscribers[event_type]
                if ref() is not None
            ]
    
    def _add_to_history(self, event_type: str, data: Any) -> None:
        """Добавить событие в историю"""
        import datetime
        
        self._event_history.append({
            'type': event_type,
            'data': data,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        # Ограничиваем размер истории
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
    
    def debug_info(self) -> Dict[str, Any]:
        """Получить отладочную информацию"""
        return {
            'event_types': self.get_event_types(),
            'subscribers': {
                event_type: self.get_subscriber_count(event_type)
                for event_type in self.get_event_types()
            },
            'history_size': len(self._event_history),
            'total_published': sum(1 for _ in self._event_history)
        }


# Глобальный экземпляр для удобства
_event_bus = None

def event_bus() -> EventBus:
    """Получить глобальную шину событий"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus.instance()
    return _event_bus


# Декораторы для удобства
def on_event(event_type: str):
    """
    Декоратор для автоматической подписки метода на событие
    
    Example:
        class MyClass:
            @on_event('path_changed')
            def handle_path_change(self, data):
                print(f"Path changed: {data}")
    """
    def decorator(func):
        # Добавляем метаданные для автоматической подписки
        func._event_subscription = event_type
        return func
    
    return decorator


def emit_event(event_type: str):
    """
    Декоратор для автоматической публикации события после вызова метода
    
    Example:
        class MyClass:
            @emit_event('data_saved')
            def save_data(self):
                # сохранение данных
                return {'status': 'success'}
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            event_bus().publish(event_type, result)
            return result
        
        return wrapper
    
    return decorator
