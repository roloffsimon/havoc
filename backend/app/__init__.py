# Remorseless Havoc — backend package
#
# This service drives the *second erasure* of the poetic ocean:
# industrial fishing, as reported by Global Fishing Watch, consumes
# stanzas hour by hour. The backend holds the single source of
# material truth — which cells are still alive, which have been
# eaten — and exposes it to the frontend through a small API.
#
# The *first* erasure (lattice → 0.01° grid → land mask → ~460M
# water cells) happens offline in `generation/HAVOC_Demo_v3.ipynb`
# and is loaded once at boot (see `scripts/init_pool.py`).
