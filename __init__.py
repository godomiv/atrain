# atrain/__init__.py
"""
A-Train for Nuke - ФИНАЛЬНАЯ ВЕРСИЯ с всеми исправлениями
ИСПРАВЛЕНО: padding %04d, имена файлов, категории, убраны уведомления, стандартные имена Write
"""

__version__ = "1.5.2"
__author__ = "A-Train Team"
__description__ = "Advanced Path Constructor for Nuke with Railway Theme"

import os
import sys

# Глобальный экземпляр окна
_window = None

def run_atrain():
    """
    ИСПРАВЛЕНО: главная функция запуска A-Train с полным функционалом
    
    Returns:
        ATrainWindow: Экземпляр главного окна
    """
    global _window
    
    try:
        # Проверяем доступность Nuke
        try:
            import nuke
            print(f"A-Train v{__version__}: Starting with Nuke {nuke.NUKE_VERSION_STRING}")
        except ImportError:
            print(f"A-Train v{__version__}: Running in standalone mode (no Nuke)")
        
        if _window is None:
            from .ui.main_window_enhanced import ATrainWindow
            _window = ATrainWindow()
            
            # Печатаем информацию о настройках проекта
            _print_project_info()
        
        _window.show()
        _window.raise_()
        _window.activateWindow()
        
        return _window
        
    except Exception as e:
        print(f"A-Train: Error launching enhanced window: {e}")
        try:
            # Fallback к простому окну если есть
            from .ui.main_window import ATrainWindow
            _window = ATrainWindow()
            _window.show()
            _window.raise_()
            _window.activateWindow()
            return _window
        except Exception as fallback_error:
            print(f"A-Train: Error launching fallback window: {fallback_error}")
            return None

def _print_project_info():
    """НОВОЕ: печать информации о проекте"""
    try:
        from .core.preset_manager import PresetManager
        pm = PresetManager()
        project_info = pm.get_project_info()
        
        print(f"A-Train: Project directory: {project_info['project_directory']}")
        print(f"A-Train: Settings directory: {project_info['atrain_directory']}")
        
        files_status = []
        for file_type, exists in project_info['files_exist'].items():
            status = "✓" if exists else "✗"
            files_status.append(f"{file_type}: {status}")
        
        print(f"A-Train: Config files: {', '.join(files_status)}")
        
    except Exception as e:
        print(f"A-Train: Error getting project info: {e}")

def show_atrain():
    """
    Показать существующее окно A-Train или создать новое
    
    Returns:
        ATrainWindow: Экземпляр главного окна
    """
    global _window
    
    if _window is not None:
        try:
            _window.show()
            _window.raise_()
            _window.activateWindow()
            return _window
        except RuntimeError:
            # Окно было удалено
            _window = None
            return run_atrain()
    else:
        return run_atrain()

def close_atrain():
    """
    Закрыть A-Train и освободить ресурсы
    
    Returns:
        bool: True если успешно закрыто
    """
    global _window
    
    if _window is not None:
        try:
            _window.close()
            _window = None
            print("A-Train: Window closed successfully")
            return True
        except Exception as e:
            print(f"A-Train: Error closing window: {e}")
            _window = None
            return False
    return True

def get_version():
    """Получить версию A-Train"""
    return __version__

def get_version_info():
    """Получить подробную информацию о версии"""
    return {
        'version': __version__,
        'author': __author__,
        'description': __description__,
        'features': [
            'Railway themed node graph',
            'Version management with VersionManager',
            'Project-based JSON settings',
            'Enhanced batch operations',
            'Live path preview with %04d padding',
            'Custom tags and presets with categories',
            'Smart Write node creation with standard names',
            'File names display in batch operations',
            'No annoying success notifications'
        ]
    }

def is_running():
    """Проверить, запущен ли A-Train"""
    global _window
    try:
        return _window is not None and _window.isVisible()
    except:
        return False

def get_window():
    """Получить экземпляр окна A-Train"""
    global _window
    return _window

# ============================================================================
# БЫСТРЫЕ ОПЕРАЦИИ - ИСПРАВЛЕНО с VersionManager и стандартными именами
# ============================================================================

