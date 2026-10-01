import asyncio, httpx
async def main():
    async with httpx.AsyncClient() as client:
        r = await client.post('http://localhost:8000/api/v1/auth/token', json={'email':'demo@aura-sre.com','password':'demo1234'})
        token = r.json()['access_token']
        headers = {'Authorization': 'Bearer ' + token}
        
        # Test 1: Analysis
        print('--- TEST 1: Analysis ---')
        r1 = await client.post('http://localhost:8000/api/v1/conversations', json={'title':'System Analysis'}, headers=headers)
        conv1_id = r1.json()['id']
        req1 = {'conversation_id': conv1_id, 'request': 'Analyze the recent system performance and tell me what I should investigate first.'}
        r2 = await client.post('http://localhost:8000/api/v1/runs', json=req1, headers=headers)
        run1_id = r2.json()['run_id']
        print('Started Run 1:', run1_id)
        
        for i in range(20):
            await asyncio.sleep(2)
            r3 = await client.get('http://localhost:8000/api/v1/runs/' + run1_id, headers=headers)
            status = r3.json()['status']
            print('Status 1:', status)
            if status in ('completed', 'failed', 'awaiting_approval'):
                break
        
        r4 = await client.get('http://localhost:8000/api/v1/conversations/' + conv1_id + '/messages', headers=headers)
        for msg in r4.json().get('items', []):
            print(msg.get('role').upper() + ': ' + msg.get('content'))
            
        # Test 2: Approval required action (quotation)
        print('\n--- TEST 2: Approval ---')
        r5 = await client.post('http://localhost:8000/api/v1/conversations', json={'title':'Quotation'}, headers=headers)
        conv2_id = r5.json()['id']
        req2 = {'conversation_id': conv2_id, 'request': 'Create a quotation draft for Acme Corp.'}
        r6 = await client.post('http://localhost:8000/api/v1/runs', json=req2, headers=headers)
        run2_id = r6.json()['run_id']
        print('Started Run 2:', run2_id)
        
        approval_id = None
        for i in range(20):
            await asyncio.sleep(2)
            r7 = await client.get('http://localhost:8000/api/v1/runs/' + run2_id, headers=headers)
            status2 = r7.json()['status']
            print('Status 2:', status2)
            if status2 == 'awaiting_approval':
                # find approval
                r_apps = await client.get('http://localhost:8000/api/v1/approvals', headers=headers)
                apps = r_apps.json().get('items', [])
                for a in apps:
                    if a['agent_run_id'] == run2_id:
                        approval_id = a['id']
                        break
                break
            if status2 in ('completed', 'failed'):
                break
        
        if approval_id:
            print('Found Approval:', approval_id)
            r_appr = await client.post('http://localhost:8000/api/v1/approvals/' + approval_id + '/approve', json={}, headers=headers)
            print('Approve Response:', r_appr.status_code)
            
            for i in range(20):
                await asyncio.sleep(2)
                r8 = await client.get('http://localhost:8000/api/v1/runs/' + run2_id, headers=headers)
                status3 = r8.json()['status']
                print('Status 2 (Post-Approval):', status3)
                if status3 in ('completed', 'failed'):
                    break
        else:
            print('No approval created.')
            
        r9 = await client.get('http://localhost:8000/api/v1/conversations/' + conv2_id + '/messages', headers=headers)
        for msg in r9.json().get('items', []):
            print(msg.get('role').upper() + ': ' + msg.get('content'))

asyncio.run(main())
