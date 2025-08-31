# check_connection.py
import os
import json
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Tải các biến từ file .env
load_dotenv()
GCP_CREDENTIALS_JSON_STRING = os.getenv("GCP_CREDENTIALS_JSON")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = "Form Responses 1" # Hoặc tên sheet của bạn

print("--- BẮT ĐẦU KIỂM TRA KẾT NỐI ---")

# --- Bước 1: Kiểm tra biến môi trường ---
if not GCP_CREDENTIALS_JSON_STRING:
    print("❌ LỖI: Không tìm thấy biến môi trường 'GCP_CREDENTIALS_JSON'. File .env có vấn đề.")
    exit()
print("✅ Bước 1: Đã tải biến môi trường 'GCP_CREDENTIALS_JSON' thành công.")

# --- Bước 2: Kiểm tra định dạng JSON ---
try:
    credentials_dict = json.loads(GCP_CREDENTIALS_JSON_STRING)
    print(f"✅ Bước 2: Phân tích JSON thành công. Client Email: {credentials_dict.get('client_email')}")
except json.JSONDecodeError as e:
    print(f"❌ LỖI: Chuỗi JSON trong .env không hợp lệ. Hãy kiểm tra lại định dạng. Chi tiết lỗi: {e}")
    exit()

# --- Bước 3: Thử kết nối và xác thực với Google ---
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    client = gspread.authorize(creds)
    print("✅ Bước 3: Xác thực với Google thành công!")
except Exception as e:
    print(f"❌ LỖI: Xác thực với Google thất bại. Vấn đề có thể nằm ở nội dung credentials hoặc API chưa được bật. Chi tiết lỗi: {e}")
    exit()

# --- Bước 4: Thử mở Spreadsheet bằng ID ---
if not SPREADSHEET_ID:
    print("❌ LỖI: Biến môi trường 'SPREADSHEET_ID' chưa được thiết lập trong .env.")
    exit()
try:
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    print(f"✅ Bước 4: Mở thành công Spreadsheet có tên: '{spreadsheet.title}'")
except gspread.exceptions.SpreadsheetNotFound:
    print(f"❌ LỖI: Không tìm thấy Spreadsheet với ID đã cung cấp.")
    print("    -> Gợi ý: Kiểm tra lại 'SPREADSHEET_ID' trong .env. Bạn đã chia sẻ Sheet cho client_email với quyền 'Editor' chưa?")
    exit()
except Exception as e:
    print(f"❌ LỖI: Không thể mở Spreadsheet. Chi tiết lỗi: {e}")
    exit()

# --- Bước 5: Thử mở Worksheet bằng tên ---
try:
    worksheet = spreadsheet.worksheet(SHEET_NAME)
    print(f"✅ Bước 5: Mở thành công Worksheet: '{worksheet.title}'")
except gspread.exceptions.WorksheetNotFound:
    print(f"❌ LỖI: Không tìm thấy Worksheet có tên '{SHEET_NAME}' trong Spreadsheet.")
    print(f"    -> Gợi ý: Tên sheet trong file .env có thể sai. Các sheet tìm thấy là: {[ws.title for ws in spreadsheet.worksheets()]}")
    exit()
except Exception as e:
    print(f"❌ LỖI: Không thể mở Worksheet. Chi tiết lỗi: {e}")
    exit()

print("\n🎉 CHÚC MỪNG! Mọi cấu hình đều chính xác và kết nối thành công!")
