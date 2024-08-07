import socket
import ssl
import sys

class URL:
  def __init__(self, url):
    # Get the url scheme e.g http or https
    self.scheme, url = url.split('://', 1)
    assert self.scheme in ['http', 'https', 'file', 'view-source:http', 'view-source:https']

    if self.scheme == 'file':
      assert url.endswith('.txt'), "Only .txt files are supported"
      self.path = url
    else:
      if 'https' in self.scheme:
        self.port = 443
      elif 'http' in self.scheme:
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

  def request(self, headers):

    if self.scheme == 'file':
      with open(self.path) as f:
        return f.read()
    else:
      request_headers = {
        "HOST": self.host,
        "User-Agent": "python/{}".format(sys.version_info.major),
        **headers
      }


      # Create a socket to communicate with the host using the system OS
      s = socket.socket(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
      )

      # Connect to the host
      s.connect((self.host, self.port))

      # Wrap the socket with SSL to make it secure
      if 'https' in self.scheme:
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=self.host)

      http_version = "1.0"

      if "Connection" in request_headers and request_headers["Connection"] == "close":
        http_version = "1.1"

      # Send the request for the path to the host
      request = "GET {} HTTP/{}\r\n".format(self.path, http_version)
      for header in request_headers:
        request += "{}: {}\r\n".format(header, request_headers[header])
      request += "\r\n"

      # print(request)
      # print("\n")

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


def show(content):
  print(content, end="")

def parse(body):
  parsed = "";
  in_tag = False
  index = 0
  for i in range(len(body)):
    if i != index:
      continue

    if body[i:-1].startswith("&lt;"):
      parsed += "<"
      index += 4
      continue

    if body[i:-1].startswith("&gt;"):
      parsed += ">"
      index += 4
      continue


    if body[i] == "<":
      in_tag = True
    elif body[i] == ">":
      in_tag = False
    elif not in_tag:
      parsed += body[i]
    index += 1
  return parsed

def load(url, headers):
  body = url.request(headers);

  if 'view-source:' in url.scheme:
    show(body)
    return

  parsed = parse(body)
  show(parsed)

if __name__ == "__main__":
  url = URL(sys.argv[1])

  headers = {}
  for arg in sys.argv[2:]:
    key, value = arg.split('=')
    headers[key] = value
  load(url, headers)