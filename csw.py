import time


class ABC():
    def __init__(self):
        self.txt = open('wenjian.txt', 'w')

    def woken(self):
        for i in range(20):
            time.sleep(1)
            self.txt.write(str(i))
            # self.txt.flush()



a = ABC()
a.woken()