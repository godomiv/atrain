# atrain/core/path_builder.py
"""
Система построения путей A-Train - ИСПРАВЛЕНО: padding с %04d
"""

import os
import re
import datetime
import getpass
from typing import List, Dict, Any, Optional, Callable, Tuple

try:
    import nuke
    NUKE_AVAILABLE = True
except ImportError:
    nuke = None
    NUKE_AVAILABLE = False

from .event_bus import EventBus

class PathBuilder:
    """Строитель путей из тегов - ИСПРАВЛЕНО padding с %04d"""
    
    def __init__(self):
        self.tags = []
        self.context_vars = {}
        
        self.dynamic_handlers = {
            'shot name': self._get_shot_name,
            'project path': self._get_project_path,
            'user': self._get_user_name,
            '[read_name]': self._get_read_name,
            'sequence': self._get_sequence_name,
            'scene': self._get_scene_name,
            'department': self._get_department,
            'task': self._get_task_name,
        }
        
        self._cache = {}
        print("PathBuilder: Initialized with dynamic handlers")
    
    def clear_tags(self):
        """Очистить все теги"""
        self.tags.clear()
        self._cache.clear()
    
    def add_tag(self, tag_data):
        """Добавить тег"""
        tag_copy = tag_data.copy()
        self.tags.append(tag_copy)
        self._cache.clear()
        return len(self.tags) - 1
    
    def remove_tag(self, index):
        """Удалить тег по индексу"""
        if 0 <= index < len(self.tags):
            self.tags.pop(index)
            self._cache.clear()
            return True
        return False
    
    def build_path(self, live_preview=False):
        """ИСПРАВЛЕНО: построение пути с правильным padding %04d"""
        if not self.tags:
            return ""
        
        try:
            result_parts = []
            
            for tag_data in self.tags:
                tag_type = tag_data.get('type', 'text')
                tag_name = tag_data.get('name', '')
                
                if tag_type == 'separator':
                    separator_value = tag_data.get('value', '/')
                    result_parts.append(separator_value)
                
                elif tag_type == 'format':
                    # ИСПРАВЛЕНО: правильный padding с %
                    version = tag_data.get('version', 'v01')
                    padding = tag_data.get('padding', '%04d')  # ИСПРАВЛЕНО: % добавлен!
                    format_ext = tag_data.get('format', 'exr')
                    
                    is_video = format_ext.lower() in ['mov', 'mp4', 'avi', 'mkv']
                    
                    if is_video:
                        result_parts.append(f".{format_ext}")
                    else:
                        if live_preview and NUKE_AVAILABLE:
                            try:
                                current_frame = nuke.frame()
                                frame_str = f"{current_frame:04d}"
                                result_parts.append(f".{frame_str}.{format_ext}")
                            except:
                                # ИСПРАВЛЕНО: при ошибке показываем %04d
                                result_parts.append(f".{padding}.{format_ext}")
                        else:
                            # ИСПРАВЛЕНО: статический режим всегда показывает %04d
                            result_parts.append(f".{padding}.{format_ext}")
                
                elif tag_type == 'expression':
                    expression = tag_data.get('expression', '')
                    if expression:
                        if live_preview:
                            evaluated = self._evaluate_expression_live(expression)
                        else:
                            evaluated = expression
                        
                        if evaluated:
                            if (result_parts and 
                                not result_parts[-1].endswith('/') and 
                                not result_parts[-1].endswith('_') and
                                not result_parts[-1].endswith('\\')):
                                result_parts.append('_')
                            result_parts.append(evaluated)
                
                elif tag_type == 'version':
                    version_value = tag_data.get('version', 'v01')
                    if version_value:
                        if (result_parts and 
                            not result_parts[-1].endswith('/') and 
                            not result_parts[-1].endswith('_') and
                            not result_parts[-1].endswith('\\')):
                            result_parts.append('_')
                        result_parts.append(version_value)
                
                elif tag_type == 'dynamic':
                    if tag_name in self.dynamic_handlers:
                        value = self.dynamic_handlers[tag_name]()
                    else:
                        value = tag_data.get('default', tag_name)
                    
                    if value:
                        if (result_parts and 
                            not result_parts[-1].endswith('/') and 
                            not result_parts[-1].endswith('_') and
                            not result_parts[-1].endswith('\\')):
                            result_parts.append('_')
                        result_parts.append(str(value))
                
                else:
                    value = tag_data.get('default', '')
                    
                    if value == '[read_name]' and live_preview:
                        value = self._get_read_name()
                    
                    if value:
                        if (result_parts and 
                            not result_parts[-1].endswith('/') and 
                            not result_parts[-1].endswith('_') and
                            not result_parts[-1].endswith('\\')):
                            result_parts.append('_')
                        result_parts.append(str(value))
            
            # Объединяем все части
            full_path = ''.join(result_parts)
            
            # Убираем двойные подчеркивания
            while '__' in full_path:
                full_path = full_path.replace('__', '_')
            
            # Убираем подчеркивания перед/после разделителей
            full_path = re.sub(r'_+([/\\])', r'\1', full_path)
            full_path = re.sub(r'([/\\])_+', r'\1', full_path)
            
            return full_path
            
        except Exception as e:
            print(f"PathBuilder: Error building path: {e}")
            return ""
    
    def _evaluate_expression_live(self, expression):
        """Оценка expression в live режиме"""
        try:
            if not NUKE_AVAILABLE:
                return expression
            
            simple_expressions = {
                '[value root.frame]': str(nuke.frame()),
                '[value root.first_frame]': str(int(nuke.root()['first_frame'].value())),
                '[value root.last_frame]': str(int(nuke.root()['last_frame'].value())),
                '[file rootname [value root.name]]': self._get_script_name_without_ext(),
                '[file dirname [value root.name]]': self._get_script_dir()
            }
            
            result = expression
            for expr, value in simple_expressions.items():
                if expr in result:
                    result = result.replace(expr, value)
            
            return result
            
        except Exception as e:
            print(f"PathBuilder: Error evaluating live expression '{expression}': {e}")
            return expression
    
    def _get_script_name_without_ext(self):
        """Получить имя скрипта без расширения"""
        try:
            if NUKE_AVAILABLE and nuke.root().name():
                script_name = os.path.basename(nuke.root().name())
                return os.path.splitext(script_name)[0]
            return 'untitled'
        except:
            return 'untitled'
    
    def _get_script_dir(self):
        """Получить директорию скрипта"""
        try:
            if NUKE_AVAILABLE and nuke.root().name():
                return os.path.dirname(nuke.root().name())
            return '/tmp'
        except:
            return '/tmp'
    
    def _get_shot_name(self):
        """Получение имени шота"""
        try:
            if NUKE_AVAILABLE and nuke.root().name():
                script_path = nuke.root().name()
                filename = os.path.basename(script_path)
                
                patterns = [
                    r'([A-Za-z0-9_]+)_comp',
                    r'([A-Za-z0-9_]+)_v\d+',
                    r'(SH\d+)',
                    r'([A-Za-z0-9_]+)\.nk'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, filename)
                    if match:
                        return match.group(1)
            
            return "shot_name"
        except:
            return "shot_name"
    
    def _get_project_path(self):
        """Получение пути проекта"""
        try:
            if NUKE_AVAILABLE and nuke.root().name():
                script_dir = os.path.dirname(nuke.root().name())
                
                current_dir = script_dir
                max_levels = 5
                
                for _ in range(max_levels):
                    if not current_dir or current_dir == os.path.dirname(current_dir):
                        break
                    
                    project_markers = ['scenes', 'scripts', 'comp', 'render', '.project', 'shots']
                    
                    try:
                        dir_contents = os.listdir(current_dir)
                        if any(marker in dir_contents for marker in project_markers):
                            return current_dir
                    except:
                        pass
                    
                    current_dir = os.path.dirname(current_dir)
                
                return script_dir
            
            return "/project/path"
        except:
            return "/project/path"
    
    def _get_user_name(self):
        """Получение имени пользователя"""
        try:
            return getpass.getuser()
        except:
            return "user"
    
    def _get_read_name(self):
        """Получение имени Read ноды"""
        try:
            if NUKE_AVAILABLE:
                selected_reads = nuke.selectedNodes("Read")
                if selected_reads:
                    return selected_reads[0].name()
                
                all_reads = nuke.allNodes("Read")
                if all_reads:
                    return all_reads[0].name()
            
            return "read_name"
        except:
            return "read_name"
    
    def _get_sequence_name(self):
        """Получение имени последовательности"""
        try:
            shot_name = self._get_shot_name()
            
            seq_match = re.search(r'(SQ\d+)', shot_name)
            if seq_match:
                return seq_match.group(1)
            
            seq_match = re.search(r'([A-Za-z]+\d+)_', shot_name)
            if seq_match:
                return seq_match.group(1)
            
            return "sequence"
        except:
            return "sequence"
    
    def _get_scene_name(self):
        """Получение имени сцены"""
        try:
            if NUKE_AVAILABLE and nuke.root().name():
                script_name = os.path.splitext(os.path.basename(nuke.root().name()))[0]
                return script_name
            return "scene"
        except:
            return "scene"
    
    def _get_department(self):
        """Получение отдела"""
        try:
            if NUKE_AVAILABLE and nuke.root().name():
                script_path = nuke.root().name()
                
                departments = {
                    'comp': ['comp', 'composite', 'compositing'],
                    'lighting': ['lighting', 'light', 'lgt'],
                    'fx': ['fx', 'effects'],
                    'layout': ['layout', 'previs'],
                    'animation': ['anim', 'animation'],
                    'modeling': ['model', 'modeling']
                }
                
                path_lower = script_path.lower()
                for dept, keywords in departments.items():
                    if any(keyword in path_lower for keyword in keywords):
                        return dept
            
            return "comp"
        except:
            return "comp"
    
    def _get_task_name(self):
        """Получение имени задачи"""
        try:
            department = self._get_department()
            
            if department == 'comp':
                return "composite"
            elif department == 'lighting':
                return "beauty"
            elif department == 'fx':
                return "sim"
            else:
                return department
        except:
            return "task"
