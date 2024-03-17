import mimetypes
import pathlib
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import socket
from multiprocessing import Process
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import logging


uri = "mongodb://mongodb:27017"


def send_data_to_socket(data):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        server = "", 5000
        sock.connect(server)
        logging.info("Sending to socket")
        sock.sendall(data)
        logging.info("Receive answer")
        answer = sock.recv(1024)
        logging.info(str(answer))
        sock.close()


def save_data(data):
    client = MongoClient(uri, server_api=ServerApi("1"))
    db = client.final_hw
    logging.info("Save to Mongo")
    logging.info(str(data))
    data_parse = urllib.parse.unquote_plus(data.decode())
    try:
        data_dict = {
            key: value for key, value in [el.split("=") for el in data_parse.split("&")]
        }
        data_dict["date"] = str(datetime.now())
        logging.info("Time added")
        db.messages.insert_one(data_dict)
        logging.info("Time added")
    except Exception as e:
        logging.error(e)
    finally:
        client.close()


def run_socket_server(ip, port):
    addr = (ip, port)
    server = socket.create_server(addr, family=socket.AF_INET)
    server.listen()
    try:
        while True:
            serveOn = server.accept()
            data = serveOn[0].recv(1024)
            logging.debug(data)
            save_data(data)
            serveOn[0].close()
    except Exception as e:
        logging.error(e)
    finally:
        server.close()


class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        data = self.rfile.read(int(self.headers["Content-Length"]))
        print(data)
        send_data_to_socket(data)
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == "/":
            self.send_html_file("index.html")
        elif pr_url.path == "/message":
            self.send_html_file("message.html")
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file("error.html", 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", "text/plain")
        self.end_headers()
        with open(f".{self.path}", "rb") as file:
            self.wfile.write(file.read())


def run_http_server(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ("", 3000)
    http = server_class(server_address, handler_class)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(threadName)s %(message)s")
    logging.info("Socket server starting")
    socket_server = Process(target=run_socket_server, args=("", 5000))
    socket_server.start()
    logging.info("Socket server started")
    http_server = Process(target=run_http_server)
    http_server.start()
    logging.info("HTTP server started")
