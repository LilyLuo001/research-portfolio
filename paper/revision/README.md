# Major-advice referee revision

Build with:

```sh
make -C paper major-revision
```

On SCC installations without `latexmk`, submit `paper/scripts/scc_build_major_revision_pdfs.sh` from the repository root.

The four required outputs are:

- `paper/build/YAX_WORKING_PAPER_REVISED.pdf`
- `paper/build/YAX_ONLINE_APPENDIX_REVISED.pdf`
- `paper/build/YAX_REFEREE_RESPONSE.pdf`
- `paper/build/YAX_REVISION_DIAGNOSIS.pdf`

The second-round outputs preserve those files and use new names:

- `paper/build/YAX_WORKING_PAPER_MAJOR_REVISION.pdf`
- `paper/build/YAX_ONLINE_APPENDIX_MAJOR_REVISION.pdf`
- `paper/build/YAX_REFEREE_RESPONSE_MAJOR_REVISION.pdf`
- `paper/build/YAX_REVISION_DIAGNOSIS_MAJOR_REVISION.pdf`

The first two are journal-facing. The response and diagnosis preserve completion status, principled non-adoptions, and author-only metadata tasks. The second-round machine results, response matrix, and receipts are under `yax/revision/referee_round2_20260905/`. This stage addresses the numbered major comments; secondary copyediting is explicitly reserved for the next pass.
