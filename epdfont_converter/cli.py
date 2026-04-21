#!/usr/bin/env python3
"""
EPDFont Converter - 命令行工具
"""

import argparse
import sys
import os
from pathlib import Path

from .converter import FontConverter
from .epdfont_builder import EPDFontInfo


def create_parser() -> argparse.ArgumentParser:
    """创建参数解析器"""
    parser = argparse.ArgumentParser(
        prog='epdfont-converter',
        description='将 TTF/OTF 字体转换为 EPDFont 格式（用于 CrossPoint 电子书阅读器）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用 3500 常用字 + 符号，16px，2-bit 灰度
  epdfont-converter input.ttf output.epdfont --charset 3500 --size 16 --2bit

  # 使用 7000 常用字，12px，1-bit 黑白，粗体
  epdfont-converter input.ttf output.epdfont --charset 7000 --size 12 --1bit --weight bold

  # 自定义字符集文件
  epdfont-converter input.ttf output.epdfont --charset ./my_chars.txt --size 14

  # 显示 EPDFont 文件信息
  epdfont-converter --info font.epdfont

  # 列出可用字符集
  epdfont-converter --list-charsets
        """
    )

    # 主要参数
    parser.add_argument('font', nargs='?',
                        help='输入字体文件路径 (TTF/OTF)')
    parser.add_argument('output', nargs='?',
                        help='输出 EPDFont 文件路径')

    # 字符集选择
    charset_group = parser.add_argument_group('字符集选项')
    charset_group.add_argument('--charset', '-c', default='3500',
                               help='字符集选择: 3500(默认), 7000, all, symbols, 或自定义文件路径')
    charset_group.add_argument('--custom-chars', '-cc', default='',
                               help='额外自定义字符（直接输入字符）')

    # 字体大小和渲染
    render_group = parser.add_argument_group('渲染选项')
    render_group.add_argument('--size', '-s', type=int, default=16,
                              help='字号（像素），默认: 16')
    render_group.add_argument('--2bit', dest='is_2bit', action='store_true', default=True,
                              help='使用 2-bit 灰度（默认）')
    render_group.add_argument('--1bit', dest='is_2bit', action='store_false',
                              help='使用 1-bit 黑白')
    render_group.add_argument('--variable-height', action='store_true', default=False,
                              help='允许变高字形（适合位图字体）')

    # 字体样式
    style_group = parser.add_argument_group('字体样式')
    style_group.add_argument('--weight', '-w', default='regular',
                             choices=['thin', 'extra_light', 'light', 'regular',
                                     'medium', 'semi_bold', 'bold', 'extra_bold', 'black'],
                             help='字体粗细，默认: regular')
    style_group.add_argument('--line-spacing', '-ls', type=int, default=2,
                             help='行距（像素），默认: 2')
    style_group.add_argument('--char-spacing', '-cs', type=int, default=0,
                             help='字间距（像素），默认: 0')

    # 渲染质量
    quality_group = parser.add_argument_group('渲染质量')
    quality_group.add_argument('--anti-alias', '-aa', default='default',
                               choices=['none', 'default', 'light', 'standard'],
                               help='抗锯齿模式，默认: default')
    quality_group.add_argument('--gamma', '-g', type=float, default=1.0,
                               help='Gamma 校正 (0.1-3.0)，默认: 1.0')
    quality_group.add_argument('--no-hinting', action='store_true',
                               help='禁用 hinting')

    # 信息查询
    info_group = parser.add_argument_group('信息查询')
    info_group.add_argument('--info', metavar='FILE',
                            help='显示 EPDFont 文件信息')
    info_group.add_argument('--list-charsets', action='store_true',
                            help='列出可用字符集')

    # GUI 模式
    gui_group = parser.add_argument_group('界面模式')
    gui_group.add_argument('--gui', action='store_true',
                           help='启动图形界面')

    # 其他
    parser.add_argument('--charset-dir',
                        help='字符集目录（默认使用 All-Chinese-Character-Set）')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0.0')

    return parser


def print_charsets(charset_dir: str = None):
    """打印可用字符集"""
    converter = FontConverter(charset_dir)
    charsets = converter.list_charsets()

    print("可用字符集:")
    print("=" * 60)
    for cs in charsets:
        print(f"  {cs['id']:10} - {cs['name']}")
        print(f"             描述: {cs['description']}")
        print(f"             字符数: {cs['char_count']}")
        print()


def print_info(file_path: str):
    """打印 EPDFont 文件信息"""
    try:
        EPDFontInfo.print_info(file_path)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    # 启动 GUI 模式
    if args.gui:
        from .gui import main as gui_main
        gui_main()
        return

    # 处理信息查询命令
    if args.info:
        print_info(args.info)
        return

    if args.list_charsets:
        print_charsets(args.charset_dir)
        return

    # 如果没有参数，默认启动 GUI
    if not args.font and not args.output and not args.info and not args.list_charsets:
        from .gui import main as gui_main
        gui_main()
        return

    # 验证必需参数
    if not args.font or not args.output:
        parser.print_help()
        sys.exit(1)

    # 检查字体文件
    if not os.path.exists(args.font):
        print(f"错误: 字体文件不存在: {args.font}", file=sys.stderr)
        sys.exit(1)

    # 创建转换器
    converter = FontConverter(args.charset_dir)

    # 执行转换
    print(f"EPDFont Converter v1.0.0")
    print(f"=" * 60)
    print(f"输入: {args.font}")
    print(f"输出: {args.output}")
    print(f"字符集: {args.charset}")
    print(f"字号: {args.size}px")
    print(f"灰度: {'2-bit' if args.is_2bit else '1-bit'}")
    print(f"粗细: {args.weight}")
    print(f"行距: {args.line_spacing}px")
    print(f"字间距: {args.char_spacing}px")
    print(f"抗锯齿: {args.anti_alias}")
    print(f"Gamma: {args.gamma}")
    print(f"Hinting: {'禁用' if args.no_hinting else '启用'}")
    print(f"变高字形: {'是' if args.variable_height else '否'}")
    print("=" * 60)
    print()

    try:
        result = converter.convert(
            font_path=args.font,
            output_path=args.output,
            charset=args.charset,
            font_size=args.size,
            is_2bit=args.is_2bit,
            font_weight=args.weight,
            line_spacing=args.line_spacing,
            char_spacing=args.char_spacing,
            anti_alias=args.anti_alias,
            gamma=args.gamma,
            hinting=not args.no_hinting,
            variable_height=args.variable_height,
            custom_chars=args.custom_chars
        )

        # 打印结果
        print()
        print("转换完成!")
        print("=" * 60)
        print(f"输出文件: {result['output_path']}")
        print(f"文件大小: {result['file_size_kb']:.2f} KB")
        print(f"总字符数: {result['total_chars']}")
        print(f"成功: {result['success_count']}")
        print(f"跳过: {result['skip_count']}")

        if result['errors']:
            print()
            print("警告/错误 (前10个):")
            for error in result['errors']:
                print(f"  - {error}")

    except KeyboardInterrupt:
        print("\n\n用户取消操作", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
