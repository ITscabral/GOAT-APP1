import os
import logging
import stat
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_invoice(invoice_number, employee_name, company_info, timesheet_data, total_hours, hourly_rate=30.0):
    """Generate a professional PDF invoice."""
    try:
        # Set the target directory to the persistent disk path
        target_directory = "/tmp/invoices"

        # Ensure the target directory exists and has appropriate permissions
        os.makedirs(target_directory, exist_ok=True)
        os.chmod(target_directory, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
        logger.info(f"Verified invoice directory: {target_directory}")

        # Define the filename path
        filename = os.path.join(target_directory, f"Invoice_{invoice_number}_{employee_name}.pdf")
        logger.info(f"Attempting to create invoice file at: {filename}")

        # Create PDF canvas
        c = canvas.Canvas(filename, pagesize=A4)

        # Optional: Insert a logo if it exists
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "company_logo.png")
        if os.path.exists(logo_path):
            c.drawImage(logo_path, 30, 770, width=120, height=80)
        else:
            logger.warning("Logo not found. Skipping logo addition.")

        # Add company and invoice details
        c.setFont("Helvetica-Bold", 12)
        c.drawString(150, 800, company_info.get("Company Name", "GOAT Removals"))
        c.setFont("Helvetica", 10)
        c.drawString(150, 780, company_info.get("Address", "123 Business St, Sydney, Australia"))
        c.drawString(150, 765, f"Phone: {company_info.get('Phone', '+61 2 1234 5678')}")

        # Add invoice title and employee information
        c.setFont("Helvetica-Bold", 16)
        c.drawString(230, 720, f"Invoice #{invoice_number}")
        date_generated = datetime.now().strftime('%Y-%m-%d %A')
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, 690, f"Employee: {employee_name}")
        c.setFont("Helvetica", 10)
        c.drawString(30, 670, f"Date Generated: {date_generated}")

        # Add timesheet details
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30, 650, "Date")
        c.drawString(150, 650, "Start Time")
        c.drawString(250, 650, "End Time")
        c.drawString(350, 650, "Hours Worked")
        c.line(30, 645, 500, 645)

        y = 630
        for entry in timesheet_data:
            date, start, end, hours = entry
            weekday = datetime.strptime(date, "%Y-%m-%d").strftime('%A')
            c.setFont("Helvetica", 10)
            c.drawString(30, y, f"{date} ({weekday})")
            c.drawString(150, y, start)
            c.drawString(250, y, end)
            c.drawString(350, y, f"{hours:.2f}")
            y -= 20
            if y < 100:  # Start a new page if needed
                c.showPage()
                y = 750

        # Add summary of hours and payment
        total_payment = total_hours * hourly_rate
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, y - 30, f"Total Hours: {total_hours:.2f}")
        c.drawString(30, y - 50, f"Hourly Rate: ${hourly_rate:.2f}")
        c.drawString(30, y - 70, f"Total Payment: ${total_payment:.2f}")

        # Footer message
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawString(30, 50, "Thank you for your work! If you have any questions, contact our office.")
        c.save()

        logger.info(f"PDF successfully saved at {filename}")

        # Check if the file was saved successfully
        if os.path.exists(filename):
            logger.info(f"Invoice successfully created: {filename}")
            return filename
        else:
            logger.error("Failed to save the invoice file.")
            return None

    except Exception as e:
        logger.error(f"Invoice generation failed: {e}")
        return None
