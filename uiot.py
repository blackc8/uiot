import socket
import threading
from _thread import *
import shlex
from tdb import tdb
import random
import string
import re
import queue

server_funcs = ["subscribe", "unsubscribe"]
clients = {}
q = queue.Queue()

def subscribe(args, usr):
  global clients
  if args[1] in clients.keys():
    usr.subs.append(args[1])
  else: return "invalid_user"
  if args[1] == usr.name: return "cannot_subscribe_self"
  clients[args[1]].append(usr.name)
  return "OK"

def unsubscribe(args, usr):
  global clients
  if args[1] in usr.subs:
    usr.subs.remove(args[1])
  else: return "user_not_subscribed"
  if args[1] == usr.name: return "cannot_subscribe_self"
  clients[args[1]].remove(usr.name)
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
  if len(data) <= 0 or len(data) >= 3: return None
  return data[0:4]

def handle_client(client):
  global db, clients, user, q
  # authentication
  client.send("uiot v0.1\n".encode())
  client.send("? username".encode())
  name = client.recv(2024).decode("utf-8")
  name = re.sub('[^A-Za-z0-9]+', '', name)
  if name in db.db.keys():
    client.send("? authkey".encode())
    key = client.recv(2024).decode("utf-8")
    key = re.sub('[^A-Za-z0-9]+', '', key)
    if key == db.db[name]: # login success
      client.send("auth_ok".encode())
    else:
      client.send("auth_fail".encode())
      client.close()
      return
  else:
    keY = gen_key(8)
    db.db[name] = keY
    q.put(db.commit())
    client.send("authkey={}".format(keY).encode())

  usr = user(name)
  clients[name] = []

  while True:
    data = client.recv(2024)
    if not data:break
    args = parse_args(data)
    if not args: continue

    if args[0] in server_funcs:
      client.send(globals()[args[0]](args,usr).encode("utf-8"))
    else:
      client.send("inavalid_command".encode("utf-8"))

def start_server(host="localhost", port=8809):
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.bind((host, port))
  sock.listen(5)
  print("uiot server running on {}:{}".format(host, port))

  try:
    while True: # accept clients
      client, addr = sock.accept()
      print("> connection_from {}".format(addr))
      start_new_thread(handle_client, (client, ))
  except KeyboardInterrupt:
    print("Closing server")
    sock.close()

start_server()
