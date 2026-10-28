import unittest
from answer_guard import transform,periods_in
class GuardTests(unittest.TestCase):
 def run_answer(self,q,a='Ответ модели с ошибкой: май +400, июнь +1100.'):
  return transform({'in1':{'text':q},'in2':{'text':a}})['result']
 def test_comparison_uses_registry_not_model(self):
  a=self.run_answer('Сравни майский и июньский выпуски IEA 2026: изменение мирового спроса на 2026 год')
  for text in ['снижение на 420','снижение на 1100','−680','700 тыс.','iea_omr_2026_05.pdf','iea_omr_2026_06.pdf']:self.assertIn(text,a)
  self.assertNotIn('+400',a)
 def test_other_months(self):
  a=self.run_answer('Сравни IEA 2026-01 и 2026-03: прогноз изменения спроса в 2026')
  self.assertIn('рост на 930',a);self.assertIn('рост на 640',a);self.assertIn('−290',a)
 def test_missing_issue_does_not_substitute(self):
  a=self.run_answer('IEA за октябрь 2026: прогноз спроса 2027','В июне прогноз роста 2 млн')
  self.assertIn('Недостаёт: выпуск IEA 2026-10',a);self.assertNotIn('2 млн',a)
 def test_empty_or_incomplete_stops(self):
  for a in ['', '<', '   ']:self.assertIn('не найден',self.run_answer('Роснефть выручка 2025',a))
 def test_other_organizations_preserved(self):
  self.assertEqual(self.run_answer('Роснефть выручка 2025','Выручка 8236 млрд руб.'),'Выручка 8236 млрд руб.')
 def test_untranslated_quote_removed(self):
  a=self.run_answer('OPEC спрос 2050','Прогноз 123 млн барр./сут.\nПеревод цитаты: «Global oil demand will continue to grow over the period».\nИсточник: opec_woo_2025.pdf, страница 17.')
  self.assertNotIn('Global',a);self.assertIn('opec_woo_2025.pdf',a)
 def test_oil_equivalent_cannot_replace_oil_demand(self):
  a=self.run_answer('OPEC мировой спрос на нефть 2050','Спрос 112,4 млн баррелей в день (mboe/d).')
  self.assertIn('не найден',a);self.assertNotIn('112,4',a)
 def test_verified_registry_survives_empty_llm(self):
  a=self.run_answer('Сравни IEA 2026-05 и 2026-06: изменение спроса на 2026','<')
  self.assertIn('снижение на 420',a);self.assertIn('−680',a)
 def test_refusal_cannot_substitute_other_year(self):
  a=self.run_answer('Роснефть EBITDA 2025','Данные за 2025 отсутствуют. В 2024 EBITDA 3029 млрд.')
  self.assertIn('не найден',a);self.assertNotIn('3029',a)
 def test_month_is_a_word(self):self.assertEqual(periods_in('Я понимаю вопрос IEA за 2026 год'),[])
 def test_cross_year_iso(self):self.assertEqual(periods_in('IEA 2025-12 против 2026-01'),['2025-12','2026-01'])
if __name__=='__main__':unittest.main()
