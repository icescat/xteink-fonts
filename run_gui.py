#!/usr/bin/env python3
"""
EPDFont Converter GUI 启动脚本
"""

import sys
import os

# 添加到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from epdfont_converter.gui import main

if __name__ == '__main__':
    print("正在启动 EPDFont Converter GUI...")
    main()
