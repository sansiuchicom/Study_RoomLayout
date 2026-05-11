# Running the Zoning Research Scripts

## Setup

```bash
cd /workspace/Study_RoomLayout_Cell
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Generate the final 33-case figure

```bash
python final_showcase_all33.py
```

This writes:

```text
outputs/figures/final_showcase_all33.png
```

## Other scripts

```bash
python 12_compare.py
python 02M_per_family.py
```

Direct experiment paths also work:

```bash
python experiments/final_showcase_all33.py
python experiments/compare_v11_v12.py
PYTHONPATH=src python -m roomlayout_cell.atom.per_family
```

The original snippets referenced `/home/claude/work`; the local scripts now
resolve imports relative to `src/` and write figures to `outputs/figures/`.
