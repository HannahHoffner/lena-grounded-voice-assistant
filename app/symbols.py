from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .kb import KnowledgeBase
from .models import (
    Language,
    MapDestination,
    PageMetadata,
    SymbolActionRequest,
    SymbolCategory,
    SymbolConfigResponse,
    SymbolResultCard,
    SymbolSubstep,
)
from .retrieval import RetrievalEngine, normalize_text


Localized = dict[Language, str]
Group = Literal["primary", "secondary"]
ResultMode = Literal["cards-map", "cards", "static"]


@dataclass(frozen=True, slots=True)
class SymbolDefinition:
    id: str
    icon: str
    labels: Localized
    query: str
    priority: int
    group: Group = "primary"
    result_mode: ResultMode = "cards-map"
    categories: tuple[str, ...] = ()
    service_types: tuple[str, ...] = ()
    page_ids: tuple[str, ...] = ()
    substeps: tuple["SymbolSubstepDefinition", ...] = ()
    static_text: Localized | None = None
    no_map_reason: Localized | None = None
    intro: Localized | None = None
    disclaimer: Localized | None = None


@dataclass(frozen=True, slots=True)
class SymbolSubstepDefinition:
    id: str
    icon: str
    labels: Localized
    query_addition: str = ""
    gender_access: tuple[str, ...] = ()
    target_groups: tuple[str, ...] = ()
    service_types: tuple[str, ...] = ()


def get_symbol_config(language: Language) -> SymbolConfigResponse:
    return SymbolConfigResponse(
        language=language,
        categories=[
            SymbolCategory(
                id=definition.id,
                label=_localize(definition.labels, language),
                icon=definition.icon,
                priority=definition.priority,
                group=definition.group,
                result_mode=definition.result_mode,
                substeps=[
                    SymbolSubstep(
                        id=substep.id,
                        label=_localize(substep.labels, language),
                        icon=substep.icon,
                    )
                    for substep in definition.substeps
                ],
            )
            for definition in sorted(SYMBOLS, key=lambda item: (item.group != "primary", item.priority, item.id))
        ],
    )


@dataclass(slots=True)
class SymbolAnswerDraft:
    answer_text: str
    status: Literal["ok", "weak_match", "unknown", "crisis"]
    category_id: str
    substep_id: str | None
    cards: list[SymbolResultCard] = field(default_factory=list)
    retrieved_page_ids: list[str] = field(default_factory=list)
    map_destinations: list[MapDestination] = field(default_factory=list)
    static_response: bool = False
    no_map_reason: str | None = None
    query: str = ""


def build_symbol_answer(payload: SymbolActionRequest, kb: KnowledgeBase) -> SymbolAnswerDraft:
    definition = symbol_by_id(payload.category_id)
    if not definition:
        return SymbolAnswerDraft(
            answer_text=_localize(UNKNOWN_TEXT, payload.language),
            status="unknown",
            category_id=payload.category_id,
            substep_id=payload.substep_id,
        )

    substep = substep_by_id(definition, payload.substep_id)
    if definition.static_text:
        return SymbolAnswerDraft(
            answer_text=_localize(definition.static_text, payload.language),
            status="crisis" if definition.id == "emergency" else "ok",
            category_id=definition.id,
            substep_id=substep.id if substep else payload.substep_id,
            retrieved_page_ids=_known_page_ids(kb, definition.page_ids),
            static_response=True,
            no_map_reason=_localize(definition.no_map_reason, payload.language) if definition.no_map_reason else None,
            query=definition.query,
        )

    query = " ".join(part for part in (definition.query, substep.query_addition if substep else "") if part).strip()
    retrieved = RetrievalEngine(kb).retrieve(query, payload.language, limit=8)
    pages = _select_pages(kb, definition, substep, [item.page_id for item in retrieved])
    if len(pages) < 3:
        fallback_ids = [page.page_id for page in kb.dataset.pages]
        pages = _merge_pages(pages, _select_pages(kb, definition, substep, fallback_ids))
    pages = _dedupe_place_pages(pages)[:6]

    if definition.id == "water":
        return SymbolAnswerDraft(
            answer_text=_water_answer_text(payload.language),
            status="ok",
            category_id=definition.id,
            substep_id=substep.id if substep else payload.substep_id,
            cards=_water_cards(payload.language),
            retrieved_page_ids=_known_page_ids(kb, definition.page_ids),
            map_destinations=_water_map_destinations(),
            query=query,
        )

    if definition.id == "hygiene" and substep and substep.id == "toilet":
        return SymbolAnswerDraft(
            answer_text=toilet_answer_text(payload.language),
            status="ok",
            category_id=definition.id,
            substep_id=substep.id,
            cards=toilet_cards(payload.language),
            retrieved_page_ids=_known_page_ids(kb, definition.page_ids),
            map_destinations=toilet_map_destinations(),
            query=query,
        )

    if not pages:
        return SymbolAnswerDraft(
            answer_text=_localize(UNKNOWN_TEXT, payload.language),
            status="unknown",
            category_id=definition.id,
            substep_id=substep.id if substep else payload.substep_id,
            no_map_reason=_localize(definition.no_map_reason, payload.language) if definition.no_map_reason else None,
            query=query,
        )

    cards = [_card_for_page(page, payload.language, definition) for page in pages]
    answer_text = _answer_text(definition, payload.language, cards)
    return SymbolAnswerDraft(
        answer_text=answer_text,
        status="ok",
        category_id=definition.id,
        substep_id=substep.id if substep else payload.substep_id,
        cards=cards,
        retrieved_page_ids=[card.page_id for card in cards],
        no_map_reason=_localize(definition.no_map_reason, payload.language) if definition.no_map_reason else None,
        query=query,
    )


