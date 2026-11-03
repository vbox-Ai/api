import base64
from Crypto.Cipher import AES
t=("LzF2SHp6NldrVmVBaHFobmVMVys3Q3l3S096MG95bUNhdDFpKyhMZFlKMVpUckRqdWl4cTJvc2E4ZXVL"
   "L1dSZDIwbG1QcHBiYkJOMHJoSWthK01iOFhKbmMwR3RWZisyc3E0dXBwOGxleXdFMk9tQUVIVGJrOG03"
   "T3lMQVMyd0dkYlBacnJCME1ma2JPaHZ5VVBZYk55TzFXS3dvTUJsenlUSGZkRTlpSmpiUkhFelFXT3hI"
   "SHhaaDlTQnN2RlFB")
b=base64.b64decode(t+"="*(-len(t)%4))
keys=[b"xPxo2S5uGPhKHx5g", b"0a1b2c3d4e5f6789", b"hyfr6iyPZMZfJFEc"]
ivs=[b"\0"*16]+keys
for k in keys:
    for iv in ivs:
        for mode in ("CBC","ECB"):
            try:
                c = AES.new(k, AES.MODE_CBC, iv) if mode=="CBC" else AES.new(k, AES.MODE_ECB)
                p = c.decrypt(b)
            except Exception as e:
                continue
            printable = sum(1 for x in p if 32 <= x < 127 or x in (9,10,13))
            if printable > len(p)*0.8:
                print(mode, k[:8], iv[:8], "->", p[:120])
