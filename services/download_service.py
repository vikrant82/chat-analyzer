import textwrap
from io import BytesIO
from fpdf import FPDF
import zipfile
import json
import base64
from typing import List, Dict, Any
from clients.base_client import Message as StandardMessage

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

def create_pdf(text: str, chat_id: str) -> BytesIO:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Chat History: {chat_id}", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=10)
    safe_text = _break_long_words(text.encode('latin-1', 'replace').decode('latin-1'), 80)
    pdf.multi_cell(0, 5, safe_text)
    
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