"""
GUI 小部件
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt


class StatusWidget(QWidget):
    """状态显示小部件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
    
    def set_status(self, message):
        self.status_label.setText(message)


class FileSelectorWidget(QWidget):
    """文件选择小部件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        self.file_label = QLabel("未选择文件")
        self.select_btn = QPushButton("选择文件")
        
        layout.addWidget(self.file_label)
        layout.addWidget(self.select_btn)
    
    def set_file(self, file_path):
        self.file_label.setText(file_path)
    
    def get_file(self):
        return self.file_label.text()
