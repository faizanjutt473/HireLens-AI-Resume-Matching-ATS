import io
import itertools
import re
import zlib
from datetime import datetime, timedelta, timezone

import numpy as np

JOB = {
    "title": "Backend Engineer",
    "description": "Build and maintain Flask APIs backed by PostgreSQL for our hiring platform.",
    "location": "Remote",
    "job_type": "Full-time",
    "experience_level": "Mid",
    "skills": ["Python", "Flask", "PostgreSQL"],
}

GOOD_RESUME = (
    "Backend developer with five years of experience. Skills: Python, Flask, PostgreSQL, "
    "Docker, Redis and REST API design for hiring platforms."
)
BAD_RESUME = (
    "Pastry chef with ten years of experience baking cakes, bread and desserts "
    "in busy bakeries across the city."
)

_n = itertools.count(1)


def unique_email(prefix="user"):
    return f"{prefix}{next(_n)}@example.com"


def fake_embed(text, **kwargs):
    """Asli model ki jagah: words ko 64 buckets mein hash karke normalize vector."""
    vec = np.zeros(64)
    for word in re.findall(r"[a-z0-9+#.]+", (text or "").lower()):
        vec[zlib.crc32(word.encode()) % 64] += 1.0
    norm = np.linalg.norm(vec)
    return (vec / norm if norm else vec).tolist()


def docx_bytes(text):
    from docx import Document

    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def pdf_bytes(lines):
    content = "BT /F1 12 Tf 72 720 Td 16 TL\n" + "\n".join(f"({l}) Tj T*" for l in lines) + "\nET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{obj}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    ).encode()
    return out


def upload(client, headers, data, name="resume.docx"):
    return client.post(
        "/api/resumes",
        data={"file": (io.BytesIO(data), name)},
        headers=headers,
        content_type="multipart/form-data",
    )


def post_job(client, employer, **over):
    r = client.post("/api/jobs", json={**JOB, **over}, headers=employer["headers"])
    assert r.status_code == 201, r.get_json()
    return r.get_json()["job"]


def apply_new(make_user, client, job_id, resume_text=GOOD_RESUME):
    """Naya candidate banata hai, resume upload karta hai aur job par apply karta hai."""
    cand = make_user("candidate")
    assert upload(client, cand["headers"], docx_bytes(resume_text)).status_code == 201
    r = client.post("/api/applications", json={"job_id": job_id}, headers=cand["headers"])
    assert r.status_code == 201, r.get_json()
    return cand, r.get_json()["application"]


def set_stage(client, employer, app_id, stage):
    r = client.patch(
        f"/api/pipeline/applications/{app_id}/stage",
        json={"stage": stage},
        headers=employer["headers"],
    )
    assert r.status_code == 200, r.get_json()
    return r.get_json()["application"]


def future_iso(days=2):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()