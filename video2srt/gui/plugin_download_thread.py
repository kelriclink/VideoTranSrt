"""
插件化模型下载线程
用于在GUI中异步下载模型
"""

from PyQt6.QtCore import QThread, pyqtSignal
from ..plugin_download_manager import get_download_manager


class PluginDownloadThread(QThread):
    """插件化模型下载线程"""
    
    progress_updated = pyqtSignal(str, int, str)  # model_name, progress, status
    finished_with_result = pyqtSignal(str, bool)  # model_name, success
    
    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name
        self.download_manager = get_download_manager()
    
    def run(self):
        """执行下载"""
        try:
            def progress_callback(model_name, progress, message):
                self.progress_updated.emit(model_name, progress, message)
            
            success = self.download_manager.download_model(
                self.model_name, 
                progress_callback
            )
            
            self.finished_with_result.emit(self.model_name, success)
            
        except Exception as e:
            self.progress_updated.emit(self.model_name, 0, f"下载失败: {str(e)}")
            self.finished_with_result.emit(self.model_name, False)