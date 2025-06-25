# atrain/ui/node_graph.py
"""
Нод граф A-Train - ИСПРАВЛЕНО: железнодорожная тема, scroll bars, padding %04d
"""

import os
from typing import List, Dict, Any, Optional
from PySide2 import QtWidgets, QtCore, QtGui

from ..core.path_builder import PathBuilder
from ..core.event_bus import EventBus

class PathChain:
    """Управление цепочкой тегов на железной дороге"""
    
    def __init__(self):
        self.tag_nodes = []
        
        # ИСПРАВЛЕНО: константы железной дороги
        self.fixed_spacing = 180
        self.rail_center_y = 200
        self.start_x = 150
        self.rail_height = 80
        self.deadend_x = 50
        
        self._path_builder = None
        self._event_bus = None
    
    @property
    def path_builder(self):
        if self._path_builder is None:
            self._path_builder = PathBuilder()
        return self._path_builder
    
    @property 
    def event_bus(self):
        if self._event_bus is None:
            self._event_bus = EventBus.instance()
        return self._event_bus
    
    def add_tag_node_to_end(self, tag_node):
        """Добавить ноду в конец цепочки"""
        if tag_node not in self.tag_nodes:
            # Format ноды всегда в конце
            if tag_node.tag_data.get('type') == 'format':
                self._remove_format_nodes()
                self.tag_nodes.append(tag_node)
                self.path_builder.add_tag(tag_node.tag_data)
            else:
                # Обычные ноды перед format нодами
                format_index = self._find_format_index()
                if format_index >= 0:
                    self.tag_nodes.insert(format_index, tag_node)
                    self.path_builder.tags.insert(format_index, tag_node.tag_data)
                else:
                    self.tag_nodes.append(tag_node)
                    self.path_builder.add_tag(tag_node.tag_data)
            
            self._reposition_all_nodes()
            self._publish_chain_change()
    
    def insert_tag_node_at_position(self, tag_node, insert_index):
        """Вставить ноду в определенную позицию"""
        if tag_node not in self.tag_nodes:
            if tag_node.tag_data.get('type') == 'format':
                self.add_tag_node_to_end(tag_node)
                return
            
            format_index = self._find_format_index()
            max_index = format_index if format_index >= 0 else len(self.tag_nodes)
            insert_index = max(0, min(insert_index, max_index))
            
            self.tag_nodes.insert(insert_index, tag_node)
            self.path_builder.tags.insert(insert_index, tag_node.tag_data)
            
            self._reposition_all_nodes()
            self._publish_chain_change()
    
    def remove_tag_node(self, tag_node):
        """Удалить ноду из цепочки"""
        if tag_node in self.tag_nodes:
            index = self.tag_nodes.index(tag_node)
            self.tag_nodes.remove(tag_node)
            self.path_builder.remove_tag(index)
            
            self._reposition_all_nodes()
            self._publish_chain_change()
    
    def find_insert_position(self, x_coordinate):
        """Найти позицию для вставки по X координате"""
        if x_coordinate < self.start_x:
            return 0
        
        for i, tag_node in enumerate(self.tag_nodes):
            if x_coordinate < tag_node.pos().x():
                return i
        
        return len(self.tag_nodes)
    
    def _find_format_index(self):
        """Найти индекс format ноды"""
        for i, node in enumerate(self.tag_nodes):
            if node.tag_data.get('type') == 'format':
                return i
        return -1
    
    def _remove_format_nodes(self):
        """Удалить все format ноды"""
        format_nodes = [node for node in self.tag_nodes if node.tag_data.get('type') == 'format']
        for node in format_nodes:
            self.remove_tag_node(node)
    
    def _reposition_all_nodes(self):
        """Переместить все ноды на правильные позиции"""
        for i, tag_node in enumerate(self.tag_nodes):
            new_x = self.start_x + i * self.fixed_spacing
            new_y = self.rail_center_y - tag_node.height / 2
            tag_node.setPos(new_x, new_y)
            tag_node.update_visual_state()
    
    def _publish_chain_change(self):
        """Публиковать событие изменения цепочки"""
        current_path = self.get_current_path()
        self.event_bus.publish('path_chain_changed', {
            'nodes_count': len(self.tag_nodes),
            'current_path': current_path
        })
    
    def get_tag_node_index(self, tag_node):
        """Получить индекс ноды"""
        return self.tag_nodes.index(tag_node) if tag_node in self.tag_nodes else -1
    
    def is_empty(self):
        """Проверить пустая ли цепочка"""
        return len(self.tag_nodes) == 0
    
    def clear(self):
        """Очистить цепочку"""
        self.tag_nodes.clear()
        self.path_builder.clear_tags()
        self._publish_chain_change()
    
    def get_rail_zone_rect(self, scene_width):
        """Получить прямоугольник зоны рельсов"""
        return QtCore.QRectF(
            self.start_x - 50, 
            self.rail_center_y - self.rail_height / 2,
            scene_width, 
            self.rail_height
        )
    
    def get_current_path(self, live_preview=False):
        """ИСПРАВЛЕНО: получить текущий путь с правильным padding"""
        try:
            return self.path_builder.build_path(live_preview=live_preview)
        except Exception as e:
            print(f"PathChain: Error building path: {e}")
            return ""


