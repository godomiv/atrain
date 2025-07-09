# atrain/core/integration.py
"""
Интеграционный модуль A-Train
Связывает все компоненты новой архитектуры
"""

import os
from typing import Dict, List, Any, Optional, Tuple

from .storage import StorageManager
from .path_builder import PathBuilder
from .models import PathContext, PresetData, TagData, TagType
from .batch import BatchOperations, get_batch_operations
from .nuke import nuke_bridge, NodeUtils
from .utils import event_bus, get_next_available_version


class ATrainCore:
    """
    Центральный класс интеграции всех компонентов A-Train
    """
    
    def __init__(self):
        self.storage = StorageManager()
        self.bridge = nuke_bridge()
        self.batch_ops = get_batch_operations()
        self.event_bus = event_bus()
        self.node_utils = NodeUtils()
        
        print("ATrainCore: Initialized")
    
    # =====================
    # Работа с путями
    # =====================
    
    def build_path_from_preset(self, preset_name: str, 
                               context: Optional[PathContext] = None) -> Tuple[bool, str, List[str]]:
        """
        Построить путь из пресета
        
        Returns:
            (success, path, issues)
        """
        try:
            # Получаем пресет
            preset = self.storage.get_preset(preset_name)
            if not preset:
                return False, "", [f"Preset '{preset_name}' not found"]
            
            # Создаем PathBuilder
            builder = PathBuilder()
            
            # Устанавливаем контекст
            if context:
                builder.set_context(context)
            
            # Добавляем теги из пресета
            all_tags = self.storage.get_all_tags()
            tags_dict = {tag.name: tag for tag in all_tags}
            
            for tag_name in preset.tags:
                if tag_name in tags_dict:
                    builder.add_tag(tags_dict[tag_name])
                else:
                    print(f"ATrainCore: Warning - tag '{tag_name}' not found")
            
            # Добавляем format тег
            format_tag = TagData(
                name='format',
                type=TagType.FORMAT,
                format=preset.format,
                padding='%04d'
            )
            builder.add_tag(format_tag)
            
            # Строим путь
            path = builder.build_path()
            
            # Валидируем
            is_valid, issues = builder.validate_path(path)
            
            return is_valid, path, issues
            
        except Exception as e:
            return False, "", [f"Error building path: {e}"]
    
    def create_write_node(self, preset_name: Optional[str] = None,
                         auto_increment: bool = True,
                         output_path: Optional[str] = None,
                         format_type: str = "exr") -> Optional[Any]:
        """Создать Write ноду с настройками из пресета"""
        if not self.bridge.available:
            print("ATrainCore: Nuke not available")
            return None
        
        try:
            # Определяем путь
            if output_path:
                path = output_path
            else:
                # Создаем контекст
                context = PathContext()
                
                # Генерируем путь
                if preset_name:
                    success, path, issues = self.build_path_from_preset(preset_name, context)
                    if not success:
                        print(f"ATrainCore: Failed to build path: {issues}")
                        # Fallback к дефолтному пути
                        path = self._get_default_path(format_type)
                else:
                    # Дефолтный путь
                    path = self._get_default_path(format_type)
            
            # Автоинкремент
            if auto_increment:
                path = get_next_available_version(path)
            
            # Создаем Write ноду
            write_node = self.node_utils.create_write_node(path)
            
            if write_node:
                # Добавляем метку
                note = "A-Train"
                if preset_name:
                    note += f" - {preset_name}"
                note += f"\n{os.path.basename(path)}"
                
                from .utils.version import extract_version
                version = extract_version(path)
                if version:
                    note += f"\n{version}"
                
                self.bridge.set_knob_value(write_node, 'note', note)
                
                # Подключаем к выбранной ноде
                selected = self.bridge.get_selected_nodes()
                if selected:
                    write_node.setInput(0, selected[0])
                    self.node_utils.position_node_relative(write_node, selected[0])
                
                print(f"ATrainCore: Created Write node -> {path}")
            
            return write_node
            
        except Exception as e:
            print(f"ATrainCore: Error creating Write node: {e}")
            return None
    
    def _get_default_path(self, format_type: str = "exr") -> str:
        """Получить дефолтный путь"""
        try:
            project_path = self.bridge.find_project_root()
            script_name = self.bridge.get_script_basename()
            
            if script_name and script_name != 'untitled':
                # Убираем версию из имени скрипта
                from .utils.version import extract_version
                version = extract_version(script_name)
                if version:
                    base_name = script_name.replace(version, '').rstrip('_')
                else:
                    base_name = script_name
                
                return f"{project_path}/{base_name}_comp_v01.%04d.{format_type}"
            else:
                user = self.bridge.get_user_name()
                return f"{project_path}/{user}_comp_v01.%04d.{format_type}"
                
        except Exception as e:
            print(f"ATrainCore: Error getting default path: {e}")
            return f"/tmp/atrain_output_v01.%04d.{format_type}"
    
    # =====================
    # Batch операции
    # =====================
    
    def batch_create_writes(self, read_nodes: Optional[List[Any]] = None,
                           preset_name: Optional[str] = None,
                           format_type: str = "exr") -> List[Any]:
        """Создать Write ноды для Read нод"""
        result = self.batch_ops.create_writes_for_reads(
            read_nodes=read_nodes,
            preset_name=preset_name,
            format_type=format_type,
            auto_increment=True
        )
        
        # Возвращаем список созданных нод
        created_nodes = []
        for batch_result in result.results:
            if batch_result.success and batch_result.created_node:
                created_nodes.append(batch_result.created_node)
        
        return created_nodes
    
    def batch_transcode(self, read_nodes: Optional[List[Any]] = None,
                       output_path: Optional[str] = None,
                       format_type: str = "mov",
                       frame_range: Optional[Tuple[int, int]] = None) -> int:
        """Транскодировать Read ноды"""
        result = self.batch_ops.transcode_reads(
            read_nodes=read_nodes,
            output_path=output_path,
            format_type=format_type,
            frame_range=frame_range
        )
        
        return result.success_count
    
    # =====================
    # Информация о системе
    # =====================
    
    def get_system_info(self) -> Dict[str, Any]:
        """Получить информацию о системе"""
        return {
            'nuke_available': self.bridge.available,
            'project_root': self.bridge.find_project_root(),
            'project_info': self.bridge.get_project_info(),
            'storage_info': self.storage.get_project_info(),
            'presets_count': len(self.storage.get_all_presets()),
            'tags_count': len(self.storage.get_all_tags()),
            'batch_stats': self.batch_ops.get_stats()
        }
    
    def validate_system(self) -> Tuple[bool, List[str]]:
        """Валидация системы"""
        issues = []
        
        # Проверяем Nuke
        if not self.bridge.available:
            issues.append("Nuke API not available")
        
        # Проверяем хранилище
        storage_validation = self.storage.validate_all()
        if not storage_validation['valid']:
            issues.extend(storage_validation['file_issues'])
        
        # Проверяем пресеты
        all_presets = self.storage.get_all_presets()
        if not all_presets:
            issues.append("No presets found")
        
        # Проверяем теги
        all_tags = self.storage.get_all_tags()
        if not all_tags:
            issues.append("No tags found")
        
        return len(issues) == 0, issues


