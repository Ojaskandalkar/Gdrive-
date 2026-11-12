import os
import logging
import gspread
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_worksheet():
    """Authenticates with Google using the Service Account and returns the first worksheet."""
    try:
        service_account_file = os.getenv("SERVICE_ACCOUNT_FILE", "service_account.json")
        sheet_name = os.getenv("SHEET_NAME")
        
        if not sheet_name:
            raise ValueError("SHEET_NAME is not set in the .env file.")
        
        gc = gspread.service_account(filename=service_account_file)
        spreadsheet = gc.open(sheet_name)
        return spreadsheet.sheet1
    except Exception as e:
        logging.error(f"Failed to connect to Google Sheets: {e}")
        raise

def read_all_records():
    """Reads and returns all data from the worksheet as a list of dictionaries."""
    try:
        worksheet = get_worksheet()
        records = worksheet.get_all_records()
        logging.info(f"Successfully read {len(records)} records from the sheet.")
        return records
    except Exception as e:
        logging.error(f"Error reading records: {e}")
        return []

def find_record(field, value):
    """Finds records matching field and value, handling whitespace and case differences."""
    try:
        records = read_all_records()
        results = []
        target_field = str(field).strip().lower()
        target_val = str(value).strip().lower()

        for r in records:
            for k, v in r.items():
                if k.strip().lower() == target_field and str(v).strip().lower() == target_val:
                    results.append(r)
                    break

        logging.info(f"Found {len(results)} records matching {field} = {value}.")
        return results
    except Exception as e:
        logging.error(f"Error finding record: {e}")
        return []

def add_record(record_dict):
    """Appends a new record dynamically aligned with actual sheet headers."""
    try:
        worksheet = get_worksheet()
        headers = worksheet.row_values(1)
        
        row_data = []
        for h in headers:
            val = ""
            for k, v in record_dict.items():
                if k.strip().lower() == h.strip().lower():
                    val = v
                    break
            row_data.append(val)
            
        worksheet.append_row(row_data)
        logging.info(f"Successfully added new record: {record_dict}")
        return True
    except Exception as e:
        logging.error(f"Error adding record: {e}")
        return False

def update_record(filter_dict, updates_dict):
    """Updates matching records dynamically by mapping header names flexibly."""
    try:
        worksheet = get_worksheet()
        records = worksheet.get_all_records()
        headers = worksheet.row_values(1)
        
        # Build 1-based column mapping with stripped header keys
        header_map = {h.strip().lower(): idx + 1 for idx, h in enumerate(headers)}
        
        updated_cells_count = 0
        for i, record in enumerate(records):
            # Check row match flexibly
            match = True
            for fk, fv in filter_dict.items():
                rec_val = None
                for rk, rv in record.items():
                    if rk.strip().lower() == fk.strip().lower():
                        rec_val = rv
                        break
                if rec_val is None or str(rec_val).strip().lower() != str(fv).strip().lower():
                    match = False
                    break
            
            if match:
                row_index = i + 2  # Data starts at row 2 in Google Sheets
                for col_name, new_value in updates_dict.items():
                    col_key = col_name.strip().lower()
                    if col_key in header_map:
                        col_index = header_map[col_key]
                        worksheet.update_cell(row_index, col_index, new_value)
                        updated_cells_count += 1
                        
        logging.info(f"Successfully updated {updated_cells_count} cell(s).")
        return updated_cells_count > 0
    except Exception as e:
        logging.error(f"Error updating record: {e}")
        return False

def summarize_records():
    """Generates a summary of the current records by status."""
    try:
        records = read_all_records()
        total_tasks = len(records)
        status_counts = {}
        
        for r in records:
            status = "Unknown"
            for k, v in r.items():
                if k.strip().lower() == "status":
                    status = v
                    break
            status_counts[status] = status_counts.get(status, 0) + 1
        
        summary = f"Total Tasks: {total_tasks}\n"
        for status, count in status_counts.items():
            summary += f"- {status}: {count}\n"
            
        logging.info("Successfully generated records summary.")
        return summary
    except Exception as e:
        logging.error(f"Error summarizing records: {e}")
        return "Could not generate summary due to an error."