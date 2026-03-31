Documentation Generation.

Planning documents for docs publishing changes live under `docs/plans/`.

Boost.Python API build-time generation:

Python API pages for Boost.Python-exported Rogue classes can embed the
``.. rogue_boostpython_api::`` directive. The directive is implemented as a
custom Sphinx extension under ``docs/src/_ext`` and renders binding-derived
sections during the doc build.

Fallback/debug helper:

```
python3 scripts/generate_boostpython_api_docs.py \
  --rst docs/src/api/python/rogue/utilities/prbs/prbs.rst
```

The helper script reads the page's ``.. autoclass::`` target and prints the same
binding-derived content used by the Sphinx directive. It is useful for debugging
the generated RST without running a full Sphinx build.
