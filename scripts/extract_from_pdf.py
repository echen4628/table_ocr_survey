from pypdf import PdfReader, PdfWriter
from typing import List, Union

def extract_pages_from_pdf(file_name: str, pages: Union[int, List[int]]):
    '''
    pages: an int or list of int's for the page numbers to extract, 1-indexed
    '''
    reader = PdfReader(file_name)
    if isinstance(pages, int):
        pages = [pages]
    for page in pages:
        
        current_pdf_page = reader.pages[page-1]

        with open(f"{file_name.removesuffix(".pdf")}-pg{page}.pdf", "wb") as output:
            writer = PdfWriter()
            writer.add_page(current_pdf_page)
            writer.write(output)
            writer.close()

if __name__ == '__main__':
    extract_pages_from_pdf("insurance_filing.pdf", pages=[3,5, 22, 36, 38])writer.close()