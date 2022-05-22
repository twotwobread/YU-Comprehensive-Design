from init.variable import IP
from web import app
from init.server import ServerSocket

if __name__ == "__main__":
    #server = ServerSocket(IP, 20)
    app.run(host=IP, port=9080)