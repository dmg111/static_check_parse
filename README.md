# static_check_parse

`static_check_parse` 是一个用于静态检查和解析的工具脚本，主要用于分析和处理代码中的静态信息。

## 功能简介

- 解析静态扫描工具生成的问题信息，将其回填至源代码中，以[问题开始 #] 问题编号 [问题结束 ]形式
- 

## 使用方法

1. 进入脚本目录：

    ```bash
    cd static-modeling/scripts/tools/static_check_parse/
    ```

2. 修改配置：

    ```
        report_path = r"/home/d800518/static-modeling/scripts/tools/static_check_parse/data/static-modeling_rule+DEVOPS专用勿动!!! (0630).csv" # Coverity生成的静态代码检查报告路径
        source_path = r"/home/d800518/static-modeling"  # 源代码根路径
        backup = True  # 是否创建备份文件
        init_state_file_flag = True # 是否初始化状态文件
        # expect_checker = ["AUTOSAR C++14 A1-1-1"] # 期望的检查器列表，示例：只处理AUTOSAR C++14 M5-0-4检查器
        expect_checker = ["AUTOSAR C++14 M5-0-4", "AUTOSAR C++14 M5-0-6", "AUTOSAR C++14 M5-0-3", "AUTOSAR C++14 M5-0-5", "AUTOSAR C++14 M5-2-2"] # 期望的检查器列表，示例：只处理AUTOSAR C++14 M5-0-4检查器
        state_path_file = r"\static_check_parse\data\state_file"  # 状态文件路径
        file_info_path = r"\static_check_parse\result\file_info.json"  # 放入提示词中的文件信息路径
        _filter_path = "static_object"  # 过滤路径，示例：只处理包含static_object的文件
        _filter_Log = True # 是否过滤掉LOG相关的行
    ```

3. 运行即可，日志打印默认等级为info


## 备注
调整日志打印级别：
搜索：
```
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
```
level = logging.DEBUG
level = logging.ERROR


## 依赖

- Python 3.x
- 相关依赖库见 `requirements.txt`

