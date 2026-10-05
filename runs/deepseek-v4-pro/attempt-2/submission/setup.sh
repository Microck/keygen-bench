#!/bin/bash
set -e
B=/workspace/work/b64
ft2 call module_new '{"channels":8,"name":"VECTOR DREAM"}' >/dev/null
mk() { # inst loop flags vol pan relnote name
  local inst=$1 name=$2 loop=$3 flags=$4 vol=$5 pan=$6 rel=$7
  local b64=$(cat $B/$name.b64)
  ft2 call sample_create_from_pcm "{\"instrument\":$inst,\"sample\":0,\"pcm\":\"$b64\",\"encoding\":\"float32\",\"name\":\"$name\"}" >/dev/null
  if [ "$loop" = "0" ]; then
    ft2 call sample_set "{\"instrument\":$inst,\"flags\":$flags,\"volume\":$vol,\"panning\":$pan,\"relative_note\":$rel}" >/dev/null
  else
    ft2 call sample_set "{\"instrument\":$inst,\"loop_start\":0,\"loop_length\":$loop,\"flags\":$flags,\"volume\":$vol,\"panning\":$pan,\"relative_note\":$rel}" >/dev/null
  fi
  ft2 call instrument_set "{\"instrument\":$inst,\"name\":\"$name\"}" >/dev/null
}
mk 1 lead 256 17 64 128 36
mk 2 harm 256 17 56 72 36
mk 3 pad 256 17 48 96 36
mk 4 bass 256 17 64 128 36
mk 5 arp 256 17 44 184 36
mk 6 kick 0 16 64 128 0
mk 7 snare 0 16 56 96 0
mk 8 chat 0 16 48 160 0
mk 9 ohat 0 16 44 160 0
mk 10 crash 0 16 40 160 0
ft2 call song_set '{"name":"VECTOR DREAM","bpm":130,"speed":6,"length":4,"loop_start":0}' >/dev/null
echo "setup done"
