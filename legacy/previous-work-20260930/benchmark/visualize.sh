#!/bin/bash
# Record the FT2 clone GUI playing one module: visualize.sh INPUT.xm SECONDS OUTPUT.mp4
# Runs inside the visualizer image as the unprivileged user. FT2 autoplays a module passed as
# its argument, so no input injection is needed. SDL's disk audio driver plays in real time and
# writes the exact PCM the mixer produced; the capture offset is the audio already written when
# the screen grab starts, which keeps picture and sound aligned within one audio buffer.
set -euo pipefail
input=$1 seconds=$2 output=$3
export DISPLAY=:9 HOME=/tmp/ft2home SDL_AUDIODRIVER=disk SDL_DISKAUDIOFILE=/tmp/played.raw SDL_VIDEODRIVER=x11
mkdir -p "$HOME"
Xvfb :9 -screen 0 1280x960x24 -nolisten tcp -nocursor >/tmp/xvfb.log 2>&1 &
for _ in $(seq 50); do xdpyinfo -display :9 >/dev/null 2>&1 && break; sleep 0.1; done
cd /tmp && ft2-clone "$input" >/tmp/ft2.log 2>&1 &
ft2=$!
window=$(xdotool search --sync --name 'Fasttracker II clone' | head -1)
eval "$(xdotool getwindowgeometry --shell "$window")"   # sets X Y WIDTH HEIGHT
xdotool mousemove 1279 40   # park the pointer outside the window so FT2 draws no cursor sprite
sleep 0.5   # let the first frame land after the map
offset_bytes=$(stat -c %s "$SDL_DISKAUDIOFILE")
ffmpeg -loglevel error -y -f x11grab -framerate 30 -video_size "${WIDTH}x${HEIGHT}" -i ":9.0+${X},${Y}" \
  -t "$seconds" -vf 'scale=1280:960:flags=lanczos' -c:v libx264 -preset ultrafast -crf 20 -pix_fmt yuv420p /tmp/video.mp4
kill "$ft2" 2>/dev/null || true; wait "$ft2" 2>/dev/null || true
# FT2 opens the device at 48000 Hz 16-bit stereo unless FT2.CFG says otherwise; there is no config here.
offset=$(python3 -c "print($offset_bytes / (48000 * 2 * 2))")
ffmpeg -loglevel error -y -i /tmp/video.mp4 -f s16le -ar 48000 -ac 2 -ss "$offset" -i "$SDL_DISKAUDIOFILE" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$output"
echo "window=${WIDTH}x${HEIGHT}+${X}+${Y} audio_offset=${offset}"
