# app.py (Phiên bản nâng cấp với lỗi rõ ràng hơn)

import os
import io
import base64
import time
import secrets
import json
from datetime import datetime

import dash
from dash import dcc, html, dash_table, callback, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import qrcode

# --- 1. CẤU HÌNH VÀ KHỞI TẠO ---
load_dotenv()
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
FORM_ID = os.getenv("FORM_ID")
GCP_CREDENTIALS_JSON_STRING = os.getenv("GCP_CREDENTIALS_JSON") 
SHEET_NAME = "Câu trả lời biểu mẫu 1" # <-- THAY ĐỔI TẠI ĐÂY NẾU CẦN

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# --- 2. CÁC HÀM HỖ TRỢ ---

def get_google_sheet_client():
    if not GCP_CREDENTIALS_JSON_STRING:
        print("Lỗi: Biến môi trường GCP_CREDENTIALS_JSON chưa được thiết lập.")
        return None
    try:
        credentials_dict = json.loads(GCP_CREDENTIALS_JSON_STRING)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Lỗi khi khởi tạo Google Client: {e}")
        return None

def generate_qr_with_token(expiry_minutes=5):
    token = secrets.token_urlsafe(8)
    expiry_timestamp = int(time.time() + expiry_minutes * 60)
    entry_value = f"{token}::{expiry_timestamp}"
    # LƯU Ý: Thay 'entry.2033789124' bằng Entry ID thực tế của câu hỏi TOKEN của bạn
    qr_url = f"https://docs.google.com/forms/d/e/{FORM_ID}/viewform?usp=pp_url&entry.2033789124={entry_value}"
    
    img = qrcode.make(qr_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_b64}", token, expiry_timestamp

# === HÀM ĐÃ ĐƯỢC NÂNG CẤP ===
def load_and_process_attendance():
    """Tải và xử lý dữ liệu, trả về thông báo lỗi cụ thể."""
    client = get_google_sheet_client()
    if not client:
        return pd.DataFrame([{"Lỗi": "Không thể kết nối Google Sheets. Kiểm tra cấu hình .env và credentials."}])
    try:
        # Mở spreadsheet
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        # Mở worksheet
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        
        if df.empty:
            return pd.DataFrame([{"Thông báo": "Chưa có dữ liệu điểm danh."}])
            
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
            df.dropna(subset=["Timestamp"], inplace=True)
            df["Thời gian điểm danh"] = df["Timestamp"].dt.strftime('%H:%M:%S %d-%m-%Y')
            df["Ngày"] = df["Timestamp"].dt.date
            df["Tuần"] = df["Timestamp"].dt.isocalendar().week
        
        return df
    # Bắt các lỗi cụ thể
    except gspread.exceptions.SpreadsheetNotFound:
        return pd.DataFrame([{"Lỗi": f"Không tìm thấy Spreadsheet. ID '{SPREADSHEET_ID}' có đúng không? Bạn đã Share cho email service account chưa?"}])
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame([{"Lỗi": f"Không tìm thấy Sheet có tên '{SHEET_NAME}'. Hãy kiểm tra lại tên tab trong Google Sheet."}])
    except Exception as e:
        return pd.DataFrame([{"Lỗi": f"Một lỗi không xác định đã xảy ra: {e}"}])

