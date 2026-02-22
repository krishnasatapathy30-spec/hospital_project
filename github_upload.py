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
        except Exception:
            return {'_error': True, 'status': e.code, 'body': ''}

def upload_file(token, owner, repo, local_path, rel_path, branch='main'):
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{urllib.request.pathname2url(rel_path)}'
    with open(local_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode('utf-8')
    # check existing
    get = gh_api_request('GET', url, token)
    if isinstance(get, dict) and get.get('_error') and get.get('status') == 404:
        # create
        payload = { 'message': f'Add {rel_path}', 'content': content, 'branch': branch }
        res = gh_api_request('PUT', url, token, payload)
        return res
    elif isinstance(get, dict) and get.get('sha'):
        # update
        payload = { 'message': f'Update {rel_path}', 'content': content, 'sha': get['sha'], 'branch': branch }
        res = gh_api_request('PUT', url, token, payload)
        return res
    else:
        return get

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--token', required=True)
    p.add_argument('--owner', required=True)
    p.add_argument('--repo', required=True)
    p.add_argument('--root', default='.')
    args = p.parse_args()

    skip_dirs = {'.git', 'venv', '__pycache__', '.pytest_cache'}
    skip_ext = {'.exe', '.db', '.sqlite3', '.pyc', '.pyo'}

    root = os.path.abspath(args.root)
    print('Scanning files to upload...')
    uploads = []
    for dirpath, dirnames, filenames in os.walk(root):
        # filter dirs
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            if fname.endswith('~'):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in skip_ext:
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root).replace('\\','/')
            uploads.append((full, rel))

    print(f'Found {len(uploads)} files to upload (skipping binary/excluded files).')
    ok = 0
    for full, rel in uploads:
        print('Uploading', rel)
        res = upload_file(args.token, args.owner, args.repo, full, rel)
        if isinstance(res, dict) and res.get('_error'):
            print('FAILED', rel, res.get('status'), (res.get('body') or '')[:200])
        else:
            ok += 1
    print(f'Uploaded {ok}/{len(uploads)} files.')
    print(f'https://github.com/{args.owner}/{args.repo}')

if __name__ == '__main__':
    main()
