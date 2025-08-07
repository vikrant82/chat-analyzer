from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from services import download_service
from clients.factory import get_client
from clients.base_client import Message as StandardMessage
from services.auth_service import get_current_user_id

class DownloadRequest(BaseModel):
    chatId: str
    startDate: str
    endDate: str
    enableCaching: bool
    format: str  # 'pdf' | 'txt' | 'html' | 'zip'
    imageProcessing: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = None

router = APIRouter()

@router.post("/download")
async def download_chat(req: DownloadRequest, user_id: str = Depends(get_current_user_id), backend: str = Query(...)):
    chat_client = get_client(backend)

    default_img_settings = {
        "enabled": True,
        "max_size_bytes": 5 * 1024 * 1024,
        "allowed_mime_types": ["image/png", "image/jpeg", "image/gif", "image/webp"]
    }
    per_req_img = req.imageProcessing or {}
    final_img_settings = {**default_img_settings, **per_req_img}

    messages_list: List[StandardMessage] = await chat_client.get_messages(
        user_id,
        req.chatId,
        req.startDate,
        req.endDate,
        enable_caching=req.enableCaching,
        image_processing_settings=final_img_settings,
        timezone_str=req.timezone
    )

    if not messages_list:
        raise HTTPException(status_code=404, detail="No messages found in the selected date range.")

    def ext_from_mime(mime: str) -> str:
        if mime == "image/jpeg": return "jpg"
        if mime == "image/png": return "png"
        if mime == "image/gif": return "gif"
        if mime == "image/webp": return "webp"
        return "bin"

    transcript_lines: List[str] = []
    in_thread = False
    image_items: List[Dict[str, Any]] = []
    img_seq = 0

    for msg in messages_list:
        is_reply = msg.thread_id is not None

        if is_reply and not in_thread:
            transcript_lines.append("\n--- Thread Started ---")
            in_thread = True
        elif not is_reply and in_thread:
            transcript_lines.append("--- Thread Ended ---\n")
            in_thread = False

        prefix = "    " if is_reply else ""
        header = f"{prefix}[{msg.author.name} at {msg.timestamp}]:"
        if msg.text:
            transcript_lines.append(f"{header} {msg.text}")
        else:
            transcript_lines.append(f"{header}")

        if msg.attachments:
            for att in msg.attachments:
                img_seq += 1
                filename = f"images/img-{img_seq}.{ext_from_mime(att.mime_type)}"
                transcript_lines.append(
                    f"{prefix}(Image #{img_seq}: {att.mime_type}; author={msg.author.name}; at={msg.timestamp}; file={filename})"
                )
                image_items.append({
                    "seq": img_seq,
                    "filename": filename,
                    "mime": att.mime_type,
                    "author": msg.author.name,
                    "timestamp": str(msg.timestamp),
                    "thread": bool(msg.thread_id),
                    "data_base64": att.data,
                })

    if in_thread:
        transcript_lines.append("--- Thread Ended ---")

    text_body = "\n".join(transcript_lines)

    if req.format == "txt":
        file_content = download_service.create_txt(text_body)
        return StreamingResponse(
            iter([file_content]),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=\"{req.chatId}_{req.startDate}_to_{req.endDate}.txt\""}
        )

    if req.format == "pdf":
        pdf_buffer = download_service.create_pdf(text_body, req.chatId)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=\"{req.chatId}_{req.startDate}_to_{req.endDate}.pdf\""}
        )

    if req.format == "html":
        html_text = download_service.create_html(messages_list, image_items, req.dict(), embed_images_as_data_uri=True)
        return StreamingResponse(
            iter([html_text.encode('utf-8')]),
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=\"{req.chatId}_{req.startDate}_to_{req.endDate}.html\""}
        )

    if req.format == "zip":
        html_for_zip = download_service.create_html(messages_list, image_items, req.dict(), embed_images_as_data_uri=False)
        zip_buffer = download_service.create_zip(text_body, html_for_zip, image_items)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=\"{req.chatId}_{req.startDate}_to_{req.endDate}.zip\""}
        )

    raise HTTPException(status_code=400, detail=f"Unsupported format: {req.format}")