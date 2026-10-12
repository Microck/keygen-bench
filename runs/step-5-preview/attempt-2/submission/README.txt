Original keygen tune: "SkidRow keygen"  (FastTracker II .XM, 8-bit samples)

- Style: classic demoscene/keygen. A minor, BPM 150, speed 6 (4 rows/beat).
- Progression: Am F C G / Am F Dm E  (i VI III VII / iv V i).
- Sections (loop): intro -> verse -> chorus -> chorus' -> break -> build -> end -> (loops to chorus).
- All pitched samples are 401-sample single-period loops at native 110 Hz so note 49 = A2
  for every instrument (harmony stays locked). Percussion are 8-bit one-shots.
- Loop: pattern 6 ends with a position-jump (Bxx -> 2); song restart = 2, so it loops
  back into the chorus (intro plays once).
- To rebuild: python3  gen_samples.py && gen_instruments.py && compose2.py; then
  bash rebuild.sh (applies setup + pattern batches, saves tune.xm). Render with the
  provided XM renderer.
