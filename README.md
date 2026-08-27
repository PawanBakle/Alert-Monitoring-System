# Alert Monitoring System

A small system for monitoring a fleet of servers (or simulated "agent" nodes) in real time,  agents report their CPU/memory/disk stats, the backend flags anything abnormal, and a dashboard shows live status over WebSockets.

I built this to get hands-on with async Django (Channels + Redis), JWT auth flows, and background job scheduling (celery-beat) 

## How it works

Each agent goes through a simple lifecycle:

1. **Register** : an agent signs up with a hostname, MAC address.
2. **Login** : it authenticates and gets back a JWT access/refresh token pair, plus the last sequence ID it successfully sent
3. **Send metrics** : on an interval, the agent posts CPU/memory/disk numbers tagged with an incrementing sequence ID.

On the server side:

- Every incoming metric is validated and evaluated for severity (Normal / Warning / Critical) based on CPU thresholds before it's saved.
- Once saved, it's pushed to Redis and broadcast out to any dashboard clients listening over WebSockets.
- A scheduled job (Celery Beat) runs in the background and checks whether any agent has gone quiet for longer than a threshold and if so, it's marked offline and that status change gets pushed out the same way.

There's also a small recovery mechanism: if a dashboard disconnects and comes back later, it sends up the last sequence ID it saw per node, and the server looks up everything it missed (alerts only) and sends it back in one batch, so a dashboard that was closed for 10 minutes doesn't just miss 10 minutes of alerts silently.

Sequence IDs are also how duplicate submissions are caught like each (node, seq_id) pair is unique at the database level, so if an agent retries a request that actually went through, it gets rejected instead of double-counted.

## Tech stack

- **Django + Django REST Framework** - core API
- **Django Channels** - WebSocket support for the dashboard
- **Redis** - channel layer / pub-sub backend for Channels, and Celery broker
- **Celery Beat** - scheduled offline-detection job
- **PostgreSQL** - database
- **Simple JWT** - token auth for agents
- **Docker Compose** - local orchestration of all of the above

## Running Locally with Docker

### 1. Clone and Navigate

```bash
git clone https://github.com/PawanBakle/Alert-Monitoring-System.git
cd project_4
```

### 2. Configure Environment Variables

Create your `.env` file from your configuration template and fill in your secrets:
```bash
cp .env.example .env
```

Ensure your `.env` contains the required keys for database and Redis communication:

Code snippet

```
DB_NAME=metrics_db
DB_USER=postgres
DB_PASSWORD=pass@123#
DB_HOST=db
REDIS_HOST=redis
```

### 3. Build and Start the Stack

Spin up the entire containerized architecture in the background:
```bash
docker compose up --build -d
```

This spins up the following services:

- **`metrics_django_web`**: Django API + WebSocket server running on port `8000`.
- **`metrics_postgres`**: PostgreSQL database running on port `5432`.
- **`metrics_redis`**: Redis instance for Channels layer and Celery broker on port `6379`.
- **`metrics_celery_worker`**: Background worker processing asynchronous tasks.
- **`metrics_celery_beat`**: Scheduler executing periodic jobs (such as offline node detection).
- **`metrics_agent_simulator`**: Simulated client agent streaming metrics data automatically.
### 4. Run Database Migrations

Initialize your relational database schema inside the running container:
```bash
docker compose exec web python manage.py migrate
```

### 5. Optional: Run an Additional Agent Simulator manually

If you want to spin up an extra simulated agent with a custom ID and interval:
```bash
python agent_simulator.py --server-id test-node-2 --interval 3
```

## API endpoints

| **Endpoint**          | **Method**  | **Purpose**                                          |
| --------------------- | ----------- | ---------------------------------------------------- |
| `/dashboard/`         | `GET`       | Live HTML dashboard view                             |
| `/api/register/`      | `POST`      | Register a new agent/node                            |
| `/api/login/`         | `POST`      | Authenticate, retrieve JWT tokens and sequence ID    |
| `/api/token/refresh/` | `POST`      | Refresh an expired access token                      |
| `/api/metrics/`       | `POST`      | Submit a metrics reading (Requires Auth)             |
| `/ws/metrics/`        | `WebSocket` | Live dashboard connection for real-time node updates |

## Project structure

```
.
├── Dockerfile
├── README.md
├── agent_simulator.py
├── alert_monitoring_system
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── clients
│   ├── admin.py
│   ├── apps.py
│   ├── consumers.py
│   ├── management
│   ├── migrations
│   ├── models.py
│   ├── routing.py
│   ├── serializers.py
│   ├── tasks.py
│   ├── templates
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── docker-compose.yml
├── manage.py
└── requirements.txt


## Known limitations / what I'd add next

- No historical charting yet : right now it's live status only, not trends over time.
- Offline-detection threshold and CPU alert thresholds are hardcoded rather than configurable per node.
- No alerting outside the dashboard itself (e.g. email/Slack on critical alerts).

