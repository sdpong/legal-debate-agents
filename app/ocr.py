import base64, io, os
import httpx
import fitz

class OcrError(RuntimeError): pass

async def read_with_vision(data: bytes, filename: str, mime_type: str | None = None) -> tuple[str, str]:
    """OCR images or PDF pages using an OpenAI-compatible vision endpoint."""
    base_url, key, model = os.getenv("OCR_AI_BASE_URL"), os.getenv("OCR_AI_API_KEY"), os.getenv("OCR_AI_MODEL")
    if not all([base_url, key, model]):
        raise OcrError("OCR AI is not configured; set OCR_AI_BASE_URL, OCR_AI_API_KEY and OCR_AI_MODEL on the server")
    images: list[tuple[str, bytes]] = []
    if filename.lower().endswith(".pdf"):
        pdf = fitz.open(stream=data, filetype="pdf")
        for page in list(pdf)[:10]: images.append(("image/png", page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).tobytes("png")))
    else:
        images = [(mime_type or "image/jpeg", data)]
    content = [{"type":"text","text":"Extract all readable text exactly. Preserve page order. Do not infer missing content."}]
    for content_type, image in images:
        content.append({"type":"image_url","image_url":{"url":f"data:{content_type};base64,{base64.b64encode(image).decode()}"}})
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(f"{base_url.rstrip('/')}/chat/completions", headers={"Authorization":f"Bearer {key}"}, json={"model":model,"temperature":0,"messages":[{"role":"user","content":content}]})
        response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"], f"ocr_pages=1-{len(images)}"
