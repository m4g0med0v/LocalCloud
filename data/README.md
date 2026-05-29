# LocalCloud

A self-hosted cloud storage platform.

## Features

- **File management** — upload, download, rename, move, delete
- **Previews** — images, video, audio, PDF, and all text formats
- **Text editor** — built-in editor with line numbers for any text file
- **Sharing** — public and private links

## Getting Started

```bash
# Clone the repo
git clone https://github.com/example/localcloud.git
cd localcloud

# Start the backend
cd backend
pip install -e .
uvicorn app.main:app --reload

# Start the frontend
cd frontend
npm install
npm run dev
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO server address |
| `SECRET_KEY` | — | JWT signing secret |

## License

MIT
