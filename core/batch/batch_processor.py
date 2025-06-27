# atrain/core/batch/batch_processor.py
"""
Процессор batch операций с новой архитектурой
"""

import os
import time
from typing import List, Dict, Any, Optional, Callable

from ..models import BatchOperation, BatchResult, BatchOperationResult, PathContext
from ..nuke import nuke_bridge, NodeUtils
from ..path_builder import PathBuilder
from ..storage import StorageManager
from ..utils import event_bus


class BatchProcessor:
    """Процессор для выполнения batch операций"""
    
    def __init__(self):
        self.bridge = nuke_bridge()
        self.node_utils = NodeUtils()
        self.storage = StorageManager()
        self.event_bus = event_bus()
        
        # Статистика операций
        self.stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_time': 0.0
        }
    
    def process_operation(self, operation: BatchOperation,
                         progress_callback: Optional[Callable] = None) -> BatchOperationResult:
        """
        Выполнить batch операцию
        
        Args:
            operation: Операция для выполнения
            progress_callback: Callback для прогресса (current, total, message)
            
        Returns:
            BatchOperationResult: Результат операции
        """
        start_time = time.time()
        result = BatchOperationResult(operation=operation)
        result.start_time = time.strftime('%Y-%m-%d %H:%M:%S')
        
        self.stats['total_operations'] += 1
        
        try:
            if operation.operation_type.value == 'create_write':
                result = self._process_create_write(operation, progress_callback)
            
            elif operation.operation_type.value == 'transcode_reads':
                result = self._process_transcode_reads(operation, progress_callback)
            
            elif operation.operation_type.value == 'update_versions':
                result = self._process_update_versions(operation, progress_callback)
            
            elif operation.operation_type.value == 'render_writes':
                result = self._process_render_writes(operation, progress_callback)
            
            else:
                raise ValueError(f"Unknown operation type: {operation.operation_type}")
            
            # Обновляем статистику
            self.stats['successful_operations'] += result.success_count
            self.stats['failed_operations'] += result.failed_count
            
        except Exception as e:
            print(f"BatchProcessor: Error processing operation: {e}")
            # Создаем failed результаты для всех нод
            for node in operation.source_nodes:
                batch_result = BatchResult(
                    source_node=node,
                    success=False,
                    errors=[f"Operation failed: {e}"]
                )
                result.results.append(batch_result)
        
        # Финализируем результат
        result.end_time = time.strftime('%Y-%m-%d %H:%M:%S')
        result.total_time = time.time() - start_time
        self.stats['total_time'] += result.total_time
        
        # Публикуем событие
        self.event_bus.publish('batch_operation_completed', result)
        
        return result
    
    def _process_create_write(self, operation: BatchOperation,
                            progress_callback: Optional[Callable]) -> BatchOperationResult:
        """Обработать создание Write нод"""
        result = BatchOperationResult(operation=operation)
        total = len(operation.source_nodes)
        
        # Генерируем базовый путь
        base_path = self._generate_base_path(operation)
        if not base_path:
            # Ошибка для всех нод
            for node in operation.source_nodes:
                batch_result = BatchResult(
                    source_node=node,
                    success=False,
                    errors=["Failed to generate base path"]
                )
                result.results.append(batch_result)
            return result
        
        # Обрабатываем каждую ноду
        for i, node in enumerate(operation.source_nodes):
            if progress_callback:
                node_name = self.node_utils.get_node_file_info(node)['clean_name']
                progress_callback(i, total, f"Processing: {node_name}")
            
            batch_result = self._create_write_for_node(node, base_path, operation)
            result.results.append(batch_result)
            
            if progress_callback:
                status = "Success" if batch_result.success else "Failed"
                progress_callback(i + 1, total, f"{status}: {batch_result.source_name}")
        
        return result
    
    def _create_write_for_node(self, node: Any, base_path: str,
                              operation: BatchOperation) -> BatchResult:
        """Создать Write ноду для конкретной ноды"""
        batch_result = BatchResult(source_node=node, success=False)
        
        try:
            # Получаем информацию о ноде
            node_info = self.node_utils.get_node_file_info(node)
            batch_result.source_name = node_info['clean_name']
            
            # Создаем контекст
            context = PathContext()
            context.read_name = node_info['clean_name']
            context.read_path = node_info['file_path']
            context.auto_increment = operation.auto_increment
            
            # Заменяем placeholder в пути
            output_path = base_path.replace('[read_name]', context.read_name)
            
            # Автоинкремент если нужно
            if operation.auto_increment:
                from ..utils.version import get_next_available_version
                output_path = get_next_available_version(output_path)
            
            # Создаем Write ноду
            write_node = self.node_utils.create_write_node(output_path)
            
            if write_node:
                # Подключаем к источнику
                if operation.connect_nodes:
                    write_node.setInput(0, node)
                    self.node_utils.position_node_relative(write_node, node, 0, 80)
                
                # Добавляем метку
                self.bridge.set_knob_value(
                    write_node, 'note',
                    f'A-Train Batch\nSource: {batch_result.source_name}'
                )
                
                batch_result.success = True
                batch_result.created_node = write_node
                batch_result.output_path = output_path
            else:
                batch_result.add_error("Failed to create Write node")
            
        except Exception as e:
            batch_result.add_error(f"Error: {e}")
        
        return batch_result
    
    def _generate_base_path(self, operation: BatchOperation) -> Optional[str]:
        """Генерировать базовый путь для операции"""
        try:
            if operation.custom_path:
                return operation.custom_path
            
            if operation.preset_name:
                # Используем пресет
                preset = self.storage.get_preset(operation.preset_name)
                if not preset:
                    print(f"BatchProcessor: Preset '{operation.preset_name}' not found")
                    return None
                
                # Строим путь из пресета
                path_builder = PathBuilder()
                
                # Добавляем теги из пресета
                all_tags = self.storage.get_all_tags()
                tags_dict = {tag.name: tag for tag in all_tags}
                
                for tag_name in preset.tags:
                    if tag_name in tags_dict:
                        path_builder.add_tag(tags_dict[tag_name])
                
                # Добавляем format тег
                from ..models import TagData, TagType
                format_tag = TagData(
                    name='format',
                    type=TagType.FORMAT,
                    format=operation.format_type,
                    padding='%04d'
                )
                path_builder.add_tag(format_tag)
                
                return path_builder.build_path()
            
            else:
                # Генерируем дефолтный путь
                project_path = self.bridge.find_project_root()
                script_name = self.bridge.get_script_basename()
                
                if script_name and script_name != 'untitled':
                    return f"{project_path}/{script_name}_[read_name]_v01.%04d.{operation.format_type}"
                else:
                    return f"{project_path}/render_[read_name]_v01.%04d.{operation.format_type}"
        
        except Exception as e:
            print(f"BatchProcessor: Error generating base path: {e}")
            return None
    
    def _process_transcode_reads(self, operation: BatchOperation,
                               progress_callback: Optional[Callable]) -> BatchOperationResult:
        """Обработать транскодирование Read нод"""
        # Транскодирование = создание Write + рендер
        # Сначала создаем Write ноды
        result = self._process_create_write(operation, progress_callback)
        
        # Если есть успешные Write ноды, запускаем рендер
        writes_to_render = []
        for batch_result in result.results:
            if batch_result.success and batch_result.created_node:
                writes_to_render.append(batch_result.created_node)
        
        if writes_to_render and operation.frame_range:
            # Создаем операцию рендера
            render_op = BatchOperation(
                operation_type='render_writes',
                source_nodes=writes_to_render,
                frame_range=operation.frame_range
            )
            
            # Рендерим
            render_result = self._process_render_writes(render_op, progress_callback)
            
            # Объединяем результаты
            for i, render_res in enumerate(render_result.results):
                if i < len(result.results):
                    if not render_res.success:
                        result.results[i].success = False
                        result.results[i].errors.extend(render_res.errors)
        
        return result
    
    def _process_update_versions(self, operation: BatchOperation,
                               progress_callback: Optional[Callable]) -> BatchOperationResult:
        """Обработать обновление версий"""
        result = BatchOperationResult(operation=operation)
        total = len(operation.source_nodes)
        
        for i, node in enumerate(operation.source_nodes):
            if progress_callback:
                progress_callback(i, total, f"Updating: {node.name()}")
            
            batch_result = BatchResult(source_node=node, success=False)
            
            try:
                # Получаем текущий путь
                current_path = self.bridge.get_knob_value(node, 'file', '')
                if not current_path:
                    batch_result.add_error("No file path found")
                    result.results.append(batch_result)
                    continue
                
                # Обновляем версию
                from ..utils.version import get_next_available_version
                new_path = get_next_available_version(current_path)
                
                if new_path != current_path:
                    self.bridge.set_knob_value(node, 'file', new_path)
                    batch_result.success = True
                    batch_result.output_path = new_path
                    
                    # Обновляем note если это A-Train нода
                    note = self.bridge.get_knob_value(node, 'note', '')
                    if 'A-Train' in note:
                        from ..utils.version import extract_version
                        version = extract_version(new_path)
                        new_note = f"A-Train\n{os.path.basename(new_path)}"
                        if version:
                            new_note += f"\n{version}"
                        self.bridge.set_knob_value(node, 'note', new_note)
                else:
                    batch_result.add_warning("No version update needed")
                    batch_result.success = True
                
            except Exception as e:
                batch_result.add_error(f"Error updating version: {e}")
            
            result.results.append(batch_result)
            
            if progress_callback:
                status = "Updated" if batch_result.success else "Failed"
                progress_callback(i + 1, total, f"{status}: {node.name()}")
        
        return result
    
    def _process_render_writes(self, operation: BatchOperation,
                             progress_callback: Optional[Callable]) -> BatchOperationResult:
        """Обработать рендер Write нод"""
        result = BatchOperationResult(operation=operation)
        total = len(operation.source_nodes)
        
        if not operation.frame_range:
            # Используем диапазон из проекта
            operation.frame_range = self.bridge.get_frame_range()
        
        first_frame, last_frame = operation.frame_range
        
        for i, node in enumerate(operation.source_nodes):
            if progress_callback:
                progress_callback(i, total, f"Rendering: {node.name()}")
            
            batch_result = BatchResult(source_node=node, success=False)
            batch_result.operation_time = time.time()
            
            try:
                # Выполняем рендер
                success = self.bridge.execute_node(node, first_frame, last_frame)
                
                if success:
                    batch_result.success = True
                    batch_result.output_path = self.bridge.get_knob_value(node, 'file', '')
                    batch_result.metadata['frames_rendered'] = last_frame - first_frame + 1
                else:
                    batch_result.add_error("Render failed")
                
            batch_result.operation_time = time.time() - batch_result.operation_time
            result.results.append(batch_result)
            
            if progress_callback:
                status = "Rendered" if batch_result.success else "Failed"
                progress_callback(i + 1, total, f"{status}: {node.name()}")
        
        return result
    
    def validate_nodes(self, nodes: List[Any], expected_class: str = None) -> Dict[str, List[Any]]:
        """Валидировать ноды перед операцией"""
        valid = []
        invalid = []
        
        for node in nodes:
            try:
                if expected_class and hasattr(node, 'Class'):
                    if node.Class() != expected_class:
                        invalid.append(node)
                        continue
                
                # Проверяем что нода существует
                if hasattr(node, 'name'):
                    node.name()  # Вызовет исключение если нода удалена
                    valid.append(node)
                else:
                    invalid.append(node)
                    
            except:
                invalid.append(node)
        
        return {'valid': valid, 'invalid': invalid}
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику операций"""
        total = self.stats['total_operations']
        
        return {
            'total_operations': total,
            'successful_operations': self.stats['successful_operations'],
            'failed_operations': self.stats['failed_operations'],
            'success_rate': (self.stats['successful_operations'] / total * 100) if total > 0 else 0.0,
            'total_time': self.stats['total_time'],
            'average_time': self.stats['total_time'] / total if total > 0 else 0.0
        }
    
    def reset_stats(self):
        """Сбросить статистику"""
        self.stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_time': 0.0
        }
