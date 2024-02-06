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
                    
                    # 다크 모드와 라이트 모드에 따른 배경색과 글자색 설정
                    bg_color = "#343a40"  # 다크 모드 배경색
                    text_color = "#ffffff"  # 다크 모드 글자색
                    
                    # GPT 응답에 배경색과 글자색을 적용하여 식별이 쉽게 함
                    st.markdown(
                        f"<div style='background-color: {bg_color}; color: {text_color}; padding: 10px; border-radius: 10px; margin-top: 10px;'>"
                        f"<b>추출된 키워드:</b> {keywords}</div>", 
                        unsafe_allow_html=True
                    )
                else:
                    st.error("기사 내용을 가져올 수 없습니다.")
        else:
            st.error(f"{formatted_target_date}에 해당하는 뉴스가 없습니다.")

if __name__ == "__main__":
    main()
