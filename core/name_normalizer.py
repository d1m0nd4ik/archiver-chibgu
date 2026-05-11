import re
import pymorphy3
from core.logging_config import logger

_MORPH = pymorphy3.MorphAnalyzer()

def to_nominative_case(full_name: str) -> str:
    if not full_name: return full_name
    parts = re.split(r'\s+', full_name.strip())
    normalized = []
    for part in parts:
        if not part: continue
        if '.' in part or len(part) < 2:
            normalized.append(part)
            continue
        try:
            parsed = _MORPH.parse(part)
            if parsed:
                normalized.append(parsed[0].normal_form.capitalize())
            else:
                normalized.append(part.capitalize())
        except Exception as e:
            logger.debug(f"Normalizer error for '{part}': {e}")
            normalized.append(part)
    return ' '.join(normalized)

def normalize_and_reorder(full_name: str) -> str:
    nom_name = to_nominative_case(full_name)
    parts = nom_name.split()
    if len(parts) < 2: return nom_name
    
    surname_endings = ('ов', 'ев', 'ёв', 'ин', 'ын', 'ович', 'евич', 'ич', 
                       'ая', 'яя', 'ова', 'ева', 'ёва', 'ина', 'ына', 'ской', 'цкий')
    surname = None
    for p in parts:
        if any(p.lower().endswith(e) for e in surname_endings) and len(p) > 3:
            surname = p
            break
    if not surname: surname = max(parts, key=len)
    
    others = [p for p in parts if p != surname]
    if len(others) == 2: return f"{surname} {others[0]} {others[1]}"
    elif len(others) == 1: return f"{surname} {others[0]}"
    return nom_name