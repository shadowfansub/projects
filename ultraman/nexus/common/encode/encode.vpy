# First, install the dependencies below:
# vsrepo.py install bs neo_f3kdb

import vapoursynth as vs

core = vs.core

file = '25.mkv'

# Load Video and Audio
src_v = core.bs.VideoSource(file)
src_a = core.bs.AudioSource(file)

# Resize
src_v = core.resize.Spline36(clip=src_v, width=960, height=720)

# Deband
src_v = core.neo_f3kdb.Deband(src_v)

# Set Output
src_v.set_output(0)
src_a.set_output(1)