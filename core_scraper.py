from playwright.sync_api import sync_playwright
from browser_locator import get_system_chrome_path
import time
import os
import httpx


def test_google_lens_upload(image_absolute_path):
    # 确保保存数据的 chrome_data 文件夹依然在代码所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(current_dir, "chrome_data")

    # 提取文件名和所在目录 (例如: D:/images/cat.jpg -> 所在目录 D:/images, 文件名 cat.jpg)
    target_dir = os.path.dirname(image_absolute_path)
    image_filename = os.path.basename(image_absolute_path)
    base_name = os.path.splitext(image_filename)[0]

    # 在原图片所在目录下，新建下载文件夹
    save_folder = os.path.join(target_dir, f"Results_{base_name}")
    os.makedirs(save_folder, exist_ok=True)

    print("🚀 启动自动化引擎...")

    chrome_path = get_system_chrome_path()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            executable_path=chrome_path,  # <--- 替换为动态路径
            viewport={'width': 1280, 'height': 800},
            locale='en-US',
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = context.pages[0]

        try:
            # --- 识图业务逻辑 ---
            print("🌐 访问谷歌识图...")
            page.goto("https://images.google.com/")
            page.wait_for_load_state("domcontentloaded")

            print("📸 点击相机图标...")
            camera_btn = page.locator(
                '.nDcEnd, [aria-label*="image" i], [aria-label*="图"], [data-tooltip*="image" i], [data-tooltip*="图"]').first
            camera_btn.wait_for(state="visible", timeout=10000)
            camera_btn.click()

            print("📤 注入本地图片...")
            upload_input = page.locator("input[type='file']")
            upload_input.wait_for(state="attached", timeout=5000)
            # 直接使用 GUI 传过来的绝对路径！
            upload_input.set_input_files(image_absolute_path)

            page.wait_for_url("**/search**", timeout=0)
            time.sleep(3)

            # --- 滚动提取逻辑 ---
            print("⬇️ 开始模拟滚轮提取链接...")
            image_urls = set()

            # 新增：记录最后一次成功抓到“新图片”的时间
            last_added_time = time.time()
            timeout_seconds = 5.0  # 设定 5 秒无新图就结束

            for scroll_count in range(20):  # 滚动次数
                page.mouse.wheel(0, 2000)
                time.sleep(1.5)  # 依然保留 1.5 秒给谷歌加载图片的时间

                extracted_urls = page.evaluate('''() => {
                                let imgs = Array.from(document.querySelectorAll('img'));
                                return imgs
                                    .map(img => img.src || img.dataset.src)
                                    .filter(src => src && src.startsWith('http') && !src.includes('favicon'));
                            }''')

                # 提取前，先记住现在的图片总数
                old_count = len(image_urls)

                for url in extracted_urls:
                    image_urls.add(url)
                    if len(image_urls) >= 100:
                        break

                # 提取后，看看现在的图片总数
                new_count = len(image_urls)

                # --- 核心：5秒超时侦测逻辑 ---
                if new_count > old_count:
                    # 只要数量涨了，说明还在源源不断出新图，刷新“最后抓取时间”
                    last_added_time = time.time()
                    print(f"🔄 当前已抓取: {new_count}/100")
                else:
                    # 数量没涨，计算一下距离上次涨数量过去多久了
                    elapsed_time = time.time() - last_added_time
                    if elapsed_time > timeout_seconds:
                        print("⏳ 连续 5 秒未发现新图片，判定网页已到底，提前结束当前任务！")
                        break  # 直接打破循环，开始下载

                if len(image_urls) >= 100:
                    break

            urls_list = list(image_urls)[:100]

        except Exception as e:
            print(f"❌ 抓取过程中出错：{e}")
            urls_list = []
        finally:
            context.close()

    # --- 下载逻辑 ---
    if urls_list:
        print(f"📥 开始下载图片至: {save_folder}")
        with httpx.Client(timeout=10.0) as client:
            success_count = 0
            for index, url in enumerate(urls_list):
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    response = client.get(url, headers=headers)
                    if response.status_code == 200:
                        file_path = os.path.join(save_folder, f"{index + 1}.jpg")
                        with open(file_path, "wb") as f:
                            f.write(response.content)
                        success_count += 1
                except Exception:
                    continue
        print(f"🎉 成功下载 {success_count} 张图片！")