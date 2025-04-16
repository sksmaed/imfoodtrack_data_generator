import time
import csv
import os
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

def scrape_family_foods(keyword):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # 無頭模式
    service = Service("chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)
    
    all_products = []
    
    try:
        url = "https://foodsafety.family.com.tw/Web_FFD_2022/"
        driver.get(url)
        time.sleep(2)
        
        # 搜尋關鍵字
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='text' and @placeholder='輸入商品名稱關鍵字']"))
        )
        search_box.send_keys(keyword)

        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn--confirm"))
        )
        search_button.click()
        time.sleep(5)
        print(f"Searching for: {keyword}")

        while True:  # 確保可以翻頁
            # 取得所有分類項目
            categories = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//ul[contains(@class, 'swiper-wrapper')]/li"))
            )

            for cat_index in range(len(categories)):
                categories = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//ul[contains(@class, 'swiper-wrapper')]/li"))
                )
                category_name = categories[cat_index].find_element(By.TAG_NAME, "span").text  # 取得分類名稱
                print(f"進入分類: {category_name}")

                categories[cat_index].click()  # 點擊分類
                time.sleep(3)  # 等待載入

                try:
                    items = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//li[contains(@class, 'results__item')]/a"))
                    )
                except:
                    print(f"No results found for: {keyword}")
                    return None

                for index in range(len(items)):  
                    # 重新獲取最新的搜尋結果
                    items = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//li[contains(@class, 'results__item')]/a"))
                    )

                    # 取得商品名稱
                    product_name = items[index].find_element(By.CLASS_NAME, "results__item-name").text
                    print(f"商品名稱: {product_name}")

                    # 詢問使用者是否要爬取
                    choice = input("是否要抓取該商品？(y/n): ").strip().lower()
                    if choice != "y":
                        print(f"跳過: {product_name}")
                        continue

                    print(f"開始抓取: {product_name}")
                    items[index].click()
                    time.sleep(3)  

                    # 取得營養素資訊
                    nutrients = {}
                    try:
                        nutrition_buttons = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CLASS_NAME, "resume__all"))
                        )
                        nutrition_buttons.click()
                        time.sleep(2)
                    except:
                        print(f"{product_name} 無法展開營養資訊")

                    nutrient_elements = driver.find_elements(By.CSS_SELECTOR, ".resume__info p")
                    for elem in nutrient_elements:
                        parts = elem.text.split()
                        if len(parts) == 3:
                            nutrients[parts[0]] = f"{parts[1]} {parts[2]}"

                    # **下載圖片**
                    try:
                        food_img = driver.find_element(By.XPATH, "//div[contains(@class, 'img-wrap')]/img").get_attribute("src")
                        img_data = requests.get(food_img).content
                        with open(f"./familyFood_img/{product_name}.jpg", "wb") as f:
                            f.write(img_data)
                    except:
                        print(f"{product_name} 無法下載圖片")

                    print(f"{product_name} 爬取完成")
                    print("=====================================")

                    # 儲存商品資訊
                    product_data = {"商品名稱": product_name, **nutrients}
                    all_products.append(product_data)

                    # 返回上一頁
                    driver.back()
                    time.sleep(3)

            # 檢查是否有下一頁按鈕
            try:
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '下一頁')]"))
                )
                next_button.click()
                time.sleep(5)
            except:
                print("沒有更多頁面了")
                break
        
        return all_products
    
    finally:
        driver.quit()

if __name__ == "__main__":
    keywords = input("請輸入欲查詢的食品關鍵字（以逗號分隔）：")
    keywords = keywords.split(",")

    all_results = []

    for keyword in keywords:
        data = scrape_family_foods(keyword)
        if data:
            all_results.extend(data) 
    
    if all_results:
        file_exists = os.path.exists("family_foods.csv")  # **檢查檔案是否已存在**

        with open("family_foods.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_results[0].keys())  # **假設欄位皆一致**
            
            if not file_exists:
                writer.writeheader()  # **僅在檔案不存在時寫入標題列**
            
            writer.writerows(all_results)  # **追加寫入資料**
    
        print("📄 資料已成功追加至 family_foods.csv ✅")
