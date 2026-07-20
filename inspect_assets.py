import urllib.request, re
url='http://127.0.0.1:8000/'
with urllib.request.urlopen(url) as r:
    c=r.read().decode()
for m in re.finditer(r'<link[^>]*rel="stylesheet"[^>]*>', c):
    print(m.group(0))
print('---JS scripts---')
for m in re.finditer(r'<script[^>]*src="[^"]*"[^>]*>', c):
    print(m.group(0))
