# Execution Plan: Vollständige, einfache Antwortsätze

## Status
Complete, Codex, 26.10.2026. Kein Commit/Tag/Push.

## Objective und Acceptance contract
- Kontrollierte Faktenakte liefern vollständige, kurze Sätze statt Feldlabels und Semikolonlisten in allen fünf unterstützten Sprachen.
- Der Screenshotfall mit Blockquote-Markern und mehrfach „Angebot“ wird reproduziert und korrigiert.
- Fakten, Negationen, Zahlen, Zugangsvorbehalte, Leistungszeiten, Quellen und Fact-IDs bleiben gebunden. Keine freie LLM-Prosa, keine Erweiterung des Vertrags.
- Lange Fakten, mehrere Akte, unbekannte Angaben und atomare Ablehnung ungültiger Pläne bleiben abgesichert; 600-Zeichen-Grenze unverändert.
- Gezielte Regression, vollständige Python-/JS-Suiten und sauberer Docker-Neubau mit netzlosen Containertests. Keine Commits/Tags/Pushes, keine neue vollständige Live-Evaluation.

## Scope und Repository review
Kanonisches Code-Repository sauber auf fb773e9. Uncommittete Änderungen im separaten Thesis-Repository bleiben unberührt. FastAPI -> LLM-Vertrag 6 -> answer_plan._render_facts -> _fit_answer -> gebundene API-Ausgabe. Der Renderer verwendet derzeit _fact_line mit festen Labels und ungefilterten Quellwerten. answer_act_texts enthält geschlossene fünfsprachige Texte und source_text. Vorhandene Tests in test_answer_plan prüfen Bindung, lange Bedingungen und Fallbacks; historische Freitexttests bleiben erhalten.

## Dead ends und Entscheidungen
- Freie Modellformulierung würde den bestehenden Schutzvertrag umgehen: unverändert ablehnen.
- Nur „>“ entfernen behebt keine Labels und Fragmente: Satzrenderer mit typbezogenen Vorlagen und Gruppierung verwenden.
- Beliebige Quellprosa grammatisch umschreiben könnte Fakten verändern: nur äußere Markdown-Listen-/Zitatmarker normalisieren, Werte sonst unverändert einsetzen; unstrukturierte Angaben in einem vollständigen Hinweissatz zitieren.
- Kürzere Darstellung darf Bedingungen nicht verlieren: bestehende bedingungsgebundene Auswahl und vollständige Validierung erhalten.
- Kein pauschales Versprechen geprüfter Leichter Sprache oder menschlich geprüfter Fremdsprachen.

## File impact
app/answer_plan.py: Einbindung Satzrenderer statt Labelrenderer. Neues kohäsives app/answer_sentences.py: Normalisierung und lokalisierte Satzvorlagen. tests/test_answer_sentences.py: reale Quellformate, fünf Sprachen, Bedingungen und Darstellung. Bestehende Tests nur bei begründeter sichtbarer Änderung ergänzen, nicht abschwächen. docs/controlled-answer-acts.md, IMPLEMENTATION_REPORT.md und relevante aktuelle Hinweise in README/Traceability nur für geändertes Verhalten und Gültigkeitsgrenzen aktualisieren.

## Milestones
1. Review abgeschlossen: Quellmarker in bootstrap/canonical/offers.json:4115–4116, aktueller Renderer, Faktentypen und vorhandene Tests gelesen.
2. Implementierung abgeschlossen: Renderer 1 mit festen Satzvorlagen, Gruppierung, konservativer Quellformatbereinigung und vollständigen kompakten Rückfalltexten. Keine Daten-/Prompt-/Vertrags-/Provideränderung.
3. Gezielte Prüfung 132 bestanden. Vollständig nativ/Container jeweils 1506 bestanden, 1 historischer strikter XFAIL und bekannte TestClient-Warnung; JS jeweils 19/19. Sauberer Docker-Neubau und Runtime-/Health-/Volume-/Neustart-/Containerwechselprüfung bestanden. Unterbrochene Entwicklungsprüfungen nicht als vollständige Läufe gezählt.
4. Dokumentationsreview mit code-documentation abgeschlossen. README, Testdokumentation, Antwortaktbeschreibung, Implementation Report und relevante Traceability-/Thesishinweise aktualisiert. Keine Thesis-LaTeX-Änderung. App-/Testquelle nach Prüfexport unverändert; Abschlussprüfung in externem verification.json.

## Validation / Recovery
Gezielt: python -m pytest tests/test_answer_sentences.py tests/test_answer_plan.py.
Vollständig: python -m pytest; node --test tests/frontend.test.cjs.
Docker: docker build --pull --no-cache --target test; docker run --rm --network none; Runtimeziel bauen und Health prüfen. Belege außerhalb Repository unter LOCALAPPDATA/LENA/verification/2026-10-26-simple-sentences. Keine nicht geprüften Erfolge berichten. Änderungen ausschließlich anhand eigener Diffs korrigieren, keine fremden Änderungen zurücksetzen.

## Offene Grenzen
Freie Quellangaben können weiterhin komplex sein. Satzvorlagen vereinfachen die Darstellung, nicht die fachliche Quelle. Menschliches Sprachreview und abschließende gemeinsame Commit-Messung bleiben erforderlich. Bestehende manuelle Baseline muss nach dem finalen Commit erneut zugeordnet werden.
