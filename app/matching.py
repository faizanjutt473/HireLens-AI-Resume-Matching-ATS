import numpy as np

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(text, chunk_words=180, max_chunks=8):
    """Lambe text ko chunks mein baant kar average vector banata hai (model ki 256 token limit ki wajah se)."""
    words = (text or "").split()
    chunks = [" ".join(words[i : i + chunk_words]) for i in range(0, len(words), chunk_words)]
    chunks = chunks[:max_chunks] or [""]
    vecs = _get_model().encode(chunks, normalize_embeddings=True)
    mean = np.mean(vecs, axis=0)
    mean = mean / (np.linalg.norm(mean) or 1.0)
    return mean.tolist()


def job_vector(job):
    if not job.embedding:
        text = f"{job.title}. {', '.join(job.skills or [])}. {job.description}"
        job.embedding = embed(text)
    return np.array(job.embedding)


def resume_vector(resume):
    if not resume.embedding:
        resume.embedding = embed(resume.raw_text)
    return np.array(resume.embedding)


def match_score(job, resume):
    """Score 0-100: 60% semantic similarity + 40% required-skills overlap."""
    cosine = float(np.dot(job_vector(job), resume_vector(resume)))
    semantic = min(max((cosine - 0.15) / 0.55, 0.0), 1.0)

    required = {s.lower(): s for s in (job.skills or [])}
    have = {s.lower() for s in (resume.skills or [])}
    matched = [name for key, name in required.items() if key in have]
    missing = [name for key, name in required.items() if key not in have]

    total = 0.6 * semantic + 0.4 * (len(matched) / len(required)) if required else semantic
    return round(total * 100, 1), matched, missing