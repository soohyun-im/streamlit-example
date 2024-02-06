import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import openai
from datetime import datetime
from retrying import retry

# Streamlit 페이지 설정
st.set_page_config(
    page_title="뉴스 속 주요 키워드 추출",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# OpenAI API 키 설정
openai.api_key = os.environ.get("OPENAI_API_KEY")

# 특정 날짜에 대한 네이버 섹션 105의 헤드라인 뉴스 가져오기
def get_headline_news_by_date(target_date):
    url = f'https://news.naver.com/main/list.nhn?mode=LSD&mid=sec&sid1=105&date={target_date}'
    response = requests.get(url)
    if response.status_code != 200:
        st.error(f"뉴스를 가져오는 데 문제가 발생했습니다. 응답 코드: {response.status_code}")
        return [], []

    soup = BeautifulSoup(response.text, 'html.parser')
    headline_news_list = soup.select('.list_body.newsflash_body .type06_headline li')

    headlines = []
    urls = []

    for news in headline_news_list:
        headline = news.select_one('dt:not(.photo) a').text.strip()
        link = news.select_one('dt:not(.photo) a')['href']
        
        headlines.append(headline)
        urls.append(link)

    return headlines, urls

# URL에서 기사 내용 가져오기
def get_contents_from_urls(news_urls):
    contents = []

    for url in news_urls:
        news = requests.get(url)
        news_html = BeautifulSoup(news.text, "html.parser")

        paragraphs = news_html.find_all(id="dic_area")
        content = ' '.join(paragraph.get_text(strip=True) for paragraph in paragraphs)

        contents.append(content)

    return contents

# GPT를 사용하여 텍스트에서 주요 키워드 추출
def ask_to_gpt_for_keywords(text):
    response = openai.chat.completions.create(
        model="gpt-4-1106-preview",
       messages=[
            {"role": "system", 
             "content": """
            You are an IT encyclopedia that knows information about all companies, technologies, and events in the world.
               Please look at the IT news we deliver and look for the company name, technology name, and event name in the article.
               Technology is a concept that encompasses both tangible and intangible technologies, services, and products, and is the core content that introduced in the news.
               Please create a word list for the input sentence according to the constraints and output format below.
               The purpose is to quickly convey to users a list of companies, technologies, and events that appear in IT articles through a word list.
               Please write the company name, event name, technology name, etc. on one line so that the words can be easily distinguished.
            """},
            
            {"role": "user", "content": text},
            
            {"role": "assistant", 
             "content": """
              #Constraints
               -Words are divided into minimal noun units and extracted.
               -Except in cases where there are no words to be written together, if it is written in Korean, the English name must be written side by side, and if it is an English name, the Korean name must be written side by side.
               - Please include the official site address link for each extracted word.
               -During extraction, each word is not duplicated.
               -Words other than company name, technology name, and event name are not extracted.
               -If the official site cannot be confirmed, the site address will not be extracted.
               -If the word matching the condition does not exist, 'none' is displayed.
               -Code blocks are not included.
              
              
               #output format
               -Company name: Word (English name) (official site link), Word (English name) (official site link)

               -Event name: Word (English name) (official site link), Word (English name) (official site link)

               -Technology name: Word (English name) (official site link), Word (English name) (official site link)

               #Output example
                 -Company name: CJ Onstyle (https://display.cjonstyle.com/), Samsung Electronics (www.samsung.com)
                 -Event name: Galaxy Unpacked 2024
                 -Technology name: Galaxy S24 series, Generative AI
            

               #Derivative process
               1. Check whether the requested content is in the given article.
               2. If there is content in the information, it is output in a designated output format.
               3. If there is no content in the information, it is output as “none.”
               4. Words or descriptions other than the output format are not included.
             """}
        ]
    )
    return response.choices[0].message.content

@retry(stop_max_attempt_number=3, wait_fixed=1000)
def make_request(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response

def main():
    st.title("뉴스 속 주요 키워드 추출 🔍")
    st.subheader("※ 뉴스 가져오기 실행 시 GPT비용이 발생하므로 신중하게 클릭해주세요")
    target_date = st.date_input("뉴스 날짜 선택", datetime.today())
    formatted_target_date = target_date.strftime('%Y%m%d')  # 날짜 형식 변환

    if st.button("뉴스 가져오기"):
        headlines, urls = get_headline_news_by_date(formatted_target_date)
    
        if headlines:
            st.subheader(f"{formatted_target_date}의 헤드라인 뉴스")
            for i, (headline, url) in enumerate(zip(headlines, urls), 1):
                st.write(f"{i}. {headline} - [기사 보기]({url})")
                
                contents = get_contents_from_urls([url])
                if contents:
                    # GPT로부터 키워드 추출 요청
                    keywords = ask_to_gpt_for_keywords(contents[0])
                    
                    # GPT 응답에 배경색을 깔아서 식별이 쉽게 함
                    st.markdown(
                        f"<div style='background-color: #e8eaf6; padding: 10px; border-radius: 10px; margin-top: 10px;'>"
                        f"<b>추출된 키워드:</b> {keywords}</div>", 
                        unsafe_allow_html=True
                    )
                else:
                    st.error("기사 내용을 가져올 수 없습니다.")
        else:
            st.error(f"{formatted_target_date}에 해당하는 뉴스가 없습니다.")

if __name__ == "__main__":
    main()
