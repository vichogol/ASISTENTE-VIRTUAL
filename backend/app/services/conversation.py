
"""Recognize conversational turns and map short queries to reviewed FAQ entries."""

import re
from dataclasses import dataclass

from app.services.knowledge import FAQ, normalize
from app.services.retrieval import INTENTS, Match, tokens

GREETING = re.compile(
    r"^[¡¿\s]*(?:hola(?:\s+(?:bot|asistente))?|buenas(?:\s+(?:tardes|noches)|(?=\s*[!¡,.;:-]|$))|"
    r"buenos\s+d[ií]as|buen\s+d[ií]a)\b[\s!¡,.:;-]*",
    re.IGNORECASE,
)
ASSISTANT = "Peñalolín"
IDENTITY = re.compile(
    r"^(?:quien eres|quien me (?:habla|responde)|como te llamas|cual es tu nombre|"
    r"eres (?:un bot|un chatbot|una persona)|que eres)(?: por favor)?$"
)
SMALL_TALK = {"", "que tal", "como estas", "como va", "como te va", "que tal estas"}
THANKS = {"gracias", "muchas gracias", "mil gracias", "gracias por tu ayuda", "gracias por la informacion"}
HELP = re.compile(
    r"^(?:que (?:puedes hacer|me puedes (?:decir|contar)|haces|tramites(?: hay| puedo (?:hacer|realizar))?|"
    r"servicios (?:hay|ofrecen)|(?:se puede|puedo) hacer(?: aqui| en la municipalidad)?)|"
    r"(?:me puedes|puedes) ayudar(?:me)?|me ayudas|(?:hola )?(?:necesito|quiero) (?:ayuda|informacion|orientacion)(?: por favor)?|"
    r"(?:quiero|necesito) hacer un tramite|ayuda(?: por favor)?|tramites(?: municipales)?|servicios(?: municipales)?)$"
)


@dataclass(frozen=True)
class Option:
    id: int
    label: str

    @property
    def key(self) -> str:
        return f"Revisdas:{self.id}"


@dataclass(frozen=True)
class Keyword:
    option: Option
    required: frozenset[str]
    extra: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Topic:
    caption: str
    focus: frozenset[str]
    options: tuple[Option, ...]
    shortcuts: tuple[Keyword, ...] = ()

    def match(self, words: frozenset[str]) -> Option | None:
        for rule in self.shortcuts:
            if rule.required <= words <= (self.focus | rule.required | rule.extra):
                return rule.option
        return None


def rule(option: Option, required: str, extra: str = "") -> Keyword:
    return Keyword(option, frozenset(required.split()), frozenset(extra.split()))


LICENSE_APPOINTMENT = Option(340, "Agendar una hora")
LICENSE_SCHEDULE = Option(287, "Ver cuándo abre la agenda")
LICENSE_OVERVIEW = Option(255, "Sacar o renovar mi licencia")
PAY_PERMIT = Option(791, "Pagar en línea")
PERMIT_COST = Option(788, "Consultar el valor")
PERMIT_RENEWAL = Option(782, "Ver requisitos de renovación")
SOCIAL_APPLY = Option(251, "Solicitar el Registro Social de Hogares")
SOCIAL_INFO = Option(448, "Saber para qué sirve")
POOL_HOURS = Option(4, "Ver horarios de la piscina")
POOL_ADDRESS = Option(3, "Ver dónde queda la piscina")
POOL_CLASSES = Option(1, "Consultar los talleres")
CULTURE_CLASSES = Option(519, "Consultar talleres en Chimkowe")
CULTURE_HOURS = Option(534, "Ver horarios de Chimkowe")
RECYCLING_CONTACT = Option(126, "Contactar al equipo de reciclaje")

LICENSE = Topic(
    "la licencia de conducir", frozenset({"conducir", "licencia"}),
    (LICENSE_APPOINTMENT, LICENSE_SCHEDULE, LICENSE_OVERVIEW),
    (
        rule(LICENSE_SCHEDULE, "horario agenda", "hora renovacion sacar"),
        rule(LICENSE_APPOINTMENT, "hora", "agenda renovacion sacar"),
        rule(LICENSE_APPOINTMENT, "agenda", "hora renovacion sacar"),
        rule(LICENSE_OVERVIEW, "renovacion"),
        rule(LICENSE_OVERVIEW, "sacar", "primer"),
    ),
)
PERMIT = Topic(
    "el permiso de circulación", frozenset({"permiso", "circulacion"}),
    (PAY_PERMIT, PERMIT_COST, PERMIT_RENEWAL),
    (
        rule(PAY_PERMIT, "circulacion virtual", "pago"),
        rule(PERMIT_COST, "circulacion costo"),
        rule(PERMIT_RENEWAL, "circulacion requisito renovacion"),
    ),
)
SOCIAL = Topic(
    "el Registro Social de Hogares", frozenset({"registro", "social", "hogares"}),
    (SOCIAL_APPLY, SOCIAL_INFO),
    (rule(SOCIAL_APPLY, "sacar", "requisito"), rule(SOCIAL_APPLY, "requisito", "sacar")),
)
POOL = Topic(
    "la Piscina Municipal", frozenset({"piscina", "temperada"}),
    (POOL_HOURS, POOL_ADDRESS, POOL_CLASSES),
    (rule(POOL_HOURS, "horario"), rule(POOL_CLASSES, "taller", "curso"), rule(POOL_CLASSES, "curso")),
)
CULTURE = Topic(
    "el Centro Cultural Chimkowe", frozenset({"chimkowe", "centro", "cultural"}),
    (CULTURE_CLASSES, CULTURE_HOURS),
    (rule(CULTURE_CLASSES, "taller"), rule(CULTURE_HOURS, "horario")),
)
RECYCLING = Topic(
    "reciclaje", frozenset({"reciclaje"}),
    (RECYCLING_CONTACT,),
    (rule(RECYCLING_CONTACT, "contacto", "canales comunicacion"),),
)
HOME = (LICENSE_OVERVIEW, PAY_PERMIT, SOCIAL_APPLY)
CHOICES = {"pago", "ubicacion", "virtual"}


