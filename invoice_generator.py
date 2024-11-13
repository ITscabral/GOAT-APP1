import os
import logging
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ddef generate_invoice(invoice_number, employee_name, company_info, timesheet_data, total_hours, hourly_rate=30.0):
    """Generate a professional PDF invoice."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    target_directory = os.path.join(BASE_DIR, "invoices")

    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    filename = os.path.join(target_directory, f"Invoice_{invoice_number}_{employee_name}.pdf")

    try:
        # Code for generating the invoice PDF
        c = canvas.Canvas(filename, pagesize=A4)
        # [PDF generation code continues here...]
        c.save()

        # Ensure this return is properly indented and inside the function
        return filename if os.path.exists(filename) else None

    except Exception as e:
        logger.error(f"Invoice generation failed: {e}")
        return None
