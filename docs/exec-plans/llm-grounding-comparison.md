# Execution Plan: Vergleich regelbasierter und LLM-basierter Faktenprüfung

## Status und Auftrag
26.10.2026, Codex, reviewed/in progress. Nutzerauftrag: Vorschlag eines
LLM-basierten Validators empirisch prüfen, nicht produktiv umstellen.
Review-first-coding und code-documentation angewendet.

## Review und Wiederverwendung
Produktiv: Textvertrag 7, endlicher atomarer Validator in grounding.py.
Der reale Duschfall scheitert reproduzierbar an „Duschgelegenheit“.
Wiederverwendung: prompt_comparison_cases.comparison_cases (deutsche synthetische
Evidence-Pakete), gespeichertes shower-diagnosis.json (reale freigegebene Fakten),
GroundedFormulatorResponse, validate_formulation, BlabladorProvider._post.
Bestehender schmutziger Arbeitsbaum bleibt unberührt. Keine Änderungen an
Anwendung, Tests, Daten, Konfiguration, Thesis oder Git-Historie.

## Verfahren und Abnahmekriterien
- Fallkatalog mit korrekten und gezielt falschen Antworten, Sollurteil und
  Begründung vor Live-Aufrufen speichern und hashen. Sollurteile durch Codex,
  nicht als unabhängiger menschlicher Goldstandard ausgeben.
- Deutsch, gleicher Evidence-/Antwortinhalt für beide Verfahren. Bestehende
  Gesamtprüfung gegen separaten evidencegebundenen LLM-Judge vergleichen.
- Fester Prompt, keine Optimierung anhand der Ergebnisse. Zwei Wiederholungen
  pro Fall, maximal 64 Aufrufe, höchstens zwei gleichzeitig, 30 s je Aufruf,
  keine Wiederholungen nach Transportfehlern. Reale lokale Providerkonfiguration
  verwenden, keine Secrets speichern.
- LLM muss atomare Aussagen, Satzindex, Angebotskennung, Belegreferenzen und
  supported/contradicted/not_supported liefern. Striktes Schema und gültige
  Referenzen werden lokal geprüft. Fehler gelten betrieblich als Ablehnung,
  werden statistisch separat ausgewiesen. Keine bloße Ja/Nein-Plausibilitätsfrage.
- Fehlablehnung belegter Antworten, Freigabe falscher Antworten, Schema-/
  Providerfehler, Wiederholungsstabilität und Latenz getrennt berichten.

## Risiken / Dead Ends
Kein repräsentativer Zufallstest und keine unabhängige Jury. Synthetische
Angebote nicht als Beratungsdaten darstellen. Prüfer kann Behauptungen
übersehen, eigene Weltkenntnis verwenden oder korrelierte Fehler machen.
End-to-End-Latenz und sichere Integration werden durch isolierte Judge-Aufrufe
nicht belegt. Hybridprüfung ist ein möglicher Folgeauftrag, nicht vorweg als
getestet bezeichnen. Keine Anwendungsgates auf Basis dieses kleinen Tests öffnen.

## Dateien und Nachweise
Nur dieser Plan im Repository; ausführbarer Versuch, fixierter Katalog,
Prompt, rohe Antworten, Messwerte und Bericht extern unter
`%LOCALAPPDATA%/LENA/verification/2026-10-26-judge-comparison`.
Keine vollständige Anwendungstestsuite nötig: keine Laufzeitänderung.
Prüfharness lokal gegen akzeptierte/abgelehnte sowie ungültige Judge-Antworten
prüfen; Quellhashes vor/nach Versuch vergleichen. Keine Löschung erforderlich.

## Fortschritt
Review und Versuchsplan abgeschlossen. Live-Vergleich ausstehend.
