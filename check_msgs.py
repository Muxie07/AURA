import urllib.request, json

req = urllib.request.Request('http://localhost:8000/api/v1/auth/token', method='POST', data=json.dumps({'email': 'demo@aura-sre.com', 'password': 'demo1234'}).encode(), headers={'Content-Type': 'application/json'})
token = json.loads(urllib.request.urlopen(req).read().decode())['access_token']

req2 = urllib.request.Request('http://localhost:8000/api/v1/conversations', headers={'Authorization': 'Bearer ' + token})
convs = json.loads(urllib.request.urlopen(req2).read().decode())['items']

for conv in convs[:10]:
    conv_id = conv['id']
    req3 = urllib.request.Request(
        f'http://localhost:8000/api/v1/conversations/{conv_id}/messages',
        headers={'Authorization': 'Bearer ' + token}
    )
    msgs = json.loads(urllib.request.urlopen(req3).read().decode())['items']
    for m in msgs:
        if m['role'] == 'assistant' and '**' in m['content'] and 'quotation' not in m['content']:
            print('FOUND MARKDOWN MESSAGE:')
            print(m['content'][:600])
            print('---')
            break