def symbol_by_id(category_id: str) -> SymbolDefinition | None:
    return next((definition for definition in SYMBOLS if definition.id == category_id), None)


def substep_by_id(definition: SymbolDefinition, substep_id: str | None) -> SymbolSubstepDefinition | None:
    if not substep_id:
        return None
    return next((substep for substep in definition.substeps if substep.id == substep_id), None)


def _select_pages(
    kb: KnowledgeBase,
    definition: SymbolDefinition,
    substep: SymbolSubstepDefinition | None,
    page_ids: list[str],
) -> list[PageMetadata]:
    pages: list[PageMetadata] = []
    seen: set[str] = set()
    available = {page.page_id for page in kb.dataset.pages}
    for page_id in definition.page_ids:
        if page_id in available and page_id not in seen:
            page = kb.get_page(page_id)
            if _matches(page, definition, substep):
                pages.append(page)
                seen.add(page.page_id)
    for page_id in page_ids:
        if page_id not in available or page_id in seen:
            continue
        page = kb.get_page(page_id)
        if not _matches(page, definition, substep):
            continue
        pages.append(page)
        seen.add(page.page_id)
    pages.sort(key=lambda page: _page_rank(page, definition, substep))
    return pages


def _merge_pages(primary: list[PageMetadata], fallback: list[PageMetadata]) -> list[PageMetadata]:
    merged: list[PageMetadata] = []
    seen: set[str] = set()
    for page in [*primary, *fallback]:
        if page.page_id in seen:
            continue
        merged.append(page)
        seen.add(page.page_id)
    return merged


def _dedupe_place_pages(pages: list[PageMetadata]) -> list[PageMetadata]:
    deduped: list[PageMetadata] = []
    seen: set[str] = set()
    for page in pages:
        key = _place_dedupe_key(page)
        if key in seen:
            continue
        deduped.append(page)
        seen.add(key)
    return deduped


def _place_dedupe_key(page: PageMetadata) -> str:
    if page.entity_signature:
        return f"signature:{page.entity_signature}"
    if page.latitude is not None and page.longitude is not None:
        return f"geo:{round(page.latitude, 5)}:{round(page.longitude, 5)}"
    normalized_address = normalize_text(page.normalized_address or page.address or "")
    if normalized_address:
        return f"address:{normalized_address}"
    return f"title:{normalize_text(page.canonical_title or page.title)}"


def _matches(page: PageMetadata, definition: SymbolDefinition, substep: SymbolSubstepDefinition | None) -> bool:
    if page.status in {"removed", "deprecated", "merged"}:
        return False
    if definition.categories and page.category not in definition.categories:
        if page.service_type not in definition.service_types:
            return False
    elif definition.service_types and page.service_type not in definition.service_types:
        return False
    if page.service_type == "service_catalog" and definition.result_mode == "cards-map":
        return False
    if not substep:
        return True
    if substep.service_types and page.service_type not in substep.service_types:
        return False
    if substep.gender_access:
        page_groups = set(page.target_groups)
        if page.gender_access not in substep.gender_access and not (page_groups & set(substep.gender_access)):
            return False
    if substep.target_groups and not (set(page.target_groups) & set(substep.target_groups)):
        return False
    return True


def _page_rank(page: PageMetadata, definition: SymbolDefinition, substep: SymbolSubstepDefinition | None) -> tuple[int, int, int, int, str]:
    preferred_index = definition.page_ids.index(page.page_id) if page.page_id in definition.page_ids else 999
    gender_match = 0
    if substep and substep.gender_access:
        gender_match = 0 if page.gender_access in substep.gender_access or set(page.target_groups) & set(substep.gender_access) else 1
    return (
        preferred_index,
        gender_match,
        0 if page.address else 1,
        0 if page.opening_hours else 1,
        page.page_id,
    )


def _card_for_page(page: PageMetadata, language: Language, definition: SymbolDefinition) -> SymbolResultCard:
    return SymbolResultCard(
        page_id=page.page_id,
        title=page.title,
        category=page.category,
        service_type=page.service_type,
        address=page.address,
        opening_hours=page.opening_hours[:4],
        phone=page.phone,
        description=_short_text(page.description or page.summary),
        action=_action_text(page, language, definition),
        last_updated=page.last_updated,
        has_map_location=bool(page.address and page.latitude is not None and page.longitude is not None),
    )


