-- Seed ассистентов для раздела "Дети 3–7" (kids_3_7)
-- Коды должны совпадать с frontend/app/main.js (KIDS_3_7_ASSISTANTS)
-- Скрипт идемпотентен: при повторном запуске обновляет title/description/system_prompt.

INSERT INTO assistants (code, slug, title, description, base_model, system_prompt, extra_config)
VALUES
  (
    'kids_3_7_self_doing',
    'kids_3_7_self_doing',
    'Сам делает: шаг за шагом',
    '',
    'gpt-4.1-mini',
    'TODO: пришлите system_prompt для ассистента "Сам делает: шаг за шагом".',
    '{}'::jsonb
  ),
  (
    'kids_3_7_kindergarten_no_tears',
    'kids_3_7_kindergarten_no_tears',
    'В сад без слез',
    '',
    'gpt-4.1-mini',
    'TODO: пришлите system_prompt для ассистента "В сад без слез".',
    '{}'::jsonb
  ),
  (
    'kids_3_7_fighting_peace',
    'kids_3_7_fighting_peace',
    'Когда ребёнок дерётся: мирный план',
    '',
    'gpt-4.1-mini',
    'TODO: пришлите system_prompt для ассистента "Когда ребёнок дерётся: мирный план".',
    '{}'::jsonb
  ),
  (
    'kids_3_7_listen_finish',
    'kids_3_7_listen_finish',
    'Могу дослушать, могу доделать',
    '',
    'gpt-4.1-mini',
    'TODO: пришлите system_prompt для ассистента "Могу дослушать, могу доделать".',
    '{}'::jsonb
  ),
  (
    'kids_3_7_scary_questions',
    'kids_3_7_scary_questions',
    'Когда ребёнок задаёт “страшные” вопросы',
    '',
    'gpt-4.1-mini',
    'TODO: пришлите system_prompt для ассистента "Когда ребёнок задаёт “страшные” вопросы".',
    '{}'::jsonb
  ),
  (
    'kids_3_7_school_step_by_step',
    'kids_3_7_school_step_by_step',
    'Школа: шаг за шагом',
    '',
    'gpt-4.1-mini',
    'TODO: пришлите system_prompt для ассистента "Школа: шаг за шагом".',
    '{}'::jsonb
  )
ON CONFLICT (code) DO UPDATE
SET
  slug = EXCLUDED.slug,
  title = EXCLUDED.title,
  description = EXCLUDED.description,
  system_prompt = EXCLUDED.system_prompt;

