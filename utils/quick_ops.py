# atrain/utils/quick_ops.py
"""
Быстрые операции A-Train - ИСПРАВЛЕНО: стандартные имена Write, информация в note
"""

import os
import getpass
import re
from typing import Optional, Dict, Any

try:
    import nuke
    NUKE_AVAILABLE = True
except ImportError:
    nuke = None
    NUKE_AVAILABLE = False

from ..core.version_manager import VersionManager
from ..core.preset_manager import PresetManager
from ..core.event_bus import EventBus

class QuickOperations:
    """
    ИСПРАВЛЕНО: Быстрые операции для создания Write нод с стандартными именами
    """
    
    def __init__(self):
        self.preset_manager = PresetManager()
        self.event_bus = EventBus.instance()
        
        # Маппинг расширений к типам файлов Nuke
        self.file_type_map = {
            '.exr': 'exr',
            '.jpeg': 'jpeg', 
            '.jpg': 'jpeg',
            '.png': 'png',
            '.dpx': 'dpx',
            '.tif': 'tiff',
            '.tiff': 'tiff',
            '.mov': 'mov',
            '.mp4': 'mov',
            '.avi': 'mov',
            '.mkv': 'mov',
            '.webm': 'mov'
        }
        
        print("QuickOperations: Initialized with enhanced VersionManager integration")
    
    def create_quick_write(self, preset_name=None, auto_increment=True, 
                          output_path=None, format_type="exr"):
        """
        ИСПРАВЛЕНО: быстрое создание Write ноды со стандартным именем и информацией в note
        
        Args:
            preset_name: Имя пресета (опционально)
            auto_increment: Автоинкремент версии
            output_path: Готовый путь (опционально)
            format_type: Тип формата файла
            
        Returns:
            nuke.Node: Созданная Write нода или None
        """
        if not NUKE_AVAILABLE:
            print("QuickOperations: Nuke not available")
            return None
        
        try:
            # Определяем путь для записи
            if output_path:
                final_path = output_path
            else:
                final_path = self._generate_path_from_preset(preset_name)
            
            if not final_path:
                print("QuickOperations: No path available")
                return None
            
            # ИСПРАВЛЕНО: автоинкремент версии используя VersionManager
            if auto_increment:
                final_path = VersionManager.increment_version_in_path(final_path)
                # Дополнительно проверяем доступность
                final_path = VersionManager.get_next_available_version(final_path)
            
            # Создаем Write ноду
            write_node = nuke.createNode('Write', inpanel=False)
            
            # Устанавливаем путь файла
            write_node['file'].setValue(final_path)
            
            # Включаем создание директорий
            try:
                write_node['create_directories'].setValue(True)
            except:
                pass
            
            # Устанавливаем тип файла
            file_type = self._determine_file_type(final_path, format_type)
            if file_type:
                try:
                    write_node['file_type'].setValue(file_type)
                except:
                    pass
            
            # ИСПРАВЛЕНО: НЕ устанавливаем кастомное имя, используем стандартное Nuke имя
            # write_node['name'].setValue(node_name)  # УБРАЛИ
            
            # ИСПРАВЛЕНО: информацию записываем в knob 'note'
            base_name = os.path.basename(final_path)
            version = VersionManager.extract_version_from_path(final_path)
            
            if preset_name:
                note_text = f"A-Train - {preset_name}\n{base_name}"
            else:
                note_text = f"A-Train\n{base_name}"
            
            if version:
                note_text += f"\n{version}"
            
            # Записываем в note knob
            if 'note' in write_node.knobs():
                write_node['note'].setValue(note_text)
            else:
                # Fallback для label
                write_node['label'].setValue(note_text)
            
            # Подключаем к выбранной ноде если есть
            connected_node = self._connect_to_selected_node(write_node)
            
            # Публикуем событие
            self.event_bus.publish('write_node_created', {
                'node': write_node,
                'path': final_path,
                'preset_name': preset_name,
                'auto_increment': auto_increment,
                'connected_to': connected_node.name() if connected_node else None,
                'version': version
            })
            
            print(f"QuickOperations: Created Write node '{write_node.name()}' -> {final_path}")
            return write_node
            
        except Exception as e:
            print(f"QuickOperations: Error creating Write node: {e}")
            return None
    
    def _generate_path_from_preset(self, preset_name):
        """ИСПРАВЛЕНО: генерация пути из пресета с правильным padding"""
        if not preset_name:
            return self._generate_default_path()
        
        try:
            # Загружаем пресет
            all_presets = self.preset_manager.get_all_presets()
            if preset_name not in all_presets:
                print(f"QuickOperations: Preset '{preset_name}' not found")
                return self._generate_default_path()
            
            preset_data = all_presets[preset_name]
            
            # Строим путь из пресета
            from ..core.path_builder import PathBuilder
            path_builder = PathBuilder()
            
            # Добавляем теги из пресета
            tag_names = preset_data.get('tags', [])
            all_tags = self.preset_manager.get_all_tags()
            
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
            
            # Строим путь
            built_path = path_builder.build_path(live_preview=True)
            return built_path if built_path else self._generate_default_path()
            
        except Exception as e:
            print(f"QuickOperations: Error generating path from preset: {e}")
            return self._generate_default_path()
    
    def _generate_default_path(self):
        """ИСПРАВЛЕНО: генерация дефолтного пути с правильным padding"""
        try:
            # Базовая информация
            user = getpass.getuser()
            
            if NUKE_AVAILABLE and nuke.root().name():
                # Есть скрипт - используем его путь
                script_path = nuke.root().name()
                script_dir = os.path.dirname(script_path)
                script_name = os.path.splitext(os.path.basename(script_path))[0]
                
                # Убираем версию из имени скрипта используя VersionManager
                current_version = VersionManager.extract_version_from_path(script_name)
                if current_version:
                    base_name = script_name.replace(current_version, '').rstrip('_')
                else:
                    base_name = script_name
                
                # ИСПРАВЛЕНО: правильный padding в дефолтном пути
                base_path = os.path.join(script_dir, f"{base_name}_comp_v01.%04d.exr")
            else:
                # Нет скрипта - используем temp путь
                base_path = f"/tmp/{user}_comp_v01.%04d.exr"
            
            return base_path.replace('\\', '/')
            
        except Exception as e:
            print(f"QuickOperations: Error generating default path: {e}")
            return "/tmp/atrain_output_v01.%04d.exr"
    
    def _determine_file_type(self, path, format_type):
        """ИСПРАВЛЕНО: определение типа файла для Nuke"""
        try:
            # Сначала по расширению в пути
            ext = os.path.splitext(path)[1].lower()
            
            # Убираем padding из расширения для видео файлов
            if '.%' in ext or '.#' in ext:
                # Это последовательность, берем реальное расширение
                clean_path = re.sub(r'\.%\d+d\.', '.', path)
                clean_path = re.sub(r'\.#+\.', '.', clean_path)
                ext = os.path.splitext(clean_path)[1].lower()
            
            if ext in self.file_type_map:
                return self.file_type_map[ext]
            
            # Потом по переданному типу
            if format_type.lower() in self.file_type_map.values():
                return format_type.lower()
            
            # По расширению format_type
            format_ext = f".{format_type.lower()}"
            if format_ext in self.file_type_map:
                return self.file_type_map[format_ext]
            
            # По умолчанию exr
            return 'exr'
            
        except Exception as e:
            print(f"QuickOperations: Error determining file type: {e}")
            return 'exr'
    
    def _connect_to_selected_node(self, write_node):
        """ИСПРАВЛЕНО: подключение к выбранной ноде с позиционированием"""
        if not NUKE_AVAILABLE:
            return None
        
        try:
            selected_nodes = nuke.selectedNodes()
            if selected_nodes:
                # Подключаем к последней выбранной ноде
                source_node = selected_nodes[-1]
                write_node.setInput(0, source_node)
                
                # ИСПРАВЛЕНО: умное позиционирование Write ноды
                write_node.setXpos(source_node.xpos() + 120)
                write_node.setYpos(source_node.ypos())
                
                # Проверяем нет ли уже нод справа
                existing_nodes = [n for n in nuke.allNodes() if n != write_node and n != source_node]
                for node in existing_nodes:
                    if (abs(node.xpos() - write_node.xpos()) < 100 and 
                        abs(node.ypos() - write_node.ypos()) < 50):
                        # Смещаем вниз если место занято
                        write_node.setYpos(write_node.ypos() + 100)
                        break
                
                return source_node
                
        except Exception as e:
            print(f"QuickOperations: Error connecting to selected node: {e}")
        
        return None
    
    def get_selected_read_nodes(self):
        """Получить выбранные Read ноды"""
        if not NUKE_AVAILABLE:
            return []
        
        try:
            selected_nodes = nuke.selectedNodes('Read')
            return selected_nodes
        except:
            return []
    
    def get_all_read_nodes(self):
        """Получить все Read ноды в скрипте"""
        if not NUKE_AVAILABLE:
            return []
        
        try:
            all_reads = nuke.allNodes('Read')
            return all_reads
        except:
            return []
    
    def create_write_for_read(self, read_node, output_path=None, format_type="exr"):
        """
        ИСПРАВЛЕНО: создать Write ноду для конкретной Read ноды со стандартным именем
        
        Args:
            read_node: Read нода
            output_path: Путь вывода (опционально)
            format_type: Тип формата
            
        Returns:
            nuke.Node: Созданная Write нода или None
        """
        if not NUKE_AVAILABLE or not read_node:
            return None
        
        try:
            # Генерируем путь если не передан
            if not output_path:
                read_name = self._get_clean_read_name(read_node)
                output_path = f"/tmp/{read_name}_v01.%04d.{format_type}"
            
            # ИСПРАВЛЕНО: автоинкремент версии используя VersionManager
            final_path = VersionManager.get_next_available_version(output_path)
            
            # Создаем Write ноду
            write_node = nuke.createNode('Write', inpanel=False)
            
            # Подключаем к Read ноде
            write_node.setInput(0, read_node)
            
            # Позиционируем
            write_node.setXpos(read_node.xpos() + 120)
            write_node.setYpos(read_node.ypos())
            
            # Настраиваем параметры
            write_node['file'].setValue(final_path)
            write_node['create_directories'].setValue(True)
            
            file_type = self._determine_file_type(final_path, format_type)
            write_node['file_type'].setValue(file_type)
            
            # ИСПРАВЛЕНО: НЕ устанавливаем кастомное имя, используем стандартное Nuke имя
            # ИСПРАВЛЕНО: информацию записываем в knob 'note'
            clean_name = self._get_clean_read_name(read_node)
            version = VersionManager.extract_version_from_path(final_path)
            
            note_text = f"A-Train\n{clean_name}"
            if version:
                note_text += f"\n{version}"
            
            # Записываем в note knob
            if 'note' in write_node.knobs():
                write_node['note'].setValue(note_text)
            else:
                # Fallback для label
                write_node['label'].setValue(note_text)
            
            print(f"QuickOperations: Created Write for Read '{read_node.name()}' -> {final_path}")
            return write_node
            
        except Exception as e:
            print(f"QuickOperations: Error creating Write for Read: {e}")
            return None
    
    def _get_clean_read_name(self, read_node):
        """ИСПРАВЛЕНО: получить очищенное имя Read ноды"""
        try:
            # Сначала пробуем получить имя файла
            file_path = read_node['file'].value()
            if file_path:
                basename = os.path.splitext(os.path.basename(file_path))[0]
                
                # Убираем номера кадров и версии используя VersionManager
                clean_name = re.sub(r'\d{3,}$', '', basename)
                clean_name = re.sub(r'[._]$', '', clean_name)
                
                current_version = VersionManager.extract_version_from_path(clean_name)
                if current_version:
                    clean_name = clean_name.replace(current_version, '').rstrip('_')
                
                # Убираем паттерны кадров
                clean_name = re.sub(r'[._]\d+$', '', clean_name)
                clean_name = re.sub(r'[._]$', '', clean_name)
                
                return clean_name if clean_name else read_node.name()
            else:
                return read_node.name()
                
        except Exception as e:
            print(f"QuickOperations: Error getting clean name: {e}")
            return read_node.name()
    
    def create_write_with_smart_versioning(self, preset_name=None, format_type="exr"):
        """
        НОВОЕ: создать Write ноду с умным управлением версиями
        
        Args:
            preset_name: Имя пресета
            format_type: Тип формата
            
        Returns:
            nuke.Node: Write нода или None
        """
        try:
            # Генерируем базовый путь
            base_path = self._generate_path_from_preset(preset_name)
            if not base_path:
                return None
            
            # Находим следующую доступную версию
            versioned_path = VersionManager.get_next_available_version(base_path)
            
            # Создаем Write ноду
            return self.create_quick_write(
                preset_name=None,
                auto_increment=False,
                output_path=versioned_path,
                format_type=format_type
            )
            
        except Exception as e:
            print(f"QuickOperations: Error creating smart versioned write: {e}")
            return None
    
    def create_writes_for_selected_reads(self, format_type="exr", use_preset=None):
        """
        ИСПРАВЛЕНО: создать Write ноды для всех выбранных Read нод
        
        Args:
            format_type: Тип формата
            use_preset: Имя пресета для генерации пути
            
        Returns:
            List[nuke.Node]: Список созданных Write нод
        """
        read_nodes = self.get_selected_read_nodes()
        if not read_nodes:
            print("QuickOperations: No Read nodes selected")
            return []
        
        created_writes = []
        
        for read_node in read_nodes:
            try:
                # Генерируем путь для ноды
                if use_preset:
                    base_path = self._generate_path_from_preset(use_preset)
                    if base_path:
                        # Заменяем [read_name] на имя ноды
                        clean_name = self._get_clean_read_name(read_node)
                        output_path = base_path.replace('[read_name]', clean_name)
                    else:
                        output_path = None
                else:
                    output_path = None
                
                write_node = self.create_write_for_read(
                    read_node, 
                    output_path=output_path,
                    format_type=format_type
                )
                
                if write_node:
                    created_writes.append(write_node)
                    
            except Exception as e:
                print(f"QuickOperations: Error processing Read '{read_node.name()}': {e}")
        
        print(f"QuickOperations: Created {len(created_writes)} Write nodes for {len(read_nodes)} Read nodes")
        return created_writes
    
    def validate_output_path(self, path):
        """
        НОВОЕ: валидация выходного пути
        
        Args:
            path: Путь для проверки
            
        Returns:
            tuple: (is_valid, issues)
        """
        issues = []
        
        if not path:
            issues.append("Empty path")
            return False, issues
        
        try:
            # Проверка недопустимых символов
            invalid_chars = ['<', '>', '|', '"', '?', '*']
            if any(char in path for char in invalid_chars):
                issues.append("Path contains invalid characters")
            
            # Проверка длины пути
            if len(path) > 260:
                issues.append("Path too long (>260 characters)")
            
            # Проверка расширения файла
            known_extensions = {'.exr', '.dpx', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.mov', '.mp4'}
            if not any(path.lower().endswith(ext) for ext in known_extensions):
                issues.append("Unknown file extension")
            
            # Проверка директории
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                except:
                    issues.append("Cannot create output directory")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Validation error: {e}")
            return False, issues
    
    def get_write_node_info(self, write_node):
        """
        НОВОЕ: получить информацию о Write ноде
        
        Args:
            write_node: Write нода
            
        Returns:
            Dict: Информация о ноде
        """
        try:
            if not write_node or not hasattr(write_node, 'Class'):
                return {}
            
            file_path = write_node['file'].value() if 'file' in write_node.knobs() else ''
            
            info = {
                'name': write_node.name(),
                'class': write_node.Class(),
                'file_path': file_path,
                'file_type': write_node['file_type'].value() if 'file_type' in write_node.knobs() else '',
                'version': VersionManager.extract_version_from_path(file_path),
                'directory': os.path.dirname(file_path) if file_path else '',
                'filename': os.path.basename(file_path) if file_path else '',
                'exists': os.path.exists(file_path) if file_path else False,
                'connected_to': write_node.input(0).name() if write_node.input(0) else None,
                'create_directories': write_node['create_directories'].value() if 'create_directories' in write_node.knobs() else False
            }
            
            return info
            
        except Exception as e:
            print(f"QuickOperations: Error getting write node info: {e}")
            return {}
    
    def update_write_node_version(self, write_node, increment=True):
        """
        НОВОЕ: обновить версию Write ноды
        
        Args:
            write_node: Write нода
            increment: True для инкремента, False для следующей доступной
            
        Returns:
            bool: True если успешно обновлено
        """
        try:
            if not write_node or 'file' not in write_node.knobs():
                return False
            
            current_path = write_node['file'].value()
            if not current_path:
                return False
            
            if increment:
                new_path = VersionManager.increment_version_in_path(current_path)
            else:
                new_path = VersionManager.get_next_available_version(current_path)
            
            if new_path != current_path:
                write_node['file'].setValue(new_path)
                
                # Обновляем note если это A-Train нода
                if 'note' in write_node.knobs():
                    note_text = write_node['note'].value()
                    if 'A-Train' in note_text:
                        version = VersionManager.extract_version_from_path(new_path)
                        base_name = os.path.basename(new_path)
                        new_note = f"A-Train\n{base_name}"
                        if version:
                            new_note += f"\n{version}"
                        write_node['note'].setValue(new_note)
                
                return True
            
            return False
            
        except Exception as e:
            print(f"QuickOperations: Error updating write node version: {e}")
            return False


# Глобальные функции для быстрого доступа
def create_quick_write(preset_name=None, auto_increment=True, output_path=None, format_type="exr"):
    """
    ИСПРАВЛЕНО: быстрое создание Write ноды
    
    Args:
        preset_name: Имя пресета
        auto_increment: Автоинкремент версии
        output_path: Готовый путь
        format_type: Тип формата
        
    Returns:
        nuke.Node: Write нода или None
    """
    quick_ops = QuickOperations()
    return quick_ops.create_quick_write(preset_name, auto_increment, output_path, format_type)

def create_writes_for_selected_reads(format_type="exr", use_preset=None):
    """
    ИСПРАВЛЕНО: создать Write ноды для всех выбранных Read нод
    
    Args:
        format_type: Тип формата
        use_preset: Имя пресета
        
    Returns:
        List[nuke.Node]: Список созданных Write нод
    """
    quick_ops = QuickOperations()
    return quick_ops.create_writes_for_selected_reads(format_type, use_preset)

def create_write_with_smart_versioning(preset_name=None, format_type="exr"):
    """
    НОВОЕ: создать Write ноду с умным управлением версиями
    
    Args:
        preset_name: Имя пресета
        format_type: Тип формата
        
    Returns:
        nuke.Node: Write нода или None
    """
    quick_ops = QuickOperations()
    return quick_ops.create_write_with_smart_versioning(preset_name, format_type)

def get_version_info(path):
    """
    ИСПРАВЛЕНО: получить информацию о версии файла
    
    Args:
        path: Путь к файлу
        
    Returns:
        Dict: Информация о версии
    """
    return {
        'current_version': VersionManager.extract_version_from_path(path),
        'next_version': VersionManager.increment_version_in_path(path),
        'next_available': VersionManager.get_next_available_version(path),
        'is_valid_format': VersionManager.validate_version_format(
            VersionManager.extract_version_from_path(path) or ''
        ),
        'version_history': VersionManager.get_version_history(path)
    }

def validate_output_path(path):
    """
    НОВОЕ: валидация выходного пути
    
    Args:
        path: Путь для проверки
        
    Returns:
        tuple: (is_valid, issues)
    """
    quick_ops = QuickOperations()
    return quick_ops.validate_output_path(path)

def update_all_write_versions(increment=True):
    """
    НОВОЕ: обновить версии всех Write нод A-Train
    
    Args:
        increment: True для инкремента версий
        
    Returns:
        int: Количество обновленных нод
    """
    if not NUKE_AVAILABLE:
        return 0
    
    quick_ops = QuickOperations()
    updated_count = 0
    
    try:
        all_writes = nuke.allNodes('Write')
        for write_node in all_writes:
            # Проверяем что это нода A-Train (по note knob)
            if 'note' in write_node.knobs():
                note_text = write_node['note'].value()
                if 'A-Train' in note_text:
                    if quick_ops.update_write_node_version(write_node, increment):
                        updated_count += 1
        
        print(f"QuickOperations: Updated {updated_count} A-Train Write nodes")
        return updated_count
        
    except Exception as e:
        print(f"QuickOperations: Error updating write versions: {e}")
        return 0

def get_atrain_write_nodes():
    """
    НОВОЕ: получить все Write ноды созданные A-Train
    
    Returns:
        List[nuke.Node]: Write ноды A-Train
    """
    if not NUKE_AVAILABLE:
        return []
    
    try:
        atrain_writes = []
        all_writes = nuke.allNodes('Write')
        
        for write_node in all_writes:
            # Проверяем note knob для A-Train
            if 'note' in write_node.knobs():
                note_text = write_node['note'].value()
                if 'A-Train' in note_text:
                    atrain_writes.append(write_node)
        
        return atrain_writes
        
    except Exception as e:
        print(f"QuickOperations: Error getting A-Train writes: {e}")
        return []
