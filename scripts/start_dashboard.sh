#!/bin/bash

# Navigate to project directory
cd /Users/zmaros/Work/Projects/team_metrics

# Activate virtual environment
source venv/bin/activate

# Start Flask dashboard
python -m src.dashboard.app

# Exit with Flask's exit code
exit $?
