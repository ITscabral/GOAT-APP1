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
