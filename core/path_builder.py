# atrain/core/path_builder.py
"""
Построитель путей с использованием стратегий тегов
"""

import os
import re
from typing import List, Dict, Any, Optional

from .models import TagData, PathContext
from .tags import tag_factory
from .nuke import nuke_bridge
from .utils import event_bus


class PathBuilder:
    """Улучшенный построитель путей"""
    
    def __init__(self):
        self.tags: List[TagData] = []
        self.tag_factory = tag_factory()
        self.bridge = nuke_bridge()
        self._context: PathContext = PathContext()
    
    def clear(self):
        """Очистить все теги"""
        self.tags.clear()
        event_bus().publish('path_cleared')
    
    def add_tag(self, tag_data: TagData) -> int:
        """
        Добавить тег
        
        Returns:
            Индекс добавленного тега
        """
        self.tags.append(tag_data)
        event_bus().publish('tag_added', tag_data)
        return len(self.tags) - 1
    
    def remove_tag(self, index: int) -> bool:
        """Удалить тег по индексу"""
        if 0 <= index < len(self.tags):
            removed_tag = self.tags.pop(index)
            event_bus().publish('tag_removed', removed_tag)
            return True
        return False
    
    def insert_tag(self, index: int, tag_data: TagData):
        """Вставить тег в позицию"""
        self.tags.insert(index, tag_data)
        event_bus().publish('tag_inserted', {'index': index, 'tag': tag_data})
    
    def move_tag(self, from_index: int, to_index: int) -> bool:
        """Переместить тег"""
        if (0 <= from_index < len(self.tags) and 
            0 <= to_index < len(self.tags)):
            tag = self.tags.pop(from_index)
            self.tags.insert(to_index, tag)
            event_bus().publish('tag_moved', {
                'from': from_index,
                'to': to_index,
                'tag': tag
            })
            return True
        return False
    
    def set_context(self, context: PathContext):
        """Установить контекст для генерации пути"""
        self._context = context
    
    def update_context(self, **kwargs):
        """Обновить поля контекста"""
        for key, value in kwargs.items():
            if hasattr(self._context, key):
                setattr(self._context, key, value)
    
    def build_path(self, live_preview: bool = False) -> str:
        """Построить путь из тегов"""
        if not self.tags:
            return ""
        
        try:
            # Обновляем контекст из Nuke если доступен
            self._update_context_from_nuke()
            
            # Добавляем live_preview в контекст
            self._context.live_preview = live_preview
            
            # Преобразуем в словарь для стратегий
            context_dict = self._context.to_dict()
            
            result_parts = []
            
            for i, tag in enumerate(self.tags):
                strategy = self.tag_factory.get_strategy(tag.type)
                if not strategy:
                    continue
                
                # Получаем значение через стратегию
                value = strategy.get_value(tag, context_dict)
                
                if value:
                    # Определяем предыдущую и следующую части для форматирования
                    prev_part = ''.join(result_parts) if result_parts else ''
                    next_part = ''  # Пока не знаем следующую часть
                    
                    # Форматируем значение
                    formatted_value = strategy.format_for_path(value, prev_part, next_part)
                    
                    if formatted_value:
                        result_parts.append(formatted_value)
            
            # Объединяем части
            full_path = ''.join(result_parts)
            
            # Очистка пути
            full_path = self._clean_path(full_path)
            
            # Публикуем событие
            event_bus().publish('path_built', full_path)
            
            return full_path
            
        except Exception as e:
            print(f"PathBuilder: Error building path: {e}")
            return ""
    
    def _update_context_from_nuke(self):
        """Обновить контекст из текущего состояния Nuke"""
        if not self.bridge.available:
            return
        
        # Обновляем базовую информацию
        project_info = self.bridge.get_project_info()
        
        self._context.project_path = self.bridge.find_project_root()
        self._context.user_name = project_info['user']
        
        # Пытаемся извлечь shot name из имени скрипта
        script_name = project_info['script_name']
        if script_name and script_name != 'untitled':
            self._context.shot_name = self._extract_shot_name(script_name)
            self._context.sequence_name = self._extract_sequence_name(script_name)
        
        # Обновляем информацию о выбранных Read нодах
        selected_reads = self.bridge.get_selected_nodes('Read')
        if selected_reads:
            self._context.update_from_read_node(selected_reads[0])
    
    def _extract_shot_name(self, script_name: str) -> str:
        """Извлечь имя шота из имени скрипта"""
        patterns = [
            r'([A-Za-z0-9_]+)_comp',
            r'([A-Za-z0-9_]+)_v\d+',
            r'(SH\d+)',
            r'([A-Za-z0-9_]+)\.nk'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, script_name)
            if match:
                return match.group(1)
        
        return script_name
    
    def _extract_sequence_name(self, script_name: str) -> str:
        """Извлечь имя последовательности"""
        # Ищем паттерн типа SQ010
        seq_match = re.search(r'(SQ\d+)', script_name)
        if seq_match:
            return seq_match.group(1)
        
        # Ищем паттерн типа SEQ01
        seq_match = re.search(r'(SEQ\d+)', script_name)
        if seq_match:
            return seq_match.group(1)
        
        return "sequence"
    
    def _clean_path(self, path: str) -> str:
        """Очистить путь от лишних символов"""
        # Убираем двойные подчеркивания
        while '__' in path:
            path = path.replace('__', '_')
        
        # Убираем двойные слеши
        while '//' in path:
            path = path.replace('//', '/')
        
        # Убираем подчеркивания перед/после разделителей
        path = re.sub(r'_+([/\\])', r'\1', path)
        path = re.sub(r'([/\\])_+', r'\1', path)
        
        # Убираем подчеркивание перед точкой
        path = re.sub(r'_+\.', '.', path)
        
        return path
    
    def validate_path(self, path: str) -> tuple[bool, list[str]]:
        """Валидировать путь"""
        issues = []
        
        if not path:
            issues.append("Path is empty")
            return False, issues
        
        # Проверка недопустимых символов
        invalid_chars = ['<', '>', '|', '"', '?', '*']
        if any(char in path for char in invalid_chars):
            issues.append("Path contains invalid characters")
        
        # Проверка длины пути (Windows limitation)
        if len(path) > 260:
            issues.append("Path too long (>260 characters)")
        
        # Проверка расширения
        known_extensions = {
            '.exr', '.dpx', '.jpg', '.jpeg', '.png', 
            '.tif', '.tiff', '.mov', '.mp4'
        }
        if not any(path.lower().endswith(ext) for ext in known_extensions):
            issues.append("Unknown or missing file extension")
        
        # Проверка версии
        from .utils.version import extract_version
        if not extract_version(path):
            issues.append("No version found in path")
        
        return len(issues) == 0, issues
    
    def get_path_info(self) -> Dict[str, Any]:
        """Получить информацию о текущем пути"""
        path = self.build_path()
        is_valid, issues = self.validate_path(path)
        
        info = {
            'path': path,
            'is_valid': is_valid,
            'issues': issues,
            'tags_count': len(self.tags),
            'context': self._context.to_dict()
        }
        
        if path:
            info['directory'] = os.path.dirname(path)
            info['filename'] = os.path.basename(path)
            
            from .utils.version import extract_version
            info['version'] = extract_version(path)
        
        return info
    
    # =====================
    # Методы для совместимости со старым API
    # =====================
    
    def clear_tags(self):
        """Очистить все теги (старый API)"""
        self.clear()
    
    def set_context_var(self, key: str, value: Any):
        """Установить контекстную переменную (старый API)"""
        self.update_context(**{key: value})
    
    def _evaluate_expression_live(self, expression: str) -> str:
        """Оценка expression (для совместимости с UI)"""
        try:
            if self.bridge.available:
                simple_expressions = {
                    '[value root.frame]': str(self.bridge.get_current_frame()),
                    '[value root.first_frame]': str(self.bridge.get_frame_range()[0]),
                    '[value root.last_frame]': str(self.bridge.get_frame_range()[1]),
                    '[file rootname [value root.name]]': self.bridge.get_script_basename(),
                    '[file dirname [value root.name]]': self.bridge.get_script_path()
                }
                
                result = expression
                for expr, value in simple_expressions.items():
                    if expr in result:
                        result = result.replace(expr, value)
                
                return result
        except:
            pass
        
        return expression
    
    # Динамические обработчики для совместимости
    @property
    def dynamic_handlers(self):
        """Обработчики для совместимости со старым UI"""
        return {
            'shot name': self._get_shot_name,
            'project path': self._get_project_path,
            'user': self._get_user_name,
            '[read_name]': self._get_read_name,
            'sequence': self._get_sequence_name,
            'scene': self._get_scene_name,
            'department': self._get_department,
            'task': self._get_task_name,
        }
    
    def _get_shot_name(self):
        return self._context.shot_name or "shot_name"
    
    def _get_project_path(self):
        return self._context.project_path or "/project/path"
    
    def _get_user_name(self):
        return self._context.user_name or "user"
    
    def _get_read_name(self):
        return self._context.read_name or "read_name"
    
    def _get_sequence_name(self):
        return self._context.sequence_name or "sequence"
    
    def _get_scene_name(self):
        if self.bridge.available:
            return self.bridge.get_script_basename()
        return "scene"
    
    def _get_department(self):
        return self._context.department or "comp"
    
    def _get_task_name(self):
        return self._context.task_name or "task"


# Для обратной совместимости
def build_path_from_tags(tags: List[TagData], live_preview: bool = False) -> str:
    """Построить путь из списка тегов (старый API)"""
    builder = PathBuilder()
    for tag in tags:
        builder.add_tag(tag)
    return builder.build_path(live_preview)
