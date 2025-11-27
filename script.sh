#!/bin/bash

echo "🔄Activating virtual environment..."
source /home/backend/env/bin/activate

echo "⚠️Navigating to project directory..."
cd /home/backend/erp

echo "⚠️Navigating to project directory..."
git pull origin master

echo "🛠 Running script..."
python python3 scripts.py

echo "✅ script run complete!"


