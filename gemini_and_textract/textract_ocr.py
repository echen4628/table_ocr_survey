import boto3
import csv
import json
from pydantic import BaseModel
from pdf2image import convert_from_path
from io import BytesIO
import os
from typing import List, Dict, Any


def convert_pdf_to_image_bytes(pdf_path):
    """Convert PDF page to image bytes for Textract processing"""
    images = convert_from_path(pdf_path, first_page=1, last_page=1)
    img_buffer = BytesIO()
    images[0].save(img_buffer, format="PNG")
    return img_buffer.getvalue()



def detect_tables_with_textract(image_bytes, region_name='us-east-1'):
    """Use AWS Textract to detect and extract tables from image"""
    # Initialize Textract client
    textract_client = boto3.client('textract', region_name=region_name)

    try:
        # Call Textract to detect tables
        response = textract_client.analyze_document(
            Document={'Bytes': image_bytes},
            FeatureTypes=['TABLES']
        )

        return response
    except Exception as e:
        print(f"Error calling Textract: {e}")
        return None


def extract_table_data(textract_response):
    """Extract table data from Textract response and convert to CSV format"""
    # Get the text blocks
    blocks=textract_response['Blocks']

    blocks_map = {}
    table_blocks = []
    for block in blocks:
        blocks_map[block['Id']] = block
        if block['BlockType'] == "TABLE":
            table_blocks.append(block)

    if len(table_blocks) <= 0:
        return "<b> NO Table FOUND </b>"

    csv = ''
    for index, table in enumerate(table_blocks):
        csv += generate_table_csv(table, blocks_map, index +1)
        csv += '\n\n'

    return [csv]

def get_rows_columns_map(table_result, blocks_map):
    rows = {}
    scores = []
    for relationship in table_result['Relationships']:
        if relationship['Type'] == 'CHILD':
            for child_id in relationship['Ids']:
                cell = blocks_map[child_id]
                if cell['BlockType'] == 'CELL':
                    row_index = cell['RowIndex']
                    col_index = cell['ColumnIndex']
                    if row_index not in rows:
                        # create new row
                        rows[row_index] = {}
                    
                    # get confidence score
                    scores.append(str(cell['Confidence']))
                        
                    # get the text value
                    rows[row_index][col_index] = get_text(cell, blocks_map)
    return rows, scores


def get_text(result, blocks_map):
    text = ''
    if 'Relationships' in result:
        for relationship in result['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = blocks_map[child_id]
                    if word['BlockType'] == 'WORD':
                        if "," in word['Text'] and word['Text'].replace(",", "").isnumeric():
                            text += '"' + word['Text'] + '"' + ' '
                        else:
                            text += word['Text'] + ' '
                    if word['BlockType'] == 'SELECTION_ELEMENT':
                        if word['SelectionStatus'] =='SELECTED':
                            text +=  'X '
    return text


# def get_table_csv_results(file_name):

#     with open(file_name, 'rb') as file:
#         img_test = file.read()
#         bytes_test = bytearray(img_test)
#         print('Image loaded', file_name)

#     # process using image bytes
#     # get the results
#     session = boto3.Session(profile_name='profile-name')
#     client = session.client('textract', region_name='region')
#     response = client.analyze_document(Document={'Bytes': bytes_test}, FeatureTypes=['TABLES'])

#     # Get the text blocks
#     blocks=response['Blocks']
#     pprint(blocks)

#     blocks_map = {}
#     table_blocks = []
#     for block in blocks:
#         blocks_map[block['Id']] = block
#         if block['BlockType'] == "TABLE":
#             table_blocks.append(block)

#     if len(table_blocks) <= 0:
#         return "<b> NO Table FOUND </b>"

#     csv = ''
#     for index, table in enumerate(table_blocks):
#         csv += generate_table_csv(table, blocks_map, index +1)
#         csv += '\n\n'

#     return csv

def generate_table_csv(table_result, blocks_map, table_index):
    rows, scores = get_rows_columns_map(table_result, blocks_map)

    table_id = 'Table_' + str(table_index)
    
    # get cells.
    csv = 'Table: {0}\n\n'.format(table_id)

    for row_index, cols in rows.items():
        for col_index, text in cols.items():
            col_indices = len(cols.items())
            csv += '{}'.format(text) + ","
        csv += '\n'
        
    csv += '\n\n Confidence Scores % (Table Cell) \n'
    cols_count = 0
    for score in scores:
        cols_count += 1
        csv += score + ","
        if cols_count == col_indices:
            csv += '\n'
            cols_count = 0

    csv += '\n\n\n'
    return csv

# def main(file_name):
#     table_csv = get_table_csv_results(file_name)

#     output_file = 'output.csv'

#     # replace content
#     with open(output_file, "wt") as fout:
#         fout.write(table_csv)

#     # show the results
#     print('CSV OUTPUT FILE: ', output_file)

def process_pdf_with_textract(pdf_path, region_name='us-east-1'):
    """Process a PDF file with Textract and return extracted tables"""
    # Convert PDF to image
    image_bytes = convert_pdf_to_image_bytes(pdf_path)

    # Detect tables with Textract
    textract_response = detect_tables_with_textract(image_bytes, region_name)

    # Extract table data
    tables = extract_table_data(textract_response)

    return tables


if __name__ == "__main__":
    # Set AWS region (you can change this as needed)
    region_name = 'us-west-2'

    # Process the same PDF files as the original script
    page_numbers = [5, 22, 36, 38] # [3, 5, 22, 36, 38]

    for page_number in page_numbers:
        pdf_path = f"pdfs/insurance_filing-pg{page_number}.pdf"

        if not os.path.exists(pdf_path):
            print(f"PDF file not found: {pdf_path}")
            continue

        print(f"Processing {pdf_path}...")

        tables = process_pdf_with_textract(pdf_path, region_name)
        # Save CSV files for each table
        for i, table in enumerate(tables):
            output_path = f"textract_outputs/insurance_filing-pg{page_number}_{i}.csv"
            with open(output_path, "wt") as fout:
                fout.write(table)

            print(f"Saved table {i} to {output_path}")

