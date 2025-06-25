# atrain/ui/styles.py
"""
Система стилей A-Train - ИСПРАВЛЕНО: зеленый path preview, золотистые табы
"""

from typing import Dict, Any
from PySide2 import QtWidgets, QtCore, QtGui

class StyleManager:
    """Singleton менеджер стилей для A-Train"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        
        # Основные цвета темной темы
        self.colors = {
            'background': '#2b2b2b',
            'surface': '#3c3c3c',
            'surface_dark': '#2a2a2a',
            'surface_light': '#4a4a4a',
            'surface_lighter': '#5a5a5a',
            
            'border': '#555555',
            'border_light': '#666666',
            'border_dark': '#444444',
            
            'text_primary': '#ffffff',
            'text_secondary': '#cccccc',
            'text_disabled': '#888888',
            'text_muted': '#aaaaaa',
            
            'selection': '#5a5a5a',
            'selection_inactive': '#4a4a4a',
            'hover': '#454545',
            'pressed': '#353535',
            
            'success': '#4CAF50',
            'warning': '#FF9800', 
            'error': '#F44336',
            'info': '#2196F3',
            
            'create_write': '#2196F3',
            'mode_toggle': '#606060',
            
            # ИСПРАВЛЕНО: зеленый path preview
            'path_preview_bg': '#1a1a1a',
            'path_preview_text': '#00ff00',
            
            # ИСПРАВЛЕНО: золотистый для табов
            'tab_selected': '#d4af37',
            'tab_hover': '#c49b26',
            
            # Железнодорожная тема
            'rail': '#a0a0a0',
            'rail_highlight': '#c0c0c0',
            'tie': '#654321',
            'tie_shadow': '#4a2f18',
            'deadend': '#c86464',
            'deadend_shadow': '#a04040',
            'railway_selection': '#ffff64',
            'path_active': '#4a9eff',
            'path_inactive': '#888888',
            'background_grid': '#2a2a2a'
        }
        
        self.fonts = {
            'default_family': 'Arial',
            'default_size': '10pt',
            'mono_family': 'Courier New',
            'mono_size': '11px',
            'small_size': '9pt',
            'large_size': '12pt'
        }
        
        self._style_cache = {}
        print("StyleManager: Initialized with enhanced styles")
    
    @classmethod
    def instance(cls):
        """Получить экземпляр StyleManager"""
        return cls()
    
    def get(self, style_name: str) -> str:
        """Получить CSS стиль по имени"""
        if style_name not in self._style_cache:
            self._style_cache[style_name] = self._generate_style(style_name)
        return self._style_cache[style_name]
    
    def get_color(self, color_name: str) -> str:
        """Получить цвет по имени"""
        return self.colors.get(color_name, '#ffffff')
    
    def _generate_style(self, style_name: str) -> str:
        """Генерация CSS стилей"""
        generators = {
            'window': self._get_window_style,
            'button': self._get_button_style,
            'create_write': self._get_create_write_style,
            'mode_toggle': self._get_mode_toggle_style,
            'tree': self._get_tree_style,
            'search_field': self._get_search_field_style,
            'clear_search': self._get_clear_search_style,
            'path_preview': self._get_path_preview_style,
            'groupbox': self._get_groupbox_style,
            'tab_widget': self._get_tab_widget_style,
            'splitter': self._get_splitter_style,
            'scroll_area': self._get_scroll_area_style,
        }
        
        generator = generators.get(style_name)
        if generator:
            return generator()
        return ""
    
    def _get_window_style(self) -> str:
        """Основной стиль окна"""
        return f"""
        QDialog {{
            background-color: {self.colors['background']};
            color: {self.colors['text_primary']};
            font-family: {self.fonts['default_family']};
            font-size: {self.fonts['default_size']};
        }}
        
        QWidget {{
            background-color: {self.colors['background']};
            color: {self.colors['text_primary']};
        }}
        """
    
    def _get_button_style(self) -> str:
        """Стиль обычных кнопок"""
        return f"""
        QPushButton {{
            background-color: {self.colors['surface']};
            color: {self.colors['text_primary']};
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
            font-family: {self.fonts['default_family']};
            font-size: {self.fonts['default_size']};
            min-height: 18px;
        }}
        
        QPushButton:hover {{
            background-color: {self.colors['surface_light']};
            border-color: {self.colors['border_light']};
        }}
        
        QPushButton:pressed {{
            background-color: {self.colors['pressed']};
        }}
        
        QPushButton:disabled {{
            background-color: {self.colors['surface_dark']};
            color: {self.colors['text_disabled']};
            border-color: {self.colors['border_dark']};
        }}
        """
    
    def _get_create_write_style(self) -> str:
        """Стиль кнопки Create Write"""
        return f"""
        QPushButton {{
            background-color: {self.colors['create_write']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 12px 24px;
            font-weight: bold;
            font-family: {self.fonts['default_family']};
            font-size: 11pt;
            min-height: 20px;
        }}
        
        QPushButton:hover {{
            background-color: #1976D2;
        }}
        
        QPushButton:pressed {{
            background-color: #1565C0;
        }}
        """
    
    def _get_mode_toggle_style(self) -> str:
        """Стиль кнопки переключения режима"""
        return f"""
        QPushButton {{
            background-color: {self.colors['mode_toggle']};
            color: {self.colors['text_primary']};
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
            padding: 6px 16px;
            font-weight: bold;
            font-family: {self.fonts['default_family']};
            font-size: {self.fonts['default_size']};
            min-width: 80px;
        }}
        
        QPushButton:hover {{
            background-color: {self.colors['surface_light']};
        }}
        
        QPushButton:pressed {{
            background-color: {self.colors['pressed']};
        }}
        """
    
    def _get_tree_style(self) -> str:
        """ИСПРАВЛЕНО: стиль дерева с правильными + индикаторами"""
        return f"""
        QTreeWidget {{
            background-color: {self.colors['surface']};
            color: {self.colors['text_primary']};
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
            outline: none;
            font-family: {self.fonts['default_family']};
            font-size: {self.fonts['small_size']};
            selection-background-color: {self.colors['selection']};
            alternate-background-color: {self.colors['surface_dark']};
            show-decoration-selected: 1;
        }}
        
        QTreeWidget::item {{
            padding: 4px 8px;
            border: none;
            min-height: 18px;
        }}
        
        QTreeWidget::item:selected {{
            background-color: {self.colors['selection']};
            color: white;
        }}
        
        QTreeWidget::item:selected:!active {{
            background-color: {self.colors['selection_inactive']};
        }}
        
        QTreeWidget::item:hover {{
            background-color: {self.colors['hover']};
        }}
        
        QTreeWidget::branch:has-children:closed:before {{
            content: "+";
            color: {self.colors['text_primary']};
            font-weight: bold;
            font-size: 12px;
            font-family: {self.fonts['default_family']};
            padding: 1px 4px;
            background-color: {self.colors['surface_light']};
            border: 1px solid {self.colors['border']};
            border-radius: 2px;
            margin: 2px;
            width: 12px;
            height: 12px;
            text-align: center;
        }}
        
        QTreeWidget::branch:has-children:open:before {{
            content: "-";
            color: {self.colors['text_primary']};
            font-weight: bold;
            font-size: 12px;
            font-family: {self.fonts['default_family']};
            padding: 1px 4px;
            background-color: {self.colors['surface_light']};
            border: 1px solid {self.colors['border']};
            border-radius: 2px;
            margin: 2px;
            width: 12px;
            height: 12px;
            text-align: center;
        }}
        """
    
    def _get_search_field_style(self) -> str:
        """Стиль поля поиска"""
        return f"""
        QLineEdit {{
            background-color: {self.colors['surface_dark']};
            color: {self.colors['text_primary']};
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
            padding: 6px 10px;
            font-family: {self.fonts['default_family']};
            font-size: {self.fonts['small_size']};
            selection-background-color: {self.colors['selection']};
        }}
        
        QLineEdit:focus {{
            border-color: {self.colors['border_light']};
            background-color: {self.colors['surface']};
        }}
        
        QLineEdit::placeholder {{
            color: {self.colors['text_disabled']};
            font-style: italic;
        }}
        """
    
    def _get_clear_search_style(self) -> str:
        """ИСПРАВЛЕНО: стиль кнопки очистки поиска как крестик"""
        return f"""
        QPushButton {{
            background-color: transparent;
            color: {self.colors['text_disabled']};
            border: none;
            font-size: 14px;
            font-weight: bold;
            padding: 0px;
            margin: 0px;
            border-radius: 10px;
            font-family: Arial;
        }}
        
        QPushButton:hover {{
            color: {self.colors['text_primary']};
            background-color: {self.colors['hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {self.colors['pressed']};
        }}
        """
    
    def _get_path_preview_style(self) -> str:
        """ИСПРАВЛЕНО: стиль превью пути с зеленым текстом"""
        return f"""
        QLabel {{
            background-color: {self.colors['path_preview_bg']};
            color: {self.colors['path_preview_text']};
            font-family: {self.fonts['mono_family']};
            font-size: {self.fonts['mono_size']};
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
            padding: 8px;
            font-weight: normal;
        }}
        """
    
    def _get_groupbox_style(self) -> str:
        """Стиль группировочных контейнеров"""
        return f"""
        QGroupBox {{
            color: {self.colors['text_primary']};
            border: 1px solid {self.colors['border']};
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 8px;
            font-weight: bold;
            font-family: {self.fonts['default_family']};
            font-size: {self.fonts['default_size']};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px 0 4px;
            background-color: {self.colors['background']};
        }}
        """
    
    def _get_tab_widget_style(self) -> str:
        """ИСПРАВЛЕНО: стиль табов с золотистым выделением"""
        return f"""
        QTabWidget::pane {{
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
            background-color: {self.colors['surface']};
            top: -1px;
        }}
        
        QTabWidget::tab-bar {{
            left: 4px;
        }}
        
        QTabBar::tab {{
            background-color: {self.colors['surface_dark']};
            border: 1px solid {self.colors['border']};
            padding: 8px 16px;
            margin-right: 2px;
            color: {self.colors['text_secondary']};
            font-weight: bold;
            font-family: {self.fonts['default_family']};
            font-size: {self.fonts['default_size']};
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            border-bottom: none;
        }}
        
        QTabBar::tab:selected {{
            background-color: {self.colors['tab_selected']};
            color: black;
            border-color: {self.colors['tab_selected']};
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: {self.colors['tab_hover']};
        }}
        
        QTabBar::tab:first {{
            margin-left: 0;
        }}
        
        QTabBar::tab:last {{
            margin-right: 0;
        }}
        """
    
    def _get_splitter_style(self) -> str:
        """Стиль разделителя"""
        return f"""
        QSplitter::handle {{
            background-color: {self.colors['border']};
            width: 2px;
            height: 2px;
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        
        QSplitter::handle:hover {{
            background-color: {self.colors['border_light']};
        }}
        """
    
    def _get_scroll_area_style(self) -> str:
        """Стиль области прокрутки"""
        return f"""
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}
        
        QScrollBar:vertical {{
            background-color: {self.colors['surface_dark']};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {self.colors['surface_light']};
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {self.colors['border_light']};
        }}
        
        QScrollBar::handle:vertical:pressed {{
            background-color: {self.colors['selection']};
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            background-color: {self.colors['surface_dark']};
            height: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {self.colors['surface_light']};
            border-radius: 6px;
            min-width: 20px;
            margin: 2px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {self.colors['border_light']};
        }}
        
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        """
    
    def get_tag_colors(self) -> Dict[str, str]:
        """Цвета для типов тегов"""
        return {
            'dynamic': '#B4C8A0',
            'version': '#A0B4C8',
            'separator': '#C8A0B4',
            'format': '#C8B4A0',
            'expression': '#A0C8B4',
            'text': '#C8C8A0',
            'default': '#C8C8A0'
        }
    
    def get_rail_colors(self) -> Dict[str, str]:
        """Цвета железнодорожной темы для node_graph"""
        return {
            'rail': self.colors['rail'],
            'rail_highlight': self.colors['rail_highlight'],
            'tie': self.colors['tie'],
            'tie_shadow': self.colors['tie_shadow'],
            'deadend': self.colors['deadend'],
            'deadend_shadow': self.colors['deadend_shadow'],
            'selection': self.colors['railway_selection'],
            'path_active': self.colors['path_active'],
            'path_inactive': self.colors['path_inactive'],
            'background_grid': self.colors['background_grid']
        }
    
    def get_node_colors(self) -> Dict[str, str]:
        """Цвета для нод в графе"""
        return {
            'separator': '#505078',
            'format': '#785050',
            'version': '#507850',
            'dynamic': '#786450',
            'expression': '#647878',
            'text': '#646464',
            'selected': '#ffff64',
            'hover': '#808080'
        }
    
    def clear_cache(self):
        """Очистить кеш стилей"""
        self._style_cache.clear()
        print("StyleManager: Style cache cleared")
