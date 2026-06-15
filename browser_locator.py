import os
import sys


def get_system_chrome_path():
    """自动寻找用户电脑上的系统级 Chrome 浏览器路径"""
    if sys.platform == "win32":
        # 方案A：通过 Windows 注册表精准查找（最可靠）
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
            path, _ = winreg.QueryValueEx(key, "")
            return path
        except WindowsError:
            pass

        # 方案B：常规安装路径轮询（以防注册表被篡改）
        paths = [
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), r"Google\Chrome\Application\chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"),
                         r"Google\Chrome\Application\chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe")
        ]
        for p in paths:
            if os.path.exists(p):
                return p

    elif sys.platform == "darwin":  # macOS
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    else:  # Linux
        return "/usr/bin/google-chrome"

    # 如果都没找到，抛出明确错误
    raise FileNotFoundError("未能检测到 Google Chrome 浏览器，请确保已安装！")