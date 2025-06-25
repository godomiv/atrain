# atrain/core/models/batch_models.py
"""
Модели данных для batch операций
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any
from enum import Enum


class BatchOperationType(Enum):
    """Типы batch операций"""
    CREATE_WRITE = "create_write"
    TRANSCODE_READS = "transcode_reads"
    UPDATE_VERSIONS = "update_versions"
    RENDER_WRITES = "render_writes"


@dataclass
class BatchOperation:
    """Описание batch операции"""
    operation_type: BatchOperationType
    source_nodes: List[Any]
    preset_name: Optional[str] = None
    
    # Опции
    auto_increment: bool = True
    connect_nodes: bool = True
    create_directories: bool = True
    format_type: str = "exr"
    
    # Для рендера
    frame_range: Optional[tuple[int, int]] = None
    
    # Дополнительные параметры
    custom_path: Optional[str] = None
    options: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Преобразование типа если строка"""
        if isinstance(self.operation_type, str):
            self.operation_type = BatchOperationType(self.operation_type)
    
    @property
    def nodes_count(self) -> int:
        """Количество нод для обработки"""
        return len(self.source_nodes)


@dataclass 
class BatchResult:
    """Результат batch операции для одной ноды"""
    source_node: Any
    success: bool
    
    # Результаты
    created_node: Optional[Any] = None
    output_path: Optional[str] = None
    
    # Информация об ошибках
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Дополнительная информация
    source_name: str = ""
    operation_time: float = 0.0
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Извлечение имени источника"""
        if not self.source_name and self.source_node:
            try:
                if hasattr(self.source_node, 'name'):
                    self.source_name = self.source_node.name()
                else:
                    self.source_name = str(self.source_node)
            except:
                self.source_name = "Unknown"
    
    def add_error(self, error: str):
        """Добавить ошибку"""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str):
        """Добавить предупреждение"""
        self.warnings.append(warning)


@dataclass
class BatchOperationResult:
    """Общий результат batch операции"""
    operation: BatchOperation
    results: List[BatchResult] = field(default_factory=list)
    
    # Статистика
    total_time: float = 0.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    @property
    def total_count(self) -> int:
        """Общее количество операций"""
        return len(self.results)
    
    @property
    def success_count(self) -> int:
        """Количество успешных операций"""
        return sum(1 for r in self.results if r.success)
    
    @property
    def failed_count(self) -> int:
        """Количество неудачных операций"""
        return sum(1 for r in self.results if not r.success)
    
    @property
    def success_rate(self) -> float:
        """Процент успешных операций"""
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100
    
    def get_all_errors(self) -> List[str]:
        """Получить все ошибки"""
        errors = []
        for result in self.results:
            for error in result.errors:
                errors.append(f"{result.source_name}: {error}")
        return errors
    
    def get_all_warnings(self) -> List[str]:
        """Получить все предупреждения"""
        warnings = []
        for result in self.results:
            for warning in result.warnings:
                warnings.append(f"{result.source_name}: {warning}")
        return warnings
