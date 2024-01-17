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
            You are an experienced AI expert extracting company and organization names and technology names mentioned in news articles.
            Please extract the names of companies, organizations, and technologies that appear in the delivered content.
    
            Next to the extracted word, write the word's classification criteria (e.g. company name, organization name, technology name).

            Your goal is to provide a list of keywords for companies, organizations, and technologies mentioned in news articles.

            Words other than company names, organization names, or technology names must never be included in the list.
            If there is no word matching the condition, extract it as none.

            After extracting words, you can list the words by dividing them into company and organization names and technology names. After that, please write in the following format:
                'Company/Organization Names:
                Ministry of Science and ICT (Organization), Korean Association of University Professors (Organization), Korea University Professors' Union (Organization), Korea University (University), Korea Society for Subjectivity Research (Organization), Office of the President (Organization)

                Technology Names:
                Energy Mix (Technology), Schema (Technology)'
            The words you extracted should be separated by ',' 
            When listing, always list 'Company/Organization Names' and corresponding words first, followed by 'Technology Names' and corresponding words.
            """},
            
            {"role": "user", "content": user_input},
            
            {"role": "assistant", 
             "content": """
              Words other than company names, organization names, or technology names must never be included in the list. 
              the words you extracted should be separated by ',' 
            When listing, always list 'Company/Organization Names' and corresponding words first, followed by 'Technology Names' and corresponding words.
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
    st.title("IT 뉴스 속 기업명/기술명 키워드 추출 🔍")
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
                    user_request = f"""Extract company,organization names and technology names mentioned in news articles: {contents[0]['content']}
                
                """
                    extracted_keywords = ask_to_gpt35_turbo(user_request)

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