def _water_cards(language: Language) -> list[SymbolResultCard]:
    return [
        SymbolResultCard(
            page_id=point.id,
            title=point.name,
            category="water",
            service_type="drinking_fountain",
            address=point.address,
            description=point.note,
            action=_localize(WATER_ACTION, language),
            has_map_location=True,
        )
        for point in WATER_POINTS[:8]
    ]


def _water_map_destinations() -> list[MapDestination]:
    return [
        MapDestination(
            id=point.id,
            page_id=point.id,
            label=point.name,
            organization_label="Leipziger Wasserwerke",
            service_type="drinking_fountain",
            address=point.address,
            latitude=point.latitude,
            longitude=point.longitude,
            description=point.note,
        )
        for point in WATER_POINTS
    ]


def _water_answer_text(language: Language) -> str:
    return _localize(WATER_INTRO, language)


def toilet_cards(language: Language, *, free_only: bool = False, limit: int = 8) -> list[SymbolResultCard]:
    return [
        SymbolResultCard(
            page_id=point.id,
            title=point.place,
            category="hygiene",
            service_type="public_toilet",
            address=point.address,
            opening_hours=[point.opening],
            phone=point.phone,
            description=_toilet_description(point),
            action=_toilet_action(point, language),
            has_map_location=True,
        )
        for point in _selected_toilet_points(free_only=free_only)[:limit]
    ]


def toilet_map_destinations(*, free_only: bool = False) -> list[MapDestination]:
    return [
        MapDestination(
            id=point.id,
            page_id=point.id,
            label=point.place,
            organization_label=point.operator,
            service_type="public_toilet",
            address=point.address,
            latitude=point.latitude,
            longitude=point.longitude,
            description=_toilet_description(point),
            opening_hours=[point.opening],
        )
        for point in _selected_toilet_points(free_only=free_only)
    ]


def toilet_answer_text(language: Language) -> str:
    return _localize(TOILET_INTRO, language)


def _selected_toilet_points(*, free_only: bool = False) -> list["ToiletPoint"]:
    if not free_only:
        return list(TOILET_POINTS)
    return [point for point in TOILET_POINTS if "kostenfrei" in point.cost.casefold()]


def _toilet_description(point: "ToiletPoint") -> str:
    return f"Kosten: {point.cost}. Ausstattung: {point.equipment}."


def _toilet_action(point: "ToiletPoint", language: Language) -> str:
    if "kostenfrei" in point.cost.casefold():
        return _localize(TOILET_FREE_ACTION, language)
    return _localize(TOILET_PAID_ACTION, language)


def _answer_text(definition: SymbolDefinition, language: Language, cards: list[SymbolResultCard]) -> str:
    parts: list[str] = []
    if definition.intro:
        parts.append(_localize(definition.intro, language))
    if definition.disclaimer:
        parts.append(_localize(definition.disclaimer, language))
    if definition.id in {"water", "toilet"} and definition.no_map_reason:
        parts.append(_localize(definition.no_map_reason, language))
    if not parts:
        parts.append(_localize(RESULT_INTRO, language))
    if cards:
        parts.append(_localize(RESULT_CARD_HINT, language))
    return " ".join(parts)


def _action_text(page: PageMetadata, language: Language, definition: SymbolDefinition) -> str:
    if definition.id == "medical":
        return _localize(MEDICAL_ACTION, language)
    if page.address:
        return _localize(GO_ACTION, language)
    if page.phone:
        return _localize(CALL_ACTION, language)
    return _localize(ASK_HELP_ACTION, language)


def _short_text(text: str, limit: int = 180) -> str | None:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rsplit(" ", 1)[0].rstrip(".") + "."


def _known_page_ids(kb: KnowledgeBase, page_ids: tuple[str, ...]) -> list[str]:
    available = {page.page_id for page in kb.dataset.pages}
    return [page_id for page_id in page_ids if page_id in available]


def _localize(values: Localized, language: Language) -> str:
    return values.get(language) or values[Language.DE]


def _l(de: str, en: str, pl: str, ro: str, ru: str) -> Localized:
    return {
        Language.DE: de,
        Language.EN: en,
        Language.PL: pl,
        Language.RO: ro,
        Language.RU: ru,
    }


UNKNOWN_TEXT = _l(
    "Dazu habe ich keine sichere passende Hilfe gefunden.",
    "I did not find safe matching help for this.",
    "Nie znalazłem bezpiecznej pasującej pomocy.",
    "Nu am găsit un ajutor potrivit și sigur.",
    "Я не нашла надежящую подходящую помощь.",
)
RESULT_INTRO = _l(
    "Diese Orte können helfen.",
    "These places may help.",
    "Te miejsca mogą pomóc.",
    "Aceste locuri pot ajuta.",
    "Эти места могут помочь.",
)
RESULT_CARD_HINT = _l(
    "Tippen Sie einen Ort an, um Details zu sehen.",
    "Tap a place to see details.",
    "Dotknij miejsca, aby zobaczyć szczegóły.",
    "Atinge un loc pentru detalii.",
    "Нажмите на место, чтобы увидеть детали.",
)
GO_ACTION = _l(
    "Gehen Sie zur Adresse.",
    "Go to this address.",
    "Idź pod ten adres.",
    "Mergi la această adresă.",
    "Идите по этому адресу.",
)
CALL_ACTION = _l(
    "Rufen Sie dort an, wenn das möglich ist.",
    "Call them if you can.",
    "Zadzwoń tam, jeśli możesz.",
    "Sună acolo dacă poți.",
    "Позвоните туда, если можете.",
)
ASK_HELP_ACTION = _l(
    "Fragen Sie dort nach Hilfe.",
    "Ask there for help.",
    "Zapytaj tam o pomoc.",
    "Întreabă acolo despre ajutor.",
    "Спросите там о помощи.",
)
MEDICAL_ACTION = _l(
    "Bei akuter Gefahr sofort 112 rufen.",
    "In immediate danger call 112 now.",
    "W nagłym zagrożeniu dzwoń teraz pod 112.",
    "În pericol imediat sună acum la 112.",
    "При немедленной опасности звоните 112.",
)


