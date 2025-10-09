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
        # 使用配置文件中的实际默认值
        assert processor.translator_type == "openai"
    
    def test_supported_formats(self):
        """测试支持的格式"""
        processor = Video2SRT()
        formats = processor.get_supported_formats()
        
        # 这些是输出格式，不是输入格式
        assert "srt" in formats
        assert "vtt" in formats
        assert "ass" in formats
    
    def test_is_supported_format(self):
        """测试格式检查"""
        processor = Video2SRT()
        
        # 测试支持的输出格式
        assert processor.is_supported_format("test.srt")
        assert processor.is_supported_format("test.vtt")
        assert processor.is_supported_format("test.ass")
        
        # 测试不支持的格式
        assert not processor.is_supported_format("test.txt")


@pytest.fixture
def test_video_file():
    """使用真实的测试视频文件"""
    test_file = Path("testvideo/1351956921-1-192.mp4")
    if test_file.exists():
        return str(test_file)
    else:
        pytest.skip("测试视频文件不存在")


class TestIntegration:
    """集成测试"""
    
    @patch('video2srt.transcriber.whisper.load_model')
    def test_process_with_mock(self, mock_load_model, test_video_file):
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
        
        # 执行处理（使用真实视频文件，但模拟转录）
        result_path = processor.process(test_video_file)
        
        # 验证结果
        assert Path(result_path).exists()
        assert str(result_path).endswith('.srt')
        
        # 验证模型被调用
        mock_model.transcribe.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
