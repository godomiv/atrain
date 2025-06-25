# atrain/__init__.py
"""
A-Train for Nuke - Рефакторенная версия с новой архитектурой
"""

__version__ = "2.0.0"
__author__ = "A-Train Team"
__description__ = "Advanced Path Constructor for Nuke with Railway Theme"

import os
import sys

# Убедимся, что путь к модулю добавлен
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

# Глобальный экземпляр окна
_window = None

def run_atrain():
    """
    Главная функция запуска A-Train
    
    Returns:
        ATrainWindow: Экземпляр главного окна
    """
    global _window
    
    try:
        # Проверяем доступность Nuke
        from .core.nuke import nuke_bridge
        bridge = nuke_bridge()
        
        if bridge.available:
            print(f"A-Train v{__version__}: Starting with Nuke {bridge.nuke.NUKE_VERSION_STRING}")
        else:
            print(f"A-Train v{__version__}: Running in standalone mode (no Nuke)")
        
        if _window is None:
            # Пока используем старое окно, потом заменим на новое
            from .ui.main_window_enhanced import ATrainWindow
            _window = ATrainWindow()
            
            # Печатаем информацию о настройках проекта
            _print_project_info()
        
        _window.show()
        _window.raise_()
        _window.activateWindow()
        
        return _window
        
    except Exception as e:
        print(f"A-Train: Error launching window: {e}")
        import traceback
        traceback.print_exc()
        return None

def _print_project_info():
    """Печать информации о проекте"""
    try:
        from .core.storage import StorageManager
        sm = StorageManager()
        project_info = sm.get_project_info()
        
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
    """Показать существующее окно A-Train или создать новое"""
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
    """Закрыть A-Train и освободить ресурсы"""
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

# ============================================================================
# БЫСТРЫЕ ОПЕРАЦИИ С НОВОЙ АРХИТЕКТУРОЙ
# ============================================================================

