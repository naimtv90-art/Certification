import os
import zipfile
import shutil
import openpyxl
import pymupdf as fitz

def generate_certificates_from_spreadsheet():
    base_dir = r"D:\Certificate generator"
    excel_path = os.path.join(base_dir, "Untitled spreadsheet.xlsx")
    master_pdf_path = os.path.join(base_dir, "AI4BT Global Summit 2026 certificate.pdf")
    font_path = os.path.join(base_dir, "AlexBrush-Regular.ttf")

    # Target folders
    output_parent_dir = os.path.join(base_dir, "Generated_Certificates")
    pdf_dir = os.path.join(output_parent_dir, "PDF")
    png_dir = os.path.join(output_parent_dir, "PNG")
    combined_pdf_path = os.path.join(output_parent_dir, "All_15_Certificates_Combined.pdf")
    zip_path = os.path.join(base_dir, "Generated_Certificates.zip")

    # 1. Clean or create output directories
    for directory in [pdf_dir, png_dir]:
        if os.path.exists(directory):
            for f in os.listdir(directory):
                p = os.path.join(directory, f)
                if os.path.isfile(p):
                    os.unlink(p)
        else:
            os.makedirs(directory, exist_ok=True)

    # 2. Load names from Excel
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb.active

    records = []
    for r in range(1, sheet.max_row + 1):
        val = sheet.cell(r, 1).value
        if val is not None and str(val).strip():
            records.append((r, str(val).strip()))

    total_records = len(records)
    print(f"Loaded {total_records} names from '{excel_path}'")

    # 3. Clean Master Template
    if not os.path.exists(master_pdf_path):
        raise FileNotFoundError(f"Master PDF not found: {master_pdf_path}")

    master_doc = fitz.open(master_pdf_path)
    stream_18 = master_doc.xref_stream(18).decode("latin1")
    lines = stream_18.split("\n")
    cleaned_lines = lines[:54] + lines[93:]
    master_doc.update_stream(18, "\n".join(cleaned_lines).encode("latin1"))

    # Font and layout setup
    font = fitz.Font(fontfile=font_path)
    base_fontsize = 75.448425
    color = (0.102, 0.1882, 0.3412)  # #1a3057 / rgb(26, 48, 87)
    base_y = 261.47937
    max_allowed_width = 430.0

    combined_doc = fitz.open()
    seen_filenames = {}
    generated_files = []

    print("\nGenerating PDF & PNG certificates...")
    for idx, (row_idx, name) in enumerate(records, start=1):
        # Auto-scale font size if name exceeds max width
        text_len = font.text_length(name, fontsize=base_fontsize)
        fontsize = base_fontsize
        if text_len > max_allowed_width:
            fontsize = base_fontsize * (max_allowed_width / text_len)
            text_len = font.text_length(name, fontsize=fontsize)

        # Create single certificate document
        doc_cert = fitz.open()
        doc_cert.insert_pdf(master_doc)
        page = doc_cert[0]

        # Center horizontally
        x = (page.rect.width - text_len) / 2.0
        y = base_y

        page.insert_font(fontname="AlexBrush", fontfile=font_path)
        page.insert_text((x, y), name, fontname="AlexBrush", fontsize=fontsize, color=color)

        # File naming
        clean_base = "".join(c for c in name if c not in '<>:"/\\|?*').strip()
        if not clean_base:
            clean_base = f"Certificate_{row_idx}"

        if clean_base in seen_filenames:
            seen_filenames[clean_base] += 1
            filename_base = f"{clean_base} ({seen_filenames[clean_base]})"
        else:
            seen_filenames[clean_base] = 1
            filename_base = clean_base

        pdf_filename = f"{filename_base}.pdf"
        png_filename = f"{filename_base}.png"

        pdf_path = os.path.join(pdf_dir, pdf_filename)
        png_path = os.path.join(png_dir, png_filename)

        # Save individual PDF
        doc_cert.save(pdf_path)

        # Save individual PNG at 300 DPI
        pix = page.get_pixmap(dpi=300)
        pix.save(png_path)

        # Add to combined document
        combined_doc.insert_pdf(doc_cert)
        doc_cert.close()

        generated_files.append((row_idx, name, pdf_path, png_path))
        print(f"  [{idx}/{total_records}] Generated -> {pdf_filename} & {png_filename}")

    master_doc.close()

    # Save combined PDF
    print(f"\nSaving combined PDF to: {combined_pdf_path}")
    combined_doc.save(combined_pdf_path)
    combined_doc.close()

    # Create ZIP archive
    print(f"Creating ZIP archive: {zip_path}")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_parent_dir):
            for file in files:
                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, base_dir)
                zipf.write(full_p, arcname=rel_p)

    print("\n================== SUMMARY ==================")
    print(f"Total Names: {total_records}")
    print(f"PDF Folder: {pdf_dir} ({len(os.listdir(pdf_dir))} files)")
    print(f"PNG Folder: {png_dir} ({len(os.listdir(png_dir))} files)")
    print(f"Combined PDF: {combined_pdf_path} ({os.path.getsize(combined_pdf_path)/(1024*1024):.2f} MB)")
    print(f"ZIP File: {zip_path} ({os.path.getsize(zip_path)/(1024*1024):.2f} MB)")
    print("=============================================")

if __name__ == "__main__":
    generate_certificates_from_spreadsheet()
