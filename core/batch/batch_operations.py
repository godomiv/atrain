# atrain/core/batch/batch_operations.py
"""
Высокоуровневый интерфейс для batch операций
"""

from typing import List, Dict, Any, Optional, Callable

from .batch_processor import BatchProcessor
from ..models import BatchOperation, BatchOperationType, BatchOperationResult
from ..nuke import nuke_bridge
from ..utils import event_bus


class BatchOperations:
    """Фасад для batch операций"""
    
    def __init__(self):
        self.processor = BatchProcessor()
        self.bridge = nuke_bridge()
        self.event_bus = event_bus()
    
    def create_writes_for_reads(self, read_nodes: Optional[List[Any]] = None,
                               preset_name: Optional[str] = None,
                               format_type: str = "exr",
                               auto_increment: bool = True,
                               progress_callback: Optional[Callable] = None) -> BatchOperationResult:
        """
        Создать Write ноды для Read нод
        
        Args:
            read_nodes: Список Read нод (если None - использует выбранные)
            preset_name: Имя пресета для генерации путей
            format_type: Формат выходных файлов
            auto_increment: Автоинкремент версий
            progress_callback: Callback для прогресса
            
        Returns:
            BatchOperationResult: Результат операции
        """
        # Получаем Read ноды
        if read_nodes is None:
            read_nodes = self.get_selected_read_nodes()
        
        if not read_nodes:
            print("BatchOperations: No Read nodes to process")
            return BatchOperationResult(
                operation=BatchOperation(
                    operation_type=BatchOperationType.CREATE_WRITE,
                    source_nodes=[]
                )
            )
        
        # Создаем операцию
        operation = BatchOperation(
            operation_type=BatchOperationType.CREATE_WRITE,
            source_nodes=read_nodes,
            preset_name=preset_name,
            format_type=format_type,
            auto_increment=auto_increment
        )
        
        # Выполняем
        return self.processor.process_operation(operation, progress_callback)
    
    def transcode_reads(self, read_nodes: Optional[List[Any]] = None,
                       output_path: Optional[str] = None,
                       format_type: str = "mov",
                       frame_range: Optional[tuple] = None,
                       progress_callback: Optional[Callable] = None) -> BatchOperationResult:
        """
        Транскодировать Read ноды (создать Write + рендер)
        
        Args:
            read_nodes: Список Read нод
            output_path: Базовый путь вывода
            format_type: Формат выходных файлов
            frame_range: Диапазон кадров (first, last)
            progress_callback: Callback для прогресса
            
        Returns:
            BatchOperationResult: Результат операции
        """
        # Получаем Read ноды
        if read_nodes is None:
            read_nodes = self.get_selected_read_nodes()
        
        if not read_nodes:
            print("BatchOperations: No Read nodes to transcode")
            return BatchOperationResult(
                operation=BatchOperation(
                    operation_type=BatchOperationType.TRANSCODE_READS,
                    source_nodes=[]
                )
            )
        
        # Если не указан диапазон, используем из проекта
        if frame_range is None:
            frame_range = self.bridge.get_frame_range()
        
        # Создаем операцию
        operation = BatchOperation(
            operation_type=BatchOperationType.TRANSCODE_READS,
            source_nodes=read_nodes,
            format_type=format_type,
            frame_range=frame_range,
            custom_path=output_path
        )
        
        # Выполняем
        return self.processor.process_operation(operation, progress_callback)
    
    def update_write_versions(self, write_nodes: Optional[List[Any]] = None,
                            progress_callback: Optional[Callable] = None) -> BatchOperationResult:
        """
        Обновить версии Write нод
        
        Args:
            write_nodes: Список Write нод (если None - все A-Train Write ноды)
            progress_callback: Callback для прогресса
            
        Returns:
            BatchOperationResult: Результат операции
        """
        # Получаем Write ноды
        if write_nodes is None:
            write_nodes = self.get_atrain_write_nodes()
        
        if not write_nodes:
            print("BatchOperations: No Write nodes to update")
            return BatchOperationResult(
                operation=BatchOperation(
                    operation_type=BatchOperationType.UPDATE_VERSIONS,
                    source_nodes=[]
                )
            )
        
        # Создаем операцию
        operation = BatchOperation(
            operation_type=BatchOperationType.UPDATE_VERSIONS,
            source_nodes=write_nodes
        )
        
        # Выполняем
        return self.processor.process_operation(operation, progress_callback)
    
    def render_writes(self, write_nodes: Optional[List[Any]] = None,
                     frame_range: Optional[tuple] = None,
                     progress_callback: Optional[Callable] = None) -> BatchOperationResult:
        """
        Рендерить Write ноды
        
        Args:
            write_nodes: Список Write нод
            frame_range: Диапазон кадров
            progress_callback: Callback для прогресса
            
        Returns:
            BatchOperationResult: Результат операции
        """
        # Получаем Write ноды
        if write_nodes is None:
            write_nodes = self.get_selected_write_nodes()
        
        if not write_nodes:
            print("BatchOperations: No Write nodes to render")
            return BatchOperationResult(
                operation=BatchOperation(
                    operation_type=BatchOperationType.RENDER_WRITES,
                    source_nodes=[]
                )
            )
        
        # Создаем операцию
        operation = BatchOperation(
            operation_type=BatchOperationType.RENDER_WRITES,
            source_nodes=write_nodes,
            frame_range=frame_range
        )
        
        # Выполняем
        return self.processor.process_operation(operation, progress_callback)
    
    # =====================
    # Утилиты для получения нод
    # =====================
    
    def get_selected_read_nodes(self) -> List[Any]:
        """Получить выбранные Read ноды"""
        return self.bridge.get_selected_nodes('Read')
    
    def get_selected_write_nodes(self) -> List[Any]:
        """Получить выбранные Write ноды"""
        return self.bridge.get_selected_nodes('Write')
    
    def get_all_read_nodes(self) -> List[Any]:
        """Получить все Read ноды"""
        return self.bridge.get_all_nodes('Read')
    
    def get_all_write_nodes(self) -> List[Any]:
        """Получить все Write ноды"""
        return self.bridge.get_all_nodes('Write')
    
    def get_atrain_write_nodes(self) -> List[Any]:
        """Получить все Write ноды созданные A-Train"""
        all_writes = self.get_all_write_nodes()
        atrain_writes = []
        
        for write in all_writes:
            note = self.bridge.get_knob_value(write, 'note', '')
            if 'A-Train' in note:
                atrain_writes.append(write)
        
        return atrain_writes
    
    def get_read_nodes_info(self, read_nodes: Optional[List[Any]] = None) -> List[Dict[str, str]]:
        """
        Получить информацию о Read нодах для UI
        
        Returns:
            List[Dict]: Информация о нодах
        """
        if read_nodes is None:
            read_nodes = self.get_selected_read_nodes()
        
        from ..nuke import NodeUtils
        node_utils = NodeUtils()
        
        nodes_info = []
        for node in read_nodes:
            info = node_utils.get_node_file_info(node)
            nodes_info.append({
                'node_name': info['node_name'],
                'file_name': info['clean_name'],
                'file_path': info['file_path'],
                'has_file': bool(info['file_path'])
            })
        
        return nodes_info
    
    # =====================
    # Быстрые операции для совместимости
    # =====================
    
    def quick_transcode(self, base_output_path: str, format_type: str = "exr") -> List[Any]:
        """
        Быстрое транскодирование выбранных Read нод (старый API)
        
        Args:
            base_output_path: Базовый путь с [read_name] placeholder
            format_type: Формат файлов
            
        Returns:
            List[Any]: Созданные Write ноды
        """
        result = self.transcode_reads(
            output_path=base_output_path,
            format_type=format_type,
            frame_range=None  # Не рендерим, только создаем Write
        )
        
        # Возвращаем список созданных нод для совместимости
        created_nodes = []
        for batch_result in result.results:
            if batch_result.success and batch_result.created_node:
                created_nodes.append(batch_result.created_node)
        
        return created_nodes
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику операций"""
        return self.processor.get_stats()
    
    def reset_stats(self):
        """Сбросить статистику"""
        self.processor.reset_stats()


# Глобальный экземпляр для удобства
_batch_operations = None

def get_batch_operations() -> BatchOperations:
    """Получить глобальный экземпляр BatchOperations"""
    global _batch_operations
    if _batch_operations is None:
        _batch_operations = BatchOperations()
    return _batch_operations
