#!/bin/bash
# Downloads the sound-effect picks one by one (Wikimedia rate-limits shared IPs; the helper waits it out).
cd "$(dirname "$0")/.."
while read -r id name; do
  [ -z "$id" ] && continue
  ls sfx/"$name".* >/dev/null 2>&1 && continue
  python3 tools/openverse.py get "$id" "$name" 2>&1 | tail -1
  sleep 20
done <<'LIST'
55222fbc-dac2-4556-bea3-1d68c9064174 braam
be9c4349-1c66-48ed-894d-2d72c51de46d shutter
0449c69e-f84d-4bd7-a3f9-f3e30916788c glitch_logo
d7264daf-6fe3-47d7-a2d7-1f7a16a8172e riser
860f7109-f217-4bbd-99f2-5adedfface83 splitflap
fffc33ac-14b8-48e8-a5e1-32496bde8d49 gsm_buzz
6bf43f24-f77a-48fc-b577-10294cd4e858 glass_tap
de0e071b-896e-4797-bb98-9ecfa7f19158 glitch_fail
cff4d25f-a3ef-41f8-8253-2bbacd928d70 glitch_place
1f5dbb6a-4120-41c7-9706-8469891ea981 glitch_collect
5098cedb-050d-40b2-8dff-3befd7aeb309 glitch_noise
7ce36601-cf29-4951-ab24-62f24cc12c7d glitch_long
c518e5db-21af-4ccc-a8dd-68d0aba2b853 cymbals
0299e833-f0b2-4f8d-9794-b53ce2106e7e gong
0e738959-26ae-45ef-bf00-b6e9a0206d84 tubebells
fb0b8fb8-1801-4ae7-9024-e7aa991674f3 static
87ddbaa1-4098-4be3-87c1-5083e9b97ef2 camera_focus
c57f672a-47fe-4848-8bfe-404960a739fc teleprinter
LIST
ls sfx
