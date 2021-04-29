from condig import host
import socket

sock = socket.socket()
sock.bind((host, 9090))
sock.listen(1)
conn, addr = sock.accept()

print 'connected:', addr

data = conn.recv(4096)
b = data.decode('utf-8').split(' ')[1]
conn.send(b)

conn.close()
