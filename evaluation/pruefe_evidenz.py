"""Providerfreie Konsistenzprüfung archivierter Thesis-Evidenz (Python >= 3.11)."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
FOLDERS = [
    'technische-evaluation-2026-10-22',
    'technische-evaluation-2026-10-26',
    'speech-integration-2026-10-27',
    'validatorentwicklung-2026-10-26',
    'validatorentwicklung-2026-10-27',
    'technische-evaluation-2026-10-27',
    'technische-evaluation-2026-10-28',
]


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream, delimiter=';'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def table_rows(text):
    """Read the simple Markdown tables used by the evaluation documents."""
    return [[cell.strip() for cell in line.strip().strip('|').split('|')]
            for line in text.splitlines() if line.startswith('|')]


def check_manual_final():
    """Check recorded structure and counts, without reassessing any answer."""
    folder = ROOT / 'manual_final_20261029'
    expected_ids = [f'F-{i:02d}' for i in range(1, 33)]
    results = (folder / 'results.md').read_text(encoding='utf-8')
    matrix = results.split('## Kriterienmatrix', 1)[1].split('## Beobachtung,', 1)[0]
    rows = [row for row in table_rows(matrix) if re.fullmatch(r'F-\d{2}', row[0])]
    require([row[0] for row in rows] == expected_ids, 'Finalmatrix: Fallkennungen/Reihenfolge')
    require(all(len(row) == 9 for row in rows), 'Finalmatrix: Spaltenumfang')
    require(all(value in {'E', 'T', 'N', 'B', '–'} for row in rows for value in row[2:8]),
            'Finalmatrix: unbekanntes Kriterienurteil')
    require(all(row[8] in {'E', 'T', 'N', 'B'} for row in rows), 'Finalmatrix: Fallurteil')

    summary = {row[0]: row[1:] for row in table_rows(
        (ROOT / 'EVALUATIONSSTAND.md').read_text(encoding='utf-8'))}
    criteria = ['Hilfeweg', 'Angebotsauswahl', 'Fakten', 'Zeit-/Ortsbezug', 'Sprache', 'Bedienung']
    for column, name in enumerate(criteria, 2):
        counts = Counter(row[column] for row in rows)
        reported = [int(value) for value in summary[name]]
        require([counts[key] for key in ['E', 'T', 'N', '–']] + [32 - counts['–']] == reported,
                f'Finalmatrix: Auszählung {name}')

    plan = (folder / 'testplan.md').read_text(encoding='utf-8')
    sections = re.split(r'(?m)^## (F-\d{2})[^\n]*\n', plan)
    require(sections[1::2] == expected_ids, 'Testplan: Fallkennungen/Reihenfolge')
    verdicts = {'erfüllt': 'E', 'teilweise erfüllt': 'T', 'nicht erfüllt': 'N', 'nicht beurteilbar': 'B'}
    for row, section in zip(rows, sections[2::2]):
        marked = re.findall(r'☒ (erfüllt|teilweise erfüllt|nicht erfüllt|nicht beurteilbar)', section)
        require(len(marked) == 1 and verdicts[marked[0]] == row[8],
                f'Testplan/Matrix: Fallurteil {row[0]}')

    raw = read_json(folder / 'evidence/rohdaten.json')
    require(list(raw['hauptlauf']) == expected_ids, 'Rohdaten: Fallkennungen/Reihenfolge')
    require(set(raw['probelauf_F-03']) == {'F-03'}, 'Rohdaten: gesonderter Probelauf')
    screenshots = set()
    for run in [raw['hauptlauf'], raw['probelauf_F-03']]:
        for case_id, case in run.items():
            require(bool(case['steps']), f'Leerer Fall: {case_id}')
            for step in case['steps']:
                require(step['case'] == case_id, f'Rohdaten: falsche Zuordnung {case_id}')
                path = (folder / step['screenshot']).resolve()
                require(path.is_relative_to(folder.resolve()) and path.is_file(),
                        f'Fehlender/ungültiger Screenshot: {case_id}')
                screenshots.add(path)
    require(screenshots == {p.resolve() for p in (folder / 'evidence').glob('*.png')},
            'Screenshots: Rohdaten und Dateibestand weichen ab')

    for name in ['README.md', 'testplan.md', 'results.md']:
        text = (folder / name).read_text(encoding='utf-8')
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text):
            if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                continue
            require((folder / target.split('#', 1)[0]).exists(), f'Fehlender Beleglink: {name}: {target}')
    return len(rows), len(screenshots), Counter(row[8] for row in rows)


def main():
    checked = 0
    for name in FOLDERS:
        folder = ROOT / name
        for relative, expected in read_json(folder / 'SHA256.json').items():
            path = folder / relative
            require(path.is_file(), f'Fehlender Beleg: {path}')
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            require(actual == expected, f'Hashabweichung: {path}')
            checked += 1

    manual_cases, screenshots, verdicts = check_manual_final()

    for day in ['26', '27']:
        folder = ROOT / f'validatorentwicklung-2026-10-{day}'
        name = 'bewertung.csv' if day == '26' else 'bewertung_ausgefüllt.csv'
        ratings_by_id = {r['item_id']: r for r in read_csv(folder / name)}
        first = [r for r in read_json(folder / 'schluessel.json')
                 if r['role'] == 'erstversuch']
        counts = Counter((r['validator'], ratings_by_id[r['item_id']]['bewertung (R/FK/FU/U)'])
                         for r in first)
        reported = read_json(folder / 'auswertung-erstversuche.json')
        expected = {(r['validator'], r['rating']): r['n'] for r in reported['cross_table']}
        require(dict(counts) == expected and len(first) == reported['first_attempts'],
                f'Erstversuchsauswertung: {day}.10.')

    cases = ET.parse(ROOT / 'technische-evaluation-2026-10-28/reviewed/native.xml').findall('.//testcase')
    modules = defaultdict(list)
    for case in cases:
        modules[case.attrib['classname'].split('.')[-1]].append(case)
    require(len(cases) == 1696 and len(modules) == 54, 'JUnit-Umfang')
    require(sum(c.find('skipped') is not None for c in cases) == 1, 'JUnit-XFAIL')
    require(not any(c.find(tag) is not None for c in cases for tag in ['failure', 'error']),
            'Unerwarteter JUnit-Fehler')
    require(sum(read_json(p)['counts']['provider_calls'] for p in
                (ROOT / 'technische-evaluation-2026-10-27/live-evaluations').glob('*/summary.json')) == 126,
            'Live-Aufrufsumme')
    print(f'OK: Finalprüfung mit {manual_cases} Fällen, sechs Kriterien, '
          f'{screenshots} Screenshots; '
          f'Fallurteile E/T/N/B={verdicts["E"]}/{verdicts["T"]}/{verdicts["N"]}/{verdicts["B"]}; '
          f'{checked} technische/formative Belege bytegleich; beide Erstversuchstabellen; '
          '1696 JUnit-Faelle/54 Module; 126 historische Live-Provideraufrufe.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, ET.ParseError) as exc:
        print(f'FEHLER: {exc}', file=sys.stderr)
        sys.exit(1)
