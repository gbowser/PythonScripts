import urllib.request
req=urllib.request.Request("https://en.wikipedia.org/wiki/Main_Page")


import urllib.request
from urllib.error import URLError, HTTPError

url = "https://www.bbc.co.uk/news"

# Build the request object
req = urllib.request.Request(url)

try:
    response = urllib.request.urlopen(req)

except HTTPError as e:
    print('The server returned error code', e.code)

except URLError as e:
    print('Failed to reach server at {} for the following reason:\n{}'
          .format(url, e.reason))

else:
    # the response came back OK

    # Read the content returned from the server
    content = response.read()

    # The content is returned as a bytestring
    # Convert it to a normal Python string
    html = content.decode('utf-8')

    print(html)