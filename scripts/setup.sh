#!/bin/bash
echo "Setting up QUANTUM-AGIS..."
cd backend && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
echo "Setup complete!"
