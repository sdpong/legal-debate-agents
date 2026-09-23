import hashlib
import json
import re
from pathlib import Path
from pypdf import PdfReader
from fastapi import UploadFile
from .models import Evidence

class EvidenceStore:
    def __init__(self, root: str = "data/evidence"):
        self.root = Path(root)

    @staticmethod
    def _safe_id(value: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", value)
        if not safe: raise ValueError("invalid case or evidence ID")
        return safe

    @staticmethod
    def redact(text: str) -> str:
        text = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[已脱敏手机号]", text)
        text = re.sub(r"(?<![0-9Xx])\d{17}[0-9Xx](?![0-9Xx])", "[已脱敏身份证号]", text)
        text = re.sub(r"(?<!\d)\d{16,19}(?!\d)", "[已脱敏账号]", text)
        return text

    @staticmethod
    def extract(data: bytes, filename: str) -> tuple[str, str]:
        if filename.lower().endswith(".pdf"):
            reader = PdfReader(__import__("io").BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(f"[p.{i + 1}] {page}" for i, page in enumerate(pages))
            return text, f"pages=1-{len(pages)}"
        return data.decode("utf-8", errors="replace"), "text"

    async def save(self, case_id: str, evidence_id: str, party: str, upload: UploadFile) -> Evidence:
        case_dir = self.root / self._safe_id(case_id)
        case_dir.mkdir(parents=True, exist_ok=True)
        data = await upload.read()
        if not data: raise ValueError("empty upload")
        digest = hashlib.sha256(data).hexdigest()
        original_name = Path(upload.filename or "upload.txt").name
        original_path = case_dir / f"{self._safe_id(evidence_id)}-{digest[:12]}-{original_name}"
        original_path.write_bytes(data)
        try:
            raw, locator = self.extract(data, original_name)
            status = "ready" if raw.strip() else "needs_ocr"
        except Exception:
            raw, locator, status = "", "unavailable", "needs_ocr"
        redacted = self.redact(raw)
        record = Evidence(evidence_id=evidence_id, name=original_name, party=party, text=redacted, locator=locator)
        manifest = {"sha256": digest, "original_filename": original_name, "stored_file": original_path.name,
                    "extraction_status": status, "record": record.model_dump()}
        (case_dir / f"{self._safe_id(evidence_id)}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        return record
