#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/vch-smoke.XXXXXX")"
trap 'if [[ "${KEEP_SMOKE:-0}" != "1" ]]; then rm -rf "$TMP_ROOT"; else echo "Smoke preservado em: $TMP_ROOT"; fi' EXIT

VIDEO="$TMP_ROOT/source.mp4"
WORKSPACE="$TMP_ROOT/runs"
CONFIG="$ROOT/config/testing/smoke.yaml"

ffmpeg -y -hide_banner -loglevel error \
  -f lavfi -i "testsrc2=size=1280x720:rate=24" \
  -f lavfi -i "sine=frequency=440:sample_rate=48000" \
  -t 12 -c:v libx264 -preset ultrafast -crf 30 -pix_fmt yuv420p \
  -c:a aac -ar 48000 -shortest "$VIDEO"

cd "$ROOT"
RUN_OUTPUT="$(VCH_CONFIG="$CONFIG" "$ROOT/vch" init "$VIDEO" examples/minimal/transcript.srt --mode full --workspace "$WORKSPACE")"
RUN_DIR="${RUN_OUTPUT#RUN_DIR=}"
VCH_CONFIG="$CONFIG" "$ROOT/vch" prepare --run "$RUN_DIR" >/dev/null
cp examples/minimal/fixtures/{04-context-map.json,05-viral-moments.json,06-candidates.json,07-feed-review.json,09-blind-review.json,10-deduplication.json,11-edit-plans.json,12-quality-review.json} "$RUN_DIR/"
VCH_CONFIG="$CONFIG" "$ROOT/vch" audit --run "$RUN_DIR" >/dev/null
VCH_CONFIG="$CONFIG" "$ROOT/vch" blind-packets --run "$RUN_DIR" >/dev/null
for file in 04-context-map.json 05-viral-moments.json 06-candidates.json 07-feed-review.json 08-technical-audit.json 09-blind-review.json 10-deduplication.json 11-edit-plans.json 12-quality-review.json; do
  VCH_CONFIG="$CONFIG" "$ROOT/vch" validate-artifact --run "$RUN_DIR" --file "$file" >/dev/null
done
VCH_CONFIG="$CONFIG" "$ROOT/vch" finalize --run "$RUN_DIR" >/dev/null
VCH_CONFIG="$CONFIG" "$ROOT/vch" subtitles --run "$RUN_DIR" >/dev/null
VCH_CONFIG="$CONFIG" "$ROOT/vch" render --run "$RUN_DIR" >/dev/null
VCH_CONFIG="$CONFIG" "$ROOT/vch" verify-output --run "$RUN_DIR" >/dev/null
VCH_CONFIG="$CONFIG" "$ROOT/vch" validate-run --run "$RUN_DIR" >/dev/null

echo "SMOKE TEST OK"
echo "RUN_DIR=$RUN_DIR"
