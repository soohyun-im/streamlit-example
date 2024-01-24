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
        model="gpt-4-1106-preview",
        messages=[
            {"role": "system", 
             "content": """
             You are a skilled AI specializing in distilling key information into key words.
Based on the following, identify the main points discussed or raised and list your words. 
the words must contain the most important idea, discovery, or topic that is crucial to the nature of the discussion.
Your goal is to provide a list of words that are key to your conversation. don't include unimportant, common words in your list
            """},
            
            {"role": "user", "content": user_input},
            
            {"role": "assistant", 
             "content": """
              Avoid using verbs or adjectives in the extracted keywords, focus on nouns and key concepts.
             Importance refers to the degree to which the content is the most essential part of the content. 
             Among these, unique and uncommon words are judged to be more important. For example, if you extract the four keywords 'Apple', 'mixed reality', 'headset', and 'Vision Pro' from the sentence 'Apple has launched the mixed reality headset 'Vision Pro'' and list them in order, the most important one is It must be 'Vision Pro', 'Mixed Reality', 'Apple', or 'Headset'.
the words list should be separated by ',' and Sort them in order of importance.
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
    st.title("뉴스 속 주요 키워드 추출 🔍")

    # 사용자로부터 뉴스 카테고리 번호 입력
    category = st.text_input(""" 
                             가져올 뉴스 카테고리 번호를 입력하세요
    100(정치) | 101(경제) | 102(사회) | 
    103(생활/문화) | 104(세계) | 105(IT/과학) 
                             """)

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
                    user_request = f"""Extract important keywords from the news: {contents[0]['content']}
                Avoid using verbs or adjectives in the extracted keywords, focus on nouns and key concepts. """
                    
                    extracted_keywords = ask_to_gpt35_turbo(user_request)

                    # Display data
                    unique_keywords = list(set(extracted_keywords.split(',')))

                    st.markdown(f"<h4>추출 키워드</h4>", unsafe_allow_html=True)
                    # Display extracted keywords with dynamic text color
                    keyword_bg_color = "#f0f8ff" if background_color != '#1E1E1E' else ''
                    st.markdown(
                        f"<div style='color: {text_color}; background-color: {keyword_bg_color}; padding: 10px;'>{' | '.join(unique_keywords)}</div>",
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
