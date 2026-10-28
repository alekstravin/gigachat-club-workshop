#!/usr/bin/env python3
"""Offline regressions for the illustrator export. Not a live generation test."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent

class ImageSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=json.loads((ROOT/'image-agent.json').read_text(encoding='utf-8'))
        cls.nodes=cls.doc['data']['nodes']
    def test_chat_history_is_kept_for_visible_output(self):
        for kind in ('ChatInput','ChatOutput'):
            node=next(n for n in self.nodes if n['data'].get('type')==kind)
            self.assertIs(node['data']['node']['template']['should_store_message']['value'],True,kind)
    def test_default_style_defers_to_explicit_prompt(self):
        node=next(n for n in self.nodes if n['data'].get('type')=='GigaChatImage')
        self.assertEqual(node['data']['node']['template']['style']['value'],'')
        system=next(n for n in self.nodes if n['data'].get('type')=='Prompt Template' and n['id']!='Prompt Template-ClubImageOutput')
        self.assertIn('Если пользователь явно указал Стиль',system['data']['node']['template']['template']['value'])
    def test_graph_has_six_nodes_and_five_resolved_edges(self):
        self.assertEqual(len(self.nodes),6)
        edges=self.doc['data']['edges'];self.assertEqual(len(edges),5)
        ids={n['id'] for n in self.nodes}
        for e in edges:
            self.assertIn(e['source'],ids);self.assertIn(e['target'],ids)
            self.assertEqual(e['data']['sourceHandle']['id'],e['source'])
            self.assertEqual(e['data']['targetHandle']['id'],e['target'])
    def test_output_retains_image_placeholder_and_text_rendering(self):
        renderer=next(n for n in self.nodes if n['id']=='Prompt Template-ClubImageOutput')
        self.assertIn('{image}',renderer['data']['node']['template']['template']['value'])
        out=next(n for n in self.nodes if n['data'].get('type')=='ChatOutput')
        self.assertEqual(out['data']['node']['template']['data_template']['value'],'{text}')

if __name__=='__main__':unittest.main()
