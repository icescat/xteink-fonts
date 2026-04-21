"""
EPDFont 文件构建模块
负责将渲染后的字形打包成 .epdfont 格式
"""

import struct
from dataclasses import dataclass
from typing import List, Dict, Optional, BinaryIO
from pathlib import Path
import numpy as np


@dataclass
class GlyphData:
    """字形数据"""
    code_point: int
    width: int
    height: int
    advance_x: int
    left: int
    top: int
    bitmap: Optional[np.ndarray]  # 灰度位图 (0-255)


class EPDFontBitmap:
    """EPDFont 位图打包器"""

    def __init__(self, width: int, height: int, is_2bit: bool):
        self.width = width
        self.height = height
        self.is_2bit = is_2bit
        self.pixels = np.zeros((height, width), dtype=np.uint8)

    def set_pixel(self, x: int, y: int, value: int):
        """设置像素值 (0-255)"""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y, x] = value

    def get_packed_bytes(self) -> bytes:
        """将像素数据打包成字节"""
        if self.is_2bit:
            return self._pack_2bit()
        else:
            return self._pack_1bit()

    def _pack_1bit(self) -> bytes:
        """打包成 1-bit 位图 (MSB first)"""
        total_pixels = self.width * self.height
        total_bytes = (total_pixels + 7) // 8
        result = bytearray(total_bytes)

        bit_mask = [0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01]
        byte_idx = 0
        bit_idx = 0
        current_byte = 0

        for y in range(self.height):
            for x in range(self.width):
                if self.pixels[y, x] > 127:  # 阈值
                    current_byte |= bit_mask[bit_idx]

                bit_idx += 1
                if bit_idx == 8:
                    result[byte_idx] = current_byte
                    byte_idx += 1
                    current_byte = 0
                    bit_idx = 0

        if bit_idx != 0:
            result[byte_idx] = current_byte

        return bytes(result)

    def _pack_2bit(self) -> bytes:
        """打包成 2-bit 灰度位图 (MSB first)"""
        # 将 0-255 映射到 0-3
        total_pixels = self.width * self.height
        total_bytes = (total_pixels + 3) // 4
        result = bytearray(total_bytes)

        byte_idx = 0
        pixel_count = 0
        current_byte = 0

        for y in range(self.height):
            for x in range(self.width):
                # 将 0-255 转换为 0-3
                val = (self.pixels[y, x] >> 6) & 0x03
                current_byte |= val << (6 - pixel_count * 2)

                pixel_count += 1
                if pixel_count == 4:
                    result[byte_idx] = current_byte
                    byte_idx += 1
                    current_byte = 0
                    pixel_count = 0

        if pixel_count != 0:
            result[byte_idx] = current_byte

        return bytes(result)


