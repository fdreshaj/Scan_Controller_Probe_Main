response = bytes.fromhex("00ffe000100000baf2051e80e10011000000ee050000")
velocity = response[9] + (response[10] << 8)
print("Velocity:", velocity)