"""Pure gesture classifier; angle units are signed raw sensor counts."""
def signed(x):
    return x if x < 128 else x - 256

def decode(data):
    if len(data) != 9 or data[0] != 0xD0:
        return None
    return bool(data[3]), tuple(signed(x) for x in data[5:8])


def decode_battery(data):
    """Return battery percentage from a PawPrint V1.1 status report."""
    if (
        len(data) != 4
        or data[0] != 0x51
        or not 0x01 <= data[1] <= 0x06
        or data[2] != 0x03
    ):
        return None
    return data[3] if data[3] <= 100 else None


class Gesture:
    def __init__(self, axis=0, left=-60, right=60, hold=.5, motion=12, speed=35):
        self.axis, self.left, self.right = axis,left,right
        self.hold,self.motion,self.speed = hold,motion,speed
        self.reset()
    def reset(self):
        self.armed=False; self.start=None; self.last=None
        self.peak=0; self.axis_peak=0; self.velocity=0; self.dimming=False
        self.sent=None; self.sent_at=0
    def feed(self,t,pressed,angles):
        if self.last is not None and t-self.last[0] > .65:
            self.reset()
        prev=self.last; self.last=(t,angles)
        if not self.armed:
            self.armed=not pressed
            return None
        if not pressed:
            if self.start is None: return None
            duration=t-self.start[0]
            action=None
            if self.dimming:
                action=('brightness',self.target) if self.target != self.sent else None
            elif duration < self.hold and self.peak < self.motion: action=('color',None)
            elif duration >= self.hold and self.peak < self.motion: action=('off',None)
            self.start=None; self.dimming=False
            return action
        if self.start is None:
            self.start=(t,angles); self.peak=0; self.axis_peak=0; self.velocity=0
            self.dimming=False; self.sent=None; self.sent_at=0
            return None
        delta=[abs(a-b) for a,b in zip(angles,self.start[1])]
        self.peak=max(self.peak,*delta); self.axis_peak=max(self.axis_peak,delta[self.axis])
        if prev and t>prev[0]:
            self.velocity=max(self.velocity,abs(angles[self.axis]-prev[1][self.axis])/(t-prev[0]))
        if t-self.start[0]>=self.hold and (self.axis_peak>=self.motion or (self.axis_peak>=self.motion/2 and self.velocity>=self.speed)):
            self.dimming=True
        if self.dimming:
            self.target=round(max(0,min(1,(angles[self.axis]-self.left)/(self.right-self.left)))*100)
            if self.sent is None or (t-self.sent_at>=.2 and abs(self.target-self.sent)>=2):
                self.sent=self.target; self.sent_at=t
                return ('brightness',self.target)
        return None
