import urllib.request
req = urllib.request.Request('https://www.instagram.com/example/?__a=1', headers={'User-Agent':'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=15) as r:
    print(r.status)
    print(r.read(500).decode('utf-8', 'ignore'))
