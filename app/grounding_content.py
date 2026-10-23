"""Conservative lexical coverage, independent of model-declared claim types.

Coverage is necessary, never sufficient, for entailment. The caller must still
check polarity, service roles, target groups, prices, schedules and availability.
Unknown content fails closed; the orchestrator can use its curated template.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from .grounding_claims import Fact, detect_service_concepts, detect_target_concepts, transliterated
from .grounding_constraints import supported_operational_statement
from .models import Language


# Function words and navigation language, not an extensible service whitelist.
# Service/target semantics remain in grounding_claims and grounding_constraints.
_CONNECTIVES = {
    Language.DE: "geh gehen wenden konnen erhalten erhaltst man diese dieses diesen bitte nacht die das den dem des ein eine einer einem einen eines er sie es du dich dir dein deine sich wir ihr ihnen ist sind bietet bieten gibt hat haben kannst kann konnen nutze nutzen wende melde bei an ruf rufe kontakt kontaktiere findest finden erhältst erhalten dort hier fur von bis ab uber unter und oder mit ohne im in am auf zu zur zum als auch nur sowie pro adresse telefon telefonnummer weitere informationen stehen findest karte details angebot angebote leistungen",
    Language.EN: "go please payment by a an it they you your their is are offers offer provides provide has have can use contact call find at in on to for from of with without and or also only per there here address phone more information details card see this that available services service",
    Language.PL: "idz prosze sa to ten ta te oferuje oferują oferuja mozesz skorzystaj skontaktuj sie zadzwon znajdziesz w we na do od dla z ze bez i lub oraz za tu tam adres telefon wiecej informacji karcie karta",
    Language.RO: "mergi sunt ofera poti foloseste folositi contacteaza suna gasesti la in pe de din pentru cu fara si sau ori un o unei unui aici acolo adresa telefon mai multe informatii card cardul",
    Language.RU: "obratis svyazhis est predlagaet predlagayut vy ty mozhete mozhno ispolzuy obratites obratitsya pozvoni pozvonite v na k ot do dlya s so bez i ili po zdes tam adres telefon bolshe informatsii kartochke",
}


def has_content_coverage(text: str, facts: Sequence[Fact], language: Language) -> bool:
    """Require every content token to have evidence or a known semantic check.

    Fact vocabulary is scoped to this offer. Known concept words are admitted
    only to the subsequent semantic checks, not treated as true by this helper.
    No claim enum, citation count or presence of a known service bypasses this
    check. In particular, mixed supported/unknown service lists fail closed.
    """
    if supported_operational_statement(text, facts, language):
        return True
    allowed = set(_CONNECTIVES[language].split())
    allowed.update(word for _, value in facts for word in re.findall(r"\w+", transliterated(value)))
    for word in re.findall(r"\w+", transliterated(text)):
        if word in allowed or detect_service_concepts(word, language) or detect_target_concepts(word, language):
            continue
        return False
    return True
