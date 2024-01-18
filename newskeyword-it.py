import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from retrying import retry
import os
import openai

st.set_page_config(
    page_title="뉴스 속 주요 키워드 추출",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Setting the API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

def get_main_news_data(category):
    url = f'https://news.naver.com/main/main.nhn?mode=LSD&mid=shm&sid1={category}'
    response = requests.get(url)

    if response.status_code != 200:
        st.error(f"뉴스를 가져오는 데 문제가 발생했습니다. 응답 코드: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    data_list = []

    # Find URLs and headlines with class sh_text
    sh_text_elements = soup.select('.sh_text')
    if sh_text_elements:
        for i, element in enumerate(sh_text_elements, 1):
            link = element.find('a')
            if link and 'href' in link.attrs:
                news_url = link['href']
                headline = link.get_text(strip=True)
                data_list.append({'url': news_url, 'headline': headline})

    return data_list

def get_contents_from_urls(news_data):
    contents_list = []

    for data in news_data:
        url = data['url']
        headline = data['headline']

        # 각 기사 html 가져오기
        news = make_request(url)
        news_html = BeautifulSoup(news.text, "html.parser")

        # 기사 내용 가져오기 (id="dic_area"인 div 태그의 내용 모두 가져오기)
        dic_area = news_html.find(id="dic_area")
        if dic_area:
            # Remove unnecessary tags (script, a, span, etc.)
            for tag in dic_area(['script', 'a', 'span']):
                tag.decompose()

            # Extract text content
            content = dic_area.get_text(strip=True)
            contents_list.append({'headline': headline, 'content': content})
        else:
            st.warning(f"기사 내용을 찾을 수 없습니다. URL: {url}")

    return contents_list

def ask_to_gpt35_turbo(user_input):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", 
             "content": """
            당신은 세상의 모든 기업과 기술 및 행사정보에 대해 알고있는 IT백과사전입니다. 전달된 IT뉴스를 보고 기사에나온 기업명과 기술명 그리고 행사명을 찾아주세요
            기술이란 유 무형의 기술 및 서비스와 제품을 포함하는 개념이며, 뉴스에서 소개하고자하는 중심내용입니다. 
            아래의 제약조건과 출력형식에따라 입력문에 대한 단어목록을 작성해주세요  
            해당 단어목록을 통해 IT기사에 나온 기업과 기술, 행사 목록을 user에게 빠르게 전달하는 것이 목적입니다.
            Please output the keywords in the following format:\n- 기업: [Company Names](english name)\n- 행사: [Event Names](english name)\n- 기술: [Technology Names](english name)
            """},
            
            {"role": "user", "content": user_input},
            
            {"role": "assistant", 
             "content": """
              #제약조건
              -단어는 최소한의 명사단위로 나눠서 추출합니다
              -병기할 단어가 없는 경우를 제외하고 한글로 적혀있는 경우 영문명을 병기하고, 영문명일경우 한글명을 반드시 병기합니다.
              -추출 시 각각 단어를 중복 추출하지않습니다.
              -기업명,기술명 그리고 행사명이 아닌 단어는 출력하지않습니다. 
              -해당하는 단어가 존재하지않는경우 'none'이라고 표시합니다.
              -코드블록은 포함하지않습니다.
              
              
              #출력 형식
              \n- 기업: [Company Names](english name)\n- 행사: [Event Names](english name)\n- 기술: [Technology Names](english name)

              #출력 예시
                -기업 : CJ온스타일(CJ Onstyle), 삼성전자(Samsung Electronics)
                -행사 : 갤럭시 언팩 2024(Galaxy Unpacked 2024)
                -기술 : 갤럭시 S24 시리즈(Galaxy S24 series), 생성형 AI(Generative AI)
            

              #도출과정
              1. 질문에대한 내용이 주어진 기사에있는지 확인한다
              2. 정보안에 내용이 있는경우 정해진 출력형식으로 출력한다.
              3. 정보안에 내용이 없는경우 없음 이라고 출력한다.
              4. 출력형식 이외의 단어나 설명은 포함하지않는다.

            

             """}
        ]
    )

    return response.choices[0].message.content

@retry(stop_max_attempt_number=3, wait_fixed=1000)  # 3번 재시도하며 1초 간격으로
def make_request(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response

def main():
    st.title("IT 뉴스 속 기업/기술/행사 키워드 찾기 🔍")
    category = 105
    if st.button("뉴스 가져오기"):
        # 뉴스 데이터 가져오기
        news_data = get_main_news_data(category)

        if news_data:
            st.subheader("헤드라인 뉴스")
            for i, data in enumerate(news_data, 1):
                # Determine text color based on background color
                background_color = st.session_state.background_color if "background_color" in st.session_state else "#FFFFFF"
                text_color = "#262730" if background_color == "#FFFFFF" else "#FFFFFF"

                # Adjust the style for dark mode
                div_style = f"padding: 5px; {'background-color: #F0F2F6;' if background_color != '#1E1E1E' else ''}"
                st.markdown(
                    f"<div style='color: {text_color}; {div_style}'>{i}.{data['headline']}</div>",
                    unsafe_allow_html=True,
                )
                st.write(f"   URL: {data['url']}")

                # 기사 내용 가져오기
                contents = get_contents_from_urls([data])
                if contents:
                    st.write("뉴스 내용 분석 중...")

                    # GPT-3.5 Turbo 모델에 기사 내용을 입력하여 주요 단어 추출
                    user_request = f"""
                    다음 뉴스를 보고 기업명,기술명,행사명을 찾아 출력형식대로 출력해주세요: 
                    {contents[0]['content']}
                    """
                    extracted_keywords = ask_to_gpt35_turbo(user_request)

                    # Store data in dictionary
                    data['Content'] = contents[0]['content']
                    data['Extracted Keywords'] = extracted_keywords

                    # Display data
                    #unique_keywords = list(set(extracted_keywords.split(',')))

                    st.markdown(f"<h4>추출 키워드</h4>", unsafe_allow_html=True)
                    # Display extracted keywords with dynamic text color
                    keyword_bg_color = "#f0f8ff" if background_color != '#1E1E1E' else ''
                    st.markdown(
                        f"<div style='color: {text_color}; background-color: {keyword_bg_color}; padding: 10px;'>{extracted_keywords}</div>",
                        unsafe_allow_html=True,
                    )
                    
                    st.markdown("<br>", unsafe_allow_html=True)

                    st.markdown(f"<h6>기사 내용 전문 보기</h6>", unsafe_allow_html=True)

                    # Adjust the style for dark mode in detailed content
                    content_style = f"font-size: 14px; color: {text_color}; {'background-color: #FFFFFF;' if background_color != '#1E1E1E' else ''}"
                    st.markdown(
                        f"<p style='{content_style}'>{contents[0]['content']}</p>",
                        unsafe_allow_html=True,
                    )

                else:
                    st.warning("내용을 가져오는 데 문제가 있습니다.")


            # Convert dictionary to DataFrame
            df = pd.DataFrame(news_data)

            # Display the entire DataFrame
            st.subheader("전체 데이터 프레임")
            st.write(df)


if __name__ == "__main__":
    main()
