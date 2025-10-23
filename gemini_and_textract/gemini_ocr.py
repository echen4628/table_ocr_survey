from google import genai
from pydantic import BaseModel
from google.genai import types
from dotenv import load_dotenv
from pydoc import pager
from pdf2image import convert_from_path
from io import BytesIO
import base64
import json


def convert_pdf_to_base64_image(pdf_path):
    images = convert_from_path(pdf_path, first_page=1, last_page=1)
    img_buffer = BytesIO()
    images[0].save(img_buffer, format="PNG")
    return base64.b64encode(img_buffer.getvalue()).decode("utf-8")


class Table(BaseModel):
    table_html: str
    description: str
    ambiguity: list[str]

from enum import Enum
class InputType(Enum):
    IMAGE = "image"
    PDF = "raw_pdf"

def ask_gemini(client, prompt, pdf_path, input_type: InputType):

    if input_type == InputType.IMAGE:
        pdf_image = convert_pdf_to_base64_image(pdf_path)
        image_part = types.Part.from_bytes(
            data=pdf_image, mime_type='image/png'
        )
        contents = [prompt, image_part]
    elif input_type == InputType.PDF:
        pdf_part = types.Part.from_bytes(
            data=open(pdf_path, 'rb').read(), mime_type='application/pdf'
        )
        contents = [prompt, pdf_part]
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=contents, config={
            "response_mime_type": "application/json",
            "response_schema": list[Table],
        },)
    return response



def parse_gemini_response(content: str):
    start = content.find("<table>")
    end = content.find("</table>") + 8
    if start != -1 and end != -1:
        return content[start:end]
    return None


# def convert_html_to_visual_table(html_content, output_path):
#     try:
#         # Parse HTML table using BeautifulSoup
#         soup = BeautifulSoup(html_content, 'html.parser')
#         table = soup.find('table')

#         if not table:
#             print("No table found in HTML content")
#             return False

#         # Extract table data with merged cell support
#         rows = []
#         max_cols = 0

#         for tr in table.find_all('tr'):
#             row = []
#             for td in tr.find_all(['td', 'th']):
#                 text = td.get_text(strip=True)
#                 colspan = int(td.get('colspan', 1))
#                 rowspan = int(td.get('rowspan', 1))

#                 # Add the cell content
#                 row.append(text)

#                 # Add empty cells for colspan
#                 for _ in range(colspan - 1):
#                     row.append('')

#             if row:  # Only add non-empty rows
#                 rows.append(row)
#                 max_cols = max(max_cols, len(row))

#         # Pad rows to have the same number of columns
#         for row in rows:
#             while len(row) < max_cols:
#                 row.append('')

#         if not rows:
#             print("No data found in table")
#             return False

#         # Create matplotlib figure
#         fig, ax = plt.subplots(
#             figsize=(max(12, max_cols * 2), max(8, len(rows) * 0.8)))
#         ax.axis('tight')
#         ax.axis('off')

#         # Create table with proper cell merging visualization
#         table_plot = ax.table(cellText=rows,
#                               cellLoc='center',
#                               loc='center',
#                               bbox=[0, 0, 1, 1])

#         # Style the table
#         table_plot.auto_set_font_size(False)
#         table_plot.set_fontsize(8)
#         table_plot.scale(1, 1.5)

#         # Color header row (first row)
#         for j in range(max_cols):
#             table_plot[(0, j)].set_facecolor('#40466e')
#             table_plot[(0, j)].set_text_props(weight='bold', color='white')

#         # Alternate row colors and handle merged cells visually
#         for i in range(len(rows)):
#             for j in range(max_cols):
#                 cell = table_plot[(i, j)]

#                 # Skip if this is a header cell
#                 if i == 0:
#                     continue

#                 # Alternate row colors
#                 if i % 2 == 0:
#                     cell.set_facecolor('#f0f0f0')
#                 else:
#                     cell.set_facecolor('white')

#                 # Add visual indication for merged cells
#                 if rows[i][j] == '':
#                     cell.set_facecolor('#e8e8e8')
#                     cell.set_text_props(style='italic', alpha=0.5)

#         # Add borders to make merged cells more visible
#         for i in range(len(rows)):
#             for j in range(max_cols):
#                 cell = table_plot[(i, j)]
#                 cell.set_edgecolor('black')
#                 cell.set_linewidth(0.5)

#         plt.title('Extracted Table (with merged cell support)',
#                   fontsize=14, fontweight='bold', pad=20)

#         # Save as image
#         plt.savefig(output_path.replace('.pdf', '.png'),
#                     dpi=300, bbox_inches='tight')
#         plt.close()

#         print(f"Visual table saved as: {output_path.replace('.pdf', '.png')}")
#         return True

    # except Exception as e:
    #     print(f"Error creating visual table: {e}")
    #     return False


if __name__ == "__main__":
    page_numbers = [3,5,22,36,38]
    input_type = InputType.PDF
    for page_number in page_numbers:
        pdf_path = f"pdfs/insurance_filing-pg{page_number}.pdf"
        #pdf_image = convert_pdf_to_base64_image(pdf_path)

        load_dotenv()

        # The client gets the API key from the environment variable `GEMINI_API_KEY`.
        client = genai.Client()
        with open("prompt.txt", "r") as file:
            prompt = file.read()
        response = ask_gemini(client, prompt, pdf_path, InputType.PDF)
        tables: list[Table] = response.parsed
        for i, table in enumerate(tables):
            output_path = f"gemini_outputs/{input_type.value}/insurance_filing-pg{page_number}_{i}.html"
            with open(output_path, "w") as file:
                file.write(table.table_html)
        with open(f"gemini_outputs/{input_type.value}/insurance_filing-pg{page_number}.json", "w") as file:
            list_of_dicts = [obj.model_dump() for obj in tables]
            json.dump(list_of_dicts, file, indent=4)
