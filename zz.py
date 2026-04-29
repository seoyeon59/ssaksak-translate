import PyPDF2

def extract_specific_page(input_pdf, output_pdf, page_number):
    # PDF 파일 열기
    with open(input_pdf, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        writer = PyPDF2.PdfWriter()

        # 페이지 번호 확인 (30페이지는 인덱스 29)
        # reader.pages의 길이를 체크하여 에러 방지
        if len(reader.pages) >= page_number:
            page = reader.pages[page_number - 1]
            writer.add_page(page)

            # 결과 저장
            with open(output_pdf, "wb") as output_file:
                writer.write(output_file)
            print(f"성공! {page_number}페이지를 '{output_pdf}'로 저장했습니다.")
        else:
            print(f"오류: 파일이 전체 {len(reader.pages)}페이지뿐이라 {page_number}페이지를 찾을 수 없습니다.")

# 실행 예시
extract_specific_page("haeun.pdf", "haeun.pdf", 30)