# atrain/core/models/path_models.py
"""
Модели данных для путей
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class PathContext:
    """Контекст для генерации пути"""
    # Основные переменные
    project_path: Optional[str] = None
    shot_name: Optional[str] = None
    sequence_name: Optional[str] = None
    user_name: Optional[str] = None
    department: Optional[str] = None
    task_name: Optional[str] = None
    
    # Для batch операций
    read_name: Optional[str] = None
    read_path: Optional[str] = None
    
    # Дополнительные переменные
    custom_vars: Dict[str, Any] = field(default_factory=dict)
    
    # Опции генерации
    live_preview: bool = False
    auto_increment: bool = True
    create_directories: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        data = {
            'project_path': self.project_path,
            'shot_name': self.shot_name,
            'sequence_name': self.sequence_name,
            'user_name': self.user_name,
            'department': self.department,
            'task_name': self.task_name,
            'read_name': self.read_name,
            'read_path': self.read_path,
            'live_preview': self.live_preview,
            'auto_increment': self.auto_increment,
            'create_directories': self.create_directories
        }
        
        # Добавляем custom переменные
        data.update(self.custom_vars)
        
        return {k: v for k, v in data.items() if v is not None}
    
    def update_from_read_node(self, read_node):
        """Обновить контекст из Read ноды"""
        if hasattr(read_node, 'name'):
            self.read_name = read_node.name()
        
        if hasattr(read_node, '__getitem__') and 'file' in read_node.knobs():
            self.read_path = read_node['file'].value()
            
            # Пытаемся извлечь информацию из пути
            if self.read_path:
                import os
                import re
                
                filename = os.path.basename(self.read_path)
                
                # Извлекаем shot name
                patterns = [
                    r'([A-Za-z0-9_]+)_\d+\.',
                    r'([A-Za-z0-9_]+)\.\d+\.',
                    r'(SH\d+)',
                    r'([A-Za-z0-9_]+)_comp',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, filename)
                    if match:
                        self.shot_name = match.group(1)
                        break
                
                # Извлекаем sequence
                seq_match = re.search(r'(SQ\d+)', self.read_path)
                if seq_match:
                    self.sequence_name = seq_match.group(1)


@dataclass
class PathResult:
    """Результат генерации пути"""
    success: bool
    path: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Дополнительная информация
    version: Optional[str] = None
    directory: Optional[str] = None
    filename: Optional[str] = None
    exists: bool = False
    
    def __post_init__(self):
        """Извлечение дополнительной информации"""
        if self.path:
            import os
            
            self.directory = os.path.dirname(self.path)
            self.filename = os.path.basename(self.path)
            self.exists = os.path.exists(self.path)
            
            # Извлекаем версию
            try:
                from ..utils.version import extract_version
                self.version = extract_version(self.path)
            except:
                pass
