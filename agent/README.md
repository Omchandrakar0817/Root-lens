# Optional monitoring agent

This sample agent sends host-level metrics to the platform so the app can correlate public website failures with CPU, memory, and disk pressure.

## Requirements

```bash
cd agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure the agent token

Create an agent in the application UI or API, then copy the returned bearer token.

## Run the agent

```bash
python monitoring_agent.py \
  --api-url http://localhost:8000/api/v1/agents/ingest \
  --token <agent-token> \
  --interval 60
```

The agent posts CPU, memory, disk, network, and top process metrics to the API at the configured interval.

This data is optional and is never fabricated. The platform only treats it as evidence when it was actually reported by an authorized agent.
