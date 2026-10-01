import httpx, asyncio, os
async def main():
    token = os.environ.get('TOKEN')
    headers = {'Authorization': f'Bearer {token}'}
    async with httpx.AsyncClient() as client:
        r1 = await client.post('http://localhost:8000/api/v1/conversations', json={'title':'Test'}, headers=headers)
        conv_id = r1.json()['id']
        r3 = await client.post('http://localhost:8000/api/v1/runs', json={'request':'Investigate our recent API latency.', 'conversation_id': conv_id}, headers=headers)
        print('Agent Run POST:', r3.status_code, r3.text)
        await asyncio.sleep(5)
        r4 = await client.get('http://localhost:8000/api/v1/runs', headers=headers)
        runs = [r for r in r4.json().get('runs', []) if r.get('conversation_id') == conv_id]
        if runs:
            print(f"Latest Run Status: {runs[0]['status']}")
            if runs[0]['error_request']:
                print(f"Error Message: {runs[0]['error_request']}")

        r2 = await client.get(f'http://localhost:8000/api/v1/conversations/{conv_id}/requests', headers=headers)
        print('Messages:', len(r2.json().get('items', [])))
        for m in r2.json().get('items', []):
            print(f"{m['role']}: {m['content']}")
asyncio.run(main())
