# xteink-fonts

给 Xteink X4 墨水屏设备制作自定义字体的工具。

## 干嘛用的

Xteink X4 自带的字体不够用，这个工具可以把电脑上的 TTF/OTF 字体转换成设备能用的 EPDFont 格式，还支持选常用汉字（3500/7000字），省得字体文件太大。

## 功能

- 支持 3500/7000 常用汉字 + 符号
- 1-bit / 2-bit 灰度可选
- 字号、行距、字间距可调
- 图形界面操作，不用敲命令

## 安装

```bash
git clone https://github.com/icescat/xteink-fonts.git
cd xteink-fonts
pip install -e .
```

依赖：Python 3.8+，需要装 freetype-py、numpy、Pillow

## 使用方法

### 图形界面（推荐）

```bash
python run_gui.py
```

或者双击 `启动GUI.bat`

界面操作：
1. 选字体文件
2. 选字符集（3500字够用，7000字更全）
3. 调字号和间距
4. 点开始转换

### 命令行

```bash
# 3500常用字，16号，2-bit灰度
python -m epdfont_converter input.ttf output.epdfont --charset 3500 --size 16

# 7000字，12号，1-bit黑白
python -m epdfont_converter input.ttf output.epdfont --charset 7000 --size 12 --1bit
```

## 字符集说明

| 字符集 | 字数 | 用途 |
|--------|------|------|
| 3500 | 约3717字 | 日常使用，推荐 |
| 7000 | 约7215字 | 看古籍或专业书 |
| all | 约8363字 | 全都要 |
| symbols | 约128字 | 只要符号 |

## 把字体拷到设备

1. SD卡根目录建个 `fonts` 文件夹
2. 把生成的 `.epdfont` 文件丢进去
3. 设备上设置 → 系统设置 → 自定义字体 → 选你的字体

## 预览效果

转换前能在软件里预览，看看字号和间距合不合适。

## 注意事项

- 2-bit 灰度显示效果更好，但文件比 1-bit 大
- 字号别太大，内存有限
- 有些字体版权受限，别乱传

## License

MIT
