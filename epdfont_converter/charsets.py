"""
字符集管理模块
提供 3500/7000 常用汉字 + 符号的字符集
"""

import os
from pathlib import Path
from typing import Set

# 内置字符集配置
BUILTIN_CHARSETS = {
    "3500": {
        "name": "3500常用汉字+符号",
        "description": "3500个常用汉字 + 常用符号，适合日常使用",
        "source_file": "3500+symbols.txt"
    },
    "7000": {
        "name": "7000常用汉字+符号",
        "description": "7000个常用汉字 + 常用符号，覆盖更广",
        "source_file": "7000+symbols.txt"
    },
    "all": {
        "name": "全部汉字+符号",
        "description": "所有汉字 + 符号，文件较大",
        "source_file": "all+symbols.txt"
    },
    "symbols": {
        "name": "仅符号",
        "description": "仅包含常用符号",
        "source_file": "symbols.txt"
    }
}


class CharsetManager:
    """字符集管理器"""

    def __init__(self, charset_dir: str = None):
        """
        初始化字符集管理器

        Args:
            charset_dir: 字符集文件目录，默认为内置 charsets 目录
        """
        if charset_dir is None:
            # 默认使用内置 charsets 目录
            base_dir = Path(__file__).parent
            self.charset_dir = base_dir / "charsets"
        else:
            self.charset_dir = Path(charset_dir)

    def get_charset_path(self, charset_name: str) -> Path:
        """
        获取字符集文件路径

        Args:
            charset_name: 字符集名称 (3500, 7000, all, symbols)

        Returns:
            字符集文件路径
        """
        if charset_name in BUILTIN_CHARSETS:
            filename = BUILTIN_CHARSETS[charset_name]["source_file"]
            return self.charset_dir / filename
        else:
            # 尝试作为文件路径
            path = Path(charset_name)
            if path.exists():
                return path
            raise FileNotFoundError(f"字符集不存在: {charset_name}")

    def load_charset(self, charset_name: str) -> Set[str]:
        """
        加载字符集

        Args:
            charset_name: 字符集名称或文件路径

        Returns:
            字符集合
        """
        path = self.get_charset_path(charset_name)

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 去重并保持顺序
        chars = list(dict.fromkeys(content))

        # 过滤控制字符，保留常用符号
        chars = [c for c in chars if ord(c) >= 32 or c in '\n\r\t']

        return set(chars)

    def get_charset_info(self, charset_name: str) -> dict:
        """
        获取字符集信息

        Args:
            charset_name: 字符集名称

        Returns:
            字符集信息字典
        """
        if charset_name in BUILTIN_CHARSETS:
            info = BUILTIN_CHARSETS[charset_name].copy()
            # 尝试获取实际字符数
            try:
                chars = self.load_charset(charset_name)
                info["char_count"] = len(chars)
            except:
                info["char_count"] = "未知"
            return info
        return {"name": "自定义", "description": "自定义字符集文件"}

    def list_charsets(self) -> list:
        """
        列出所有可用字符集

        Returns:
            字符集信息列表
        """
        result = []
        for key, info in BUILTIN_CHARSETS.items():
            item = {"id": key, **info}
            try:
                chars = self.load_charset(key)
                item["char_count"] = len(chars)
            except:
                item["char_count"] = "文件未找到"
            result.append(item)
        return result


def get_default_charset_dir() -> Path:
    """获取默认字符集目录"""
    base_dir = Path(__file__).parent
    return base_dir / "charsets"
