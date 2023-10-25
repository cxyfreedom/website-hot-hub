# -*- coding: utf-8 -*-
import logging
import hashlib
import os
from datetime import datetime

logging.basicConfig(format="%(asctime)s %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


def current_time():
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def current_date():
    return datetime.now().astimezone().strftime("%Y-%m-%d")


def ensure_dir(file):
    directory = os.path.abspath(os.path.dirname(file))
    if not os.path.exists(directory):
        os.makedirs(directory)


def write_text_file(full_path: str, content: str) -> None:
    ensure_dir(full_path)
    with open(full_path, "w") as fd:
        fd.write(content)


def get_weread_id(book_id: str) -> str:
    try:
        # 创建 MD5 哈希对象
        hash_object = hashlib.md5()
        hash_object.update(book_id.encode("utf-8"))
        str_result = hash_object.hexdigest()

        # 取哈希结果的前三个字符作为初始值
        str_sub = str_result[:3]

        # 判断书籍 ID 的类型并进行转换
        fa = []
        if book_id.isdigit():
            # 如果书籍 ID 只包含数字，则将其拆分成长度为 9 的子字符串，并转换为十六进制表示
            chunks = [
                format(int(book_id[i : i + 9]), "x") for i in range(0, len(book_id), 9)
            ]
            fa = ["3", chunks]
        else:
            # 如果书籍 ID 包含其他字符，则将每个字符的 Unicode 编码转换为十六进制表示
            hex_str = "".join(format(ord(char), "x") for char in book_id)
            fa = ["4", [hex_str]]

        # 将类型添加到初始值中
        str_sub += fa[0]

        # 将数字2和哈希结果的后两个字符添加到初始值中
        str_sub += "2" + str_result[-2:]

        # 处理转换后的子字符串数组
        for sub in fa[1]:
            sub_length = format(len(sub), "x").zfill(2)
            str_sub += sub_length + sub

            # 如果不是最后一个子字符串，则添加分隔符 'g'
            if sub != fa[1][-1]:
                str_sub += "g"

        # 如果初始值长度不足 20，从哈希结果中取足够的字符补齐
        if len(str_sub) < 20:
            str_sub += str_result[0 : 20 - len(str_sub)]

        # 创建新的哈希对象
        final_hash_object = hashlib.md5()
        final_hash_object.update(str_sub.encode("utf-8"))
        final_str = final_hash_object.hexdigest()

        # 取最终哈希结果的前三个字符并添加到初始值的末尾
        str_sub += final_str[:3]

        return str_sub
    except Exception as error:
        print("处理微信读书 ID 时出现错误：" + str(error))
        return ""
