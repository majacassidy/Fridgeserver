import time

fh = open("lastfill.txt","w")
fh.write(str(time.time()))
fh.close()

fh = open("lastfill.txt","r")
print fh.read()
fh.close()
