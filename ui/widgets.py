# atrain/ui/widgets.py
"""
UI виджеты A-Train - ИСПРАВЛЕНО: убраны уведомления, категории при сохранении
"""

import datetime
import re
from typing import Dict, List, Any, Optional
from PySide2 import QtWidgets, QtCore, QtGui

from ..core.preset_manager import PresetManager
from ..core.version_manager import VersionManager
from ..core.event_bus import EventBus
from .styles import StyleManager

class DebouncedSearchMixin:
    """Миксин для отложенного поиска"""
    
    def __init__(self):
        self.search_timer = QtCore.QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.pending_search = ""
    
    def debounced_search(self, text, delay=300):
        """Отложенный поиск с задержкой"""
        self.pending_search = text
        self.search_timer.stop()
        self.search_timer.start(delay)
    
    def perform_search(self):
        """Выполнить поиск"""
        self.filter_items(self.pending_search)
    
    def filter_items(self, text):
        """Фильтрация элементов - должен быть переопределен"""
        raise NotImplementedError("Subclasses must implement filter_items")


class BaseListWidget(QtWidgets.QWidget, DebouncedSearchMixin):
    """Базовый класс для списков"""
    
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        DebouncedSearchMixin.__init__(self)
        
        self.style_manager = StyleManager.instance()
        self.event_bus = EventBus.instance()
        
        self.current_data = {}
        self.filtered_data = {}
    
    def setup_ui(self):
        """Настройка базового UI"""
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Встроенный поиск с кнопкой очистки
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.setContentsMargins(5, 5, 5, 5)
        
        search_label = QtWidgets.QLabel("Search:")
        search_label.setStyleSheet("color: #ccc; font-size: 9pt; font-weight: bold;")
        search_layout.addWidget(search_label)
        
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Type to search...")
        self.search_field.setStyleSheet(self.style_manager.get('search_field'))
        self.search_field.textChanged.connect(self.debounced_search)
        search_layout.addWidget(self.search_field)
        
        # Кнопка очистки как крестик
        self.clear_search_btn = QtWidgets.QPushButton("✕")
        self.clear_search_btn.setMaximumWidth(20)
        self.clear_search_btn.setMaximumHeight(20)
        self.clear_search_btn.setStyleSheet(self.style_manager.get('clear_search'))
        self.clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(self.clear_search_btn)
        
        layout.addLayout(search_layout)
        
        # Scroll area для дерева
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(self.style_manager.get('scroll_area'))
        
        # Дерево
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet(self.style_manager.get('tree'))
        self.tree.itemDoubleClicked.connect(self.on_item_activated)
        
        scroll_area.setWidget(self.tree)
        layout.addWidget(scroll_area)
        
        self.setLayout(layout)
    
    def clear_search(self):
        """Очистить поиск"""
        self.search_field.clear()
        self.pending_search = ""
        self.filter_items("")
    
    def set_search_text(self, text):
        """Установить текст поиска"""
        self.search_field.setText(text)
        self.debounced_search(text)
    
    def on_item_activated(self, item, column):
        """Обработчик активации элемента - должен быть переопределен"""
        pass


