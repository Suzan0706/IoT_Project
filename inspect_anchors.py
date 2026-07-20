import urllib.request, re
url='http://127.0.0.1:8000/'
with urllib.request.urlopen(url) as r:
    c=r.read().decode()
# print all domain-tab anchors exactly
for m in re.finditer(r'<a [^>]*domain-tab[^>]*>', c):
    print(repr(m.group(0)))
# also any <a href containing domain=
for m in re.finditer(r'<a [^>]*href="[^"]*domain=[^"]*"[^>]*>', c):
    print('HREF:', m.group(0)[:120])
