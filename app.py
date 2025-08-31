# app.py (Phiên bản cuối cùng với logic highlight và hiển thị cột tùy chỉnh)

import os
import io
import base64
import time
import secrets
import json
import logging
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

# === THIẾT LẬP LOGGING ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 1. CẤU HÌNH VÀ KHỞI TẠO ---
load_dotenv()
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
FORM_ID = os.getenv("FORM_ID")
GCP_CREDENTIALS_JSON_STRING = os.getenv("GCP_CREDENTIALS_JSON") 
SHEET_NAME = "Form Responses 1" # <-- Hoặc tên sheet thực tế của bạn

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# --- 2. CÁC HÀM HỖ TRỢ ---

def get_google_sheet_client():
    if not GCP_CREDENTIALS_JSON_STRING:
        logger.error("Biến môi trường GCP_CREDENTIALS_JSON chưa được thiết lập.")
        return None
    try:
        credentials_dict = json.loads(GCP_CREDENTIALS_JSON_STRING)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        client = gspread.authorize(creds)
        logger.info("Khởi tạo Google Sheets client thành công")
        return client
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo Google Client: {e}")
        return None

def generate_qr_with_token(expiry_minutes=5):
    now = datetime.now()
    attendance_code = f"{now.strftime('T%d%H%M%S')}"
    expiry_timestamp = int(time.time() + expiry_minutes * 60)
    
    # LƯU Ý: Thay 'entry.xxxxxxxxxx' bằng Entry ID của câu hỏi "Mã điểm danh" của bạn
    ENTRY_ID_MA_DIEM_DANH = "entry.2033789124" # THAY THẾ ID NÀY
    
    qr_url = f"https://docs.google.com/forms/d/e/{FORM_ID}/viewform?usp=pp_url&{ENTRY_ID_MA_DIEM_DANH}={attendance_code}"
    
    img = qrcode.make(qr_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    
    logger.info(f"Tạo QR code thành công - Mã điểm danh: {attendance_code}")
    return f"data:image/png;base64,{img_b64}", attendance_code, expiry_timestamp

def load_and_process_attendance():
    logger.info("Bắt đầu tải dữ liệu từ Google Sheets...")
    client = get_google_sheet_client()
    if not client:
        return pd.DataFrame([{"Lỗi": "Không thể kết nối Google Sheets."}])
    
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        # 1. Đọc dữ liệu bình thường, không có dtype
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        
        if df.empty:
            return pd.DataFrame([{"Thông báo": "Chưa có dữ liệu điểm danh."}])
        
        # 2. CHUYỂN ĐỔI KIỂU DỮ LIỆU THỦ CÔNG
        # Liệt kê tất cả các cột cần đảm bảo là văn bản
        string_columns = ["Mã điểm danh", "Mã số người học", "Lớp học phần"]
        
        for col in string_columns:
            if col in df.columns:
                # Ép kiểu cột đó thành string, fillna('') để xử lý các ô trống
                df[col] = df[col].astype(str).fillna('')
        
        # 3. Xử lý Timestamp
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
            df.dropna(subset=["Timestamp"], inplace=True)
            df["Thời gian điểm danh"] = df["Timestamp"].dt.strftime('%H:%M:%S %d-%m-%Y')
            
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        return pd.DataFrame([{"Lỗi": f"Không tìm thấy Spreadsheet ID. Đã share quyền Editor chưa?"}])
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame([{"Lỗi": f"Không tìm thấy Sheet '{SHEET_NAME}'."}])
    except Exception as e:
        logger.error(f"Lỗi không xác định: {e}", exc_info=True)
        return pd.DataFrame([{"Lỗi": f"Lỗi không xác định: {e}"}])

# --- 3. LAYOUT ---
app.layout = dbc.Container([
    dcc.Store(id='session-store', storage_type='session'), 
    dcc.Download(id="download-excel"),
    html.H2("Hệ thống điểm danh bằng mã QR", className="text-center my-4"),
    html.Hr(),
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Tạo mã QR điểm danh"),
            dbc.CardBody([
                dbc.Label("Thời gian hiệu lực của mã QR:", className="fw-bold"),
                dcc.Slider(0, 15, 5, value=5, id="expiry-slider", marks={1:"1 phút", 5:"5 phút", 10:"10 phút", 15:"15 phút"}),
                dbc.Button("Tạo QR mới", id="btn-generate", color="primary", className="w-100 mt-3"),
                html.Hr(),
                html.Div(id="qr-status-display", className="text-center"),
                html.Img(id="qr-code-display", style={"width":"280px", "margin":"10px auto", "display":"block"}),
            ])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Bảng điểm danh"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(dcc.DatePickerSingle(id="filter-date", placeholder="Lọc theo ngày"), width=4),
                    dbc.Col(dcc.Input(id="filter-class", type="text", placeholder="Lọc theo lớp học phần..."), width=4),
                    dbc.Col(dbc.ButtonGroup([
                        dbc.Button("Lọc", id="btn-filter", color="info"),
                        dbc.Button("Reset", id="btn-reset", color="secondary")
                    ]), width=4),
                ], className="mb-3 align-items-end"),
                dcc.Loading(dash_table.DataTable(
                    id="attendance-table", 
                    page_size=20, 
                    style_table={"overflowX":"auto"},
                    style_cell={'textAlign': 'left', 'whiteSpace': 'normal', 'height': 'auto'},
                    style_header={'fontWeight': 'bold', 'textAlign': 'center'},
                )),
                html.Div([
                    dbc.Button("Làm mới dữ liệu", id="btn-refresh", color="success"),
                    dbc.Button("Xuất Excel", id="btn-excel", color="secondary", className="ms-2"),
                ], className="mt-3"),
            ])
        ]), width=9)
    ]),
    dcc.Interval(id="auto-refresh-interval", interval=60*1000, n_intervals=0)
], fluid=True)