# --- PHẦN LAYOUT VÀ CALLBACKS KHÔNG THAY ĐỔI ---
# (Dán phần layout và callbacks từ code cũ của bạn vào đây)
app.layout = dbc.Container([
    dcc.Store(id='token-store', storage_type='session'),
    dcc.Download(id="download-excel"),
    html.H2("Hệ thống điểm danh bằng mã QR", className="text-center my-4"),
    html.Hr(),
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Tạo mã QR điểm danh"),
            dbc.CardBody([
                dbc.Label("Thời gian hiệu lực của mã QR:"),
                dcc.Slider(5, 15, 5, value=5, id="expiry-slider", marks={5:"5 phút", 10:"10 phút", 15:"15 phút"}),
                dbc.Button("Tạo QR mới", id="btn-generate", color="primary", className="w-100 mt-3"),
                html.Hr(),
                html.Div(id="qr-status-display", className="text-center"),
                html.Img(id="qr-code-display", style={"width":"250px", "margin":"10px auto", "display":"block"})
            ])
        ]), width=4),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Bảng điểm danh"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(dcc.DatePickerSingle(id="filter-date", placeholder="Lọc theo ngày")),
                    dbc.Col(dcc.Input(id="filter-class", type="text", placeholder="Lọc theo lớp...")),
                    dbc.Col(dbc.Button("Lọc", id="btn-filter", color="info"), className="d-grid"),
                ], className="mb-3"),
                dcc.Loading(dash_table.DataTable(
                    id="attendance-table", page_size=10, style_table={"overflowX":"auto"}
                )),
                html.Div([
                    dbc.Button("Làm mới dữ liệu", id="btn-refresh", color="success"),
                    dbc.Button("Xuất Excel", id="btn-excel", color="secondary", className="ms-2"),
                ], className="mt-3"),
            ])
        ]), width=8)
    ]),
    dcc.Interval(id="auto-refresh-interval", interval=30*1000, n_intervals=0)
], fluid=True)

@callback(
    Output("qr-code-display", "src"),
    Output("qr-status-display", "children"),
    Output("token-store", "data"),
    Input("btn-generate", "n_clicks"),
    State("expiry-slider", "value"),
    prevent_initial_call=True
)
def generate_and_display_qr(n_clicks, expiry_minutes):
    img_b64, token, expiry_timestamp = generate_qr_with_token(expiry_minutes)
    expiry_time_str = datetime.fromtimestamp(expiry_timestamp).strftime('%H:%M:%S')
    status_message = f"Mã QR hợp lệ trong {expiry_minutes} phút (đến {expiry_time_str})."
    token_data = {'token': token, 'expiry': expiry_timestamp}
    return img_b64, dbc.Alert(status_message, color="info"), token_data

@callback(
    Output("attendance-table", "data"),
    Output("attendance-table", "columns"),
    Input("btn-refresh", "n_clicks"),
    Input("auto-refresh-interval", "n_intervals"),
    Input("btn-filter", "n_clicks"),
    State("filter-date", "date"),
    State("filter-class", "value")
)
def update_attendance_table(n_refresh, n_interval, n_filter, date_filter, class_filter):
    df = load_and_process_attendance()
    if "Lỗi" in df.columns or "Thông báo" in df.columns:
        return df.to_dict("records"), [{"name": i, "id": i} for i in df.columns]

    triggered_id = ctx.triggered_id
    if triggered_id == 'btn-filter':
        if date_filter:
            df = df[df["Ngày"] == pd.to_datetime(date_filter).date()]
        if class_filter and "Lớp" in df.columns:
            df = df[df["Lớp"].astype(str).str.contains(class_filter, case=False, na=False)]

    columns_to_display = [col for col in ["Timestamp", "Mã số sinh viên", "Họ và tên", "Lớp", "Thời gian điểm danh"] if col in df.columns]
    return df[columns_to_display].to_dict("records"), [{"name": i, "id": i} for i in columns_to_display]

@callback(
    Output("download-excel", "data"),
    Input("btn-excel", "n_clicks"),
    prevent_initial_call=True
)
def export_to_excel(n_clicks):
    df = load_and_process_attendance()
    if "Lỗi" in df.columns or "Thông báo" in df.columns:
        return None
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='DiemDanh')
    excel_data = output.getvalue()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"BaoCaoDiemDanh_{timestamp}.xlsx"
    return dcc.send_bytes(excel_data, filename)

if __name__ == "__main__":
    app.run_server(debug=True)
