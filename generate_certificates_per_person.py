import os
import shutil
import zipfile
import openpyxl
import pymupdf as fitz

def generate_certificates():
    base_dir = r"D:\Certificate generator"
    excel_path = os.path.join(base_dir, "Untitled spreadsheet.xlsx")
    master_pdf_path = os.path.join(base_dir, "AI4BT Global Summit 2026 certificate.pdf")
    font_path = os.path.join(base_dir, "AlexBrush-Regular.ttf")

    # Target new folder
    output_root = os.path.join(base_dir, "Certificates_New")
    per_person_dir = os.path.join(output_root, "Per_Person")
    pdf_dir = os.path.join(output_root, "PDF")
    png_dir = os.path.join(output_root, "PNG")
    combined_pdf_path = os.path.join(output_root, "All_15_Certificates_Combined.pdf")
    zip_path = os.path.join(base_dir, "Certificates_New.zip")

    # 1. Clean / create output directories
    if os.path.exists(output_root):
        shutil.rmtree(output_root)
    os.makedirs(per_person_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(png_dir, exist_ok=True)

    # 2. Load names from Excel
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb.active

    records = []
    for r in range(1, sheet.max_row + 1):
        val = sheet.cell(r, 1).value
        if val is not None and str(val).strip():
            name_str = str(val).strip()
            # If header row exists
            if r == 1 and name_str.lower() in ["name", "full name", "names"]:
                continue
            records.append((r, name_str))

    total_records = len(records)
    print(f"Loaded {total_records} names from '{excel_path}'")

    # 3. Clean Master Template (remove placeholder name 'Azharul Islam')
    if not os.path.exists(master_pdf_path):
        raise FileNotFoundError(f"Master PDF not found: {master_pdf_path}")

    master_doc = fitz.open(master_pdf_path)
    stream_18 = master_doc.xref_stream(18).decode("latin1")
    lines = stream_18.split("\n")
    cleaned_lines = lines[:54] + lines[93:]
    master_doc.update_stream(18, "\n".join(cleaned_lines).encode("latin1"))

    # Font and styling
    font = fitz.Font(fontfile=font_path)
    base_fontsize = 75.448425
    color = (0.102, 0.1882, 0.3412)  # #1a3057 / rgb(26, 48, 87)
    base_y = 261.47937
    max_allowed_width = 430.0

    combined_doc = fitz.open()
    seen_filenames = {}
    generated_info = []

    print("\nGenerating certificates (PDF & PNG)...")
    for idx, (row_idx, name) in enumerate(records, start=1):
        # Calculate scaled font size if width exceeds underline limit
        text_len = font.text_length(name, fontsize=base_fontsize)
        fontsize = base_fontsize
        if text_len > max_allowed_width:
            fontsize = base_fontsize * (max_allowed_width / text_len)
            text_len = font.text_length(name, fontsize=fontsize)

        # Create single certificate
        doc_cert = fitz.open()
        doc_cert.insert_pdf(master_doc)
        page = doc_cert[0]

        # Center horizontally on page
        x = (page.rect.width - text_len) / 2.0
        y = base_y

        page.insert_font(fontname="AlexBrush", fontfile=font_path)
        page.insert_text((x, y), name, fontname="AlexBrush", fontsize=fontsize, color=color)

        # File and folder naming
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

        # 1. Per-person dedicated directory: Certificates_New/Per_Person/<Person_Name>/
        person_folder = os.path.join(per_person_dir, filename_base)
        os.makedirs(person_folder, exist_ok=True)
        person_pdf = os.path.join(person_folder, pdf_filename)
        person_png = os.path.join(person_folder, png_filename)

        # 2. Central PDF & PNG directories: Certificates_New/PDF/ and Certificates_New/PNG/
        all_pdf = os.path.join(pdf_dir, pdf_filename)
        all_png = os.path.join(png_dir, png_filename)

        # Save PDF files
        doc_cert.save(person_pdf)
        shutil.copy2(person_pdf, all_pdf)

        # Render 300 DPI high-quality PNG
        pix = page.get_pixmap(dpi=300)
        pix.save(person_png)
        shutil.copy2(person_png, all_png)

        # Add to combined multi-page PDF
        combined_doc.insert_pdf(doc_cert)
        doc_cert.close()

        generated_info.append({
            "idx": idx,
            "row": row_idx,
            "name": name,
            "folder": filename_base,
            "fontsize": round(fontsize, 2)
        })
        print(f"  [{idx:02d}/{total_records:02d}] Generated: {filename_base} (Font size: {fontsize:.2f}pt)")

    master_doc.close()

    # Save combined PDF
    print(f"\nSaving combined PDF to: {combined_pdf_path}")
    combined_doc.save(combined_pdf_path)
    combined_doc.close()

    # Create ZIP file for easy download / transfer
    print(f"Creating ZIP archive: {zip_path}")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_root):
            for file in files:
                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, base_dir)
                zipf.write(full_p, arcname=rel_p)

    print("\n==================== SUMMARY ====================")
    print(f"Total Certificates Generated: {total_records}")
    print(f"Root Output Folder: {output_root}")
    print(f"1. Per Person Folders: {per_person_dir} ({len(os.listdir(per_person_dir))} person folders)")
    print(f"2. Separate PDF Folder: {pdf_dir} ({len(os.listdir(pdf_dir))} PDFs)")
    print(f"3. Separate PNG Folder: {png_dir} ({len(os.listdir(png_dir))} PNGs)")
    print(f"4. Combined PDF: {combined_pdf_path}")
    print(f"5. Complete ZIP Package: {zip_path} ({os.path.getsize(zip_path) / (1024 * 1024):.2f} MB)")
    print("=================================================")

if __name__ == "__main__":
    generate_certificates()
