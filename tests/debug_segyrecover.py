# debug_inseis.py
import traceback
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.segyrecover.__main__ import main
    main()
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
    input("Press Enter to exit...")