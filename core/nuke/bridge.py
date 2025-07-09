# atrain/core/nuke/bridge.py
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
