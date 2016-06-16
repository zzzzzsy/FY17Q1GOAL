import math


class Calculate:
    def __init__(self, val):
        self.val = [float(item) for item in val]

    def mid(self):
        if len(self.val) < 1:
            return None
        else:
            seq = self.val
            seq.sort()
            return seq[len(seq) // 2]

    def percentile(self, p):
        if len(self.val) < 1:
            value = None
        elif p >= 100:
            print('ERROR: percentile must be < 100.  you supplied: %s\n' % p)
            value = None
        else:
            seq = self.val
            seq.sort()
            print(seq)
            index = int(len(self.val) * (p / 100))
            if len(self.val) * p % 100 == 0:
                value = seq[index - 1]
            else:
                value = (seq[index - 1] + seq[index]) / 2
        return value

a = []
for i in range(101):
    a.append(i)
c = Calculate(a)
print(c.percentile(90))
print(a)

