# Глобальный экземпляр
_nuke_bridge_instance = None

def nuke_bridge() -> NukeBridge:
    """Получить глобальный экземпляр NukeBridge"""
    global _nuke_bridge_instance
    if _nuke_bridge_instance is None:
        _nuke_bridge_instance = NukeBridge()
    return _nuke_bridge_instance atrain/core/nuke/bridge.py
"""
Централизованный интерфейс к Nuke API
"""

import os
import getpass
from typing import Optional, List, Dict, Any, Tuple


class NukeBridge:
    """
    Мост между A-Train и Nuke API
    Предоставляет унифицированный интерфейс с fallback для standalone режима
    """
    
    def __init__(self):
        self._nuke = None
        self._available = False
        
        try:
            import nuke
            self._nuke = nuke
            self._available = True
            print("NukeBridge: Nuke API available")
        except ImportError:
            print("NukeBridge: Running in standalone mode (no Nuke)")
    
    @property
    def available(self) -> bool:
        """Доступен ли Nuke API"""
        return self._available
    
    @property
    def nuke(self):
        """Прямой доступ к nuke модулю (для особых случаев)"""
        return self._nuke
    
    # =====================
    # Работа со скриптом
    # =====================
    
    @property
    def root(self):
        """Root нода Nuke"""
        if self.available:
            return self._nuke.root()
        return None
    
    def get_script_name(self) -> str:
        """Получить имя текущего скрипта"""
        if self.available and self._nuke.root().name():
            return self._nuke.root().name()
        return ""
    
    def get_script_path(self) -> str:
        """Получить путь к текущему скрипту"""
        script_name = self.get_script_name()
        if script_name:
            return os.path.dirname(script_name)
        return ""
    
    def get_script_basename(self) -> str:
        """Получить имя скрипта без пути и расширения"""
        script_name = self.get_script_name()
        if script_name:
            basename = os.path.basename(script_name)
            return os.path.splitext(basename)[0]
        return "untitled"
    
    def get_frame_range(self) -> Tuple[int, int]:
        """Получить диапазон кадров"""
        if self.available:
            first = int(self._nuke.root()['first_frame'].value())
            last = int(self._nuke.root()['last_frame'].value())
            return (first, last)
        return (1, 100)
    
    def get_current_frame(self) -> int:
        """Получить текущий кадр"""
        if self.available:
            return self._nuke.frame()
        return 1
    
    # =====================
    # Работа с нодами
    # =====================
    
    def get_selected_nodes(self, node_class: Optional[str] = None) -> List[Any]:
        """Получить выбранные ноды"""
        if not self.available:
            return []
        
        if node_class:
            return self._nuke.selectedNodes(node_class)
        return self._nuke.selectedNodes()
    
    def get_all_nodes(self, node_class: Optional[str] = None) -> List[Any]:
        """Получить все ноды определенного класса"""
        if not self.available:
            return []
        
        if node_class:
            return self._nuke.allNodes(node_class)
        return self._nuke.allNodes()
    
    def create_node(self, node_type: str, **kwargs) -> Optional[Any]:
        """Создать ноду"""
        if not self.available:
            return None
        
        try:
            # Извлекаем специальные параметры
            inpanel = kwargs.pop('inpanel', False)
            
            # Создаем ноду
            node = self._nuke.createNode(node_type, inpanel=inpanel)
            
            # Устанавливаем параметры
            for key, value in kwargs.items():
                if key in node.knobs():
                    node[key].setValue(value)
            
            return node
            
        except Exception as e:
            print(f"NukeBridge: Error creating node: {e}")
            return None
    
    def delete_node(self, node: Any) -> bool:
        """Удалить ноду"""
        if not self.available or not node:
            return False
        
        try:
            self._nuke.delete(node)
            return True
        except Exception as e:
            print(f"NukeBridge: Error deleting node: {e}")
            return False
    
    def execute_node(self, node: Any, first_frame: int, last_frame: int) -> bool:
        """Выполнить рендер ноды"""
        if not self.available or not node:
            return False
        
        try:
            self._nuke.execute(node, first_frame, last_frame)
            return True
        except Exception as e:
            print(f"NukeBridge: Error executing node: {e}")
            return False
    
    # =====================
    # Работа с knobs
    # =====================
    
    def get_knob_value(self, node: Any, knob_name: str, default: Any = None) -> Any:
        """Получить значение knob"""
        if not self.available or not node:
            return default
        
        try:
            if knob_name in node.knobs():
                return node[knob_name].value()
        except:
            pass
        
        return default
    
    def set_knob_value(self, node: Any, knob_name: str, value: Any) -> bool:
        """Установить значение knob"""
        if not self.available or not node:
            return False
        
        try:
            if knob_name in node.knobs():
                node[knob_name].setValue(value)
                return True
        except Exception as e:
            print(f"NukeBridge: Error setting knob value: {e}")
        
        return False
    
    # =====================
    # UI функции
    # =====================
    
    def show_message(self, message: str, title: str = "A-Train") -> None:
        """Показать сообщение пользователю"""
        if self.available:
            self._nuke.message(f"{title}\n\n{message}")
        else:
            print(f"{title}: {message}")
    
    def ask_user(self, question: str, title: str = "A-Train") -> bool:
        """Спросить да/нет у пользователя"""
        if self.available:
            return self._nuke.ask(f"{title}\n\n{question}")
        else:
            # В standalone режиме всегда возвращаем True
            print(f"{title}: {question} [Y/n]")
            return True
    
    def get_filename(self, prompt: str = "Select file", pattern: str = "*") -> Optional[str]:
        """Диалог выбора файла"""
        if self.available:
            return self._nuke.getFilename(prompt, pattern)
        return None
    
    # =====================
    # Утилиты
    # =====================
    
    def get_user_name(self) -> str:
        """Получить имя пользователя"""
        try:
            return getpass.getuser()
        except:
            return "user"
    
    def get_project_info(self) -> Dict[str, str]:
        """Получить информацию о проекте"""
        info = {
            'script_name': self.get_script_basename(),
            'script_path': self.get_script_path(),
            'user': self.get_user_name(),
        }
        
        if self.available:
            info['frame_range'] = f"{self.get_frame_range()[0]}-{self.get_frame_range()[1]}"
            info['current_frame'] = str(self.get_current_frame())
        
        return info
    
    def find_project_root(self) -> str:
        """Найти корень проекта"""
        script_path = self.get_script_path()
        if not script_path:
            return os.path.expanduser('~')
        
        # Ищем маркеры проекта
        markers = [
            'scenes', 'scripts', 'comp', 'render',
            '.project', 'shots', 'sequences', 'assets'
        ]
        
        current_dir = script_path
        for _ in range(5):  # Максимум 5 уровней вверх
            if not current_dir or current_dir == os.path.dirname(current_dir):
                break
            
            try:
                dir_contents = os.listdir(current_dir)
                if any(marker in dir_contents for marker in markers):
                    return current_dir
            except:
                pass
            
            current_dir = os.path.dirname(current_dir)
        
        return script_path


#
