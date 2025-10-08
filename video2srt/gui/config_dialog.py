"""
配置对话框
"""

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget, 
                            QPushButton, QLabel, QLineEdit, QComboBox,
                            QCheckBox, QTabWidget, QGroupBox, QGridLayout,
                            QTextEdit, QMessageBox, QFileDialog, QSpinBox,
                            QProgressBar, QTableWidget, QTableWidgetItem,
                            QHeaderView, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from ..config_manager import config_manager
from ..model_manager import model_manager


class ModelDownloadThread(QThread):
    """模型下载线程"""
    progress_updated = pyqtSignal(str, int, str)  # model_size, progress, status
    
    def __init__(self, model_size: str):
        super().__init__()
        self.model_size = model_size
    
    def run(self):
        """执行下载"""
        model_manager.download_model(self.model_size, self.progress_updated.emit)


class CustomDownloadThread(QThread):
    """自定义下载线程"""
    progress_updated = pyqtSignal(str, int, str)  # model_name, progress, status
    
    def __init__(self, url: str, model_name: str):
        super().__init__()
        self.url = url
        self.model_name = model_name
    
    def run(self):
        """执行自定义下载"""
        model_manager.download_from_url(self.url, self.model_name, self.progress_updated.emit)


class TestTranslatorThread(QThread):
    """翻译器测试线程"""
    finished_with_result = pyqtSignal(str)
    
    def __init__(self, translator_type: str, text: str, target_lang: str):
        super().__init__()
        self.translator_type = translator_type
        self.text = text
        self.target_lang = target_lang
    
    def run(self):
        try:
            from ..translator import get_translator
            translator = get_translator(self.translator_type)
            result = translator.translate_text(self.text, self.target_lang)
            if result and result != self.text:
                self.finished_with_result.emit(f"✅ {self.translator_type}: 连接成功\n测试结果: {self.text} -> {result}")
            else:
                self.finished_with_result.emit(f"⚠️ {self.translator_type}: 返回原文，可能未正常工作")
        except Exception as e:
            self.finished_with_result.emit(f"❌ {self.translator_type}: {e}")