def quick_write(preset_name=None, auto_increment=True, format_type="exr"):
    """
    ИСПРАВЛЕНО: быстрое создание Write ноды со стандартным именем
    
    Args:
        preset_name (str): Имя пресета (опционально)
        auto_increment (bool): Автоинкремент версии
        format_type (str): Формат файла
        
    Returns:
        nuke.Node: Созданная Write нода или None
    """
    try:
        from .utils.quick_ops import create_quick_write
        return create_quick_write(preset_name, auto_increment, format_type=format_type)
    except Exception as e:
        print(f"A-Train: Error in quick_write: {e}")
        return None

def batch_write(preset_name=None):
    """
    ИСПРАВЛЕНО: batch создание Write нод для выбранных Read нод
    
    Args:
        preset_name (str): Имя пресета (опционально)
        
    Returns:
        list: Список созданных Write нод
    """
    try:
        from .utils.batch_ops import create_write_nodes_for_selected
        results = create_write_nodes_for_selected(preset_name or "Default")
        return [r.created_node for r in results if r.success and r.created_node]
    except Exception as e:
        print(f"A-Train: Error in batch_write: {e}")
        return []

def transcode_reads(base_path, format_type="exr"):
    """
    ИСПРАВЛЕНО: транскодирование выбранных Read нод с именами файлов
    
    Args:
        base_path (str): Базовый путь с [read_name] placeholder
        format_type (str): Формат файла
        
    Returns:
        list: Список созданных Write нод
    """
    try:
        from .utils.batch_ops import transcode_selected_reads
        return transcode_selected_reads(base_path, format_type)
    except Exception as e:
        print(f"A-Train: Error in transcode_reads: {e}")
        return []

def create_writes_for_selected(format_type="exr", use_preset=None):
    """
    ИСПРАВЛЕНО: создать Write ноды для выбранных Read нод
    
    Args:
        format_type (str): Формат файла
        use_preset (str): Имя пресета
        
    Returns:
        list: Список созданных Write нод
    """
    try:
        from .utils.quick_ops import create_writes_for_selected_reads
        return create_writes_for_selected_reads(format_type, use_preset)
    except Exception as e:
        print(f"A-Train: Error in create_writes_for_selected: {e}")
        return []

# ============================================================================
# РАБОТА С ПУТЯМИ И ГРАФОМ - ИСПРАВЛЕНО с правильным padding
# ============================================================================

def get_current_path():
    """
    Получить текущий сгенерированный путь из A-Train
    
    Returns:
        str: Текущий путь или пустая строка
    """
    global _window
    
    if _window is not None:
        try:
            if hasattr(_window, 'current_path'):
                return _window.current_path
            elif _window.is_advanced_mode:
                from .ui.node_graph import path_chain
                return path_chain.get_current_path()
            else:
                return _window.basic_path_preview.text()
        except Exception as e:
            print(f"A-Train: Error getting current path: {e}")
    
    return ""

def build_path_from_tags(tags, live_preview=False):
    """
    ИСПРАВЛЕНО: построить путь из списка тегов с правильным padding %04d
    
    Args:
        tags (list): Список тегов
        live_preview (bool): Live preview режим
        
    Returns:
        str: Построенный путь
    """
    try:
        from .core.path_builder import PathBuilder
        builder = PathBuilder()
        
        for tag in tags:
            builder.add_tag(tag)
        
        return builder.build_path(live_preview=live_preview)
    except Exception as e:
        print(f"A-Train: Error building path from tags: {e}")
        return ""

def add_tag_to_graph(tag_data):
    """
    Добавить тег в граф A-Train
    
    Args:
        tag_data (dict): Данные тега
        
    Returns:
        bool: True если тег добавлен успешно
    """
    global _window
    
    if _window is not None:
        try:
            if hasattr(_window, 'atrain_widget') and _window.is_advanced_mode:
                _window.atrain_widget.add_tag_node(tag_data)
                return True
        except Exception as e:
            print(f"A-Train: Error adding tag to graph: {e}")
    
    return False

