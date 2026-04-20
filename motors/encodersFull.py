import pigpio
import asyncio

class Encoder:
    def __init__(self, daemon, pinA, pinB, direction):
        self.daemon = daemon
        self.pinA = pinA
        self.pinB = pinB

        self.encoderDirection = direction

        self.tick = 0
        self.prevTick = 0

        self.lookup = [0, -1, 1, 0, 
                       1, 0, 0, -1,
                       -1, 0, 0, 1,
                       0, 1, -1, 0]
        
        self.daemon.set_mode(self.pinA, pigpio.INPUT)
        self.daemon.set_mode(self.pinB, pigpio.INPUT)

        self.daemon.set_pull_up_down(self.pinA, pigpio.PUD_UP)
        self.daemon.set_pull_up_down(self.pinB, pigpio.PUD_UP)

        self.daemon.set_glitch_filter(self.pinA, 5)
        self.daemon.set_glitch_filter(self.pinB, 5)

        # Seed from actual pin levels after pull-ups settle
        import time; time.sleep(0.01)
        self.prevA = self.daemon.read(self.pinA)
        self.prevB = self.daemon.read(self.pinB)

        self.pinAFunction = self.daemon.callback(self.pinA, pigpio.EITHER_EDGE, self.onPinUpdate)
        self.pinBFunction = self.daemon.callback(self.pinB, pigpio.EITHER_EDGE, self.onPinUpdate)

    def onPinUpdate(self, gpio, level, _tick):
        # Use the level delivered by the callback — faster and more accurate than re-reading
        if gpio == self.pinA:
            currA, currB = level, self.daemon.read(self.pinB)
        else:
            currA, currB = self.daemon.read(self.pinA), level
        index = (self.prevA << 3) | (self.prevB << 2) | (currA << 1) | currB
        self.tick += self.lookup[index]
        self.prevA = currA
        self.prevB = currB

    def getTick(self):
        return self.tick

    async def handlePrint(self):
        while True:
            if(self.prevTick != self.tick):
                print(f"The {self.encoderDirection} encoder is {self.tick}")
                self.prevTick = self.tick
            await asyncio.sleep(0.01)

# green is A, blue is B
rightEncoderPinA =  17
rightEncoderPinB = 27
leftEncoderPinA = 24
leftEncoderPinB = 25

pioDaemon = pigpio.pi()

if not pioDaemon.connected:
    print("Fail!")
    exit()

leftEncoder = Encoder(pioDaemon, leftEncoderPinA, leftEncoderPinB, "left")
rightEncoder = Encoder(pioDaemon, rightEncoderPinA, rightEncoderPinB, "right")

print("encoders success!")

async def main():
    task1 = asyncio.create_task(leftEncoder.handlePrint())
    task2 = asyncio.create_task(rightEncoder.handlePrint())
    
    await asyncio.sleep(100)

    print("Finished testing!")

    task1.cancel()
    task2.cancel()

    leftEncoder.pinAFunction.cancel()
    rightEncoder.pinAFunction.cancel()
    pioDaemon.stop()



asyncio.run(main())
