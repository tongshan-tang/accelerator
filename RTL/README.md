# RTL

Current RTL implementation for the selected Plan B sparse matrix accelerator.

Directory roles:

- `common/`: shared parameters, type definitions, and small reusable modules.
- `memory/`: SRAM/BRAM wrappers and matrix storage interfaces.
- `matcher/`: CSR/CSC pointer fetch, index buffering, and merge matcher.
- `compute/`: FP16 MAC, accumulation, and output formatting.
- `control/`: top-level scheduling, task FIFO, and backpressure control.
- `top/`: top-level integration modules.
