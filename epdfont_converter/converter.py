"""
字体转换器主模块
整合字符集、渲染、构建功能
"""

import os
import sys
from pathlib import Path
from typing import Optional, Set, Callable
from tqdm import tqdm

from .charsets import CharsetManager
from .font_renderer import FontRenderer, RenderConfig, FontWeight, AntiAliasMode
from .epdfont_builder import EPDFontBuilder, GlyphData, EPDFontInfo


class FontConverter:
    """字体转换器"""

    def __init__(self, charset_dir: Optional[str] = None):
        """
        初始化转换器

        Args:
            charset_dir: 字符集目录，默认使用 All-Chinese-Character-Set
        """
        self.charset_manager = CharsetManager(charset_dir)
        self.progress_callback: Optional[Callable[[int, int, str], None]] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """
        设置进度回调函数

        Args:
            callback: 回调函数(current, total, message)
        """
        self.progress_callback = callback

    def convert(
        self,
        font_path: str,
        output_path: str,
        charset: str = "3500",
        font_size: int = 16,
        is_2bit: bool = True,
        font_weight: str = "regular",
        line_spacing: int = 2,
        char_spacing: int = 0,
        anti_alias: str = "default",
        gamma: float = 1.0,
        hinting: bool = True,
        variable_height: bool = False,
        custom_chars: Optional[str] = None
    ) -> dict:
        """
        转换字体

        Args:
            font_path: 输入字体文件路径
            output_path: 输出 EPDFont 文件路径
            charset: 字符集 (3500, 7000, all, symbols 或自定义文件路径)
            font_size: 字号（像素）
            is_2bit: 是否使用 2-bit 灰度
            font_weight: 字体粗细 (thin, extra_light, light, regular, medium, semi_bold, bold, extra_bold, black)
            line_spacing: 行距（像素）
            char_spacing: 字间距（像素）
            anti_alias: 抗锯齿模式 (none, default, light, standard)
            gamma: Gamma 校正 (0.1-3.0)
            hinting: 是否使用 hinting
            variable_height: 是否允许变高字形
            custom_chars: 额外自定义字符

        Returns:
            转换结果信息字典
        """
        # 验证输入文件
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"字体文件不存在: {font_path}")

        # 加载字符集
        print(f"加载字符集: {charset}")
        chars = self.charset_manager.load_charset(charset)

        # 添加自定义字符
        if custom_chars:
            chars.update(custom_chars)

        char_list = sorted(chars, key=lambda c: ord(c))
        print(f"共 {len(char_list)} 个字符")

        # 创建渲染配置
        weight_map = {
            "thin": FontWeight.THIN,
            "extra_light": FontWeight.EXTRA_LIGHT,
            "light": FontWeight.LIGHT,
            "regular": FontWeight.REGULAR,
            "medium": FontWeight.MEDIUM,
            "semi_bold": FontWeight.SEMI_BOLD,
            "bold": FontWeight.BOLD,
            "extra_bold": FontWeight.EXTRA_BOLD,
            "black": FontWeight.BLACK,
        }

        aa_map = {
            "none": AntiAliasMode.NONE,
            "default": AntiAliasMode.DEFAULT,
            "light": AntiAliasMode.LIGHT,
            "standard": AntiAliasMode.STANDARD,
        }

        config = RenderConfig(
            font_size=font_size,
            font_weight=weight_map.get(font_weight.lower(), FontWeight.REGULAR),
            line_spacing=line_spacing,
            char_spacing=char_spacing,
            anti_alias=aa_map.get(anti_alias.lower(), AntiAliasMode.DEFAULT),
            gamma=max(0.1, min(3.0, gamma)),
            hinting=hinting
        )

        # 创建字体渲染器
        print(f"加载字体: {font_path}")
        renderer = FontRenderer(font_path, config)

        # 创建 EPDFont 构建器
        builder = EPDFontBuilder(font_size, is_2bit, variable_height)

        # 渲染所有字符
        print(f"开始渲染 ({'2-bit' if is_2bit else '1-bit'} 灰度)...")
        success_count = 0
        skip_count = 0
        error_list = []

        iterator = enumerate(char_list)
        if self.progress_callback is None:
            iterator = tqdm(list(iterator), desc="渲染进度")

        for i, char in iterator:
            if self.progress_callback:
                self.progress_callback(i, len(char_list), f"渲染: {char}")

            try:
                result = renderer.render_char(char)

                if result is None:
                    skip_count += 1
                    error_list.append(f"U+{ord(char):04X} ({char}): 字体中不存在")
                    continue

                # 创建字形数据
                glyph = GlyphData(
                    code_point=result["code_point"],
                    width=result["width"],
                    height=result["height"],
                    advance_x=result["advance_x"],
                    left=result["left"],
                    top=result["top"],
                    bitmap=result["bitmap"]
                )

                builder.add_glyph(glyph)
                success_count += 1

            except Exception as e:
                skip_count += 1
                error_list.append(f"U+{ord(char):04X} ({char}): {str(e)}")

        renderer.close()

        # 构建输出文件
        print(f"\n构建 EPDFont 文件...")
        builder.build(output_path)

        # 获取文件信息
        file_size = os.path.getsize(output_path)

        result = {
            "success": True,
            "output_path": output_path,
            "file_size": file_size,
            "file_size_kb": file_size / 1024,
            "total_chars": len(char_list),
            "success_count": success_count,
            "skip_count": skip_count,
            "font_size": font_size,
            "is_2bit": is_2bit,
            "charset": charset,
            "errors": error_list[:10] if len(error_list) > 10 else error_list  # 最多保留10个错误
        }

        return result

    def get_font_info(self, epdfont_path: str) -> dict:
        """
        获取 EPDFont 文件信息

        Args:
            epdfont_path: EPDFont 文件路径

        Returns:
            文件信息字典
        """
        return EPDFontInfo.read_header(epdfont_path)

    def list_charsets(self) -> list:
        """
        列出可用字符集

        Returns:
            字符集列表
        """
        return self.charset_manager.list_charsets()


def convert_font(
    font_path: str,
    output_path: str,
    **kwargs
) -> dict:
    """
    便捷的字体转换函数

    Args:
        font_path: 输入字体文件路径
        output_path: 输出 EPDFont 文件路径
        **kwargs: 其他参数，见 FontConverter.convert

    Returns:
        转换结果
    """
    converter = FontConverter()
    return converter.convert(font_path, output_path, **kwargs)
