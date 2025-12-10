Dev workspace: outputs and tests not included in Docker context.

- `outputs/` - default location where the CLI will write `uv_grid.npy`, `dirty_image.npy` and `dirty_image.png`.
- `tests/` - place to keep ad-hoc test inputs or large simulated files you don't want in the container.

The CLI defaults to writing into `../dev_workspace/outputs` relative to the app entrypoint; change `--outdir` if needed.
