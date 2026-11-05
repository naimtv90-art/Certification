import os
import zipfile
import shutil
import openpyxl
import fitz  # PyMuPDF

def generate_all():
    base_dir = r"d:\Certificate generator"
    master_pdf_path = os.path.join(base_dir, "AI4BT Global Summit 2026 certificate.pdf")
    excel_path = os.path.join(base_dir, "27Sun-2PM.xlsx")
    font_path = os.path.join(base_dir, "AlexBrush-Regular.ttf")

    # Output paths strictly per prompt specifications
    combined_pdf_path = os.path.join(base_dir, "All_Names_Combined.pdf")
    zip_output_path = os.path.join(base_dir, "Individual_PDFs.zip")
    individual_dir = os.path.join(base_dir, "Individual_PDFs")

    # Clean previous individual PDFs folder
    if os.path.exists(individual_dir):
        for f in os.listdir(individual_dir):
            file_path = os.path.join(individual_dir, f)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Warning cleaning {file_path}: {e}")
    else:
        os.makedirs(individual_dir, exist_ok=True)

    # 1. Load names from Excel (AI4BT Registrations sheet)
    print(f"Loading names from Excel: {excel_path}")
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb["AI4BT Registrations"]

    records = []
    # Read rows from row 2 (skipping row 1 header)
    for row_idx in range(2, sheet.max_row + 1):
        reg_id = sheet.cell(row_idx, 1).value
        name_val = sheet.cell(row_idx, 2).value
        if name_val is not None and str(name_val).strip():
            raw_name = str(name_val).strip()
            records.append((row_idx, str(reg_id).strip() if reg_id else "", raw_name))

    total_names = len(records)
    print(f"Total names loaded from Excel: {total_names}")

    # 2. Prepare Master Template
    if not os.path.exists(master_pdf_path):
        raise FileNotFoundError(f"Master PDF not found: {master_pdf_path}")

    master_doc = fitz.open(master_pdf_path)
    
    # In this Master PDF, xref 18 is Form XObject X46. Lines 54 to 92 draw 'Azharul Islam'.
    # Removing lines 54 to 92 cleanly leaves all graphics, logos, borders, and signatures untouched.
    stream_18 = master_doc.xref_stream(18).decode("latin1")
    lines = stream_18.split("\n")
    cleaned_lines = lines[:54] + lines[93:]
    master_doc.update_stream(18, "\n".join(cleaned_lines).encode("latin1"))

    # Font properties matching master template
    font = fitz.Font(fontfile=font_path)
    base_fontsize = 75.448425
    color = (0.102, 0.1882, 0.3412)  # #1a3057 / rgb(26, 48, 87)
    base_y = 261.47937               # Master baseline y-coordinate
    max_allowed_width = 430.0        # Fits cleanly within 456.12 pt underline with neat margin

    combined_doc = fitz.open()
    generated_individual = []
    seen_filenames = {}
    failed_names = []

    print("\nGenerating personalized PDFs...")
    for idx, (row_idx, reg_id, name) in enumerate(records, start=1):
        try:
            # Measure width and calculate proportional font size if text exceeds line boundary
            text_len = font.text_length(name, fontsize=base_fontsize)
            fontsize = base_fontsize
            if text_len > max_allowed_width:
                fontsize = base_fontsize * (max_allowed_width / text_len)
                text_len = font.text_length(name, fontsize=fontsize)

            # Create document for this certificate from cleaned master
            doc_cert = fitz.open()
            doc_cert.insert_pdf(master_doc)
            page = doc_cert[0]

            # Center horizontally on page
            x = (page.rect.width - text_len) / 2.0
            y = base_y

            # Insert exact name with AlexBrush font
            page.insert_font(fontname="AlexBrush", fontfile=font_path)
            page.insert_text((x, y), name, fontname="AlexBrush", fontsize=fontsize, color=color)

            # A. Add page to combined PDF
            combined_doc.insert_pdf(doc_cert)

            # B. Save individual PDF
            # Sanitize OS forbidden filename chars: <>:"/\|?*
            clean_filename_base = "".join(c for c in name if c not in '<>:"/\\|?*').strip()
            if not clean_filename_base:
                clean_filename_base = f"Certificate_{row_idx}"

            # If duplicate name exists in the list, number it so exactly 305 unique files are saved
            if clean_filename_base in seen_filenames:
                seen_filenames[clean_filename_base] += 1
                filename = f"{clean_filename_base} ({seen_filenames[clean_filename_base]}).pdf"
            else:
                seen_filenames[clean_filename_base] = 1
                filename = f"{clean_filename_base}.pdf"

            pdf_file_path = os.path.join(individual_dir, filename)
            doc_cert.save(pdf_file_path)
            doc_cert.close()

            generated_individual.append((name, pdf_file_path, filename))

            if idx % 50 == 0 or idx == total_names:
                print(f"  [{idx}/{total_names}] Created: {filename}")

        except Exception as e:
            failed_names.append((row_idx, name, str(e)))
            print(f"Error on row {row_idx} ({name}): {e}")

    master_doc.close()

    # Save A. All_Names_Combined.pdf
    print(f"\nSaving Combined PDF ({len(combined_doc)} pages): {combined_pdf_path}")
    combined_doc.save(combined_pdf_path)
    combined_doc.close()

    # Create B. Individual_PDFs.zip
    print(f"Creating ZIP archive: {zip_output_path}")
    with zipfile.ZipFile(zip_output_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for name, file_path, filename in generated_individual:
            zipf.write(file_path, arcname=filename)

    # Quality Control Verification
    print("\n================== QUALITY CONTROL VERIFICATION ==================")
    print(f"1. Total names in Excel: {total_names}")
    print(f"2. Total individual PDFs created: {len(generated_individual)}")
    print(f"3. Combined PDF pages count: {len(fitz.open(combined_pdf_path))}")
    print(f"4. Individual PDFs in folder: {len(os.listdir(individual_dir))}")
    with zipfile.ZipFile(zip_output_path, "r") as z:
        print(f"5. Individual PDFs in ZIP: {len(z.namelist())}")
    print(f"6. Failed / Unprocessed names: {len(failed_names)}")
    print(f"7. Combined PDF size: {os.path.getsize(combined_pdf_path) / (1024*1024):.2f} MB")
    print(f"8. ZIP archive size: {os.path.getsize(zip_output_path) / (1024*1024):.2f} MB")
    print("==================================================================")

    return total_names, len(generated_individual), total_names, failed_names

if __name__ == "__main__":
    generate_all()
