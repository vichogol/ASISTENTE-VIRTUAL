
"""Retrieve an FAQ only when the question and supporting evidence agree."""

import logging
import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.config import settings
from app.services.knowledge import FAQ, normalize

logger = logging.getLogger(__name__)

STOP = set("""
a al algo ante asi como con cual cuales cuando de del donde el ella ellas en es esa ese esto
ha hay la las le les lo los me mi mis o para por porque puedo puede que se si su sus te tu un una
uno y yo ayuda hola favor quiero quisiera saber necesito consultar consulta penalolen chile comuna
tramite tramites tramitar hago hacer realiza realizar puede debo tenga tengo este esta municipal municipalidad encontrar atencion puedo servicio
""".split())

SYNONYMS = {
    "papeles": "requisito", "documento": "requisito", "documentos": "requisito", "requisitos": "requisito",
    "pagar": "pago", "cancelo": "pago", "pagos": "pago", "pague": "pago",
    "vale": "costo", "cuesta": "costo", "precio": "costo", "valor": "costo", "costos": "costo",
    "renovar": "renovacion", "renuevo": "renovacion", "renovaciones": "renovacion",
    "agendar": "agenda", "agendo": "agenda", "agendamiento": "agenda", "reservar": "agenda",
    "reserva": "agenda", "cita": "agenda", "horas": "hora", "turno": "hora",
    "horarios": "horario", "abre": "horario", "abren": "horario", "apertura": "horario", "habilita": "horario",
    "licencias": "licencia", "permiso": "permiso", "permisos": "permiso",
    "talleres": "taller", "cursos": "curso", "mascotas": "mascota", "multas": "multa",
    "becas": "beca", "subsidios": "subsidio", "bicicletas": "bicicleta", "arboles": "arbol", "reciclar": "reciclaje",
    "esterilizar": "esterilizacion", "castrar": "esterilizacion",
    "ubicado": "ubicacion", "ubicada": "ubicacion",
    "queda": "ubicacion", "quedan": "ubicacion", "llegar": "ubicacion",
    "telefono": "contacto", "email": "contacto", "correo": "contacto",
    "extravio": "duplicado", "perdi": "duplicado", "obtener": "sacar", "solicitar": "sacar",
    "primera": "primer", "saco": "sacar", "circulasion": "circulacion",
    "inscribo": "inscripcion", "inscribirme": "inscripcion", "inscribirse": "inscripcion",
}
INTENTS = {
    "requisito", "pago", "costo", "renovacion", "agenda", "horario", "ubicacion", "contacto",
    "duplicado", "vencida", "primer", "presencial", "examen", "tarjeta", "cuota", "traslado", "inscripcion",
}
SENSITIVE_CASE = re.compile(
    r"\b(?:estado de (?:mi|la) (?:solicitud|postulacion|causa|expediente)|"
    r"mi (?:folio|expediente|rut|run)|(?:folio|expediente|causa|patente) (?:nro|numero|\d+)|"
    r"(?:confirmar|confirmame|averigua|revisar) (?:mi|el estado de mi)|"
    r"(?:por que|cuando) (?:me (?:rechazaron|responden|pagaran|depositan)|"
    r"(?:rechazaron|responden|pagan) mi))\b"
)
URL_WORDS = re.compile(r"\b(?:en linea|por internet|online|on line)\b")


def tokens(value: str) -> frozenset[str]:
    text = URL_WORDS.sub(" virtual ", normalize(value))
    text = re.sub(r"\b(?:rsh|registro social)\b(?! de hogares)", "registro social de hogares", text)
    text = re.sub(r"\bpermiso (?:del? )?(?:auto|vehiculo|automovil)\b", "permiso circulacion", text)
    text = re.sub(r"\b(?:carnet|carne|licencia) (?:para|de) (?:manejar|conducir)\b", "licencia conducir", text)
    text = re.sub(r"\bpiscina (?:temperada municipal|temperada|municipal)\b", "piscina temperada", text)
    text = re.sub(r"\b(?:cual es la direccion|donde esta|como llego)\b", "ubicacion", text)
    text = re.sub(r"\b(?:que debo llevar|que tengo que llevar|que necesito para)\b", "requisito", text)
    text = re.sub(r"\b(?:cuando abre[n]? (?:la agenda|las horas)|cuando se habilita la agenda)\b",
                  "horario agenda hora", text)
    return frozenset(SYNONYMS.get(word, word) for word in text.split() if word not in STOP)


def one_edit(first: str, second: str) -> bool:
    if len(first) == len(second):
        positions = [i for i, (left, right) in enumerate(zip(first, second)) if left != right]
        if len(positions) == 1:
            return True
        if len(positions) == 2:
            a, b = positions
            return b == a + 1 and first[a] == second[b] and first[b] == second[a]
        return False
    shorter, longer = sorted((first, second), key=len)
    if len(longer) - len(shorter) != 1:
        return False
    offset = next((i for i, (a, b) in enumerate(zip(shorter, longer)) if a != b), len(shorter))
    return shorter[offset:] == longer[offset + 1:]


@dataclass(frozen=True)
class Match:
    faq: FAQ
    score: float
    method: str
    eligible: bool


