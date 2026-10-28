#!/usr/bin/env python3
"""Edit one real GigaBlocks Prompt Template in a NEW JSON copy.
Usage: python3 edit_schema.py source.json dest.json --prompt-file system.txt
No credentials are printed. This is a local syntax/graph check, not a Studio run.
"""
import argparse
import copy
import json
from pathlib import Path
import sys

# Exact designated configuration fields only: never replace words in code/prompts.
SENSITIVE_FIELDS = {
    'credentials', 'api_key', 'api_token', 'access_token', 'refresh_token',
    'authorization', 'authorization_key', 'password', 'secret', 'client_secret',
    'private_key', 'session_id', 'context_id',
}

def edit(source, destination, prompt_file):
    source, destination, prompt_file = map(lambda p: Path(p).expanduser().resolve(), (source, destination, prompt_file))
    if source == destination:
        raise ValueError('Source and destination must differ; preserve the original.')
    if destination.exists():
        raise ValueError('Destination already exists; choose a new file name.')
    prompt = prompt_file.read_text(encoding='utf-8').strip()
    if not prompt:
        raise ValueError('Prompt file is empty.')
    doc = json.loads(source.read_text(encoding='utf-8'))
    data = doc.get('data')
    if not isinstance(data, dict) or not isinstance(data.get('nodes'), list) or not isinstance(data.get('edges'), list):
        raise ValueError('Expected a GigaBlocks export with data.nodes and data.edges.')
    ids_before = [n.get('id') for n in data['nodes']]
    edges_before = copy.deepcopy(data['edges'])
    candidates=[]
    for node in data['nodes']:
        component = node.get('data', {})
        template = component.get('node', {}).get('template', {})
        if component.get('type') in ('Prompt Template', 'PromptTemplate'):
            field = template.get('template')
            if isinstance(field, dict) and 'value' in field:
                candidates.append(field)
    if len(candidates) != 1:
        raise ValueError(f'Expected exactly one Prompt Template node; found {len(candidates)}. Select it manually in a copy.')
    candidates[0]['value'] = prompt
    scrubbed=0
    for node in data['nodes']:
        fields=node.get('data', {}).get('node', {}).get('template', {})
        for name, config in fields.items():
            if name.lower() in SENSITIVE_FIELDS and isinstance(config, dict) and 'value' in config:
                if config['value'] not in ('', None):
                    scrubbed += 1
                config['value']=''
    assert [n.get('id') for n in data['nodes']] == ids_before
    assert data['edges'] == edges_before
    serialized=json.dumps(doc, ensure_ascii=False, indent=2)
    json.loads(serialized)  # Syntax round-trip; does not execute embedded code.
    with destination.open('x', encoding='utf-8') as output:
        output.write(serialized+'\n')
    print(f'Created: {destination.name}; prompt nodes changed: 1; designated nonempty fields cleared: {scrubbed}; nodes: {len(ids_before)}; edges preserved: {len(edges_before)}.')
    print('Review before sharing: code, prompts, files and arbitrary custom fields can still contain secrets; this exact-field cleaner is not a comprehensive secret scanner. Re-select account/tenant in Studio and test the imported copy.', file=sys.stderr)
    return doc

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source');p.add_argument('destination');p.add_argument('--prompt-file', required=True)
    a=p.parse_args()
    try:
        edit(a.source,a.destination,a.prompt_file)
    except (OSError, ValueError, AssertionError) as exc:
        p.exit(2, f'Not changed: {exc}\n')
if __name__=='__main__':
    main()