class EPDFontBuilder:
    """EPDFont 文件构建器"""

    # 文件头大小
    HEADER_SIZE = 48

    def __init__(self, font_size: int, is_2bit: bool = True, variable_height: bool = False):
        """
        初始化构建器

        Args:
            font_size: 字体大小（像素）
            is_2bit: 是否使用 2-bit 灰度
            variable_height: 是否允许变高字形
        """
        self.font_size = font_size
        self.is_2bit = is_2bit
        self.variable_height = variable_height
        self.glyphs: Dict[int, GlyphData] = {}

    def add_glyph(self, glyph: GlyphData):
        """添加字形"""
        self.glyphs[glyph.code_point] = glyph

    def _merge_intervals(self, sorted_codes: List[int]) -> List[tuple]:
        """合并连续的 Unicode 区间"""
        if not sorted_codes:
            return []

        intervals = []
        start = sorted_codes[0]
        prev = sorted_codes[0]

        for code in sorted_codes[1:]:
            if code == prev + 1:
                prev = code
            else:
                intervals.append((start, prev))
                start = code
                prev = code

        intervals.append((start, prev))
        return intervals

    def _create_bitmap(self, glyph: GlyphData) -> EPDFontBitmap:
        """从字形数据创建位图"""
        if glyph.bitmap is None:
            # 空白字形
            bmp = EPDFontBitmap(0, self.font_size, self.is_2bit)
        else:
            h, w = glyph.bitmap.shape
            bmp = EPDFontBitmap(w, h, self.is_2bit)

            for y in range(h):
                for x in range(w):
                    bmp.set_pixel(x, y, glyph.bitmap[y, x])

        return bmp

    def build(self, output_path: str):
        """
        构建并保存 EPDFont 文件

        Args:
            output_path: 输出文件路径
        """
        # 排序码点
        sorted_codes = sorted(self.glyphs.keys())

        if not sorted_codes:
            raise ValueError("没有字形数据")

        # 合并连续区间
        intervals = self._merge_intervals(sorted_codes)

        # 计算各部分大小
        intervals_size = len(intervals) * 12  # 每个区间 12 字节
        glyphs_size = len(sorted_codes) * 13  # 每个字形 13 字节

        # 预计算位图数据
        bitmap_data = {}
        for code in sorted_codes:
            glyph = self.glyphs[code]
            bmp = self._create_bitmap(glyph)
            bitmap_data[code] = bmp.get_packed_bytes()

        bitmaps_size = sum(len(data) for data in bitmap_data.values())

        # 计算偏移量
        offset_intervals = self.HEADER_SIZE
        offset_glyphs = offset_intervals + intervals_size
        offset_bitmaps = offset_glyphs + glyphs_size
        file_size = offset_bitmaps + bitmaps_size

        # 写入文件
        with open(output_path, 'wb') as f:
            self._write_header(
                f, len(intervals), file_size, len(sorted_codes),
                offset_intervals, offset_glyphs, offset_bitmaps
            )
            self._write_intervals(f, intervals)
            self._write_glyphs(f, sorted_codes, bitmap_data)
            self._write_bitmaps(f, sorted_codes, bitmap_data)

    def _write_header(self, f: BinaryIO, interval_count: int, file_size: int,
                      glyph_count: int, offset_intervals: int,
                      offset_glyphs: int, offset_bitmaps: int):
        """写入文件头"""
        # Magic (4 bytes)
        f.write(b'EPDF')
        # IntervalCount (4 bytes)
        f.write(struct.pack('<I', interval_count))
        # FileSize (4 bytes)
        f.write(struct.pack('<I', file_size))
        # Height (4 bytes)
        f.write(struct.pack('<I', self.font_size))
        # GlyphCount (4 bytes)
        f.write(struct.pack('<I', glyph_count))
        # Ascender (4 bytes)
        f.write(struct.pack('<i', 0))
        # Reserved (4 bytes)
        f.write(struct.pack('<i', 0))
        # Descender (4 bytes)
        f.write(struct.pack('<i', 0))
        # Is2Bit (4 bytes)
        f.write(struct.pack('<I', 1 if self.is_2bit else 0))
        # OffsetIntervals (4 bytes)
        f.write(struct.pack('<I', offset_intervals))
        # OffsetGlyphs (4 bytes)
        f.write(struct.pack('<I', offset_glyphs))
        # OffsetBitmaps (4 bytes)
        f.write(struct.pack('<I', offset_bitmaps))

    def _write_intervals(self, f: BinaryIO, intervals: List[tuple]):
        """写入区间表"""
        current_glyph_idx = 0
        for start, end in intervals:
            f.write(struct.pack('<I', start))      # Start
            f.write(struct.pack('<I', end))        # End
            f.write(struct.pack('<I', current_glyph_idx))  # IndexOffset
            current_glyph_idx += (end - start + 1)

    def _write_glyphs(self, f: BinaryIO, sorted_codes: List[int],
                      bitmap_data: Dict[int, bytes]):
        """写入字形属性表"""
        current_bitmap_offset = 0

        for code in sorted_codes:
            glyph = self.glyphs[code]
            data = bitmap_data[code]

            # width (1 byte)
            f.write(struct.pack('<B', glyph.width))
            # height (1 byte)
            f.write(struct.pack('<B', glyph.height))
            # advance_x (1 byte)
            f.write(struct.pack('<B', glyph.advance_x))
            # left (1 byte, signed)
            f.write(struct.pack('<b', glyph.left))
            # padding (1 byte)
            f.write(struct.pack('<B', 0))
            # top (1 byte, signed)
            f.write(struct.pack('<b', glyph.top))
            # padding (1 byte)
            f.write(struct.pack('<B', 0))
            # data_length (2 bytes)
            f.write(struct.pack('<H', len(data)))
            # data_offset (4 bytes)
            f.write(struct.pack('<I', current_bitmap_offset))

            current_bitmap_offset += len(data)

    def _write_bitmaps(self, f: BinaryIO, sorted_codes: List[int],
                       bitmap_data: Dict[int, bytes]):
        """写入位图数据"""
        for code in sorted_codes:
            f.write(bitmap_data[code])


class EPDFontInfo:
    """EPDFont 文件信息读取器"""

    @staticmethod
    def read_header(file_path: str) -> dict:
        """读取文件头信息"""
        with open(file_path, 'rb') as f:
            magic = f.read(4)
            if magic != b'EPDF':
                raise ValueError(f"无效的 EPDFont 文件: {file_path}")

            f.seek(0)
            header = {
                'magic': f.read(4).decode('ascii'),
                'interval_count': struct.unpack('<I', f.read(4))[0],
                'file_size': struct.unpack('<I', f.read(4))[0],
                'height': struct.unpack('<I', f.read(4))[0],
                'glyph_count': struct.unpack('<I', f.read(4))[0],
                'ascender': struct.unpack('<i', f.read(4))[0],
                'reserved': struct.unpack('<i', f.read(4))[0],  # Reserved
                'descender': struct.unpack('<i', f.read(4))[0],
                'is_2bit': struct.unpack('<I', f.read(4))[0] == 1,
                'offset_intervals': struct.unpack('<I', f.read(4))[0],
                'offset_glyphs': struct.unpack('<I', f.read(4))[0],
                'offset_bitmaps': struct.unpack('<I', f.read(4))[0],
            }

        return header

    @staticmethod
    def print_info(file_path: str):
        """打印文件信息"""
        header = EPDFontInfo.read_header(file_path)

        print(f"EPDFont 文件信息: {Path(file_path).name}")
        print("=" * 50)
        print(f"  魔数: {header['magic']}")
        print(f"  文件大小: {header['file_size']:,} bytes ({header['file_size']/1024:.2f} KB)")
        print(f"  字体高度: {header['height']} px")
        print(f"  字形数量: {header['glyph_count']:,}")
        print(f"  区间数量: {header['interval_count']:,}")
        print(f"  灰度模式: {'2-bit' if header['is_2bit'] else '1-bit'}")
        print(f"  区间表偏移: 0x{header['offset_intervals']:08X}")
        print(f"  字形表偏移: 0x{header['offset_glyphs']:08X}")
        print(f"  位图偏移: 0x{header['offset_bitmaps']:08X}")
