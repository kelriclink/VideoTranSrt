"""
测试模块
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from video2srt.core import Video2SRT
from video2srt.formatter import SRTFormatter


class TestSRTFormatter:
    """SRT 格式化器测试"""
    
    def test_format_time(self):
        """测试时间格式化"""
        assert SRTFormatter.format_time(0) == "00:00:00,000"
        assert SRTFormatter.format_time(65.5) == "00:01:05,500"
        assert SRTFormatter.format_time(3661.123) == "01:01:01,123"
    
    def test_format_segment(self):
        """测试分段格式化"""
        segment = {
            "start": 10.5,
            "end": 15.2,
            "text": "Hello world"
        }
        
        result = SRTFormatter.format_segment(segment, 1)
        expected = "1\n00:00:10,500 --> 00:00:15,200\nHello world\n"
        
        assert result == expected
    
    def test_format_segments(self):
        """测试多分段格式化"""
        segments = [
            {"start": 0, "end": 5, "text": "First segment"},
            {"start": 5, "end": 10, "text": "Second segment"}
        ]
        
        result = SRTFormatter.format_segments(segments)
        assert "First segment" in result
        assert "Second segment" in result
        assert result.count("-->") == 2


class TestVideo2SRT:
    """Video2SRT 主类测试"""
    
    def test_init(self):
        """测试初始化"""
        processor = Video2SRT(model_size="base")
        assert processor.model_size == "base"
        assert processor.translator_type == "google"
    
    def test_supported_formats(self):
        """测试支持的格式"""
        processor = Video2SRT()
        formats = processor.get_supported_formats()
        
        assert ".mp4" in formats
        assert ".mp3" in formats
        assert ".wav" in formats
    
    def test_is_supported_format(self):
        """测试格式检查"""
        processor = Video2SRT()
        
        assert processor.is_supported_format("test.mp4")
        assert processor.is_supported_format("test.MP4")  # 大小写不敏感
        assert not processor.is_supported_format("test.txt")


@pytest.fixture
def temp_audio_file():
    """创建临时音频文件"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        # 写入一些假数据
        f.write(b"fake audio data")
        temp_path = f.name
    
    yield temp_path
    
    # 清理
    os.unlink(temp_path)


class TestIntegration:
    """集成测试"""
    
    @patch('video2srt.transcriber.whisper.load_model')
    def test_process_with_mock(self, mock_load_model, temp_audio_file):
        """使用模拟对象测试处理流程"""
        # 模拟 whisper 模型
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "Hello world",
            "language": "en",
            "segments": [
                {"start": 0, "end": 2, "text": "Hello world"}
            ]
        }
        mock_load_model.return_value = mock_model
        
        # 创建处理器
        processor = Video2SRT(model_size="tiny")
        
        # 模拟音频提取
        with patch('video2srt.audio_extractor.AudioExtractor') as mock_extractor:
            mock_extractor.return_value.__enter__.return_value.extract_audio.return_value = temp_audio_file
            
            # 执行处理
            result_path = processor.process(temp_audio_file)
            
            # 验证结果
            assert Path(result_path).exists()
            assert result_path.endswith('.srt')
            
            # 验证模型被调用
            mock_model.transcribe.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