class TagListWidget(BaseListWidget):
    """Виджет списка тегов - ИСПРАВЛЕНО: убраны уведомления"""
    
    tag_selected = QtCore.Signal(dict)
    
    def __init__(self, preset_manager, parent=None):
        super().__init__(parent)
        self.preset_manager = preset_manager
        
        self.setup_ui()
        self.create_buttons()
        self.refresh_data()
        
        self.event_bus.subscribe('data_changed', self.refresh_data)
    
    def force_refresh(self):
        """Принудительное обновление"""
        self.preset_manager.cache.invalidate()
        self.refresh_data()
        QtCore.QTimer.singleShot(100, self.refresh_data)
    
    def refresh_data(self, data=None):
        """Обновление данных тегов"""
        tags = self.preset_manager.get_all_tags_grouped()
        self.current_data = tags
        self.filter_items("")
    
    def filter_items(self, search_text):
        """Фильтрация тегов"""
        if not search_text:
            self.filtered_data = self.current_data
        else:
            self.filtered_data = {}
            for group, tags in self.current_data.items():
                filtered_tags = []
                for t in tags:
                    if (search_text.lower() in t['name'].lower() or 
                        search_text.lower() in str(t.get('default', '')).lower()):
                        filtered_tags.append(t)
                if filtered_tags:
                    self.filtered_data[group] = filtered_tags
        
        self.populate_tree()
    
    def populate_tree(self):
        """Заполнение дерева тегов"""
        self.tree.clear()
        search_active = bool(self.pending_search.strip())
        
        for group_name, tags in self.filtered_data.items():
            if search_active and not tags:
                continue
            
            if search_active:
                # Плоский список при поиске
                for tag in tags:
                    item = QtWidgets.QTreeWidgetItem()
                    preview = self.get_tag_preview(tag)
                    display_text = f"[{group_name}] {tag['name']}"
                    if preview and preview != tag['name']:
                        display_text += f" → {preview}"
                    
                    item.setText(0, display_text)
                    item.setData(0, QtCore.Qt.UserRole, tag)
                    
                    color = self.get_tag_color(tag)
                    item.setForeground(0, QtGui.QBrush(color))
                    
                    self.tree.addTopLevelItem(item)
            else:
                # Группированный список
                group_item = QtWidgets.QTreeWidgetItem([f"{group_name} ({len(tags)})"])
                group_item.setExpanded(True)
                
                font = group_item.font(0)
                font.setBold(True)
                group_item.setFont(0, font)
                
                if not tags:
                    empty_item = QtWidgets.QTreeWidgetItem(["(empty)"])
                    empty_item.setForeground(0, QtGui.QBrush(QtGui.QColor(128, 128, 128)))
                    font = empty_item.font(0)
                    font.setItalic(True)
                    empty_item.setFont(0, font)
                    empty_item.setFlags(QtCore.Qt.NoItemFlags)
                    group_item.addChild(empty_item)
                else:
                    for tag in tags:
                        child_item = QtWidgets.QTreeWidgetItem()
                        preview = self.get_tag_preview(tag)
                        display_text = tag['name']
                        if preview and preview != tag['name']:
                            display_text += f" → {preview}"
                        
                        child_item.setText(0, display_text)
                        child_item.setData(0, QtCore.Qt.UserRole, tag)
                        
                        color = self.get_tag_color(tag)
                        child_item.setForeground(0, QtGui.QBrush(color))
                        
                        group_item.addChild(child_item)
                
                self.tree.addTopLevelItem(group_item)
    
    def create_buttons(self):
        """Создание кнопок управления"""
        self.buttons_container = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setSpacing(5)
        
        self.add_tag_btn = QtWidgets.QPushButton("Add Tag")
        self.add_tag_btn.clicked.connect(self.add_tag_direct)
        self.add_tag_btn.setStyleSheet(self.style_manager.get('button'))
        grid_layout.addWidget(self.add_tag_btn, 0, 0)
        
        self.category_manager_btn = QtWidgets.QPushButton("Categories")
        self.category_manager_btn.clicked.connect(self.manage_tag_categories)
        self.category_manager_btn.setStyleSheet(self.style_manager.get('button'))
        grid_layout.addWidget(self.category_manager_btn, 0, 1)
        
        self.edit_tag_btn = QtWidgets.QPushButton("Edit")
        self.edit_tag_btn.clicked.connect(self.edit_selected_tag)
        self.edit_tag_btn.setStyleSheet(self.style_manager.get('button'))
        grid_layout.addWidget(self.edit_tag_btn, 1, 0)
        
        self.delete_tag_btn = QtWidgets.QPushButton("Delete")
        self.delete_tag_btn.clicked.connect(self.delete_selected_tag)
        self.delete_tag_btn.setStyleSheet(self.style_manager.get('button'))
        grid_layout.addWidget(self.delete_tag_btn, 1, 1)
        
        self.buttons_container.setLayout(grid_layout)
        self.layout().addWidget(self.buttons_container)
    
    def get_tag_preview(self, tag):
        """Получить превью тега"""
        tag_type = tag.get('type', 'text')
        
        if tag_type == 'expression':
            value = str(tag.get('expression', ''))
            return value[:20] + "..." if len(value) > 20 else value
        else:
            value = str(tag.get('default', ''))
            return value[:20] + "..." if len(value) > 20 else value
    
    def get_tag_color(self, tag):
        """Получить цвет тега по типу"""
        colors = {
            'dynamic': QtGui.QColor(180, 200, 140),
            'version': QtGui.QColor(140, 180, 200),
            'separator': QtGui.QColor(160, 140, 200),
            'format': QtGui.QColor(200, 140, 140),
            'expression': QtGui.QColor(140, 200, 180),
            'text': QtGui.QColor(200, 180, 140)
        }
        return colors.get(tag.get('type', 'text'), QtGui.QColor(200, 180, 140))
    
    def on_item_activated(self, item, column):
        """Обработчик активации тега"""
        tag_data = item.data(0, QtCore.Qt.UserRole)
        if tag_data:
            self.tag_selected.emit(tag_data)
    
    def add_tag_direct(self):
        """ИСПРАВЛЕНО: убраны уведомления об успехе"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Add Tag")
        dialog.setModal(True)
        dialog.resize(350, 400)
        
        layout = QtWidgets.QVBoxLayout()
        
        # Имя тега
        name_layout = QtWidgets.QHBoxLayout()
        name_layout.addWidget(QtWidgets.QLabel("Name:"))
        name_edit = QtWidgets.QLineEdit()
        name_edit.setStyleSheet(self.style_manager.get('search_field'))
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)
        
        # Категория
        category_layout = QtWidgets.QHBoxLayout()
        category_layout.addWidget(QtWidgets.QLabel("Category:"))
        category_combo = QtWidgets.QComboBox()
        categories = self.preset_manager.get_tag_categories()
        category_combo.addItems(categories)
        category_combo.setStyleSheet(self.style_manager.get('button'))
        category_layout.addWidget(category_combo)
        layout.addLayout(category_layout)
        
        # Тип
        type_layout = QtWidgets.QHBoxLayout()
        type_layout.addWidget(QtWidgets.QLabel("Type:"))
        type_combo = QtWidgets.QComboBox()
        type_combo.addItems(['text', 'expression'])
        type_combo.setStyleSheet(self.style_manager.get('button'))
        type_layout.addWidget(type_combo)
        layout.addLayout(type_layout)
        
        # Значение/выражение
        default_layout = QtWidgets.QVBoxLayout()
        default_label = QtWidgets.QLabel("Default:")
        default_layout.addWidget(default_label)
        
        # Поле для текста
        default_edit = QtWidgets.QLineEdit()
        default_edit.setStyleSheet(self.style_manager.get('search_field'))
        default_layout.addWidget(default_edit)
        
        # Поле для выражения
        expr_edit = QtWidgets.QTextEdit()
        expr_edit.setStyleSheet(self.style_manager.get('path_preview'))
        expr_edit.setMaximumHeight(80)
        expr_edit.setPlainText("[value root.frame]")
        expr_edit.setVisible(False)
        default_layout.addWidget(expr_edit)
        
        # Примеры для выражений
        examples_label = QtWidgets.QLabel(
            "Examples:\n"
            "[value root.frame] - current frame\n"
            "[value root.first_frame] - first frame\n"
            "[file rootname [value root.name]] - script name"
        )
        examples_label.setStyleSheet("color: #aaa; font-size: 10px;")
        examples_label.setVisible(False)
        default_layout.addWidget(examples_label)
        
        layout.addLayout(default_layout)
        
        def on_type_changed():
            is_expression = type_combo.currentText() == 'expression'
            default_label.setText("Expression:" if is_expression else "Default:")
            default_edit.setVisible(not is_expression)
            expr_edit.setVisible(is_expression)
            examples_label.setVisible(is_expression)
        
        type_combo.currentTextChanged.connect(on_type_changed)
        
        # Кнопки
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.setStyleSheet(self.style_manager.get('button'))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            name = name_edit.text().strip()
            category = category_combo.currentText()
            tag_type = type_combo.currentText()
            
            if tag_type == 'expression':
                expression_value = expr_edit.toPlainText().strip()
                default_value = ""
            else:
                default_value = default_edit.text().strip()
                expression_value = ""
            
            if name:
                try:
                    if tag_type == 'expression':
                        tag_data = {
                            'name': name,
                            'type': 'expression',
                            'category': category,
                            'expression': expression_value
                        }
                        
                        custom = self.preset_manager.load_custom()
                        custom_expression_tags = custom.get('custom_expression_tags', [])
                        custom_expression_tags.append(tag_data)
                        custom['custom_expression_tags'] = custom_expression_tags
                        self.preset_manager.save_custom(custom)
                    else:
                        tag_data = {
                            'name': name,
                            'type': 'text',
                            'category': category,
                            'default': default_value
                        }
                        self.preset_manager.add_custom_tag(tag_data)
                    
                    print(f"Added {tag_type} tag: {name}")  # ИСПРАВЛЕНО: только в консоль
                    self.force_refresh()
                    # ИСПРАВЛЕНО: убрали уведомление
                    
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Error", f"Failed to add tag: {e}")
    
    def manage_tag_categories(self):
        """Управление категориями тегов"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Tag Category Manager")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QtWidgets.QVBoxLayout()
        
        list_widget = QtWidgets.QListWidget()
        list_widget.setStyleSheet(self.style_manager.get('tree'))
        
        categories = self.preset_manager.get_tag_categories()
        for category in categories:
            list_widget.addItem(category)
        
        layout.addWidget(list_widget)
        
        buttons_layout = QtWidgets.QHBoxLayout()
        
        add_btn = QtWidgets.QPushButton("Add")
        add_btn.setStyleSheet(self.style_manager.get('button'))
        add_btn.clicked.connect(lambda: self.add_category(list_widget, 'tag'))
        buttons_layout.addWidget(add_btn)
        
        edit_btn = QtWidgets.QPushButton("Edit")
        edit_btn.setStyleSheet(self.style_manager.get('button'))
        edit_btn.clicked.connect(lambda: self.edit_category(list_widget, 'tag'))
        buttons_layout.addWidget(edit_btn)
        
        delete_btn = QtWidgets.QPushButton("Delete")
        delete_btn.setStyleSheet(self.style_manager.get('button'))
        delete_btn.clicked.connect(lambda: self.delete_category(list_widget, 'tag'))
        buttons_layout.addWidget(delete_btn)
        
        layout.addLayout(buttons_layout)
        
        dialog_buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        dialog_buttons.setStyleSheet(self.style_manager.get('button'))
        dialog_buttons.rejected.connect(dialog.reject)
        layout.addWidget(dialog_buttons)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def add_category(self, list_widget, category_type):
        """Добавление категории"""
        name, ok = QtWidgets.QInputDialog.getText(self, "Add Category", "Category name:")
        if ok and name.strip():
            name = name.strip()
            list_widget.addItem(name)
            self.save_categories(list_widget, category_type)
            self.force_refresh()
    
    def edit_category(self, list_widget, category_type):
        """Редактирование категории"""
        current_item = list_widget.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.information(self, "Info", "Select a category to edit")
            return
        
        current_name = current_item.text()
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "Edit Category", "Category name:", text=current_name
        )
        if ok and new_name.strip():
            current_item.setText(new_name.strip())
            self.save_categories(list_widget, category_type)
            self.force_refresh()
    
    def delete_category(self, list_widget, category_type):
        """Удаление категории"""
        current_item = list_widget.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.information(self, "Info", "Select a category to delete")
            return
        
        category_name = current_item.text()
        if category_name == 'General':
            QtWidgets.QMessageBox.warning(self, "Warning", "Cannot delete 'General' category")
            return
        
        reply = QtWidgets.QMessageBox.question(
            self, "Delete Category", 
            f"Delete category '{category_name}'?\n"
            f"All items in this category will be moved to 'General'.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            row = list_widget.row(current_item)
            list_widget.takeItem(row)
            self.save_categories(list_widget, category_type)
            self.preset_manager.move_items_to_general_category(category_name, category_type)
            self.force_refresh()
    
    def save_categories(self, list_widget, category_type):
        """Сохранение категорий"""
        categories = []
        for i in range(list_widget.count()):
            categories.append(list_widget.item(i).text())
        
        if 'General' not in categories:
            categories.insert(0, 'General')
        
        if category_type == 'tag':
            self.preset_manager.save_tag_categories(categories)
        else:
            self.preset_manager.save_preset_categories(categories)
    
    def edit_selected_tag(self):
        """Редактирование выбранного тега"""
        selected = self.tree.selectedItems()
        if not selected:
            QtWidgets.QMessageBox.information(self, "Info", "Select a tag to edit")
            return
        
        tag_data = selected[0].data(0, QtCore.Qt.UserRole)
        if not tag_data:
            return
        
        if tag_data.get('source') != 'custom':
            QtWidgets.QMessageBox.information(self, "Info", "Only custom tags can be edited")
            return
        
        # Простое редактирование - только показываем информацию
        tag_name = tag_data.get('name', '')
        tag_type = tag_data.get('type', 'text')
        QtWidgets.QMessageBox.information(
            self, "Tag Info", 
            f"Tag: {tag_name}\nType: {tag_type}\n\nUse 'Delete' and 'Add Tag' to modify tags."
        )
    
    def delete_selected_tag(self):
        """ИСПРАВЛЕНО: убраны уведомления об успехе"""
        selected = self.tree.selectedItems()
        if not selected:
            QtWidgets.QMessageBox.information(self, "Info", "Select a tag to delete")
            return
        
        tag_data = selected[0].data(0, QtCore.Qt.UserRole)
        if not tag_data:
            return
        
        if tag_data.get('source') != 'custom':
            QtWidgets.QMessageBox.information(self, "Info", "Only custom tags can be deleted")
            return
        
        tag_name = tag_data.get('name', '')
        reply = QtWidgets.QMessageBox.question(
            self, "Delete Tag", 
            f"Delete tag '{tag_name}'?\n\nThis action cannot be undone.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                custom = self.preset_manager.load_custom()
                tag_type = tag_data.get('type', 'text')
                
                if tag_type == 'expression':
                    custom_tags = custom.get('custom_expression_tags', [])
                    custom['custom_expression_tags'] = [
                        tag for tag in custom_tags if tag.get('name') != tag_name
                    ]
                else:
                    custom_tags = custom.get('custom_tags', [])
                    custom['custom_tags'] = [
                        tag for tag in custom_tags if tag.get('name') != tag_name
                    ]
                
                self.preset_manager.save_custom(custom)
                self.force_refresh()
                
                print(f"Tag '{tag_name}' deleted successfully")  # ИСПРАВЛЕНО: только в консоль
                # ИСПРАВЛЕНО: убрали уведомление
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to delete tag: {e}")


class PresetListWidget(BaseListWidget):
    """Виджет списка пресетов - ИСПРАВЛЕНО: категория при сохранении"""
    
    preset_selected = QtCore.Signal(str, dict)
    
    def __init__(self, preset_manager, parent_window, parent=None):
        super().__init__(parent)
        self.preset_manager = preset_manager
        self.parent_window = parent_window
        
        self.setup_ui()
        self.create_buttons()
        self.refresh_data()
        
        self.event_bus.subscribe('data_changed', self.refresh_data)
    
    def refresh_data(self, data=None):
        """Обновление данных пресетов"""
        presets = self.preset_manager.get_all_presets_grouped()
        self.current_data = presets
        self.filter_items("")
    
    def filter_items(self, search_text):
        """Фильтрация пресетов"""
        if not search_text:
            self.filtered_data = self.current_data
        else:
            self.filtered_data = {}
            for group, presets in self.current_data.items():
                filtered_presets = []
                for preset in presets:
                    name_match = search_text.lower() in preset.get('name', '').lower()
                    format_match = search_text.lower() in preset.get('format', '').lower()
                    tags_match = search_text.lower() in ' '.join(preset['data'].get('tags', [])).lower()
                    
                    if name_match or format_match or tags_match:
                        filtered_presets.append(preset)
                
                if filtered_presets:
                    self.filtered_data[group] = filtered_presets
        
        self.populate_tree()
    
    def populate_tree(self):
        """Заполнение дерева пресетов"""
        self.tree.clear()
        search_active = bool(self.pending_search.strip())
        
        for group_name, presets in self.filtered_data.items():
            if search_active and not presets:
                continue
            
            if search_active:
                # Плоский список при поиске
                for preset in presets:
                    item = QtWidgets.QTreeWidgetItem()
                    name = preset.get('name', 'Unknown')
                    tags_count = preset.get('tags_count', 0)
                    format_type = preset.get('format', 'exr')
                    
                    display_text = f"[{group_name}] {name} ({tags_count} tags, {format_type})"
                    item.setText(0, display_text)
                    item.setData(0, QtCore.Qt.UserRole, preset)
                    
                    color = self.get_preset_color(preset)
                    item.setForeground(0, QtGui.QBrush(color))
                    
                    self.tree.addTopLevelItem(item)
            else:
                # Группированный список
                group_item = QtWidgets.QTreeWidgetItem([f"{group_name} ({len(presets)})"])
                group_item.setExpanded(True)
                
                font = group_item.font(0)
                font.setBold(True)
                group_item.setFont(0, font)
                
                for preset in presets:
                    child_item = QtWidgets.QTreeWidgetItem()
                    name = preset.get('name', 'Unknown')
                    tags_count = preset.get('tags_count', 0)
                    format_type = preset.get('format', 'exr')
                    
                    display_text = f"{name} ({tags_count} tags, {format_type})"
                    child_item.setText(0, display_text)
                    child_item.setData(0, QtCore.Qt.UserRole, preset)
                    
                    color = self.get_preset_color(preset)
                    child_item.setForeground(0, QtGui.QBrush(color))
                    
                    group_item.addChild(child_item)
                
                self.tree.addTopLevelItem(group_item)
    
    def get_preset_color(self, preset):
        """Получить цвет пресета"""
        if preset.get('source') == 'default':
            return QtGui.QColor(150, 150, 200)
        else:
            return QtGui.QColor(200, 200, 140)
    
    def on_item_activated(self, item, column):
        """Обработчик активации пресета"""
        preset_data = item.data(0, QtCore.Qt.UserRole)
        if preset_data:
            name = preset_data.get('name', '')
            data = preset_data.get('data', {})
            self.preset_selected.emit(name, data)
    
    def create_buttons(self):
        """Создание кнопок управления"""
        self.buttons_container = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setSpacing(5)
        
        self.save_btn = QtWidgets.QPushButton("Save Current Preset")
        self.save_btn.clicked.connect(self.save_current_preset)
        self.save_btn.setStyleSheet(self.style_manager.get('button'))
        grid_layout.addWidget(self.save_btn, 0, 0)
        
        self.category_manager_btn = QtWidgets.QPushButton("Categories")
        self.category_manager_btn.clicked.connect(self.manage_preset_categories)
        self.category_manager_btn.setStyleSheet(self.style_manager.get('button'))
        grid_layout.addWidget(self.category_manager_btn, 0, 1)
        
        self.edit_btn = QtWidgets.QPushButton("Edit")
        self.edit_btn.clicked.connect(self.edit_selected_preset)
        self.edit_btn.setStyleSheet(self.style_manager.get('button'))
        grid_layout.addWidget(self.edit_btn, 1, 0)
        
        self.delete_btn = QtWidgets.QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_selected_preset)
        self.delete_btn.setStyleSheet(self.style_manager.get('button'))
        grid_layout.addWidget(self.delete_btn, 1, 1)
        
        self.buttons_container.setLayout(grid_layout)
        self.layout().addWidget(self.buttons_container)
    
    def save_current_preset(self):
        """ИСПРАВЛЕНО: сохранение пресета с выбором категории"""
        # Диалог с именем и категорией
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Save Preset")
        dialog.setModal(True)
        dialog.resize(300, 150)
        
        layout = QtWidgets.QVBoxLayout()
        
        # Имя пресета
        name_layout = QtWidgets.QHBoxLayout()
        name_layout.addWidget(QtWidgets.QLabel("Name:"))
        name_edit = QtWidgets.QLineEdit()
        name_edit.setStyleSheet(self.style_manager.get('search_field'))
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)
        
        # ИСПРАВЛЕНО: выбор категории
        category_layout = QtWidgets.QHBoxLayout()
        category_layout.addWidget(QtWidgets.QLabel("Category:"))
        category_combo = QtWidgets.QComboBox()
        categories = self.preset_manager.get_preset_categories()
        category_combo.addItems(categories)
        category_combo.setCurrentText("General")  # По умолчанию General
        category_combo.setStyleSheet(self.style_manager.get('button'))
        category_layout.addWidget(category_combo)
        layout.addLayout(category_layout)
        
        # Кнопки
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.setStyleSheet(self.style_manager.get('button'))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            name = name_edit.text().strip()
            category = category_combo.currentText()  # ИСПРАВЛЕНО: получаем выбранную категорию
            
            if name:
                current_tags = []
                format_type = "exr"
                
                # Получаем теги из графа если в advanced режиме
                if self.parent_window and self.parent_window.is_advanced_mode:
                    from .node_graph import path_chain
                    for node in path_chain.tag_nodes:
                        if node.tag_data.get('type') == 'format':
                            format_type = node.tag_data.get('format', 'exr')
                        elif node.tag_data.get('type') != 'format':
                            current_tags.append(node.tag_data.get('name', ''))
                
                try:
                    # ИСПРАВЛЕНО: передаем выбранную категорию
                    self.preset_manager.save_custom_preset(name, current_tags, format_type, category)
                    self.refresh_data()
                    
                    # ИСПРАВЛЕНО: убрали уведомление
                    print(f"PresetListWidget: Preset '{name}' saved in category '{category}'")
                    
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save preset: {e}")
    
    def manage_preset_categories(self):
        """Управление категориями пресетов - аналогично тегам"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Preset Category Manager")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QtWidgets.QVBoxLayout()
        
        list_widget = QtWidgets.QListWidget()
        list_widget.setStyleSheet(self.style_manager.get('tree'))
        
        categories = self.preset_manager.get_preset_categories()
        for category in categories:
            list_widget.addItem(category)
        
        layout.addWidget(list_widget)
        
        buttons_layout = QtWidgets.QHBoxLayout()
        
        add_btn = QtWidgets.QPushButton("Add")
        add_btn.setStyleSheet(self.style_manager.get('button'))
        add_btn.clicked.connect(lambda: self.add_category(list_widget, 'preset'))
        buttons_layout.addWidget(add_btn)
        
        edit_btn = QtWidgets.QPushButton("Edit")
        edit_btn.setStyleSheet(self.style_manager.get('button'))
        edit_btn.clicked.connect(lambda: self.edit_category(list_widget, 'preset'))
        buttons_layout.addWidget(edit_btn)
        
        delete_btn = QtWidgets.QPushButton("Delete")
        delete_btn.setStyleSheet(self.style_manager.get('button'))
        delete_btn.clicked.connect(lambda: self.delete_category(list_widget, 'preset'))
        buttons_layout.addWidget(delete_btn)
        
        layout.addLayout(buttons_layout)
        
        dialog_buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        dialog_buttons.setStyleSheet(self.style_manager.get('button'))
        dialog_buttons.rejected.connect(dialog.reject)
        layout.addWidget(dialog_buttons)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def add_category(self, list_widget, category_type):
        """Добавление категории пресета"""
        name, ok = QtWidgets.QInputDialog.getText(self, "Add Category", "Category name:")
        if ok and name.strip():
            name = name.strip()
            list_widget.addItem(name)
            self.save_categories(list_widget, category_type)
            self.refresh_data()
    
    def edit_category(self, list_widget, category_type):
        """Редактирование категории пресета"""
        current_item = list_widget.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.information(self, "Info", "Select a category to edit")
            return
        
        current_name = current_item.text()
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "Edit Category", "Category name:", text=current_name
        )
        if ok and new_name.strip():
            current_item.setText(new_name.strip())
            self.save_categories(list_widget, category_type)
            self.refresh_data()
    
    def delete_category(self, list_widget, category_type):
        """Удаление категории пресета"""
        current_item = list_widget.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.information(self, "Info", "Select a category to delete")
            return
        
        category_name = current_item.text()
        if category_name == 'General':
            QtWidgets.QMessageBox.warning(self, "Warning", "Cannot delete 'General' category")
            return
        
        reply = QtWidgets.QMessageBox.question(
            self, "Delete Category", 
            f"Delete category '{category_name}'?\n"
            f"All presets in this category will be moved to 'General'.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            row = list_widget.row(current_item)
            list_widget.takeItem(row)
            self.save_categories(list_widget, category_type)
            self.preset_manager.move_items_to_general_category(category_name, category_type)
            self.refresh_data()
    
    def save_categories(self, list_widget, category_type):
        """Сохранение категорий пресетов"""
        categories = []
        for i in range(list_widget.count()):
            categories.append(list_widget.item(i).text())
        
        if 'General' not in categories:
            categories.insert(0, 'General')
        
        if category_type == 'preset':
            self.preset_manager.save_preset_categories(categories)
        else:
            self.preset_manager.save_tag_categories(categories)
    
    def edit_selected_preset(self):
        """Редактирование выбранного пресета"""
        selected = self.tree.selectedItems()
        if not selected:
            QtWidgets.QMessageBox.information(self, "Info", "Select a preset to edit")
            return
        
        preset_data = selected[0].data(0, QtCore.Qt.UserRole)
        if not preset_data or preset_data.get('source') != 'custom':
            QtWidgets.QMessageBox.information(self, "Info", "Only custom presets can be edited")
            return
        
        # Простое редактирование категории
        current_category = preset_data.get('category', 'General')
        categories = self.preset_manager.get_preset_categories()
        
        category, ok = QtWidgets.QInputDialog.getItem(
            self, "Edit Preset Category", 
            f"Category for '{preset_data.get('name', '')}':",
            categories, categories.index(current_category) if current_category in categories else 0
        )
        
        if ok and category != current_category:
            try:
                custom = self.preset_manager.load_custom()
                preset_name = preset_data.get('name')
                if preset_name in custom.get('custom_presets', {}):
                    custom['custom_presets'][preset_name]['category'] = category
                    self.preset_manager.save_custom(custom)
                    self.refresh_data()
                    print(f"Updated preset category: {preset_name} → {category}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to update preset: {e}")
    
    def delete_selected_preset(self):
        """ИСПРАВЛЕНО: убраны уведомления об успехе"""
        selected = self.tree.selectedItems()
        if not selected:
            QtWidgets.QMessageBox.information(self, "Info", "Select a preset to delete")
            return
        
        preset_data = selected[0].data(0, QtCore.Qt.UserRole)
        if not preset_data or preset_data.get('source') != 'custom':
            QtWidgets.QMessageBox.information(self, "Info", "Only custom presets can be deleted")
            return
        
        preset_name = preset_data.get('name', '')
        reply = QtWidgets.QMessageBox.question(
            self, "Delete Preset", 
            f"Delete preset '{preset_name}'?\n\nThis action cannot be undone.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                self.preset_manager.delete_custom_preset(preset_name)
                self.refresh_data()
                print(f"Preset '{preset_name}' deleted successfully")  # ИСПРАВЛЕНО: только в консоль
                # ИСПРАВЛЕНО: убрали уведомление
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to delete preset: {e}")
    
    def update_buttons_visibility(self, visible):
        """Обновить видимость кнопок"""
        self.buttons_container.setVisible(visible)
