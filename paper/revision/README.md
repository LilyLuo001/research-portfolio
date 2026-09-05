# Revised referee package

Build with:

```sh
make -C paper revised
```

On SCC installations without `latexmk`, run `qsub paper/scripts/scc_build_revised_pdfs.sh` from the repository root.

The four required outputs are:

- `paper/build/YAX_WORKING_PAPER_REVISED.pdf`
- `paper/build/YAX_ONLINE_APPENDIX_REVISED.pdf`
- `paper/build/YAX_REFEREE_RESPONSE.pdf`
- `paper/build/YAX_REVISION_DIAGNOSIS.pdf`

The first two are journal-facing. The response and diagnosis preserve completion status, principled non-adoptions, failed diagnostics, and author-only metadata tasks. Machine results and receipts are under `yax/revision/referee_20260905/results/`.