class ConfigDialog(QDialog):
    """配置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("配置设置")
        self.setModal(True)
        self.resize(800, 600)
        
        # 模型下载相关
        self.download_threads = {}
        self.model_progress_bars = {}
        self.download_status_labels = {}
        
        self.init_ui()
        self.load_config()
        self.refresh_model_table()
        
        # 设置定时器刷新模型表格
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_model_table)
        self.refresh_timer.start(5000)  # 每5秒刷新一次
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Whisper 配置页
        self.whisper_tab = self.create_whisper_tab()
        self.tab_widget.addTab(self.whisper_tab, "语音识别")
        
        # 模型管理页
        self.model_tab = self.create_model_management_tab()
        self.tab_widget.addTab(self.model_tab, "模型管理")
        
        # 翻译器配置页
        self.translator_tab = self.create_translator_tab()
        self.tab_widget.addTab(self.translator_tab, "翻译器")
        
        # 通用设置页
        self.general_tab = self.create_general_tab()
        self.tab_widget.addTab(self.general_tab, "通用设置")
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_connections)
        
        self.reset_btn = QPushButton("重置默认")
        self.reset_btn.clicked.connect(self.reset_to_default)
        
        self.import_btn = QPushButton("导入配置")
        self.import_btn.clicked.connect(self.import_config)
        
        self.export_btn = QPushButton("导出配置")
        self.export_btn.clicked.connect(self.export_config)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_config)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.test_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def create_whisper_tab(self):
        """创建 Whisper 配置页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Whisper 模型设置
        whisper_group = QGroupBox("Whisper 模型设置")
        whisper_layout = QGridLayout(whisper_group)
        
        whisper_layout.addWidget(QLabel("模型大小:"), 0, 0)
        self.whisper_model_combo = QComboBox()
        self.whisper_model_combo.setEditable(True)
        
        # 添加所有可用的模型，按类型分组
        english_models = ['tiny.en', 'base.en', 'small.en', 'medium.en']
        multilingual_models = ['tiny', 'base', 'small', 'medium', 'large']
        
        # 添加英语专用模型
        for model in english_models:
            self.whisper_model_combo.addItem(f"{model} (英语专用)")
        
        # 添加多语言模型
        for model in multilingual_models:
            self.whisper_model_combo.addItem(f"{model} (多语言)")
        
        self.whisper_model_combo.setCurrentText('base (多语言)')
        self.whisper_model_combo.setToolTip("选择 Whisper 模型：\n• .en 模型：英语专用，准确性更高\n• 多语言模型：支持多种语言\n• turbo：优化版本，速度更快")
        whisper_layout.addWidget(self.whisper_model_combo, 0, 1)
        
        whisper_layout.addWidget(QLabel("默认语言:"), 1, 0)
        self.whisper_language_combo = QComboBox()
        self.whisper_language_combo.addItems([
            'auto (自动检测)', 'zh (中文)', 'en (英语)', 'ja (日语)', 
            'ko (韩语)', 'fr (法语)', 'de (德语)', 'es (西班牙语)', 'ru (俄语)'
        ])
        whisper_layout.addWidget(self.whisper_language_combo, 1, 1)
        
        whisper_layout.addWidget(QLabel("设备:"), 2, 0)
        self.whisper_device_combo = QComboBox()
        self.whisper_device_combo.addItems(['auto (自动)', 'cpu', 'cuda'])
        self.whisper_device_combo.setCurrentText('auto (自动)')
        whisper_layout.addWidget(self.whisper_device_combo, 2, 1)
        
        # 模型路径设置
        whisper_layout.addWidget(QLabel("模型路径:"), 3, 0)
        model_path_layout = QHBoxLayout()
        self.model_path_edit = QLineEdit()
        self.model_path_edit.setPlaceholderText("留空使用默认路径")
        model_path_layout.addWidget(self.model_path_edit)
        
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_model_path)
        model_path_layout.addWidget(browse_btn)
        whisper_layout.addLayout(model_path_layout, 3, 1)
        
        layout.addWidget(whisper_group)
        
        # 添加一些说明文本
        info_text = QTextEdit()
        info_text.setMaximumHeight(100)
        info_text.setPlainText(
            "Whisper 模型说明:\n"
            "英语专用模型 (.en):\n"
            "• tiny.en: 39MB, 最快速度, 较低准确性\n"
            "• base.en: 74MB, 快速, 中等准确性\n"
            "• small.en: 244MB, 中等速度, 较好准确性\n"
            "• medium.en: 769MB, 较慢, 高准确性\n\n"
            "多语言模型:\n"
            "• tiny: 39MB, 最快速度, 较低准确性\n"
            "• base: 74MB, 快速, 中等准确性 (推荐)\n"
            "• small: 244MB, 中等速度, 较好准确性\n"
            "• medium: 769MB, 较慢, 高准确性\n"
            "• large: 1550MB, 最慢, 最高准确性\n"
            "• turbo: 809MB, 快速, 优化版本"
        )
        info_text.setReadOnly(True)
        layout.addWidget(info_text)
        
        layout.addStretch()
        return widget
    
    def create_model_management_tab(self):
        """创建模型管理页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 模型信息显示
        info_group = QGroupBox("模型信息")
        info_layout = QVBoxLayout(info_group)
        
        # 磁盘使用情况
        disk_info = model_manager.get_disk_usage()
        disk_label = QLabel(f"模型存储路径: {disk_info['model_path']}")
        disk_label.setWordWrap(True)
        info_layout.addWidget(disk_label)
        
        disk_usage_label = QLabel(f"已使用空间: {disk_info['total_size_mb']} MB, 文件数量: {disk_info['file_count']}")
        info_layout.addWidget(disk_usage_label)
        
        layout.addWidget(info_group)
        
        # 模型列表
        model_group = QGroupBox("模型管理")
        model_layout = QVBoxLayout(model_group)
        
        # 创建模型表格
        self.model_table = QTableWidget()
        self.model_table.setColumnCount(7)
        self.model_table.setHorizontalHeaderLabels([
            "模型名称", "大小", "速度", "准确性", "状态", "进度", "操作"
        ])
        
        # 设置表格属性
        header = self.model_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.model_table.setAlternatingRowColors(True)
        self.model_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        model_layout.addWidget(self.model_table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_model_table)
        button_layout.addWidget(refresh_btn)
        
        upload_btn = QPushButton("上传模型")
        upload_btn.clicked.connect(self.upload_model)
        button_layout.addWidget(upload_btn)
        
        custom_download_btn = QPushButton("自定义下载")
        custom_download_btn.clicked.connect(self.custom_download)
        button_layout.addWidget(custom_download_btn)
        
        manual_download_btn = QPushButton("手动下载")
        manual_download_btn.clicked.connect(self.show_manual_download_help)
        button_layout.addWidget(manual_download_btn)
        
        refresh_urls_btn = QPushButton("刷新下载地址")
        refresh_urls_btn.clicked.connect(self.refresh_download_urls)
        button_layout.addWidget(refresh_urls_btn)
        
        cleanup_btn = QPushButton("清理所有模型")
        cleanup_btn.clicked.connect(self.cleanup_all_models)
        button_layout.addWidget(cleanup_btn)
        
        button_layout.addStretch()
        model_layout.addLayout(button_layout)
        
        layout.addWidget(model_group)
        
        return widget
    
    def create_translator_tab(self):
        """创建翻译器配置页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 翻译器选择（单选）
        translator_selection_group = QGroupBox("翻译器选择")
        translator_selection_layout = QVBoxLayout(translator_selection_group)
        
        # 翻译器类型选择
        translator_type_layout = QHBoxLayout()
        translator_type_layout.addWidget(QLabel("选择翻译器:"))
        
        self.translator_type_combo = QComboBox()
        # 只显示可用的翻译器
        available_translators = config_manager.get_available_translators()
        self.translator_type_combo.addItems(available_translators)
        translator_type_layout.addWidget(self.translator_type_combo)
        translator_selection_layout.addLayout(translator_type_layout)
        
        # 翻译器状态显示
        self.translator_status_label = QLabel("状态: 检查中...")
        translator_selection_layout.addWidget(self.translator_status_label)
        
        # 测试翻译器按钮
        test_translator_btn = QPushButton("测试翻译器")
        test_translator_btn.clicked.connect(self.test_current_translator)
        translator_selection_layout.addWidget(test_translator_btn)
        
        layout.addWidget(translator_selection_group)
        
        # Google 翻译设置
        google_group = QGroupBox("Google 翻译")
        google_layout = QGridLayout(google_group)
        
        google_layout.addWidget(QLabel("超时时间(秒):"), 0, 0)
        self.google_timeout_spin = QSpinBox()
        self.google_timeout_spin.setRange(5, 60)
        self.google_timeout_spin.setValue(15)
        google_layout.addWidget(self.google_timeout_spin, 0, 1)
        
        google_layout.addWidget(QLabel("重试次数:"), 1, 0)
        self.google_retry_spin = QSpinBox()
        self.google_retry_spin.setRange(1, 10)
        self.google_retry_spin.setValue(3)
        google_layout.addWidget(self.google_retry_spin, 1, 1)
        
        layout.addWidget(google_group)
        
        # 离线翻译设置
        offline_group = QGroupBox("离线翻译")
        offline_layout = QGridLayout(offline_group)
        
        offline_layout.addWidget(QLabel("首选服务:"), 0, 0)
        self.offline_service_combo = QComboBox()
        self.offline_service_combo.addItems([
            "auto (自动选择)",
            "googletrans",
            "deep_translator"
        ])
        offline_layout.addWidget(self.offline_service_combo, 0, 1)
        
        layout.addWidget(offline_group)
        
        # OpenAI 翻译设置
        openai_group = QGroupBox("OpenAI 翻译")
        openai_layout = QGridLayout(openai_group)
        
        self.openai_enabled_check = QCheckBox("启用 OpenAI 翻译")
        openai_layout.addWidget(self.openai_enabled_check, 0, 0, 1, 2)
        
        openai_layout.addWidget(QLabel("API Key:"), 1, 0)
        self.openai_api_key_edit = QLineEdit()
        self.openai_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_api_key_edit.setPlaceholderText("输入 OpenAI API Key")
        openai_layout.addWidget(self.openai_api_key_edit, 1, 1)
        
        openai_layout.addWidget(QLabel("Base URL:"), 2, 0)
        self.openai_base_url_edit = QLineEdit()
        self.openai_base_url_edit.setPlaceholderText("https://api.openai.com/v1")
        openai_layout.addWidget(self.openai_base_url_edit, 2, 1)
        
        openai_layout.addWidget(QLabel("模型:"), 3, 0)
        self.openai_model_combo = QComboBox()
        self.openai_model_combo.setEditable(True)
        self.openai_model_combo.addItems([
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo-16k"
        ])
        self.openai_model_combo.setToolTip("可以选择预设模型或输入自定义模型名称")
        openai_layout.addWidget(self.openai_model_combo, 3, 1)
        
        openai_layout.addWidget(QLabel("最大 Token:"), 4, 0)
        self.openai_max_tokens_spin = QSpinBox()
        self.openai_max_tokens_spin.setRange(100, 8000)
        self.openai_max_tokens_spin.setValue(4000)
        openai_layout.addWidget(self.openai_max_tokens_spin, 4, 1)
        
        openai_layout.addWidget(QLabel("温度:"), 5, 0)
        self.openai_temperature_spin = QSpinBox()
        self.openai_temperature_spin.setRange(0, 100)
        self.openai_temperature_spin.setValue(30)
        self.openai_temperature_spin.setSuffix("%")
        openai_layout.addWidget(self.openai_temperature_spin, 5, 1)
        
        layout.addWidget(openai_group)
        
        # 百度翻译设置
        baidu_group = QGroupBox("百度翻译")
        baidu_layout = QGridLayout(baidu_group)
        
        self.baidu_enabled_check = QCheckBox("启用百度翻译")
        baidu_layout.addWidget(self.baidu_enabled_check, 0, 0, 1, 2)
        
        baidu_layout.addWidget(QLabel("App ID:"), 1, 0)
        self.baidu_app_id_edit = QLineEdit()
        self.baidu_app_id_edit.setPlaceholderText("输入百度翻译 App ID")
        baidu_layout.addWidget(self.baidu_app_id_edit, 1, 1)
        
        baidu_layout.addWidget(QLabel("Secret Key:"), 2, 0)
        self.baidu_secret_key_edit = QLineEdit()
        self.baidu_secret_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.baidu_secret_key_edit.setPlaceholderText("输入百度翻译 Secret Key")
        baidu_layout.addWidget(self.baidu_secret_key_edit, 2, 1)
        
        layout.addWidget(baidu_group)
        
        # 简单翻译设置
        simple_group = QGroupBox("简单翻译")
        simple_layout = QGridLayout(simple_group)
        
        self.simple_enabled_check = QCheckBox("启用简单翻译")
        self.simple_enabled_check.setChecked(True)
        simple_layout.addWidget(self.simple_enabled_check, 0, 0, 1, 2)
        
        layout.addWidget(simple_group)
        layout.addStretch()
        
        return widget
    
    def create_general_tab(self):
        """创建通用设置页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 默认设置
        default_group = QGroupBox("默认设置")
        default_layout = QGridLayout(default_group)
        
        default_layout.addWidget(QLabel("默认翻译器:"), 0, 0)
        self.default_translator_combo = QComboBox()
        self.default_translator_combo.addItems([
            "google", "openai", "offline", "baidu", "tencent", "aliyun", "simple"
        ])
        default_layout.addWidget(self.default_translator_combo, 0, 1)
        
        default_layout.addWidget(QLabel("备用翻译器:"), 1, 0)
        self.fallback_translator_combo = QComboBox()
        self.fallback_translator_combo.addItems([
            "simple", "offline", "google"
        ])
        default_layout.addWidget(self.fallback_translator_combo, 1, 1)
        
        self.auto_detect_check = QCheckBox("自动检测语言")
        default_layout.addWidget(self.auto_detect_check, 2, 0, 1, 2)
        
        self.save_on_exit_check = QCheckBox("退出时保存配置")
        default_layout.addWidget(self.save_on_exit_check, 3, 0, 1, 2)
        
        layout.addWidget(default_group)
        
        # 配置信息
        info_group = QGroupBox("配置信息")
        info_layout = QVBoxLayout(info_group)
        
        self.config_info_text = QTextEdit()
        self.config_info_text.setMaximumHeight(100)
        self.config_info_text.setReadOnly(True)
        info_layout.addWidget(self.config_info_text)
        
        layout.addWidget(info_group)
        layout.addStretch()
        
        return widget
    
    def load_config(self):
        """加载配置到界面"""
        # Whisper 配置
        model_size = config_manager.get_whisper_model_size()
        # 根据模型类型设置正确的显示文本
        if model_size.endswith('.en'):
            display_text = f"{model_size} (英语专用)"
        elif model_size == 'turbo':
            display_text = f"{model_size} (多语言优化)"
        else:
            display_text = f"{model_size} (多语言)"
        
        # 查找匹配的项
        for i in range(self.whisper_model_combo.count()):
            if self.whisper_model_combo.itemText(i) == display_text:
                self.whisper_model_combo.setCurrentIndex(i)
                break
        else:
            # 如果没有找到匹配项，设置为用户自定义输入
            self.whisper_model_combo.setCurrentText(model_size)
        whisper_lang = config_manager.get_whisper_language()
        if whisper_lang == 'auto':
            self.whisper_language_combo.setCurrentText('auto (自动检测)')
        else:
            lang_map = {'zh': 'zh (中文)', 'en': 'en (英语)', 'ja': 'ja (日语)', 
                       'ko': 'ko (韩语)', 'fr': 'fr (法语)', 'de': 'de (德语)', 
                       'es': 'es (西班牙语)', 'ru': 'ru (俄语)'}
            self.whisper_language_combo.setCurrentText(lang_map.get(whisper_lang, whisper_lang))
        
        device = config_manager.get('whisper.device', 'auto')
        if device == 'auto':
            self.whisper_device_combo.setCurrentText('auto (自动)')
        else:
            self.whisper_device_combo.setCurrentText(device)
        
        # 加载模型路径
        model_path = config_manager.get_whisper_model_path()
        if model_path and model_path != str(Path(__file__).parent.parent / "model"):
            self.model_path_edit.setText(model_path)
        
        # 翻译器选择
        default_translator = config_manager.get_default_translator()
        if default_translator in [self.translator_type_combo.itemText(i) for i in range(self.translator_type_combo.count())]:
            self.translator_type_combo.setCurrentText(default_translator)
        
        # Google 翻译配置
        self.google_timeout_spin.setValue(config_manager.get('translators.google.timeout', 15))
        self.google_retry_spin.setValue(config_manager.get('translators.google.retry_count', 3))
        
        # 离线翻译配置
        service = config_manager.get('translators.offline.service', 'auto')
        if service == 'auto':
            self.offline_service_combo.setCurrentText("auto (自动选择)")
        else:
            self.offline_service_combo.setCurrentText(service)
        
        # OpenAI 翻译配置
        self.openai_enabled_check.setChecked(config_manager.is_translator_enabled('openai'))
        self.openai_api_key_edit.setText(config_manager.get_openai_api_key())
        self.openai_base_url_edit.setText(config_manager.get('translators.openai.base_url', ''))
        self.openai_model_combo.setCurrentText(config_manager.get('translators.openai.model', 'gpt-3.5-turbo'))
        self.openai_max_tokens_spin.setValue(config_manager.get('translators.openai.max_tokens', 4000))
        self.openai_temperature_spin.setValue(int(config_manager.get('translators.openai.temperature', 0.3) * 100))
        
        # 百度翻译配置
        self.baidu_enabled_check.setChecked(config_manager.is_translator_enabled('baidu'))
        self.baidu_app_id_edit.setText(config_manager.get('translators.baidu.app_id', ''))
        self.baidu_secret_key_edit.setText(config_manager.get('translators.baidu.secret_key', ''))
        
        # 简单翻译配置
        self.simple_enabled_check.setChecked(config_manager.is_translator_enabled('simple'))
        
        # 通用设置
        self.default_translator_combo.setCurrentText(config_manager.get_default_translator())
        self.fallback_translator_combo.setCurrentText(config_manager.get_fallback_translator())
        self.auto_detect_check.setChecked(config_manager.get('general.auto_detect_language', True))
        self.save_on_exit_check.setChecked(config_manager.get('general.save_config_on_exit', True))
        
        # 更新配置信息
        self.update_config_info()
    
    def save_config(self):
        """保存配置"""
        try:
            # Whisper 配置
            model_text = self.whisper_model_combo.currentText()
            # 从显示文本中提取模型名称
            if ' (英语专用)' in model_text:
                model_size = model_text.replace(' (英语专用)', '')
            elif ' (多语言)' in model_text:
                model_size = model_text.replace(' (多语言)', '')
            elif ' (多语言优化)' in model_text:
                model_size = model_text.replace(' (多语言优化)', '')
            else:
                model_size = model_text  # 用户自定义输入
            
            config_manager.set_whisper_model_size(model_size)
            whisper_lang = self.whisper_language_combo.currentText().split()[0]
            if whisper_lang == 'auto':
                whisper_lang = 'auto'
            config_manager.set_whisper_language(whisper_lang)
            
            device = self.whisper_device_combo.currentText()
            if device == 'auto (自动)':
                device = 'auto'
            config_manager.set('whisper.device', device)
            
            # 保存模型路径
            model_path = self.model_path_edit.text().strip()
            if model_path:
                config_manager.set_whisper_model_path(model_path)
            else:
                config_manager.set('whisper.model_path', '')
            
            # Google 翻译配置
            # 翻译器配置
            config_manager.set_default_translator(self.translator_type_combo.currentText())
            config_manager.set('translators.google.timeout', self.google_timeout_spin.value())
            config_manager.set('translators.google.retry_count', self.google_retry_spin.value())
            
            # 离线翻译配置
            service = self.offline_service_combo.currentText()
            if service == "auto (自动选择)":
                service = "auto"
            config_manager.set('translators.offline.service', service)
            
            # OpenAI 翻译配置
            config_manager.set_translator_enabled('openai', self.openai_enabled_check.isChecked())
            config_manager.set_openai_api_key(self.openai_api_key_edit.text())
            config_manager.set('translators.openai.base_url', self.openai_base_url_edit.text())
            config_manager.set('translators.openai.model', self.openai_model_combo.currentText())
            config_manager.set('translators.openai.max_tokens', self.openai_max_tokens_spin.value())
            config_manager.set('translators.openai.temperature', self.openai_temperature_spin.value() / 100.0)
            
            # 百度翻译配置
            config_manager.set_translator_enabled('baidu', self.baidu_enabled_check.isChecked())
            config_manager.set('translators.baidu.app_id', self.baidu_app_id_edit.text())
            config_manager.set('translators.baidu.secret_key', self.baidu_secret_key_edit.text())
            
            # 简单翻译配置
            config_manager.set_translator_enabled('simple', self.simple_enabled_check.isChecked())
            
            # 通用设置
            config_manager.set_default_translator(self.default_translator_combo.currentText())
            config_manager.set_fallback_translator(self.fallback_translator_combo.currentText())
            config_manager.set('general.auto_detect_language', self.auto_detect_check.isChecked())
            config_manager.set('general.save_config_on_exit', self.save_on_exit_check.isChecked())
            
            # 保存到文件
            if config_manager.save_config():
                QMessageBox.information(self, "成功", "配置已保存!")
                self.accept()
            else:
                QMessageBox.warning(self, "错误", "保存配置失败!")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置时出现错误: {e}")
            print(f"保存配置详细错误: {e}")
            import traceback
            traceback.print_exc()
    
    def test_connections(self):
        """测试连接"""
        self.test_btn.setEnabled(False)
        results = []
        pending_threads = []

        # OpenAI 测试（可选）
        if self.openai_api_key_edit.text():
            t1 = TestTranslatorThread("openai", "Hello", "zh")
            pending_threads.append(t1)
        else:
            results.append("⚠️ OpenAI: 未设置 API Key")

        # Google 测试（必测）
        t2 = TestTranslatorThread("google", "Hello", "zh")
        pending_threads.append(t2)

        self._test_results = results
        self._test_threads = pending_threads

        def on_thread_finished(msg: str):
            self._test_results.append(msg)
            # 当全部线程结束时展示结果
            if all(not th.isRunning() for th in self._test_threads):
                QMessageBox.information(self, "连接测试", "\n".join(self._test_results))
                self.test_btn.setEnabled(True)

        for th in pending_threads:
            th.finished_with_result.connect(on_thread_finished)
            th.start()
    
    def reset_to_default(self):
        """重置为默认配置"""
        reply = QMessageBox.question(
            self, "确认", "确定要重置为默认配置吗？这将清除所有自定义设置。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if config_manager.reset_to_default():
                self.load_config()
                QMessageBox.information(self, "成功", "已重置为默认配置!")
            else:
                QMessageBox.warning(self, "错误", "重置配置失败!")
    
    def import_config(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置文件", "", "JSON 文件 (*.json);;所有文件 (*)"
        )
        
        if file_path:
            if config_manager.import_config(file_path):
                self.load_config()
                QMessageBox.information(self, "成功", "配置导入成功!")
            else:
                QMessageBox.warning(self, "错误", "配置导入失败!")
    
    def export_config(self):
        """导出配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置文件", "video2srt_config.json", "JSON 文件 (*.json);;所有文件 (*)"
        )
        
        if file_path:
            if config_manager.export_config(file_path):
                QMessageBox.information(self, "成功", "配置导出成功!")
            else:
                QMessageBox.warning(self, "错误", "配置导出失败!")
    
    def update_config_info(self):
        """更新配置信息"""
        config_file = str(config_manager.config_file)
        available_translators = config_manager.get_available_translators()
        
        info_text = f"""配置文件: {config_file}
可用翻译器: {', '.join(available_translators)}
默认翻译器: {config_manager.get_default_translator()}
备用翻译器: {config_manager.get_fallback_translator()}"""
        
        self.config_info_text.setText(info_text)
    
    def browse_model_path(self):
        """浏览模型路径"""
        path = QFileDialog.getExistingDirectory(
            self, 
            "选择模型存储路径",
            config_manager.get_whisper_model_path()
        )
        if path:
            self.model_path_edit.setText(path)
    
    def refresh_model_table(self):
        """刷新模型表格"""
        try:
            models = model_manager.get_model_info()
            custom_models = model_manager.list_custom_models()
            
            # 合并标准模型和自定义模型
            all_models = {}
            for model_name, info in models.items():
                all_models[model_name] = info
            
            for custom_model in custom_models:
                all_models[custom_model['name']] = {
                    'size': custom_model['size'],
                    'speed': '未知',
                    'accuracy': '未知',
                    'description': '自定义模型',
                    'downloaded': True,
                    'file_size': custom_model['size'],
                    'type': 'custom'
                }
            
            self.model_table.setRowCount(len(all_models))
            
            for row, (model_name, info) in enumerate(all_models.items()):
                # 模型名称
                self.model_table.setItem(row, 0, QTableWidgetItem(model_name))
                
                # 大小
                self.model_table.setItem(row, 1, QTableWidgetItem(info['size']))
                
                # 速度
                self.model_table.setItem(row, 2, QTableWidgetItem(info['speed']))
                
                # 准确性
                self.model_table.setItem(row, 3, QTableWidgetItem(info['accuracy']))
                
                # 状态
                status = "已下载" if info['downloaded'] else "未下载"
                if info['downloaded']:
                    status += f" ({info['file_size']})"
                self.model_table.setItem(row, 4, QTableWidgetItem(status))
                
                # 进度条
                progress_widget = QWidget()
                progress_layout = QVBoxLayout(progress_widget)
                progress_layout.setContentsMargins(2, 2, 2, 2)
                
                progress_bar = QProgressBar()
                progress_bar.setVisible(False)
                progress_layout.addWidget(progress_bar)
                
                status_label = QLabel("")
                status_label.setVisible(False)
                status_label.setStyleSheet("color: blue; font-size: 10px;")
                progress_layout.addWidget(status_label)
                
                self.model_table.setCellWidget(row, 5, progress_widget)
                
                # 存储进度条和状态标签的引用
                self.model_progress_bars[model_name] = progress_bar
                self.download_status_labels[model_name] = status_label
                
                # 操作按钮
                button_widget = QWidget()
                button_layout = QHBoxLayout(button_widget)
                button_layout.setContentsMargins(2, 2, 2, 2)
                
                if info['downloaded']:
                    delete_btn = QPushButton("删除")
                    delete_btn.clicked.connect(lambda checked, name=model_name: self.delete_model(name))
                    button_layout.addWidget(delete_btn)
                else:
                    download_btn = QPushButton("下载")
                    download_btn.clicked.connect(lambda checked, name=model_name: self.download_model(name))
                    button_layout.addWidget(download_btn)
                
                self.model_table.setCellWidget(row, 6, button_widget)
                
        except Exception as e:
            print(f"刷新模型表格失败: {e}")
    
    def download_model(self, model_size: str):
        """下载模型"""
        if model_size in self.download_threads:
            QMessageBox.warning(self, "警告", f"模型 {model_size} 正在下载中")
            return
        
        # 创建下载线程
        thread = ModelDownloadThread(model_size)
        thread.progress_updated.connect(self.on_download_progress)
        thread.finished.connect(lambda: self.on_download_finished(model_size))
        
        self.download_threads[model_size] = thread
        thread.start()
        
        # 显示开始下载的状态
        if model_size in self.model_progress_bars:
            progress_bar = self.model_progress_bars[model_size]
            status_label = self.download_status_labels[model_size]
            progress_bar.setVisible(True)
            progress_bar.setValue(0)
            status_label.setVisible(True)
            status_label.setText("开始下载...")
    
    def on_download_progress(self, model_size: str, progress: int, status: str):
        """下载进度更新"""
        # 更新进度条和状态标签
        if model_size in self.model_progress_bars:
            progress_bar = self.model_progress_bars[model_size]
            status_label = self.download_status_labels[model_size]
            
            progress_bar.setVisible(True)
            progress_bar.setValue(progress)
            status_label.setVisible(True)
            status_label.setText(status)
            
            # 更新状态列
            for row in range(self.model_table.rowCount()):
                if self.model_table.item(row, 0).text() == model_size:
                    self.model_table.setItem(row, 4, QTableWidgetItem(f"下载中... ({progress}%)"))
                    break
        
        print(f"模型 {model_size} 下载进度: {progress}% - {status}")
    
    def on_download_finished(self, model_size: str):
        """下载完成"""
        if model_size in self.download_threads:
            del self.download_threads[model_size]
        
        # 隐藏进度条
        if model_size in self.model_progress_bars:
            progress_bar = self.model_progress_bars[model_size]
            status_label = self.download_status_labels[model_size]
            progress_bar.setVisible(False)
            status_label.setVisible(False)
        
        QMessageBox.information(self, "下载完成", f"模型 {model_size} 下载完成")
        self.refresh_model_table()
    
    def delete_model(self, model_size: str):
        """删除模型"""
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除模型 {model_size} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if model_manager.delete_model(model_size):
                QMessageBox.information(self, "成功", f"模型 {model_size} 已删除")
                self.refresh_model_table()
            else:
                QMessageBox.warning(self, "失败", f"删除模型 {model_size} 失败")
    
    def cleanup_all_models(self):
        """清理所有模型"""
        reply = QMessageBox.question(
            self, 
            "确认清理", 
            "确定要删除所有模型文件吗？这将释放磁盘空间但需要重新下载模型。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = model_manager.cleanup_models()
            QMessageBox.information(self, "清理完成", f"已删除 {deleted_count} 个模型文件")
            self.refresh_model_table()
    
    def upload_model(self):
        """上传模型文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模型文件",
            "",
            "PyTorch模型文件 (*.pt *.pth);;所有文件 (*)"
        )
        
        if file_path:
            # 询问模型名称
            from PyQt6.QtWidgets import QInputDialog
            model_name, ok = QInputDialog.getText(
                self, 
                "模型名称", 
                "请输入模型名称:", 
                text=Path(file_path).stem
            )
            
            if ok and model_name:
                if model_manager.upload_model(file_path, model_name):
                    QMessageBox.information(self, "成功", f"模型 {model_name} 上传成功")
                    self.refresh_model_table()
                else:
                    QMessageBox.warning(self, "失败", "模型上传失败")
    
    def custom_download(self):
        """自定义下载模型"""
        dialog = QDialog(self)
        dialog.setWindowTitle("自定义下载")
        dialog.setModal(True)
        dialog.resize(400, 200)
        
        layout = QVBoxLayout(dialog)
        
        # URL输入
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("下载链接:"))
        url_edit = QLineEdit()
        url_edit.setPlaceholderText("https://example.com/model.pt")
        url_layout.addWidget(url_edit)
        layout.addLayout(url_layout)
        
        # 模型名称输入
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("模型名称:"))
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("my_model")
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        download_btn = QPushButton("开始下载")
        download_btn.clicked.connect(lambda: self.start_custom_download(url_edit.text(), name_edit.text(), dialog))
        button_layout.addWidget(download_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def start_custom_download(self, url: str, model_name: str, dialog: QDialog):
        """开始自定义下载"""
        if not url or not model_name:
            QMessageBox.warning(self, "错误", "请输入下载链接和模型名称")
            return
        
        dialog.accept()
        
        # 创建下载线程
        thread = CustomDownloadThread(url, model_name)
        thread.progress_updated.connect(self.on_download_progress)
        thread.finished.connect(lambda: self.on_custom_download_finished(model_name))
        
        self.download_threads[model_name] = thread
        thread.start()
        
        # 显示开始下载的状态
        if model_name in self.model_progress_bars:
            progress_bar = self.model_progress_bars[model_name]
            status_label = self.download_status_labels[model_name]
            progress_bar.setVisible(True)
            progress_bar.setValue(0)
            status_label.setVisible(True)
            status_label.setText("开始下载...")
    
    def on_custom_download_finished(self, model_name: str):
        """自定义下载完成"""
        if model_name in self.download_threads:
            del self.download_threads[model_name]
        
        # 隐藏进度条
        if model_name in self.model_progress_bars:
            progress_bar = self.model_progress_bars[model_name]
            status_label = self.download_status_labels[model_name]
            progress_bar.setVisible(False)
            status_label.setVisible(False)
        
        QMessageBox.information(self, "下载完成", f"模型 {model_name} 下载完成")
        self.refresh_model_table()
    
    def show_manual_download_help(self):
        """显示手动下载帮助"""
        help_text = """
手动下载Whisper模型

由于网络问题，自动下载可能失败。您可以手动下载模型：

方法1: 使用HuggingFace (推荐)
1. 访问: https://huggingface.co/openai/whisper-base
2. 点击 "Files and versions" 标签
3. 下载 pytorch_model.bin 文件
4. 重命名为 base.pt
5. 放入 model 文件夹

方法2: 使用命令行工具
运行: python manual_download.py base

方法3: 使用自定义URL
1. 点击"自定义下载"按钮
2. 输入模型下载链接
3. 开始下载

支持的模型:
- tiny: 39MB (最快)
- base: 74MB (推荐)
- small: 244MB
- medium: 769MB
- large: 1550MB (最准确)

模型存储路径: {model_path}
        """.format(model_path=model_manager.model_path)
        
        QMessageBox.information(self, "手动下载帮助", help_text)
    
    def refresh_download_urls(self):
        """刷新下载地址"""
        try:
            QMessageBox.information(self, "刷新中", "正在刷新模型下载地址...")
            
            # 刷新URL缓存
            model_manager.refresh_download_urls()
            
            # 获取所有模型的URL信息
            urls = model_manager.get_dynamic_download_urls()
            
            # 显示URL信息
            url_info = "当前可用的下载地址:\n\n"
            
            for model_size, url_list in urls.items():
                url_info += f"{model_size} 模型:\n"
                
                # 测试每个URL的可用性
                for i, url in enumerate(url_list):
                    is_available = model_manager.test_url_availability(url)
                    status = "可用" if is_available else "不可用"
                    url_info += f"  {i+1}. [{status}] {url}\n"
                
                url_info += "\n"
            
            QMessageBox.information(self, "下载地址信息", url_info)
            
        except Exception as e:
            QMessageBox.warning(self, "刷新失败", f"刷新下载地址失败: {e}")
    
    def test_current_translator(self):
        """测试当前选择的翻译器"""
        translator_type = self.translator_type_combo.currentText()
        self.translator_status_label.setText(f"状态: {translator_type} 测试中...")
        self.setEnabled(False)

        def done(msg: str):
            # 根据结果设置状态
            if msg.startswith("✅"):
                self.translator_status_label.setText(f"状态: {translator_type} 可用")
                QMessageBox.information(self, "测试成功", msg)
            elif msg.startswith("⚠️"):
                self.translator_status_label.setText(f"状态: {translator_type} 异常")
                QMessageBox.warning(self, "测试提醒", msg)
            else:
                self.translator_status_label.setText(f"状态: {translator_type} 不可用")
                QMessageBox.warning(self, "测试失败", msg)
            self.setEnabled(True)

        th = TestTranslatorThread(translator_type, "Hello", "zh")
        th.finished_with_result.connect(done)
        th.start()
    
    def on_translator_changed(self):
        """翻译器选择改变时的处理"""
        translator_type = self.translator_type_combo.currentText()
        self.translator_status_label.setText(f"状态: {translator_type} (未测试)")
