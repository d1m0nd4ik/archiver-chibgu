"""Параметры расширенного поиска по архиву."""
from __future__ import annotations

from dataclasses import dataclass, field


SORT_OPTIONS = {
    'date_desc': 'Дата (новые)',
    'date_asc': 'Дата (старые)',
    'likes_desc': 'Лайки',
    'comments_desc': 'Комментарии',
    'shares_desc': 'Репосты',
    'popularity_desc': 'Популярность',
}


@dataclass
class PostSearchParams:
    query: str = ''
    date_from: str | None = None
    date_to: str | None = None
    tag_hashtag: str | None = None
    department_id: int | None = None
    author_employee_id: int | None = None
    media_type: str | None = None  # photo, video, clip, any, none
    post_source: str | None = None  # vk, manual
    sort: str = 'date_desc'
    limit: int = 500
    offset: int = 0
