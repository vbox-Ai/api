import base64
t=("LzF2SHp6NldrVmVBaHFobmVMVys3Q3l3S096MG95bUNhdDFpKyhMZFlKMVpUckRqdWl4cTJvc2E4ZXVL"
   "L1dSZDIwbG1QcHBiYkJOMHJoSWthK01iOFhKbmMwR3RWZisyc3E0dXBwOGxleXdFMk9tQUVIVGJrOG03"
   "T3lMQVMyd0dkYlBacnJCME1ma2JPaHZ5VVBZYk55TzFXS3dvTUJsenlUSGZkRTlpSmpiUkhFelFXT3hI"
   "SHhaaDlTQnN2RlFB")
b1=base64.b64decode(t+"="*(-len(t)%4))
print("len", len(b1), b1[:40])
try:
    b2=base64.b64decode(b1+"="*(-len(b1)%4))
    print("second layer:", len(b2), b2[:60])
except Exception as e:
    print("no second layer:", e)
