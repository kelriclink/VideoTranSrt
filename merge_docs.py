import os
import glob
import shutil

# 确保doc目录存在
os.makedirs('doc', exist_ok=True)

# 创建主文档文件
main_doc_path = os.path.join('doc', 'documentation.md')
with open(main_doc_path, 'w', encoding='utf-8') as main_doc:
    main_doc.write("# VideoTransRT 文档\n\n## 目录\n")
    
    # 获取所有MD文件（排除README.md和doc目录下的文件）
    md_files = [f for f in glob.glob("*.md") if f != "README.md" and not f.startswith("doc/")]
    
    # 先处理README.md（如果存在）
    if os.path.exists("README.md"):
        md_files = ["README.md"] + md_files
    
    # 为每个文件创建目录条目
    for md_file in md_files:
        section_name = os.path.splitext(md_file)[0].replace('_', ' ').title()
        anchor = section_name.lower().replace(' ', '-')
        main_doc.write(f"- [{section_name}](#{anchor})\n")
    
    main_doc.write("\n")
    
    # 合并所有MD文件内容
    for md_file in md_files:
        section_name = os.path.splitext(md_file)[0].replace('_', ' ').title()
        main_doc.write(f"## {section_name}\n\n")
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 移除文件开头的标题（如果有）
                lines = content.split('\n')
                if lines and lines[0].startswith('# '):
                    content = '\n'.join(lines[1:])
                main_doc.write(content.strip() + "\n\n")
        except Exception as e:
            main_doc.write(f"*无法读取 {md_file}: {str(e)}*\n\n")

    main_doc.write("\n\n---\n\n*此文档由合并脚本自动生成*")

print(f"已创建合并文档: {main_doc_path}")

# 创建备份目录
backup_dir = os.path.join('doc', 'md_backup')
os.makedirs(backup_dir, exist_ok=True)

# 备份并删除原始MD文件
for md_file in glob.glob("*.md"):
    try:
        # 备份文件
        shutil.copy2(md_file, os.path.join(backup_dir, md_file))
        print(f"已备份: {md_file} -> {os.path.join(backup_dir, md_file)}")
        
        # 删除原始文件
        os.remove(md_file)
        print(f"已删除: {md_file}")
    except Exception as e:
        print(f"处理 {md_file} 时出错: {str(e)}")

print(f"所有MD文件已备份到: {backup_dir}")
print("合并和清理完成!")