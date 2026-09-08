"""Retrieve the unchanged course snapshot without distributing data in Git."""
from pathlib import Path
import hashlib
import requests
ROOT=Path(__file__).resolve().parents[1]
URL='https://raw.githubusercontent.com/anmolsingh0219/FRE-GY-7871A-Assignment1/532c65cf91cdf62a8d37c9bbe6ff0961c152d756/data/universe/ark_holdings_raw.csv'
SHA256='16697ed3f42ab79c1ea5fca55edbdb7f567c6dcbe4427fe54ef752baa67a397a'
if __name__=='__main__':
    path=ROOT/'data/universe/ark_holdings_raw.csv'
    data=path.read_bytes() if path.exists() else requests.get(URL,timeout=60).content
    if hashlib.sha256(data).hexdigest()!=SHA256:
        raise RuntimeError('Holdings checksum differs from the course snapshot; inspect before proceeding')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)
    print('Course holdings snapshot verified.')
