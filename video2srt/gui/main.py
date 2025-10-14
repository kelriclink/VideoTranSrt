"""
GUI 主窗口
"""

import sys
import threading
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QLabel, QLineEdit, QComboBox,
                            QCheckBox, QProgressBar, QTextEdit, QFileDialog,
                            QMessageBox, QGroupBox, QGridLayout, QSpinBox, QMenuBar, QMenu, QDialog)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QIcon, QAction

from video2srt.core import Video2SRT
from video2srt.gui.config_dialog import ConfigDialog


class ProcessingThread(QThread):
    """处理线程"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    log_updated = pyqtSignal(str)
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, model_size, input_file, output_file, **kwargs):
        super().__init__()
        self.model_size = model_size
        self.input_file = input_file
        self.output_file = output_file
        self.kwargs = kwargs
    
    def run(self):
        try:
            # 透传回调
            def on_status(msg: str):
                self.status_updated.emit(msg)
                self.log_updated.emit(msg)
            def on_progress(val: int):
                self.progress_updated.emit(val)
            def on_log(msg: str):
                self.log_updated.emit(msg)

            self.status_updated.emit("开始处理...")
            self.progress_updated.emit(10)

            # 在子线程内部创建处理器，避免跨线程共享状态
            from video2srt.core import Video2SRT
            processor = Video2SRT(model_size=self.model_size)

            result_path = processor.process(
                self.input_file,
                output_path=self.output_file,
                status_callback=on_status,
                progress_callback=on_progress,
                log_callback=on_log,
                **self.kwargs
            )
            
            self.progress_updated.emit(100)
            self.status_updated.emit("处理完成!")
            self.finished.emit(str(result_path))
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class Video2SRTGUI(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.processor = None
        self.processing_thread = None
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("Video2SRT - 视频转字幕工具")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 文件选择组
        file_group = self.create_file_group()
        main_layout.addWidget(file_group)
        
        # 设置组
        settings_group = self.create_settings_group()
        main_layout.addWidget(settings_group)
        
        # 翻译组
        translation_group = self.create_translation_group()
        main_layout.addWidget(translation_group)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.process_btn = QPushButton("开始处理")
        self.process_btn.clicked.connect(self.start_processing)
        self.process_btn.setMinimumHeight(40)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_all)
        
        self.config_btn = QPushButton("设置")
        self.config_btn.clicked.connect(self.open_config)
        
        control_layout.addWidget(self.process_btn)
        control_layout.addWidget(self.clear_btn)
        control_layout.addWidget(self.config_btn)
        control_layout.addStretch()
        
        main_layout.addLayout(control_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 状态显示
        self.status_label = QLabel("就绪")
        main_layout.addWidget(self.status_label)
        
        # 日志显示
        log_group = QGroupBox("处理日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_group)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        open_action = QAction('打开文件', self)
        open_action.triggered.connect(self.select_input_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 设置（点击即打开配置对话框）
        settings_action = QAction('设置', self)
        settings_action.triggered.connect(self.open_config)
        menubar.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_file_group(self):
        """创建文件选择组"""
        group = QGroupBox("文件选择")
        layout = QGridLayout(group)
        
        # 输入文件
        layout.addWidget(QLabel("输入文件:"), 0, 0)
        self.input_file_edit = QLineEdit()
        self.input_file_edit.setPlaceholderText("选择视频或音频文件...")
        # 监听输入文件变化，自动更新输出文件名
        self.input_file_edit.textChanged.connect(self.on_input_file_changed)
        layout.addWidget(self.input_file_edit, 0, 1)
        
        self.input_file_btn = QPushButton("浏览...")
        self.input_file_btn.clicked.connect(self.select_input_file)
        layout.addWidget(self.input_file_btn, 0, 2)
        
        # 输出文件
        layout.addWidget(QLabel("输出文件:"), 1, 0)
        self.output_file_edit = QLineEdit()
        self.output_file_edit.setPlaceholderText("自动生成...")
        layout.addWidget(self.output_file_edit, 1, 1)
        
        self.output_file_btn = QPushButton("浏览...")
        self.output_file_btn.clicked.connect(self.select_output_file)
        layout.addWidget(self.output_file_btn, 1, 2)
        
        return group
    
    def create_settings_group(self):
        """创建设置组"""
        group = QGroupBox("识别设置")
        layout = QGridLayout(group)
        
        # 模型选择
        layout.addWidget(QLabel("模型大小:"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)  # 允许用户编辑
        
        # 使用插件系统获取所有可用的模型
        from ..plugin_download_manager import get_download_manager
        download_manager = get_download_manager()
        all_models = download_manager.get_all_models()
        
        # 仅按标准 Whisper 分类添加模型
        for model_name, model_info in all_models.items():
            if model_name.endswith('.en'):
                type_label = "英语专用"
            else:
                type_label = "多语言"
            display_text = f"{model_name} ({type_label})"
            self.model_combo.addItem(display_text)
        
        self.model_combo.setCurrentText('base (多语言)')
        self.model_combo.setToolTip("选择 Whisper 模型：\n• .en 模型：英语专用，准确性更高\n• 多语言模型：支持多种语言")
        layout.addWidget(self.model_combo, 0, 1)
        
        # 语言选择
        layout.addWidget(QLabel("源语言:"), 1, 0)
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            'auto (自动检测)', 'zh (中文)', 'en (英语)', 'ja (日语)', 
            'ko (韩语)', 'fr (法语)', 'de (德语)', 'es (西班牙语)', 'ru (俄语)'
        ])
        layout.addWidget(self.language_combo, 1, 1)
        
        return group
    
    def create_translation_group(self):
        """创建翻译组"""
        group = QGroupBox("翻译设置")
        layout = QGridLayout(group)
        
        # 翻译开关
        self.translate_checkbox = QCheckBox("启用翻译")
        self.translate_checkbox.toggled.connect(self.toggle_translation)
        layout.addWidget(self.translate_checkbox, 0, 0, 1, 2)
        
        # 目标语言
        layout.addWidget(QLabel("目标语言:"), 1, 0)
        self.target_language_combo = QComboBox()
        self.target_language_combo.addItems([
            'en (英语)', 'zh (中文)', 'ja (日语)', 'ko (韩语)',
            'fr (法语)', 'de (德语)', 'es (西班牙语)', 'ru (俄语)'
        ])
        self.target_language_combo.setEnabled(False)
        layout.addWidget(self.target_language_combo, 1, 1)
        
        # 双语字幕
        self.bilingual_checkbox = QCheckBox("双语字幕")
        self.bilingual_checkbox.setEnabled(False)
        layout.addWidget(self.bilingual_checkbox, 2, 0, 1, 2)
        
        return group
    
    def select_input_file(self):
        """选择输入文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频或音频文件",
            "",
            "音视频文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.mp3 *.wav *.m4a *.aac *.ogg *.flac);;所有文件 (*)"
        )
        
        if file_path:
            self.input_file_edit.setText(file_path)
            # 自动设置输出文件名（每次选择都更新）
            output_path = Path(file_path).with_suffix('.srt')
            self.output_file_edit.setText(str(output_path))
    
    def select_output_file(self):
        """选择输出文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存字幕文件",
            "",
            "SRT 文件 (*.srt);;所有文件 (*)"
        )
        
        if file_path:
            self.output_file_edit.setText(file_path)
    
    def on_input_file_changed(self, text):
        """输入文件变化时的处理"""
        if text.strip():
            try:
                # 检查是否是有效的文件路径
                input_path = Path(text.strip())
                if input_path.exists() and input_path.is_file():
                    # 自动更新输出文件名
                    output_path = input_path.with_suffix('.srt')
                    self.output_file_edit.setText(str(output_path))
            except Exception:
                # 如果路径无效，不更新输出文件名
                pass
    
    def toggle_translation(self, checked):
        """切换翻译功能"""
        self.target_language_combo.setEnabled(checked)
        self.bilingual_checkbox.setEnabled(checked)
    
    def start_processing(self):
        """开始处理"""
        # 验证输入
        input_file = self.input_file_edit.text().strip()
        if not input_file:
            QMessageBox.warning(self, "警告", "请选择输入文件!")
            return
        
        if not Path(input_file).exists():
            QMessageBox.warning(self, "警告", "输入文件不存在!")
            return
        
        # 获取设置
        model_text = self.model_combo.currentText()
        # 从显示文本中提取模型名称
        model_size = model_text
        
        # 定义所有可能的标签
        labels_to_remove = [
            ' (Distil-Whisper)',
            ' (Intel优化)',
            ' (英语专用)',
            ' (多语言)',
            ' (Distil-Whisper (Intel GPU))',
            ' (Intel优化 (Intel GPU))',
            ' (英语专用 (Intel GPU))',
            ' (多语言 (Intel GPU))'
        ]
        
        # 移除标签获取模型名称
        for label in labels_to_remove:
            if model_text.endswith(label):
                model_size = model_text.replace(label, '')
                break
        
        # 如果没有匹配的标签，尝试提取括号前的内容
        if model_size == model_text and '(' in model_text and ')' in model_text:
            # 提取第一个括号前的内容
            model_size = model_text.split(' (')[0]
        
        source_language = self.language_combo.currentText().split()[0]
        if source_language == 'auto':
            source_language = None
        
        output_file = self.output_file_edit.text().strip() or None
        
        # 翻译设置
        translate = None
        bilingual = False
        if self.translate_checkbox.isChecked():
            target_lang = self.target_language_combo.currentText().split()[0]
            translate = target_lang
            bilingual = self.bilingual_checkbox.isChecked()
        
        # 创建处理线程
        self.processing_thread = ProcessingThread(
            model_size,
            input_file,
            output_file,
            language=source_language,
            translate=translate,
            bilingual=bilingual
        )
        
        # 连接信号
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.status_updated.connect(self.update_status)
        self.processing_thread.log_updated.connect(self.append_log)
        self.processing_thread.finished.connect(self.processing_finished)
        self.processing_thread.error_occurred.connect(self.processing_error)
        
        # 开始处理
        self.process_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        
        self.processing_thread.start()
    
    def update_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)
    
    def update_status(self, message):
        """更新状态"""
        self.status_label.setText(message)
        self.log_text.append(message)

    def append_log(self, message: str):
        """追加日志"""
        self.log_text.append(message)
    
    def processing_finished(self, result_path):
        """处理完成"""
        self.process_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        QMessageBox.information(
            self, 
            "完成", 
            f"字幕文件已生成:\n{result_path}"
        )
    
    def processing_error(self, error_message):
        """处理错误"""
        self.process_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(
            self, 
            "错误", 
            f"处理过程中出现错误:\n{error_message}"
        )
    
    def clear_all(self):
        """清空所有"""
        self.input_file_edit.clear()
        self.output_file_edit.clear()
        self.log_text.clear()
        self.progress_bar.setVisible(False)
        self.status_label.setText("就绪")
    
    def open_config(self):
        """打开配置对话框"""
        dialog = ConfigDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 配置已保存，可以在这里添加刷新逻辑
            self.log_text.append("配置已更新")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 Video2SRT",
            """
            <h3>Video2SRT v1.0.0</h3>
            <p>智能视频/音频转字幕工具</p>
            <p>基于 OpenAI Whisper 的语音识别</p>
            <p>支持多种翻译服务</p>
            <p>作者: Your Name</p>
            <p>GitHub: https://github.com/yourusername/video2srt</p>
            """
        )


def main():
    """启动 GUI"""
    app = QApplication(sys.argv)
    app.setApplicationName("Video2SRT")
    app.setApplicationVersion("1.0.0")
    
    window = Video2SRTGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
