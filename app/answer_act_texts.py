"""Geschlossene Ausgabeakte und Labels (DE/EN/PL/RO/RU).

Maschinell formuliert, noch kein unabhängiges Sprachreview. Diese Texte
übersetzen nur feste Akte und kuratierte Enumwerte, keine freien Behauptungen.
"""

from .models import Language

_LANGUAGES = (Language.DE, Language.EN, Language.PL, Language.RO, Language.RU)

COPY = {
    "compact_unknown_fee": ("Kosten unbestätigt. Frage bei {name} nach.", "Cost unconfirmed. Ask {name}.", "Koszt niepotwierdzony. Zapytaj w {name}.", "Cost neconfirmat. Întreabă la {name}.", "Стоимость не подтверждена. Уточни в {name}."),
    "compact_unknown_hours": ("Zeiten unbestätigt. Frage bei {name} nach.", "Hours unconfirmed. Ask {name}.", "Godziny niepotwierdzone. Zapytaj w {name}.", "Ore neconfirmate. Întreabă la {name}.", "Время не подтверждено. Уточни в {name}."),
    "compact_unknown_access": ("Dein Zugang ist unbestätigt. Frage bei {name} nach.", "Your access is unconfirmed. Ask {name}.", "Twój dostęp nie jest potwierdzony. Zapytaj w {name}.", "Accesul tău nu este confirmat. Întreabă la {name}.", "Твой доступ не подтверждён. Уточни в {name}."),
    "compact_unknown_availability": ("Verfügbarkeit unbestätigt. Frage bei {name} nach.", "Availability unconfirmed. Ask {name}.", "Dostępność niepotwierdzona. Zapytaj w {name}.", "Disponibilitate neconfirmată. Întreabă la {name}.", "Доступность не подтверждена. Уточни в {name}."),
    "compact_unknown_detail": ("Keine Zusage für dein Anliegen. Frage bei {name} nach.", "Your request is not confirmed. Ask {name}.", "Twoja prośba nie jest potwierdzona. Zapytaj w {name}.", "Cererea ta nu este confirmată. Întreabă la {name}.", "Твой запрос не подтверждён. Уточни в {name}."),
    "contact": ("Frage bei {name} nach.", "Ask {name} for details.", "Zapytaj w {name} o szczegóły.", "Cere detalii la {name}.", "Уточни подробности в {name}."),
    "referral": ("Wende dich an {name}.", "Contact {name}.", "Skontaktuj się z {name}.", "Contactează {name}.", "Свяжись с {name}."),
    "unknown_fee": ("Die Kosten für dein konkretes Anliegen kann ich nicht verbindlich bestätigen. Frage bei {name} nach.", "I cannot confirm the cost for your specific request. Ask {name} for details.", "Nie mogę potwierdzić kosztu Twojej konkretnej prośby. Zapytaj w {name} o szczegóły.", "Nu pot confirma costul pentru cererea ta concretă. Cere detalii la {name}.", "Я не могу подтвердить стоимость для твоего конкретного запроса. Уточни подробности в {name}."),
    "unknown_hours": ("Die Zeiten für dein konkretes Anliegen kann ich nicht verbindlich bestätigen. Frage bei {name} nach.", "I cannot confirm the hours for your specific request. Ask {name} for details.", "Nie mogę potwierdzić godzin dla Twojej konkretnej prośby. Zapytaj w {name} o szczegóły.", "Nu pot confirma orele pentru cererea ta concretă. Cere detalii la {name}.", "Я не могу подтвердить время для твоего конкретного запроса. Уточни подробности в {name}."),
    "unknown_access": ("Ob die Zugangsbedingungen für dich erfüllt sind, kann ich nicht bestätigen. Frage bei {name} nach.", "I cannot confirm that you meet the access conditions. Ask {name} for details.", "Nie mogę potwierdzić, że spełniasz warunki dostępu. Zapytaj w {name} o szczegóły.", "Nu pot confirma că îndeplinești condițiile de acces. Cere detalii la {name}.", "Я не могу подтвердить, что ты соответствуешь условиям доступа. Уточни подробности в {name}."),
    "unknown_availability": ("Ob {name} jetzt verfügbar ist oder dich aufnehmen kann, ist nicht bestätigt.", "Current availability or admission at {name} is not confirmed.", "Bieżąca dostępność lub przyjęcie w {name} nie są potwierdzone.", "Disponibilitatea actuală sau primirea la {name} nu sunt confirmate.", "Текущая доступность или возможность приёма в {name} не подтверждены."),
    "unknown_detail": ("Für dein konkretes Anliegen kann ich bei {name} keine Zusage machen. Frage dort nach.", "I cannot confirm that {name} can meet your specific request. Ask there for details.", "Nie mogę potwierdzić, że {name} spełni Twoją konkretną prośbę. Zapytaj tam o szczegóły.", "Nu pot confirma că {name} îți poate îndeplini cererea concretă. Cere detalii acolo.", "Я не могу подтвердить, что {name} может выполнить твой конкретный запрос. Уточни подробности там."),
    "description": ("Beschreibung", "Description", "Opis", "Descriere", "Описание"),
    "service": ("Angebot", "Service", "Usługa", "Serviciu", "Услуга"),
    "address": ("Adresse", "Address", "Adres", "Adresă", "Адрес"),
    "phone": ("Telefon", "Phone", "Telefon", "Telefon", "Телефон"),
    "email": ("E-Mail", "Email", "E-mail", "E-mail", "Электронная почта"),
    "url": ("Website", "Website", "Strona", "Site", "Сайт"),
    "opening_time": ("Öffnungszeiten", "Opening hours", "Godziny otwarcia", "Program", "Часы работы"),
    "stand_time": ("Standzeiten", "Stop times", "Godziny postoju", "Ore de staționare", "Время стоянки"),
    "note": ("Hinweis", "Note", "Uwaga", "Notă", "Примечание"),
    "district": ("Stadtteil", "District", "Dzielnica", "Cartier", "Район"),
    "operator": ("Betreiber", "Operator", "Operator", "Operator", "Оператор"),
    "facility": ("Ausstattung", "Facilities", "Wyposażenie", "Dotări", "Оснащение"),
    "fee": ("Kosten", "Cost", "Koszt", "Cost", "Стоимость"),
    "fee_status": ("Kostenstatus", "Fee status", "Status opłat", "Statutul taxei", "Статус оплаты"),
    "air_distance": ("Luftlinie ab Hauptbahnhof", "Straight-line distance from main station", "Odległość w linii prostej od dworca głównego", "Distanța în linie dreaptă de la gara principală", "Расстояние по прямой от главного вокзала"),
    "location_description": ("Standort", "Location", "Lokalizacja", "Amplasare", "Местоположение"),
    "potable_water_status": ("Trinkwasserstatus", "Drinking-water status", "Status wody pitnej", "Statutul apei potabile", "Статус питьевой воды"),
    "seasonal_status": ("Saison", "Season", "Sezon", "Sezon", "Сезон"),
    "operation_status": ("Gespeicherter Betriebsstatus", "Recorded operation status", "Zapisany status działania", "Starea de funcționare înregistrată", "Зафиксированный статус работы"),
    "service_condition": ("Leistungsbedingung", "Service condition", "Warunek usługi", "Condiție a serviciului", "Условие услуги"),
    "source": ("Quelle", "Source", "Źródło", "Sursă", "Источник"),
    "target_group": ("Zielgruppe", "Target group", "Grupa docelowa", "Grup țintă", "Целевая группа"),
    "minimum_age": ("Mindestalter", "Minimum age", "Wiek minimalny", "Vârsta minimă", "Минимальный возраст"),
    "maximum_age": ("Höchstalter", "Maximum age", "Wiek maksymalny", "Vârsta maximă", "Максимальный возраст"),
    "eligible_gender": ("Zugangsgruppe", "Access group", "Grupa dostępu", "Grup de acces", "Группа доступа"),
    "access": ("Zugangsbedingung", "Access condition", "Warunek dostępu", "Condiție de acces", "Условие доступа"),
}

