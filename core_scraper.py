from playwright.sync_api import sync_playwright
from browser_locator import get_system_chrome_path
import time
import os
import httpx
import sys

def test_google_lens_upload(image_absolute_path):
    base_dir = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    user_data_dir = os.path.join(base_dir, "GoogleLensAuto_Data", "chrome_data")
    os.makedirs(user_data_dir, exist_ok=True)

    target_dir = os.path.dirname(image_absolute_path)
    image_filename = os.path.basename(image_absolute_path)
    base_name = os.path.splitext(image_filename)[0]

    save_folder = os.path.join(target_dir, f"Results_{base_name}")
    os.makedirs(save_folder, exist_ok=True)

    print("🚀 启动自动化引擎...")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            executable_path=get_system_chrome_path(),
            viewport={'width': 1280, 'height': 800},
            locale='en-US',
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = context.pages[0]

        try:
            print("🌐 访问谷歌识图...")
            page.goto("https://images.google.com/")
            page.wait_for_load_state("domcontentloaded")

            print("📸 点击相机图标...")
            camera_btn = page.locator('.nDcEnd, [aria-label*="image" i], [aria-label*="图"]').first
            camera_btn.wait_for(state="visible", timeout=10000)
            camera_btn.click()

            print("📤 注入本地图片...")
            page.locator("input[type='file']").set_input_files(image_absolute_path)
            page.wait_for_url("**/search**", timeout=0)
            time.sleep(3)

            print("⬇️ 开始模拟滚轮并使用【JS插件正则爆破法】提取高清链接...")
            image_urls = set()

            last_added_time = time.time()
            timeout_seconds = 5.0  

            for scroll_count in range(20):
                page.mouse.wheel(0, 2000)
                time.sleep(1.5)

                # ==========================================
                # 核心重构：带“最高清过滤”和“同源去重”的超级提取器
                # ==========================================
                extracted_urls = page.evaluate(r'''async () => {
                    const uniqueImages = new Map();

                    // --- 过滤层 1：DOM 渲染层拦截 ---
                    function getBestUrlFromImg(img) {
                        // 严格判断：已经在网页上渲染的图片，哪怕是 99x99 也直接干掉
                        if (img.naturalWidth > 0 && (img.naturalWidth < 100 || img.naturalHeight < 100)) {
                            return null;
                        }

                        let bestUrl = (img.src && !img.src.startsWith('data:')) ? img.src : null;
                        let maxWidth = img.naturalWidth || 0;

                        if (img.srcset) {
                            img.srcset.split(',').forEach(source => {
                                const parts = source.trim().split(/\s+/);
                                const url = parts[0];
                                if (!url || url.startsWith('data:')) return;

                                let width = 0;
                                if (parts.length > 1) {
                                    const match = parts[1].match(/^(\d+)(w|x)$/);
                                    if (match) {
                                        width = parseInt(match[1], 10);
                                        if (match[2] === 'x') width *= 1000;
                                    }
                                }
                                if (width > maxWidth) {
                                    maxWidth = width;
                                    bestUrl = url;
                                }
                            });
                        }
                        return bestUrl;
                    }

                    // --- 过滤层 2：URL 基因特征拦截 ---
                    function addUrlToSet(url) {
                        if (!url || !url.startsWith('http') || url.includes('favicon')) return;

                        const sizeRegex = /[-_](\d+)x(\d+)\.([a-zA-Z0-9]+)$/i;
                        const match = url.match(sizeRegex);
                        
                        let baseUrl = url;
                        let area = Infinity;
                        let isOriginal = true;

                        if (match) {
                            const w = parseInt(match[1], 10);
                            const h = parseInt(match[2], 10);
                            
                            // 严格判断：通过正则发现它本身就是一个小于 100x100 的缩略图，直接抛弃
                            if (w < 100 || h < 100) return;

                            area = w * h;
                            baseUrl = url.replace(sizeRegex, '.$3');
                            isOriginal = false;
                        }

                        // 优胜劣汰
                        if (!uniqueImages.has(baseUrl)) {
                            uniqueImages.set(baseUrl, { url, area, isOriginal });
                        } else {
                            const existing = uniqueImages.get(baseUrl);
                            if (isOriginal) {
                                uniqueImages.set(baseUrl, { url, area, isOriginal });
                            } else if (!existing.isOriginal && area > existing.area) {
                                uniqueImages.set(baseUrl, { url, area, isOriginal });
                            }
                        }
                    }

                    // --- 第一阶段：全方位静态提取 ---
                    document.querySelectorAll('img').forEach(img => {
                        const bestUrl = getBestUrlFromImg(img);
                        if (bestUrl) addUrlToSet(bestUrl);
                    });

                    const bgRegex = /url\(\s*?['"]?\s*?(\S+?)\s*?['"]?\s*?\)/i;
                    document.querySelectorAll('*').forEach(el => {
                        const bg = window.getComputedStyle(el).getPropertyValue('background-image');
                        if (bg && bg !== 'none') {
                            const match = bgRegex.exec(bg);
                            if (match && match[1]) {
                                addUrlToSet(match[1].replace(/^['"]|['"]$/g, ''));
                            }
                        }
                    });

                    const globalRegex = /https?:\/\/[^"\s]+?\.(?:jpg|jpeg|png|gif|webp|bmp|svg|tiff|avif|ico)/gi;
                    const matches = document.body.innerHTML.match(globalRegex);
                    if (matches) {
                        matches.forEach(url => addUrlToSet(url));
                    }

                    // 汇总第一阶段幸存的 URL 候选者
                    const candidateUrls = Array.from(uniqueImages.values()).map(info => info.url);

                    // --- 过滤层 3：内存静默加载与真实分辨率终极校验（核心） ---
                    // 对于正则爆破出来的无尺寸信息 URL，我们在浏览器内存中试加载它，获取真实分辨率
                    const checkImageSize = (url) => {
                        return new Promise((resolve) => {
                            const img = new Image();
                            img.onload = () => {
                                // 真正读取到了物理像素，只有 >= 100 才会放行
                                if (img.naturalWidth >= 100 && img.naturalHeight >= 100) {
                                    resolve(url);
                                } else {
                                    resolve(null); // 小于 100x100，淘汰
                                }
                            };
                            img.onerror = () => {
                                resolve(null);
                            };
                            img.src = url;
                        });
                    };

                    const finalResults = await Promise.all(candidateUrls.map(checkImageSize));
                    
                    return finalResults.filter(url => url !== null);
                }''')

                old_count = len(image_urls)

                for url in extracted_urls:
                    image_urls.add(url)
                    if len(image_urls) >= 100:
                        break

                new_count = len(image_urls)

                # 超时侦测逻辑
                if new_count > old_count:
                    last_added_time = time.time()
                    print(f"🔄 当前已抓取: {new_count}/100")
                else:
                    elapsed_time = time.time() - last_added_time
                    if elapsed_time > timeout_seconds:
                        print("⏳ 连续 5 秒未发现新图片，判定网页已到底，提前结束提取！")
                        break

                if len(image_urls) >= 100:
                    break

            urls_list = list(image_urls)[:100]

        except Exception as e:
            print(f"❌ 抓取过程中出错：{e}")
            urls_list = []
        finally:
            context.close()

     # --- 下载与大小过滤逻辑 ---
    if urls_list:
        print(f"📥 开始下载并过滤图片至: {save_folder}")
        with httpx.Client(timeout=10.0) as client:
            success_count = 0
            skipped_count = 0
            
            for index, url in enumerate(urls_list):
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    response = client.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        # 核心逻辑：获取图片在内存中的字节大小
                        file_size_bytes = len(response.content)
                        file_size_kb = file_size_bytes / 1024
                        
                        # 严格过滤：只有大于等于 90KB 的图片才予以保存
                        if file_size_kb >= 90:
                            file_path = os.path.join(save_folder, f"{success_count + 1}.jpg")
                            with open(file_path, "wb") as f:
                                f.write(response.content)
                            success_count += 1
                            print(f"✅ [保留] 大小: {file_size_kb:.2f} KB | 链接: {url[:60]}...")
                        else:
                            skipped_count += 1
                            print(f"🗑️ [丢弃] 大小不足: {file_size_kb:.2f} KB < 90 KB | 链接: {url[:60]}...")
                            
                except Exception as e:
                    print(f"❌ [下载失败] {url[:60]}... 错误: {e}")
                    continue
                    
            print(f"🎉 任务结束！成功保存 {success_count} 张高清大图，因小于 90KB 剔除了 {skipped_count} 张低质图片。")