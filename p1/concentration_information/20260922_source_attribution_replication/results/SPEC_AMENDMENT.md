# 2024 external-sample amendment

On 2026-09-22, the user changed the external sample from 2024 January--June
to the symmetric full-year design: the fifth and fifteenth NYSE session of
every 2024 month. This is 24 fixed dates and 72 maximum requests: 24
XNAS.ITCH, 24 ARCX.PILLAR, and 24 shared GLBX.MDP3 ES.v.0 requests.

The frozen equity universe remains the 23 stocks actually present in the 2023
`DIRECTIONAL_FEATURES` panel plus SPY. BF remains excluded because it did not
enter that frozen panel. Existing nonempty Jan--June native DBNs remain valid
reusable input only when their exact request identity matches; the downloader
hashes and reuses them, and refuses overwrites or an empty target.