class TagNode(QtWidgets.QGraphicsItem):
    """Графическая нода тега с железнодорожной темой"""
    
    def __init__(self, tag_data, x=0, y=0):
        super().__init__()
        
        self.tag_data = tag_data.copy()
        
        # Размеры ноды
        self.width = 140
        self.height = 80
        
        # Состояние drag&drop
        self.is_being_dragged = False
        self.drag_start_scene_pos = None
        self.drag_start_item_pos = None
        self.was_in_chain = False
        self.click_threshold = 5
        self.mouse_press_scene_pos = None
        self.group_drag_offsets = {}
        
        # Кеш для значений
        self._cached_value = None
        self._cache_timestamp = 0
        
        # ИСПРАВЛЕНО: цвета из стилей для разных типов
        from .styles import StyleManager
        style_manager = StyleManager.instance()
        node_colors = style_manager.get_node_colors()
        
        self.rail_colors = {
            'separator': QtGui.QColor(node_colors['separator']),
            'format': QtGui.QColor(node_colors['format']),
            'version': QtGui.QColor(node_colors['version']),
            'dynamic': QtGui.QColor(node_colors['dynamic']),
            'expression': QtGui.QColor(node_colors['expression']),
            'text': QtGui.QColor(node_colors['text']),
            'default': QtGui.QColor(node_colors['text'])
        }
        
        # Настройки графического элемента
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        
        self.setPos(x, y)
    
    def get_display_name(self):
        """Получить отображаемое имя"""
        return self.tag_data.get('name', 'Unknown')
    
    def get_tag_value(self):
        """Получить значение тега"""
        tag_type = self.tag_data.get('type', 'text')
        
        if tag_type == 'separator':
            return self.tag_data.get('value', '/')
        elif tag_type == 'format':
            return self.tag_data.get('format', 'exr')
        elif tag_type == 'version':
            return self.tag_data.get('version', 'v01')
        elif tag_type == 'dynamic':
            try:
                return path_chain.path_builder._get_dynamic_value(self.tag_data)
            except:
                return self.tag_data.get('default', 'dynamic')
        elif tag_type == 'expression':
            try:
                expression = self.tag_data.get('expression', '')
                return path_chain.path_builder._evaluate_expression_live(expression)
            except:
                return self.tag_data.get('expression', 'expr')
        else:
            value = self.tag_data.get('default', '')
            if value == '[read_name]':
                try:
                    return path_chain.path_builder._get_read_name()
                except:
                    return 'read_name'
            return value
    
    def boundingRect(self):
        """Границы элемента"""
        return QtCore.QRectF(0, 0, self.width, self.height)
    
    def paint(self, painter, option, widget):
        """ИСПРАВЛЕНО: отрисовка ноды точно как в оригинале"""
        rect = self.boundingRect()
        tag_type = self.tag_data.get('type', 'text')
        
        # Определяем цвет в зависимости от состояния
        if self in path_chain.tag_nodes:
            # Нода в цепочке - используем цвет типа
            base_color = self.rail_colors.get(tag_type, self.rail_colors['default'])
            if self.isSelected():
                brush = QtGui.QBrush(QtGui.QColor('#ffff64'))  # Желтый для выделения
                pen = QtGui.QPen(QtGui.QColor(255, 255, 100), 3)
            else:
                brush = QtGui.QBrush(base_color)
                pen = QtGui.QPen(base_color.lighter(130), 1)
        else:
            # Нода вне цепочки - серые тона
            if self.isSelected():
                brush = QtGui.QBrush(QtGui.QColor(100, 150, 200))
                pen = QtGui.QPen(QtGui.QColor(255, 255, 100), 3)
            else:
                brush = QtGui.QBrush(QtGui.QColor(60, 60, 60))
                pen = QtGui.QPen(QtGui.QColor(120, 120, 120), 1)
        
        painter.setBrush(brush)
        painter.setPen(pen)
        
        # ИСПРАВЛЕНО: разные формы для разных типов тегов
        if tag_type == 'separator':
            painter.drawRect(rect)
        elif tag_type == 'format':
            painter.drawRoundedRect(rect, 15, 15)
        elif tag_type == 'dynamic':
            painter.drawRoundedRect(rect, 5, 15)
        elif tag_type == 'expression':
            painter.drawEllipse(rect)
        else:
            painter.drawRoundedRect(rect, 8, 8)
        
        # Отрисовка текста
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))
        painter.setFont(QtGui.QFont("Arial", 9, QtGui.QFont.Bold))
        
        title_rect = QtCore.QRectF(5, 5, self.width - 10, 20)
        painter.drawText(title_rect, QtCore.Qt.AlignCenter, self.get_display_name())
        
        # Отображение значения
        value = self.get_tag_value()
        if value:
            painter.setFont(QtGui.QFont("Arial", 8))
            painter.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200)))
            value_rect = QtCore.QRectF(5, 25, self.width - 10, 40)
            painter.drawText(
                value_rect, 
                QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, 
                str(value)
            )
    
    def mousePressEvent(self, event):
        """Обработка нажатия мыши"""
        if event.button() == QtCore.Qt.LeftButton:
            self.mouse_press_scene_pos = event.scenePos()
            self.drag_start_scene_pos = event.scenePos()
            self.drag_start_item_pos = self.pos()
            self.was_in_chain = self in path_chain.tag_nodes
            
            modifiers = event.modifiers()
            if modifiers & QtCore.Qt.ShiftModifier:
                self.setSelected(True)
            else:
                if not self.isSelected():
                    if self.scene():
                        for item in self.scene().selectedItems():
                            if item != self:
                                item.setSelected(False)
                    self.setSelected(True)
                
                self._prepare_group_drag()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Обработка перемещения мыши"""
        if not (event.buttons() & QtCore.Qt.LeftButton):
            return
        
        if self.mouse_press_scene_pos is None:
            return
        
        move_distance = (event.scenePos() - self.mouse_press_scene_pos).manhattanLength()
        if move_distance < self.click_threshold:
            return
        
        if not self.is_being_dragged:
            self.is_being_dragged = True
        
        scene_delta = event.scenePos() - self.drag_start_scene_pos
        new_pos = self.drag_start_item_pos + scene_delta
        
        constrained_pos = self._apply_constraints(new_pos)
        self.setPos(constrained_pos)
        
        self._move_selected_group(constrained_pos)
    
    def mouseReleaseEvent(self, event):
        """Обработка отпускания мыши"""
        if event.button() == QtCore.Qt.LeftButton:
            if self.is_being_dragged:
                self._handle_group_drop()
                self.is_being_dragged = False
                self.mouse_press_scene_pos = None
                self.drag_start_scene_pos = None
                self.drag_start_item_pos = None
                self.was_in_chain = False
                self.group_drag_offsets = {}
            else:
                super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """Обработка двойного клика - редактирование"""
        self._edit_tag()
    
    def _apply_constraints(self, pos):
        """Применить ограничения позиции (привязка к рельсам)"""
        if not self.is_being_dragged:
            return pos
        
        node_center_y = pos.y() + self.height / 2
        if abs(node_center_y - path_chain.rail_center_y) < 80:
            snapped_y = path_chain.rail_center_y - self.height / 2
            return QtCore.QPointF(pos.x(), snapped_y)
        
        return pos
    
    def _prepare_group_drag(self):
        """Подготовка группового перетаскивания"""
        if not self.scene():
            return
        
        self.group_drag_offsets = {}
        selected_items = [item for item in self.scene().selectedItems() if isinstance(item, TagNode)]
        
        for item in selected_items:
            if item != self:
                offset = item.pos() - self.pos()
                self.group_drag_offsets[item] = offset
    
    def _move_selected_group(self, leader_pos):
        """Перемещение группы выделенных нод"""
        if not self.scene():
            return
        
        for item, offset in self.group_drag_offsets.items():
            if isinstance(item, TagNode):
                new_item_pos = leader_pos + offset
                constrained_item_pos = item._apply_constraints(new_item_pos)
                
                item_was_dragging = item.is_being_dragged
                item.is_being_dragged = False
                item.setPos(constrained_item_pos)
                item.is_being_dragged = item_was_dragging
    
    def _handle_group_drop(self):
        """Обработка группового сброса на рельсы"""
        if not self.scene():
            return
        
        selected_items = [item for item in self.scene().selectedItems() if isinstance(item, TagNode)]
        
        rail_zone = path_chain.get_rail_zone_rect(2000)
        
        nodes_in_rail = []
        nodes_out_rail = []
        
        for item in selected_items:
            node_center = QtCore.QPointF(
                item.pos().x() + item.width / 2,
                item.pos().y() + item.height / 2
            )
            
            if rail_zone.contains(node_center):
                nodes_in_rail.append(item)
            else:
                nodes_out_rail.append(item)
        
        if nodes_out_rail:
            self._extract_group_with_positions(nodes_out_rail)
        
        if nodes_in_rail:
            self._handle_group_rail_insertion(nodes_in_rail)
    
    def _extract_group_with_positions(self, nodes_out_rail):
        """Извлечение группы нод из рельсов"""
        chain_nodes = []
        
        for node in nodes_out_rail:
            if node in path_chain.tag_nodes:
                chain_nodes.append((path_chain.get_tag_node_index(node), node))
        
        chain_nodes.sort(key=lambda x: x[0])
        
        for _, node in chain_nodes:
            path_chain.remove_tag_node(node)
        
        # Располагаем свободные ноды
        start_x = 200
        start_y = 400
        for i, (_, node) in enumerate(chain_nodes):
            new_x = start_x + i * 160
            node.setPos(new_x, start_y)
    
    def _handle_group_rail_insertion(self, nodes_in_rail):
        """Обработка вставки группы на рельсы"""
        for node in nodes_in_rail:
            if node in path_chain.tag_nodes:
                path_chain.remove_tag_node(node)
        
        sorted_nodes = sorted(nodes_in_rail, key=lambda n: n.pos().x())
        
        if sorted_nodes:
            first_node = sorted_nodes[0]
            insert_pos = path_chain.find_insert_position(first_node.pos().x())
            
            for i, node in enumerate(sorted_nodes):
                path_chain.insert_tag_node_at_position(node, insert_pos + i)
    
    def _edit_tag(self):
        """Редактирование тега"""
        tag_type = self.tag_data.get('type', 'text')
        
        if tag_type == 'separator':
            self._edit_separator()
        elif tag_type == 'format':
            self._edit_format()
        elif tag_type == 'version':
            self._edit_version()
        elif tag_type == 'dynamic':
            self._edit_dynamic()
        elif tag_type == 'expression':
            self._edit_expression()
        else:
            self._edit_default()
        
        self.update()
        
        if self in path_chain.tag_nodes:
            index = path_chain.get_tag_node_index(self)
            if index >= 0:
                path_chain.path_builder.tags[index] = self.tag_data
                path_chain._publish_chain_change()
    
    def _edit_default(self):
        """Редактирование обычного значения"""
        current_value = self.tag_data.get('default', '')
        text, ok = QtWidgets.QInputDialog.getText(
            None, f"Edit {self.get_display_name()}", "Enter value:",
            QtWidgets.QLineEdit.Normal, current_value
        )
        if ok:
            self.tag_data['default'] = text
    
    def _edit_separator(self):
        """Редактирование разделителя"""
        current_value = self.tag_data.get('value', '/')
        text, ok = QtWidgets.QInputDialog.getText(
            None, "Edit Separator", "Enter separator:",
            QtWidgets.QLineEdit.Normal, current_value
        )
        if ok:
            self.tag_data['value'] = text
    
    def _edit_format(self):
        """ИСПРАВЛЕНО: редактирование формата с правильным padding"""
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Edit Format")
        dialog.setModal(True)
        dialog.resize(300, 200)
        
        layout = QtWidgets.QVBoxLayout()
        
        # Format
        format_layout = QtWidgets.QHBoxLayout()
        format_layout.addWidget(QtWidgets.QLabel("Format:"))
        format_combo = QtWidgets.QComboBox()
        formats = ['exr', 'dpx', 'jpg', 'png', 'tif', 'mov', 'mp4']
        format_combo.addItems(formats)
        current_format = self.tag_data.get('format', 'exr')
        if current_format in formats:
            format_combo.setCurrentText(current_format)
        format_layout.addWidget(format_combo)
        layout.addLayout(format_layout)
        
        # Padding
        padding_layout = QtWidgets.QHBoxLayout()
        padding_layout.addWidget(QtWidgets.QLabel("Padding:"))
        padding_edit = QtWidgets.QLineEdit(self.tag_data.get('padding', '%04d'))
        padding_layout.addWidget(padding_edit)
        layout.addLayout(padding_layout)
        
        # Кнопки
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.tag_data['format'] = format_combo.currentText()
            self.tag_data['padding'] = padding_edit.text()
    
    def _edit_version(self):
        """Редактирование версии"""
        current_version = self.tag_data.get('version', 'v01')
        text, ok = QtWidgets.QInputDialog.getText(
            None, "Edit Version", "Enter version:",
            QtWidgets.QLineEdit.Normal, current_version
        )
        if ok:
            self.tag_data['version'] = text
    
    def _edit_dynamic(self):
        """Информация о динамическом теге"""
        QtWidgets.QMessageBox.information(
            None, "Dynamic Tag", 
            f"Dynamic tag: {self.get_display_name()}\n"
            f"Current value: {self.get_tag_value()}\n\n"
            "This value is automatically generated."
        )
    
    def _edit_expression(self):
        """Редактирование expression"""
        current_expr = self.tag_data.get('expression', '')
        text, ok = QtWidgets.QInputDialog.getText(
            None, "Edit Expression", "Enter Nuke expression:",
            QtWidgets.QLineEdit.Normal, current_expr
        )
        if ok:
            self.tag_data['expression'] = text
    
    def update_visual_state(self):
        """Обновить визуальное состояние"""
        self.update()


class ATrainWidget(QtWidgets.QGraphicsView):
    """ИСПРАВЛЕНО: основной граф A-Train с правильными scroll bars и железнодорожной темой"""
    
    path_changed = QtCore.Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.scene = QtWidgets.QGraphicsScene()
        self.setScene(self.scene)
        
        # ИСПРАВЛЕНО: scroll bars как в оригинале точно
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Применяем стиль scroll bars
        from .styles import StyleManager
        style_manager = StyleManager.instance()
        self.setStyleSheet(style_manager.get('scroll_area'))
        
        # Цвет фона
        self.setBackgroundBrush(QtGui.QColor(35, 35, 35))
        
        self.format_node = None
        self.live_preview = True
        self.pan_mode = False
        self.last_pan_point = QtCore.QPoint()
        
        self.scene.setSceneRect(-3000, -2000, 8000, 4000)
        
        self._create_format_node()
        
        self.event_bus = EventBus.instance()
        
        # Таймер обновления пути
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self._emit_path_update)
        self.update_timer.start(200)
    
    def sizeHint(self):
        return QtCore.QSize(800, 400)
    
    def minimumSizeHint(self):
        return QtCore.QSize(400, 200)
    
    def set_live_preview(self, enabled):
        """Включить/выключить live preview"""
        self.live_preview = enabled
        self._update_path()
    
    def _update_path(self):
        """Обновить путь"""
        path = path_chain.get_current_path(live_preview=self.live_preview)
        self.path_changed.emit(path)
    
    def _emit_path_update(self):
        """Периодическое обновление пути"""
        current_path = path_chain.get_current_path(live_preview=self.live_preview)
        self.path_changed.emit(current_path)
    
    def _create_format_node(self):
        """ИСПРАВЛЕНО: создать format ноду с правильным padding"""
        format_tag = {
            'name': 'format',
            'type': 'format',
            'version': 'v01',
            'padding': '%04d',  # ИСПРАВЛЕНО: % добавлен
            'format': 'exr'
        }
        
        self.format_node = TagNode(format_tag, 200, 200)
        self.scene.addItem(self.format_node)
        path_chain.add_tag_node_to_end(self.format_node)
    
    def add_tag_node(self, tag_data):
        """Добавить новую ноду тега"""
        tag_node = TagNode(tag_data, 200, 350)
        self.scene.addItem(tag_node)
        
        self.event_bus.publish('tag_node_added', tag_data)
        return tag_node
    
    def clear_all_nodes(self):
        """Очистить все ноды"""
        format_node_data = None
        if self.format_node:
            format_node_data = self.format_node.tag_data.copy()
        
        path_chain.clear()
        self.scene.clear()
        self._create_format_node()
    
    def load_preset_nodes(self, tag_names_list, format_type='exr'):
        """ИСПРАВЛЕНО: загрузить ноды из пресета с правильным padding"""
        path_chain.clear()
        self.scene.clear()
        
        # Создаем format ноду
        format_tag = {
            'name': 'format',
            'type': 'format',
            'version': 'v01',
            'padding': '%04d',  # ИСПРАВЛЕНО: % добавлен
            'format': format_type
        }
        
        self.format_node = TagNode(format_tag, 200, 200)
        self.scene.addItem(self.format_node)
        path_chain.add_tag_node_to_end(self.format_node)
        
        # Загружаем теги из PresetManager
        from ..core.preset_manager import PresetManager
        preset_manager = PresetManager()
        all_tags = preset_manager.get_all_tags()
        
        for tag_name in tag_names_list:
            for tag_data in all_tags:
                if (tag_data.get('name') == tag_name and 
                    tag_data.get('type') != 'format'):
                    tag_node = TagNode(tag_data, 200, 350)
                    self.scene.addItem(tag_node)
                    path_chain.add_tag_node_to_end(tag_node)
                    break
    
    def drawBackground(self, painter, rect):
        """ИСПРАВЛЕНО: отрисовка железнодорожного фона точно как в оригинале"""
        super().drawBackground(painter, rect)
        
        from .styles import StyleManager
        style_manager = StyleManager.instance()
        rail_colors = style_manager.get_rail_colors()
        
        # Константы железной дороги
        rail_center_y = path_chain.rail_center_y
        rail_spacing = 40
        rail_width = 4
        tie_width = 50
        tie_height = 8
        tie_spacing = 30
        
        # Цвета железной дороги
        rail_color = QtGui.QColor(rail_colors['rail'])
        tie_color = QtGui.QColor(rail_colors['tie'])
        deadend_color = QtGui.QColor(rail_colors['deadend'])
        
        # Отрисовка шпал
        painter.setBrush(QtGui.QBrush(tie_color))
        painter.setPen(QtGui.QPen(tie_color.darker(150), 1))
        
        start_x = max(path_chain.deadend_x, int(rect.left() - tie_spacing))
        start_x = start_x - (start_x % tie_spacing)
        
        for x in range(int(start_x), int(rect.right() + tie_spacing), tie_spacing):
            tie_rect = QtCore.QRectF(
                x - tie_width / 2,
                rail_center_y - rail_spacing / 2 - tie_height / 2,
                tie_width,
                rail_spacing + tie_height
            )
            painter.drawRect(tie_rect)
        
        # Отрисовка рельсов
        painter.setPen(QtGui.QPen(rail_color, rail_width))
        
        upper_rail_y = rail_center_y - rail_spacing / 2
        painter.drawLine(path_chain.deadend_x, upper_rail_y, rect.right(), upper_rail_y)
        
        lower_rail_y = rail_center_y + rail_spacing / 2
        painter.drawLine(path_chain.deadend_x, lower_rail_y, rect.right(), lower_rail_y)
        
        # Блики на рельсах
        rail_highlight = QtGui.QColor(rail_colors['rail_highlight'])
        painter.setPen(QtGui.QPen(rail_highlight, 2))
        painter.drawLine(path_chain.deadend_x, upper_rail_y - 1, rect.right(), upper_rail_y - 1)
        painter.drawLine(path_chain.deadend_x, lower_rail_y + 1, rect.right(), lower_rail_y + 1)
        
        # Тупик
        painter.setPen(QtGui.QPen(deadend_color, 6))
        painter.drawLine(
            path_chain.deadend_x, upper_rail_y - 10,
            path_chain.deadend_x, lower_rail_y + 10
        )
        
        # Подсказка если нет нод
        if len(path_chain.tag_nodes) <= 1:
            painter.setPen(QtGui.QPen(QtGui.QColor(180, 180, 180)))
            painter.setFont(QtGui.QFont("Arial", 14))
            
            text_rect = QtCore.QRectF(path_chain.start_x, rail_center_y - 60, 500, 30)
            painter.drawText(text_rect, "Drop tag nodes here to build path")
    
    def mousePressEvent(self, event):
        """Обработка нажатия мыши для pan"""
        if ((event.button() == QtCore.Qt.LeftButton and event.modifiers() & QtCore.Qt.AltModifier) or
            event.button() == QtCore.Qt.MiddleButton):
            self.pan_mode = True
            self.last_pan_point = event.pos()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Обработка перемещения мыши для pan"""
        if self.pan_mode:
            delta = event.pos() - self.last_pan_point
            self.last_pan_point = event.pos()
            
            h_scroll = self.horizontalScrollBar()
            v_scroll = self.verticalScrollBar()
            
            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())
            
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Обработка отпускания мыши для pan"""
        if ((event.button() == QtCore.Qt.LeftButton and self.pan_mode) or
            (event.button() == QtCore.Qt.MiddleButton and self.pan_mode)):
            self.pan_mode = False
            self.setCursor(QtCore.Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event):
        """Обработка колеса мыши - зум"""
        factor = 1.2
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
        
        current_scale = self.transform().m11()
        if (factor > 1.0 and current_scale < 3.0) or (factor < 1.0 and current_scale > 0.1):
            self.scale(factor, factor)
    
    def keyPressEvent(self, event):
        """Обработка нажатия клавиш"""
        if event.key() == QtCore.Qt.Key_Alt:
            self.setCursor(QtCore.Qt.OpenHandCursor)
        elif event.key() == QtCore.Qt.Key_Delete:
            selected_items = self.scene.selectedItems()
            for item in selected_items:
                if isinstance(item, TagNode):
                    if item.tag_data.get('type') == 'format':
                        continue  # Не удаляем format ноду
                    
                    path_chain.remove_tag_node(item)
                    self.scene.removeItem(item)
        
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """Обработка отпускания клавиш"""
        if event.key() == QtCore.Qt.Key_Alt and not self.pan_mode:
            self.setCursor(QtCore.Qt.ArrowCursor)
        
        super().keyReleaseEvent(event)


# Глобальный экземпляр PathChain
path_chain = PathChain()
