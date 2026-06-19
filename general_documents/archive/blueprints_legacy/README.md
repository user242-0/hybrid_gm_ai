# Legacy output blueprints

These files are historical, hand-written examples of `emotion_eval.yml` and
`story.yml`. They were moved out of the top-level `blueprints/` directory on
2026-06-19 because runtime emitters generate these job artifacts directly and
do not read the blueprints.

They remain useful as compact design references, but they are not runtime
schemas or guaranteed-valid fixtures. Current behavior is defined by:

- `src/datalab/emitters/emotion_emitter.py`
- `src/datalab/emitters/story_emitter.py`
