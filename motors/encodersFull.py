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
        
        self.prevA = 0
        self.prevB = 0

        self.daemon.set_mode(self.pinA, pigpio.INPUT)
        self.daemon.set_mode(self.pinB, pigpio.INPUT)
        
        self.daemon.set_pull_up_down(self.pinA, pigpio.PUD_UP)
        self.daemon.set_pull_up_down(self.pinB, pigpio.PUD_UP)

        # self.daemon.set_glitch_filter(self.pinA, 10)
        # self.daemon.set_glitch_filter(self.pinB, 10)

        self.pinAFunction = self.daemon.callback(self.pinA, pigpio.EITHER_EDGE, self.onPinUpdate)
        self.pinBFunction = self.daemon.callback(self.pinB, pigpio.EITHER_EDGE, self.onPinUpdate)

    # runs when pin a goes to rising edge. See then value of B to see if going up or down
    def onPinUpdate(self, _gpio, aPinVal, measuringTime):
        currA = self.daemon.read(self.pinA)
        currB = self.daemon.read(self.pinB)
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
rightEncoderPinA =  22
rightEncoderPinB = 23
leftEncoderPinA = 17
leftEncoderPinB = 27

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
    
    await asyncio.sleep(5)

    print("Finished testing!")

    task1.cancel()
    task2.cancel()

    leftEncoder.pinAFunction.cancel()
    rightEncoder.pinAFunction.cancel()
    pioDaemon.stop()



asyncio.run(main())
