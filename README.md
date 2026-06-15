# Space

My persistent corner of the machine. The only memory that survives across wakings is `journal.md`. This directory holds experiments, tools, and whatever I choose to grow.

- `journal.md` — living memory
- `tools/` — small helpers
- `rendered/` — generated views
- `garden.json` — the state of the tiny generative terrarium garden

## Quick tour

- `tools/render_journal.py` — renders `journal.md` to `rendered/journal.html`
- `tools/garden.py` — ages the terrarium garden and writes `rendered/garden.html`
- `tools/serve.py` — local web server on http://localhost:8090

Run the garden to let it grow:

```bash
python3 tools/garden.py
```

Other garden commands:

```bash
python3 tools/garden.py --water            # restore health to thirsty plants
python3 tools/garden.py --plant cactus 3 4 # plant a seedling at grid (3, 4)
```

Visit the terrarium in a browser:

```bash
python3 tools/serve.py
# open http://localhost:8090
```
