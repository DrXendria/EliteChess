"""
FIDE rating list import (XML format).
"""
import xml.etree.ElementTree as ET
from typing import Optional
from models import Player, Title


def search_fide_xml(filepath: str, query: str, max_results: int = 50) -> list[dict]:
    """Search FIDE XML rating list by name or FIDE ID."""
    results = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        query_lower = query.lower().strip()

        for player_elem in root.iter('player'):
            name = player_elem.findtext('name', '').strip()
            fide_id = player_elem.findtext('fideid', '').strip()

            if query_lower in name.lower() or query_lower == fide_id:
                rating = int(player_elem.findtext('rating', '0') or '0')
                title = player_elem.findtext('title', '').strip()
                country = player_elem.findtext('country', '').strip()
                birthday = player_elem.findtext('birthday', '').strip()

                results.append({
                    'name': name,
                    'fide_id': fide_id,
                    'rating': rating,
                    'title': title,
                    'country': country,
                    'birthday': birthday,
                })

                if len(results) >= max_results:
                    break

    except ET.ParseError as e:
        print(f"XML parse error: {e}")
    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except Exception as e:
        print(f"FIDE XML search error: {e}")

    return results


def fide_to_player(fide_data: dict) -> Player:
    """Convert FIDE XML data to Player object."""
    name_parts = fide_data.get('name', '').split(', ', 1)
    surname = name_parts[0] if name_parts else ''
    first_name = name_parts[1] if len(name_parts) > 1 else ''

    title_str = fide_data.get('title', '')
    try:
        title = Title(title_str) if title_str else Title.NONE
    except ValueError:
        title = Title.NONE

    birth_year = 0
    birthday = fide_data.get('birthday', '')
    if birthday:
        try:
            birth_year = int(birthday[:4])
        except (ValueError, IndexError):
            pass

    rating = int(fide_data.get('rating', 0))
    return Player(
        name=first_name,
        surname=surname,
        rating=rating,
        elo=rating,
        title=title,
        fide_id=fide_data.get('fide_id', ''),
        club=fide_data.get('country', ''),
        birth_year=birth_year,
    )


def load_fide_list_info(filepath: str) -> Optional[dict]:
    """Get basic info about a FIDE rating list file."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        count = sum(1 for _ in root.iter('player'))
        return {
            'filepath': filepath,
            'player_count': count,
        }
    except Exception as e:
        print(f"FIDE list info error: {e}")
        return None