def split_greeting(message: str) -> tuple[str, str]:
    greeting = ""
    while match := GREETING.match(message):
        greeting = "¡Hola! "
        message = message[match.end():].strip()
    return message, greeting


def small_talk(question: str, greeting: str) -> tuple[str, tuple[Option, ...]] | None:
    key = normalize(question)
    if key in THANKS:
        return "¡De nada! Si te surge otra duda sobre Peñalolén, aquí estoy.", ()
    if key in SMALL_TALK:
        return f"{greeting or '¡Hola! '}Soy {ASSISTANT}. ¿En qué te puedo ayudar hoy?", HOME
    if IDENTITY.fullmatch(key):
        return (
            f"{greeting or '¡Hola! '}Soy {ASSISTANT}, el asistente virtual municipal de Peñalolén. "
            "Puedo ayudarte a encontrar trámites, conocer sus requisitos o ubicar un recinto. ¿Qué necesitas?",
            HOME,
        )
    if HELP.fullmatch(key) or not tokens(question):
        return (
            f"{greeting}Puedo orientarte sobre trámites y servicios de Peñalolén. "
            "¿Qué necesitas hacer? Puedes elegir un tema o escribirlo con tus palabras.",
            HOME,
        )
    words = tokens(question)
    if words == {"horario"}:
        return f"{greeting}¿De qué recinto o servicio quieres saber el horario?", (POOL_HOURS, CULTURE_HOURS)
    if words == {"ubicacion"}:
        return f"{greeting}¿Qué recinto o servicio estás buscando?", (POOL_ADDRESS,)
    if words == {"virtual"}:
        return f"{greeting}¿Qué trámite necesitas hacer en línea?", (PAY_PERMIT, LICENSE_APPOINTMENT)
    if words and words <= INTENTS | {"hora", "virtual"}:
        return f"{greeting}¿Sobre qué trámite o servicio quieres consultar?", HOME
    return None


def topic_for(words: frozenset[str]) -> Topic | None:
    candidates: list[Topic] = []
    if "licencia" in words and not (words & {"medica", "medico", "laboral", "comercial", "software"}):
        candidates.append(LICENSE)
    if "circulacion" in words or ("permiso" in words and words <= PERMIT.focus | CHOICES):
        candidates.append(PERMIT)
    if {"registro", "social"} <= words:
        candidates.append(SOCIAL)
    if "piscina" in words:
        candidates.append(POOL)
    if "chimkowe" in words:
        candidates.append(CULTURE)
    if "reciclaje" in words:
        candidates.append(RECYCLING)
    return candidates[0] if len(candidates) == 1 else None


def clarify(topic: Topic, words: frozenset[str]) -> str | None:
    if topic is PERMIT and "circulacion" not in words:
        return "¿Te refieres al permiso de circulación? Si buscas otro tipo de permiso, dime cuál."
    if topic is RECYCLING and words <= {"reciclaje", "ubicacion"}:
        return "¿Qué material quieres reciclar? Con ese dato puedo buscar un lugar o cómo entregarlo."
    if words <= topic.focus or (topic is PERMIT and words <= topic.focus | {"pago", "ubicacion"}):
        return f"Te puedo orientar sobre {topic.caption}. ¿Qué necesitas saber?"
    return None


def suggestions(options: tuple[Option, ...], records: dict[str, FAQ]) -> list[dict[str, str]]:
    return [
        {"label": option.label, "question": faq.question}
        for option in options
        if (faq := records.get(option.key)) and faq.reviewed
    ]


def nearby_questions(question: str, words: frozenset[str], ranked: list[Match]) -> list[dict[str, str]]:
    if not words or len(words) > 3 or words & INTENTS:
        return []
    options: dict[str, dict[str, str]] = {}
    current = normalize(question)
    for item in ranked:
        faq = item.faq
        key = normalize(faq.question)
        title = tokens(faq.question)
        if faq.reviewed and key != current and 0 < len(faq.question) <= 140 and words < title:
            options.setdefault(key, {"label": faq.question, "question": faq.question})
        if len(options) == 3:
            break
    return list(options.values())
