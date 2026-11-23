import requests

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAiLCJqdGkiOiJjY2VjMzcwNS1hZWM0LTQxZjgtYTM5ZC04NTJlYTUxZjEzYTkiLCJ0eXBlIjoiYWNjZXNzIiwidGVuYW50X2lkIjpudWxsLCJwbGFudF9pZCI6bnVsbCwiaWF0IjoxNzg2NjEyMzU4LCJleHAiOjIxMDE5NzIzNTh9.lxfl9aoDa4majrYQY_AMVMk-Sx9r4UOTK7S07iC0gB8'
headers = {'Authorization': 'Bearer ' + token}

# 1. Statistics
r_stat = requests.get('http://127.0.0.1:8020/demo-api/v1/erp/statistics', headers=headers)
print('STATISTICS HTTP STATUS:', r_stat.status_code)
if r_stat.status_code == 200:
    s = r_stat.json().get('data', {})
    print('  active_rows:', s.get('active_rows'))
    print('  active_imports:', s.get('active_imports'))
    print('  archived_imports:', s.get('archived_imports'))
    print('  is_reset_active:', s.get('is_reset_active'))
    print('  total_rows_imported:', s.get('total_rows_imported'))

# 2. Jobs
r_jobs = requests.get('http://127.0.0.1:8020/demo-api/v1/erp/jobs?page=1&page_size=10', headers=headers)
print('\nJOBS HTTP STATUS:', r_jobs.status_code)
if r_jobs.status_code == 200:
    items = r_jobs.json().get('data', {}).get('items', [])
    print(f'  Found {len(items)} jobs:')
    for j in items:
        print(f"  - {j['job_number']} | {j['file_name']} | Type: {j.get('file_type')} | Period: {j.get('dataset_period')} | Active: {j.get('is_active_dataset')} | Reset: {j.get('is_reset')} | Uploader: {j.get('uploaded_by')}")
