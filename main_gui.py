import customtkinter as ctk
from tkinter import filedialog
import threading
import os
import time

# 导入你的核心功能模块
from signin import manual_google_login
from core_scraper import test_google_lens_upload

# 设置 CustomTkinter 主题
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class GoogleLensApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- 窗口基础设置 ---
        self.title("Google Lens 批处理引擎")
        self.geometry("500x650")
        self.resizable(False, False)

        self.target_folder = ""  # 存放用户选择的文件夹路径

        # --- UI 布局构建 ---
        self.create_widgets()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # --- 第一步：账号授权区域 ---
        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(pady=10, padx=20, fill="x")

        self.login_label = ctk.CTkLabel(self.frame_login, text="第一步：初始化与环境授权",
                                        font=ctk.CTkFont(weight="bold"))
        self.login_label.pack(pady=(10, 5))

        self.btn_login = ctk.CTkButton(
            self.frame_login,
            text="🔓 浏览器登录/授权",
            fg_color="#D9534F",
            hover_color="#C9302C",
            command=self.start_login_thread
        )
        self.btn_login.pack(pady=(0, 10))

        # --- 第二步：任务配置区域 ---
        self.frame_task = ctk.CTkFrame(self)
        self.frame_task.pack(pady=10, padx=20, fill="x")

        self.task_label = ctk.CTkLabel(self.frame_task, text="第二步：选择目标文件夹", font=ctk.CTkFont(weight="bold"))
        self.task_label.pack(pady=(10, 5))

        self.btn_folder = ctk.CTkButton(self.frame_task, text="📁 选择包含图片的文件夹", command=self.select_folder)
        self.btn_folder.pack(pady=(0, 5))

        self.path_label = ctk.CTkLabel(self.frame_task, text="当前未选择任何文件夹", text_color="gray")
        self.path_label.pack(pady=(0, 10))

        # --- 第三步：核心执行区域 ---
        self.btn_start = ctk.CTkButton(
            self,
            text="🚀 开始自动识图与下载",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color="#5CB85C",
            hover_color="#4CAE4C",
            state="disabled",  # 没选文件夹前禁用
            command=self.start_scraper_thread
        )
        self.btn_start.pack(pady=20, padx=20, fill="x")

        # --- 第四步：日志输出监控区 ---
        self.log_box = ctk.CTkTextbox(self, height=180, state="disabled")
        self.log_box.pack(pady=(0, 20), padx=20, fill="x")
        self.log_message("系统初始化完毕，等待操作...")

    # --- 软件关闭清理 ---

    def on_closing(self):
        """窗口关闭时的安全清理逻辑"""
        try:
            self.log_message("正在清理底层引擎并释放内存，请稍候...")
            self.update() # 刷新 UI，让用户看到提示
        except:
            pass
            
        # 🌟 核心修复：强制清理被主线程抛弃的 Playwright Node.js 驱动
        import subprocess
        try:
            # 杀掉残留的 node 进程，释放对 PyInstaller _MEI 临时目录的占用锁
            subprocess.run(
                ['taskkill', '/F', '/IM', 'node.exe'], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW # 防止闪黑框
            )
        except Exception:
            pass
            
        # 销毁 GUI 窗口
        self.destroy()
        
        # 使用 os._exit(0) 进行硬退出，直接终结整个 Python 进程树
        os._exit(0)

    # --- 核心交互逻辑 ---

    def log_message(self, message):
        """线程安全的日志打印功能"""
        # 允许写入
        self.log_box.configure(state="normal")
        # 插入时间戳和内容
        current_time = time.strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{current_time}] {message}\n")
        # 自动滚动到底部
        self.log_box.see("end")
        # 锁定为只读
        self.log_box.configure(state="disabled")
        # 同时打印到控制台方便调试
        print(message)

    def select_folder(self):
        """选择文件夹并解锁开始按钮"""
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.target_folder = folder_path
            self.path_label.configure(text=f"已选择: {folder_path}", text_color="white")
            self.btn_start.configure(state="normal")
            self.log_message(f"目标文件夹已设定: {folder_path}")

    # --- 多线程控制区（绝对不能在主线程跑 Playwright） ---

    def start_login_thread(self):
        self.log_message("正在唤起独立登录环境，请在弹出的窗口中操作...")
        self.btn_login.configure(state="disabled", text="环境运行中...")
        # 新开线程执行登录
        threading.Thread(target=self.run_login, daemon=True).start()

    def run_login(self):
        try:
            manual_google_login()
            self.log_message("登录环境已成功关闭！状态已保存。")
        except Exception as e:
            self.log_message(f"登录过程发生异常: {e}")
        finally:
            self.btn_login.configure(state="normal", text="🔓 浏览器进行登录/授权")

    def start_scraper_thread(self):
        self.log_message("🚀 自动化流水线启动！")
        self.btn_start.configure(state="disabled", text="流水线作业中...")
        self.btn_login.configure(state="disabled")
        self.btn_folder.configure(state="disabled")

        threading.Thread(target=self.run_scraper_loop, daemon=True).start()

    def run_scraper_loop(self):
        try:
            # 遍历所选文件夹下的所有图片
            valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
            files = [f for f in os.listdir(self.target_folder) if f.lower().endswith(valid_extensions)]

            if not files:
                self.log_message("❌ 目标文件夹中没有找到任何支持的图片文件！")
                return

            self.log_message(f"📦 共发现 {len(files)} 张图片，开始排队处理...")

            for index, file_name in enumerate(files, 1):
                self.log_message(f"▶️ 开始处理第 {index}/{len(files)} 张图片: {file_name}")

                # 构造绝对路径
                image_full_path = os.path.join(self.target_folder, file_name)

                # 这里调用你的原函数。
                # 注意：你之前的 test_google_lens_upload 内部是用 os.path.join(current_dir, image_filename) 的
                # 建议稍微修改一下那个函数，让它直接接收完整的绝对路径 (image_full_path)。
                # 为了兼容你现在的代码，如果它只接收文件名，请确保你的测试图片也在根目录，
                # 但最终版需要让核心代码直接处理传进来的 image_full_path！

                test_google_lens_upload(image_full_path)

                self.log_message(f"✅ 图片 {file_name} 作业结束。")
                time.sleep(2)  # 缓冲一下，防止风控

            self.log_message("🎉 所有目标图片已全部处理完毕！")

        except Exception as e:
            self.log_message(f"❌ 流水线崩溃: {e}")
        finally:
            # 恢复 UI 按钮状态
            self.btn_start.configure(state="normal", text="🚀 开始全自动识图与下载")
            self.btn_login.configure(state="normal")
            self.btn_folder.configure(state="normal")


if __name__ == "__main__":
    app = GoogleLensApp()
    app.mainloop()