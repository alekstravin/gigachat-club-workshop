#!/usr/bin/env python3
"""Create this computer's public verification configuration. No model calls.
Private signing key is created/loaded only through collector.signing_key().
Never prints or copies private-key material. Base newsroom-agent.json is preserved.
"""
from pathlib import Path
import ast
import copy
import json
import re

ROOT = Path(__file__).resolve().parent
SENSITIVE_FIELDS = {
    'credentials', 'api_key', 'api_token', 'access_token', 'refresh_token',
    'authorization', 'authorization_key', 'password', 'secret', 'client_secret',
    'private_key', 'session_id', 'context_id', 'trace_id',
}

def public_code(code, numbers):
    updated, n = re.subn(r'(?m)^PUBLIC_N\s*=\s*\d+\s*$', 'PUBLIC_N = '+str(numbers.n), code)
    updated, e = re.subn(r'(?m)^PUBLIC_E\s*=\s*\d+\s*$', 'PUBLIC_E = '+str(numbers.e), updated)
    if (n,e)!=(1,1):
        raise ValueError('Expected exactly one PUBLIC_N and PUBLIC_E declaration.')
    ast.parse(updated)
    return updated

def prepare():
    # cryptography and private-key management stay inside the collector.
    from collector import signing_key
    numbers = signing_key().public_key().public_numbers()
    base = ROOT.parent/'newsroom-agent.json'
    doc = copy.deepcopy(json.loads(base.read_text(encoding='utf-8')))
    guards = [n for n in doc['data']['nodes'] if n.get('id')=='TransformComponent-SourceGuard']
    if len(guards)!=1:
        raise ValueError('Expected one SourceGuard in the base schema.')
    field=guards[0]['data']['node']['template']['_generated_code']
    field['value']=public_code(field['value'],numbers)
    for node in doc['data']['nodes']:
        fields=node.get('data',{}).get('node',{}).get('template',{})
        for name,value in fields.items():
            if name.lower() in SENSITIVE_FIELDS and isinstance(value,dict) and 'value' in value:
                value['value']=''
    verifier=public_code((ROOT/'verify_evidence.py').read_text(encoding='utf-8'),numbers)
    generated=ROOT/'generated';generated.mkdir(exist_ok=True)
    public={'n':str(numbers.n),'e':numbers.e}
    schema=json.dumps(doc,ensure_ascii=False,indent=2)+'\n'
    json.loads(schema)
    # Public artifacts only. Re-running setup retains the collector's existing key.
    (generated/'news-agent-personal.json').write_text(schema,encoding='utf-8')
    (generated/'public_key.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    (ROOT/'public_key.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    (ROOT/'verify_evidence.py').write_text(verifier,encoding='utf-8')
    print('Ready: generated/news-agent-personal.json and generated/public_key.json')
    print('Private key stays in the collector user directory; never copy it into this package.')
    print('Next: import the generated schema as a NEW agent, then run python server.py.')
    return generated

if __name__=='__main__':
    try:
        prepare()
    except (ImportError,OSError,ValueError,KeyError) as error:
        raise SystemExit('Setup stopped: '+str(error))
