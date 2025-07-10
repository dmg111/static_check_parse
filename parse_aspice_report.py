#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @author: 800518
# @time: 2025/6/5 17:40
import datetime
import hashlib
import json
import logging
import os
import re
import shutil
import time
from pathlib import Path
import pandas as pd
import argparse
from typing import Text


report_path = r"/home/workspace/perception/.vscode/static_check_parse/data/perception_rule+DEVOPS专用勿动!!! (18).csv" # Coverity生成的静态代码检查报告路径
source_path = r"/home/workspace/perception"  # 源代码根路径
backup = True  # 是否创建备份文件
init_state_file_flag = True # 是否初始化状态文件
expect_checker = []
# expect_checker = ["AUTOSAR C++14 A1-1-1"] # 期望的检查器列表，示例：只处理AUTOSAR C++14 M5-0-4检查器
expect_checker = ["AUTOSAR C++14 M5-0-4", "AUTOSAR C++14 M5-0-6", "AUTOSAR C++14 M5-0-3", "AUTOSAR C++14 M5-0-5", "AUTOSAR C++14 A4-7-1"] # 期望的检查器列表，示例：只处理AUTOSAR C++14 M5-0-4检查器
state_path_file = r"\static_check_parse\data\state_file"  # 状态文件路径
file_info_path = r"\static_check_parse\result\file_info.json"  # 放入提示词中的文件信息路径
_filter_path = ""  # 过滤路径，示例：只处理包含static_object的文件
_filter_Log = False # 是否过滤掉LOG相关的行
SKIP_LOG_NUM = 0 # 跳过的LOG行数


# LOG检测相关配置
LOG_PATTERNS = [
    r'LOG_\w+\s*\(',   # 匹配 LOG_INFO(...)、LOG_ERROR(...) 等函数调用形式
    r'LOG_\w+\s*<<',   # 匹配 LOG_INFO << ...、LOG_ERROR << ... 等流式日志输出
]


def timestamp_to_md5():
    # 获取当前时间戳（精确到毫秒）
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
    
    # 计算MD5哈希值
    md5_hash = hashlib.md5(timestamp.encode('utf-8')).hexdigest()
    return md5_hash
unique_id = timestamp_to_md5()[:4]
print("生成的唯一标识符:", unique_id)

def root_path():
    """ 获取 根路径： /static-modeling/scripts/tools """
    path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # '/home/d800518/static-modeling/scripts/tools'
    # path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) # '/home/d800518/static-modeling'
    return path

def ensure_path_sep(path: Text) -> Text:
    """兼容 windows 和 linux 不同环境的操作系统路径 """
    if "/" in path:
        path = os.sep.join(path.split("/"))

    if "\\" in path:
        path = os.sep.join(path.split("\\"))

    return root_path() + path

def backup_file(file_path: str, unique_id) -> None:
    """备份文件（单文件备份"""
    if not os.path.exists(file_path):
        logging.warning(f"待备份文件不存在: {file_path}")
        return

    # 生成相对路径，去除 source_path 前缀
    if source_path in file_path:
        rel_path = os.path.relpath(file_path, source_path)
    else:
        rel_path = file_path
    backup_dir = os.path.join(source_path, f'backup_{unique_id}')
    backup_file_path = os.path.join(backup_dir, rel_path)
    os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
    try:
        with open(file_path, 'r', encoding='utf-8') as src_file, \
             open(backup_file_path, 'w', encoding='utf-8') as backup_file:
            backup_file.writelines(src_file.readlines())
        logging.debug(f"为 {file_path} 创建备份文件: {backup_file_path}")
    except Exception as e:
        logging.error(f"备份文件 {file_path} 失败: {e}")

def create_backup(src: str, backup: bool = True) -> None:
    # 创建源文件夹的备份
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    dst = f"{src}.bak_{timestamp}"
    if not backup:
        print("备份已关闭，跳过备份步骤")
        return

    if not os.path.exists(src):
        print(f"源文件夹 {src} 不存在！")
    else:
        shutil.copytree(src, dst)
        print(f"已备份 {src} 到 {dst}")

