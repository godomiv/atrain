# atrain/core/integration.py
"""
Интеграционный модуль A-Train
Связывает PathBuilder с PresetManager и предоставляет высокоуровневые функции
"""

import os
from typing import Dict, List, Any, Optional, Tuple, Callable

from .preset_manager import PresetManager
from .path_builder import PathBuilder, build_path_from_tags
from .event_bus import EventBus, timed_cache

class PresetPathBuilder:
    """
    Интегрированная система построения путей из пресетов
    Объединяет PresetManager и PathBuilder для полноценной работы
    """
    
    def __init__(self, preset_manager: Optional[PresetManager] = None):
        """
        Инициализация с ленивой загрузкой компонентов
        
        Args:
            preset_manager: Экземпляр PresetManager (опционально)
        """
        self._preset_manager = preset_manager
        self._path_builder = None
        self._event_bus = None
        
        # Кеш для сгенерированных путей
        self._path_cache: Dict[str, str] = {}
        
        # Настройки по умолчанию
        self.default_format = "exr"
        self.auto_increment = True
        self.create_directories = True
        
        print("PresetPathBuilder: Initialized")
    
    @property
    def preset_manager(self) -> PresetManager:
        """Ленивая загрузка PresetManager"""
        if self._preset_manager is None:
            self._preset_manager = PresetManager()
            print("PresetPathBuilder: PresetManager loaded")
        return self._preset_manager
    
    @property
    def path_builder(self) -> PathBuilder:
        """Ленивая загрузка PathBuilder"""
        if self._path_builder is None:
            self._path_builder = PathBuilder()
            print("PresetPathBuilder: PathBuilder loaded")
        return self._path_builder
    
    @property
    def event_bus(self) -> EventBus:
        """Ленивая загрузка EventBus"""
        if self._event_bus is None:
            self._event_bus = EventBus.instance()
            print("PresetPathBuilder: EventBus connected")
        return self._event_bus
    
    def build_path_from_preset(self, preset_name: str, 
                               context: Optional[Dict[str, Any]] = None,
                               format_override: Optional[str] = None) -> Tuple[bool, str, List[str]]:
        """
        Построить путь из пресета
        
        Args:
            preset_name: Имя пресета
            context: Дополнительные контекстные переменные
            format_override: Принудительный формат файла
            
        Returns:
            Tuple[bool, str, List[str]]: (успех, путь, ошибки/предупреждения)
        """
        try:
            print(f"PresetPathBuilder: Building path from preset '{preset_name}'")
            
            # Загружаем пресет
            all_presets = self.preset_manager.get_all_presets()
            if preset_name not in all_presets:
                return False, "", [f"Preset '{preset_name}' not found"]
            
            preset_data = all_presets[preset_name]
            
            # Получаем теги пресета
            tag_names = preset_data.get('tags', [])
            preset_format = preset_data.get('format', self.default_format)
            final_format = format_override or preset_format
            
            if not tag_names:
                return False, "", ["Preset contains no tags"]
            
            # Преобразуем имена тегов в данные тегов
            success, tag_data_list, errors = self._resolve_tag_names(tag_names)
            if not success:
                return False, "", errors
            
            # Создаем новый PathBuilder для этого пресета
            builder = PathBuilder()
            
            # Устанавливаем контекстные переменные
            if context:
                for key, value in context.items():
                    builder.set_context_var(key, value)
            
            # Добавляем теги в builder
            for tag_data in tag_data_list:
                builder.add_tag(tag_data)
            
            # Генерируем путь
            generated_path = builder.build_path(final_format)
            
            if not generated_path:
                return False, "", ["Failed to generate path from tags"]
            
            # Применяем автоинкремент если нужно
            if self.auto_increment:
                generated_path = self._apply_auto_increment(generated_path)
            
            # Валидируем путь
            valid, validation_issues = builder.validate_path(generated_path)
            
            # Создаем директории если нужно
            if self.create_directories and valid:
                self._ensure_output_directory(generated_path)
            
            # Кешируем результат
            cache_key = f"{preset_name}_{hash(str(context))}"
            self._path_cache[cache_key] = generated_path
            
            # Публикуем событие
            self.event_bus.publish('path_generated', {
                'preset_name': preset_name,
                'path': generated_path,
                'format': final_format,
                'context': context
            })
            
            print(f"PresetPathBuilder: Generated path: {generated_path}")
            
            return True, generated_path, validation_issues
            
        except Exception as e:
            error_msg = f"Error building path from preset '{preset_name}': {e}"
            print(f"PresetPathBuilder: {error_msg}")
            return False, "", [error_msg]
    
    def _resolve_tag_names(self, tag_names: List[str]) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
        """Преобразование имен тегов в данные тегов"""
        try:
            all_tags = self.preset_manager.get_all_tags()
            tags_dict = {tag['name']: tag for tag in all_tags}
            
            resolved_tags = []
            errors = []
            
            for tag_name in tag_names:
                if tag_name in tags_dict:
                    resolved_tags.append(tags_dict[tag_name])
                else:
                    # Создаем fallback тег
                    fallback_tag = {
                        'name': tag_name,
                        'type': 'text',
                        'default': tag_name,
                        'source': 'fallback'
                    }
                    resolved_tags.append(fallback_tag)
                    errors.append(f"Tag '{tag_name}' not found, using fallback")
            
            return True, resolved_tags, errors
            
        except Exception as e:
            return False, [], [f"Error resolving tag names: {e}"]
    
    def _apply_auto_increment(self, path: str) -> str:
        """Применение автоинкремента к пути"""
        try:
            if not os.path.exists(path):
                return path
            
            directory = os.path.dirname(path)
            filename = os.path.basename(path)
            name, ext = os.path.splitext(filename)
            
            # Ищем существующие версии
            counter = 1
            while True:
                # Пытаемся найти версию в имени файла
                import re
                version_match = re.search(r'v(\d+)', name)
                
                if version_match:
                    # Инкрементируем существующую версию
                    current_version = int(version_match.group(1))
                    new_version = current_version + counter
                    digits = len(version_match.group(1))
                    new_name = re.sub(r'v\d+', f'v{new_version:0{digits}d}', name)
                else:
                    # Добавляем версию
                    new_name = f"{name}_v{counter:02d}"
                
                new_path = os.path.join(directory, f"{new_name}{ext}")
                
                if not os.path.exists(new_path):
                    print(f"PresetPathBuilder: Auto-incremented path: {path} -> {new_path}")
                    return new_path
                
                counter += 1
                if counter > 100:  # Защита от бесконечного цикла
                    break
            
            return path
            
        except Exception as e:
            print(f"PresetPathBuilder: Error in auto-increment: {e}")
            return path
    
    def _ensure_output_directory(self, path: str):
        """Создание выходной директории"""
        try:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                print(f"PresetPathBuilder: Created directory: {directory}")
        except Exception as e:
            print(f"PresetPathBuilder: Error creating directory: {e}")
    
    @timed_cache(seconds=30.0)
    def get_preset_path_preview(self, preset_name: str, 
                               context: Optional[Dict[str, Any]] = None) -> str:
        """
        Получить превью пути для пресета с кешированием
        
        Args:
            preset_name: Имя пресета
            context: Контекстные переменные
            
        Returns:
            str: Превью пути или сообщение об ошибке
        """
        try:
            success, path, errors = self.build_path_from_preset(preset_name, context)
            
            if success:
                return path
            else:
                return f"Error: {'; '.join(errors)}"
                
        except Exception as e:
            return f"Error generating preview: {e}"
    
    def get_available_presets(self) -> List[str]:
        """Получить список доступных пресетов"""
        try:
            all_presets = self.preset_manager.get_all_presets()
            return list(all_presets.keys())
        except Exception as e:
            print(f"PresetPathBuilder: Error getting presets: {e}")
            return []
    
    def validate_preset(self, preset_name: str) -> Tuple[bool, List[str]]:
        """
        Валидация пресета
        
        Args:
            preset_name: Имя пресета для валидации
            
        Returns:
            Tuple[bool, List[str]]: (валиден, список проблем)
        """
        try:
            all_presets = self.preset_manager.get_all_presets()
            
            if preset_name not in all_presets:
                return False, [f"Preset '{preset_name}' does not exist"]
            
            preset_data = all_presets[preset_name]
            issues = []
            
            # Проверяем наличие тегов
            tag_names = preset_data.get('tags', [])
            if not tag_names:
                issues.append("Preset contains no tags")
            
            # Проверяем существование тегов
            all_tags = self.preset_manager.get_all_tags()
            tags_dict = {tag['name']: tag for tag in all_tags}
            
            missing_tags = []
            for tag_name in tag_names:
                if tag_name not in tags_dict:
                    missing_tags.append(tag_name)
            
            if missing_tags:
                issues.append(f"Missing tags: {', '.join(missing_tags)}")
            
            # Проверяем формат
            format_type = preset_data.get('format', '')
            if not format_type:
                issues.append("Preset missing format specification")
            
            # Пытаемся сгенерировать путь
            try:
                success, path, path_errors = self.build_path_from_preset(preset_name)
                if not success:
                    issues.extend(path_errors)
            except Exception as e:
                issues.append(f"Path generation failed: {e}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            return False, [f"Error validating preset: {e}"]
    
    def get_preset_info(self, preset_name: str) -> Optional[Dict[str, Any]]:
        """
        Получить подробную информацию о пресете
        
        Args:
            preset_name: Имя пресета
            
        Returns:
            Dict: Информация о пресете или None
        """
        try:
            all_presets = self.preset_manager.get_all_presets()
            
            if preset_name not in all_presets:
                return None
            
            preset_data = all_presets[preset_name]
            
            # Базовая информация
            info = {
                'name': preset_name,
                'tags': preset_data.get('tags', []),
                'format': preset_data.get('format', self.default_format),
                'category': preset_data.get('category', 'General'),
                'source': preset_data.get('source', 'custom'),
                'created': preset_data.get('created', ''),
                'author': preset_data.get('author', ''),
                'tags_count': len(preset_data.get('tags', [])),
            }
            
            # Валидация
            valid, issues = self.validate_preset(preset_name)
            info['valid'] = valid
            info['issues'] = issues
            
            # Превью пути
            try:
                success, preview_path, _ = self.build_path_from_preset(preset_name)
                info['path_preview'] = preview_path if success else "Unable to generate"
            except:
                info['path_preview'] = "Error generating preview"
            
            return info
            
        except Exception as e:
            print(f"PresetPathBuilder: Error getting preset info: {e}")
            return None
    
    def clear_cache(self):
        """Очистить кеш путей"""
        self._path_cache.clear()
        if hasattr(self.get_preset_path_preview, 'clear_cache'):
            self.get_preset_path_preview.clear_cache()
        print("PresetPathBuilder: Path cache cleared")


class BatchPathBuilder:
    """
    Система batch построения путей для множества элементов
    """
    
    def __init__(self, preset_path_builder: Optional[PresetPathBuilder] = None):
        """
        Инициализация
        
        Args:
            preset_path_builder: Экземпляр PresetPathBuilder
        """
        self._preset_path_builder = preset_path_builder
        self._event_bus = None
        
        print("BatchPathBuilder: Initialized")
    
    @property
    def preset_path_builder(self) -> PresetPathBuilder:
        """Ленивая загрузка PresetPathBuilder"""
        if self._preset_path_builder is None:
            self._preset_path_builder = PresetPathBuilder()
            print("BatchPathBuilder: PresetPathBuilder loaded")
        return self._preset_path_builder
    
    @property
    def event_bus(self) -> EventBus:
        """Ленивая загрузка EventBus"""
        if self._event_bus is None:
            self._event_bus = EventBus.instance()
            print("BatchPathBuilder: EventBus connected")
        return self._event_bus
    
    def build_paths_for_reads(self, preset_name: str, 
                             read_nodes: Optional[List] = None) -> List[Dict[str, Any]]:
        """
        Построить пути для Read нод
        
        Args:
            preset_name: Имя пресета
            read_nodes: Список Read нод (если None, использует выбранные)
            
        Returns:
            List[Dict]: Список результатов для каждой ноды
        """
        try:
            # Получаем Read ноды
            if read_nodes is None:
                read_nodes = self._get_selected_read_nodes()
            
            if not read_nodes:
                print("BatchPathBuilder: No Read nodes provided")
                return []
            
            results = []
            
            for read_node in read_nodes:
                try:
                    # Создаем контекст для каждой ноды
                    context = self._create_context_for_read(read_node)
                    
                    # Генерируем путь
                    success, path, errors = self.preset_path_builder.build_path_from_preset(
                        preset_name, context
                    )
                    
                    result = {
                        'read_node': read_node,
                        'read_name': read_node.name() if hasattr(read_node, 'name') else str(read_node),
                        'success': success,
                        'path': path,
                        'errors': errors,
                        'context': context
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    error_result = {
                        'read_node': read_node,
                        'read_name': str(read_node),
                        'success': False,
                        'path': '',
                        'errors': [f"Error processing node: {e}"],
                        'context': {}
                    }
                    results.append(error_result)
            
            # Публикуем событие
            self.event_bus.publish('batch_paths_generated', {
                'preset_name': preset_name,
                'results': results,
                'success_count': sum(1 for r in results if r['success']),
                'total_count': len(results)
            })
            
            print(f"BatchPathBuilder: Generated {len(results)} paths for preset '{preset_name}'")
            
            return results
            
        except Exception as e:
            print(f"BatchPathBuilder: Error in batch path building: {e}")
            return []
    
    def _get_selected_read_nodes(self) -> List:
        """Получить выбранные Read ноды из Nuke"""
        try:
            import nuke
            return nuke.selectedNodes("Read")
        except:
            return []
    
    def _create_context_for_read(self, read_node) -> Dict[str, Any]:
        """Создать контекст для Read ноды"""
        context = {}
        
        try:
            if hasattr(read_node, 'name'):
                context['read_name'] = read_node.name()
            
            if hasattr(read_node, '__getitem__'):  # Nuke node
                # Извлекаем информацию из Read ноды
                file_path = read_node['file'].value() if 'file' in read_node.knobs() else ''
                
                if file_path:
                    # Пытаемся извлечь shot/sequence из пути
                    filename = os.path.basename(file_path)
                    
                    # Паттерны для shot names
                    import re
                    shot_patterns = [
                        r'([A-Za-z0-9_]+)_\d+\.',  # shot_name_0001.exr
                        r'([A-Za-z0-9_]+)\.\d+\.',  # shot_name.0001.exr
                        r'(SH\d+)',                 # SH010
                        r'([A-Za-z0-9_]+)_comp',    # shot_comp
                    ]
                    
                    for pattern in shot_patterns:
                        match = re.search(pattern, filename)
                        if match:
                            context['shot_name'] = match.group(1)
                            break
                    
                    # Sequence из пути
                    seq_match = re.search(r'(SQ\d+)', file_path)
                    if seq_match:
                        context['sequence'] = seq_match.group(1)
            
        except Exception as e:
            print(f"BatchPathBuilder: Error creating context for read node: {e}")
        
        return context
    
    def get_batch_preview(self, preset_name: str, 
                         read_nodes: Optional[List] = None) -> List[Dict[str, str]]:
        """
        Получить превью путей для batch операции
        
        Args:
            preset_name: Имя пресета
            read_nodes: Список Read нод
            
        Returns:
            List[Dict]: Превью для каждой ноды
        """
        try:
            if read_nodes is None:
                read_nodes = self._get_selected_read_nodes()
            
            previews = []
            
            for read_node in read_nodes:
                try:
                    context = self._create_context_for_read(read_node)
                    read_name = read_node.name() if hasattr(read_node, 'name') else str(read_node)
                    
                    preview_path = self.preset_path_builder.get_preset_path_preview(
                        preset_name, context
                    )
                    
                    previews.append({
                        'read_name': read_name,
                        'preview_path': preview_path
                    })
                    
                except Exception as e:
                    previews.append({
                        'read_name': str(read_node),
                        'preview_path': f"Error: {e}"
                    })
            
            return previews
            
        except Exception as e:
            print(f"BatchPathBuilder: Error generating batch preview: {e}")
            return []


# Глобальные экземпляры для удобства
_global_preset_path_builder = None
_global_batch_path_builder = None

def get_preset_path_builder() -> PresetPathBuilder:
    """Получить глобальный экземпляр PresetPathBuilder"""
    global _global_preset_path_builder
    if _global_preset_path_builder is None:
        _global_preset_path_builder = PresetPathBuilder()
    return _global_preset_path_builder

def get_batch_path_builder() -> BatchPathBuilder:
    """Получить глобальный экземпляр BatchPathBuilder"""
    global _global_batch_path_builder
    if _global_batch_path_builder is None:
        _global_batch_path_builder = BatchPathBuilder()
    return _global_batch_path_builder

# Удобные функции для быстрого использования
def build_preset_path(preset_name: str, 
                     context: Optional[Dict[str, Any]] = None,
                     format_override: Optional[str] = None) -> Tuple[bool, str, List[str]]:
    """Быстрое построение пути из пресета"""
    builder = get_preset_path_builder()
    return builder.build_path_from_preset(preset_name, context, format_override)

def get_preset_preview(preset_name: str, 
                      context: Optional[Dict[str, Any]] = None) -> str:
    """Быстрое получение превью пути"""
    builder = get_preset_path_builder()
    return builder.get_preset_path_preview(preset_name, context)

def validate_preset_path(preset_name: str) -> Tuple[bool, List[str]]:
    """Быстрая валидация пресета"""
    builder = get_preset_path_builder()
    return builder.validate_preset(preset_name)

def build_batch_paths(preset_name: str, read_nodes: Optional[List] = None) -> List[Dict[str, Any]]:
    """Быстрое построение batch путей"""
    builder = get_batch_path_builder()
    return builder.build_paths_for_reads(preset_name, read_nodes)

# Функции для отладки
def debug_integration():
    """Отладочная информация о системе интеграции"""
    print("=== Integration Debug ===")
    
    try:
        ppb = get_preset_path_builder()
        print(f"PresetPathBuilder: {ppb}")
        print(f"Available presets: {len(ppb.get_available_presets())}")
        
        bpb = get_batch_path_builder()
        print(f"BatchPathBuilder: {bpb}")
        
        # Тестируем один пресет
        presets = ppb.get_available_presets()
        if presets:
            test_preset = presets[0]
            valid, issues = ppb.validate_preset(test_preset)
            print(f"Test preset '{test_preset}' valid: {valid}")
            if issues:
                print(f"Issues: {issues}")
        
    except Exception as e:
        print(f"Error in integration debug: {e}")
    
    print("========================")

# Пример использования (можно удалить в продакшн)
if __name__ == "__main__":
    print("A-Train Integration Test")
    
    # Тестируем PresetPathBuilder
    ppb = PresetPathBuilder()
    
    # Получаем доступные пресеты
    presets = ppb.get_available_presets()
    print(f"Available presets: {presets}")
    
    if presets:
        # Тестируем первый пресет
        test_preset = presets[0]
        success, path, errors = ppb.build_path_from_preset(test_preset)
        print(f"Test path for '{test_preset}': {path}")
        if errors:
            print(f"Errors: {errors}")
    
    # Отладочная информация
    debug_integration()
