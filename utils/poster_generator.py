"""
Utility functions for generating missing child posters
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import qrcode
from io import BytesIO
import os
import requests

def generate_missing_poster(missing_child, base_url="https://sachet.onrender.com"):
    """
    Generate a professional missing child poster with photo, details, and QR code
    
    Args:
        missing_child: MissingChild database object
        base_url: Base URL for QR code generation
    
    Returns:
        PIL Image object
    """
    # Create canvas (A4 size: 2480x3508 pixels at 300 DPI)
    width, height = 2480, 3508
    poster = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(poster)
    
    # Colors
    RED = (220, 53, 69)
    BLACK = (0, 0, 0)
    GRAY = (108, 117, 125)
    
    try:
        # Try to use custom fonts, fallback to default if not available
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 180)
        header_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 100)
        body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 70)
        detail_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
    except:
        # Fallback to default font
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        detail_font = ImageFont.load_default()
    
    # 1. MISSING Header (Red background)
    draw.rectangle([(0, 0), (width, 300)], fill=RED)
    title_text = "MISSING"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_width) // 2, 80), title_text, fill='white', font=title_font)
    
    # 2. Child Photo
    y_offset = 350
    photo_size = 1200
    
    if missing_child.photo_filename:
        try:
            # Download or load photo
            if missing_child.photo_filename.startswith('http'):
                response = requests.get(missing_child.photo_filename, timeout=10)
                child_photo = Image.open(BytesIO(response.content))
            else:
                photo_path = os.path.join('static', 'uploads', missing_child.photo_filename)
                child_photo = Image.open(photo_path)
            
            # Resize and center photo
            child_photo.thumbnail((photo_size, photo_size), Image.Resampling.LANCZOS)
            
            # Add border
            bordered_photo = Image.new('RGB', (photo_size + 20, photo_size + 20), RED)
            photo_x = (photo_size + 20 - child_photo.width) // 2
            photo_y = (photo_size + 20 - child_photo.height) // 2
            bordered_photo.paste(child_photo, (photo_x, photo_y))
            
            # Paste on poster
            poster_x = (width - bordered_photo.width) // 2
            poster.paste(bordered_photo, (poster_x, y_offset))
            y_offset += bordered_photo.height + 80
        except Exception as e:
            print(f"Error loading photo: {e}")
            # Draw placeholder
            draw.rectangle([(640, y_offset), (1840, y_offset + photo_size)], outline=RED, width=10)
            draw.text((width // 2 - 200, y_offset + photo_size // 2), "Photo Not Available", 
                     fill=GRAY, font=body_font)
            y_offset += photo_size + 80
    else:
        # No photo available
        draw.rectangle([(640, y_offset), (1840, y_offset + photo_size)], outline=RED, width=10)
        draw.text((width // 2 - 200, y_offset + photo_size // 2), "Photo Not Available", 
                 fill=GRAY, font=body_font)
        y_offset += photo_size + 80
    
    # 3. Child Details
    details = [
        ("Name:", missing_child.name),
        ("Age:", f"{missing_child.age} years old"),
        ("Gender:", missing_child.gender),
        ("Last Seen:", missing_child.last_seen_location),
    ]
    
    if missing_child.location_subcategory:
        details.append(("Specific Location:", missing_child.location_subcategory))
    
    for label, value in details:
        # Label
        draw.text((200, y_offset), label, fill=RED, font=header_font)
        y_offset += 120
        
        # Value (wrap text if too long)
        max_width = width - 400
        wrapped_text = wrap_text(value, detail_font, max_width, draw)
        for line in wrapped_text:
            draw.text((200, y_offset), line, fill=BLACK, font=detail_font)
            y_offset += 80
        
        y_offset += 40
    
    # 4. Description
    draw.text((200, y_offset), "Description:", fill=RED, font=header_font)
    y_offset += 120
    
    desc_lines = wrap_text(missing_child.description, detail_font, width - 400, draw)
    for line in desc_lines[:5]:  # Limit to 5 lines
        draw.text((200, y_offset), line, fill=BLACK, font=detail_font)
        y_offset += 80
    
    y_offset += 100
    
    # 5. QR Code
    case_url = f"{base_url}/case/{missing_child.report_id}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(case_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=BLACK, back_color="white")
    qr_img = qr_img.resize((400, 400))
    
    # Center QR code
    qr_x = (width - 400) // 2
    poster.paste(qr_img, (qr_x, y_offset))
    y_offset += 450
    
    # QR code label
    qr_text = "Scan for more information"
    qr_bbox = draw.textbbox((0, 0), qr_text, font=body_font)
    qr_text_width = qr_bbox[2] - qr_bbox[0]
    draw.text(((width - qr_text_width) // 2, y_offset), qr_text, fill=GRAY, font=body_font)
    y_offset += 100
    
    # 6. Contact Information
    draw.text((200, y_offset), "If you have any information, please contact:", 
             fill=RED, font=header_font)
    y_offset += 120
    
    contact_text = missing_child.emergency_contact
    contact_bbox = draw.textbbox((0, 0), contact_text, font=body_font)
    contact_width = contact_bbox[2] - contact_bbox[0]
    draw.text(((width - contact_width) // 2, y_offset), contact_text, fill=BLACK, font=body_font)
    y_offset += 100
    
    # 7. Report ID (small, bottom)
    report_text = f"Report ID: {missing_child.report_id}"
    draw.text((200, height - 150), report_text, fill=GRAY, font=detail_font)
    
    return poster


def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within max_width"""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines
