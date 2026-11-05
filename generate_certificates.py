import os
import zipfile
import shutil
import openpyxl
import fitz  # PyMuPDF

def generate_certificates(excel_filename="27Sun-2PM (1).xlsx", output_folder_name="Certificates"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    master_pdf_path = os.path.join(base_dir, "AI4BT Global Summit 2026 certificate.pdf")
    excel_path = os.path.join(base_dir, excel_filename)
    font_path = os.path.join(base_dir, "AlexBrush-Regular.ttf")
    output_dir = os.path.join(base_dir, output_folder_name)
    zip_output_path = os.path.join(base_dir, f"{output_folder_name}.zip")

    # 1. Ensure clean output directory
    if os.path.exists(output_dir):
        # Clean previous generated files in folder
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # 2. Load names from Excel
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb.active

    names = []
    skipped = []

    # Read rows
    for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        # Extract first non-empty cell
        row_vals = [c for c in row if c is not None and str(c).strip()]
        if not row_vals:
            continue
        
        name_val = str(row_vals[0]).strip()
        # Skip header if it says 'Full Name' or 'Name'
        if row_idx == 1 and name_val.lower() in ["full name", "name", "names"]:
            continue

        if not name_val:
            skipped.append((row_idx, "Empty or whitespace-only name"))
            continue

        names.append((row_idx, name_val))

    print(f"Total valid names found in '{excel_filename}': {len(names)}")
    if skipped:
        print(f"Skipped rows ({len(skipped)}): {skipped}")

    # 3. Prepare Master Template with clean removal of placeholder name
    if not os.path.exists(master_pdf_path):
        raise FileNotFoundError(f"Master PDF not found: {master_pdf_path}")

    master_doc = fitz.open(master_pdf_path)
    
    # In master PDF, xref 18 contains Form XObject X54 where lines 69-106 draw 'Azharul Islam'
    # Removing lines 69 to 106 leaves all vector art, underlines, logos, and surrounding text 100% pristine.
    stream_18 = master_doc.xref_stream(18).decode("latin1")
    lines = stream_18.split("\n")
    cleaned_lines = lines[:69] + lines[107:]
    master_doc.update_stream(18, "\n".join(cleaned_lines).encode("latin1"))

    # Font properties matching master PDF
    font = fitz.Font(fontfile=font_path)
    base_fontsize = 75.448425
    color = (0.102, 0.1882, 0.3412)  # Master color: #1a3057 / rgb(26, 48, 87)
    base_y = 261.47937               # Master baseline y-coordinate
    # Underline is from x=192.89 to x=649.00 (width=456.12 pt).
    # Setting max_allowed_width to 430.0 guarantees names never extend past the underline.
    max_allowed_width = 430.0

    generated_pdfs = []
    failed_names = []
    seen_filenames = {}

    # Combined PDF containing all certificates in order
    combined_pdf_path = os.path.join(output_dir, "All_Certificates.pdf")
    combined_doc = fitz.open()

    for idx, (row_idx, name) in enumerate(names, start=1):
        try:
            # Auto-fit scaling to guarantee name stays inside underline
            text_len = font.text_length(name, fontsize=base_fontsize)
            fontsize = base_fontsize
            if text_len > max_allowed_width:
                fontsize = base_fontsize * (max_allowed_width / text_len)
                text_len = font.text_length(name, fontsize=fontsize)

            # Create document for this certificate
            doc_cert = fitz.open()
            doc_cert.insert_pdf(master_doc)
            page = doc_cert[0]

            # Center horizontally on page
            x = (page.rect.width - text_len) / 2.0
            y = base_y

            # Insert font and text
            page.insert_font(fontname="AlexBrush", fontfile=font_path)
            page.insert_text((x, y), name, fontname="AlexBrush", fontsize=fontsize, color=color)

            # Add to combined document
            combined_doc.insert_pdf(doc_cert)

            # File naming: exact name as in Excel + .pdf
            # Strip invalid characters for Windows filesystem: <>:"/\|?*
            clean_name = "".join(c for c in name if c not in '<>:"/\\|?*').strip()
            
            # Handle duplicate names by appending (2), (3), etc. so all individual files are kept
            if clean_name in seen_filenames:
                seen_filenames[clean_name] += 1
                filename = f"{clean_name} ({seen_filenames[clean_name]}).pdf"
            else:
                seen_filenames[clean_name] = 1
                filename = f"{clean_name}.pdf"

            output_pdf_path = os.path.join(output_dir, filename)
            doc_cert.save(output_pdf_path)
            doc_cert.close()

            generated_pdfs.append((name, output_pdf_path, filename))
            if idx % 50 == 0 or idx == len(names):
                print(f"[{idx}/{len(names)}] Generated: {filename}")
        except Exception as e:
            failed_names.append((row_idx, name, str(e)))
            print(f"Error processing row {row_idx} ({name}): {e}")

    master_doc.close()

    # Save combined PDF
    print(f"\nSaving combined PDF ({len(generated_pdfs)} pages): {combined_pdf_path}")
    combined_doc.save(combined_pdf_path)
    combined_doc.close()

    # Also keep a copy of All_Certificates.pdf in base_dir for convenience
    shutil.copy2(combined_pdf_path, os.path.join(base_dir, "All_Certificates.pdf"))

    # 4. Create ZIP archive of the entire Certificates folder
    print(f"Creating ZIP file: {zip_output_path}")
    with zipfile.ZipFile(zip_output_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, output_dir)
                zipf.write(full_p, arcname=os.path.join(output_folder_name, rel_p))

    print("\n================== SUMMARY ==================")
    print(f"Excel Source: {excel_filename}")
    print(f"Total Names Processed: {len(generated_pdfs)}")
    print(f"Combined PDF: {combined_pdf_path} ({len(generated_pdfs)} pages)")
    print(f"Individual PDFs Folder: {output_dir}")
    print(f"Total Individual PDFs in Folder: {len(generated_pdfs)}")
    print(f"Failed / Skipped: {len(failed_names) + len(skipped)}")
    print(f"ZIP Archive: {zip_output_path} ({os.path.getsize(zip_output_path) / (1024*1024):.2f} MB)")
    print("=============================================")

    return generated_pdfs, failed_names, skipped

if __name__ == "__main__":
    generate_certificates("27Sun-2PM (1).xlsx", "Certificates")