# --- 4. CALLBACKS (ĐÃ CẬP NHẬT) ---

@callback(
    Output("qr-code-display", "src"),
    Output("qr-status-display", "children"),
    Output("session-store", "data"),
    Input("btn-generate", "n_clicks"),
    State("expiry-slider", "value"),
    prevent_initial_call=True
)
def generate_and_display_qr(n_clicks, expiry_minutes):
    if not FORM_ID:
        return "", dbc.Alert("FORM_ID chưa được cấu hình", color="danger"), {}
    
    img_b64, attendance_code, expiry_timestamp = generate_qr_with_token(expiry_minutes)
    
    if not img_b64:
        return "", dbc.Alert("Không thể tạo mã QR", color="danger"), {}
    
    expiry_time_str = datetime.fromtimestamp(expiry_timestamp).strftime('%H:%M:%S')
    
    status_message = html.Div([
        html.H5(f"Mã điểm danh: {attendance_code}", className="text-success fw-bold"),
        html.P(f"Hiệu lực đến: {expiry_time_str} ({expiry_minutes} phút)", className="small text-muted")
    ])
    
    session_data = {
        'attendance_code': str(attendance_code), # Đảm bảo là chuỗi
        'created_at': datetime.now().isoformat()
    }
    
    return img_b64, status_message, session_data

