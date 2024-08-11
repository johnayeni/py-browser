import socket
import ssl
import sys
import tkinter

SCROLL_STEP = 100
HSTEP, VSTEP = 13, 18

class URL:
  def __init__(self, url):
    # Get the url scheme e.g http or https
    self.scheme, url = url.split('://', 1)
    assert self.scheme in ['http', 'https', 'file', 'view-source:http', 'view-source:https'], "Invalid scheme"

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

      #Check if the port is specified in the host
      if ":" in self.host:
        self.host, self.port = self.host.split(":", 1)
        self.port = int(self.port)

  def request(self, headers):
    # If the scheme is file, read the file and return the content
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

      # Set the default http version to 1.0
      http_version = "1.0"

      # Check if the connection is close and set the http version to 1.1
      # as close connection is only supported in http 1.1
      if "Connection" in request_headers and request_headers["Connection"] == "close":
        http_version = "1.1"

      # Send the request for the path to the host
      request = "GET {} HTTP/{}\r\n".format(self.path, http_version)
      for header in request_headers:
        request += "{}: {}\r\n".format(header, request_headers[header])
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

class Browser:
  def __init__(self, width=800, height=600):
    self.width = width
    self.height = height
    self.scroll = 0
    self.display_list = []
    self.window = tkinter.Tk()
    self.canvas = tkinter.Canvas(self.window, width=width, height=height)
    self.canvas.pack()
    self.bind_keys()

  def scroll_down(self, event):
    self.scroll += SCROLL_STEP
    self.draw()

  def scroll_up(self, event):
    self.scroll -= SCROLL_STEP
    self.draw()

  def bind_keys(self):
    self.window.bind("<Down>", self.scroll_down)
    self.window.bind("<Up>", self.scroll_up)

  def lex(self, body):
    text = "";
    in_tag = False
    index = 0
    for i in range(len(body)):
      if i != index:
        continue

      if body[i:-1].startswith("&lt;"):
        text += "<"
        index += 4
        continue

      if body[i:-1].startswith("&gt;"):
        text += ">"
        index += 4
        continue


      if body[i] == "<":
        in_tag = True
      elif body[i] == ">":
        in_tag = False
      elif not in_tag:
        text += body[i]
      index += 1
    return text


  def layout(self, text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
      display_list.append((cursor_x, cursor_y, c))
      cursor_x += HSTEP
      if cursor_x > self.width - HSTEP:
        cursor_x = HSTEP
        cursor_y += VSTEP
    return display_list

  def draw(self):
    # clear the canvas before drawing to prevent overlapping previous drawings
    self.canvas.delete("all")
    for x, y, c in self.display_list:
      # check if the current character is within the scroll range
      if y > self.scroll + self.height: continue
      if y + VSTEP < self.scroll: continue
      self.canvas.create_text(x, y - self.scroll, text=c)

  def load(self, url, headers):
    body = url.request(headers);

    # For the view-source scheme, the we do not need to parse the document
    if 'view-source:' in url.scheme:
      self.display_list = self.layout(body)
      self.draw()
      return
    text = self.lex(body)
    self.display_list = self.layout(text)
    self.draw()
    # Start the tkinter main loop to keep checking for events
    tkinter.mainloop()

if __name__ == "__main__":
  url = URL(sys.argv[1])

  headers = {}
  for arg in sys.argv[2:]:
    key, value = arg.split('=')
    headers[key] = value
  Browser().load(url, headers)
