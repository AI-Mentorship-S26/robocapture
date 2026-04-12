import rotaryio
import time
from board import *

enc = rotaryio.IncrementalEncoder(22, 23)
last_position = None

while True:
    position = enc.position
    print(position)
