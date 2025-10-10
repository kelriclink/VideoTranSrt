#!/usr/bin/env python3
"""
测试新的插件目录结构
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_plugin_discovery():
    """测试插件发现功能"""
    print("=== 测试插件发现功能 ===")
    
    try:
        from video2srt.plugins.manager import PluginManager
        
        # 创建插件管理器
        manager = PluginManager()
        
        # 发现插件
        manager.discover_plugins()
        
        # 检查已注册的插件
        plugin_names = manager.list_plugins()
        print(f"发现的插件数量: {len(plugin_names)}")
        
        for plugin_name in plugin_names:
            print(f"  - {plugin_name}")
            
        return len(plugin_names) > 0
        
    except Exception as e:
        print(f"插件发现测试失败: {e}")
        return False

def test_model_loader_factory():
    """测试ModelLoaderFactory功能"""
    print("\n=== 测试ModelLoaderFactory功能 ===")
    
    try:
        from video2srt.model_loaders import create_loader
        
        # 测试不同的模型类型
        test_cases = [
            ("tiny", "标准Whisper tiny模型"),
            ("base", "标准Whisper base模型"),
            ("small", "标准Whisper small模型"),
            ("medium", "标准Whisper medium模型"),
            ("large", "标准Whisper large模型"),
            ("large-v2", "标准Whisper large-v2模型"),
            ("large-v3", "标准Whisper large-v3模型"),
        ]
        
        success_count = 0
        for model_size, description in test_cases:
            try:
                loader = create_loader(model_size)
                if loader:
                    print(f"  ✓ {model_size} ({description}): {loader.__class__.__name__}")
                    success_count += 1
                else:
                    print(f"  ✗ {model_size} ({description}): 返回None")
            except Exception as e:
                print(f"  ✗ {model_size} ({description}): {e}")
        
        print(f"\n成功创建加载器: {success_count}/{len(test_cases)}")
        return success_count > 0
        
    except Exception as e:
        print(f"ModelLoaderFactory测试失败: {e}")
        return False

def test_unsupported_model():
    """测试不支持的模型"""
    print("\n=== 测试不支持的模型 ===")
    
    try:
        from video2srt.model_loaders import create_loader
        
        # 测试不支持的模型
        unsupported_models = [
            "unsupported-model",
            "fake/model",
            "invalid-size"
        ]
        
        for model in unsupported_models:
            try:
                loader = create_loader(model)
                if loader is None:
                    print(f"  ✓ {model}: 正确返回None")
                else:
                    print(f"  ✗ {model}: 意外返回了加载器 {loader.__class__.__name__}")
            except Exception as e:
                print(f"  ✓ {model}: 正确抛出异常 - {e}")
        
        return True
        
    except Exception as e:
        print(f"不支持模型测试失败: {e}")
        return False

def test_plugin_environment_validation():
    """测试插件环境验证"""
    print("\n=== 测试插件环境验证 ===")
    
    try:
        from video2srt.plugins.manager import PluginManager
        
        manager = PluginManager()
        manager.discover_plugins()
        
        plugin_names = manager.list_plugins()
        
        for plugin_name in plugin_names:
            try:
                # 创建临时实例来验证环境
                plugin_class = manager._plugins[plugin_name]
                plugin_instance = plugin_class("dummy")
                is_valid = plugin_instance.validate_environment()
                print(f"  {plugin_name}: 环境验证 {'✓' if is_valid else '✗'}")
            except Exception as e:
                print(f"  {plugin_name}: 环境验证异常 - {e}")
        
        return True
        
    except Exception as e:
        print(f"环境验证测试失败: {e}")
        return False

def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试向后兼容性 ===")
    
    try:
        # 测试旧的导入方式
        from video2srt.model_loaders import ModelLoaderFactory
        
        # 测试静态方法
        loader = ModelLoaderFactory.create_loader("tiny")
        if loader:
            print("  ✓ 向后兼容性测试通过")
            return True
        else:
            print("  ✗ 向后兼容性测试失败: 返回None")
            return False
            
    except Exception as e:
        print(f"向后兼容性测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试新的插件目录结构...")
    
    tests = [
        ("插件发现", test_plugin_discovery),
        ("ModelLoaderFactory", test_model_loader_factory),
        ("不支持的模型", test_unsupported_model),
        ("环境验证", test_plugin_environment_validation),
        ("向后兼容性", test_backward_compatibility),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"{test_name}测试出现异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    print("\n" + "="*50)
    print("测试结果汇总:")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试都通过了！新的插件目录结构工作正常。")
    else:
        print("⚠️  部分测试失败，请检查插件配置。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)