def parse_csv_report(report_path: str, expect_checker:list=None) -> dict:
    """解析CSV格式的静态代码检测报告，提取问题行信息"""
    issues = {}
    try:
        df = pd.read_csv(report_path)
        for index, row in df.iterrows():
            try:
                issue_path = row['文件']
                issue_func = row['函数']
                issue_checker = row['检查器']
                issue_line = row['行号']
                if not str(issue_line).isdigit():
                    logging.error(f"第{index}行的行号不是数字: {issue_line}")
                    continue
            except Exception as e:
                logging.warning(f"解析行 {index} 失败: {e}")
                continue
            # expect_checker = ["AUTOSAR C++14 M5-0-4"]
            if expect_checker and issue_checker not in expect_checker:
                continue
            # 规范文件路径
            issue_path = os.path.normpath(issue_path)
            # 将问题添加到对应文件的问题列表中
            if issue_path not in issues:
                # 使用字典结构：行号 -> 描述列表
                issues[issue_path] = {}
            # 确保行号对应的描述列表存在
            if issue_line not in issues[issue_path]:
                issues[issue_path][issue_line] = []
            # 添加描述（去重处理）
            if issue_checker not in issues[issue_path][issue_line]:
                issues[issue_path][issue_line].append(issue_checker)
    except Exception as e:
        logging.error(f"解析报告失败: {e}")
        return {}
    return issues

def load_processed_issues(state_file: str) -> dict:
    """加载已处理问题的状态"""
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"加载状态文件 {state_file} 失败: {e}")
    # 创建并初始化空的状态文件
    initialize_state_file(state_file)
    return {}

def initialize_state_file(state_file: str, init_flag: bool=False) -> None:
    """初始化空的状态文件"""
    if init_flag and os.path.exists(state_file):
        os.remove(state_file)
        logging.info(f"已删除文件: {state_file}")

    if not os.path.exists(state_file):
        try:
            # 确保目录存在
            state_dir = os.path.dirname(state_file)
            if state_dir and not os.path.exists(state_dir):
                os.makedirs(state_dir, exist_ok=True)

            # 创建空的状态文件
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            logging.debug(f"创建新的状态文件: {state_file}")
        except Exception as e:
            logging.error(f"创建状态文件 {state_file} 失败: {e}")

def save_processed_issues(state_file: str, processed: dict) -> None:
    """保存已处理问题的状态"""
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(processed, f, indent=2)
    except Exception as e:
        logging.error(f"保存状态文件 {state_file} 失败: {e}")

def generate_issue_key(line_num: int, description: str) -> str:
    """生成问题的唯一标识键，使用行号和描述"""
    return f"{line_num}_{description}"
    # return md5(f"{file_path}_{line_hash}_{description}".encode('utf-8')).hexdigest()

def get_processed_issues(file_path: str, state: dict) -> list:
    """获取文件已处理的问题"""
    file_state = state.get(file_path, {})
    return file_state.get('issues', [])

def extract_issue_description(text: str) -> str:
    """从注释中提取问题描述内容（精确模式）"""
    # 匹配 [问题开始  #] 之后、[问题结束] 之前的内容
    pattern = fr'\[问题开始\s*\#{unique_id}\]\s*(.*?)\s*\[问题结束\]'
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return ""

def annotate_file(file_path: str, issues: dict, state_file: str) -> bool:
    """在C++文件中添加问题注释，使用状态文件避免重复添加"""
    global SKIP_LOG_NUM
    state = load_processed_issues(state_file)
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # 跟踪实际添加的注释数量
        comments_added = 0
        # 按行号降序排列，以便在插入注释后不影响后续行号
        issues_sorted = sorted(issues.keys(), reverse=True)
        target_contents = []
        # 添加注释
        for line_num in issues_sorted:
            descriptions = ', '.join(issues[line_num])
            issue_key = generate_issue_key(line_num, descriptions)
            # 若已经回填过注释，则在state文件中存在
            if state and file_path in state and issue_key in state[file_path]["his_version_issues"]:
                logging.debug(f"跳过已处理的问题: {file_path}:{line_num} - {descriptions}")
                continue
            # 若为打印日志行，则跳过
            if _filter_Log and any(re.search(pattern, lines[line_num - 1]) for pattern in LOG_PATTERNS):
                SKIP_LOG_NUM += 1
                logging.debug(f"跳过打印日志行: {file_path}:{line_num} - {lines[line_num - 1].strip()}")
                continue

            # 构造注释行，包含唯一标识符，
            comment_line = f"// [问题开始  #{unique_id}]{line_num}_{descriptions}  [问题结束]\n"
            # 保存注释行和内容行
            target_contents.append(comment_line)
            target_contents.append(lines[line_num - 1].rstrip('\n'))

            # 在问题行之前插入注释
            lines.insert(line_num - 1, comment_line)
            comments_added += 1
            # 更新行状态
            if file_path not in state:
                state[file_path] = {
                    'his_version_issues': [],  # 历史问题
                    'new_lines': {}  # 添加注释后的行
                }
            # 记录处理的问题
            state[file_path]['his_version_issues'].append(issue_key)
            state[file_path]['new_lines'][issue_key] = {
                'comment_line': ''
            }

        # 只有在实际添加了注释时才写回文件
        if comments_added > 0:
            # 更新注释所在行标
            line_caches = {}
            for i, line in enumerate(lines, 1):
                temp = extract_issue_description(line)
                if temp and temp in state[file_path]['new_lines']:
                    state[file_path]['new_lines'][temp]['comment_line'] = i

            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            logging.debug(f"为 {file_path} 添加了 {comments_added} 个注释")
            # 保存更新后的状态
            save_processed_issues(state_file, state)
            return True
        else:
            logging.debug(f"{file_path} 不需要添加新注释")
            return False
    except IndexError as e:
        logging.error(f"处理文件 {file_path} 时发生索引错误: {e}")
        return False
    except Exception as e:
        logging.error(f"处理文件 {file_path} 失败: {e}")
        return False

