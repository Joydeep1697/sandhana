#!/bin/bash
cd backend
python3 -m uvicorn core.fastapi_app:app --host 0.0.0.0 --port 8000 &
PID=$!
sleep 2
curl -s http://localhost:8000/api/equation/fixture > ../fixture_response.json
kill $PID
