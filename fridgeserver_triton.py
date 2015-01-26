# This program was written by Damaz de Jong, last time this line was updated was 2015 01 05
# v104


# R2D2 commands:
# EXIT      (no response)
# NAME
# VERSION
# TIME
# UPDATE    (no response)
# VERBOSE ##(no response)
# HAPPY     (returns status of dweet thread)

# VERBOSE LEVELS
# 0 critical/emergency only
# 1 add ERR
# 5 add important events

# 10 add info

# VADER COMMANDS (use with extreme caution)
# EXIT      (no response)
# FLUSH     (no response)
# PING      (response PONG)

# TODO
# more efficient questions to triton

import socket, select
import Queue
import threading
import time
import dweepy
import traceback
import sys

#
#   Put here all fridge dependent variables
#
execfile("local_settings.py")
#print triton_ip

exitflag= 0
version='104'
verbose=99

#be sure to check the channels of the cernox and RuO2


def printerr(message):
    if verbose>=1:
        print "ERR: "+message+" at "+time.asctime( time.localtime(time.time()) )
def printevent(message):
    if verbose>=5:
        print message+" at "+time.asctime( time.localtime(time.time()) )
def printinf(message):
    if verbose>=10:
        print message

#todo: check queue overflows
class UpdateThread (threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        global exitflag
        printinf("Starting " + self.name)
        #update(self.name, self.q)
        while not exitflag:
            #print "Updating"
            
            queueLock.acquire()
            if self.q.full():
                #print "ERR: CRITICAL! %s noticed Queue full, suspected that Queue thread dead" % self.name
                #print "waving exitflag at "+time.asctime( time.localtime(time.time()) )
                #exitflag=1
                printerr("update thread noticed queue full")

            else:         
                self.q.put(("UPDATE THREAD","R2D2:UPDATE"))
            queueLock.release()
            time.sleep(20)
        printinf("Exiting " + self.name)

class DweetThread (threading.Thread):
    def __init__(self, threadID, name, dq):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.dq = dq
    def run(self):
        global exitflag
        printinf("Starting " + self.name)
        #update(self.name, self.q)
        while not exitflag:
            dweetLock.acquire()
            if not self.dq.empty():
                data = self.dq.get()
                dweetLock.release()
                try:
                    dweepy.dweet_for(dweetname, data)
                except:
                    printerr("dweet failed")
                    #traceback.print_exc(file=sys.stdout)
            else:
                dweetLock.release()
                
            time.sleep(1)
            
        printinf("Exiting " + self.name)

class QueueThread (threading.Thread):
    def __init__(self, threadID, name, q, dq):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
        self.dq = dq
        #self.tritonsock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #variable for checking dweet thread
        self.happy=1
      
    def run(self):
        global exitflag
        global verbose
        printinf("Starting " + self.name)
        #update(self.name, self.q)
        self.triton_connect()
        while not exitflag:
            #print "Working"
            queueLock.acquire()
            if not workQueue.empty():
                data = self.q.get()
                queueLock.release()
                try:
                    self.requesthandler(data)
                except:
                    print "ERR: CRITICAL! request could not be handled and crashed!!!"
                    print "waving exitflag! at "+time.asctime( time.localtime(time.time()) )
                    traceback.print_exc(file=sys.stdout)
                    exitflag=1
            else:
                queueLock.release()
                time.sleep(0.1)
            #todo sleep(0.1)
            #time.sleep(0.1)
        printinf("Exiting " + self.name)
        self.triton_disconnect()
        
    def requesthandler(self, data):
        #print "%s processing %s" % (self.name, data)
        if data[1].startswith('R2D2:'):
            self.r2d2handler(data[0],data[1][5:])#pass on command stripping 'R2D2:'
        elif data[1].startswith('VADER:'):
            #this is none of my business
            pass
        elif data[1].startswith('READ:') or data[1].startswith('SET:'):
            response=self.tritonhandler(data[1])
            try:
                data[0].send(response)
                printinf("     reply: "+response)
            except:
                printerr("remote client unexpectedly gone")
            finally:
                data[0].shutdown(2)
                data[0].close()
        else:
            printerr(data[1]+" is not recognized as a command")

    def triton_connect(self):
        printevent('Connecting to triton')
        try:
            self.tritonsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tritonsock.connect((triton_ip, triton_port))
            self.tritonsock.settimeout(60)            
        except:
            printerr("could not connect to triton")

    def triton_disconnect(self):
        try:
            self.tritonsock.shutdown(2)
            self.tritonsock.close()
        except:
            printerr("could not disconnect, already closed")
            
            
    def tritonhandler(self, data):
        #print('connecting to fridge')
        #try:
        #    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #    sock.connect((triton_ip, triton_port))
        #except:
        #    print "ERR: could not connect to triton at "+time.asctime( time.localtime(time.time()) )
        #    return "ERR:CNCTT"
        for n in xrange(1, 5):
            r=self.tritoncommunicator(data)
            if not r == '':
                return r
            time.sleep(n)
        printerr("I tried many times but still failed")
        print data
        return "ERR:CNCTT"
        
    def tritoncommunicator(self, data):
        bufsize=1024
        r=''
        try:
            sent = self.tritonsock.send(data)
            r = self.tritonsock.recv(bufsize)
            #print(r)
        except socket.timeout:
            printerr("triton connection timeout")
            self.triton_connect()
        except socket.error as e:
            printerr("triton connection error")
            if verbose>=1:
                print "error({0}): {1}".format(e.errno, e.strerror)
            self.triton_connect()
        except:
            traceback.print_exc(file=sys.stdout)
            if verbose>=1:
                print "Unexpected error:", sys.exc_info()[0]
            self.triton_connect()

            #try:
            #    self.tritonsock.send(data)
            #    r = self.tritonsock.recv(bufsize)
            #except:
            #    print "ERR: triton communication error at "+time.asctime( time.localtime(time.time()) )
        finally:  
            return r
        
    def triton_getmctemp(self):
        try:
            #cold sensor
            t1=str(self.tritonhandler(coldsensor))
            t1=''.join([c for c in t1 if c in '1234567890.'])[1:]


            #hot sensor
            t2=str(self.tritonhandler(hotsensor))
            t2=''.join([c for c in t2 if c in '1234567890.'])[1:]
            try:
                if float(t1)<4.0 or float(t2)<4.0:
                    return float(t1)
                else:
                    return float(t2)
            except:
                #if this error is thrown, some exception is not caught
                printerr("float conversion error, suspecting some triton communication error for mctemp")
        except:
            print t1
            print t2
            traceback.print_exc(file=sys.stdout)
    def triton_getmagnetstatus(self):
        try:
            r=str(self.tritonhandler('READ:SYS:VRM:VECT\r\n'))
            if r.find("INVALID") == -1:
                if r.find('[')==-1:
                    #this should not happen
                    if r.find("timeout"):
                        printerr("magnet connection timeout")
                        return 2
                    #if this error is thrown, some exception is not caught
                    printerr("preventing splitting and float conversion error, suspecting some triton communication error")
                    return 2
                r=r.split('[')[1].split(']')[0]
                r.replace(" ","")
                r=r.split('T')
                if not len(r)==3:
                    return 2
                if abs(float(r[0]))<=0.00005 and abs(float(r[1]))<=0.00005 and abs(float(r[2]))<=0.00005:
                    return 0
                else:
                    return 1
            else:
                return 0
        except:
            traceback.print_exc(file=sys.stdout)
    def triton_getaction(self):
        action=str(self.tritonhandler('READ:SYS:DR:ACTN\r\n'))[17:].strip('\n')
        if action =='PCL':
            action = 'Precooling'
        if action =='EPCL':
            action = 'Empty precool loop'
        if action =='COND':
            action = 'Condensing'    
        if action =='NONE':
            if self.triton_getmctemp()<2:
                action = 'Circulating'
            #elif self.tritonhandler('READ:DEV:T2:TEMP:SIG:TEMP\r\n'):
            #    action = 'Standing by'
            else:
                action = 'Idle'     
        if action =='COLL':
            action = 'Collecting mixture' 
        return action
    
    def r2d2handler(self, sock, data):
        global exitflag
        global verbose
        if data.startswith('EXIT'):
            print "waving exitflag at "+time.asctime( time.localtime(time.time()) )
            exitflag=1
        elif data.startswith('VERBOSE'):
            print "changing verbose level at "+time.asctime( time.localtime(time.time()) )
            print "verbose was " +str(verbose)
            verbose=int(data[8:])# strip "VERBOSE "
            print "verbose is " +str(verbose)
        elif data.startswith('NAME'):
            try:
                sock.send('My name is: '+dweetname)
            except:
                print("ERR: R2D2 communication error")
        elif data.startswith('VERSION'):
            try:
                sock.send('version is: '+version)
            except:
                print("ERR: R2D2 communication error")
        elif data.startswith('TIME'):
            try:
                sock.send('my time is: '+time.asctime( time.localtime(time.time()) ))
            except:
                print("ERR: R2D2 communication error")
        elif data.startswith('HAPPY'):
            try:
                sock.send(str(self.happy))
            except:
                print("ERR: R2D2 communication error")
        elif data.startswith('UPDATE'):
            #print("dweeting!")
            #dweepy.dweet_for('Delft_LK2', {'Action': time.ctime(time.time()),'Status': 1,'MCtemp': 0,'water_tempin':0,'water_tempout':2,'P2':0})
            #this code need to be cleaned up!


            #TODO
            magstatus = self.triton_getmagnetstatus()
            
            MCtemp = self.triton_getmctemp()
            P2 = str(self.tritonhandler('READ:DEV:P2:PRES:SIG:PRES\r\n'))
            P2=''.join([c for c in P2 if c in '1234567890.'])[1:]
            CWin = str(self.tritonhandler('READ:DEV:C1:PTC:SIG:WIT\r\n'))
            CWin=''.join([c for c in CWin if c in '1234567890.'])[1:]
            CWout = str(self.tritonhandler('READ:DEV:C1:PTC:SIG:WOT\r\n'))
            CWout=''.join([c for c in CWout if c in '1234567890.'])[1:]
            
            action = self.triton_getaction()

            fridgestatus=self.tritonhandler('READ:SYS:DR:STATUS\r\n')
            if fridgestatus.startswith('STAT:SYS:DR:STATUS:OK'):
                fridgestatus=1
            else:
                fridgestatus=0
            
            lasstfill=''
            try:
                fh = open("lastfill.txt","r")
                lastfill=fh.read()
            except:
                printerr("problem with reading lastfill.txt")
                lastfill="0"
            finally:
                fh.close()


            #try:
            #    dweepy.dweet_for(dweetname, {'Action': action,'Status': magstatus,'MCtemp': MCtemp,'water_tempin':CWin,'water_tempout':CWout,'P2':P2,'server':time.time(),'lastfill':lastfill,'fridgestatus':fridgestatus})
            #except:
            #    printerr("dweet failed")
            #    traceback.print_exc(file=sys.stdout)
            dweetLock.acquire()
            if self.dq.full():
                self.happy=0
                printerr("Queue Thread noticed dweetqueue full, ignoring")
            else:
                self.happy=1
                self.dq.put({'Action': action,'Status': magstatus,'MCtemp': MCtemp,'water_tempin':CWin,'water_tempout':CWout,'P2':P2,'server':time.time(),'lastfill':lastfill,'fridgestatus':fridgestatus})
            dweetLock.release()
            
        else:
            printerr(data+" is not recognized as a R2D2 command")
        
class SocketThread (threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
    def run(self):
        global exitflag
        printinf("Starting " + self.name)
        #create server socket
    
        # List to keep track of socket descriptors
        CONNECTION_LIST = []
        RECV_BUFFER = 4096 # Advisable to keep it as an exponent of 2
        PORT = 5611
     
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind(("0.0.0.0", PORT))
        #serversocket.bind(("", PORT))
        serversocket.listen(5)
    
        printinf("Fridgeserver started on " + str(socket.gethostname()) + ":" + str(PORT))
        
        # Add server socket to the list of readable connections
        CONNECTION_LIST.append(serversocket)
        while not exitflag:
        #do stuff
            read_sockets,write_sockets,error_sockets = select.select(CONNECTION_LIST,[],[],60)
        
            for sock in read_sockets:
                    #New connection
                if sock == serversocket:
                    # Handle the case in which there is a new connection recieved through server_socket
                    sockfd, addr = serversocket.accept()
                    CONNECTION_LIST.append(sockfd)
                    if verbose>=10:
                        print "Client (%s, %s) connected" % addr
             
                    #Some incoming message from a client
                else:
                        # Data recieved from client, process it
                    try:
                        #In Windows, sometimes when a TCP program closes abruptly,
                        # a "Connection reset by peer" exception will be thrown
                        data = sock.recv(RECV_BUFFER)
                        if data:
                            #how do i know if command or answer is complete
                            #i have to be compatible with the triton server documentation, that propably mean using \r\n as en delimiter
                            printinf('     Received: '+data)
                            if data.startswith('VADER:EXIT'):
                                print "DETECTED EMERGENCY EXIT COMMAND AT "+time.asctime( time.localtime(time.time()) )
                                print "waving exit flag!"
                                exitflag=1
                            if data.startswith('VADER:FLUSH'):
                                print "DETECTED EMERGENCY FLUSH AT "+time.asctime( time.localtime(time.time()) )
                                queueLock.acquire()
                                self.q.queue.clear()
                                queueLock.release()
                            if data.startswith('VADER:PING'):
                                sock.send("PONG")
                                sock.shutdown(2)
                                sock.close()

                            queueLock.acquire()
                            if self.q.full():
                                #print "ERR: CRITICAL! %s noticed Queue full, suspected that Queue thread dead" % self.name
                                #print "waving exitflag"
                                #exitflag=1
                                printerr("Socket Thread noticed queue full, replying full error")

                                sock.send("ERR:QFE")
                                sock.shutdown(2)
                                sock.close()
                            else:                            
                                self.q.put((sock,data))
                            queueLock.release()
                        CONNECTION_LIST.remove(sock)
                    except:
                        if verbose>=1:
                            print "ERR: Client (%s, %s) is offline" % addr
                        sock.close()
                        CONNECTION_LIST.remove(sock)
                        continue


    
        #close server socket
        printinf("closing serversocket...")
        serversocket.close()
        printinf("Exiting " + self.name)


    
if __name__ == "__main__":
    queueLock = threading.Lock()
    workQueue = Queue.Queue(100)
    
    dweetLock = threading.Lock()
    dweetQueue = Queue.Queue(10)

    print 'Server started on '+time.asctime( time.localtime(time.time()) )


    queuethread=QueueThread(1,"Queue Thread", workQueue, dweetQueue)
    queuethread.start()
    time.sleep(1)
    dweetthread=DweetThread(1,"Dweet Thread", dweetQueue)
    dweetthread.start()
    time.sleep(1)
    socketthread=SocketThread(3,"Socket Thread", workQueue)
    socketthread.start()
    time.sleep(1)
    updatethread =UpdateThread(2, "Update Thread", workQueue)
    updatethread.start()

    #time.sleep(5)
    #print 'waving exitflag because this is a dummey version of the program'
    #exitflag=1





    socketthread.join()
    updatethread.join()
    queuethread.join()
    dweetthread.join()
    print("byebye at "+time.asctime( time.localtime(time.time()) ))
