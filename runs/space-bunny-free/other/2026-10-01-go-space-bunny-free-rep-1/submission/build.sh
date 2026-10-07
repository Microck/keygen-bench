set -e
cd /workspace
S=/workspace/samples
ft2 call module_new '{"channels":12,"name":"NEONKEYGEN"}' > /dev/null
i=1
for f in lead lead2 arp bass pad kick snare hat openhat tom crash stab_dm stab_bb stab_f stab_c; do
  ft2 call sample_load "{\"path\":\"$S/$f.wav\",\"instrument\":$i}" > /dev/null
  i=$((i+1))
done
ft2 call instrument_set '{"instrument":1,"name":"LEAD"}' > /dev/null
ft2 call instrument_set '{"instrument":2,"name":"LEAD2"}' > /dev/null
ft2 call instrument_set '{"instrument":3,"name":"ARP"}' > /dev/null
ft2 call instrument_set '{"instrument":4,"name":"BASS"}' > /dev/null
ft2 call instrument_set '{"instrument":5,"name":"PAD"}' > /dev/null
ft2 call instrument_set '{"instrument":6,"name":"KICK"}' > /dev/null
ft2 call instrument_set '{"instrument":7,"name":"SNARE"}' > /dev/null
ft2 call instrument_set '{"instrument":8,"name":"HAT"}' > /dev/null
ft2 call instrument_set '{"instrument":9,"name":"OPENHAT"}' > /dev/null
ft2 call instrument_set '{"instrument":10,"name":"TOM"}' > /dev/null
ft2 call instrument_set '{"instrument":11,"name":"CRASH"}' > /dev/null
ft2 call instrument_set '{"instrument":12,"name":"CHORD Dm"}' > /dev/null
ft2 call instrument_set '{"instrument":13,"name":"CHORD Bb"}' > /dev/null
ft2 call instrument_set '{"instrument":14,"name":"CHORD F"}' > /dev/null
ft2 call instrument_set '{"instrument":15,"name":"CHORD C"}' > /dev/null
# stereo placement (per instrument, volume kept at the loaded default)
ft2 call sample_set '{"instrument":3,"volume":64,"panning":96}'   > /dev/null   # arp    left
ft2 call sample_set '{"instrument":8,"volume":64,"panning":64}'   > /dev/null   # hat    left
ft2 call sample_set '{"instrument":9,"volume":64,"panning":48}'   > /dev/null   # open   left
ft2 call sample_set '{"instrument":5,"volume":64,"panning":176}'  > /dev/null   # pad    right
ft2 call sample_set '{"instrument":11,"volume":64,"panning":160}' > /dev/null   # crash  right
for i in 12 13 14 15; do ft2 call sample_set "{\"instrument\":$i,\"volume\":64,\"panning\":160}" > /dev/null; done
ft2 call song_set '{"bpm":150,"speed":6,"length":16,"loop_start":0}' > /dev/null
for p in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  ft2 call pattern_set_length "{\"pattern\":$p,\"rows\":32}" > /dev/null
done
for p in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  ft2 call order_set "{\"position\":$p,\"pattern\":$p}" > /dev/null
done
ft2 batch /workspace/work/build/cells.json > /dev/null
ft2 call module_info '{}'
