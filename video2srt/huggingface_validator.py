"""
Hugging Face 模型文件验证器
用于在下载前验证模型文件的实际存在性，避免404错误
"""

import requests
import json
from typing import List, Dict, Set, Optional, Tuple
import urllib3
import ssl

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context


class HuggingFaceValidator:
    """Hugging Face 模型文件验证器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        
    def get_model_files(self, model_name: str) -> Optional[Set[str]]:
        """
        获取Hugging Face模型的实际文件列表
        
        Args:
            model_name: 模型名称，格式如 "distil-whisper/distil-large-v3.5"
            
        Returns:
            文件名集合，如果获取失败返回None
        """
        try:
            api_url = f"https://huggingface.co/api/models/{model_name}/tree/main"
            response = self.session.get(api_url, timeout=10)
            response.raise_for_status()
            
            files_data = response.json()
            file_names = set()
            
            for item in files_data:
                if item.get("type") == "file":
                    file_names.add(item.get("path", ""))
            
            return file_names
            
        except Exception as e:
            print(f"获取模型文件列表失败 {model_name}: {e}")
            return None
    
    def validate_file_list(self, model_name: str, expected_files: List[str]) -> Tuple[bool, Dict[str, str]]:
        """
        验证模型的预期文件列表与实际文件列表是否匹配
        
        Args:
            model_name: 模型名称
            expected_files: 预期的文件列表
            
        Returns:
            (是否完全匹配, 详细报告)
        """
        actual_files = self.get_model_files(model_name)
        
        if actual_files is None:
            return False, {"error": "无法获取实际文件列表"}
        
        expected_set = set(expected_files)
        missing_files = expected_set - actual_files
        extra_files = actual_files - expected_set
        
        report = {
            "model_name": model_name,
            "expected_count": len(expected_files),
            "actual_count": len(actual_files),
            "missing_files": list(missing_files),
            "extra_files": list(extra_files),
            "is_valid": len(missing_files) == 0
        }
        
        return len(missing_files) == 0, report
    
    def get_corrected_file_list(self, model_name: str, expected_files: List[str]) -> Optional[List[str]]:
        """
        获取修正后的文件列表（移除不存在的文件）
        
        Args:
            model_name: 模型名称
            expected_files: 预期的文件列表
            
        Returns:
            修正后的文件列表，如果获取失败返回None
        """
        actual_files = self.get_model_files(model_name)
        
        if actual_files is None:
            return None
        
        # 只保留实际存在的文件
        corrected_files = [f for f in expected_files if f in actual_files]
        return corrected_files
    
    def validate_download_urls(self, model_name: str, download_urls: List[str]) -> Tuple[bool, Dict[str, str]]:
        """
        验证下载URL列表中的文件是否都存在
        
        Args:
            model_name: 模型名称
            download_urls: 下载URL列表
            
        Returns:
            (是否全部有效, 详细报告)
        """
        # 从URL中提取文件名
        expected_files = []
        for url in download_urls:
            if "/resolve/main/" in url:
                filename = url.split("/resolve/main/")[-1]
                expected_files.append(filename)
        
        return self.validate_file_list(model_name, expected_files)
    
    def print_validation_report(self, report: Dict[str, str]):
        """打印验证报告"""
        print(f"\n=== 模型文件验证报告: {report['model_name']} ===")
        print(f"预期文件数量: {report['expected_count']}")
        print(f"实际文件数量: {report['actual_count']}")
        print(f"验证结果: {'✅ 通过' if report['is_valid'] else '❌ 失败'}")
        
        if report['missing_files']:
            print(f"\n缺失文件 ({len(report['missing_files'])}):")
            for file in report['missing_files']:
                print(f"  - {file}")
        
        if report['extra_files']:
            print(f"\n额外文件 ({len(report['extra_files'])}):")
            for file in report['extra_files']:
                print(f"  + {file}")
        
        if 'error' in report:
            print(f"\n错误: {report['error']}")


def validate_model_files(model_name: str, expected_files: List[str]) -> bool:
    """
    便捷函数：验证模型文件
    
    Args:
        model_name: 模型名称
        expected_files: 预期文件列表
        
    Returns:
        是否验证通过
    """
    validator = HuggingFaceValidator()
    is_valid, report = validator.validate_file_list(model_name, expected_files)
    validator.print_validation_report(report)
    return is_valid


if __name__ == "__main__":
    # 测试代码
    validator = HuggingFaceValidator()
    
    # 测试 distil-large-v3.5
    test_files = [
        "config.json",
        "generation_config.json", 
        "merges.txt",
        "model.safetensors",
        "preprocessor_config.json",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.json",
        "normalizer.json"  # 这个文件不存在
    ]
    
    is_valid, report = validator.validate_file_list("distil-whisper/distil-large-v3.5", test_files)
    validator.print_validation_report(report)
    
    # 获取修正后的文件列表
    corrected_files = validator.get_corrected_file_list("distil-whisper/distil-large-v3.5", test_files)
    if corrected_files:
        print(f"\n修正后的文件列表:")
        for file in corrected_files:
            print(f"  - {file}")