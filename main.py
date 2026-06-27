import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
import os 
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import re

app = FastAPI()
load_dotenv()

DATA_ID = os.getenv('DATA_ID')
BASE_DIR = Path(__file__).resolve().parent
cred_path = BASE_DIR / 'config' / 'credential.json'

origins = [
    'http://localhost:5500',
    'http://127.0.0.1:5500'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials = True,
    allow_methods = ['*'],
    allow_headers = ['*']
)


creds = Credentials.from_service_account_file(
    cred_path,
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]
)

client = gspread.authorize(creds)
spreadsheet = client.open_by_key(DATA_ID)
sheets = spreadsheet.worksheets()

def normalize_key(text):
    text = text.strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "_", text)

    return text.lower()


def clean_sheet_data(rows):
    cleaned = []

    for row in rows:
        clean_row = []

        for cell in row:
            cell = cell.replace("|", "").strip()

            if cell:
                clean_row.append(cell)

        if clean_row:
            cleaned.append(clean_row)

    return cleaned


def parse_sheet(sheet):
    rows = clean_sheet_data(sheet.get_all_values())

    result = {
        "title": sheet.title.strip(),
        "slug": normalize_key(sheet.title),
        "description": "",
        "type": None,
        "content": None
    }

    if not rows:
        return result

    result["description"] = rows[0][0]

    # Detecta tabela
    if len(rows) > 2 and len(rows[1]) >= 3:
        result["type"] = "table"

        headers = [
            normalize_key(header)
            for header in rows[1]
        ]

        table_rows = []

        for row in rows[2:]:
            item = {}

            for i, value in enumerate(row):
                if i < len(headers):
                    item[headers[i]] = value

            if item:
                table_rows.append(item)

        result["content"] = table_rows

    else:
        result["type"] = "key_value"

        content = {}

        for row in rows[1:]:
            if len(row) >= 2:
                key = normalize_key(row[0])
                value = row[1]

                content[key] = value

        result["content"] = content

    return result


@app.get('/sheets')
def get_sheets():
    data = {
        normalize_key(sheet.title): parse_sheet(sheet)
        for sheet in sheets
    }
    return data