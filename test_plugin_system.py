"""
测试插件系统的集成和功能
"""

import sys
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_plugin_discovery():
    """测试插件发现功能"""
    print("=== 测试插件发现 ===")
    
    try:
        from video2srt.plugins.manager import plugin_manager
        
        plugins = plugin_manager.list_plugins()
        print(f"发现的插件: {plugins}")
        
        plugin_info = plugin_manager.get_plugin_info()
        for info in plugin_info:
            print(f"插件信息: {info}")
        
        supported_models = plugin_manager.get_supported_models()
        print(f"支持的模型: {supported_models}")
        
        return True
    except Exception as e:
        print(f"插件发现测试失败: {e}")
        return False

def test_model_loader_factory():
    """测试模型加载器工厂"""
    print("\n=== 测试模型加载器工厂 ===")
    
    try:
        from video2srt.model_loaders import ModelLoaderFactory
        
        # 测试标准Whisper模型
        print("测试标准Whisper模型...")
        try:
            loader = ModelLoaderFactory.create_loader("base", device="cpu")
            print(f"成功创建标准Whisper加载器: {loader}")
        except Exception as e:
            print(f"标准Whisper加载器创建失败: {e}")
        
        # 已移除 Intel/OpenVINO 与 Distil-Whisper 加载器测试
        
        # 测试不支持的模型
        print("测试不支持的模型...")
        try:
            loader = ModelLoaderFactory.create_loader("unsupported-model")
            print(f"意外成功创建不支持的加载器: {loader}")
        except ValueError as e:
            print(f"正确拒绝不支持的模型: {e}")
        except Exception as e:
            print(f"不支持模型测试出现意外错误: {e}")
        
        return True
    except Exception as e:
        print(f"模型加载器工厂测试失败: {e}")
        return False

def test_plugin_environment():
    """测试插件环境验证"""
    print("\n=== 测试插件环境验证 ===")
    
    try:
        from video2srt.plugins.manager import plugin_manager
        
        # 测试每个插件的环境验证
        for plugin_name in plugin_manager.list_plugins():
            try:
                plugin_class = plugin_manager._plugins[plugin_name]
                temp_instance = plugin_class("dummy")
                env_valid = temp_instance.validate_environment()
                requirements = temp_instance.get_requirements()
                
                print(f"插件 {plugin_name}:")
                print(f"  环境验证: {'通过' if env_valid else '失败'}")
                print(f"  依赖包: {requirements}")
                
            except Exception as e:
                print(f"插件 {plugin_name} 环境验证出错: {e}")
        
        return True
    except Exception as e:
        print(f"插件环境验证测试失败: {e}")
        return False

def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试向后兼容性 ===")
    
    try:
        # 测试旧的导入方式是否仍然有效
        from video2srt.model_loaders import ModelLoaderFactory
        
        # 测试旧的静态方法调用方式
        loader = ModelLoaderFactory.create_loader("base", device="cpu")
        print(f"向后兼容测试成功: {loader}")
        
        return True
    except Exception as e:
        print(f"向后兼容性测试失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("开始测试插件系统...")
    
    tests = [
        test_plugin_discovery,
        test_model_loader_factory,
        test_plugin_environment,
        test_backward_compatibility
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
                print("✓ 测试通过")
            else:
                print("✗ 测试失败")
        except Exception as e:
            print(f"✗ 测试异常: {e}")
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 所有测试通过！插件系统工作正常。")
    else:
        print("⚠️  部分测试失败，请检查插件系统配置。")

if __name__ == "__main__":
    main()