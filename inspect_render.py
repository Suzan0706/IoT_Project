import urllib.request, re
url='http://127.0.0.1:8000/'
with urllib.request.urlopen(url) as r:
    c=r.read().decode()

# Extract all <script> blocks and look for the domain filter one
blocks = re.findall(r'<script>(.*?)</script>', c, re.DOTALL)
for b in blocks:
    if 'loadDomain' in b:
        print('FOUND DOMAIN SCRIPT, length', len(b))
        print(b[:400])
        print('...')
        print(b[-400:])
        break
else:
    print('DOMAIN SCRIPT NOT FOUND IN RENDERED PAGE')

# Check for any obvious template artifacts left in output
for bad in ['{%', '%}', '{{']:
    if bad in c:
        print('TEMPLATE ARTIFACT LEAKED:', bad)
