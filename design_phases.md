Metric arrives
    │
    ▼
CPU <= 80? ──Yes──▶ Send "metrics" message ──▶ Done
    │
    No
    ▼
Was already alerting? ──Yes──▶ Send "metrics" only (don't spam)
    │
    No
    ▼
Create new alert state
Send "metrics" message
Send "alert" message
Done