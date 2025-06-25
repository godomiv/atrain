# atrain/ui/main_window_enhanced.py
"""
Главное окно A-Train - ИСПРАВЛЕНО: убрано серое поле, имена файлов, категории, убраны уведомления
"""

import os
from typing import Optional, Dict, Any, List
from PySide2 import QtWidgets, QtCore, QtGui

from ..core.preset_manager import PresetManager
from ..core.version_manager import VersionManager
from ..core.event_bus import EventBus
from .styles import StyleManager
from .widgets import TagListWidget, PresetListWidget

class ATrainWindow(QtWidgets.QDialog):
    """ИСПРАВЛЕНО: Главное окно A-Train - все исправления применены"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("A-Train Path Constructor v1.5")
        self.preset_manager = PresetManager()
        self.style_manager = StyleManager.instance()
        self.event_bus = EventBus.instance()
        
        # Флаги состояния
        self.is_advanced_mode = False
        self.loading_preset = False
        self._switching_mode = False
        
        self.advanced_mode_size = None
        self.basic_mode_size = None
        
        # ИСПРАВЛЕНО: инициализируем виджеты как None
        self.left_panel_widget = None
        self.atrain_widget = None
        self.tag_list_widget = None
        self.main_splitter = None
        
        self.setup_ui()
        self.preset_list_widget.update_buttons_visibility(False)
        self.adjust_window_to_content()
        
        self.event_bus.subscribe('data_changed', self.on_data_changed)
        
        # Таймер для обновления Read нод
        self.read_info_timer = QtCore.QTimer()
        self.read_info_timer.timeout.connect(self.update_read_info)
        self.read_info_timer.start(1000)
    
    def setup_ui(self):
        """ИСПРАВЛЕНО: настройка UI с правильным управлением виджетами"""
        self.main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.main_layout)
        self.setStyleSheet(self.style_manager.get('window'))
        
        # Создаем только правую панель в базовом режиме
        self.create_right_panel()
        self.main_layout.addWidget(self.right_panel_widget, 1)
    
    def _ensure_left_panel_exists(self):
        """ИСПРАВЛЕНО: создать левую панель если не существует"""
        if self.left_panel_widget is None or not self._is_widget_valid(self.left_panel_widget):
            print("Creating new left panel widget")
            self.left_panel_widget = QtWidgets.QWidget()
            self.left_panel_widget.setVisible(False)
            
            left_layout = QtWidgets.QVBoxLayout()
            
            # Создаем A-Train Widget (граф)
            if self.atrain_widget is None or not self._is_widget_valid(self.atrain_widget):
                from .node_graph import ATrainWidget
                self.atrain_widget = ATrainWidget()
                self.atrain_widget.path_changed.connect(self.update_path_preview)
                self.atrain_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            
            left_layout.addWidget(self.atrain_widget, 3)
            
            # Path preview для advanced режима
            self.create_advanced_path_preview(left_layout)
            
            self.left_panel_widget.setLayout(left_layout)
    
    def _is_widget_valid(self, widget):
        """ИСПРАВЛЕНО: проверить валидность виджета"""
        try:
            if widget is None:
                return False
            widget.isVisible()
            return True
        except RuntimeError:
            return False
    
    def create_advanced_path_preview(self, layout):
        """Path preview для advanced режима"""
        preview_group = QtWidgets.QGroupBox("Path Preview")
        preview_group.setStyleSheet(self.style_manager.get('groupbox'))
        
        preview_layout = QtWidgets.QVBoxLayout()
        
        # Live preview checkbox
        preview_controls = QtWidgets.QHBoxLayout()
        
        self.live_preview_checkbox = QtWidgets.QCheckBox("Live Preview")
        self.live_preview_checkbox.setChecked(True)
        self.live_preview_checkbox.setStyleSheet("QCheckBox { color: white; font-weight: bold; }")
        self.live_preview_checkbox.toggled.connect(self.toggle_live_preview)
        preview_controls.addWidget(self.live_preview_checkbox)
        
        preview_controls.addStretch()
        
        self.preview_mode_label = QtWidgets.QLabel("Mode: Live")
        self.preview_mode_label.setStyleSheet("color: #aaa; font-size: 10px;")
        preview_controls.addWidget(self.preview_mode_label)
        
        preview_layout.addLayout(preview_controls)
        
        # Path preview label
        self.path_preview = QtWidgets.QLabel("No path")
        self.path_preview.setStyleSheet(self.style_manager.get('path_preview'))
        self.path_preview.setWordWrap(True)
        self.path_preview.setMinimumHeight(40)
        self.path_preview.setMaximumHeight(80)
        preview_layout.addWidget(self.path_preview)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group, 0)
    
    def create_right_panel(self):
        """Создание правой панели"""
        self.right_panel_widget = QtWidgets.QWidget()
        right_panel_layout = QtWidgets.QVBoxLayout()
        
        # Панель режимов
        self.create_mode_panel(right_panel_layout)
        
        # Контейнер пресетов БЕЗ верхнего поиска
        self.create_presets_container_no_search(right_panel_layout)
        
        # Path Preview для базового режима
        self.create_basic_path_preview(right_panel_layout)
        
        # Batch Operations
        self.create_batch_operations(right_panel_layout)
        
        # Clear Railway кнопка (скрыта в базовом режиме)
        self.create_clear_button(right_panel_layout)
        
        # Create Write в самом низу
        self.create_write_button(right_panel_layout)
        
        self.right_panel_widget.setLayout(right_panel_layout)
    
    def create_mode_panel(self, layout):
        """Панель переключения режимов"""
        mode_panel = QtWidgets.QGroupBox()
        mode_panel.setStyleSheet("QGroupBox { border: none; }")
        mode_layout = QtWidgets.QHBoxLayout()
        
        self.mode_info_label = QtWidgets.QLabel("Basic Mode")
        self.mode_info_label.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        mode_layout.addWidget(self.mode_info_label)
        mode_layout.addStretch()
        
        self.mode_toggle_btn = QtWidgets.QPushButton("Advanced")
        self.mode_toggle_btn.clicked.connect(self.toggle_mode)
        self.mode_toggle_btn.setStyleSheet(self.style_manager.get('mode_toggle'))
        mode_layout.addWidget(self.mode_toggle_btn)
        
        mode_panel.setLayout(mode_layout)
        layout.addWidget(mode_panel, 0)
    
    def create_presets_container_no_search(self, layout):
        """ИСПРАВЛЕНО: контейнер пресетов БЕЗ верхнего поиска"""
        self.tabs_container = QtWidgets.QGroupBox("Presets")
        self.tabs_container.setStyleSheet(self.style_manager.get('groupbox'))
        tabs_layout = QtWidgets.QVBoxLayout()
        
        # Только табы - поиск встроен в виджеты
        self.main_tabs = QtWidgets.QTabWidget()
        self.main_tabs.setStyleSheet(self.style_manager.get('tab_widget'))
        
        # PresetListWidget с собственным встроенным поиском
        self.preset_list_widget = PresetListWidget(self.preset_manager, self)
        self.preset_list_widget.preset_selected.connect(self.load_preset_data)
        self.main_tabs.addTab(self.preset_list_widget, "Presets")
        
        tabs_layout.addWidget(self.main_tabs)
        self.tabs_container.setLayout(tabs_layout)
        layout.addWidget(self.tabs_container, 1)
    
    def create_basic_path_preview(self, layout):
        """Path Preview для базового режима"""
        self.basic_preview_group = QtWidgets.QGroupBox("Path Preview")
        self.basic_preview_group.setStyleSheet(self.style_manager.get('groupbox'))
        basic_preview_layout = QtWidgets.QVBoxLayout()
        
        self.basic_path_preview = QtWidgets.QLabel("No path - load a preset")
        self.basic_path_preview.setStyleSheet(self.style_manager.get('path_preview'))
        self.basic_path_preview.setWordWrap(True)
        self.basic_path_preview.setMinimumHeight(40)
        self.basic_path_preview.setMaximumHeight(80)
        basic_preview_layout.addWidget(self.basic_path_preview)
        
        self.basic_preview_group.setLayout(basic_preview_layout)
        layout.addWidget(self.basic_preview_group, 0)
    
    def create_batch_operations(self, layout):
        """Batch operations секция"""
        self.batch_container = QtWidgets.QGroupBox("Batch Operations")
        self.batch_container.setStyleSheet(self.style_manager.get('groupbox'))
        batch_layout = QtWidgets.QVBoxLayout()
        
        self.read_info_label = QtWidgets.QLabel("No Read nodes selected")
        self.read_info_label.setStyleSheet("color: #aaa; font-size: 10px;")
        batch_layout.addWidget(self.read_info_label)
        
        transcode_btn = QtWidgets.QPushButton("Transcode Selected Reads")
        transcode_btn.clicked.connect(self.transcode_selected_reads)
        transcode_btn.setStyleSheet(self.style_manager.get('button'))
        batch_layout.addWidget(transcode_btn)
        
        self.batch_container.setLayout(batch_layout)
        layout.addWidget(self.batch_container, 0)
    
    def create_clear_button(self, layout):
        """Clear Railway кнопка"""
        self.clear_btn = QtWidgets.QPushButton("Clear Railway")
        self.clear_btn.clicked.connect(self.clear_railway)
        self.clear_btn.setStyleSheet(self.style_manager.get('button'))
        self.clear_btn.setVisible(False)
        layout.addWidget(self.clear_btn)
    
    def create_write_button(self, layout):
        """Create Write кнопка в самом низу"""
        create_write_btn = QtWidgets.QPushButton("Create Write")
        create_write_btn.clicked.connect(self.create_write_node)
        create_write_btn.setStyleSheet(self.style_manager.get('create_write'))
        layout.addWidget(create_write_btn)
    
    def toggle_mode(self):
        """ИСПРАВЛЕНО: переключение режимов без ошибок удаления виджетов"""
        if self._switching_mode:
            return
        
        self._switching_mode = True
        
        try:
            self.store_current_size()
            self.is_advanced_mode = not self.is_advanced_mode
            
            if self.is_advanced_mode:
                self.switch_to_advanced_mode()
            else:
                self.switch_to_basic_mode()
            
            self.preset_list_widget.update_buttons_visibility(self.is_advanced_mode)
            self.restore_mode_size()
            
        except Exception as e:
            print(f"Error toggling mode: {e}")
        finally:
            self._switching_mode = False
    
    def switch_to_advanced_mode(self):
        """ИСПРАВЛЕНО: переключение в advanced режим"""
        print("Switching to advanced mode")
        
        self.mode_toggle_btn.setText("Basic")
        self.mode_info_label.setText("Advanced Mode")
        self.tabs_container.setTitle("Presets & Tags")
        
        # ИСПРАВЛЕНО: убеждаемся что левая панель существует
        self._ensure_left_panel_exists()
        
        # ИСПРАВЛЕНО: создаем новый splitter если не существует или не валиден
        if self.main_splitter is None or not self._is_widget_valid(self.main_splitter):
            if hasattr(self, 'main_splitter') and self.main_splitter is not None:
                try:
                    self.main_layout.removeWidget(self.main_splitter)
                    self.main_splitter.setParent(None)
                except:
                    pass
            
            self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
            self.main_splitter.setChildrenCollapsible(False)
        
        # ИСПРАВЛЕНО: правильно управляем родителями виджетов
        try:
            self.main_layout.removeWidget(self.right_panel_widget)
            
            self.main_splitter.addWidget(self.left_panel_widget)
            self.main_splitter.addWidget(self.right_panel_widget)
            
            total_width = self.width()
            self.main_splitter.setSizes([int(total_width * 0.7), int(total_width * 0.3)])
            
            self.main_layout.addWidget(self.main_splitter, 1)
            
        except Exception as e:
            print(f"Error setting up splitter: {e}")
        
        # Показываем левую панель, скрываем basic preview
        if self._is_widget_valid(self.left_panel_widget):
            self.left_panel_widget.setVisible(True)
        
        if self._is_widget_valid(self.basic_preview_group):
            self.basic_preview_group.setVisible(False)
        
        # ИСПРАВЛЕНО: создаем TagListWidget если не существует
        if self.tag_list_widget is None or not self._is_widget_valid(self.tag_list_widget):
            self.tag_list_widget = TagListWidget(self.preset_manager)
            self.tag_list_widget.tag_selected.connect(self.add_tag)
        
        # Добавляем таб Tags если не существует
        tags_tab_exists = False
        for i in range(self.main_tabs.count()):
            if self.main_tabs.tabText(i) == "Tags":
                tags_tab_exists = True
                break
        
        if not tags_tab_exists:
            self.main_tabs.addTab(self.tag_list_widget, "Tags")
        
        # Показываем Clear кнопку
        if self._is_widget_valid(self.clear_btn):
            self.clear_btn.setVisible(True)
    
    def switch_to_basic_mode(self):
        """ИСПРАВЛЕНО: переключение в basic режим - полное удаление левой панели"""
        print("Switching to basic mode")
        
        self.mode_toggle_btn.setText("Advanced")
        self.mode_info_label.setText("Basic Mode")
        self.tabs_container.setTitle("Presets")
        
        # ИСПРАВЛЕНО: полностью удаляем splitter и левую панель
        if hasattr(self, 'main_splitter') and self.main_splitter is not None:
            try:
                # Удаляем виджеты из splitter
                if self._is_widget_valid(self.left_panel_widget):
                    self.main_splitter.removeWidget(self.left_panel_widget)
                    self.left_panel_widget.setParent(None)  # ИСПРАВЛЕНО: убираем parent
                    self.left_panel_widget = None  # ИСПРАВЛЕНО: обнуляем ссылку
                
                if self._is_widget_valid(self.right_panel_widget):
                    self.main_splitter.removeWidget(self.right_panel_widget)
                
                # Удаляем splitter
                self.main_layout.removeWidget(self.main_splitter)
                self.main_splitter.setParent(None)
                self.main_splitter = None
                
            except Exception as e:
                print(f"Error removing splitter: {e}")
        
        # ИСПРАВЛЕНО: добавляем right panel обратно в main layout
        try:
            self.main_layout.addWidget(self.right_panel_widget, 1)
        except Exception as e:
            print(f"Error adding right panel: {e}")
        
        # Показываем basic preview
        if self._is_widget_valid(self.basic_preview_group):
            self.basic_preview_group.setVisible(True)
        
        # Убираем TagListWidget
        if self.tag_list_widget is not None:
            tag_index = -1
            for i in range(self.main_tabs.count()):
                if self.main_tabs.tabText(i) == "Tags":
                    tag_index = i
                    break
            if tag_index >= 0:
                try:
                    self.main_tabs.removeTab(tag_index)
                    self.tag_list_widget = None  # ИСПРАВЛЕНО: обнуляем ссылку
                except:
                    pass
        
        # Скрываем Clear кнопку
        if self._is_widget_valid(self.clear_btn):
            self.clear_btn.setVisible(False)
    
    def store_current_size(self):
        """Сохранить размер"""
        try:
            current_size = self.size()
            if self.is_advanced_mode:
                self.advanced_mode_size = current_size
            else:
                self.basic_mode_size = current_size
        except:
            pass
    
    def restore_mode_size(self):
        """Восстановить размер"""
        try:
            if self.is_advanced_mode and self.advanced_mode_size:
                self.resize(self.advanced_mode_size)
            elif not self.is_advanced_mode and self.basic_mode_size:
                self.resize(self.basic_mode_size)
            else:
                self.adjust_window_to_content()
        except:
            self.adjust_window_to_content()
    
    def adjust_window_to_content(self):
        """Подогнать размер окна"""
        try:
            if self.is_advanced_mode:
                self.resize(1200, 800)
                self.setMinimumSize(1000, 600)
            else:
                self.resize(600, 800)
                self.setMinimumSize(500, 500)
        except:
            pass
    
    def load_preset_data(self, preset_name, preset_data):
        """Загрузка пресета"""
        self.loading_preset = True
        self.read_info_timer.stop()
        
        try:
            tag_names = preset_data.get('tags', [])
            format_type = preset_data.get('format', 'exr')
            
            if self.is_advanced_mode and self._is_widget_valid(self.atrain_widget):
                self.atrain_widget.load_preset_nodes(tag_names, format_type)
                from .node_graph import path_chain
                current_path = path_chain.get_current_path(live_preview=False)
                if self._is_widget_valid(self.path_preview):
                    self.path_preview.setText(current_path)
            else:
                from ..core.path_builder import PathBuilder
                path_builder = PathBuilder()
                
                all_tags = self.preset_manager.get_all_tags()
                for tag_name in tag_names:
                    for tag_data in all_tags:
                        if tag_data.get('name') == tag_name:
                            path_builder.add_tag(tag_data)
                            break
                
                format_tag = {
                    'name': 'format', 
                    'type': 'format', 
                    'format': format_type,
                    'padding': '%04d'
                }
                path_builder.add_tag(format_tag)
                
                basic_path = path_builder.build_path()
                if self._is_widget_valid(self.basic_path_preview):
                    self.basic_path_preview.setText(basic_path)
        
        except Exception as e:
            error_msg = f"Error loading preset: {e}"
            print(error_msg)
            if self.is_advanced_mode and self._is_widget_valid(self.path_preview):
                self.path_preview.setText("Error loading preset")
            elif self._is_widget_valid(self.basic_path_preview):
                self.basic_path_preview.setText("Error loading preset")
        finally:
            self.loading_preset = False
            self.read_info_timer.start(1000)
    
    def add_tag(self, tag_data):
        """Добавить тег в граф"""
        if self.is_advanced_mode and self._is_widget_valid(self.atrain_widget):
            self.atrain_widget.add_tag_node(tag_data)
    
    def clear_railway(self):
        """Очистить граф"""
        if self.is_advanced_mode and self._is_widget_valid(self.atrain_widget):
            self.atrain_widget.clear_all_nodes()
    
    def create_write_node(self):
        """ИСПРАВЛЕНО: создание Write ноды без уведомлений"""
        try:
            if self.is_advanced_mode and self._is_widget_valid(self.atrain_widget):
                from .node_graph import path_chain
                current_path = path_chain.get_current_path(live_preview=False)
            else:
                current_path = self.basic_path_preview.text()
            
            if current_path in ["No path - load a preset", "No path", "Error loading preset"]:
                QtWidgets.QMessageBox.information(self, "Info", "No path built - load a preset first!")
                return
            
            # Используем VersionManager
            incremented_path = VersionManager.get_next_available_version(current_path)
            
            # Создаем Write ноду
            from ..utils.quick_ops import QuickOperations
            quick_ops = QuickOperations()
            
            write_node = quick_ops.create_quick_write(
                output_path=incremented_path,
                auto_increment=False
            )
            
            if write_node:
                version_str = VersionManager.extract_version_from_path(incremented_path)
                # ИСПРАВЛЕНО: убрали уведомление, только в консоль
                print(f"Created Write node: {write_node.name()} -> {os.path.basename(incremented_path)} ({version_str})")
            else:
                QtWidgets.QMessageBox.critical(self, "Error", "Failed to create Write node")
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to create Write node: {e}")
    
    def transcode_selected_reads(self):
        """ИСПРАВЛЕНО: batch операция без уведомлений успеха"""
        try:
            from ..utils.batch_ops import BatchOperations
            batch_ops = BatchOperations()
            read_nodes = batch_ops.get_selected_read_nodes()
            
            if not read_nodes:
                QtWidgets.QMessageBox.information(self, "Info", "No Read nodes selected!")
                return
            
            if self.is_advanced_mode and self._is_widget_valid(self.atrain_widget):
                from .node_graph import path_chain
                current_path = path_chain.get_current_path(live_preview=False)
            else:
                current_path = self.basic_path_preview.text()
            
            if current_path in ["No path - load a preset", "No path", "Error loading preset"]:
                QtWidgets.QMessageBox.information(self, "Info", "No path built - load a preset first!")
                return
            
            created_writes = batch_ops.transcode_selected_reads(current_path)
            
            if created_writes:
                # ИСПРАВЛЕНО: только в консоль, убрали уведомление
                file_names = [batch_ops.get_filename_from_read(read_nodes[i]) for i in range(len(created_writes))]
                print(f"Created {len(created_writes)} Write nodes for: {', '.join(file_names[:5])}")
                if len(created_writes) > 5:
                    print(f"...and {len(created_writes)-5} more")
            else:
                QtWidgets.QMessageBox.warning(self, "Warning", "No Write nodes were created!")
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to transcode: {e}")
    
    def update_path_preview(self, path):
        """Обновление path preview"""
        if self.loading_preset:
            return
        
        if self._is_widget_valid(self.path_preview):
            if path:
                self.path_preview.setText(path)
            else:
                self.path_preview.setText("No path")
    
    def toggle_live_preview(self, enabled):
        """Live preview переключение"""
        if self._is_widget_valid(self.atrain_widget):
            self.atrain_widget.set_live_preview(enabled)
            if self._is_widget_valid(self.preview_mode_label):
                self.preview_mode_label.setText("Mode: Live" if enabled else "Mode: Static")
    
    def update_read_info(self):
        """ИСПРАВЛЕНО: показываем имена ФАЙЛОВ из Read нод"""
        if self.loading_preset:
            return
        
        try:
            from ..utils.batch_ops import BatchOperations
            batch_ops = BatchOperations()
            read_nodes = batch_ops.get_selected_read_nodes()
            
            if self._is_widget_valid(self.read_info_label):
                if read_nodes:
                    if len(read_nodes) == 1:
                        # ИСПРАВЛЕНО: показываем имя файла, а не имя ноды
                        file_name = batch_ops.get_filename_from_read(read_nodes[0])
                        self.read_info_label.setText(f"1 Read selected: {file_name}")
                    elif len(read_nodes) <= 3:
                        # ИСПРАВЛЕНО: показываем имена файлов
                        file_names = [batch_ops.get_filename_from_read(node) for node in read_nodes]
                        self.read_info_label.setText(f"{len(read_nodes)} Reads: {', '.join(file_names)}")
                    else:
                        # ИСПРАВЛЕНО: показываем первые два имени файлов
                        first_file_names = [batch_ops.get_filename_from_read(node) for node in read_nodes[:2]]
                        remaining = len(read_nodes) - 2
                        self.read_info_label.setText(f"{len(read_nodes)} Reads: {', '.join(first_file_names)}... +{remaining}")
                else:
                    self.read_info_label.setText("No Read nodes selected")
        except Exception as e:
            if self._is_widget_valid(self.read_info_label):
                self.read_info_label.setText("No Read nodes selected")
    
    def on_data_changed(self, data=None):
        """Обработчик изменений данных"""
        try:
            if hasattr(self, 'preset_list_widget') and self._is_widget_valid(self.preset_list_widget):
                self.preset_list_widget.refresh_data()
            if hasattr(self, 'tag_list_widget') and self._is_widget_valid(self.tag_list_widget):
                self.tag_list_widget.refresh_data()
        except:
            pass
    
    def closeEvent(self, event):
        """Закрытие окна"""
        try:
            self.event_bus.unsubscribe('data_changed', self.on_data_changed)
            self.read_info_timer.stop()
        except:
            pass
        event.accept()

