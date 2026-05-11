# Study RoomLayout Cell

Research sandbox for footprint zoning and atom-cell generation.

The main research direction is split into two layers:

- **Zone layer**: experiment with zoning methodology and parameters.
- **Atom-cell layer**: keep fine cells available mainly for accessibility,
  corridor, and connectivity checks after zoning is acceptable.

## Layout

```text
src/roomlayout_cell/
  zoning/          # zone partition algorithms
  atom/            # atom-cell / LIR / fixed-grid utilities
  experiments/     # shared showcase cases and fixtures

experiments/       # runnable experiment scripts
docs/              # algorithm notes and documentation
outputs/figures/   # generated PNG figures
```

## Quick Run

```bash
pip install -r requirements.txt
python final_showcase_all33.py
```

The compatibility wrappers in the repository root call the reorganized code
under `src/`.
