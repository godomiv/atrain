# atrain/utils/batch_ops.py
"""
Batch операции A-Train - ИСПРАВЛЕНО: имена файлов, Write ноды вниз, стандартные имена
"""

import os
import re
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass

try:
    import nuke
    NUKE_AVAILABLE = True
except ImportError:
    nuke = None
    NUKE_AVAILABLE = False

from ..core.version_manager import VersionManager
from ..core.event_bus import EventBus
from .quick_ops import QuickOperations

@dataclass
class BatchOperation:
    """Описание batch операции"""
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
    """Результат batch операции"""
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
    """ИСПРАВЛЕНО: Система batch операций с именами файлов и правильным позиционированием"""
    
    def __init__(self):
        self.quick_operations = QuickOperations()
        self.event_bus = EventBus.instance()
        
        # Статистика операций
        self.operation_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'last_operation_time': None
        }
        
        print("BatchOperations: Initialized with VersionManager integration")
    
    def get_selected_read_nodes(self) -> List[Any]:
        """Получить выбранные Read ноды"""
        if not NUKE_AVAILABLE:
            return []
        
        try:
            selected_nodes = nuke.selectedNodes('Read')
            return selected_nodes
        except Exception as e:
            print(f"BatchOperations: Error getting selected Read nodes: {e}")
            return []
    
    def get_all_read_nodes(self) -> List[Any]:
        """Получить все Read ноды в скрипте"""
        if not NUKE_AVAILABLE:
            return []
        
        try:
            all_reads = nuke.allNodes('Read')
            return all_reads
        except Exception as e:
            print(f"BatchOperations: Error getting all Read nodes: {e}")
            return []
    
    def get_selected_write_nodes(self) -> List[Any]:
        """Получить выбранные Write ноды"""
        if not NUKE_AVAILABLE:
            return []
        
        try:
            selected_nodes = nuke.selectedNodes('Write')
            return selected_nodes
        except Exception as e:
            print(f"BatchOperations: Error getting selected Write nodes: {e}")
            return []
    
    def get_filename_from_read(self, read_node) -> str:
        """
        ИСПРАВЛЕНО: получить ИМЕНА ФАЙЛОВ (не имена нод) из Read ноды
        
        Args:
            read_node: Read нода
            
        Returns:
            str: Очищенное имя файла для отображения в UI
        """
        try:
            # Получаем путь к файлу
            file_path = read_node['file'].value()
            if file_path:
                # Извлекаем имя файла без расширения и номеров кадров
                basename = os.path.splitext(os.path.basename(file_path))[0]
                
                # ИСПРАВЛЕНО: убираем номера кадров и версии, оставляем только имя файла
                clean_name = re.sub(r'[._]\d{3,}$', '', basename)  # Убираем кадры
                clean_name = re.sub(r'[._]$', '', clean_name)       # Убираем лишние точки/подчеркивания
                
                # Убираем версии используя VersionManager
                current_version = VersionManager.extract_version_from_path(clean_name)
                if current_version:
                    clean_name = clean_name.replace(current_version, '').rstrip('_')
                
                return clean_name if clean_name else os.path.splitext(os.path.basename(file_path))[0]
            else:
                # Если нет файла - используем имя ноды как fallback
                return read_node.name()
                
        except Exception as e:
            print(f"BatchOperations: Error getting filename from Read node: {e}")
            return read_node.name()
    
    def get_read_nodes_info(self) -> List[Dict[str, str]]:
        """
        ИСПРАВЛЕНО: получить информацию о выбранных Read нодах для UI (показываем имена файлов)
        
        Returns:
            List[Dict]: Список с информацией о Read нодах
        """
        read_nodes = self.get_selected_read_nodes()
        nodes_info = []
        
        for node in read_nodes:
            try:
                file_path = node['file'].value()
                # ИСПРАВЛЕНО: показываем имена файлов, а не имена нод
                clean_name = self.get_filename_from_read(node)
                
                info = {
                    'node_name': node.name(),
                    'file_name': clean_name,  # ИСПРАВЛЕНО: отдельно имя файла
                    'file_path': file_path,
                    'has_file': bool(file_path)
                }
                nodes_info.append(info)
            except Exception as e:
                print(f"BatchOperations: Error getting info for node {node.name()}: {e}")
                nodes_info.append({
                    'node_name': node.name(),
                    'file_name': node.name(),  # fallback к имени ноды
                    'file_path': '',
                    'has_file': False
                })
        
        return nodes_info
    
    def create_write_from_read(self, read_node, output_path, format_type="exr") -> Optional[Any]:
        """
        ИСПРАВЛЕНО: создать Write ноду с позиционированием ВНИЗ и стандартным именем
        
        Args:
            read_node: Read нода
            output_path: Путь вывода с возможным [read_name] placeholder
            format_type: Тип формата файла
            
        Returns:
            nuke.Node: Write нода или None
        """
        if not NUKE_AVAILABLE or not read_node:
            return None
        
        try:
            # Создаем Write ноду
            write_node = nuke.createNode('Write', inpanel=False)
            
            # Подключаем к Read ноде
            write_node.setInput(0, read_node)
            
            # Получаем чистое имя файла из Read ноды
            filename = self.get_filename_from_read(read_node)
            
            # Заменяем placeholder в пути
            final_path = output_path.replace('[read_name]', filename)
            
            # Автоинкремент версии используя VersionManager
            final_path = VersionManager.get_next_available_version(final_path)
            
            # Устанавливаем параметры Write ноды
            write_node['file'].setValue(final_path)
            write_node['file_type'].setValue(format_type)
            write_node['create_directories'].setValue(True)
            
            # ИСПРАВЛЕНО: позиционируем Write ноду ВНИЗ от Read (не вправо)
            write_node.setXpos(read_node.xpos())  # Та же X позиция
            write_node.setYpos(read_node.ypos() + 80)  # ВНИЗ на 80 пикселей
            
            # ИСПРАВЛЕНО: стандартное имя Write ноды (Write1, Write2, etc.)
            # Nuke автоматически присваивает уникальные имена, НЕ переопределяем
            
            # ИСПРАВЛЕНО: информацию записываем в knob 'note', указываем только пресет
            preset_info = f"A-Train Batch\nFile: {filename}\nPath: {os.path.basename(final_path)}"
            if hasattr(write_node, 'knob') and 'note' in write_node.knobs():
                write_node['note'].setValue(preset_info)
            else:
                # Fallback - используем label если note недоступен
                write_node['label'].setValue(preset_info)
            
            print(f"BatchOperations: Created Write '{write_node.name()}' below Read '{read_node.name()}'")
            return write_node
            
        except Exception as e:
            print(f"BatchOperations: Error creating Write from Read: {e}")
            return None
    
    def create_write_nodes_batch(self, operation: BatchOperation, 
                                progress_callback: Optional[Callable] = None) -> List[BatchResult]:
        """
        ИСПРАВЛЕНО: создать Write ноды для batch операции с прогрессом
        
        Args:
            operation: Описание операции
            progress_callback: Колбек для прогресса (current, total, message)
            
        Returns:
            List[BatchResult]: Результаты операций
        """
        results = []
        total_nodes = len(operation.source_nodes)
        
        if total_nodes == 0:
            return results
        
        try:
            # Обновляем статистику
            self.operation_stats['total_operations'] += 1
            
            # Генерируем базовый путь
            if operation.preset_name:
                base_output_path = self._get_path_from_preset(operation.preset_name)
            else:
                base_output_path = self._generate_default_batch_path()
            
            if not base_output_path:
                # Все операции неудачны
                for i, source_node in enumerate(operation.source_nodes):
                    result = BatchResult(
                        source_node=source_node,
                        success=False,
                        errors=["No output path available"]
                    )
                    results.append(result)
                    
                    if progress_callback:
                        progress_callback(i + 1, total_nodes, f"Failed: {source_node.name()}")
                
                return results
            
            # Обрабатываем каждую ноду
            for i, source_node in enumerate(operation.source_nodes):
                try:
                    if progress_callback:
                        node_name = self.get_filename_from_read(source_node)
                        progress_callback(i, total_nodes, f"Processing: {node_name}")
                    
                    # Создаем Write ноду
                    write_node = self.create_write_from_read(
                        source_node, 
                        base_output_path, 
                        operation.format_type
                    )
                    
                    if write_node:
                        output_path = write_node['file'].value()
                        
                        result = BatchResult(
                            source_node=source_node,
                            success=True,
                            created_node=write_node,
                            output_path=output_path
                        )
                        
                        self.operation_stats['successful_operations'] += 1
                    else:
                        result = BatchResult(
                            source_node=source_node,
                            success=False,
                            errors=["Failed to create Write node"]
                        )
                        self.operation_stats['failed_operations'] += 1
                    
                    results.append(result)
                    
                    if progress_callback:
                        status = "Success" if result.success else "Failed"
                        node_name = self.get_filename_from_read(source_node)
                        progress_callback(i + 1, total_nodes, f"{status}: {node_name}")
                
                except Exception as e:
                    result = BatchResult(
                        source_node=source_node,
                        success=False,
                        errors=[str(e)]
                    )
                    results.append(result)
                    self.operation_stats['failed_operations'] += 1
                    
                    if progress_callback:
                        node_name = self.get_filename_from_read(source_node)
                        progress_callback(i + 1, total_nodes, f"Error: {node_name}")
            
            # Публикуем событие завершения
            self.event_bus.publish('batch_write_completed', {
                'operation': operation,
                'results': results,
                'success_count': sum(1 for r in results if r.success),
                'total_count': len(results)
            })
            
            return results
            
        except Exception as e:
            print(f"BatchOperations: Error in batch operation: {e}")
            # Возвращаем результаты с ошибками для всех нод
            for source_node in operation.source_nodes:
                results.append(BatchResult(
                    source_node=source_node,
                    success=False,
                    errors=[f"Batch operation failed: {e}"]
                ))
            return results
    
    def render_write_nodes_batch(self, write_nodes: List[Any], frame_range: tuple,
                               progress_callback: Optional[Callable] = None) -> List[BatchResult]:
        """
        Batch рендер Write нод с прогрессом
        
        Args:
            write_nodes: Список Write нод
            frame_range: Диапазон кадров (first, last)
            progress_callback: Колбек прогресса
            
        Returns:
            List[BatchResult]: Результаты рендера
        """
        if not NUKE_AVAILABLE:
            return []
        
        results = []
        total_nodes = len(write_nodes)
        first_frame, last_frame = frame_range
        
        try:
            for i, write_node in enumerate(write_nodes):
                try:
                    if progress_callback:
                        progress_callback(i, total_nodes, f"Rendering: {write_node.name()}")
                    
                    # Выполняем рендер
                    nuke.execute(write_node, first_frame, last_frame)
                    
                    result = BatchResult(
                        source_node=write_node,
                        success=True,
                        output_path=write_node['file'].value()
                    )
                    
                    if progress_callback:
                        progress_callback(i + 1, total_nodes, f"Rendered: {write_node.name()}")
                
                except Exception as e:
                    result = BatchResult(
                        source_node=write_node,
                        success=False,
                        errors=[f"Render failed: {e}"]
                    )
                    
                    if progress_callback:
                        progress_callback(i + 1, total_nodes, f"Failed: {write_node.name()}")
                
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"BatchOperations: Error in batch render: {e}")
            return results
    
    def transcode_selected_reads(self, base_output_path: str, format_type: str = "exr") -> List[Any]:
        """
        ИСПРАВЛЕНО: транскодировать выбранные Read ноды (оригинальная функция из файла)
        
        Args:
            base_output_path: Базовый путь вывода с [read_name] placeholder
            format_type: Тип формата
            
        Returns:
            List[nuke.Node]: Созданные Write ноды
        """
        read_nodes = self.get_selected_read_nodes()
        if not read_nodes:
            print("BatchOperations: No Read nodes selected for transcoding")
            return []
        
        created_writes = []
        
        print(f"BatchOperations: Starting transcode of {len(read_nodes)} Read nodes")
        
        for read_node in read_nodes:
            try:
                write_node = self.create_write_from_read(
                    read_node, base_output_path, format_type
                )
                if write_node:
                    created_writes.append(write_node)
                    
            except Exception as e:
                node_name = self.get_filename_from_read(read_node)
                print(f"BatchOperations: Error processing '{node_name}': {e}")
        
        print(f"BatchOperations: Created {len(created_writes)} Write nodes")
        return created_writes
    
    def batch_create_writes_with_versions(self, read_nodes: List[Any], 
                                        base_path: str, format_type: str = "exr") -> List[Any]:
        """
        НОВОЕ: создать Write ноды с автоматическими версиями
        
        Args:
            read_nodes: Список Read нод
            base_path: Базовый путь
            format_type: Тип формата
            
        Returns:
            List[nuke.Node]: Созданные Write ноды
        """
        created_writes = []
        
        for read_node in read_nodes:
            try:
                # Генерируем уникальный путь для каждой ноды
                filename = self.get_filename_from_read(read_node)
                node_path = base_path.replace('[read_name]', filename)
                
                # Получаем следующую доступную версию
                versioned_path = VersionManager.get_next_available_version(node_path)
                
                # Создаем Write ноду
                write_node = self.create_write_from_read(read_node, versioned_path, format_type)
                if write_node:
                    created_writes.append(write_node)
                    
            except Exception as e:
                print(f"BatchOperations: Error creating versioned write for {read_node.name()}: {e}")
        
        return created_writes
    
    def _get_path_from_preset(self, preset_name: str) -> Optional[str]:
        """Получить путь из пресета"""
        try:
            from ..core.preset_manager import PresetManager
            preset_manager = PresetManager()
            
            all_presets = preset_manager.get_all_presets()
            if preset_name not in all_presets:
                print(f"BatchOperations: Preset '{preset_name}' not found")
                return None
            
            preset_data = all_presets[preset_name]
            
            # Строим путь как в QuickOperations
            from ..core.path_builder import PathBuilder
            path_builder = PathBuilder()
            
            # Добавляем теги
            tag_names = preset_data.get('tags', [])
            all_tags = preset_manager.get_all_tags()
            
            for tag_name in tag_names:
                for tag_data in all_tags:
                    if tag_data.get('name') == tag_name:
                        path_builder.add_tag(tag_data)
                        break
            
            # ИСПРАВЛЕНО: добавляем format тег с правильным padding
            format_type = preset_data.get('format', 'exr')
            format_tag = {
                'name': 'format',
                'type': 'format',
                'format': format_type,
                'version': 'v01',
                'padding': '%04d'  # ИСПРАВЛЕНО: % добавлен
            }
            path_builder.add_tag(format_tag)
            
            return path_builder.build_path(live_preview=True)
            
        except Exception as e:
            print(f"BatchOperations: Error getting path from preset '{preset_name}': {e}")
            return None
    
    def _generate_default_batch_path(self) -> str:
        """ИСПРАВЛЕНО: генерация дефолтного пути для batch операций"""
        try:
            import getpass
            user = getpass.getuser()
            
            if NUKE_AVAILABLE and nuke.root().name():
                script_path = nuke.root().name()
                script_dir = os.path.dirname(script_path)
                script_name = os.path.splitext(os.path.basename(script_path))[0]
                
                # Убираем версию из имени скрипта используя VersionManager
                current_version = VersionManager.extract_version_from_path(script_name)
                if current_version:
                    base_name = script_name.replace(current_version, '').rstrip('_')
                else:
                    base_name = script_name
                
                return os.path.join(script_dir, f"{base_name}_[read_name]_v01.%04d.exr").replace('\\', '/')
            else:
                return f"/tmp/{user}_[read_name]_v01.%04d.exr"
                
        except Exception as e:
            print(f"BatchOperations: Error generating default path: {e}")
            return "/tmp/batch_[read_name]_v01.%04d.exr"
    
    def validate_read_nodes(self, read_nodes: List[Any]) -> Dict[str, List[Any]]:
        """
        НОВОЕ: валидация Read нод для batch операций
        
        Args:
            read_nodes: Список Read нод
            
        Returns:
            Dict: Валидные и невалидные ноды
        """
        valid_nodes = []
        invalid_nodes = []
        
        for node in read_nodes:
            try:
                # Проверяем что нода существует и это Read
                if node and hasattr(node, 'Class') and node.Class() == 'Read':
                    # Проверяем что есть файл
                    file_path = node['file'].value()
                    if file_path and file_path.strip():
                        valid_nodes.append(node)
                    else:
                        invalid_nodes.append(node)
                else:
                    invalid_nodes.append(node)
            except:
                invalid_nodes.append(node)
        
        return {
            'valid': valid_nodes,
            'invalid': invalid_nodes
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику операций"""
        total = self.operation_stats['total_operations']
        successful = self.operation_stats['successful_operations']
        
        return {
            'total_operations': total,
            'successful_operations': successful,
            'failed_operations': self.operation_stats['failed_operations'],
            'success_rate': (successful / total * 100) if total > 0 else 0.0,
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
    
    def export_batch_results(self, results: List[BatchResult], export_path: str) -> bool:
        """
        НОВОЕ: экспорт результатов batch операции
        
        Args:
            results: Результаты операций
            export_path: Путь для экспорта
            
        Returns:
            bool: True если успешно
        """
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
                    'source_node': result.source_node.name() if result.source_node else 'Unknown',
                    'success': result.success,
                    'created_node': result.created_node.name() if result.created_node else None,
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


# Глобальные функции для совместимости с оригинальным API
def create_write_nodes_for_selected(preset_name: str = "Default") -> List[BatchResult]:
    """
    ИСПРАВЛЕНО: создать Write ноды для выбранных Read нод
    
    Args:
        preset_name: Имя пресета
        
    Returns:
        List[BatchResult]: Результаты операций
    """
    batch_ops = BatchOperations()
    read_nodes = batch_ops.get_selected_read_nodes()
    
    if not read_nodes:
        return []
    
    operation = BatchOperation(
        operation_type='create_write',
        source_nodes=read_nodes,
        preset_name=preset_name,
        auto_increment=True,
        connect_nodes=True,
        create_directories=True
    )
    
    return batch_ops.create_write_nodes_batch(operation)

def transcode_selected_reads(base_output_path: str, format_type: str = "exr") -> List[Any]:
    """
    ИСПРАВЛЕНО: быстрая функция транскодирования (совместимость с оригинальным API)
    
    Args:
        base_output_path: Базовый путь
        format_type: Тип формата
        
    Returns:
        List[nuke.Node]: Write ноды
    """
    batch_ops = BatchOperations()
    return batch_ops.transcode_selected_reads(base_output_path, format_type)

def get_batch_stats() -> Dict[str, Any]:
    """Получить статистику batch операций"""
    batch_ops = BatchOperations()
    return batch_ops.get_stats()

def get_selected_read_nodes() -> List[Any]:
    """Получить выбранные Read ноды (совместимость)"""
    batch_ops = BatchOperations()
    return batch_ops.get_selected_read_nodes()

def get_filename_from_read(read_node) -> str:
    """Получить имя файла из Read ноды (совместимость)"""
    batch_ops = BatchOperations()
    return batch_ops.get_filename_from_read(read_node)

def batch_create_writes_with_auto_versions(read_nodes: List[Any], base_path: str) -> List[Any]:
    """
    НОВОЕ: создать Write ноды с автоматическими версиями
    
    Args:
        read_nodes: Read ноды
        base_path: Базовый путь
        
    Returns:
        List[nuke.Node]: Write ноды
    """
    batch_ops = BatchOperations()
    return batch_ops.batch_create_writes_with_versions(read_nodes, base_path)
