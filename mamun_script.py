import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import subprocess
import json
import fitz

# 1. Convert Unicode lines to Bijoy JSON via Node.js
node_script = """
const conv = require('@abdalgolabs/ansi-unicode-converter');
const fs = require('fs');

const l1 = "এই মর্মে প্রত্যায়ন করা যাচ্ছে যে, নং ২৪১৬৯৩৭ ল্যাঃ কর্পোঃ (টিবিভি) মোঃ ওবায়েদ উল্লাহ, ১১ আর্টিলারি ব্রিগেড,";
const l2_1 = "জাহাংগিরাবাদ সেনানিবাস। বয়স ৩২ বছর ০২ মাস ৫ দিন এবং উচ্চতা ০৫ ফুট ১১";
const l2_2 = " ইঞ্চি। উক্ত ব্যক্তির হাতের";
const l3 = "কব্জির বর্তমান অবস্থার পরিধি বিশেষজ্ঞ চিকিৎসক কর্তৃক পর্যবেক্ষণ করে ১৯ সেঃ মিঃ পাওয়া যায় বিধায় বর্তমান";
const l4 = "ওজন হতে অতিরিক্ত ১০ (দশ)পাউন্ড ওজন প্রাপ্য বলে মতামত প্রদান করা হলো।";

const data = {
    l1: conv.unicodeToBijoy(l1),
    l2_1: conv.unicodeToBijoy(l2_1),
    l2_2: conv.unicodeToBijoy(l2_2),
    l3: conv.unicodeToBijoy(l3),
    l4: conv.unicodeToBijoy(l4)
};
fs.writeFileSync('bijoy_lines.json', JSON.stringify(data), 'utf8');
"""
subprocess.run(["node", "-e", node_script], check=True)

with open('bijoy_lines.json', 'r', encoding='utf-8') as f:
    lines = json.load(f)

# 2. Load the base document image
img = cv2.imread('extracted_img.png')
h_img, w_img = img.shape[:2]

# 3. Clean the main body text area
# y: 240 to 442, x: 165 to 1420
img[240:442, 165:1420] = (255, 255, 255)

# 4. Clean CMH Savar. in the doctor's stamp
# y: 948 to 982, x: 1140 to 1340
img[948:982, 1140:1340] = (255, 255, 255)

# Convert to PIL Image for rendering
img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
draw = ImageDraw.Draw(img_pil)

# Fonts
font_size = 35
font_bn = ImageFont.truetype('C:/Windows/Fonts/SutonnyMJ.ttf', font_size)
font_half = ImageFont.truetype('C:/Windows/Fonts/times.ttf', font_size - 2)
font_stamp = ImageFont.truetype('C:/Windows/Fonts/timesbd.ttf', 21)

text_color = (25, 25, 25)
stamp_color = (45, 38, 62)

x_left = 170
x_right = 1408
target_width = x_right - x_left

# Baselines from original document analysis
y_positions = [247, 300, 350, 405]

def draw_justified_line(draw_obj, words, y_pos, target_w, start_x, font, color):
    word_widths = [draw_obj.textlength(w, font=font) for w in words]
    total_words_w = sum(word_widths)
    num_spaces = len(words) - 1
    space_width = (target_w - total_words_w) / num_spaces if num_spaces > 0 else 0
    
    curr_x = start_x
    for i, w in enumerate(words):
        draw_obj.text((curr_x, y_pos), w, font=font, fill=color)
        curr_x += word_widths[i] + space_width

# Line 1: Justified
words_l1 = lines['l1'].split(' ')
draw_justified_line(draw, words_l1, y_positions[0], target_width, x_left, font_bn, text_color)

# Line 2: Justified with fraction ½
words_l2_p1 = lines['l2_1'].split(' ')
words_l2_p2 = lines['l2_2'].strip().split(' ')

w_p1_words = [draw.textlength(w, font=font_bn) for w in words_l2_p1[:-1]]
w_last_p1 = draw.textlength(words_l2_p1[-1], font=font_bn)
w_half = draw.textlength('½', font=font_half)
w_p2_words = [draw.textlength(w, font=font_bn) for w in words_l2_p2]

compound_w = w_last_p1 + w_half
all_token_widths = w_p1_words + [compound_w] + w_p2_words
total_l2_tokens_w = sum(all_token_widths)
num_l2_spaces = len(all_token_widths) - 1
space_l2_w = (target_width - total_l2_tokens_w) / num_l2_spaces

curr_x = x_left
for i, w in enumerate(words_l2_p1[:-1]):
    draw.text((curr_x, y_positions[1]), w, font=font_bn, fill=text_color)
    curr_x += w_p1_words[i] + space_l2_w

draw.text((curr_x, y_positions[1]), words_l2_p1[-1], font=font_bn, fill=text_color)
draw.text((curr_x + w_last_p1, y_positions[1]), '½', font=font_half, fill=text_color)
curr_x += compound_w + space_l2_w

for i, w in enumerate(words_l2_p2):
    draw.text((curr_x, y_positions[1]), w, font=font_bn, fill=text_color)
    curr_x += w_p2_words[i] + space_l2_w

# Line 3: Justified
words_l3 = lines['l3'].split(' ')
draw_justified_line(draw, words_l3, y_positions[2], target_width, x_left, font_bn, text_color)

# Line 4: Left-aligned
draw.text((x_left, y_positions[3]), lines['l4'], font=font_bn, fill=text_color)

# Doctor's stamp: draw CMH Bogura.
draw.text((1152, 952), 'CMH Bogura.', font=font_stamp, fill=stamp_color)

# Save final certificate image
final_img_path = 'updated_certificate.png'
img_pil.save(final_img_path, quality=98)
print('Successfully saved updated_certificate.png')

# Create matching PDF
doc_orig = fitz.open('Untitled-2.pdf')
orig_rect = doc_orig[0].rect
doc_orig.close()

doc_new = fitz.open()
new_page = doc_new.new_page(width=orig_rect.width, height=orig_rect.height)
new_page.insert_image(orig_rect, filename=final_img_path)
pdf_output_path = 'Untitled-2_Updated.pdf'
doc_new.save(pdf_output_path)
doc_new.close()
print(f'Successfully saved {pdf_output_path}')