def parse_state_file(state_file: str=ensure_path_sep(state_path_file)) -> dict:
    """解析状态文件，返回已处理问题的字典"""
    if not os.path.exists(state_file):
        logging.warning(f"状态文件 {state_file} 不存在")
        return {}
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            state_json = json.load(f)
            # 解析json文件中的new_lines,问题的文件名和行数以及总问题数输出新的字典
            issues = {}
            for file_path, file_info in state_json.items():
                issues[file_path] = {
                    'total': len(file_info.get('new_lines', {})),
                    'lines': file_info.get('new_lines', {}),
                }
            # 将issues写会文件file_info.json
            write_with_json(file_info_path, issues)
            logging.info(f"已解析状态文件 {state_file}，共找到 {len(issues)} 个文件")
    except Exception as e:
        logging.error(f"解析状态文件 {state_file} 失败: {e}")

def write_with_json(file_path: str, data: dict) -> None:
    """将数据写入JSON文件"""
    # 不存在文件时，创建目录
    file_path = ensure_path_sep(file_path)
    if not file_path.endswith('.json'):
        file_path += '.json'
    dir_path = os.path.dirname(file_path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            logging.info(f"已将数据写入文件 {file_path}")
    except Exception as e:
        logging.error(f"写入文件 {file_path} 失败: {e}")

def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # # 如果需要备份，创建备份
    # source_file = os.path.join(source_path, start_module_name)
    # create_backup(source_file, backup)
    state_file = ensure_path_sep(state_path_file)
    # 初始化状态文件
    initialize_state_file(state_file, init_flag=init_state_file_flag)
    # 解析报告
    logging.info(f"正在解析报告: {report_path}")
    issues = parse_csv_report(report_path, expect_checker=expect_checker)
    if not issues:
        logging.error("未从报告中解析出任何问题")
        return
    # 处理每个文件
    total_files = len(issues)
    success_files = 0
    files_with_changes = 0
    logging.info(f"找到 {total_files} 个包含问题的文件")
    timestamp_uniq = time.strftime("%Y%m%d_%H%M%S")
    for file_path, file_issues in issues.items():
        if _filter_path and _filter_path not in file_path:
            logging.debug(f"跳过不符合过滤条件的文件: {file_path}")
            continue
        # 检查文件是否存在
        file_path = source_path + file_path
        if not os.path.exists(file_path):
            logging.warning(f"文件 {file_path} 不存在")
            continue
        # 检查文件是否为C++文件
        ext = Path(file_path).suffix.lower()
        if ext not in ['.cpp', '.cxx', '.cc', '.c', '.h', '.hpp', '.hxx', '.cuh', '.hh', '.cu','.h++', '.c++']:
            logging.warning(f"文件 {file_path} 不是C++文件，跳过")
            continue
        # 备份当前文件
        backup_file(file_path, timestamp_uniq) 
        # 处理文件
        if annotate_file(file_path, file_issues, state_file):
            success_files += 1
            files_with_changes += 1
        else:
            success_files += 1
    # 输出统计信息
    print(f"处理完成: {success_files}/{total_files} 文件成功处理")
    print(f"其中 {files_with_changes} 个文件添加了新注释")
    print(f"跳过的LOG行数: {SKIP_LOG_NUM}")
    print(f"总问题数: {sum(len(issues) for issues in issues.values())}")
    print(f"状态文件已保存至: {state_file}")
    parse_state_file()


if __name__ == '__main__':
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"执行时间为:{end_time-start_time}")