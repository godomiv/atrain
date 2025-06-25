# atrain/core/nuke/node_utils.py
"""
Утилиты для работы с Nuke нодами
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from .bridge import nuke_bridge


class NodeUtils:
    """Утилиты для работы с нодами"""
    
    def __init__(self):
        self.bridge = nuke_bridge()
    
    # =====================
    # Read ноды
    # =====================
    
    def get_read_info(self, read_node: Any) -> Dict[str, Any]:
        """Получить информацию о Read ноде"""
        info = {
            'name': '',
            'file_path': '',
            'file_name': '',
            'clean_name': '',
            'exists': False,
            'frame_range': None,
            'colorspace': '',
            'channels': ''
        }
        
        if not read_node:
            return info
        
        try:
            # Базовая информация
            info['name'] = read_node.name()
            
            # Путь к файлу
            file_path = self.bridge.get_knob_value(read_node, 'file', '')
            info['file_path'] = file_path
            
            if file_path:
                info['file_name'] = os.path.basename(file_path)
                info['clean_name'] = self.extract_clean_name(file_path)
                info['exists'] = os.path.exists(file_path)
            
            # Технические параметры
            info['frame_range'] = (
                self.bridge.get_knob_value(read_node, 'first', 0),
                self.bridge.get_knob_value(read_node, 'last', 0)
            )
            info['colorspace'] = self.bridge.get_knob_value(read_node, 'colorspace', '')
            
            # Каналы
            channels = self.bridge.get_knob_value(read_node, 'channels', 'rgb')
            info['channels'] = channels
            
        except Exception as e:
            print(f"NodeUtils: Error getting read info: {e}")
        
        return info
    
    def extract_clean_name(self, file_path: str) -> str:
        """Извлечь чистое имя из пути файла"""
        if not file_path:
            return ""
        
        try:
            basename = os.path.splitext(os.path.basename(file_path))[0]
            
            # Убираем номера кадров
            clean_name = re.sub(r'[._]\d{3,}, '', basename)
            clean_name = re.sub(r'[._], '', clean_name)
            
            # Убираем версии
            from ..utils.version import extract_version
            version = extract_version(clean_name)
            if version:
                clean_name = clean_name.replace(version, '').rstrip('_')
            
            # Убираем паттерны кадров
            clean_name = re.sub(r'[._]\d+, '', clean_name)
            clean_name = re.sub(r'[._], '', clean_name)
            
            return clean_name if clean_name else basename
            
        except Exception as e:
            print(f"NodeUtils: Error extracting clean name: {e}")
            return os.path.basename(file_path)
