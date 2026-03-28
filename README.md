# ForgeLink AI

ForgeLink AI is a Track 6 Open Innovation project built with React, FastAPI,
and Python. It helps innovators turn scattered ideas into actionable startup
opportunities by matching problem statements, team skills, and market signals.

## Concept

Open innovation often fails because ideas, collaborators, and execution plans
live in separate places. ForgeLink AI brings them together in one flow:

- submit an idea or problem statement
- define available team skills and target domain
- receive an AI-scored opportunity assessment
- get feature suggestions, collaborator gaps, and a startup sprint plan

## Why It Fits Open Innovation

- Works across domains instead of solving only one niche problem
- Encourages collaboration between builders, designers, and domain experts
- Turns raw ideas into structured execution plans
- Can be used by hackathons, incubators, campuses, and startup communities

## Tech Stack

- Frontend: React + Vite
- Backend: FastAPI
- AI/ML: Python rule-based opportunity scoring and recommendation engine

## Demo Flow

1. User enters an idea, domain, problem severity, market timing, and team skills.
2. ForgeLink AI computes an innovation readiness score.
3. The app highlights strengths, missing skills, and risks.
4. It generates MVP features, target users, launch experiments, and an implementation roadmap.

## Local Run

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100
```

Backend runs at `http://127.0.0.1:8100`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://127.0.0.1:5174`.

### Frontend Deployment

The frontend can be deployed separately on Vercel or Netlify.

Default production backend:

```text
https://forgelinkai.onrender.com
```

Optional environment variable:

```text
VITE_API_BASE_URL=https://forgelinkai.onrender.com
```

#### Vercel

1. Import the GitHub repo into Vercel.
2. Set the project root directory to `frontend`.
3. Build command:

```bash
npm run build
```

4. Output directory:

```text
dist
```

5. Add `VITE_API_BASE_URL=https://forgelinkai.onrender.com` if you want it explicit.

## Deployment

This project is set up so FastAPI can serve the built React frontend in a
single deployment.

### Render

1. Push the project to GitHub.
2. Create a Render Web Service or Blueprint.
3. Use the included `render.yaml`.
4. Render will install backend dependencies, build the React app, and start FastAPI.
5. The backend pins Python to `3.13.9` via `backend/runtime.txt` for package compatibility.

In deployment, the frontend defaults to the same origin for API requests, so it
does not depend on a localhost API URL.
