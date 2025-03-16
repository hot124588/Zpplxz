import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import subprocess
from datetime import datetime
import uuid
import requests
import webbrowser

# 假设这是当前软件的版本号
CURRENT_VERSION = "4.1"


class ImageProcessorPro:
    def __init__(self, root):
        self.root = root
        self.root.title("尘飞图片处理器 v" + CURRENT_VERSION)
        self.root.geometry("1200x800")

        self.thumbnail_slots = []
        self.batch_files = []
        self.current_rotation = 0

        self.create_widgets()
        self.center_window()
        self.root.bind("<MouseWheel>", self.on_mousewheel)

        # 检查更新
        self.check_for_updates()

    def center_window(self):
        """窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')

    def create_widgets(self):
        tab_control = ttk.Notebook(self.root)

        # 缩略图模式标签页
        thumbnail_tab = ttk.Frame(tab_control)
        self.create_thumbnail_tab(thumbnail_tab)
        tab_control.add(thumbnail_tab, text="缩略图模式")

        # 批量模式标签页
        batch_tab = ttk.Frame(tab_control)
        self.create_batch_tab(batch_tab)
        tab_control.add(batch_tab, text="批量模式")

        tab_control.pack(expand=1, fill="both")
        self.status_bar = ttk.Label(self.root, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_thumbnail_tab(self, parent):
        """缩略图模式界面"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        # 左侧滚动区域
        left_container = ttk.Frame(main_frame, width=400)
        left_container.pack(side=tk.LEFT, fill=tk.Y)

        canvas = tk.Canvas(left_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建10个缩略图插槽
        self.thumbnail_slots = []
        for i in range(10):
            slot_frame = ttk.Frame(scrollable_frame, relief="groove", borderwidth=2)
            slot_frame.pack(pady=5, fill=tk.X, padx=5)

            slot = {
                'frame': slot_frame,
                'add_btn': ttk.Button(slot_frame, text="添加图片",
                                      command=lambda idx=i: self.add_thumbnail(idx)),
                'path': None,
                'rotation': 0,
                'label': None,
                'rotate_btn': None,
                'clear_btn': None,
                'image': None
            }
            slot['add_btn'].pack(expand=True)
            self.thumbnail_slots.append(slot)

        # 右侧控制面板
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        instruction_frame = ttk.Frame(right_frame)
        instruction_frame.pack(pady=10, fill=tk.X)

        instructions = (
            "操作指南：\n\n"
            "1. 左侧可添加最多10张图片\n"
            "2. 使用滚动条查看所有图片\n"
            "3. 单个图片支持旋转和删除\n"
            "4. 点击下方按钮批量处理\n"
            "5. 处理结果自动保存到CF_OK目录"
        )
        ttk.Label(
            instruction_frame,
            text=instructions,
            justify=tk.CENTER,
            font=('微软雅黑', 12),
            wraplength=350
        ).pack(pady=5)

        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(pady=15)

        btn_config = {'padding': 6, 'width': 18}
        ttk.Button(btn_frame, text="全部旋转",
                   command=self.rotate_all_thumbnails, **btn_config).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="开始处理",
                   command=self.process_all, **btn_config).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="清空全部",
                   command=self.clear_all_thumbnails, **btn_config).grid(row=0, column=2, padx=5)

        self.thumbnail_progress = ttk.Progressbar(right_frame, orient="horizontal", length=400)
        self.thumbnail_progress.pack(pady=15)

        ttk.Label(right_frame, text="Developed by ChenFei using DeepSeek", font=('Arial', 9)).pack(side=tk.BOTTOM)

    def create_batch_tab(self, parent):
        """批量模式界面"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        # 创建顶部滚动容器
        scroll_container = ttk.Frame(main_frame)
        scroll_container.pack(fill=tk.BOTH, expand=True)
        # 文件列表区域
        list_frame = ttk.LabelFrame(main_frame, text="待处理文件列表（支持多选）")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        scrollbar = ttk.Scrollbar(list_frame)
        self.batch_listbox = tk.Listbox(list_frame,
                                        selectmode=tk.EXTENDED,
                                        yscrollcommand=scrollbar.set,
                                        height=8,
                                        font=('Arial', 10))
        scrollbar.config(command=self.batch_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.batch_listbox.pack(fill=tk.BOTH, expand=True)

        # 实时预览区域（显示前20个文件）
        preview_frame = ttk.LabelFrame(main_frame, text="实时预览（前20个文件）")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # 双滚动条容器
        self.preview_canvas = tk.Canvas(preview_frame, height=200, highlightthickness=0)
        h_scroll = ttk.Scrollbar(preview_frame, orient="horizontal", command=self.preview_canvas.xview)
        v_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_canvas.yview)

        self.preview_container = ttk.Frame(self.preview_canvas)
        self.preview_canvas.create_window((0, 0), window=self.preview_container, anchor="nw")

        # 配置滚动区域
        self.preview_container.bind("<Configure>",
                                    lambda e: self.preview_canvas.configure(
                                        scrollregion=self.preview_canvas.bbox("all")
                                    ))
        self.preview_canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        # 布局组件
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        # 操作控制面板
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(pady=10, fill=tk.X)

        # 文件操作按钮
        ttk.Button(control_frame, text="添加文件", command=self.add_batch_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="移除选中", command=self.remove_selected_batch).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="清空列表", command=self.clear_batch_list).pack(side=tk.LEFT, padx=5)

        # 旋转控制面板
        rotate_frame = ttk.LabelFrame(main_frame, text="批量旋转设置")
        rotate_frame.pack(fill=tk.X, pady=10)

        # 角度选择组件
        ttk.Label(rotate_frame, text="旋转角度：").pack(side=tk.LEFT, padx=5)
        self.rotation_var = tk.IntVar(value=0)
        ttk.Spinbox(rotate_frame,
                    from_=0,
                    to=360,
                    increment=90,
                    textvariable=self.rotation_var,
                    width=5,
                    command=self.update_batch_previews).pack(side=tk.LEFT, padx=5)

        # 方向选择组件
        self.direction_var = tk.StringVar(value="clockwise")
        ttk.Radiobutton(rotate_frame,
                        text="顺时针",
                        variable=self.direction_var,
                        value="clockwise",
                        command=self.update_batch_previews).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(rotate_frame,
                        text="逆时针",
                        variable=self.direction_var,
                        value="counter_clockwise",
                        command=self.update_batch_previews).pack(side=tk.LEFT, padx=10)

        # 应用预览按钮
        ttk.Button(rotate_frame,
                   text="更新预览",
                   command=self.update_batch_previews,
                   style='Accent.TButton').pack(side=tk.RIGHT, padx=10)

        # 进度条
        self.batch_progress = ttk.Progressbar(main_frame,
                                              orient="horizontal",
                                              length=400,
                                              mode="determinate")
        self.batch_progress.pack(pady=10, fill=tk.X)

        # 处理按钮（修改布局后的部分）
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10, fill=tk.X)

        ttk.Button(btn_frame,
                   text="执行批量处理",
                   command=self.process_all,
                   style='Accent.TButton').pack(fill=tk.X, pady=5)

    def on_mousewheel(self, event):
        """鼠标滚轮控制水平滚动"""
        if event.delta > 0:
            self.preview_canvas.xview_scroll(-1, "units")
        else:
            self.preview_canvas.xview_scroll(1, "units")

    def update_batch_previews(self):
        """更新所有文件的实时预览（仅显示前20个）"""
        # 清空现有预览
        for widget in self.preview_container.winfo_children():
            widget.destroy()

        # 计算最终旋转角度
        base_angle = self.rotation_var.get()
        direction = -1 if self.direction_var.get() == "clockwise" else 1
        self.current_rotation = base_angle * direction

        # 网格布局参数
        thumbs_per_row = 5
        thumb_size = 120

        # 生成缩略图网格（仅显示前20个文件）
        row_frame = None
        for idx, path in enumerate(self.batch_files[:20]):
            try:
                # 每行创建新容器
                if idx % thumbs_per_row == 0:
                    row_frame = ttk.Frame(self.preview_container)
                    row_frame.pack(fill=tk.X, pady=5)

                # 单个缩略图容器
                thumb_frame = ttk.Frame(row_frame, relief="groove", borderwidth=1)
                thumb_frame.pack(side=tk.LEFT, padx=5, pady=5)

                # 加载并旋转图片
                with Image.open(path) as img:
                    rotated_img = img.rotate(self.current_rotation, expand=True)
                    thumbnail = self.create_thumbnail(rotated_img, (thumb_size, thumb_size))

                # 显示缩略图
                label = ttk.Label(thumb_frame, image=thumbnail)
                label.image = thumbnail
                label.pack()

                # 显示文件信息
                info_text = f"{os.path.basename(path)[:15]}\n旋转角度：{self.current_rotation}°"
                ttk.Label(thumb_frame,
                          text=info_text,
                          wraplength=thumb_size - 20,
                          font=('Arial', 8),
                          justify=tk.CENTER).pack()

            except Exception as e:
                print(f"生成预览失败：{str(e)}")

        # 更新界面
        self.preview_canvas.update_idletasks()

    def create_thumbnail(self, img, size=(160, 160)):
        """生成缩略图"""
        img_copy = img.copy()
        img_copy.thumbnail(size)
        return ImageTk.PhotoImage(img_copy)

    def add_thumbnail(self, idx):
        """添加缩略图"""
        file_path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        if not file_path:
            return

        try:
            with Image.open(file_path) as img:
                slot = self.thumbnail_slots[idx]
                slot['add_btn'].pack_forget()

                thumbnail = self.create_thumbnail(img)
                slot['label'] = ttk.Label(slot['frame'], image=thumbnail)
                slot['label'].image = thumbnail
                slot['label'].pack()

                btn_frame = ttk.Frame(slot['frame'])
                btn_frame.pack()

                slot['rotate_btn'] = ttk.Button(
                    btn_frame, text="↻ 旋转",
                    command=lambda idx=idx: self.rotate_thumbnail(idx)
                )
                slot['rotate_btn'].pack(side=tk.LEFT, padx=2)

                slot['clear_btn'] = ttk.Button(
                    btn_frame, text="× 清除",
                    command=lambda idx=idx: self.clear_thumbnail_slot(idx)
                )
                slot['clear_btn'].pack(side=tk.LEFT, padx=2)

                slot.update({
                    'path': file_path,
                    'image': img.copy(),
                    'rotation': 0
                })
        except Exception as e:
            messagebox.showerror("加载失败", f"无法读取图片：{str(e)}")

    def rotate_thumbnail(self, idx):
        """旋转单个缩略图"""
        slot = self.thumbnail_slots[idx]
        if slot['path']:
            slot['rotation'] = (slot['rotation'] + 90) % 360
            rotated_img = slot['image'].rotate(-slot['rotation'], expand=True)
            thumbnail = self.create_thumbnail(rotated_img)
            slot['label'].configure(image=thumbnail)
            slot['label'].image = thumbnail

    def clear_thumbnail_slot(self, idx):
        """清空缩略图插槽"""
        slot = self.thumbnail_slots[idx]
        for widget in [slot['label'], slot['rotate_btn'], slot['clear_btn']]:
            if widget: widget.pack_forget()
        slot.update({
            'path': None,
            'rotation': 0,
            'image': None,
            'label': None,
            'rotate_btn': None,
            'clear_btn': None
        })
        slot['add_btn'].pack()

    def rotate_all_thumbnails(self):
        """旋转所有缩略图"""
        for idx in range(10):
            if self.thumbnail_slots[idx]['path']:
                self.rotate_thumbnail(idx)

    def clear_all_thumbnails(self):
        """清空所有缩略图插槽"""
        if messagebox.askyesno("确认清除", "确定要清除所有图片吗？"):
            for idx in range(10):
                self.clear_thumbnail_slot(idx)

    def add_batch_files(self):
        """添加批量处理文件"""
        files = filedialog.askopenfilenames(
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        if files:
            for f in files:
                if f not in self.batch_files:
                    self.batch_files.append(f)
                    self.batch_listbox.insert(tk.END, os.path.basename(f))
            self.update_batch_previews()
            self.update_status(f"已添加 {len(files)} 个文件")

    def remove_selected_batch(self):
        """移除选中文件"""
        selections = self.batch_listbox.curselection()
        for idx in reversed(selections):
            del self.batch_files[idx]
            self.batch_listbox.delete(idx)
        self.update_batch_previews()
        self.update_status(f"已移除 {len(selections)} 个文件")

    def clear_batch_list(self):
        """清空文件列表"""
        if messagebox.askyesno("确认清空", "确定要清空所有文件吗？"):
            self.batch_files.clear()
            self.batch_listbox.delete(0, tk.END)
            self.update_batch_previews()
            self.update_status("文件列表已清空")

    def process_all(self):
        """执行批量处理"""
        output_dir = os.path.join(os.getcwd(), "CF_OK")
        os.makedirs(output_dir, exist_ok=True)

        process_queue = []

        # 收集缩略图模式文件
        for slot in self.thumbnail_slots:
            if slot['path']:
                process_queue.append({
                    'path': slot['path'],
                    'angle': -slot['rotation']
                })

        # 收集批量模式文件
        if self.batch_files:
            process_queue.extend([{
                'path': path,
                'angle': self.current_rotation
            } for path in self.batch_files])

        total = len(process_queue)
        if total == 0:
            messagebox.showwarning("无操作", "没有需要处理的图片")
            return

        progress = self.batch_progress
        progress['maximum'] = total
        progress['value'] = 0

        success_count = 0
        for idx, item in enumerate(process_queue, 1):
            try:
                with Image.open(item['path']) as img:
                    rotated = img.rotate(item['angle'], expand=True)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
                    unique_code = uuid.uuid4().hex[:6]
                    ext = os.path.splitext(item['path'])[1].lower()
                    save_path = os.path.join(output_dir, f"{timestamp}_{unique_code}{ext}")
                    rotated.save(save_path, quality=95)

                    success_count += 1
                    progress['value'] = idx
                    self.update_status(f"正在处理：{os.path.basename(item['path'])}")
                    self.root.update_idletasks()

            except Exception as e:
                messagebox.showerror("处理失败", f"{os.path.basename(item['path'])} 处理失败：{str(e)}")

        subprocess.Popen(f'explorer "{os.path.normpath(output_dir)}"')
        messagebox.showinfo("处理完成",
                            f"成功处理 {success_count}/{total} 个文件\n输出目录已自动打开")
        progress['value'] = 0

    def update_status(self, message):
        """更新状态栏"""
        self.status_bar.config(text=f"状态：{message}")

    def check_for_updates(self):
        """检查是否有新版本可用"""
        try:
            response = requests.get("https://your-update-server.com/version.json")  # 替换为你的更新服务器地址
            response.raise_for_status()
            latest_version = response.json().get("version", "")

            if latest_version and latest_version != CURRENT_VERSION:
                if messagebox.askyesno("发现新版本", f"发现新版本 v{latest_version}，是否前往下载？"):
                    webbrowser.open("https://your-update-server.com/download")  # 替换为你的下载页面地址
            else:
                self.update_status("当前已是最新版本")
        except requests.RequestException as e:
            self.update_status(f"检查更新失败: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('Accent.TButton',
                    font=('Arial', 10, 'bold'),
                    foreground='white',
                    background='#0078D7',
                    padding=6)
    style.map('Accent.TButton',
              background=[('active', '#006CBA'), ('disabled', '#D9D9D9')])
    root.option_add('*TCombobox*Listbox.font', ('Arial', 10))
    app = ImageProcessorPro(root)
    root.mainloop()