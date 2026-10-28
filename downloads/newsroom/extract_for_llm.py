import json

def transform(inputs):
    value=inputs.get('in1')
    if not isinstance(value,dict):value=getattr(value,'data',{})
    if isinstance(value.get('data'),dict) and 'gate' not in value:value=value['data']
    if value.get('gate')!='PASS':raise ValueError('Выпуск остановлен: GATE_NOT_PASSED')
    baseline=json.loads(value['text'])
    prompt={'period_start':baseline['period_start'],'period_end':baseline['period_end'],'articles':[{'id':a['id'],'title':a['title'],'text':a['text'][:6500]} for a in baseline['articles']]}
    return {'result':json.dumps(prompt,ensure_ascii=False),'baseline':value['text']}
