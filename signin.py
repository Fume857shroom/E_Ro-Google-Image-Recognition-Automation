from playwright.sync_api import sync_playwright
from browser_locator import get_system_chrome_path
import os

def manual_google_login():
    base_dir = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    user_data_dir = os.path.join(base_dir, "GoogleLensAuto_Data", "chrome_data")
    os.makedirs(user_data_dir, exist_ok=True)

    print(f"📁 Chrome 用户数据目录已固定为: {user_data_dir}")

    print("🚀 启动专属登录浏览器...")
    chrome_path = get_system_chrome_path()

    with sync_playwright() as p:
        # 添加 executable_path，确保与主程序使用同一个浏览器核心
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            executable_path=chrome_path,  # <--- 新增这一行
            viewport={'width': 1280, 'height': 800},
            locale='en-US',
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0]

        page.goto("https://myaccount.google.com/")

        print("\n" + "="*50)
        print("🛑 【无限循环：手动登录模式已开启】")
        print("1. 浏览器现已锁定开启状态，你有无限的时间完成登录。")
        print("2. 验证码、两步验证、甚至是异地登录拦截，都可以慢慢处理。")
        print("3. 处理完毕后，请【手动点击浏览器右上角的 X】关闭浏览器。")
        print("="*50 + "\n")

        try:
            while len(context.pages) > 0:
                # 每次停顿 1 秒，防止死循环把 CPU 跑满
                page.wait_for_timeout(1000)
        except Exception:
            # 捕获因你手动关掉浏览器而可能产生的断开连接报错
            pass

        print("✅ 无限循环解除！")
        print("💾 您的 Google 登录状态已安全保存在了 'chrome_data' 文件夹中。")

if __name__ == "__main__":
    manual_google_login()