def load_preset_to_graph(preset_name):
    """
    Загрузить пресет в граф A-Train
    
    Args:
        preset_name (str): Имя пресета
        
    Returns:
        bool: True если пресет загружен успешно
    """
    global _window
    
    if _window is not None:
        try:
            from .core.preset_manager import PresetManager
            pm = PresetManager()
            all_presets = pm.get_all_presets()
            
            if preset_name in all_presets:
                preset_data = all_presets[preset_name]
                tags = preset_data.get('tags', [])
                format_type = preset_data.get('format', 'exr')
                
                if hasattr(_window, 'atrain_widget') and _window.is_advanced_mode:
                    _window.atrain_widget.load_preset_nodes(tags, format_type)
                    return True
                else:
                    # Загружаем в базовом режиме
                    _window.load_preset_data(preset_name, preset_data)
                    return True
        except Exception as e:
            print(f"A-Train: Error loading preset to graph: {e}")
    
    return False

def clear_graph():
    """
    Очистить граф A-Train
    
    Returns:
        bool: True если граф очищен успешно
    """
    global _window
    
    if _window is not None:
        try:
            if hasattr(_window, 'atrain_widget') and _window.is_advanced_mode:
                _window.atrain_widget.clear_all_nodes()
                return True
        except Exception as e:
            print(f"A-Train: Error clearing graph: {e}")
    
    return False

def get_graph_path():
    """
    Получить текущий путь из графа A-Train
    
    Returns:
        str: Путь из графа или пустая строка
    """
    try:
        from .ui.node_graph import path_chain
        return path_chain.get_current_path()
    except Exception as e:
        print(f"A-Train: Error getting graph path: {e}")
        return ""

def get_graph_tags():
    """
    Получить список тегов из графа A-Train
    
    Returns:
        list: Список данных тегов из графа
    """
    try:
        from .ui.node_graph import path_chain
        return [node.tag_data for node in path_chain.tag_nodes]
    except Exception as e:
        print(f"A-Train: Error getting graph tags: {e}")
        return []

# ============================================================================
# УПРАВЛЕНИЕ ВЕРСИЯМИ - ИСПРАВЛЕНО с VersionManager
# ============================================================================

def increment_version(path):
    """
    ИСПРАВЛЕНО: увеличить версию в пути файла
    
    Args:
        path (str): Путь к файлу
        
    Returns:
        str: Путь с увеличенной версией
    """
    try:
        from .core.version_manager import VersionManager
        return VersionManager.increment_version_in_path(path)
    except Exception as e:
        print(f"A-Train: Error incrementing version: {e}")
        return path

def extract_version(path):
    """
    ИСПРАВЛЕНО: извлечь версию из пути файла
    
    Args:
        path (str): Путь к файлу
        
    Returns:
        str: Найденная версия или None
    """
    try:
        from .core.version_manager import VersionManager
        return VersionManager.extract_version_from_path(path)
    except Exception as e:
        print(f"A-Train: Error extracting version: {e}")
        return None

def get_next_version(path):
    """
    НОВОЕ: получить следующую доступную версию файла
    
    Args:
        path (str): Путь к файлу
        
    Returns:
        str: Путь с доступной версией
    """
    try:
        from .core.version_manager import VersionManager
        return VersionManager.get_next_available_version(path)
    except Exception as e:
        print(f"A-Train: Error getting next version: {e}")
        return path

def get_version_history(path):
    """
    НОВОЕ: получить историю версий файла
    
    Args:
        path (str): Путь к файлу
        
    Returns:
        list: Список путей к версиям файла
    """
    try:
        from .core.version_manager import VersionManager
        return VersionManager.get_version_history(path)
    except Exception as e:
        print(f"A-Train: Error getting version history: {e}")
        return []

def validate_version(version_string):
    """
    НОВОЕ: проверить корректность формата версии
    
    Args:
        version_string (str): Строка версии
        
    Returns:
        bool: True если формат корректен
    """
    try:
        from .core.version_manager import VersionManager
        return VersionManager.validate_version_format(version_string)
    except Exception as e:
        print(f"A-Train: Error validating version: {e}")
        return False

def create_write_with_version(output_path, auto_increment=True):
    """
    ИСПРАВЛЕНО: создать Write ноду с автоматическим управлением версиями
    
    Args:
        output_path (str): Базовый путь вывода
        auto_increment (bool): Автоинкремент версии
        
    Returns:
        nuke.Node: Write нода или None
    """
    try:
        if auto_increment:
            from .core.version_manager import VersionManager
            final_path = VersionManager.get_next_available_version(output_path)
        else:
            final_path = output_path
        
        from .utils.quick_ops import create_quick_write
        return create_quick_write(output_path=final_path, auto_increment=False)
    except Exception as e:
        print(f"A-Train: Error creating write with version: {e}")
        return None

