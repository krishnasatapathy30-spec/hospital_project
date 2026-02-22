#!/usr/bin/env python3
import os, sys, json, base64, argparse, urllib.request, urllib.error

def gh_api_request(method, url, token, data=None):
    req = urllib.request.Request(url, data=(json.dumps(data).encode('utf-8') if data is not None else None), method=method)
    req.add_header('Authorization', f'token {token}')
    req.add_header('User-Agent', 'upload-script')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    if data is not None:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode('utf-8')
            return {'_error': True, 'status': e.code, 'body': body}
        except:
            return {'_error': True, 'status': e.code, 'body': ''}

def upload_file(token, owner, repo, local_path, rel_path, branch='main'):
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{urllib.request.pathname2url(rel_path)}'
    with open(local_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode('utf-8')
    get = gh_api_request('GET', url, token)
    if isinstance(get, dict) and get.get('_error') and get.get('status') == 404:
        payload = { 'message': f'Add {rel_path}', 'content': content, 'branch': branch }
        res = gh_api_request('PUT', url, token, payload)
        return res
    elif isinstance(get, dict) and get.get('sha'):
        payload = { 'message': f'Update {rel_path}', 'content': content, 'sha': get['sha'], 'branch': branch }
        res = gh_api_request('PUT', url, token, payload)
        return res
    else:
        return get

def gather_files(root):
    files = []
    # include top-level important files
    top_files = ['app.py','Procfile','requirements.txt','README.md','start_ngrok.py','push_with_token.ps1','create_github_repo.ps1','github_upload.py','github_upload_selective.py','run_project.bat']
    for f in top_files:
        p = os.path.join(root, f)
        if os.path.isfile(p):
            files.append((p, f))
    # include entire 'main folder' directory
    mf = os.path.join(root, 'main folder')
    for dirpath, dirnames, filenames in os.walk(mf):
        # skip caches
        dirnames[:] = [d for d in dirnames if d not in ('__pycache__',)]
        for fname in filenames:
            if fname.endswith(('.pyc','.pyo')):
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root).replace('\\','/')
            files.append((full, rel))
    return files

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--token', required=True)
    p.add_argument('--owner', required=True)
    p.add_argument('--repo', required=True)
    p.add_argument('--root', default='.')
    args = p.parse_args()

    root = os.path.abspath(args.root)
    files = gather_files(root)
    print(f'Will upload {len(files)} files (selective).')
    ok=0
    for full, rel in files:
        print('Uploading', rel)
        res = upload_file(args.token, args.owner, args.repo, full, rel)
        if isinstance(res, dict) and res.get('_error'):
            print('FAILED', rel, res.get('status'), (res.get('body') or '')[:200])
        else:
            ok+=1
    print(f'Uploaded {ok}/{len(files)} files.')
    print(f'https://github.com/{args.owner}/{args.repo}')

if __name__=='__main__':
    main()
