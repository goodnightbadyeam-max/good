#!/usr/bin/env python3
"""Удаляет из custom_reviews.txt отзывы с оценкой ниже MIN_RATING.

Строка старого формата:  ник | подарок | оценка | текст | дата
Строка нового формата:   ник | подарок | оценка | текст | дата | user_id
Комментарии (#) и пустые строки не трогаем.
"""
import os
import shutil
import sys

MIN_RATING = 4
REVIEWS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom_reviews.txt')

if not os.path.exists(REVIEWS_FILE):
    print('custom_reviews.txt не найден — удалять нечего')
    sys.exit(0)

with open(REVIEWS_FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

kept, removed = [], []
for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith('#'):
        kept.append(line)
        continue

    parts = [p.strip() for p in stripped.split('|')]
    if len(parts) < 4:
        kept.append(line)          # мусорную строку всё равно не покажем
        continue

    try:
        rating = int(parts[2])
    except ValueError:
        kept.append(line)
        continue

    (removed if rating < MIN_RATING else kept).append(line)

if not removed:
    print('плохих отзывов нет, файл не трогаю')
    sys.exit(0)

backup = REVIEWS_FILE + '.bak'
shutil.copy2(REVIEWS_FILE, backup)

with open(REVIEWS_FILE, 'w', encoding='utf-8') as f:
    f.writelines(kept)

print(f'удалено отзывов: {len(removed)} (копия старого файла: {backup})')
for line in removed:
    print('  - ' + line.strip())
