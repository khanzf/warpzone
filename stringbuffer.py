#!/usr/bin/python

class stringBuffer(list):
    def __init__(self):
        super(stringBuffer, self).__init__()

    def put(self, newmsg):
        for x in newmsg: self.append(x)

    def peek(self, count):
        return ''.join([self[x] for x in range(count)])

    def get(self, count = -1):
        tmplen = self.__len__()
        if tmplen == 0:
            return ''
        if tmplen < count:
            count = tmplen
        if count == -1:
            count = self.__len__()
        return ''.join([self.pop(0) for x in range(count)])

    def length(self):
        return self.__len__()