@callback(
    Output("attendance-table", "data"),
    Output("attendance-table", "columns"),
    Output("attendance-table", "style_data_conditional"),
    Output("filter-date", "date"),
    Output("filter-class", "value"),
    Input("btn-refresh", "n_clicks"),
    Input("auto-refresh-interval", "n_intervals"),
    Input("btn-filter", "n_clicks"),
    Input("btn-reset", "n_clicks"),
    State("filter-date", "date"),
    State("filter-class", "value"),
    State("session-store", "data")
)
def update_attendance_table(n_refresh, n_interval, n_filter, n_reset, date_filter, class_filter, session_data):
    triggered_id = ctx.triggered_id if ctx.triggered else 'auto-refresh-interval'
    df = load_and_process_attendance()
    
    if "Lỗi" in df.columns or "Thông báo" in df.columns:
        cols = [{"name": i, "id": i} for i in df.columns]
        return df.to_dict("records"), cols, [], date_filter, class_filter

    if triggered_id == 'btn-reset':
        date_filter, class_filter = None, ""
    
    df_filtered = df.copy()
    if date_filter and "Timestamp" in df_filtered.columns:
        df_filtered = df_filtered[pd.to_datetime(df_filtered["Timestamp"]).dt.date == pd.to_datetime(date_filter).date()]
    if class_filter and "Lớp học phần" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Lớp học phần"].astype(str).str.contains(class_filter, case=False, na=False)]

    # --- LOGIC HIGHLIGHT ĐÃ CẬP NHẬT ---
    style_data_conditional = []
    if session_data and 'attendance_code' in session_data and 'created_at' in session_data:
        current_code = str(session_data['attendance_code'])
        session_start_time = datetime.fromisoformat(session_data['created_at'])
        
        # 1. Chỉ xét những lượt điểm danh diễn ra trong phiên hiện tại
        df_current_session = df_filtered[df_filtered["Timestamp"] >= session_start_time].copy()

        if not df_current_session.empty and "Mã điểm danh" in df_current_session.columns and "Mã số người học" in df_current_session.columns:
            # Chuyển đổi sang chuỗi để so sánh an toàn
            df_current_session['Mã điểm danh'] = df_current_session['Mã điểm danh'].astype(str)
            
            # 2. Lọc ra những dòng KHÔNG PHẢI giảng viên (có mã số người học) VÀ có mã điểm danh sai
            mismatched_rows = df_current_session[
                (df_current_session["Mã số người học"].astype(str).str.strip() != '') & # Có mã SV
                (df_current_session["Mã điểm danh"] != current_code) # Mã điểm danh sai
            ]
            
            if not mismatched_rows.empty:
                logger.info(f"Phát hiện {len(mismatched_rows)} sinh viên không khớp mã.")
                style_data_conditional.append({
                    'if': {'filter_query': f'{{id}} eq {i}' for i in mismatched_rows.index},
                    'backgroundColor': '#FFD2D2',
                    'color': '#D8000C',
                })

    # --- LOGIC HIỂN THỊ CỘT ĐÃ CẬP NHẬT ---
    # Danh sách các cột bạn muốn hiển thị, theo đúng thứ tự
    columns_to_display_ordered = [
        "STT", # Sẽ được thêm sau
        "Thời gian điểm danh",
        "Email Address",
        "Đối tượng",
        "Mã điểm danh",
        "Mã số người học",
        "Lớp học phần",
        "Người học được hỗ trợ điểm danh",
        "Người học được đánh giá",
        "Điểm của người học được đánh giá"
    ]
    
    # Lọc ra những cột thực sự tồn tại trong DataFrame
    final_columns = [col for col in columns_to_display_ordered if col in df_filtered.columns or col == "STT"]

    # Thêm cột STT
    df_filtered.insert(0, 'STT', range(1, len(df_filtered) + 1))
    
    # Thêm ID vào dữ liệu để filter_query hoạt động
    df_filtered['id'] = df_filtered.index
    
    table_cols = [{"name": i, "id": i} for i in final_columns]
    
    return df_filtered[final_columns + ['id']].to_dict("records"), table_cols, style_data_conditional, date_filter, class_filter

@callback(
    Output("download-excel", "data"),
    Input("btn-excel", "n_clicks"),
    prevent_initial_call=True
)
def export_to_excel(n_clicks):
    df = load_and_process_attendance()
    if "Lỗi" in df.columns or "Thông báo" in df.columns: return None
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='DiemDanh')
    
    filename = f"BaoCaoDiemDanh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return dcc.send_bytes(output.getvalue(), filename)

if __name__ == "__main__":
    app.run_server(debug=True)
