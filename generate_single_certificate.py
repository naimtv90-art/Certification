import os
import shutil
import pymupdf as fitz

def generate_certificate_for(name="Md Adib Ibne Yousuf"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    master_pdf_path = os.path.join(base_dir, "AI4BT Global Summit 2026 certificate.pdf")
    font_path = os.path.join(base_dir, "AlexBrush-Regular.ttf")

    if not os.path.exists(master_pdf_path):
        raise FileNotFoundError(f"Master PDF not found: {master_pdf_path}")
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font file not found: {font_path}")

    # Prepare master template by cleanly stripping placeholder name
    master_doc = fitz.open(master_pdf_path)
    stream_18 = master_doc.xref_stream(18).decode("latin1")
    lines = stream_18.split("\n")
    cleaned_lines = lines[:54] + lines[93:]
    master_doc.update_stream(18, "\n".join(cleaned_lines).encode("latin1"))

    # Font properties
    font = fitz.Font(fontfile=font_path)
    base_fontsize = 75.448425
    color = (0.102, 0.1882, 0.3412)  # #1a3057 / rgb(26, 48, 87)
    base_y = 261.47937
    max_allowed_width = 430.0

    # Auto-scale font size if needed
    text_len = font.text_length(name, fontsize=base_fontsize)
    fontsize = base_fontsize
    if text_len > max_allowed_width:
        fontsize = base_fontsize * (max_allowed_width / text_len)
        text_len = font.text_length(name, fontsize=fontsize)

    # Create certificate document
    doc_cert = fitz.open()
    doc_cert.insert_pdf(master_doc)
    page = doc_cert[0]

    # Center text horizontally
    x = (page.rect.width - text_len) / 2.0
    y = base_y

    page.insert_font(fontname="AlexBrush", fontfile=font_path)
    page.insert_text((x, y), name, fontname="AlexBrush", fontsize=fontsize, color=color)

    # Target folder: Dedicated folder in root (matching "A B M Ahsan Al Mamun" structure)
    dedicated_dir = os.path.join(base_dir, name)
    os.makedirs(dedicated_dir, exist_ok=True)
    dedicated_pdf = os.path.join(dedicated_dir, f"{name}.pdf")
    dedicated_png = os.path.join(dedicated_dir, f"{name}.png")

    # Save PDF
    doc_cert.save(dedicated_pdf)

    # Render 300 DPI high-quality PNG
    pix = page.get_pixmap(dpi=300)
    pix.save(dedicated_png)

    # Also save to root directory
    root_pdf = os.path.join(base_dir, f"{name}.pdf")
    root_png = os.path.join(base_dir, f"{name}.png")
    shutil.copy2(dedicated_pdf, root_pdf)
    shutil.copy2(dedicated_png, root_png)

    # Also update Certificates_New structure
    cert_new_dir = os.path.join(base_dir, "Certificates_New")
    if os.path.exists(cert_new_dir):
        # Per_Person
        per_person_folder = os.path.join(cert_new_dir, "Per_Person", name)
        os.makedirs(per_person_folder, exist_ok=True)
        shutil.copy2(dedicated_pdf, os.path.join(per_person_folder, f"{name}.pdf"))
        shutil.copy2(dedicated_png, os.path.join(per_person_folder, f"{name}.png"))

        # Central PDF & PNG folders
        pdf_folder = os.path.join(cert_new_dir, "PDF")
        png_folder = os.path.join(cert_new_dir, "PNG")
        if os.path.exists(pdf_folder):
            shutil.copy2(dedicated_pdf, os.path.join(pdf_folder, f"{name}.pdf"))
        if os.path.exists(png_folder):
            shutil.copy2(dedicated_png, os.path.join(png_folder, f"{name}.png"))

    doc_cert.close()
    master_doc.close()

    print(f"Successfully generated certificate for: '{name}'")
    print(f"Font size: {fontsize:.2f} pt, X: {x:.2f}, Y: {y:.2f}, Text width: {text_len:.2f}")
    print(f"Saved PDF to: {dedicated_pdf}")
    print(f"Saved PNG to: {dedicated_png}")
    print(f"Also copied to root: {root_pdf} and {root_png}")

if __name__ == "__main__":
    import sys
    target_name = sys.argv[1] if len(sys.argv) > 1 else "Md Azizur Rahman"
    generate_certificate_for(target_name)
