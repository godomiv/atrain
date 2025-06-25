# atrain/core/nuke/callbacks.py
"""
Менеджер Nuke callbacks для A-Train
"""

from typing import Callable, List, Dict, Any
from .bridge import nuke_bridge


class NukeCallbackManager:
    """Управление Nuke callbacks"""
    
    def __init__(self):
        self.bridge = nuke_bridge()
        self.callbacks: Dict[str, List[Callable]] = {
            'on_user_create': [],
            'on_script_load': [],
            'on_script_save': [],
            'on_script_close': [],
            'on_selection_changed': [],
            'on_node_created': [],
            'on_node_deleted': []
        }
        self._registered = False
        
    def register_all(self):
        """Регистрация всех callbacks в Nuke"""
        if not self.bridge.available or self._registered:
            return
        
        nuke = self.bridge.nuke
        
        try:
            # onCreate callbacks
            nuke.addOnUserCreate(self._on_user_create)
            nuke.addOnCreate(self._on_create)
            
            # Script callbacks
            nuke.addOnScriptLoad(self._on_script_load)
            nuke.addOnScriptSave(self._on_script_save)
            nuke.addOnScriptClose(self._on_script_close)
            
            # Knob changed для отслеживания выделения
            nuke.addKnobChanged(self._on_knob_changed)
            
            self._registered = True
            print("NukeCallbackManager: Callbacks registered")
            
        except Exception as e:
            print(f"NukeCallbackManager: Error registering callbacks: {e}")
    
    def unregister_all(self):
        """Удаление всех callbacks из Nuke"""
        if not self.bridge.available or not self._registered:
            return
        
        nuke = self.bridge.nuke
        
        try:
            # Удаляем callbacks
            nuke.removeOnUserCreate(self._on_user_create)
            nuke.removeOnCreate(self._on_create)
            nuke.removeOnScriptLoad(self._on_script_load)
            nuke.removeOnScriptSave(self._on_script_save)
            nuke.removeOnScriptClose(self._on_script_close)
            nuke.removeKnobChanged(self._on_knob_changed)
            
            self._registered = False
            print("NukeCallbackManager: Callbacks unregistered")
            
        except Exception as e:
            print(f"NukeCallbackManager: Error unregistering callbacks: {e}")
    
    # =====================
    # Добавление обработчиков
    # =====================
    
    def add_callback(self, event_type: str, callback: Callable):
        """Добавить callback для события"""
        if event_type in self.callbacks:
            if callback not in self.callbacks[event_type]:
                self.callbacks[event_type].append(callback)
    
    def remove_callback(self, event_type: str, callback: Callable):
        """Удалить callback для события"""
        if event_type in self.callbacks:
            try:
                self.callbacks[event_type].remove(callback)
            except ValueError:
                pass
    
    def on_node_created(self, callback: Callable):
        """Декоратор для обработки создания ноды"""
        self.add_callback('on_node_created', callback)
        return callback
    
    def on_selection_changed(self, callback: Callable):
        """Декоратор для обработки изменения выделения"""
        self.add_callback('on_selection_changed', callback)
        return callback
    
    def on_script_load(self, callback: Callable):
        """Декоратор для обработки загрузки скрипта"""
        self.add_callback('on_script_load', callback)
        return callback
    
    # =====================
    # Внутренние обработчики
    # =====================
    
    def _on_user_create(self):
        """Вызывается при создании ноды пользователем"""
        try:
            node = self.bridge.nuke.thisNode()
            self._trigger_callbacks('on_user_create', node)
            self._trigger_callbacks('on_node_created', node)
        except:
            pass
    
    def _on_create(self):
        """Вызывается при создании любой ноды"""
        try:
            node = self.bridge.nuke.thisNode()
            self._trigger_callbacks('on_node_created', node)
        except:
            pass
    
    def _on_script_load(self):
        """Вызывается при загрузке скрипта"""
        self._trigger_callbacks('on_script_load')
    
    def _on_script_save(self):
        """Вызывается при сохранении скрипта"""
        self._trigger_callbacks('on_script_save')
    
    def _on_script_close(self):
        """Вызывается при закрытии скрипта"""
        self._trigger_callbacks('on_script_close')
    
    def _on_knob_changed(self):
        """Вызывается при изменении knob"""
        try:
            node = self.bridge.nuke.thisNode()
            knob = self.bridge.nuke.thisKnob()
            
            # Отслеживаем изменение выделения
            if knob and knob.name() == 'selected':
                self._trigger_callbacks('on_selection_changed', node)
                
        except:
            pass
    
    def _trigger_callbacks(self, event_type: str, *args, **kwargs):
        """Вызвать все callbacks для события"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"NukeCallbackManager: Error in callback: {e}")


# Глобальный экземпляр
_callback_manager = None

def get_callback_manager() -> NukeCallbackManager:
    """Получить глобальный менеджер callbacks"""
    global _callback_manager
    if _callback_manager is None:
        _callback_manager = NukeCallbackManager()
    return _callback_manager