def vector_scores(query: str, revision: str) -> dict[str, float]:
    if not settings.semantic_search:
        return {}
    try:
        from app.services.vector_store import embed, get_collection

        collection = get_collection(revision)
        metadata = collection.metadata or {}
        if metadata.get("faq_revision") != revision or metadata.get("embedding_model") != settings.embedding_model:
            return {}
        count = min(settings.top_k, collection.count())
        if not count:
            return {}
        result = collection.query(query_embeddings=embed([query]), n_results=count)
        return {
            key: max(0.0, min(1.0, 1.0 - distance))
            for key, distance in zip(result["ids"][0], result["distances"][0])
        }
    except Exception:
        logger.warning("Índice semántico no disponible. Se aplica búsqueda léxica.", exc_info=True)
        return {}


class Retriever:
    def __init__(self, faqs: tuple[FAQ, ...], revision: str) -> None:
        self.revision = revision
        self.faqs = {faq.key: faq for faq in faqs}
        self.index = tuple(
            (faq, normalize(faq.question), tokens(faq.question), tokens(faq.tags)) for faq in faqs
        )
        self.frequency = Counter(word for _, _, words, _ in self.index for word in words)
        vocabulary: dict[int, list[str]] = {}
        for word in self.frequency:
            if len(word) >= 5 and word.isalpha():
                vocabulary.setdefault(len(word), []).append(word)
        self.vocabulary = vocabulary

    def correct_keywords(self, words: frozenset[str]) -> frozenset[str]:
        corrected = set(words)
        for word in words:
            uses = self.frequency[word]
            if uses > 1 or len(word) < 5 or not word.isalpha():
                continue
            candidates = [
                term for length in (len(word) - 1, len(word), len(word) + 1)
                for term in self.vocabulary.get(length, ())
                if one_edit(word, term)
                and (not uses or (self.frequency[term] >= 4 and sorted(term) == sorted(word)))
            ]
            if len(candidates) == 1:
                corrected.remove(word)
                corrected.add(candidates[0])
        return frozenset(corrected)

    def rank(self, message: str, learned: dict[str, float]) -> list[Match]:
        query = normalize(message)
        exact = [
            Match(faq, 1.0, "exacta", True) for faq, question, _, _ in self.index if query == question
        ]
        if exact and any(result.faq.reviewed for result in exact):
            return sorted(exact, key=lambda result: not result.faq.reviewed)
        raw_words = tokens(message)
        words = self.correct_keywords(raw_words)
        typo = words != raw_words
        if not words:
            return []
        weight = {word: 1 / (1 + self.frequency[word]) ** 0.25 for word in words}
        total = sum(weight.values())
        ranked: list[Match] = []
        intents = words & INTENTS
        subjects = words - INTENTS
        distinctive = len(subjects) == 1 and bool(intents) and self.frequency[next(iter(subjects))] <= 15
        for faq, _, title, tags in self.index:
            common = words & title
            if not common:
                continue
            coverage = sum(weight[word] for word in sorted(common)) / total
            precision = len(common) / len(title)
            tag_coverage = len((words - title) & tags) / len(words)
            score = min(1.0, 0.67 * coverage + 0.33 * precision + 0.04 * tag_coverage)
            equivalent = words == title and len(words) >= 2
            independent = (
                len(words - INTENTS) >= 2 and len(common - INTENTS) >= 2 and coverage >= .74
                and intents <= title and precision >= .43
            )
            keyword_match = faq.reviewed and distinctive and words <= title and score >= .76
            learned_match = faq.reviewed and independent and score >= .68 and learned.get(faq.key, 0) >= .58
            eligible = equivalent or keyword_match or (independent and score >= .72) or learned_match
            method = "equivalente" if equivalent else "palabras_clave" if keyword_match else "similar"
            if learned_match and score < .72:
                method = "aprendida"
            if typo and eligible:
                method = "difusa"
            ranked.append(Match(faq, score, method, eligible))
        if exact:
            ranked = exact + [candidate for candidate in ranked if candidate.faq.key not in {m.faq.key for m in exact}]
        semantic = vector_scores(message, self.revision) if any(match.eligible for match in ranked) else {}
        ranked.sort(key=lambda match: (
            match.eligible,
            match.score + .035 * match.faq.reviewed + .04 * semantic.get(match.faq.key, 0)
            + .045 * learned.get(match.faq.key, 0),
            match.faq.reviewed,
        ), reverse=True)
        return ranked


def same_answer(first: FAQ, second: FAQ) -> bool:
    if first.revision == second.revision:
        return True
    first_text, second_text = normalize(first.text), normalize(second.text)
    if first.links != second.links or re.findall(r"\d+", first_text) != re.findall(r"\d+", second_text):
        return False
    return SequenceMatcher(None, first_text, second_text, autojunk=False).ratio() >= .91


def confident_match(ranked: list[Match]) -> Match | None:
    if not ranked or not ranked[0].eligible:
        return None
    best = ranked[0]
    for other in ranked[1:]:
        if not other.eligible or other.faq.reviewed != best.faq.reviewed:
            continue
        if abs(best.score - other.score) > .055:
            continue
        if best.method == "exacta" and other.method != "exacta":
            continue
        if best.method == "equivalente" and other.method == "similar":
            continue
        if not same_answer(best.faq, other.faq):
            return None
    return best