WATER_ACTION = _l(
    "Gehen Sie zum Punkt auf der Karte.",
    "Go to the point on the map.",
    "Idz do punktu na mapie.",
    "Mergi la punctul de pe harta.",
    "Идите к точке на карте.",
)
WATER_INTRO = _l(
    "Offizielle Trinkwasserbrunnen der Leipziger Wasserwerke. In der kalten Jahreszeit können Brunnen abgeschaltet sein.",
    "Official drinking-water fountains from Leipziger Wasserwerke. In cold months fountains may be switched off.",
    "Oficjalne punkty wody pitnej Leipziger Wasserwerke. W zimnych miesiacach moga byc wylaczone.",
    "Fantani oficiale cu apa potabila de la Leipziger Wasserwerke. In lunile reci pot fi oprite.",
    "Официальные питьевые фонтаны Leipziger Wasserwerke. В холодные месяцы они могут быть отключены.",
)
TOILET_INTRO = _l(
    "Öffentliche City-Toiletten. Meist 50 Cent. Mit Euroschlüssel kostenlos. Ein Standort ist kostenfrei.",
    "Public city toilets. Usually 50 cents. Free with Euro key. One location is free.",
    "Publiczne toalety miejskie. Zwykle 50 centow. Z kluczem Euro bezplatnie. Jedno miejsce jest bezplatne.",
    "Toalete publice ale orasului. De obicei 50 de centi. Gratuit cu cheia Euro. Un loc este gratuit.",
    "Общественные городские туалеты. Обычно 50 центов. С Euro key бесплатно. Одно место бесплатное.",
)
TOILET_PAID_ACTION = _l(
    "50 Cent bereithalten. Muenzen oder Karte.",
    "Have 50 cents ready. Coins or card.",
    "Przygotuj 50 centow. Monety albo karta.",
    "Pregateste 50 de centi. Monede sau card.",
    "Подготовьте 50 центов. Монеты или карта.",
)
TOILET_FREE_ACTION = _l(
    "Dieser Standort ist kostenfrei.",
    "This location is free.",
    "To miejsce jest bezplatne.",
    "Acest loc este gratuit.",
    "Это место бесплатное.",
)


@dataclass(frozen=True, slots=True)
class WaterPoint:
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    note: str | None = None


@dataclass(frozen=True, slots=True)
class ToiletPoint:
    id: str
    place: str
    district: str
    opening: str
    equipment: str
    cost: str
    phone: str
    latitude: float
    longitude: float
    operator: str = "RBL Media GmbH"

    @property
    def address(self) -> str:
        return f"{self.place}, {self.district}, Leipzig"


