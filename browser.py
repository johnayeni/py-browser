import socket
import ssl

class URL:
  def __init__(self, url):
    # Get the url scheme e.g http or https
    self.scheme, url = url.split('://', 1)
    assert self.scheme in ['http', 'https']

    if self.scheme == 'https':
      self.port = 443
    elif self.scheme == 'http':
      self.port = 80

    # check if the current path is the root path
    if "/" not in url:
      url = url + "/"

    # Separate the host and the path
    self.host, url = url.split('/', 1)
    self.path = "/" + url

    if ":" in self.host:
      self.host, self.port = self.host.split(":", 1)
      self.port = int(self.port)

  def request(self):
    # Create a socket to communicate with the host using the system OS
    s = socket.socket(
      family=socket.AF_INET,
      type=socket.SOCK_STREAM,
      proto=socket.IPPROTO_TCP,
    )

    # Connect to the host
    s.connect((self.host, self.port))

    # Wrap the socket with SSL to make it secure
    if self.scheme == 'https':
      ctx = ssl.create_default_context()
      s = ctx.wrap_socket(s, server_hostname=self.host)

    # Send the request for the path to the host
    request = "GET {} HTTP/1.0\r\n".format(self.path)
    request += "HOST: {}\r\n".format(self.host)
    request += "\r\n"
    s.send(request.encode('utf8'))

    # Read the incoming responses from the host until a new line is found
    response = s.makefile("r", encoding="utf8", newline="\r\n")

    # Get the status details of the response
    statusline = response.readline()
    version, status, explanation = statusline.split(" ", 2)


    # Get the headers of the response
    response_headers = {}
    while True:
      line = response.readline()
      if line == "\r\n": break
      header, value = line.split(":", 1)
      response_headers[header.casefold()] = value.strip()

    assert "transfer-encoding" not in response_headers
    assert "content-encoding" not in response_headers

    # Get the content of the response
    content = response.read()

    return content

def show(body):
  in_tag = False
  for c in body:
    if c == "<":
      in_tag = True
    elif c == ">":
      in_tag = False
    elif not in_tag:
      print(c, end="")

def load(url):
  body = url.request();
  show(body)

if __name__ == "__main__":
  import sys
  url = URL(sys.argv[1])
  load(url)