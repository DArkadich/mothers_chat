-- Seed ассистентов для раздела "Малыши 1–3" (kids_1_3)
-- Коды должны совпадать с frontend/app/main.js (KIDS_1_3_ASSISTANTS)
-- Скрипт идемпотентен: при повторном запуске обновляет title/description/system_prompt.

INSERT INTO assistants (code, slug, title, description, base_model, system_prompt, extra_config)
VALUES
  (
    'kids_1_3_crisis3',
    'kids_1_3_crisis3',
    'Кризис трёх лет: держим баланс',
    '',
    'gpt-4.1-mini',
    'TODO: пришлите system_prompt для ассистента "Кризис трёх лет: держим баланс".',
    '{}'::jsonb
  ),
  (
    'kids_1_3_picky_eater',
    'kids_1_3_picky_eater',
    'Как накормить разборчивого малыша',
    '',
    'gpt-4.1-mini',
    'TODO: пришлите system_prompt для ассистента "Как накормить разборчивого малыша".',
    '{}'::jsonb
  ),
  (
    'kids_1_3_potty',
    'kids_1_3_potty',
    'Горшок: шаг за шагом',
    '',
    'gpt-4.1-mini',
    'TODO: пришлите system_prompt для ассистента "Горшок: шаг за шагом".',
    '{}'::jsonb
  ),
  (
    'kids_1_3_independent_play',
    'kids_1_3_independent_play',
    'Самостоятельная игра: шаг за шагом',
    '',
    'gpt-4.1-mini',
    'TODO: пришлите system_prompt для ассистента "Самостоятельная игра: шаг за шагом".',
    '{}'::jsonb
  ),
  (
    'kids_1_3_first_words',
    'kids_1_3_first_words',
    'Первые слова: легко и играючи',
    '',
    'gpt-4.1-mini',
    'TODO: пришлите system_prompt для ассистента "Первые слова: легко и играючи".',
    '{}'::jsonb
  ),
  (
    'kids_1_3_listening',
    'kids_1_3_listening',
    'Когда ребёнок слушается',
    '',
    'gpt-4.1-mini',
    'TODO: пришлите system_prompt для ассистента "Когда ребёнок слушается".',
    '{}'::jsonb
  )
ON CONFLICT (code) DO UPDATE
SET
  slug = EXCLUDED.slug,
  title = EXCLUDED.title,
  description = EXCLUDED.description,
  system_prompt = EXCLUDED.system_prompt;

