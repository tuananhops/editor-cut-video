#!/usr/bin/env python3
"""Optional: rewrite a CTranslate2 model.bin with float16 weights as float32 (e.g. large-v3),
so compute_type=float32 loads without an fp16->fp32 conversion peak.
usage: ct2_f16_to_f32.py SRC_DIR/model.bin DST_DIR/model.bin   (copy config.json, tokenizer.json,
       vocabulary.* , preprocessor_config.json to DST_DIR yourself; then --model DST_DIR)"""
import struct
import sys

import numpy as np

src, dst = sys.argv[1], sys.argv[2]
fi, fo = open(src, "rb"), open(dst, "wb")


def ri(fmt):
    b = fi.read(struct.calcsize(fmt))
    fo.write(b)
    return struct.unpack(fmt, b)[0]


def rs():
    n = struct.unpack("H", fi.read(2))[0]
    s = fi.read(n)
    fo.write(struct.pack("H", n))
    fo.write(s)
    return s[:-1].decode()


ver = ri("I"); name = rs(); rev = ri("I"); nv = ri("I")
print(ver, name, rev, nv)
for _ in range(nv):
    rs(); rank = ri("B"); [ri("I") for _ in range(rank)]
    dt = struct.unpack("B", fi.read(1))[0]
    nb = struct.unpack("I", fi.read(4))[0]
    data = fi.read(nb)
    if dt == 4:  # float16
        data = np.frombuffer(data, dtype=np.float16).astype(np.float32).tobytes()
        dt = 0
    fo.write(struct.pack("B", dt)); fo.write(struct.pack("I", len(data))); fo.write(data)
fo.write(fi.read())  # aliases
print("done")
