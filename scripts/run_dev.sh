#!/bin/bash
echo "Starting QUANTUM-AGIS..."
cd backend && uvicorn app.main:app --reload --port 8000 &
cd frontend && npm run dev &
wait
