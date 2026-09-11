"""Collect the two research packages in the project delivery folder."""
import hashlib
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / 'outputs'
cutoff = json.loads((out / 'audit.json').read_text())['sample_end']
monitor = out / 'company_monitor'
assert json.loads((monitor / 'data.json').read_text())['metadata']['as_of_date'] == cutoff
files = []
for folder, topic in [(out, 'Sentiment_and_Uncertainty'), (monitor, 'Company_Monitoring')]:
    for kind, extension in [('Report', 'docx'), ('Report', 'pdf'), ('Data', 'xlsx')]:
        files.append(folder / f'ARK_Holdings_{topic}_{kind}_{cutoff}.{extension}')
for path in files:
    if not path.is_file():
        raise FileNotFoundError(path)
destination = root.parent / 'deliverable'
destination.mkdir(exist_ok=True)
expected = {path.name for path in files}
unexpected = {path.name for path in destination.iterdir()} - expected
if unexpected:
    raise ValueError(f'Unrelated files need separate handling: {sorted(unexpected)}')
for source in files:
    target = destination / source.name
    shutil.copy2(source, target)
    assert hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(source.read_bytes()).digest()
assert {path.name for path in destination.iterdir()} == expected
for extension in ['xlsx', 'docx', 'pdf']:
    assert len(list(destination.glob(f'*.{extension}'))) == 2
print(destination)
print('Verified: 2 Excel workbooks, 2 Word reports, 2 PDF reports.')
