# HireLens: AI-Powered Job Portal

HireLens is a full-stack job portal built with **Flask** and **PostgreSQL**. Employers post jobs and manage applicants on a drag-and-drop hiring pipeline. Candidates upload a resume, and the system extracts skills and calculates an **AI match score** (sentence-transformers embeddings + skills overlap) for every job.

> Author: **Muhammad Faizan Farooq** | GitHub: [faizanjutt473](https://github.com/faizanjutt473)

---

## Features

**Candidate**
- Register and log in (JWT authentication)
- Upload resume (PDF or DOCX, up to 5 MB); skills are extracted automatically
- Live job search with filters (keyword, location, job type)
- AI match ring (0 to 100%) on every job, with matched and missing skills in the tooltip
- One-click apply, duplicate applications blocked
- Track application stages and see upcoming interviews

**Employer**
- Post, close and reopen jobs
- Applicants ranked by match score
- Drag-and-drop hiring pipeline: Applied, Shortlisted, Interview, Hired, Rejected
- Open the applicant's resume directly
- Schedule interviews (date, time, link) with automatic email to the candidate; cancel with email
- Analytics: hiring funnel, time-to-hire, applications in the last 14 days, skills in demand

**Engineering**
- Role-based access control (candidate / employer) and ownership checks
- Background email sending with Celery (+ Redis), with an eager mode for local development
- Full stage history audit trail
- 73 automated tests, about 97% coverage

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, Flask-Bcrypt, Flask-CORS, Marshmallow |
| Database | PostgreSQL (JSON columns for skills and embeddings) |
| AI / NLP | sentence-transformers (`all-MiniLM-L6-v2`), spaCy, pdfplumber, python-docx |
| Async tasks | Celery, Redis, Flask-Mail |
| Frontend | HTML, CSS, vanilla JavaScript (served by Flask) |
| Testing | pytest, pytest-cov |
| DevOps | Dockerfile and docker-compose (optional) |

---

## Project Structure

```
Jobportal/
└── backend/
    ├── app/
    │   ├── __init__.py            # create_app(), extensions, blueprint registration
    │   ├── config.py              # Config, TestingConfig (env based)
    │   ├── extensions.py          # db, jwt, bcrypt, cors, migrate, mail
    │   ├── models.py              # User, Company, Job, Resume, Application,
    │   │                          # StageHistory, Interview
    │   ├── utils.py               # current_user(), role_required()
    │   ├── matching.py            # embeddings + match_score()
    │   ├── emails.py              # queue_email(), time formatting
    │   ├── tasks.py               # Celery task: send_email
    │   ├── celery_app.py          # Celery factory
    │   │
    │   ├── main/                  # page routes (serves HTML templates)
    │   ├── auth/                  # register, login (routes.py, schemas.py)
    │   ├── jobs/                  # job CRUD and search (routes.py, schemas.py)
    │   ├── resumes/               # upload, parser.py, skills.py, routes.py
    │   ├── applications/          # apply, my applications, match scores
    │   ├── pipeline/              # employer pipeline, stage change, resume download
    │   ├── interviews/            # schedule, upcoming, cancel (+ schemas.py)
    │   ├── analytics/             # employer analytics
    │   │
    │   ├── templates/             # FRONTEND: HTML pages
    │   │   ├── login.html
    │   │   ├── jobs.html
    │   │   ├── candidate.html
    │   │   ├── employer.html
    │   │   └── ...                # other pages (home, register)
    │   └── static/                # FRONTEND: assets
    │       ├── css/
    │       │   └── style.css
    │       └── js/
    │           ├── app.js         # shared helpers (selectors, toast, navbar)
    │           ├── api.js         # fetch wrapper with JWT
    │           ├── jobs.js        # job feed, match rings, apply, post job
    │           ├── resumes.js     # resume upload and skills
    │           ├── applications.js# candidate applications and interviews
    │           ├── pipeline.js    # drag-and-drop board, interview form
    │           └── analytics.js   # charts and stats
    │
    ├── migrations/                # Alembic migrations
    ├── tests/                     # pytest suite
    │   ├── conftest.py
    │   ├── helpers.py
    │   ├── test_auth.py
    │   ├── test_jobs.py
    │   ├── test_applications.py
    │   ├── test_pipeline.py
    │   ├── test_analytics.py
    │   └── test_misc.py
    ├── uploads/                   # stored resumes (not committed)
    ├── make_celery.py             # Celery worker entry point
    ├── run.py                     # Flask entry point
    ├── requirements.txt
    ├── pytest.ini
    ├── Dockerfile
    ├── docker-compose.yml
    ├── .dockerignore
    └── .env                       # secrets (not committed)
```

> The frontend is served by Flask itself, so it lives inside `app/templates` and `app/static`. Adjust the tree if your folder names differ slightly.

---

## Database Design

| Table | Purpose |
|---|---|
| `users` | Accounts with role (`candidate` or `employer`) |
| `companies` | One company per employer |
| `candidate_profiles` | Optional candidate details |
| `jobs` | Job posts, `skills_required` (JSON), `embedding` (JSON), status |
| `resumes` | Uploaded files, extracted `skills`, `raw_text`, `embedding`, `is_active` |
| `applications` | Candidate applied to job, `match_score`, `stage`, `hired_at`. Unique on (job, candidate) |
| `stage_history` | Every stage change (from, to, who, when) |
| `interviews` | Scheduled interviews linked to an application |

---

## How the AI Match Score Works

1. The job text (title, skills, description) and the resume text are split into chunks of about 180 words (the model has a 256 token limit).
2. Each chunk is embedded with `all-MiniLM-L6-v2` and the vectors are averaged and normalised.
3. Cosine similarity is rescaled to 0 to 1 (`(cosine - 0.15) / 0.55`, clipped).
4. Final score = **60% semantic similarity + 40% required-skills overlap**, shown as 0 to 100.
5. Embeddings are cached in the database and cleared when a job's title, description or skills change.

The model (about 90 MB) downloads automatically on first use.

---

## API Overview

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login` |
| Jobs | `GET /api/jobs`, `GET /api/jobs/<id>`, `GET /api/jobs/mine`, `POST /api/jobs`, `PATCH /api/jobs/<id>` |
| Applications | `POST /api/applications`, `GET /api/applications/mine`, `GET /api/applications/scores?job_ids=1,2` |
| Pipeline | `GET /api/pipeline/jobs/<id>`, `PATCH /api/pipeline/applications/<id>/stage`, `GET /api/pipeline/applications/<id>/resume` |
| Interviews | `POST /api/interviews`, `GET /api/interviews/upcoming`, `GET /api/interviews/mine`, `POST /api/interviews/<id>/cancel` |
| Analytics | `GET /api/analytics/employer` |

Resume upload endpoints live under `/api/resumes`.

---

## Getting Started

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/faizanjutt473/<your-repo>.git
cd Jobportal/backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Create the database

Create an empty PostgreSQL database (for example `hirelens`) and a second one for tests (`hirelens_test`).

### 3. Configure `.env`

```env
DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/hirelens
SECRET_KEY=change-me
JWT_SECRET_KEY=change-me-too

APP_TIMEZONE=Asia/Karachi
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_EAGER=true

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=
```

Use the same variable names your `config.py` reads. If `MAIL_USERNAME` is empty, emails are printed in the terminal instead of being sent. For Gmail use an App Password.

### 4. Run migrations and start the server

```bash
flask db upgrade
python run.py
```

Open `http://localhost:5000`.

### 5. (Optional) Real Celery worker

```bash
# set CELERY_EAGER=false in .env, start Redis, then:
celery -A make_celery worker --pool=solo --loglevel=info
```

`--pool=solo` is needed on Windows.

### 6. (Optional) Docker

```bash
docker compose up --build
```

Needs several GB of free disk space (PyTorch and spaCy are large).

---

## Running the Tests

Tests use a separate database (`hirelens_test`). The AI model is mocked, so no download is needed.

```bash
pytest
pytest --cov=app --cov-report=term-missing
```

Current result: **73 passed, 96.9% coverage**.

---

## Security Notes

- Passwords hashed with bcrypt
- JWT-protected routes with role checks (`role_required`)
- Employers can only see and change their own jobs, applicants and interviews (others get 404 or 403)
- Resume upload limited to PDF and DOCX, 5 MB
- Output is HTML-escaped in the frontend
- Secrets are kept in `.env` (never commit it)

---

## Roadmap

- Candidate profile page and job bookmarks
- Resume ranking with a BERT skill-extraction model
- Real-time notifications
- Deployment on Render, Railway or Fly.io

---

## License

This project is for learning and portfolio purposes. Add a license (for example MIT) before publishing.