def update_all_write_versions(increment=True):
    """
    НОВОЕ: обновить версии всех Write нод A-Train
    
    Args:
        increment (bool): True для инкремента версий
        
    Returns:
        int: Количество обновленных нод
    """
    try:
        from .utils.quick_ops import update_all_write_versions
        return update_all_write_versions(increment)
    except Exception as e:
        print(f"A-Train: Error updating write versions: {e}")
        return 0

# ============================================================================
# РАБОТА С НАСТРОЙКАМИ И ПРЕСЕТАМИ - ИСПРАВЛЕНО с категориями
# ============================================================================

def get_project_info():
    """
    НОВОЕ: получить информацию о проекте
    
    Returns:
        dict: Информация о проекте и настройках
    """
    try:
        from .core.preset_manager import PresetManager
        pm = PresetManager()
        return pm.get_project_info()
    except Exception as e:
        print(f"A-Train: Error getting project info: {e}")
        return {}

def backup_settings(backup_dir=None):
    """
    НОВОЕ: создать бэкап настроек проекта
    
    Args:
        backup_dir (str): Директория для бэкапа (опционально)
        
    Returns:
        list: Список созданных файлов бэкапа
    """
    try:
        from .core.preset_manager import PresetManager
        pm = PresetManager()
        return pm.backup_settings(backup_dir)
    except Exception as e:
        print(f"A-Train: Error creating backup: {e}")
        return []

def export_settings(export_path):
    """
    НОВОЕ: экспорт настроек в один файл
    
    Args:
        export_path (str): Путь для экспорта
        
    Returns:
        bool: True если успешно
    """
    try:
        from .core.preset_manager import PresetManager
        pm = PresetManager()
        return pm.export_settings(export_path)
    except Exception as e:
        print(f"A-Train: Error exporting settings: {e}")
        return False

def import_settings(import_path, merge=True):
    """
    НОВОЕ: импорт настроек из файла
    
    Args:
        import_path (str): Путь к файлу настроек
        merge (bool): True для слияния, False для замены
        
    Returns:
        bool: True если успешно
    """
    try:
        from .core.preset_manager import PresetManager
        pm = PresetManager()
        return pm.import_settings(import_path, merge)
    except Exception as e:
        print(f"A-Train: Error importing settings: {e}")
        return False

def get_all_presets():
    """
    Получить все доступные пресеты
    
    Returns:
        dict: Словарь пресетов
    """
    try:
        from .core.preset_manager import PresetManager
        pm = PresetManager()
        return pm.get_all_presets()
    except Exception as e:
        print(f"A-Train: Error getting presets: {e}")
        return {}

def get_all_tags():
    """
    Получить все доступные теги
    
    Returns:
        list: Список тегов
    """
    try:
        from .core.preset_manager import PresetManager
        pm = PresetManager()
        return pm.get_all_tags()
    except Exception as e:
        print(f"A-Train: Error getting tags: {e}")
        return []

# ============================================================================
# СТАТИСТИКА И ОТЛАДКА
# ============================================================================

def get_batch_stats():
    """
    ИСПРАВЛЕНО: получить статистику batch операций
    
    Returns:
        dict: Статистика операций
    """
    try:
        from .utils.batch_ops import get_batch_stats
        return get_batch_stats()
    except Exception as e:
        print(f"A-Train: Error getting batch stats: {e}")
        return {}

def get_atrain_write_nodes():
    """
    НОВОЕ: получить все Write ноды созданные A-Train
    
    Returns:
        list: Write ноды A-Train
    """
    try:
        from .utils.quick_ops import get_atrain_write_nodes
        return get_atrain_write_nodes()
    except Exception as e:
        print(f"A-Train: Error getting A-Train writes: {e}")
        return []

def validate_output_path(path):
    """
    НОВОЕ: валидация выходного пути
    
    Args:
        path (str): Путь для проверки
        
    Returns:
        tuple: (is_valid, issues)
    """
    try:
        from .utils.quick_ops import validate_output_path
        return validate_output_path(path)
    except Exception as e:
        print(f"A-Train: Error validating path: {e}")
        return False, [str(e)]

