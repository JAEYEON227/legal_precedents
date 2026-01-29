###############
# KCS Customs Legal Precedent Crawler
#
# This program automatically visits the Korean Customs Service website
# and collects legal precedent data to keep our chatbot's knowledge up-to-date.
#
# How it works:
# 1. Opens the customs portal website using an automated browser
# 2. Navigates to the legal precedents section (법령판례등 > 판례결정례 > 소송)
# 3. Goes through multiple pages collecting case information
# 4. For each case, clicks the title to view details and extracts:
#    - Court name, case number, judgment date, case summary, etc.
# 5. Removes duplicate entries and saves all data as JSON
#
# The program runs without showing a browser window (headless mode)
# and is designed to work both locally and on cloud servers.
###############

###############
# Environments
###############

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
from datetime import datetime
import pandas as pd
from io import StringIO
import json
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent

class CustomsCrawler:
    def __init__(self):
        """크롤러 초기화"""
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Selenium WebDriver 설정 (Streamlit Cloud 호환)"""
        options = webdriver.ChromeOptions()
        
        # 기존 옵션 유지
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Streamlit Cloud에서 필요한 추가 옵션들
        options.add_argument('--headless')  # GUI 없이 실행 (필수)
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        
        # ChromeDriver 설정 (Streamlit Cloud 호환)
        try:
            # 시스템에 설치된 chromium-driver 사용 시도
            service = Service('/usr/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=options)
        except:
            try:
                # webdriver-manager를 사용하지 않고 직접 시도
                self.driver = webdriver.Chrome(options=options)
            except:
                try:
                    # 마지막 시도: webdriver-manager 사용 (로컬 환경용)
                    from webdriver_manager.chrome import ChromeDriverManager
                    self.driver = webdriver.Chrome(
                        service=Service(ChromeDriverManager().install()), 
                        options=options
                    )
                except Exception as e:
                    print(f"Chrome 드라이버 설정 실패: {e}")
                    raise e

        # 기존 설정 유지 (헤드리스 모드에서는 maximize_window 제거)
        # self.driver.maximize_window()  # 헤드리스 모드에서는 불필요
        self.wait = WebDriverWait(self.driver, 10)
        
    def navigate_to_lawsuit_page(self):
        """관세법령정보포털 > 법원/판례 등 > 판례/결정례 > 소송 페이지로 이동"""
        # 1. 사이트 접속
        self.driver.get("https://unipass.customs.go.kr/clip/index.do")
        time.sleep(2)
        
        # 2. "법령판례등" 클릭
        world_hs_menu = self.wait.until(
            EC.element_to_be_clickable((By.ID, "TOPMENU_LNK_M_ULS0100000000"))
        )
        world_hs_menu.click()
        print("법령판례 등 메뉴 클릭 완료")
        time.sleep(2)

        # 3. "판례결정례" 클릭
        domestic_cases_menu = self.wait.until(
            EC.element_to_be_clickable((By.ID, "LEFTMENU_LNK_M_ULS0105000000"))
        )
        domestic_cases_menu.click()
        print("판례결정례 메뉴 클릭 완료")
        time.sleep(2)

        # 4. "소송" 클릭
        committee_decisions_menu = self.wait.until(
            EC.element_to_be_clickable((By.ID, "LEFTMENU_LNK_UI-ULS-0105-003Q"))
        )
        committee_decisions_menu.click()
        print("소송 메뉴 클릭 완료")
        time.sleep(2)

        # 5. "n개 보기" 설정
        dropdown = self.driver.find_element(By.NAME, 'pagePerRecord')
        select = Select(dropdown)
        select.select_by_value('50')
        self.driver.implicitly_wait(2)
        print("50개 보기 설정 완료")
        
    def get_case_links(self):
        """현재 페이지의 모든 사건번호별 세부정보 링크 수집"""
        # 스크롤 내리기 (JavaScript로 페이지 맨 아래까지)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # 고정된 class를 가진 모든 <td> 태그 찾기
        td_elements = self.driver.find_elements(By.XPATH, '//td[@class="ellipsis textLeft hlzone1"]')
        links = []

        # 각 사건번호별 세부정보 링크(href) 찾기
        for td in td_elements:
            title = td.get_attribute("title")
            a_tag = td.find_element(By.TAG_NAME, "a")
            href = a_tag.get_attribute("href")
            links.append({"title": title, "href": href})
            print(f"Found case: {title}")

        print(f"Found {len(links)} links to process.")
        return links
        
    def scrape_case_detail(self, case_title):
        """개별 사건의 상세 정보 스크래핑"""
        try:
            # XPath로 특정 class와 title이 매칭되는 <td> 내의 <a> 찾기
            popup_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f'//td[@class="ellipsis textLeft hlzone1" and @title="{case_title}"]/a'))
            )

            # 링크 클릭
            popup_link.click()
            print(f"팝업 링크 클릭 완료: {case_title}")
            time.sleep(2)
            
            # 테이블 데이터 스크래핑
            tbody = self.driver.find_element(By.XPATH, "//tbody")
            rows = tbody.find_elements(By.TAG_NAME, "tr")

            # 데이터 수집
            page_data = {}
            for row in rows:
                headers = row.find_elements(By.TAG_NAME, "th")
                cells = row.find_elements(By.TAG_NAME, "td")
                
                # Map headers to cells
                if headers and cells:
                    for i in range(len(headers)):
                        key = headers[i].text.strip()
                        value = cells[i].text.strip() if i < len(cells) else None
                        page_data[key] = value
                elif headers:
                    for header in headers:
                        page_data[header.text.strip()] = None
                elif cells:
                    for cell in cells:
                        page_data[f"Extra_Cell_{len(page_data) + 1}"] = cell.text.strip()

            # 목록으로 돌아가기
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            list_page = self.driver.find_element(By.ID, "histBack")
            list_page.click()
            print("목록 버튼 클릭 완료")
            time.sleep(1)
            
            return page_data
            
        except Exception as e:
            print(f"Error processing case {case_title}: {e}")
            return None
            
    def go_to_next_page(self, page_num):
        """다음 페이지로 이동"""
        try:
            # 스크롤 내리기
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            next_page = self.driver.find_element(By.XPATH, f"//li/a[@href='#{page_num}']")
            next_page.click()
            print(f"페이지 {page_num} 이동 완료")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"Error moving to page {page_num}: {e}")
            return False
            
    def crawl_data(self, max_pages=8, progress_callback=None):
        """
        메인 크롤링 함수

        Args:
            max_pages (int): 크롤링할 최대 페이지 수
            progress_callback (function): 진행률 콜백 함수

        Returns:
            list: 크롤링된 데이터 리스트
        """
        data = []
        
        try:
            # WebDriver 설정
            self.setup_driver()
            print("WebDriver 설정 완료")
            
            # 소송 페이지로 이동
            self.navigate_to_lawsuit_page()
            print("소송 페이지 이동 완료")
            
            # 각 페이지별 크롤링
            for k in range(2, max_pages + 2):  # 2부터 시작 (원본 코드 유지)
                current_page = k - 1
                print(f"\n=== 페이지 {current_page}/{max_pages} 처리 중 ===")
                
                # 현재 페이지의 사건 링크들 수집
                links = self.get_case_links()
                
                # 페이지 시작 시 진행률 업데이트
                if progress_callback:
                    progress_callback(current_page, max_pages, collected_count=len(data))
                
                # 각 사건별 상세 정보 스크래핑
                for j, link in enumerate(links):
                    case_title = link['title']
                    print(f"Processing case {j + 1}/{len(links)}: {case_title}")
                    
                    # 각 사건 처리 시 진행률 업데이트
                    if progress_callback:
                        progress_callback(current_page, max_pages, j + 1, len(links), len(data))
                    
                    case_data = self.scrape_case_detail(case_title)
                    if case_data:
                        data.append(case_data)
                
                # 마지막 페이지가 아니면 다음 페이지로 이동
                if current_page < max_pages:
                    success = self.go_to_next_page(k)
                    if not success:
                        print(f"페이지 {k} 이동 실패. 크롤링을 중단합니다.")
                        break
            
            # 최종 진행률 업데이트
            if progress_callback:
                progress_callback(max_pages, max_pages, collected_count=len(data))
                
        except Exception as e:
            print(f"크롤링 중 오류 발생: {e}")
            raise e
            
        finally:
            # WebDriver 종료
            if self.driver:
                self.driver.quit()
                print("WebDriver 종료 완료")
        
        # 중복 제거 및 데이터 정리
        if data:
            df_temp = pd.DataFrame(data)
            df_unique = df_temp.drop_duplicates()
            
            print(f"크롤링 전체 데이터: {len(df_temp)}건")
            print(f"중복 제거 후 데이터: {len(df_unique)}건")
            
            # 중복 제거된 데이터를 딕셔너리 형태로 변환
            unique_data = df_unique.to_dict(orient="records")
            return unique_data
        else:
            print("수집된 데이터가 없습니다.")
            return []

# 독립 실행 시 테스트 코드
if __name__ == "__main__":
    # 테스트 실행
    crawler = CustomsCrawler()

    print("크롤링 시작...")
    data = crawler.crawl_data(max_pages=2)  # 테스트용으로 3페이지만
    
    if data:
        print(f"크롤링 완료! 총 {len(data)}건의 데이터를 수집했습니다.")
        
        # 데이터 저장 (프로젝트 루트에 저장)
        output_file = PROJECT_ROOT / "data_kcs_temp.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"데이터가 {output_file}에 저장되었습니다.")
    else:
        print("수집된 데이터가 없습니다.")