ENUM_COPY = {
    "adults": ("Erwachsene", "adults", "dorośli", "adulți", "взрослые"),
    "under_27": ("unter 27 Jahre", "under 27", "poniżej 27 lat", "sub 27 de ani", "младше 27 лет"),
    "men": ("Männer", "men", "mężczyźni", "bărbați", "мужчины"),
    "women": ("Frauen", "women", "kobiety", "femei", "женщины"),
    "people_who_use_drugs": ("Menschen mit Drogenkonsum", "people who use drugs", "osoby używające narkotyków", "persoane care consumă droguri", "люди, употребляющие наркотики"),
    "people_experiencing_homelessness": ("wohnungslose Menschen", "people experiencing homelessness", "osoby w kryzysie bezdomności", "persoane fără adăpost", "люди без жилья"),
    "people_without_regular_healthcare": ("Menschen ohne reguläre Gesundheitsversorgung", "people without regular healthcare", "osoby bez regularnej opieki zdrowotnej", "persoane fără îngrijire medicală regulată", "люди без регулярной медицинской помощи"),
    "minors": ("Minderjährige", "minors", "osoby niepełnoletnie", "minori", "несовершеннолетние"),
    "female": ("weiblich", "female", "kobiety", "femei", "женщины"),
    "male": ("männlich", "male", "mężczyźni", "bărbați", "мужчины"),
    "non_binary": ("nichtbinär", "non-binary", "osoby niebinarne", "persoane non-binare", "небинарные люди"),
    "diverse": ("divers", "diverse", "osoby różnorodnej płci", "persoane cu gen divers", "люди различной гендерной идентичности"),
    "free": ("kostenfrei", "free", "bezpłatnie", "gratuit", "бесплатно"),
    "paid": ("kostenpflichtig", "paid", "odpłatnie", "contra cost", "платно"),
    "unknown": ("unbekannt", "unknown", "nieznane", "necunoscut", "неизвестно"),
    "helene_after_21_or_no_social_benefit_entitlement": ("nach 21:00 Uhr oder ohne Sozialleistungsanspruch", "after 21:00 or without entitlement to social benefits", "po 21:00 lub bez prawa do świadczeń socjalnych", "după 21:00 sau fără drept la prestații sociale", "после 21:00 или при отсутствии права на социальные выплаты"),
}