# Глобальный экземпляр
_atrain_core = None

def get_atrain_core() -> ATrainCore:
    """Получить глобальный экземпляр ATrainCore"""
    global _atrain_core
    if _atrain_core is None:
        _atrain_core = ATrainCore()
    return _atrain_core


# Удобные функции для быстрого доступа
def quick_write(preset_name: Optional[str] = None,
               auto_increment: bool = True,
               output_path: Optional[str] = None,
               format_type: str = "exr") -> Optional[Any]:
    """Быстрое создание Write ноды"""
    core = get_atrain_core()
    return core.create_write_node(preset_name, auto_increment, output_path, format_type)


def batch_writes(preset_name: Optional[str] = None,
                format_type: str = "exr") -> List[Any]:
    """Создать Write ноды для выбранных Read нод"""
    core = get_atrain_core()
    return core.batch_create_writes(None, preset_name, format_type)


def get_presets() -> Dict[str, Any]:
    """Получить все пресеты"""
    core = get_atrain_core()
    presets = {}
    for name, preset in core.storage.get_all_presets().items():
        presets[name] = preset.to_dict()
    return presets


def get_tags() -> List[Dict[str, Any]]:
    """Получить все теги"""
    core = get_atrain_core()
    return [tag.to_dict() for tag in core.storage.get_all_tags()]


def validate_atrain() -> Tuple[bool, List[str]]:
    """Валидировать систему A-Train"""
    core = get_atrain_core()
    return core.validate_system()