WATER_POINTS: tuple[WaterPoint, ...] = (
    WaterPoint("water-kurt-masur-platz", "Kurt-Masur-Platz", "Kurt-Masur-Platz, 04109 Leipzig", 51.3383275, 12.3799126, "Am Gewandhaus."),
    WaterPoint("water-katharinenstrasse", "Katharinenstrasse", "Katharinenstrasse, 04109 Leipzig", 51.34237, 12.3751626000001),
    WaterPoint("water-windorfer-strasse", "Windorfer Straße", "Windorfer Straße, 04229 Leipzig", 51.3146466, 12.3277264, "Höhe Taborkirche."),
    WaterPoint("water-markranstaedt-strandbad", "Markranstaedt: Strandbad", "Am Eingang des Strandbades, Markranstaedt", 51.309587, 12.242329),
    WaterPoint("water-petersstrasse", "Petersstrasse", "Petersstrasse, 04109 Leipzig", 51.339025, 12.374591),
    WaterPoint("water-karl-heine-platz", "Karl-Heine-Platz", "Karl-Heine-Platz, 04229 Leipzig", 51.3326943, 12.336354),
    WaterPoint("water-lindenauer-markt", "Lindenauer Markt", "Lindenauer Markt, 04177 Leipzig", 51.3372454, 12.3343972),
    WaterPoint("water-markt", "Markt", "Markt, Leipzig", 51.3806512, 12.5004706),
    WaterPoint("water-arthur-bretschneider-park", "Arthur-Bretschneider-Park", "Arthur-Bretschneider-Park, Leipzig", 51.3674033, 12.381683),
    WaterPoint("water-paunsdorf-gruener-bogen", "Paunsdorf, Grüner Bogen", "Grüner Bogen, Zugang über Hainbuchenstraße, Leipzig", 51.3579817, 12.4571525, "Nähe Kletterspielplatz."),
    WaterPoint("water-voelkerschlachtdenkmal", "Voelkerschlachtdenkmal", "Voelkerschlachtdenkmal, Leipzig", 51.3141266, 12.4103392),
    WaterPoint("water-zwenkauer-markt", "Zwenkauer Markt", "Zwenkauer Markt, Zwenkau", 51.2175577, 12.3241064),
    WaterPoint("water-lene-voigt-park", "Lene-Voigt-Park", "Reichpietschstrasse, 04317 Leipzig", 51.3337806, 12.4027672),
    WaterPoint("water-markkleeberg-rathausstrasse", "Rathausstrasse / Ecke Suedstrasse", "Rathausstrasse, 04416 Markkleeberg", 51.279528, 12.37346),
    WaterPoint("water-alte-salzstrasse-gruenauer-allee", "Alte Salzstrasse & Gruenauer Allee", "Alte Salzstrasse & Gruenauer Allee, Leipzig", 51.3218404, 12.3023902, "Laut Karte zeitweise in Betrieb."),
    WaterPoint("water-cospudener-see", "Cospudener See", "Nordstrand, Lauer 7", 51.2804761, 12.3506751),
    WaterPoint("water-schoenefelder-allee", "Schönefelder Allee", "Schönefelder Allee, Höhe Heinkstraße, Leipzig", 51.3546915, 12.4058614, "Mariannenpark."),
    WaterPoint("water-park-moeckern", "Park Moeckern", "Park Moeckern, Leipzig", 51.3677311, 12.3457964),
    WaterPoint("water-gohliser-anger", "Gohliser Anger", "Gohliser Anger, Leipzig", 51.3572601, 12.3648349),
    WaterPoint("water-alte-salzstrasse-63", "Alte Salzstrasse 63", "Alte Salzstrasse 63, Leipzig", 51.3203351, 12.2993546),
    WaterPoint("water-naunhof", "Naunhof", "Ungibauerstrasse am Stadtgut, Naunhof", 51.2783422, 12.5888609),
    WaterPoint("water-neustaedter-markt", "Neustaedter Markt / Kreuzkirche", "Neustaedter Markt, Leipzig", 51.3481002, 12.4031765),
    WaterPoint("water-generationenpark-grosspoesna", "Generationenpark Grosspoesna", "Generationenpark Grosspoesna", 51.2679317, 12.501568),
    WaterPoint("water-borsdorf", "Borsdorf", "Borsdorf", 51.346191, 12.540378),
    WaterPoint("water-em-brunnen", "EM-Brunnen", "Leipzig Zentrum", 51.3435893782088, 12.3719447817533),
    WaterPoint("water-rathausplatz-schkeuditz", "Rathausplatz Schkeuditz", "Rathausplatz, Schkeuditz", 51.3963710000569, 12.2215628353347),
    WaterPoint("water-rabet-konradstrasse", "Rabet, Konradstrasse", "Rabet, Konradstrasse, Leipzig", 51.3447056621269, 12.4039637117069),
    WaterPoint("water-goetheplatz-boehlitz", "Goetheplatz, Böhlitz-Ehrenberg", "Goetheplatz, Böhlitz-Ehrenberg, Leipzig", 51.3554350837877, 12.2862403074404),
    WaterPoint("water-gorkistrasse", "Gorkistrasse", "Gorkistrasse, Leipzig", 51.3584122131928, 12.41762814395),
    WaterPoint("water-haus-auensee", "Haus Auensee", "Haus Auensee, Leipzig", 51.3688007735188, 12.3150875601685),
    WaterPoint("water-brunno-wilhelm-leuschner-platz", "Brunno on Tour", "Wilhelm-Leuschner-Platz, Leipzig", 51.3392707483798, 12.3811548715806, "Mobiler Trinkbrunnen, 4. Mai bis 14. Juni."),
    WaterPoint("water-brunno-riemannstrasse", "Brunno on Tour", "Riemannstrasse an der Peterskirche, Leipzig", 51.3309468, 12.3755304, "Mobiler Trinkbrunnen, 4. Mai bis 14. Juni."),
    WaterPoint("water-brunno-stuttgarter-allee", "Brunno on Tour", "Stuttgarter Allee am Pep Center, Leipzig", 51.3229122, 12.2886561, "Mobiler Trinkbrunnen, 4. Mai bis 14. Juni."),
    WaterPoint("water-brunno-stuenzer-strasse", "Brunno on Tour", "Stünzer Straße an der 74. Grundschule, Leipzig", 51.3365697, 12.4117395, "Mobiler Trinkbrunnen, 4. Mai bis 14. Juni."),
    WaterPoint("water-brunno-lindenthal", "Brunno on Tour", "Spielplatz zur Lindenhoehe, Leipzig-Lindenthal", 51.391282, 12.3349057, "Mobiler Trinkbrunnen, 4. Mai bis 14. Juni."),
)


