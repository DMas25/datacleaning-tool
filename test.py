print("🚀 Running test file")

import os
import sys

# Force Python to see current folder
sys.path.append(os.getcwd())

print("Working directory:", os.getcwd())

from coltradata.engine import run_pipeline_from_uploaded_file

print("✅ Import successful")