def debug_info():
    """
    ИСПРАВЛЕНО: получить отладочную информацию A-Train
    
    Returns:
        dict: Отладочная информация
    """
    try:
        info = {
            'version': __version__,
            'window_running': is_running(),
            'current_path': get_current_path(),
            'graph_tags_count': len(get_graph_tags()),
            'batch_stats': get_batch_stats(),
            'project_info': get_project_info(),
            'atrain_writes_count': len(get_atrain_write_nodes())
        }
        
        # Добавляем информацию о графе если в advanced режиме
        if _window and _window.is_advanced_mode:
            from .ui.node_graph import path_chain
            info['graph_nodes_count'] = len(path_chain.tag_nodes)
            info['graph_path'] = path_chain.get_current_path()
        
        return info
    except Exception as e:
        return {'error': str(e), 'version': __version__}

def test_version_patterns():
    """
    НОВОЕ: тестирование паттернов версий
    
    Returns:
        dict: Результаты тестов
    """
    try:
        from .core.version_manager import test_version_patterns
        test_version_patterns()
        return {'status': 'Test completed, check console output'}
    except Exception as e:
        return {'error': str(e)}

# ============================================================================
# АЛИАСЫ ДЛЯ СОВМЕСТИМОСТИ С ОРИГИНАЛЬНЫМ API
# ============================================================================

# Основные функции
runatrain = run_atrain
runatrainhybrid = run_atrain
showatrain = show_atrain
closeatrain = close_atrain

# Быстрые операции
quickwrite = quick_write
batchwrite = batch_write
transcodereads = transcode_reads

# Работа с путями
getCurrentPath = get_current_path
buildPathFromTags = build_path_from_tags
addTagToGraph = add_tag_to_graph
loadPresetToGraph = load_preset_to_graph
clearGraph = clear_graph
getGraphPath = get_graph_path
getGraphTags = get_graph_tags

# Управление версиями
incrementVersion = increment_version
extractVersion = extract_version
getNextVersion = get_next_version
getVersionHistory = get_version_history
validateVersion = validate_version

# Настройки
getProjectInfo = get_project_info
backupSettings = backup_settings
exportSettings = export_settings
importSettings = import_settings
getAllPresets = get_all_presets
getAllTags = get_all_tags

# Статистика
getBatchStats = get_batch_stats
debugInfo = debug_info

# ============================================================================
# ИНТЕГРАЦИЯ С NUKE MENU - ИСПРАВЛЕНО с новыми функциями
# ============================================================================

