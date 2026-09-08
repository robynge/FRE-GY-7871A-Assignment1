"""Build all exhibits from a completed local corpus and market dataset."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.analysis import run_analysis

if __name__=="__main__":
    run_analysis()
