#!/usr/bin/env python3
"""
EPDFont Converter - 安装脚本
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取 README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding='utf-8') if readme_path.exists() else ""

setup(
    name="xteink-fonts",
    version="1.0.0",
    author="EPDFont Converter Team",
    description="将 TTF/OTF 字体转换为 EPDFont 格式（用于 CrossPoint 电子书阅读器）",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/epdfont-converter",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "freetype-py>=2.3.0",
        "numpy>=1.20.0",
        "tqdm>=4.60.0",
        "Pillow>=8.0.0",  # 用于 GUI 图像处理
    ],
    entry_points={
        "console_scripts": [
            "xteink-fonts=epdfont_converter.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