def install_menu():
    """
    ИСПРАВЛЕНО: установить A-Train в меню Nuke с полным функционалом
    
    Returns:
        bool: True если успешно установлено
    """
    try:
        import nuke
        
        # Создаем главное меню A-Train
        atrain_menu = nuke.menu('Nuke').addMenu('A-Train')
        
        # Основные команды
        atrain_menu.addCommand('Launch A-Train', 'import atrain; atrain.run_atrain()', 'ctrl+alt+a')
        atrain_menu.addSeparator()
        
        # Быстрые операции
        quick_menu = atrain_menu.addMenu('Quick Operations')
        quick_menu.addCommand('Quick Write', 'import atrain; atrain.quick_write()', 'ctrl+alt+w')
        quick_menu.addCommand('Batch Write Selected', 'import atrain; atrain.batch_write()', 'ctrl+alt+b')
        quick_menu.addCommand('Transcode Selected Reads', 
                             'import atrain; atrain.transcode_reads("/tmp/[read_name]_v01.%04d.exr")')
        quick_menu.addSeparator()
        quick_menu.addCommand('Create Write with Versioning', 
                             'import atrain; atrain.create_write_with_version("output_v01.%04d.exr")')
        
        # Управление версиями
        version_menu = atrain_menu.addMenu('Version Tools')
        version_menu.addCommand('Increment All A-Train Writes', 
                               'import atrain; count = atrain.update_all_write_versions(); '
                               'print(f"Updated {count} Write nodes")')
        version_menu.addCommand('Get Next Available Version', 
                               'import atrain; path = nuke.getFilename("Select file"); '
                               'result = atrain.get_next_version(path); print(f"Next version: {result}")')
        version_menu.addCommand('Show Version History', 
                               'import atrain; path = nuke.getFilename("Select file"); '
                               'history = atrain.get_version_history(path); '
                               'print(f"Version history: {history}")')
        
        # Настройки проекта
        settings_menu = atrain_menu.addMenu('Project Settings')
        settings_menu.addCommand('Show Project Info', 
                                'import atrain; info = atrain.get_project_info(); '
                                'print(f"Project: {info}")')
        settings_menu.addCommand('Backup Settings', 
                                'import atrain; files = atrain.backup_settings(); '
                                'print(f"Backup created: {len(files)} files")')
        settings_menu.addCommand('Export Settings...', 
                                'import atrain; path = nuke.getFilename("Export to", "*.json"); '
                                'atrain.export_settings(path) if path else None')
        settings_menu.addCommand('Import Settings...', 
                                'import atrain; path = nuke.getFilename("Import from", "*.json"); '
                                'atrain.import_settings(path) if path else None')
        
        # Отладка и справка
        atrain_menu.addSeparator()
        atrain_menu.addCommand('Debug Info', 
                              'import atrain; info = atrain.debug_info(); '
                              'print("=== A-Train Debug Info ==="); '
                              'for k, v in info.items(): print(f"{k}: {v}")')
        atrain_menu.addCommand('Test Version Patterns', 
                              'import atrain; atrain.test_version_patterns()')
        atrain_menu.addCommand('Show A-Train Writes', 
                              'import atrain; writes = atrain.get_atrain_write_nodes(); '
                              'print(f"A-Train Write nodes: {[w.name() for w in writes]}")')
        atrain_menu.addSeparator()
        atrain_menu.addCommand('Close A-Train', 'import atrain; atrain.close_atrain()')
        
        print(f"A-Train v{__version__}: Menu installed successfully")
        return True
        
    except Exception as e:
        print(f"A-Train: Error installing menu: {e}")
        return False

def uninstall_menu():
    """
    НОВОЕ: удалить меню A-Train из Nuke
    
    Returns:
        bool: True если успешно удалено
    """
    try:
        import nuke
        nuke_menu = nuke.menu('Nuke')
        nuke_menu.removeItem('A-Train')
        print("A-Train: Menu uninstalled successfully")
        return True
    except Exception as e:
        print(f"A-Train: Error uninstalling menu: {e}")
        return False

# ============================================================================
# ТОЧКИ ВХОДА
# ============================================================================

def main():
    """Альтернативная точка входа"""
    return run_atrain()

def cli():
    """Точка входа для командной строки"""
    import argparse
    
    parser = argparse.ArgumentParser(description=f'A-Train v{__version__} - {__description__}')
    parser.add_argument('--version', action='version', version=f'A-Train {__version__}')
    parser.add_argument('--info', action='store_true', help='Show debug information')
    parser.add_argument('--test-versions', action='store_true', help='Test version patterns')
    parser.add_argument('--backup', metavar='DIR', help='Create backup of settings')
    parser.add_argument('--export', metavar='FILE', help='Export settings to file')
    parser.add_argument('--import', metavar='FILE', dest='import_file', help='Import settings from file')
    
    args = parser.parse_args()
    
    if args.info:
        info = debug_info()
        print("=== A-Train Debug Information ===")
        for key, value in info.items():
            print(f"{key}: {value}")
    
    elif args.test_versions:
        test_version_patterns()
    
    elif args.backup:
        files = backup_settings(args.backup)
        print(f"Backup created: {len(files)} files")
        for file in files:
            print(f"  {file}")
    
    elif args.export:
        if export_settings(args.export):
            print(f"Settings exported to: {args.export}")
        else:
            print("Export failed")
    
    elif args.import_file:
        if import_settings(args.import_file):
            print(f"Settings imported from: {args.import_file}")
        else:
            print("Import failed")
    
    else:
        print(f"A-Train v{__version__} - {__description__}")
        print("Use --help for available options")

if __name__ == "__main__":
    # Тестирование при прямом запуске
    print(f"A-Train v{__version__} - {__description__}")
    print("Debug info:", debug_info())