TOILET_POINTS: tuple[ToiletPoint, ...] = (
    ToiletPoint("toilet-0001", "Lindenauer Markt", "Altlindenau", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.33689999956661, 12.3347000001057),
    ToiletPoint("toilet-0002", "Friedenspark (Philipp-Rosenthal-Straße)", "Zentrum-Südost", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.324699999594856, 12.39410000053511),
    ToiletPoint("toilet-0003", "Palmengarten (Jahnallee)", "Lindenau", "geschlossen", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.339000000025, 12.345800000098798),
    ToiletPoint("toilet-0004", "Johannapark (Friedrich-Ebert-Straße)", "Zentrum-West", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.33590000005577, 12.366400000703694),
    ToiletPoint("toilet-0005", "Goethestraße (Schwanenteich)", "Zentrum", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.342000000221, 12.381099999538476),
    ToiletPoint("toilet-0006", "Martin-Luther-Ring (Besuchereingang Neues Rathaus)", "Zentrum", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.33599999999644, 12.374100000338409),
    ToiletPoint("toilet-0007", "Wilhelm-Liebknecht-Platz", "Zentrum-Nord", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.34959999978016, 12.37699999971623),
    ToiletPoint("toilet-0008", "Clara-Zetkin-Park (Rennbahnweg)", "Zentrum-Süd", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.32659999963498, 12.36429999989396),
    ToiletPoint("toilet-0009", "Bayrischer Platz (Riemannstraße)", "Zentrum-Süd", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.330499999711485, 12.379799999957303),
    ToiletPoint("toilet-0010", "Arthur-Bretschneider-Park (Kleiststraße)", "Eutritzsch", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.36870000021054, 12.381099999443974),
    ToiletPoint("toilet-0011", "Am Elsterwehr", "Zentrum-West", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.335399999666016, 12.351199999731184),
    ToiletPoint("toilet-0012", "Konradstraße", "Volkmarsdorf", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.344599999984226, 12.409200000449404),
    ToiletPoint("toilet-0013", "P+R Neue Messe (Georg-Herwegh-Straße)", "Wiederitzsch", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.3946000003357, 12.384299999416488),
    ToiletPoint("toilet-0014", "P+R Lausen (Miltitzer Allee)", "Grünau-Nord", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.31649999969557, 12.269199999458452),
    ToiletPoint("toilet-0015", "P+R Völkerschlachtdenkmal (Straße des 18. Oktober)", "Probstheida", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.31410000004343, 12.408799999509808),
    ToiletPoint("toilet-0016", "P+R Schönauer Ring (Jenaer Straße)", "Schönau", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.323799999638496, 12.284599999869),
    ToiletPoint("toilet-0017", "P+R Bhf. Knauthain (Dieskaustraße)", "Knautkleeberg-Knauthain", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.27749999972135, 12.309400000517464),
    ToiletPoint("toilet-0018", "Wochenmarkt Leipzig Grünau (Stuttgarter Allee)", "Grünau-Mitte", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.31740000013661, 12.291100000432149),
    ToiletPoint("toilet-0019", "LVB-Gleisschleife Erholungspark Lößnig-Dölitz (Siegfriedstraße)", "Lößnig", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.296199999995814, 12.396499999865181),
    ToiletPoint("toilet-0020", "Augustusplatz (Opernseite)", "Zentrum", "ganztägig", "Barrierefrei, All Gender, Wickeltisch", "50 Cent (Barzahlung oder mit Karte)", "0800 44 6666 02", 51.33950000033617, 12.381800000622702),
    ToiletPoint("toilet-0021", "Lene-Voigt-Park", "Reudnitz-Thonberg", "ganztägig", "Barrierearm, All Gender", "kostenfrei", "0800 44 6666 02", 51.33386800038458, 12.403085999808539),
)


