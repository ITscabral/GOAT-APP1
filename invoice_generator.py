import os
import logging
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_invoice(invoice_number, employee_name, company_info, timesheet_data, total_hours, hourly_rate=30.0):
    """Generate a professional PDF invoice."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    target_directory = os.path.join(BASE_DIR, "invoices")
    logger.info(f"Target directory: {target_directory}")

    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    filename = os.path.join(target_directory, f"Invoice_{invoice_number}_{employee_name}.pdf")
    logger.info(f"Full path to invoice: {filename}")

    try:
        c = canvas.Canvas(filename, pagesize=A4)
        logo_path = os.path.join(BASE_DIR, "company_logo.png")
        if os.path.exists(logo_path):
            c.drawImage(logo_path, 30, 770, width=120, height=80)
        else:
            logger.warning("Logo not found, skipping.")

        c.setFont("Helvetica-Bold", 12)
        c.drawString(150, 800, company_info.get("Company Name", "GOAT Removals"))
        c.setFont("Helvetica", 10)
        c.drawString(150, 780, company_info.get("Address", "123 Business St, Sydney, Australia"))
        c.drawString(150, 765, f"Phone: {company_info.get('Phone', '+61 2 1234 5678')}")

        c.setFont("Helvetica-Bold", 16)
        c.drawString(230, 720, f"Invoice #{invoice_number}")
        date_generated = datetime.now().strftime('%Y-%m-%d %A')
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, 690, f"Employee: {employee_name}")
        c.setFont("Helvetica", 10)
        c.drawString(30, 670, f"Date Generated: {date_generated}")

        y = 640
        for entry in timesheet_data:
            date, start, end, hours = entry
            weekday = datetime.strptime(date, "%Y-%m-%d").strftime('%A')
            c.setFont("Helvetica", 10)
            c.drawString(30, y, f"{date} ({weekday})")
            c.drawString(150, y, start)
            c.drawString(250, y, end)
            c.drawString(350, y, f"{hours:.2f}")
            y -= 20

        total_payment = total_hours * hourly_rate
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, y - 30, f"Total Hours: {total_hours:.2f}")
        c.drawString(30, y - 50, f"Hourly Rate: ${hourly_rate:.2f}")
        c.drawString(30, y - 70, f"Total Payment: ${total_payment:.2f}")

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawString(30, 50, "Thank you for your work! If you have any questions, contact our office.")
        c.save()
        logger.info(f"PDF saved at {filename}")

        return filename if os.path.exists(filename) else None
    except Exception as e:
        logger.error(f"Invoice generation failed: {e}")
        return None



@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
    username = request.form.get('username')

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    # Fetch time entries for the employee
    conn = get_db_connection()
    entries = conn.execute('SELECT date, start_time, end_time FROM time_entries WHERE username = ?', (username,)).fetchall()
    conn.close()

    if not entries:
        return jsonify({'error': 'No time entries found for this user'}), 400

    timesheet_data = [
        (entry['date'], entry['start_time'], entry['end_time'],
         round((datetime.strptime(entry['end_time'], "%H:%M") - datetime.strptime(entry['start_time'], "%H:%M") - timedelta(minutes=30)).seconds / 3600.0, 2))
        for entry in entries
    ]
    total_hours = sum(entry[3] for entry in timesheet_data)

    conn = get_db_connection()
    invoice_number = conn.execute('SELECT COALESCE(MAX(invoice_number), 0) + 1 FROM invoices').fetchone()[0]
    conn.close()

    company_info = {
        "Company Name": "GOAT Removals",
        "Address": "123 Business St, Sydney, Australia",
        "Phone": "+61 2 1234 5678"
    }

    filepath = generate_invoice(invoice_number, username, company_info, timesheet_data, total_hours)
    if filepath is None or not os.path.exists(filepath):
        return jsonify({'error': 'Failed to generate invoice or file not found'}), 500

    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO invoices (invoice_number, username, date, total_hours, total_payment, filename) VALUES (?, ?, ?, ?, ?, ?)',
            (invoice_number, username, datetime.now().strftime("%Y-%m-%d"), total_hours, total_hours * 30, filepath)
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        return jsonify({'error': f'Failed to save invoice data: {str(e)}'}), 500

    # Return the file as a downloadable PDF
    return send_file(filepath, as_attachment=True)

# Note: The open_invoice function is intended for local use only and may not work on cloud deployment environments.
def open_invoice(filename):
    """Open the generated PDF invoice using the native system viewer."""
    try:
        logger.info(f"Attempting to open invoice: {filename}")

        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")

        if os.name == 'nt':  # Windows
            os.startfile(filename)
        elif os.name == 'posix':  # macOS/Linux
            subprocess.run(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', filename], check=True)
        else:
            raise OSError("Unsupported operating system.")

    except Exception as e:
        logger.error(f"Failed to open invoice: {e}")
