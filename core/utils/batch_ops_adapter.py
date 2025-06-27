# atrain/utils/batch_ops_adapter.py
"""
Адаптер для совместимости со старым batch_ops API
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from ..core.batch import get_batch_operations
from ..core.models import BatchOperation as NewBatchOperation, BatchResult as NewBatchResult


# Старые dataclasses для совместимости
@dataclass
class BatchOperation:
    """Старая структура для совместимости"""
    operation_type: str
    source_nodes: List[Any]
    preset_name: Optional[str] = None
    auto_increment: bool = True
    connect_nodes: bool = True
    create_directories: bool = True
    format_type: str = "exr"
    frame_range: Optional[tuple] = None


@dataclass
class BatchResult:
    """Старая структура для совместимости"""
    source_node: Any
    success: bool
    created_node: Optional[Any] = None
    output_path: Optional[str] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class BatchOperations:
    """Адаптер для старого BatchOperations API"""
    
    def __init__(self):
        self._batch_ops = get_batch_operations()
        
        # Статистика для совместимости
        self.operation_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'last_operation_time': None
        }
    
    def get_selected_read_nodes(self) -> List[Any]:
        """Получить выбранные Read ноды"""
        return self._batch_ops.get_selected_read_nodes()
    
    def get_all_read_nodes(self) -> List[Any]:
        """Получить все Read ноды"""
        return self._batch_ops.get_all_read_nodes()
    
    def get_selected_write_nodes(self) -> List[Any]:
        """Получить выбранные Write ноды"""
        return self._batch_ops.get_selected_write_nodes()
    
    def get_filename_from_read(self, read_node) -> str:
        """Получить имя файла из Read ноды"""
        info = self._batch_ops.bridge.get_knob_value(read_node, 'file', '')
        if info:
            from ..core.nuke import NodeUtils
            node_utils = NodeUtils()
            return node_utils.extract_clean_name(info)
        return read_node.name() if hasattr(read_node, 'name') else str(read_node)
    
    def get_read_nodes_info(self) -> List[Dict[str, str]]:
        """Получить информацию о Read нодах"""
        return self._batch_ops.get_read_nodes_info()
    
    def create_write_from_read(self, read_node, output_path, format_type="exr") -> Optional[Any]:
        """Создать Write ноду для Read ноды"""
        # Используем новый API
        result = self._batch_ops.create_writes_for_reads(
            read_nodes=[read_node],
            format_type=format_type,
            auto_increment=True
        )
        
        if result.success_count > 0:
            return result.results[0].created_node
        return None
    
    def create_write_nodes_batch(self, operation: BatchOperation,
                               progress_callback: Optional[Callable] = None) -> List[BatchResult]:
        """Создать Write ноды batch"""
        # Конвертируем в новый формат и выполняем
        new_result = self._batch_ops.create_writes_for_reads(
            read_nodes=operation.source_nodes,
            preset_name=operation.preset_name,
            format_type=operation.format_type,
            auto_increment=operation.auto_increment,
            progress_callback=progress_callback
        )
        
        # Конвертируем результаты в старый формат
        old_results = []
        for new_res in new_result.results:
            old_result = BatchResult(
                source_node=new_res.source_node,
                success=new_res.success,
                created_node=new_res.created_node,
                output_path=new_res.output_path,
                errors=new_res.errors,
                warnings=new_res.warnings
            )
            old_results.append(old_result)
        
        # Обновляем статистику
        self.operation_stats['total_operations'] += 1
        self.operation_stats['successful_operations'] += new_result.success_count
        self.operation_stats['failed_operations'] += new_result.failed_count
        
        return old_results
    
    def render_write_nodes_batch(self, write_nodes: List[Any], frame_range: tuple,
                               progress_callback: Optional[Callable] = None) -> List[BatchResult]:
        """Batch рендер Write нод"""
        # Используем новый API
        new_result = self._batch_ops.render_writes(
            write_nodes=write_nodes,
            frame_range=frame_range,
            progress_callback=progress_callback
        )
        
        # Конвертируем результаты
        old_results = []
        for new_res in new_result.results:
            old_result = BatchResult(
                source_node=new_res.source_node,
                success=new_res.success,
                output_path=new_res.output_path,
                errors=new_res.errors,
                warnings=new_res.warnings
            )
            old_results.append(old_result)
        
        return old_results
    
    def transcode_selected_reads(self, base_output_path: str, format_type: str = "exr") -> List[Any]:
        """Транскодировать выбранные Read ноды"""
        return self._batch_ops.quick_transcode(base_output_path, format_type)
    
    def batch_create_writes_with_versions(self, read_nodes: List[Any],
                                        base_path: str, format_type: str = "exr") -> List[Any]:
        """Создать Write ноды с версиями"""
        result = self._batch_ops.create_writes_for_reads(
            read_nodes=read_nodes,
            format_type=format_type,
            auto_increment=True
        )
        
        created_writes = []
        for batch_result in result.results:
            if batch_result.success and batch_result.created_node:
                created_writes.append(batch_result.created_node)
        
        return created_writes
    
    def validate_read_nodes(self, read_nodes: List[Any]) -> Dict[str, List[Any]]:
        """Валидировать Read ноды"""
        return self._batch_ops.processor.validate_nodes(read_nodes, 'Read')
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику"""
        # Объединяем старую и новую статистику
        new_stats = self._batch_ops.get_stats()
        
        return {
            'total_operations': self.operation_stats['total_operations'] + new_stats['total_operations'],
            'successful_operations': self.operation_stats['successful_operations'] + new_stats['successful_operations'],
            'failed_operations': self.operation_stats['failed_operations'] + new_stats['failed_operations'],
            'last_operation_time': self.operation_stats['last_operation_time']
        }
    
    def reset_stats(self):
        """Сбросить статистику"""
        self.operation_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'last_operation_time': None
        }
        self._batch_ops.reset_stats()
    
    def export_batch_results(self, results: List[BatchResult], export_path: str) -> bool:
        """Экспорт результатов"""
        try:
            import json
            import datetime
            
            export_data = {
                'export_time': datetime.datetime.now().isoformat(),
                'total_operations': len(results),
                'successful_operations': sum(1 for r in results if r.success),
                'failed_operations': sum(1 for r in results if not r.success),
                'results': []
            }
            
            for result in results:
                result_data = {
                    'source_node': result.source_node.name() if hasattr(result.source_node, 'name') else 'Unknown',
                    'success': result.success,
                    'created_node': result.created_node.name() if result.created_node and hasattr(result.created_node, 'name') else None,
                    'output_path': result.output_path,
                    'errors': result.errors,
                    'warnings': result.warnings
                }
                export_data['results'].append(result_data)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"BatchOperations: Error exporting results: {e}")
            return False
