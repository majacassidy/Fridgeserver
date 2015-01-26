# telnet program example
import socket, select, string, sys
import traceback
 
#main function
if __name__ == "__main__":
     
   
    #host = "127.0.0.1"
    host="131.180.116.101"
    port = 5611
     
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
     
    # connect to remote host
    try :
        s.connect((host, port))
    except :
        print 'Unable to connect'
        print "Unexpected error:", sys.exc_info()[0]
        traceback.print_exc(file=sys.stdout)
        sys.exit()   
     
    print 'Connected to remote host. Start sending messages'
    try:
        s.send('R2D2:EXIT\r\n')
        #s.send('R2D3:blah\r\n')
    except:
        print 'sending failed'
    finally:
        s.shutdown(2)
        s.close()

    print 'exit'
