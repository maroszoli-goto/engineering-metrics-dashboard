#!/bin/bash

# Navigate to project directory
cd /Users/zmaros/Work/Projects/team_metrics

# Activate virtual environment
source venv/bin/activate

# Run data collection
python collect_data.py

# Exit with collection script's exit code
exit $?
