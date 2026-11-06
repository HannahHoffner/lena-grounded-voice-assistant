# Ergebnis Validator-Ablationstest

## Ablauf der 120 Anfragen

- Formulator verworfen → Template: 76
- LLM-Text angezeigt: 37
- kein Formulatoraufruf (Dialog/Template/technischer Rückfall): 7

## Erstversuche: Validatorurteil × Bewertung

| | richtig (R) | falsch (FK/FU) |
|---|---:|---:|
| Validator nimmt an | 12 | 2 (davon kritisch 1) |
| Validator verwirft | 86 | 3 (davon kritisch 3) |

Als unklar (U) bewertet und ausgeschlossen: 10

## Kennzahlen (Wilson-95-%-Intervall)

- **Fehlerquote ohne Validator:** 5/103 = 4.9% [95 %: 2.1%–10.9%]
- **davon kritisch:** 4/103 = 3.9% [95 %: 1.5%–9.6%]
- **Vom Validator abgefangen** (Anteil der falschen Erstversuche): 3/5 = 60.0% [95 %: 23.1%–88.2%]
- **Vom Validator übersehen** (Anteil der falschen Erstversuche): 2/5 = 40.0% [95 %: 11.8%–76.9%]
- **Kritische Fehler übersehen:** 1/4 = 25.0% [95 %: 4.6%–69.9%]
- **Unnötig verworfen** (Anteil der richtigen Erstversuche): 86/98 = 87.8% [95 %: 79.8%–92.9%]
- **Trefferquote der Ablehnungen** (verworfen und tatsächlich falsch): 3/89 = 3.4% [95 %: 1.2%–9.4%]

## Was Nutzende gesehen hätten (gleiche Anfragen)

- **Ohne Validator** (Erstversuch angezeigt): falsch 5/103 = 4.9% [95 %: 2.1%–10.9%]; kritisch 4/103 = 3.9% [95 %: 1.5%–9.6%]
- **Mit Validator:** LLM-Text angezeigt in 27 Fällen, davon falsch 2/27 = 7.4% [95 %: 2.1%–23.4%], kritisch 1/27 = 3.7% [95 %: 0.7%–18.3%]; Template statt LLM-Text: 75/103 = 72.8% [95 %: 63.5%–80.5%]; Retrytext unklar: 1

Kuratierte Templates wurden nicht bewertet und gelten hier als nicht falsch.

## Nach Sprache (Erstversuche)

| Sprache | n | falsch | kritisch | verworfen | unnötig verworfen |
|---|---:|---:|---:|---:|---:|
| de | 22 | 1 | 1 | 17 | 16 |
| en | 22 | 2 | 1 | 17 | 16 |
| pl | 19 | 0 | 0 | 19 | 19 |
| ro | 20 | 1 | 1 | 19 | 18 |
| ru | 20 | 1 | 1 | 17 | 17 |

## Ablehnungsgründe des Validators (Erstversuche)

| Diagnose | verworfen | davon tatsächlich falsch |
|---|---:|---:|
| content_not_covered | 53 | 0 |
| service_fact_missing | 19 | 0 |
| no_result_boundary_missing | 4 | 3 |
| phone_not_exact | 4 | 0 |
| price_service_mismatch | 3 | 0 |
| formulator_invalid_fact | 1 | 0 |
| email_not_cited | 1 | 0 |
| current_availability_unsupported | 1 | 0 |
| domain_boundary_missing | 1 | 0 |
| target_claim_contradicted | 1 | 0 |
| fee_claim_unsupported | 1 | 0 |

## Grenzen

Eine Bewerterin, keine Übereinstimmungsmessung; synthetische Anfragen, ein Lauf,
ein Modellprofil (Commit siehe manifest.json). Null Fehler bedeuten keine
Fehlerfreiheit. Hilfsübersetzungen für PL/RO/RU sind nicht maßgeblich.