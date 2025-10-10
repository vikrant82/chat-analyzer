import textwrap
from io import BytesIO
from fpdf import FPDF
import zipfile
import json
import base64
from typing import List, Dict, Any
from clients.base_client import Message as StandardMessage
from PIL import Image
import tempfile
import os

def _break_long_words(text: str, max_len: int) -> str:
    """Inserts spaces into words longer than max_len to allow for line breaking."""
    words = text.split(' ')
    new_words = []
    for word in words:
        if len(word) > max_len:
            new_words.append(' '.join(textwrap.wrap(word, max_len, break_long_words=True)))
        else:
            new_words.append(word)
    return ' '.join(new_words)

def create_pdf(messages_list: List[StandardMessage], image_items: List[Dict[str, Any]], chat_id: str, date_range: str) -> BytesIO:
    """
    Create a PDF with text and embedded images.
    
    Args:
        messages_list: List of message objects
        image_items: List of image data dictionaries with base64 encoded images
        chat_id: Chat identifier
        date_range: Date range string for display
    
    Returns:
        BytesIO buffer containing the PDF
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Chat History: {chat_id}", 0, 1, 'C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 5, f"Date Range: {date_range}", 0, 1, 'C')
    pdf.ln(5)
    
    # Create a lookup for images by sequence number
    img_lookup = {item["seq"]: item for item in image_items}
    current_img_seq = 0
    in_thread = False
    
    for msg in messages_list:
        is_reply = msg.thread_id is not None
        
        # Thread markers
        if is_reply and not in_thread:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 5, "--- Thread Started ---", 0, 1)
            in_thread = True
        elif not is_reply and in_thread:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 5, "--- Thread Ended ---", 0, 1)
            pdf.ln(3)
            in_thread = False
        
        # Message header
        pdf.set_font("Arial", 'B', 10)
        indent = 10 if is_reply else 0
        pdf.set_x(10 + indent)
        header_text = f"{msg.author.name} at {msg.timestamp}"
        safe_header = header_text.encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 5, safe_header, 0, 1)
        
        # Message text
        if msg.text:
            pdf.set_font("Arial", size=10)
            pdf.set_x(10 + indent)
            safe_text = _break_long_words(msg.text.encode('latin-1', 'replace').decode('latin-1'), 80)
            # Use multi_cell for text wrapping
            x_pos = pdf.get_x()
            y_pos = pdf.get_y()
            pdf.set_xy(x_pos, y_pos)
            # Split text into lines manually to maintain indent
            for line in safe_text.split('\n'):
                pdf.set_x(10 + indent)
                pdf.multi_cell(0, 5, line)
        
        # Embed images if present
        if msg.attachments:
            for att in msg.attachments:
                current_img_seq += 1
                item = img_lookup.get(current_img_seq)
                if not item:
                    continue
                
                try:
                    # Decode base64 image
                    img_data = base64.b64decode(item['data_base64'])
                    
                    # Create a temporary file for the image
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                        tmp_path = tmp_file.name
                        
                        # Convert image to a format FPDF can handle
                        img = Image.open(BytesIO(img_data))
                        
                        # Convert RGBA to RGB if necessary
                        if img.mode in ('RGBA', 'LA', 'P'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                            img = background
                        
                        # Save as PNG
                        img.save(tmp_path, 'PNG')
                    
                    try:
                        # Calculate image dimensions to fit on page
                        # Max width: 180mm (leaving margins), Max height: 100mm
                        max_width = 180
                        max_height = 100
                        
                        img_width_mm = img.width * 0.264583  # Convert pixels to mm (96 DPI)
                        img_height_mm = img.height * 0.264583
                        
                        # Scale down if too large
                        scale = min(max_width / img_width_mm, max_height / img_height_mm, 1.0)
                        final_width = img_width_mm * scale
                        final_height = img_height_mm * scale
                        
                        # Check if we need a new page
                        if pdf.get_y() + final_height > pdf.page_break_trigger:
                            pdf.add_page()
                        
                        pdf.set_x(10 + indent)
                        # Add image caption
                        pdf.set_font("Arial", 'I', 8)
                        pdf.cell(0, 4, f"[Image #{current_img_seq}]", 0, 1)
                        
                        # Add the image
                        pdf.image(tmp_path, x=10 + indent, w=final_width)
                        pdf.ln(2)
                        
                    finally:
                        # Clean up temp file
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                    
                except Exception as e:
                    # If image embedding fails, add a placeholder text
                    pdf.set_font("Arial", 'I', 9)
                    pdf.set_x(10 + indent)
                    error_msg = f"[Image #{current_img_seq} - Could not embed: {str(e)[:50]}]"
                    pdf.cell(0, 5, error_msg.encode('latin-1', 'replace').decode('latin-1'), 0, 1)
        
        pdf.ln(3)  # Space between messages
    
    if in_thread:
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, "--- Thread Ended ---", 0, 1)
    
    pdf_bytes = pdf.output(dest='S')
    output = BytesIO(pdf_bytes)
    output.seek(0)
    return output

def create_txt(text_body: str) -> bytes:
    return text_body.encode('utf-8')

def create_html(messages_list: List[StandardMessage], image_items: List[Dict[str, Any]], req: Dict[str, Any], embed_images_as_data_uri: bool) -> str:
    def escape_html(s: str) -> str:
        return (s.replace("&", "&").replace("<", "<").replace(">", ">"))

    html_lines: List[str] = []
    html_lines.append("<!DOCTYPE html>")
    html_lines.append("<html><head><meta charset='utf-8'><title>Chat Export</title>")
    html_lines.append("<style>body{font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.4} .msg{margin:6px 0} .reply{margin-left:1.5em;border-left:2px solid #ddd;padding-left:0.75em} .meta{color:#555} img{max-width:100%;height:auto;margin:4px 0;border:1px solid #eee;border-radius:4px}</style>")
    html_lines.append("</head><body>")
    html_lines.append(f"<h2>Chat Export: {escape_html(req['chatId'])}</h2>")
    html_lines.append(f"<p class='meta'>Range: {escape_html(req['startDate'])} to {escape_html(req['endDate'])}</p>")

    in_thread_html = False
    img_lookup = {item["seq"]: item for item in image_items}
    current_img_seq = 0

    for msg in messages_list:
        is_reply = msg.thread_id is not None
        if is_reply and not in_thread_html:
            html_lines.append("<hr><p><strong>--- Thread Started ---</strong></p>")
            in_thread_html = True
        elif not is_reply and in_thread_html:
            html_lines.append("<p><strong>--- Thread Ended ---</strong></p><hr>")
            in_thread_html = False

        div_class = "msg reply" if is_reply else "msg"
        author = escape_html(msg.author.name)
        ts = escape_html(str(msg.timestamp))
        text_html = escape_html(msg.text or "")
        html_lines.append(f"<div class='{div_class}'><div class='meta'><strong>{author}</strong> <em>{ts}</em></div>")
        if text_html:
            html_lines.append(f"<div>{text_html}</div>")

        if msg.attachments:
            for att in msg.attachments:
                current_img_seq += 1
                item = img_lookup.get(current_img_seq)
                if not item:
                    continue
                if embed_images_as_data_uri:
                    html_lines.append(f"<div><img src='data:{item['mime']};base64,{item['data_base64']}' alt='Image #{item['seq']}'/></div>")
                else:
                    html_lines.append(f"<div><img src='{escape_html(item['filename'])}' alt='Image #{item['seq']}'/></div>")
        html_lines.append("</div>")

    if in_thread_html:
        html_lines.append("<p><strong>--- Thread Ended ---</strong></p>")

    html_lines.append("</body></html>")
    return "\n".join(html_lines)

def create_zip(text_body: str, html_body: str, image_items: List[Dict[str, Any]]) -> BytesIO:
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("transcript.txt", text_body.encode('utf-8'))
        zf.writestr("transcript_with_images.html", html_body.encode('utf-8'))

        for item in image_items:
            try:
                raw = base64.b64decode(item["data_base64"])
            except Exception:
                raw = b""
            zf.writestr(item["filename"], raw)

        manifest = [{
            "seq": it["seq"],
            "filename": it["filename"],
            "mime": it["mime"],
            "author": it["author"],
            "timestamp": it["timestamp"],
            "thread": it["thread"]
        } for it in image_items]
        zf.writestr("manifest.json", json.dumps(manifest, indent=2).encode('utf-8'))

    buf.seek(0)
    return buf