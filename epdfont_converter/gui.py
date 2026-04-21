#!/usr/bin/env python3
"""
EPDFont Converter - GUI 模式
使用 tkinter 构建可视化界面
"""

import os
import sys
import threading
from pathlib import Path
from tkinter import (
    Tk, Frame, Label, Button, Entry, StringVar, IntVar, DoubleVar,
    BooleanVar, OptionMenu, Checkbutton, Scale, filedialog, messagebox,
    Text, Scrollbar, Canvas, PhotoImage, LabelFrame, Toplevel
)
from tkinter import ttk

from .converter import FontConverter
from .epdfont_builder import EPDFontInfo
from .charsets import CharsetManager


class FontPreviewCanvas(Canvas):
    """字体预览画布"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.config(bg='white', highlightthickness=1, highlightbackground='#cccccc')
        self.preview_text = "字体预览\nABC abc 123\n中文测试"
        self.font_path = None
        self.font_size = 16
        self.font_weight = "regular"
        self.line_spacing = 2
        self.char_spacing = 0
        self.anti_alias = "default"
        self.gamma = 1.0
        self.hinting = True

    def update_preview(self, font_path=None, font_size=None, font_weight=None,
                       line_spacing=None, char_spacing=None, anti_alias=None,
                       gamma=None, hinting=None, preview_text=None):
        """更新预览"""
        self.delete("all")

        if font_path and os.path.exists(font_path):
            self.font_path = font_path
        if font_size is not None:
            self.font_size = font_size
        if font_weight is not None:
            self.font_weight = font_weight
        if line_spacing is not None:
            self.line_spacing = line_spacing
        if char_spacing is not None:
            self.char_spacing = char_spacing
        if anti_alias is not None:
            self.anti_alias = anti_alias
        if gamma is not None:
            self.gamma = gamma
        if hinting is not None:
            self.hinting = hinting
        if preview_text:
            self.preview_text = preview_text

        if not self.font_path:
            self.create_text(
                self.winfo_width() // 2, self.winfo_height() // 2,
                text="请选择字体文件",
                font=("Microsoft YaHei", 12),
                fill="#999999"
            )
            return

        # 尝试加载字体并渲染预览
        try:
            import freetype
            face = freetype.Face(self.font_path)

            # 设置字体大小
            face.set_pixel_sizes(0, self.font_size)

            # 计算行高（字号 + 行距）
            line_height = self.font_size + self.line_spacing

            # 设置加载标志
            load_flags = freetype.FT_LOAD_RENDER
            if self.anti_alias == "none":
                load_flags |= freetype.FT_LOAD_TARGET_MONO
            elif self.anti_alias == "light":
                load_flags |= freetype.FT_LOAD_TARGET_LIGHT

            if not self.hinting:
                load_flags |= freetype.FT_LOAD_NO_HINTING

            y_offset = 30
            for line in self.preview_text.split('\n'):
                x_offset = 20
                for char in line:
                    glyph_index = face.get_char_index(ord(char))
                    if glyph_index > 0:
                        face.load_glyph(glyph_index, load_flags)
                        bitmap = face.glyph.bitmap

                        # 应用 Gamma 校正
                        gamma_factor = self.gamma

                        # 渲染位图
                        for row in range(bitmap.rows):
                            for col in range(bitmap.width):
                                # 处理不同的位图格式
                                if bitmap.pixel_mode == freetype.FT_PIXEL_MODE_MONO:
                                    # 1-bit 位图
                                    byte_index = row * bitmap.pitch + (col // 8)
                                    if byte_index < len(bitmap.buffer):
                                        byte = bitmap.buffer[byte_index]
                                        bit = 7 - (col % 8)
                                        pixel = 255 if (byte >> bit) & 1 else 0
                                    else:
                                        pixel = 0
                                else:
                                    # 8-bit 灰度位图
                                    pixel = bitmap.buffer[row * bitmap.pitch + col]

                                # Gamma 校正
                                if gamma_factor != 1.0 and pixel > 0:
                                    pixel = int(255 * ((pixel / 255.0) ** gamma_factor))

                                if pixel > 0:
                                    x = x_offset + face.glyph.bitmap_left + col
                                    y = y_offset - face.glyph.bitmap_top + row

                                    # 根据像素值设置灰度
                                    if pixel > 200:
                                        color = '#000000'
                                    elif pixel > 150:
                                        color = '#444444'
                                    elif pixel > 100:
                                        color = '#888888'
                                    else:
                                        color = '#bbbbbb'

                                    self.create_rectangle(
                                        x, y, x+1, y+1,
                                        fill=color, outline=''
                                    )

                    # 添加字间距
                    x_offset += (face.glyph.advance.x >> 6) + self.char_spacing

                y_offset += line_height

        except Exception as e:
            self.create_text(
                self.winfo_width() // 2, self.winfo_height() // 2,
                text=f"预览加载失败\n{str(e)[:50]}",
                font=("Microsoft YaHei", 10),
                fill="#ff0000"
            )


class EPDFontGUI:
    """EPDFont Converter GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("EPDFont Converter - 字体转换工具")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # 设置窗口图标（如果有的话）
        # self.root.iconbitmap("icon.ico")

        # 初始化转换器
        self.converter = FontConverter()
        self.charset_manager = CharsetManager()

        # 创建变量
        self._create_variables()

        # 创建界面
        self._create_ui()

        # 居中窗口
        self._center_window()

    def _create_variables(self):
        """创建 tkinter 变量"""
        # 文件路径
        self.font_path_var = StringVar()
        self.output_path_var = StringVar()

        # 字符集
        self.charset_var = StringVar(value="3500")

        # 字体参数
        self.font_size_var = IntVar(value=16)
        self.font_weight_var = StringVar(value="regular")
        self.line_spacing_var = IntVar(value=2)
        self.char_spacing_var = IntVar(value=0)

        # 渲染参数
        self.is_2bit_var = BooleanVar(value=True)
        self.anti_alias_var = StringVar(value="default")
        self.gamma_var = DoubleVar(value=1.0)
        self.hinting_var = BooleanVar(value=True)
        self.variable_height_var = BooleanVar(value=False)

        # 自定义字符
        self.custom_chars_var = StringVar()

        # 状态
        self.status_var = StringVar(value="就绪")
        self.progress_var = IntVar(value=0)

        # 绑定变量变化事件（用于自动刷新预览）
        self._bind_preview_updates()

    def _bind_preview_updates(self):
        """绑定预览更新事件"""
        # 字体参数变化时刷新预览
        self.font_size_var.trace('w', lambda *args: self._delayed_refresh())
        self.line_spacing_var.trace('w', lambda *args: self._delayed_refresh())
        self.char_spacing_var.trace('w', lambda *args: self._delayed_refresh())
        self.anti_alias_var.trace('w', lambda *args: self._delayed_refresh())
        self.gamma_var.trace('w', lambda *args: self._delayed_refresh())
        self.hinting_var.trace('w', lambda *args: self._delayed_refresh())

    def _delayed_refresh(self):
        """延迟刷新预览（避免频繁更新）"""
        if hasattr(self, '_refresh_after_id'):
            self.root.after_cancel(self._refresh_after_id)
        self._refresh_after_id = self.root.after(100, self._refresh_preview)

    def _create_ui(self):
        """创建用户界面"""
        # 主框架
        main_frame = Frame(self.root, padx=20, pady=15)
        main_frame.pack(fill='both', expand=True)

        # 创建左右分栏
        content_frame = Frame(main_frame)
        content_frame.pack(fill='both', expand=True)

        # 左侧面板
        left_frame = Frame(content_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # 右侧面板
        right_frame = Frame(content_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))

        # 左侧面板内容
        self._create_file_section(left_frame)
        self._create_charset_section(left_frame)
        self._create_font_style_section(left_frame)
        self._create_render_section(left_frame)

        # 右侧面板内容
        self._create_preview_section(right_frame)
        self._create_progress_section(right_frame)

        # 底部按钮
        self._create_button_section(main_frame)

        # 状态栏
        self._create_status_bar(main_frame)

    def _create_file_section(self, parent):
        """创建文件选择区域"""
        frame = LabelFrame(parent, text="文件选择", font=("Microsoft YaHei", 10, "bold"), padx=10, pady=10)
        frame.pack(fill='x', pady=(0, 10))

        # 字体文件
        font_frame = Frame(frame)
        font_frame.pack(fill='x', pady=2)

        Label(font_frame, text="字体文件:", font=("Microsoft YaHei", 9)).pack(side='left')

        font_entry = Entry(font_frame, textvariable=self.font_path_var, font=("Microsoft YaHei", 9))
        font_entry.pack(side='left', fill='x', expand=True, padx=5)

        Button(
            font_frame,
            text="浏览...",
            font=("Microsoft YaHei", 9),
            command=self._browse_font
        ).pack(side='left')

        # 输出文件
        output_frame = Frame(frame)
        output_frame.pack(fill='x', pady=2)

        Label(output_frame, text="输出文件:", font=("Microsoft YaHei", 9)).pack(side='left')

        output_entry = Entry(output_frame, textvariable=self.output_path_var, font=("Microsoft YaHei", 9))
        output_entry.pack(side='left', fill='x', expand=True, padx=5)

        Button(
            output_frame,
            text="浏览...",
            font=("Microsoft YaHei", 9),
            command=self._browse_output
        ).pack(side='left')

    def _create_charset_section(self, parent):
        """创建字符集选择区域"""
        frame = LabelFrame(parent, text="字符集", font=("Microsoft YaHei", 10, "bold"), padx=10, pady=10)
        frame.pack(fill='x', pady=(0, 10))

        # 字符集选择
        charset_frame = Frame(frame)
        charset_frame.pack(fill='x', pady=2)

        Label(charset_frame, text="选择字符集:", font=("Microsoft YaHei", 9)).pack(side='left')

        charset_options = ["3500", "7000", "all", "symbols"]
        charset_combo = ttk.Combobox(
            charset_frame,
            textvariable=self.charset_var,
            values=charset_options,
            width=10,
            state='readonly'
        )
        charset_combo.pack(side='left', padx=5)

        # 字符集信息
        self.charset_info_label = Label(
            charset_frame,
            text="3500常用汉字 + 符号 (~3716字符)",
            font=("Microsoft YaHei", 8),
            fg="#666666",
            width=35,
            anchor='w'
        )
        self.charset_info_label.pack(side='left', padx=10)

        self.charset_var.trace('w', self._update_charset_info)

        # 自定义字符
        custom_frame = Frame(frame)
        custom_frame.pack(fill='x', pady=5)

        Label(custom_frame, text="额外字符:", font=("Microsoft YaHei", 9)).pack(side='left')

        custom_entry = Entry(custom_frame, textvariable=self.custom_chars_var, font=("Microsoft YaHei", 9))
        custom_entry.pack(side='left', fill='x', expand=True, padx=5)

    def _create_font_style_section(self, parent):
        """创建字体样式区域"""
        frame = LabelFrame(parent, text="字体样式", font=("Microsoft YaHei", 10, "bold"), padx=10, pady=10)
        frame.pack(fill='x', pady=(0, 10))

        # 字号
        size_frame = Frame(frame)
        size_frame.pack(fill='x', pady=2)

        Label(size_frame, text="字号:", font=("Microsoft YaHei", 9)).pack(side='left')

        size_scale = Scale(
            size_frame,
            from_=8,
            to=72,
            orient='horizontal',
            variable=self.font_size_var,
            length=200
        )
        size_scale.pack(side='left', padx=5)

        size_label = Label(size_frame, textvariable=self.font_size_var, font=("Microsoft YaHei", 9), width=3)
        size_label.pack(side='left')
        Label(size_frame, text="px", font=("Microsoft YaHei", 9)).pack(side='left')

        # 行距和字间距
        spacing_frame = Frame(frame)
        spacing_frame.pack(fill='x', pady=2)

        Label(spacing_frame, text="行距:", font=("Microsoft YaHei", 9)).pack(side='left')
        line_scale = Scale(
            spacing_frame,
            from_=-5,
            to=20,
            orient='horizontal',
            variable=self.line_spacing_var,
            length=100
        )
        line_scale.pack(side='left', padx=5)

        Label(spacing_frame, text="字间距:", font=("Microsoft YaHei", 9)).pack(side='left', padx=(20, 0))
        char_scale = Scale(
            spacing_frame,
            from_=-2,
            to=10,
            orient='horizontal',
            variable=self.char_spacing_var,
            length=100
        )
        char_scale.pack(side='left', padx=5)

    def _create_render_section(self, parent):
        """创建渲染选项区域"""
        frame = LabelFrame(parent, text="渲染选项", font=("Microsoft YaHei", 10, "bold"), padx=10, pady=10)
        frame.pack(fill='x', pady=(0, 10))

        # 灰度模式
        mode_frame = Frame(frame)
        mode_frame.pack(fill='x', pady=2)

        Checkbutton(
            mode_frame,
            text="2-bit 灰度 (推荐)",
            variable=self.is_2bit_var,
            font=("Microsoft YaHei", 9)
        ).pack(side='left')

        Checkbutton(
            mode_frame,
            text="变高字形",
            variable=self.variable_height_var,
            font=("Microsoft YaHei", 9)
        ).pack(side='left', padx=20)

        # 抗锯齿
        aa_frame = Frame(frame)
        aa_frame.pack(fill='x', pady=2)

        Label(aa_frame, text="抗锯齿:", font=("Microsoft YaHei", 9)).pack(side='left')

        aa_options = ["none", "default", "light", "standard"]
        aa_combo = ttk.Combobox(
            aa_frame,
            textvariable=self.anti_alias_var,
            values=aa_options,
            width=10,
            state='readonly'
        )
        aa_combo.pack(side='left', padx=5)

        # Gamma
        gamma_frame = Frame(frame)
        gamma_frame.pack(fill='x', pady=2)

        Label(gamma_frame, text="Gamma:", font=("Microsoft YaHei", 9)).pack(side='left')

        gamma_scale = Scale(
            gamma_frame,
            from_=0.1,
            to=3.0,
            resolution=0.1,
            orient='horizontal',
            variable=self.gamma_var,
            length=150
        )
        gamma_scale.pack(side='left', padx=5)

        gamma_label = Label(gamma_frame, textvariable=self.gamma_var, font=("Microsoft YaHei", 9), width=4)
        gamma_label.pack(side='left')

        # Hinting
        Checkbutton(
            frame,
            text="启用 Hinting",
            variable=self.hinting_var,
            font=("Microsoft YaHei", 9)
        ).pack(anchor='w', pady=2)

    def _create_preview_section(self, parent):
        """创建预览区域"""
        frame = LabelFrame(parent, text="字体预览", font=("Microsoft YaHei", 10, "bold"), padx=10, pady=10)
        frame.pack(fill='both', expand=True, pady=(0, 10))

        # 预览画布
        self.preview_canvas = FontPreviewCanvas(frame, width=350, height=250)
        self.preview_canvas.pack(fill='both', expand=True)



    def _create_progress_section(self, parent):
        """创建进度显示区域"""
        frame = LabelFrame(parent, text="转换进度", font=("Microsoft YaHei", 10, "bold"), padx=10, pady=10)
        frame.pack(fill='x', pady=(0, 10))

        # 进度条
        self.progress_bar = ttk.Progressbar(
            frame,
            variable=self.progress_var,
            maximum=100,
            length=300,
            mode='determinate'
        )
        self.progress_bar.pack(fill='x', pady=5)

        # 状态标签
        self.status_label = Label(
            frame,
            textvariable=self.status_var,
            font=("Microsoft YaHei", 9)
        )
        self.status_label.pack(anchor='w')

        # 日志文本框
        log_frame = Frame(frame)
        log_frame.pack(fill='both', expand=True, pady=5)

        self.log_text = Text(
            log_frame,
            height=8,
            font=("Consolas", 9),
            wrap='word'
        )
        self.log_text.pack(side='left', fill='both', expand=True)

        scrollbar = Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=scrollbar.set)

    def _create_button_section(self, parent):
        """创建按钮区域"""
        frame = Frame(parent)
        frame.pack(fill='x', pady=15)

        # 左侧按钮（帮助 + 功能按钮）
        left_buttons = Frame(frame)
        left_buttons.pack(side='left')

        # 帮助按钮
        Button(
            left_buttons,
            text="?",
            font=("Microsoft YaHei", 10, "bold"),
            width=3,
            command=self._show_help
        ).pack(side='left', padx=5)

        Button(
            left_buttons,
            text="查看字体信息",
            font=("Microsoft YaHei", 9),
            command=self._show_font_info
        ).pack(side='left', padx=5)

        Button(
            left_buttons,
            text="打开输出目录",
            font=("Microsoft YaHei", 9),
            command=self._open_output_dir
        ).pack(side='left', padx=5)

        # 右侧按钮（开始转换 + 退出）
        right_buttons = Frame(frame)
        right_buttons.pack(side='right')

        self.convert_button = Button(
            right_buttons,
            text="开始转换",
            font=("Microsoft YaHei", 10, "bold"),
            bg="#4CAF50",
            fg="white",
            width=15,
            command=self._start_conversion
        )
        self.convert_button.pack(side='left', padx=5)

        Button(
            right_buttons,
            text="退出",
            font=("Microsoft YaHei", 9),
            width=10,
            command=self.root.quit
        ).pack(side='left', padx=5)

    def _create_status_bar(self, parent):
        """创建状态栏"""
        # 状态栏保留但不显示版本号
        pass

    def _center_window(self):
        """将窗口居中"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    # ==================== 事件处理 ====================

    def _browse_font(self):
        """浏览字体文件"""
        file_path = filedialog.askopenfilename(
            title="选择字体文件",
            filetypes=[
                ("字体文件", "*.ttf *.otf *.woff *.woff2"),
                ("TrueType", "*.ttf"),
                ("OpenType", "*.otf"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.font_path_var.set(file_path)
            # 自动设置输出路径（总是更新）
            output = Path(file_path).with_suffix('.epdfont')
            self.output_path_var.set(str(output))
            # 刷新预览
            self._refresh_preview()

    def _browse_output(self):
        """浏览输出文件"""
        file_path = filedialog.asksaveasfilename(
            title="保存 EPDFont 文件",
            defaultextension=".epdfont",
            filetypes=[("EPDFont 文件", "*.epdfont")]
        )
        if file_path:
            self.output_path_var.set(file_path)

    def _update_charset_info(self, *args):
        """更新字符集信息"""
        charset = self.charset_var.get()
        info = self.charset_manager.get_charset_info(charset)
        char_count = info.get('char_count', '未知')
        self.charset_info_label.config(
            text=f"{info['name']} (~{char_count}字符)"
        )

    def _refresh_preview(self):
        """刷新字体预览"""
        self.preview_canvas.update_preview(
            font_path=self.font_path_var.get(),
            font_size=self.font_size_var.get(),
            line_spacing=self.line_spacing_var.get(),
            char_spacing=self.char_spacing_var.get(),
            anti_alias=self.anti_alias_var.get(),
            gamma=self.gamma_var.get(),
            hinting=self.hinting_var.get()
        )

    def _show_help(self):
        """显示帮助信息"""
        help_text = """使用说明

【基本流程】
1. 选择字体文件（TTF/OTF格式）
2. 设置输出文件路径
3. 选择字符集（3500/7000常用字）
4. 调整字体参数
5. 点击"开始转换"

【各区域说明】

文件选择：
  • 字体文件 - 要转换的TTF/OTF字体
  • 输出文件 - 生成的.epdfont文件路径

字符集：
  • 3500 - 3500常用汉字+符号（推荐）
  • 7000 - 7000常用汉字+符号（更全面）
  • all - 所有汉字（文件较大）
  • symbols - 仅符号

字体样式：
  • 字号 - 字体大小（8-72像素）
  • 行距 - 行间距调整
  • 字间距 - 字符间距调整

渲染选项：
  • 2-bit灰度 - 推荐，显示效果更好
  • 变高字形 - 适合位图字体
  • 抗锯齿 - 字体平滑处理（none/default/light/standard）
  • Gamma - 灰度校正（0.1-3.0）
  • Hinting - 字体优化

【按钮说明】

  ? - 显示此帮助信息
  查看字体信息 - 显示选中字体的详细信息
  打开输出目录 - 打开输出文件所在文件夹
  开始转换 - 开始字体转换过程
  退出 - 关闭程序

【提示】
• 转换过程会显示进度条和日志
• 字体预览会实时响应参数变化
• 支持自定义字符添加到字符集
"""

        # 创建帮助对话框
        help_window = Toplevel(self.root)
        help_window.title("使用帮助")
        help_window.geometry("550x600")
        help_window.transient(self.root)
        help_window.grab_set()
        help_window.focus_set()

        # 主框架
        main_frame = Frame(help_window, padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)

        # 文本框框架
        text_frame = Frame(main_frame)
        text_frame.pack(fill='both', expand=True)

        # 文本框
        text_widget = Text(text_frame, wrap='word', font=("Microsoft YaHei", 10), padx=10, pady=10)
        text_widget.pack(side='left', fill='both', expand=True)
        text_widget.insert('1.0', help_text)
        text_widget.config(state='disabled')

        # 滚动条
        scrollbar = Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        text_widget.config(yscrollcommand=scrollbar.set)

        # 关闭按钮
        Button(main_frame, text="关闭", command=help_window.destroy, font=("Microsoft YaHei", 10), width=10).pack(pady=10)

        # 居中显示
        help_window.update_idletasks()
        x = (help_window.winfo_screenwidth() // 2) - (550 // 2)
        y = (help_window.winfo_screenheight() // 2) - (600 // 2)
        help_window.geometry(f'+{x}+{y}')

        help_window.wait_window()

    def _show_font_info(self):
        """显示字体信息"""
        font_path = self.font_path_var.get()
        if not font_path or not os.path.exists(font_path):
            messagebox.showerror("错误", "请先选择有效的字体文件")
            return

        try:
            import freetype
            face = freetype.Face(font_path)

            # 获取字符映射信息
            charmaps_info = []
            for i in range(face.num_charmaps):
                try:
                    face.select_charmap(i)
                    charmaps_info.append(f"  - 平台ID: {face.charmap.platform_id}, 编码ID: {face.charmap.encoding_id}")
                except:
                    pass

            info_text = f"""
