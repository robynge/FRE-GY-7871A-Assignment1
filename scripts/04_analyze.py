"""Build current and original-course-period exhibits from the acquired corpus."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.analysis import run_analysis
from src.config import OUTPUT_DIR, COURSE_SAMPLE_END

if __name__=="__main__":
    run_analysis()
    run_analysis(sample_end=COURSE_SAMPLE_END, output_dir=OUTPUT_DIR/"course_2021_2025")
