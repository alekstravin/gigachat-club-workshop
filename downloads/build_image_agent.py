#!/usr/bin/env python3
"""Rebuild the Club gas illustrator from real Studio-exported components.
Not a native export of the current edited canvas; verify a new import in Studio.
Usage: python3 build_image_agent.py --image-template exported-image.json --simple-template exported-simple.json --prompt-file live-system-prompt.txt --output image-agent.json
"""
import argparse,copy,json
from pathlib import Path
SENSITIVE={'credentials','api_key','api_token','access_token','refresh_token','authorization','authorization_key','password','secret','client_secret','private_key','session_id','context_id','trace_id'}
OUTPUT='Изображение создано Kandinsky. Скопируйте строку data:image ниже в просмотрщик image-viewer.html из материалов Клуба, чтобы увидеть и скачать картинку.\n\n{image}'
def clean(doc):
 for n in doc['data']['nodes']:
  for k,v in n.get('data',{}).get('node',{}).get('template',{}).items():
   if k.lower() in SENSITIVE and isinstance(v,dict) and 'value' in v:v['value']=''
 return doc

def h(x):return json.dumps(x,ensure_ascii=False,separators=(',',':')).replace('"','œ')
def edge(src,port,dst,field):
 sh={'dataType':src['data']['type'],'id':src['id'],'name':port,'output_types':['Message']}
 config=dst['data']['node']['template'][field]
 th={'fieldName':field,'id':dst['id'],'inputTypes':config.get('input_types',['Message']),'type':config.get('type','str')}
 a,b=h(sh),h(th)
 return {'animated':False,'className':'','data':{'sourceHandle':sh,'targetHandle':th},'id':f'reactflow__edge-{src["id"]}{a}-{dst["id"]}{b}','selected':False,'source':src['id'],'sourceHandle':a,'target':dst['id'],'targetHandle':b}
def build(image_template,simple_template,prompt):
 base=copy.deepcopy(image_template)
 def get(doc,typ):return copy.deepcopy(next(n for n in doc['data']['nodes'] if n['data'].get('type')==typ))
 inp=get(simple_template,'ChatInput');out=get(simple_template,'ChatOutput');model=get(base,'GigaChatModel');system=get(base,'Prompt Template');image=get(base,'GigaChatImage');render=get(simple_template,'Prompt Template')
 render['id']='Prompt Template-ClubImageOutput';render['data']['id']=render['id'];r=render['data']['node'];r['display_name']='Изображение для просмотрщика';r['template']['template']['value']=OUTPUT;r['custom_fields']={'template':['image']};r['field_order']=['template','image','tool_placeholder','signal_input']
 f=copy.deepcopy(r['template']['tool_placeholder']);f.update({'name':'image','display_name':'image','advanced':False,'required':False,'tool_mode':False,'value':''});r['template']['image']=f
 system['data']['node']['template']['template']['value']=prompt.strip()
 image['data']['node']['template']['style']['value']=''
 out['data']['node']['template']['data_template']['value']='{text}'
 nodes=[inp,system,model,image,render,out]
 for n,(x,y) in zip(nodes,[(0,120),(0,350),(360,120),(720,120),(1080,120),(1440,120)]):
  n['position']={'x':x,'y':y};n['selected']=False;n.pop('dragging',None)
  fields=n['data']['node']['template']
  for key in ['input_value','signal_input']:
   if key in fields:fields[key]['value']=''
  if 'should_store_message' in fields:fields['should_store_message']['value']=True
 base['data']['nodes']=nodes;base['data']['edges']=[edge(inp,'message',model,'input_value'),edge(system,'prompt',model,'system_message'),edge(model,'text_output',image,'prompt'),edge(image,'image_base64',render,'image'),edge(render,'prompt',out,'input_value')]
 base['name']='Клуб ИИИИ — Газовая отрасль: иллюстратор';base['id']='';base['endpoint_name']=None;base['description']='Повторная сборка текущей схемы на основе нативного шаблона Studio: 6 узлов, 5 связей, стиль По умолчанию; художественный стиль задаётся запросом. Не нативный экспорт текущего канваса; проверьте импорт отдельной копией. Изображение передаётся как data:image для просмотра в image-viewer.html.'
 return clean(base)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['image-template','simple-template','prompt-file','output']:p.add_argument('--'+name,required=True)
 a=p.parse_args();dest=Path(a.output)
 if dest.resolve() in [Path(a.image_template).resolve(),Path(a.simple_template).resolve()]:p.error('output must differ from source')
 d=build(json.loads(Path(a.image_template).read_text()),json.loads(Path(a.simple_template).read_text()),Path(a.prompt_file).read_text())
 dest.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print('Created',dest.name,': 6 nodes, 5 edges. Verify in Studio; no model request executed.')
if __name__=='__main__':main()
