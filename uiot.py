import socket
import threading
import shlex
from tdb import tdb
import random
import string
import re
import queue

q=queue.Queue()
server_funcs = ["sub", "unsub","ask","say", "mysubs", "myclients"]

clients = {}
conns = {}

def mysubs(args, usr):
  if len(usr.subs) == 0: return ";"
  return ";".join(usr.subs)

def myclients(args, usr):
  global clients
  if len(clients[usr.name]) == 0: return ";"
  return ";".join(clients[usr.name])

def sub(args, usr):
  global clients
  if args[1] in clients.keys():
    usr.subs.append(args[1])
  else: return "invalid_user"
  if args[1] == usr.name: return "cannot_subscribe_self"
  clients[args[1]].append(usr.name)
  return "OK"

def unsub(args, usr):
  global clients
  if args[1] in usr.subs:
    usr.subs.remove(args[1])
  else: return "user_not_subscribed"
  if args[1] == usr.name: return "cannot_subscribe_self"
  clients[args[1]].remove(usr.name)
  return "OK"

def say(args, usr):
  global clients, conns
  if len(args) < 3: return "not_enough_args"
  if len(args) == 4:
    tosend = args[3].split(";")
    for i in tosend: # check all clients are subscribers
      if i not in clients[usr.name]:
        return "no_such_subscriber {}".format(i)
  else: tosend = clients[usr.name] # default: send to all subscribers
  for c in tosend: # send
    # ! key value from
    syntx = "! "+args[1]+" "+args[2]+" "+usr.name
    conns[c].send(syntx.encode())
  return "OK"

def ask(args, usr):
  global clients, conns
  if len(args) < 2: return "not_enough_args"
  if len(args) >= 3:
    tosend = args[2].split(";")
    for i in tosend: # check all clients are subscribers
      if i not in clients[usr.name]:
        return "no_such_subscriber {}".format(i)
  else: tosend = clients[usr.name] # default: send to all subscribers

  for c in tosend: # send
    # ? key from
    syntx = "? "+args[1]+" "+usr.name
    conns[c].send(syntx.encode())
  return "OK"


# database
db = tdb("users.tdb")

class user:
  def __init__(self, name):
    self.name = name
    self.subs = []

def gen_key(length):
    letters = string.ascii_lowercase
    key  = ''.join(random.choice(letters) for i in range(length))
    return key

def parse_args(data):
  data = shlex.split(data.decode('utf-8'))
  if len(data) <= 0 or len(data) >= 4: return None
  return data[0:4]

def handle_client(client):
  global db, clients, user, conns
  # authentication
  client.send("uiot v0.1\n".encode())
  client.send("? username".encode())
  name = client.recv(2024).decode("utf-8")
  name = re.sub('[^A-Za-z0-9]+', '', name)
  if name in db.db.keys():
    client.send("? authkey".encode())
    keY = client.recv(2024).decode("utf-8")
    keY = re.sub('[^A-Za-z0-9]+', '', keY)
    if keY == db.db[name]: # login success
      client.send("auth_ok".encode())
    else:
      client.send("auth_fail".encode())
      client.close()
      return
  else:
    keY = gen_key(8)
    db.db[name] = keY
    q.put(db.commit(db=db.db))
    client.send("! authkey {}".format(keY).encode())

  usr = user(name)
  clients[name] = []
  conns[name] = client

  while True:
    data = client.recv(2024)
    if not data:break
    args = parse_args(data)
    if not args: continue

    if args[0] in server_funcs:
      client.send(globals()[args[0]](args,usr).encode("utf-8"))
    else:
      client.send("inavalid_command".encode("utf-8"))
  client.close()

def start_server(host="localhost", port=8809):
  global lock
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.bind((host, port))
  sock.listen(5)
  print("uiot server running on {}:{}".format(host, port))
  try:
    while True: # accept clients
      client, addr = sock.accept()
      print("> connection_from {}".format(addr))
      t = threading.Thread(target=handle_client, args=(client,))
      t.daemon = True
      t.start()
  except KeyboardInterrupt:
    print("Closing server")
    sock.close()

start_server()
