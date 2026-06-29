import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
import os 
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
sh = client.open_by_key(DATA_ID)

def load_sheet(name):
    ws = sh.worksheet(name)
    return ws.get_all_records()

sheets = {
    'products': load_sheet('products'),
    'numbers': load_sheet('numbers'),
    'bonuses': load_sheet('bonuses'),
    'comercial': load_sheet('comercial'),
    'delivery': load_sheet('delivery')
}

def index_by_product_id(rows):
    result = {}

    for row in rows:
        pid = row["product_id"]

        if pid not in result:
            result[pid] = []

        result[pid].append(row)

    return result

numbers_idx = index_by_product_id(sheets["numbers"])
bonuses_idx = index_by_product_id(sheets["bonuses"])
comercial_idx = index_by_product_id(sheets["comercial"])
delivery_idx = index_by_product_id(sheets["delivery"])

def build_product(product_row):
    pid = product_row["product_id"]

    return {
        **product_row,
        "numbers": sorted(numbers_idx.get(pid, []),
            key=lambda x: x.get('order', 0)
        ),

        "bonuses": bonuses_idx.get(pid, []),
        "comercial": sorted(
            comercial_idx.get(pid, []),
            key=lambda x: x.get('order', 0)
        ),

        "delivery": sorted(
            delivery_idx.get(pid, []),
            key=lambda x: x.get("order", 0)
        )
    }

products = sheets["products"]

all_products = [build_product(p) for p in products]

@app.get('/sheets')
def get_sheets():
    return all_products
