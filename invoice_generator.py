import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def generate_invoice(invoice_number, employee_name, company_info, timesheet_data, total_hours, hourly_rate=30.0):
    """Generate a professional PDF invoice."""

    # Step 1: Define the specific folder path
    target_directory = r"C:\Users\Lucas Cabral\Desktop\APP GOAT REMOVALS"
    print(f"[INFO] Target directory: {target_directory}")

    # Step 2: Ensure the directory exists
    if not os.path.exists(target_directory):
        print("[INFO] Directory does not exist, creating it...")
        os.makedirs(target_directory)

    # Step 3: Create the filename with the full path
    filename = os.path.join(target_directory, f"Invoice_{invoice_number}_{employee_name}.pdf")
    print(f"[INFO] Full path to invoice: {filename}")

    try:
        # Initialize PDF canvas
        print(f"[INFO] Generating PDF at {filename}")
        c = canvas.Canvas(filename, pagesize=A4)

        # Optional: Add a logo if it exists
        logo_path = "company_logo.png"
        if os.path.exists(logo_path):
            c.drawImage(logo_path, 30, 770, width=120, height=80)
        else:
            print("[WARNING] Logo not found, skipping.")

        # Add Company Info
        c.setFont("Helvetica-Bold", 12)
        c.drawString(150, 800, company_info.get("Company Name", "GOAT Removals"))
        c.setFont("Helvetica", 10)
        c.drawString(150, 780, company_info.get("Address", "123 Business St, Sydney, Australia"))
        c.drawString(150, 765, f"Phone: {company_info.get('Phone', '+61 2 1234 5678')}")

        # Add Invoice Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(230, 720, f"Invoice #{invoice_number}")

        # Add Employee Name and Date
        date_generated = datetime.now().strftime('%Y-%m-%d %A')
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, 690, f"Employee: {employee_name}")
        c.setFont("Helvetica", 10)
        c.drawString(30, 670, f"Date Generated: {date_generated}")

        # Add Table Data
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

        # Summary and Footer
        total_payment = total_hours * hourly_rate
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, y - 30, f"Total Hours: {total_hours:.2f}")
        c.drawString(30, y - 50, f"Hourly Rate: ${hourly_rate:.2f}")
        c.drawString(30, y - 70, f"Total Payment: ${total_payment:.2f}")

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawString(30, 50, "Thank you for your work! If you have any questions, contact our office.")

        # Save the PDF
        c.save()
        print(f"[SUCCESS] PDF saved at {filename}")

        # Validate the file exists after saving
        if os.path.exists(filename):
            print(f"[INFO] File exists: {filename}")
            return filename
        else:
            raise FileNotFoundError(f"File not found at: {filename}")

    except Exception as e:
        print(f"[ERROR] Invoice generation failed: {e}")
        return None
def open_invoice(filename):
    """Open the generated PDF invoice using the native system viewer."""
    try:
        print(f"[INFO] Attempting to open invoice: {filename}")

        # Check if the file exists
        if not os.path.exists(filename):
            raise FileNotFoundError(f"[ERROR] File not found: {filename}")

        # Open file based on OS
        if os.name == 'nt':  # Windows
            os.startfile(filename)
        elif os.name == 'posix':  # macOS/Linux
            subprocess.run(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', filename], check=True)
        else:
            raise OSError("Unsupported operating system.")

    except Exception as e:
        print(f"[ERROR] Failed to open invoice: {e}")