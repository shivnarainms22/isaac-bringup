#!/usr/bin/env bash
# M2 environment probe: what does the Isaac container have for building PX4 / XRCE /
# Pegasus, and where's the disk? Run inside the container with the repo mounted at /work.
echo "== OS =="
grep -E "PRETTY_NAME|VERSION_ID" /etc/os-release

echo "== build tools (path or MISSING) =="
for t in gcc g++ make cmake ninja git python3 pip3 colcon rustc; do
  printf "%-8s: " "$t"; command -v "$t" || echo MISSING
done

echo "== python =="
python3 --version 2>&1
echo "isaac python.sh:"; ls -1 /isaac-sim/python.sh 2>/dev/null || echo "  (not at /isaac-sim/python.sh)"

echo "== disk: container writable layer (/) =="
df -h / 2>/dev/null | tail -1

echo "== disk: /work mount (should be /home, the big disk) =="
df -h /work 2>/dev/null | tail -1

echo "== /work writable test =="
if touch /work/.probe_write_test 2>/dev/null; then echo "WRITABLE"; rm -f /work/.probe_write_test; else echo "NOT writable"; fi

echo "== a few PX4 build python deps (importable?) =="
for m in jinja2 yaml kconfiglib packaging; do
  python3 -c "import $m" 2>/dev/null && echo "$m: ok" || echo "$m: MISSING"
done

echo "PROBE BUILDENV DONE"