def quick_write(preset_name=None, auto_increment=True, format_type="exr"):
    """
    Быстрое создание Write ноды
    
    Args:
        preset_name (str): Имя пресета (опционально)
        auto_increment (bool): Автоинкремент версии
        format_type (str): Формат файла
        
    Returns:
        nuke.Node: Созданная Write нода или None
    """
    try:
        from .core.nuke import nuke_bridge, NodeUtils
        from .core.storage import StorageManager
        from .core.path_builder import PathBuilder
        from .core.utils.version import get_next_available_version
        
        bridge = nuke_bridge()
        if not bridge.available:
            print("A-Train: Nuke not available")
            return None
        
        # Создаём путь
        path_builder = PathBuilder()
        
        if preset_name:
            # Загружаем пресет
            sm = StorageManager()
            preset = sm.get_preset(preset_name)
            if preset:
                # Добавляем теги из пресета
                all_tags = sm.get_all_tags()
                tags_dict = {tag.name: tag for tag in all_tags}
                
                for tag_name in preset.tags:
                    if tag_name in tags_dict:
                        path_builder.add_tag(tags_dict[tag_name])
                
                # Добавляем format тег
                from .core.models import TagData, TagType
                format_tag = TagData(
                    name='format',
                    type=TagType.FORMAT,
                    format=preset.format,
                    padding='%04d'
                )
                path_builder.add_tag(format_tag)
        else:
            # Используем дефолтный путь
            from .core.models import PathContext
            context = PathContext()
            path_builder.set_context(context)
            
            # Простой путь
            output_path = f"{context.project_path or '/tmp'}/output_v01.%04d.{format_type}"
        
        # Строим путь
        output_path = path_builder.build_path()
        
        # Автоинкремент если нужно
        if auto_increment:
            output_path = get_next_available_version(output_path)
        
        # Создаём Write ноду
        node_utils = NodeUtils()
        write_node = node_utils.create_write_node(output_path)
        
        if write_node:
            # Добавляем метку A-Train
            bridge.set_knob_value(write_node, 'note', f'A-Train\n{os.path.basename(output_path)}')
            
            # Подключаем к выбранной ноде
            selected = bridge.get_selected_nodes()
            if selected:
                write_node.setInput(0, selected[0])
                node_utils.position_node_relative(write_node, selected[0])
        
        return write_node
        
    except Exception as e:
        print(f"A-Train: Error in quick_write: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_current_path():
    """Получить текущий путь из окна A-Train"""
    global _window
    
    if _window is not None:
        try:
            if hasattr(_window, 'get_current_path'):
                return _window.get_current_path()
            elif hasattr(_window, 'basic_path_preview'):
                return _window.basic_path_preview.text()
        except:
            pass
    
    return ""

# ============================================================================
# РАБОТА С ВЕРСИЯМИ
# ============================================================================

def increment_version(path):
    """Увеличить версию в пути"""
    from .core.utils.version import increment_version as inc_ver
    return inc_ver(path)

def get_next_version(path):
    """Получить следующую доступную версию"""
    from .core.utils.version import get_next_available_version
    return get_next_available_version(path)

# ============================================================================
# РАБОТА С НАСТРОЙКАМИ
# ============================================================================

def get_all_presets():
    """Получить все доступные пресеты"""
    try:
        from .core.storage import StorageManager
        sm = StorageManager()
        return {name: preset.to_dict() for name, preset in sm.get_all_presets().items()}
    except Exception as e:
        print(f"A-Train: Error getting presets: {e}")
        return {}

def get_all_tags():
    """Получить все доступные теги"""
    try:
        from .core.storage import StorageManager
        sm = StorageManager()
        return [tag.to_dict() for tag in sm.get_all_tags()]
    except Exception as e:
        print(f"A-Train: Error getting tags: {e}")
        return []

# ============================================================================
# ИНТЕГРАЦИЯ С NUKE MENU
# ============================================================================

def install_menu():
    """Установить A-Train в меню Nuke"""
    try:
        from .core.nuke import nuke_bridge
        bridge = nuke_bridge()
        
        if not bridge.available:
            print("A-Train: Cannot install menu - Nuke not available")
            return False
        
        nuke = bridge.nuke
        
        # Создаем главное меню A-Train
        atrain_menu = nuke.menu('Nuke').addMenu('A-Train')
        
        # Основные команды
        atrain_menu.addCommand('Launch A-Train', 'import atrain; atrain.run_atrain()', 'ctrl+alt+a')
        atrain_menu.addSeparator()
        
        # Быстрые операции
        quick_menu = atrain_menu.addMenu('Quick Operations')
        quick_menu.addCommand('Quick Write', 'import atrain; atrain.quick_write()', 'ctrl+alt+w')
        
        # Версии
        version_menu = atrain_menu.addMenu('Version Tools')
        version_menu.addCommand('Get Next Version', 
                               'import atrain; path = nuke.getFilename("Select file"); '
                               'if path: print("Next version:", atrain.get_next_version(path))')
        
        atrain_menu.addSeparator()
        atrain_menu.addCommand('Close A-Train', 'import atrain; atrain.close_atrain()')
        
        print(f"A-Train v{__version__}: Menu installed successfully")
        return True
        
    except Exception as e:
        print(f"A-Train: Error installing menu: {e}")
        return False

# ============================================================================
# ТОЧКИ ВХОДА
# ============================================================================

def main():
    """Альтернативная точка входа"""
    return run_atrain()

# Алиасы для совместимости
runatrain = run_atrain
showatrain = show_atrain
closeatrain = close_atrain
quickwrite = quick_write
getNextVersion = get_next_version
getAllPresets = get_all_presets
getAllTags = get_all_tags

if __name__ == "__main__":
    print(f"A-Train v{__version__} - {__description__}")
    
    # Тестируем импорты
    try:
        from .core.nuke import nuke_bridge
        print("✓ Nuke bridge ready")
        
        from .core.storage import StorageManager
        print("✓ Storage ready")
        
        from .core.path_builder import PathBuilder
        print("✓ Path builder ready")
        
        print("\nA-Train core systems initialized successfully!")
    except Exception as e:
        print(f"✗ Initialization error: {e}")
        import traceback
        traceback.print_exc()
