from urllib.request import Request, urlopen

urls = [
    'https://www.instagram.com/example/?__a=1',
    'https://www.instagram.com/example/'
]

for url in urls:
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=12) as response:
            print('URL', url)
            print('STATUS', response.status)
            body = response.read(1000).decode('utf-8', 'ignore')
            print(body)
            print('---')
    except Exception as exc:
        print('URL', url)
        print('ERR', repr(exc))
        print('---')
