def indent_closing_braces(file_path, indent='    '):
    """
    给 .ini 文件中所有顶格的 '}' 前面加上缩进。
    例如:
    }
    →    }

    :param file_path: ini 文件路径
    :param indent: 缩进字符串，默认4个空格
    """
    # 读取文件所有行
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 修改符合条件的行
    new_lines = []
    for line in lines:
        stripped = line.rstrip('\n')  # 去掉行尾换行符
        if stripped.strip() == '}' and stripped.startswith('}'):  # 顶格的单独 '}'
            new_lines.append(indent + '}' + '\n')
        else:
            new_lines.append(line)

    # 写回文件（覆盖原文件）
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"✅ 已处理完成: {file_path}")

if __name__ == "__main__":
    indent_closing_braces("race_pars_Shanghai.ini")