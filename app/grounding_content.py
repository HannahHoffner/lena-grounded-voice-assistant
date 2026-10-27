"""Historical lexical diagnostic; not an acceptance gate since validator 8.

Retained for characterization and reproducibility of the 02a3612 ablation.
The runtime deliberately does not call this module.


Claimtypunabhängige Inhaltsprüfung für Leistungs- und Identitätsaussagen.

Audit-Befund F-01 (23.10.2026): ``Scharni bietet eine Fahrradreparatur an.``
wurde mit einer gültigen Namensreferenz akzeptiert, sobald das Modell den Satz
als ``action`` oder ``fact`` statt als ``service`` deklarierte. Die Ursache war
nicht ein fehlendes Stichwort, sondern dass die Strenge der Prüfung vom
selbstdeklarierten Claimtyp abhing und unbekannte Inhalte als ``not_checked``
durchgelassen wurden.

Dieses Modul ersetzt die Abhängigkeit vom Claimtyp durch eine Beobachtung des
Validators selbst und einen entscheidbaren Vertrag:

1. **Aussageform erkennen.** Ein Satz, der mit einem Prädikat einer
   geschlossenen Klasse behauptet, dass ein Angebot etwas *anbietet, ausgibt,
   bereitstellt, hat* oder dass man dort etwas *bekommt/findet*, ist eine
   Leistungsaussage – gleich welchen Claimtyp das Modell angibt. Für Deutsch
   und Englisch zählen zusätzlich Identitätsaussagen mit Kopula und
   unbestimmtem Artikel („X ist eine …“, „X is a …“).
2. **Offene Inhaltswörter abdecken.** In einer solchen Aussage muss jedes Wort
   einer offenen Wortklasse entweder aus den Fakten desselben ausgewählten
   Angebots stammen (mit begrenzter Flexions- und Kompositatoleranz) oder zu
   einem Wortschatz gehören, den eine *eigene nachgelagerte Prüfung* bewertet:
   Leistungs- und Zielgruppenkonzepte (``grounding_claims``), Wochentage
   (``WEEKDAY_NOT_CITED``/Zeitfenster) und – nur bei kuratiertem
   ``fee_status`` – Entgelt-/Zahlungswörter (``fee_claim_matches``). Zahlen prüft ``_validate_operational_tokens``.
3. **Unbekanntes schlägt geschlossen fehl.** Bleibt ein Wort übrig, wird die
   gesamte Antwort mit ``CONTENT_NOT_COVERED`` verworfen; der Aufrufer nutzt
   dann Retry bzw. das kuratierte Template.

Grenzen (bewusst, dokumentiert): Die Wortklassenlisten sind endlich. Für
Polnisch, Rumänisch und Russisch liegen die Fakten überwiegend deutsch vor; dort
können Leistungsaussagen nur über den mehrsprachigen Konzeptwortschatz belegt
werden, frei übersetzte Zusatzwörter führen zur (sicheren) Ablehnung.
Kopula-Beschreibungen ohne unbestimmten Artikel sowie Kopulasätze in PL/RO/RU
fallen nicht unter Schritt 1 und werden weiterhin nur durch die Konzept-,
Zielgruppen-, Alters-, Entgelt- und Zahlenprüfungen begrenzt. Das ist eine
begrenzte regelbasierte Faktenkontrolle, keine Entailment-Garantie.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from .grounding_claims import (
    DAILY_LABEL,
    WEEKDAY_NAMES,
    Fact,
    detect_service_concepts,
    detect_target_concepts,
    transliterated,
)
from .grounding_constraints import OPERATIONAL_LABEL_WORDS, fee_or_payment_word
from .models import Language


_WORD_RE = re.compile(r"[^\W\d_]+")


def _words(value: str) -> frozenset[str]:
    return frozenset(value.split())


# Prädikate, die eine Bereitstellungs-, Erhalts- oder Besitzaussage über das
# Angebot bilden. Formen sind transliteriert und diakritikfrei (siehe
# ``transliterated``). Die Liste beschreibt eine Wortklasse, keine Leistungen.
PROVISION_PREDICATES: dict[Language, frozenset[str]] = {
    Language.DE: _words(
        "biete bietest bietet bieten anbieten anbietet angeboten gibt gebt geben gib "
        "vergibt vergeben verteilt verteilen ausgeben ausgegeben bekommst bekommt bekommen "
        "erhaltst erhalt erhalten kriegst hat hast haben verfugt verfugen stellt stellen "
        "bereitgestellt bereit findest findet finden"
    ),
    Language.EN: _words(
        "offer offers offered offering provide provides provided providing give gives given "
        "get gets receive receives received has have hand hands handed serve serves served "
        "distribute distributes find finds"
    ),
    Language.PL: _words(
        "oferuje oferuja zapewnia zapewniaja daje daja dostaniesz dostanie otrzymasz otrzyma "
        "ma maja wydaje wydaja udostepnia znajdziesz"
    ),
    Language.RO: _words(
        "ofera oferi ofere asigura da dau primesti primeste primi are au distribuie gasesti"
    ),
    Language.RU: _words(
        "predlagaet predlagayut predostavlyaet predostavlyayut daet dayut poluchish poluchit "
        "poluchite poluchaet est imeet imeyut vydaet vydayut razdaet razdayut naydesh"
    ),
}

# Kopula + unbestimmter Artikel als Identitäts-/Klassifikationsaussage. Nur für
# die Sprachen, in denen die Fakten selbst vorliegen (siehe Modulgrenzen).
_IDENTITY_PATTERNS: dict[Language, re.Pattern[str]] = {
    Language.DE: re.compile(r"\b(?:ist|sind)\s+(?:ein|eine|einer|einen|eines)\b"),
    Language.EN: re.compile(r"\b(?:is|are)\s+(?:a|an)\b"),
}

# Geschlossene Wortklassen: Artikel, Pronomen, Präpositionen, Konjunktionen,
# Hilfs-/Modalverben, Partikeln, Negation, Quantoren sowie die feste
# Darstellungssprache der Oberfläche (Karte, Adresse, Quelle). Keine dieser
# Formen benennt eine Leistung, Zielgruppe, Bedingung oder Verfügbarkeit;
# Negation wird zusätzlich in ``grounding.py`` gesondert ausgewertet.
CLOSED_CLASS_WORDS: dict[Language, frozenset[str]] = {
    Language.DE: _words(
        "der die das den dem des ein eine einen einem einer eines kein keine keinen keinem keiner "
        "und oder aber sowie auch nur noch schon sehr ganz mit ohne fur von vom zu zum zur bei beim "
        "in im an am auf aus uber unter nach vor neben zwischen um durch gegen bis ab seit dort hier "
        "da dann du dich dir dein deine deinen deinem deiner er sie es wir ihr ihnen ihm ihn sich "
        "man ist sind war waren wird werden wurde wurden kann kannst konnen darf darfst musst muss "
        "soll sollst nicht so wie als was wo wann jede jeder jedes alle allen einige mehr weitere "
        "weiteren weiterer zudem ausserdem dabei dazu davon damit dafur pro je ebenfalls bitte "
        "dies diese dieser dieses diesem diesen sein seine seinem seinen seiner ihre ihrem ihren "
        "ihrer dort etwa ca bzw usw etc z b u a wahrend wegen trotz laut gemass innerhalb ausserhalb "
        "per uber telefonisch schriftlich personlich direkt "
        "karte kartchen informationen information details angaben adresse anschrift telefon "
        "telefonnummer kontakt email mail webseite website offnungszeiten offnungszeit zeiten "
        "uhr angebot angebote quelle beschrieben angegeben genannt dokumentiert vermerkt"
    ),
    Language.EN: _words(
        "the a an and or but also only with without for of to from at in on by into about as is "
        "are was were be been will can could may must should you your they them their it its this "
        "that these those there here we us our he she his her who which what where when more other "
        "another each all some any not no too very please per such also during because via within "
        "by phone directly in person "
        "card information details address phone telephone contact email website opening hours time "
        "times offer source described stated listed documented noted mentioned"
    ),
    Language.PL: _words(
        "i oraz lub albo a ale tez takze rowniez tylko z ze w we na do od dla przy po o u za bez "
        "przez pod nad jest sa to ten ta te tam tu tutaj ty ci cie ciebie tobie twoj twoja ich jego "
        "jej on ona one oni sie mozesz moze mozna nie bardzo wiecej inne kazdy wszystkie jak gdzie "
        "kiedy ktory ktora ktore prosze karta karcie karty informacje informacji szczegoly adres "
        "telefon kontakt godziny otwarcia oferta podczas telefonicznie mailowo"
    ),
    Language.RO: _words(
        "si sau dar iar de la in pe cu fara pentru din spre prin sub peste un o unui unei niste "
        "este e sunt poti poate pot tu tine te iti tau ta lor lui ei ea el ele se acolo aici mai "
        "foarte doar numai nu care ce unde cand fiecare toate alte alt alta card cardul informatii "
        "detalii adresa telefon contact program oferta va vei timpul telefonic"
    ),
    Language.RU: _words(
        "i ili a no takzhe tolko s so v vo na k ko ot do dlya pri po o ob u za bez cherez pod nad "
        "eto etot eta eti tam zdes ty tebya tebe tvoy tvoya ikh ego ee on ona oni my vy vas vam "
        "mozhesh mozhno mozhet budet ne net ochen bolshe drugie kazhdyy vse kak gde kogda kotoryy "
        "kotoraya kotorye pozhaluysta kartochke kartochka informatsiya informatsii adres telefon "
        "tozhe kontakt chasy raboty vremya telefonu pochte"
    ),
}

# Handlungsaufforderungen an die lesende Person („Nutze X.“, „Ruf an.“) sind
# ebenfalls eine geschlossene Klasse: Sie behaupten nichts über das Angebot.
DIRECTIVE_VERBS: dict[Language, frozenset[str]] = {
    Language.DE: _words(
        "nutze nutzen geh gehe gehen wende wenden melde melden ruf rufe anrufen kontaktiere "
        "kontaktieren frag frage fragen besuche besuchen komm komme schau schaue erreichst erreichen"
    ),
    Language.EN: _words("use go contact call ask visit come turn check see reach"),
    Language.PL: _words("skorzystaj idz zglos zadzwon skontaktuj zapytaj odwiedz przyjdz sprawdz"),
    Language.RO: _words("foloseste mergi suna contacteaza intreaba viziteaza vino verifica"),
    Language.RU: _words(
        "vospolzuysya idi obratis obratites pozvoni pozvonite svyazhis sprosi posetit prikhodi"
    ),
}

# Generische Personennomen und Zeitbeschriftungen. Die Bedeutung einer
# Zielgruppe trägt das geprüfte Attribut („wohnungslose“, „Frauen“), nicht das
# Kopfnomen („Menschen“); Öffnungs-/Terminbeschriftungen sind Darstellung, die
# zugehörigen Tage und Uhrzeiten prüfen die Zeitregeln. „jetzt/aktuell“ bleibt
# davon getrennt durch ``claims_current_availability`` erfasst.
GENERIC_HEADS: dict[Language, frozenset[str]] = {
    Language.DE: _words("menschen mensch personen person leute termine termin geoffnet offen sprechzeiten"),
    Language.EN: _words("people persons person open opens hours schedule"),
    Language.PL: _words("ludzie ludzi osoby osob osoba otwarte otwarty otwarta czynne czynny godziny"),
    Language.RO: _words("persoane persoanele persoana oameni deschis deschisa deschiderea intre orar"),
    Language.RU: _words("lyudi lyudey lyudyam lyudam otkryt otkryta otkryto otkryty priem raspisanie"),
}

# Minimale gemeinsame Präfixlänge und maximale Endungsabweichung der
# Flexionstoleranz („Schlafplätze“ zu „Schlafplatz“, „sonntags“ zu „Sonntag“).
_MIN_STEM = 4
_MAX_SUFFIX = 3


def _tokens(value: str) -> list[str]:
    return _WORD_RE.findall(transliterated(value))


def asserts_provision(text: str, language: Language) -> bool:
    """Erkennt eine Bereitstellungs-/Erhalts-/Besitz- oder Identitätsaussage."""
    tokens = _tokens(text)
    if any(token in PROVISION_PREDICATES[language] for token in tokens):
        return True
    pattern = _IDENTITY_PATTERNS.get(language)
    return bool(pattern and pattern.search(" ".join(tokens)))


def _evidence_vocabulary(facts: Sequence[Fact]) -> set[str]:
    vocabulary: set[str] = set()
    for _, value in facts:
        tokens = _tokens(value)
        vocabulary.update(tokens)
        # Komposita: „Wäsche waschen“ deckt „Wäschewaschen“.
        vocabulary.update(left + right for left, right in zip(tokens, tokens[1:]))
    return vocabulary


def _inflection_of(word: str, vocabulary: Iterable[str]) -> bool:
    for known in vocabulary:
        shorter = min(len(word), len(known))
        if shorter < _MIN_STEM or abs(len(word) - len(known)) > _MAX_SUFFIX:
            continue
        prefix = 0
        for left, right in zip(word, known):
            if left != right:
                break
            prefix += 1
        if prefix >= _MIN_STEM and prefix >= max(len(word), len(known)) - _MAX_SUFFIX:
            return True
    return False


# Übliche Wochentagsabkürzungen („Mo–Fr“). Sie tragen dieselbe Bedeutung wie
# die ausgeschriebenen Namen; Zeit-/Tagesbezüge prüfen die Uhrzeit-,
# Wochentags- und Zeitfensterregeln in ``grounding.py`` unabhängig davon.
WEEKDAY_ABBREVIATIONS: dict[Language, frozenset[str]] = {
    Language.DE: _words("mo di mi do fr sa so"),
    Language.EN: _words("mon tue tues wed thu thur thurs fri sat sun"),
    Language.PL: _words("pon pn wt sr czw pt sob nd niedz"),
    Language.RO: _words("lu ma mi jo vi sa du lun mar mie vin sam dum"),
    Language.RU: _words("pn vt sr cht pt sb vs"),
}


def _schedule_word(word: str, language: Language) -> bool:
    labels = [transliterated(name) for name in WEEKDAY_NAMES[language]]
    labels.append(transliterated(DAILY_LABEL[language]))
    return word in WEEKDAY_ABBREVIATIONS[language] or word in labels or _inflection_of(word, labels)


def unsupported_content_words(
    text: str, facts: Sequence[Fact], language: Language, *, require_coverage: bool = False,
) -> tuple[str, ...]:
    """Liefert offene Inhaltswörter einer Leistungsaussage ohne Beleg.

    Historisch werden nur Leistungs-/Identitätsaussagen geprüft. Vertrag 7
    setzt require_coverage auch für andere Formulierungen, damit ein anderes
    Verb oder Claimlabel keine unbelegten Inhalte freigibt.
    Ein leeres Ergebnis ist keine Wahrheitsaussage: es
    bedeutet nur, dass jedes Inhaltswort belegt ist oder einer anderen,
    unabhängig ausgeführten Prüfung unterliegt.
    """
    if not require_coverage and not asserts_provision(text, language):
        return ()
    closed = (
        CLOSED_CLASS_WORDS[language] | PROVISION_PREDICATES[language] | DIRECTIVE_VERBS[language]
        | OPERATIONAL_LABEL_WORDS[language] | GENERIC_HEADS[language]
    )
    vocabulary = _evidence_vocabulary(facts)
    # Entgelt-/Zahlungswörter prüft fee_claim_matches nur gegen einen
    # kuratierten fee_status; ohne ihn müssen sie wie jedes Wort belegt sein.
    fee_checked = any(kind == "fee_status" for kind, _ in facts)
    residual: list[str] = []
    for word in _tokens(text):
        if (
            len(word) == 1  # Einzelbuchstaben („E-Mail“, „z. B.“) tragen keinen Inhalt
            or word in closed
            or word in vocabulary
            or detect_service_concepts(word, language)
            or detect_target_concepts(word, language)
            or (fee_checked and fee_or_payment_word(word, language))
            or _schedule_word(word, language)
            or _inflection_of(word, vocabulary)
        ):
            continue
        residual.append(word)
    return tuple(dict.fromkeys(residual))