SYMBOLS: tuple[SymbolDefinition, ...] = (
    SymbolDefinition(
        id="sleep",
        icon="bed",
        labels=_l("Schlafen", "Sleep", "Nocleg", "Somn", "Ночлег"),
        query="uebernachtung notunterkunft schlafen wohnungslosigkeit",
        priority=10,
        categories=("housing",),
        service_types=("overnight_shelter", "youth_emergency_housing", "child_emergency_housing", "protected_housing"),
        page_ids=(
            "wohnungsnotfallhilfe-pdf-uebernachtungshaus-maenner",
            "wohnungsnotfallhilfe-pdf-uebernachtungshaus-frauen-katalog",
            "wohnungsnotfallhilfe-pdf-alternative-iii",
            "aww-frauen-uebernachtungshaus",
            "wohnungsnotfallhilfe-pdf-jugendnotdienst",
            "wohnungsnotfallhilfe-pdf-kindernotdienst",
        ),
        intro=_l("Hier sind Schlaf-Orte.", "Here are sleeping places.", "Tu są miejsca do spania.", "Aici sunt locuri pentru dormit.", "Вот места для ночлега."),
        substeps=(
            SymbolSubstepDefinition("men", "person", _l("Männer", "Men", "Mężczyźni", "Bărbați", "Мужчины"), "maenner", gender_access=("men",)),
            SymbolSubstepDefinition("women", "person", _l("Frauen", "Women", "Kobiety", "Femei", "Женщины"), "frauen", gender_access=("women",)),
            SymbolSubstepDefinition(
                "young",
                "child",
                _l("Junge Person / Kind", "Young person / child", "Młoda osoba / dziecko", "Tânăr / copil", "Молодой человек / ребенок"),
                "jugendnotdienst kindernotdienst",
                service_types=("youth_emergency_housing", "child_emergency_housing"),
            ),
            SymbolSubstepDefinition("unsure", "question", _l("Egal / nicht sicher", "Any / not sure", "Wszystko jedno / nie wiem", "Orice / nu sunt sigur", "Любое / не знаю")),
        ),
    ),
    SymbolDefinition(
        id="food",
        icon="food",
        labels=_l("Essen", "Food", "Jedzenie", "Mâncare", "Еда"),
        query="essen lebensmittel tafel warme mahlzeit heute",
        priority=20,
        categories=("food", "social", "addiction"),
        service_types=("food_distribution", "day_center", "streetwork_food_outreach"),
        page_ids=("tafel-leipzig-zentrale-lindenau-west", "tafel-leipzig-ost-volkmarsdorf", "tafel-leipzig-ost-paunsdorf", "wohnungsnotfallhilfe-pdf-insel", "leipzig-schadensminimierung-schwanenteich"),
        intro=_l("Essen heute, wenn Zeiten vorhanden sind.", "Food today, when times are available.", "Jedzenie dziś, jeśli są godziny.", "Mâncare azi, dacă există program.", "Еда сегодня, если есть часы."),
    ),
    SymbolDefinition(
        id="water",
        icon="water",
        labels=_l("Trinken", "Water", "Woda", "Apă", "Вода"),
        query="trinkwasser brunnen wasser trinken",
        priority=30,
        result_mode="cards-map",
        categories=("water",),
        page_ids=("trinkwasserbrunnen",),
        intro=_l("Es gibt öffentliche Trinkwasserbrunnen.", "There are public drinking-water fountains.", "Są publiczne fontanny z wodą pitną.", "Există fântâni publice cu apă potabilă.", "Есть общественные питьевые фонтаны."),
        no_map_reason=_l("Einzelne Brunnen sind hier noch nicht als Kartenpunkte gespeichert.", "Individual fountains are not stored as map points yet.", "Pojedyncze punkty wody nie są jeszcze zapisane na mapie.", "Fântânile individuale nu sunt încă salvate ca puncte pe hartă.", "Отдельные фонтаны еще не сохранены как точки на карте."),
    ),
    SymbolDefinition(
        id="hygiene",
        icon="wash",
        labels=_l("Toilette / Waschen", "Toilet / Wash", "Toaleta / Mycie", "Toaletă / Spălat", "Туалет / мыться"),
        query="toilette dusche waschen hygiene koerperpflege",
        priority=40,
        categories=("hygiene", "housing", "food"),
        service_types=("hygiene", "day_center"),
        substeps=(
            SymbolSubstepDefinition("toilet", "toilet", _l("Toilette", "Toilet", "Toaleta", "Toaletă", "Туалет"), "oeffentliche toiletten", service_types=("hygiene",)),
            SymbolSubstepDefinition("shower", "shower", _l("Dusche / Waschen", "Shower / wash", "Prysznic / mycie", "Duș / spălat", "Душ / мыться"), "duschen waschen koerperpflege oase insel", service_types=("day_center",)),
        ),
        intro=_l("Hier finden Sie Hygiene-Hilfe.", "Here is hygiene help.", "Tu znajdziesz pomoc higieniczną.", "Aici găsești ajutor pentru igienă.", "Здесь помощь с гигиеной."),
        no_map_reason=_l("Öffentliche Toiletten sind noch nicht einzeln als Kartenpunkte gespeichert.", "Public toilets are not stored as individual map points yet.", "Toalety publiczne nie są jeszcze zapisane jako osobne punkty mapy.", "Toaletele publice nu sunt încă salvate ca puncte separate pe hartă.", "Общественные туалеты еще не сохранены отдельными точками карты."),
    ),
    SymbolDefinition(
        id="medical",
        icon="medical",
        labels=_l("Medizin", "Medical", "Medycyna", "Medical", "Медицина"),
        query="medizin sprechstunde cabl arzt wohnungslose gesundheit",
        priority=50,
        categories=("medical",),
        service_types=("medical_consultation", "medical"),
        page_ids=("cabl-uvo", "gesundheitsamt", "drk-kurse"),
        intro=_l("Das ist nur Orientierung zu Hilfe-Angeboten.", "This is only orientation to help offers.", "To tylko orientacja w ofertach pomocy.", "Aceasta este doar orientare către oferte de ajutor.", "Это только ориентир по предложениям помощи."),
        disclaimer=_l("Keine medizinische Diagnose.", "No medical diagnosis.", "To nie jest diagnoza medyczna.", "Nu este diagnostic medical.", "Это не медицинский диагноз."),
    ),
    SymbolDefinition(
        id="emergency",
        icon="alert",
        labels=_l("Notfall", "Emergency", "Alarm", "Urgență", "Срочно"),
        query="notfall 112 110 akute gefahr",
        priority=60,
        result_mode="static",
        categories=("emergency", "crisis"),
        page_ids=("notfallkontakte", "telefonseelsorge-leipzig"),
        static_text=_l(
            "Akute Gefahr: 112 anrufen. Bei Gewalt oder Gefahr durch andere Menschen: 110 anrufen. Am Bahnhof: sofort zu Mitarbeitenden, Bahnhofsmission oder Arzt gehen. Nicht allein bleiben.",
            "Immediate danger: call 112. Violence or danger from another person: call 110. At the station: go to staff, Bahnhofsmission or a doctor now. Do not stay alone.",
            "Bezpośrednie zagrożenie: zadzwoń pod 112. Przemoc lub zagrożenie od innej osoby: 110. Na dworcu idź od razu do pracowników, Bahnhofsmission albo lekarza. Nie zostawaj sam.",
            "Pericol imediat: sună la 112. Violență sau pericol de la altă persoană: sună la 110. La gară mergi imediat la personal, Bahnhofsmission sau medic. Nu rămâne singur.",
            "Немедленная опасность: звоните 112. Насилие или опасность от другого человека: 110. На вокзале сразу идите к сотрудникам, в Bahnhofsmission или к врачу. Не оставайтесь одни.",
        ),
        no_map_reason=_l("Notfall-Hilfe braucht keinen Kartenweg.", "Emergency help does not need a map route.", "Pomoc alarmowa nie wymaga mapy.", "Ajutorul de urgență nu are nevoie de hartă.", "Для срочной помощи карта не нужна."),
    ),
    SymbolDefinition(
        id="clothing",
        icon="clothes",
        labels=_l("Kleidung", "Clothes", "Ubrania", "Haine", "Одежда"),
        query="kleidung kleiderkammer kleiderspenden warme kleidung",
        priority=70,
        group="secondary",
        categories=("clothing", "social"),
        service_types=("clothing_support",),
        page_ids=("diakonie-kleiderkammern", "bahnhofsmission-bund", "bahnhofsmission-caritas"),
    ),
    SymbolDefinition(
        id="counseling",
        icon="help",
        labels=_l("Beratung", "Advice", "Porady", "Consiliere", "Консультация"),
        query="beratung soziale hilfe wohnungslosigkeit notlagen",
        priority=80,
        group="secondary",
        categories=("social", "housing"),
        service_types=("counseling", "station_support"),
        page_ids=("wohnungsnotfallhilfe-pdf-bahnhofsmission-leipzig-katalog", "caritas-allgemeine-soziale-beratung", "drk-soziale-beratung"),
    ),
    SymbolDefinition(
        id="addiction",
        icon="addiction",
        labels=_l("Sucht / Drogenhilfe", "Drugs / addiction", "Uzależnienie", "Dependență", "Зависимость"),
        query="sucht drogenhilfe schadensminimierung konsum streetwork",
        priority=90,
        group="secondary",
        categories=("addiction",),
        page_ids=("suchtzentrum", "suchtzentrum-safe-streetwork", "suchtzentrum-team-konsum", "diakonie-suchtberatung-blaues-kreuz"),
    ),
    SymbolDefinition(
        id="documents",
        icon="documents",
        labels=_l("Dokumente / Ämter", "Documents", "Dokumenty", "Documente", "Документы"),
        query="dokumente amt schulden mietrecht beratung",
        priority=100,
        group="secondary",
        categories=("documents", "social", "housing"),
        service_types=("counseling", "financial_housing_support"),
        page_ids=("caritas-schuldnerberatung", "wohnungsnotfallhilfe-pdf-wirtschaftliche-wohnhilfen", "wohnungsnotfallhilfe-pdf-sozialdienst"),
    ),
    SymbolDefinition(
        id="station",
        icon="station",
        labels=_l("Bahnhofsmission / Streetwork", "Station help", "Pomoc na dworcu", "Ajutor la gară", "Помощь на вокзале"),
        query="bahnhofsmission streetwork hauptbahnhof soziale hilfe",
        priority=110,
        group="secondary",
        categories=("social", "addiction"),
        service_types=("station_support", "streetwork", "streetwork_food_outreach"),
        page_ids=("wohnungsnotfallhilfe-pdf-bahnhofsmission-leipzig-katalog", "diakonie-streetwork", "suchtzentrum-safe-streetwork"),
    ),
    SymbolDefinition(
        id="unsure",
        icon="question",
        labels=_l("Nicht sicher", "Not sure", "Nie wiem", "Nu știu", "Не знаю"),
        query="hilfe beratung essen schlafen medizin kleidung hygiene",
        priority=120,
        group="secondary",
        categories=("social", "housing", "food", "medical", "clothing"),
        service_types=("station_support", "counseling", "day_center", "food_distribution", "medical_consultation", "clothing_support"),
        page_ids=("wohnungsnotfallhilfe-pdf-bahnhofsmission-leipzig-katalog", "leipziger-oase", "caritas-allgemeine-soziale-beratung"),
    ),
)