def act_text(key: str, language: Language, **values: str) -> str:
    """Nur geschlossene Schlüssel und vertrauenswürdige Evidence-Werte einsetzen."""
    return COPY[key][_LANGUAGES.index(language)].format(**values)


def enum_text(value: str, language: Language) -> str:
    return ENUM_COPY[value][_LANGUAGES.index(language)]


# Exact values of the infrastructure builder; closed localization, no inference.
SOURCE_COPY = {
    ("service", "Öffentliche Toilette"): ("Öffentliche Toilette", "Public toilet", "Toaleta publiczna", "Toaletă publică", "Общественный туалет"),
    ("service", "Kostenloser Trinkwasserbrunnen"): ("Kostenloser Trinkwasserbrunnen", "Free drinking-water fountain", "Bezpłatna fontanna z wodą pitną", "Cișmea gratuită cu apă potabilă", "Бесплатный питьевой фонтан"),
    ("seasonal_status", "in Betrieb von April bis Oktober"): ("Saison April bis Oktober", "Season April to October", "Sezon od kwietnia do października", "Sezon din aprilie până în octombrie", "Сезон с апреля по октябрь"),
    ("operation_status", "aktueller Betriebsstatus unbekannt"): ("aktueller Betriebsstatus unbekannt", "current operation status unknown", "bieżący status działania nieznany", "starea actuală de funcționare necunoscută", "текущий статус работы неизвестен"),
    ("potable_water_status", "verified"): ("laut Quelle geprüft", "verified in the source", "zweryfikowane w źródle", "verificat în sursă", "проверено в источнике"),
}


def source_text(kind: str, value: str, language: Language) -> str:
    key = (kind, value)
    return SOURCE_COPY[key][_LANGUAGES.index(language)] if key in SOURCE_COPY else value
