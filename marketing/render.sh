#!/bin/sh
set -eu

output_dir=${1:-docs/media}
frame_dir="$output_dir/frames"
mkdir -p "$frame_dir"

for source in marketing/frames/*.svg; do
  qlmanage -t -s 1350 -o "$frame_dir" "$source" >/dev/null 2>&1
done

cp "$frame_dir/01-message.svg.png" "$output_dir/safarakeet-message.png"
cp "$frame_dir/03-listening.svg.png" "$output_dir/safarakeet-listening.png"
cp "$frame_dir/04-private.svg.png" "$output_dir/safarakeet-private.png"

ffmpeg -hide_banner -loglevel error -y \
  -loop 1 -t 4 -i "$frame_dir/01-message.svg.png" \
  -loop 1 -t 4 -i "$frame_dir/02-tailnet.svg.png" \
  -loop 1 -t 4 -i "$frame_dir/03-listening.svg.png" \
  -loop 1 -t 4 -i "$frame_dir/04-private.svg.png" \
  -filter_complex "\
    [0:v]fps=30,format=yuv420p[s0];[1:v]fps=30,format=yuv420p[s1];\
    [2:v]fps=30,format=yuv420p[s2];[3:v]fps=30,format=yuv420p[s3];\
    [s0][s1]xfade=transition=fade:duration=0.6:offset=3.4[x1];\
    [x1][s2]xfade=transition=fade:duration=0.6:offset=6.8[x2];\
    [x2][s3]xfade=transition=fade:duration=0.6:offset=10.2,format=yuv420p[out]" \
  -map "[out]" -t 13.6 -r 30 -c:v libx264 -crf 18 -movflags +faststart \
  "$output_dir/safarakeet-promo.mp4"

printf 'marketing media: rendered\n'
