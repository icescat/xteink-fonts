"""
字体渲染模块
支持 FreeType 字体渲染，包含粗细、行距、字间距等配置
"""

import freetype
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum


class FontWeight(Enum):
    """字体粗细"""
    THIN = 100
    EXTRA_LIGHT = 200
    LIGHT = 300
    REGULAR = 400
    MEDIUM = 500
    SEMI_BOLD = 600
    BOLD = 700
    EXTRA_BOLD = 800
    BLACK = 900


class AntiAliasMode(Enum):
    """抗锯齿模式"""
    NONE = "none"           # 无抗锯齿
    DEFAULT = "default"     # 默认
    LIGHT = "light"         # 轻量
    STANDARD = "standard"   # 标准


@dataclass
class RenderConfig:
    """渲染配置"""
    font_size: int = 16                 # 字号（像素）
    font_weight: FontWeight = FontWeight.REGULAR  # 字体粗细
    line_spacing: int = 2               # 行距（像素）
    char_spacing: int = 0               # 字间距（像素）
    anti_alias: AntiAliasMode = AntiAliasMode.DEFAULT  # 抗锯齿模式
    gamma: float = 1.0                  # Gamma 校正
    hinting: bool = True                # 是否使用 hinting
    lcd_filter: bool = False            # LCD 滤波

    def __post_init__(self):
        # 验证参数
        if self.font_size < 4 or self.font_size > 256:
            raise ValueError(f"字号必须在 4-256 之间: {self.font_size}")
        if self.line_spacing < -10 or self.line_spacing > 50:
            raise ValueError(f"行距必须在 -10 到 50 之间: {self.line_spacing}")
        if self.char_spacing < -5 or self.char_spacing > 20:
            raise ValueError(f"字间距必须在 -5 到 20 之间: {self.char_spacing}")


class FontRenderer:
    """字体渲染器"""

    def __init__(self, font_path: str, config: Optional[RenderConfig] = None):
        """
        初始化字体渲染器

        Args:
            font_path: 字体文件路径
            config: 渲染配置
        """
        self.font_path = font_path
        self.config = config or RenderConfig()

        # 加载字体
        self.face = freetype.Face(font_path)

        # 设置字体大小
        self._set_font_size()

        # 设置粗细
        self._set_font_weight()

    def _set_font_size(self):
        """设置字体大小"""
        # 使用像素大小
        self.face.set_pixel_sizes(0, self.config.font_size)

        # 获取实际度量
        self.metrics = self.face.size
        self.ascender = self.metrics.ascender >> 6
        self.descender = self.metrics.descender >> 6
        self.height = self.metrics.height >> 6
        self.max_advance = self.metrics.max_advance >> 6

    def _set_font_weight(self):
        """设置字体粗细（通过选择不同字重或合成）"""
        weight = self.config.font_weight

        # 尝试选择匹配的 weight
        if weight == FontWeight.BOLD:
            # 尝试选择 Bold 变体
            try:
                self.face.select_size(0)
            except:
                pass

    def _get_load_flags(self) -> int:
        """获取加载标志"""
        flags = freetype.FT_LOAD_RENDER

        # 抗锯齿设置
        if self.config.anti_alias == AntiAliasMode.NONE:
            flags |= freetype.FT_LOAD_TARGET_MONO
        elif self.config.anti_alias == AntiAliasMode.LIGHT:
            flags |= freetype.FT_LOAD_TARGET_LIGHT
        else:
            flags |= freetype.FT_LOAD_TARGET_NORMAL

        # Hinting
        if not self.config.hinting:
            flags |= freetype.FT_LOAD_NO_HINTING

        return flags

    def render_char(self, char: str) -> Optional[dict]:
        """
        渲染单个字符

        Args:
            char: 要渲染的字符

        Returns:
            包含位图信息的字典，或 None（如果字符不存在）
        """
        code_point = ord(char)

        # 获取字形索引
        glyph_index = self.face.get_char_index(code_point)
        if glyph_index == 0:
            return None

        # 加载并渲染字形
        flags = self._get_load_flags()
        self.face.load_glyph(glyph_index, flags)

        # 获取位图
        bitmap = self.face.glyph.bitmap

        if bitmap.width == 0 or bitmap.rows == 0:
            # 空白字形（如空格）
            return {
                "code_point": code_point,
                "width": 0,
                "height": self.config.font_size,
                "bitmap": None,
                "advance_x": self.face.glyph.advance.x >> 6,
                "advance_y": self.face.glyph.advance.y >> 6,
                "left": self.face.glyph.bitmap_left,
                "top": self.face.glyph.bitmap_top,
            }

        # 转换为 numpy 数组
        buffer = np.array(bitmap.buffer, dtype=np.uint8).reshape(bitmap.rows, bitmap.width)

        # Gamma 校正
        if self.config.gamma != 1.0:
            buffer = self._apply_gamma(buffer)

        return {
            "code_point": code_point,
            "width": bitmap.width,
            "height": bitmap.rows,
            "bitmap": buffer,
            "advance_x": self.face.glyph.advance.x >> 6,
            "advance_y": self.face.glyph.advance.y >> 6,
            "left": self.face.glyph.bitmap_left,
            "top": self.face.glyph.bitmap_top,
        }

    def _apply_gamma(self, buffer: np.ndarray) -> np.ndarray:
        """应用 Gamma 校正"""
        gamma = self.config.gamma
        normalized = buffer / 255.0
        corrected = np.power(normalized, gamma)
        return (corrected * 255).astype(np.uint8)

    def get_char_bbox(self, char: str) -> Optional[Tuple[int, int, int, int]]:
        """
        获取字符边界框

        Args:
            char: 字符

        Returns:
            (x, y, width, height) 或 None
        """
        result = self.render_char(char)
        if result is None:
            return None

        return (
            result["left"],
            result["top"],
            result["width"],
            result["height"]
        )

    def get_text_size(self, text: str) -> Tuple[int, int]:
        """
        获取文本尺寸

        Args:
            text: 文本

        Returns:
            (width, height)
        """
        width = 0
        max_height = 0

        for char in text:
            result = self.render_char(char)
            if result:
                width += result["advance_x"] + self.config.char_spacing
                max_height = max(max_height, result["height"])

        # 减去最后一个字符的字间距
        if text:
            width -= self.config.char_spacing

        return (width, max_height)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """关闭字体"""
        # FreeType 会自动清理
        pass


def create_renderer(font_path: str, **kwargs) -> FontRenderer:
    """
    创建字体渲染器的便捷函数

    Args:
        font_path: 字体文件路径
        **kwargs: 渲染配置参数

    Returns:
        FontRenderer 实例
    """
    config = RenderConfig(**kwargs)
    return FontRenderer(font_path, config)
