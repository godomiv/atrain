# atrain/core/tags/strategies.py
"""
Конкретные стратегии для разных типов тегов
"""

import os
import re
from typing import Optional, Dict, Any
from PySide2 import QtWidgets, QtGui

from .base import TagStrategy
from ..models import TagData
from ..nuke import nuke_bridge


class TextTagStrategy(TagStrategy):
    """Стратегия для текстовых тегов"""
    
    def get_value(self, tag_data: TagData, context: Dict[str, Any]) -> str:
        value = tag_data.default or tag_data.name
        
        # Обработка специальных значений
        if value == '[read_name]' and 'read_name' in context:
            return context['read_name']
        
        return value
    
    def get_display_name(self, tag_data: TagData) -> str:
        return tag_data.name
    
    def get_display_value(self, tag_data: TagData, context: Dict[str, Any]) -> str:
        return self.get_value(tag_data, context)
    
    def edit_dialog(self, tag_data: TagData, parent: Optional[QtWidgets.QWidget] = None) -> Optional[TagData]:
        current_value = tag_data.default or ''
        text, ok = QtWidgets.QInputDialog.getText(
            parent, f"Edit {tag_data.name}", "Enter value:",
            QtWidgets.QLineEdit.Normal, current_value
        )
        
        if ok:
            new_data = TagData.from_dict(tag_data.to_dict())
            new_data.default = text
            return new_data
        
        return None
    
    def get_node_color(self) -> QtGui.QColor:
        return QtGui.QColor(200, 180, 140)
    
    def get_node_shape(self) -> str:
        return "rounded_rect"


class SeparatorTagStrategy(TagStrategy):
    """Стратегия для разделителей"""
    
    def get_value(self, tag_data: TagData, context: Dict[str, Any]) -> str:
        return tag_data.value or '/'
    
    def get_display_name(self, tag_data: TagData) -> str:
        return tag_data.name
    
    def get_display_value(self, tag_data: TagData, context: Dict[str, Any]) -> str:
        return f"'{self.get_value(tag_data, context)}'"
    
    def edit_dialog(self, tag_data: TagData, parent: Optional[QtWidgets.QWidget] = None) -> Optional[TagData]:
        current_value = tag_data.value or '/'
        text, ok = QtWidgets.QInputDialog.getText(
            parent, "Edit Separator", "Enter separator:",
            QtWidgets.QLineEdit.Normal, current_value
        )
        
        if ok:
            new_data = TagData.from_dict(tag_data.to_dict())
            new_data.value = text
            return new_data
        
        return None
    
    def get_node_color(self) -> QtGui.QColor:
        return QtGui.QColor(160, 140, 200)
    
    def get_node_shape(self) -> str:
        return "rect"
    
    def format_for_path(self, value: str, prev_part: str, next_part: str) -> str:
        # Разделители не нуждаются в дополнительном форматировании
        return value


class FormatTagStrategy(TagStrategy):
    """Стратегия для формата файла"""
    
    def get_value(self, tag_data: TagData, context: Dict[str, Any]) -> str:
        format_ext = tag_data.format or 'exr'
        padding = tag_data.padding or '%04d'
        
        is_video = format_ext.lower() in ['mov', 'mp4', 'avi', 'mkv']
        
        if is_video:
            return f".{format_ext}"
        else:
            if context.get('live_preview'):
                bridge = nuke_bridge()
                if bridge.available:
                    try:
                        current_frame = bridge.get_current_frame()
                        frame_str = f"{current_frame:04d}"
                        return f".{frame_str}.{format_ext}"
                    except:
                        pass
            
            return f".{padding}.{format_ext}"
    
    def get_display_name(self, tag_data: TagData) -> str:
        return "format"
    
    def get_display_value(self, tag_data: TagData, context: Dict[str, Any]) -> str:
        return tag_data.format or 'exr'