字体信息:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
字体名称: {face.family_name.decode('utf-8', errors='ignore') if face.family_name else 'Unknown'}
样式: {face.style_name.decode('utf-8', errors='ignore') if face.style_name else 'Regular'}
字形数量: {face.num_glyphs}
字符集数量: {face.num_charmaps}

字体度量:
  上升: {face.ascender >> 6} px
  下降: {face.descender >> 6} px
  高度: {face.height >> 6} px
  最大前进宽度: {face.max_advance_width >> 6} px
  最大前进高度: {face.max_advance_height >> 6} px

支持的字符表:
"""
            if charmaps_info:
                info_text += "\n".join(charmaps_info[:5])
            else:
                info_text += "  (无法获取字符表信息)"

            messagebox.showinfo("字体信息", info_text)

        except Exception as e:
            messagebox.showerror("错误", f"无法读取字体信息:\n{str(e)}")

    def _open_output_dir(self):
        """打开输出目录"""
        output_path = self.output_path_var.get()
        if output_path:
            output_dir = os.path.dirname(output_path)
            if os.path.exists(output_dir):
                os.startfile(output_dir)
            else:
                os.startfile(os.getcwd())
        else:
            os.startfile(os.getcwd())

    def _log(self, message):
        """添加日志"""
        self.log_text.insert('end', message + '\n')
        self.log_text.see('end')
        self.root.update_idletasks()

    def _start_conversion(self):
        """开始转换"""
        # 验证输入
        font_path = self.font_path_var.get()
        if not font_path or not os.path.exists(font_path):
            messagebox.showerror("错误", "请选择有效的字体文件")
            return

        output_path = self.output_path_var.get()
        if not output_path:
            messagebox.showerror("错误", "请指定输出文件路径")
            return

        # 禁用转换按钮
        self.convert_button.config(state='disabled', text="转换中...")
        self.progress_var.set(0)
        self.log_text.delete('1.0', 'end')

        # 在新线程中执行转换
        thread = threading.Thread(target=self._do_conversion)
        thread.daemon = True
        thread.start()

    def _do_conversion(self):
        """执行转换（在后台线程中）"""
        try:
            font_path = self.font_path_var.get()
            output_path = self.output_path_var.get()

            self.status_var.set("正在加载字符集...")
            self.root.after(0, lambda: self._log(f"加载字符集: {self.charset_var.get()}"))

            # 设置进度回调
            def progress_callback(current, total, message):
                progress = int((current / total) * 100)
                self.progress_var.set(progress)
                self.status_var.set(f"{message} ({current}/{total})")
                if current % 100 == 0:
                    self.root.after(0, lambda m=message: self._log(m))

            self.converter.set_progress_callback(progress_callback)

            # 执行转换
            self.status_var.set("开始转换...")
            self.root.after(0, lambda: self._log("开始转换..."))

            result = self.converter.convert(
                font_path=font_path,
                output_path=output_path,
                charset=self.charset_var.get(),
                font_size=self.font_size_var.get(),
                is_2bit=self.is_2bit_var.get(),
                font_weight=self.font_weight_var.get(),
                line_spacing=self.line_spacing_var.get(),
                char_spacing=self.char_spacing_var.get(),
                anti_alias=self.anti_alias_var.get(),
                gamma=self.gamma_var.get(),
                hinting=self.hinting_var.get(),
                variable_height=self.variable_height_var.get(),
                custom_chars=self.custom_chars_var.get()
            )

            # 显示结果
            self.status_var.set("转换完成!")
            self.progress_var.set(100)

            result_text = f"""
转换完成!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
输出文件: {result['output_path']}
文件大小: {result['file_size_kb']:.2f} KB
总字符数: {result['total_chars']}
成功: {result['success_count']}
跳过: {result['skip_count']}
"""
            self.root.after(0, lambda: self._log(result_text))

            if result['errors']:
                self.root.after(0, lambda: self._log("\n警告:"))
                for error in result['errors'][:5]:
                    self.root.after(0, lambda e=error: self._log(f"  - {e}"))

            self.root.after(0, lambda: messagebox.showinfo("完成", "字体转换成功!"))

        except Exception as e:
            self.status_var.set(f"错误: {str(e)}")
            self.root.after(0, lambda: self._log(f"错误: {str(e)}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"转换失败:\n{str(e)}"))

        finally:
            # 恢复转换按钮
            self.root.after(0, lambda: self.convert_button.config(
                state='normal',
                text="开始转换"
            ))


def main():
    """GUI 主函数"""
    root = Tk()
    app = EPDFontGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
