
"""Published addresses and explicit routing rules for the Peñalolén service."""

from dataclasses import asdict, dataclass

from app.services.knowledge import FAQ, normalize
from app.services.place_catalog import GRECIA, ORIENTAL, PLACES

PORTAL = "https://tramites.penalolen.cl/"
BUILDINGS = PORTAL + "Tramites/buscar"
PHONEBOOK = PORTAL + "Telefonos"
DIRECTORY = "https://www.penalolen.cl/directorio-telefonico/"
OIRS_PAGE = "https://participa.penalolen.cl/p/4-informacion-y-atencion-vecinal"
FAQ_PAGE = PORTAL + "Preguntas/ver"
MAIN_PHONE = "+56 2 2486 8000"
ENVIRONMENT = PORTAL + "Direcciones/ver/direccion-de-medio-ambiente"


@dataclass(frozen=True)
class Route:
    unit: str
    address: str | None
    phone: str | None
    email: str | None
    url: str
    source_url: str
    building: str | None = None


OIRS = Route("Oficina de Información, Reclamos y Sugerencias (OIRS)", GRECIA, MAIN_PHONE,
             "oirsdigital@penalolen.cl", OIRS_PAGE, FAQ_PAGE, "consistorial")

# Aliases come from Direccion and cover variants used by the two worksheets.
ROUTES = (
    (("transito",), Route("Dirección de Tránsito y Transporte Público", GRECIA,
                         "+56 2 2486 8806", None, PORTAL, PHONEBOOK, "cav")),
    (("obras",), Route("Dirección de Obras Municipales", GRECIA, "+56 2 2486 8770", None,
                      PORTAL + "Direcciones/ver/direccion-de-obras-municipales",
                      PORTAL + "Direcciones/ver/direccion-de-obras-municipales", "cav")),
    (("desarrollo comunitario",), Route("Dirección de Desarrollo Comunitario (DIDECO)", GRECIA,
                                     "+56 2 2486 8127", None, PORTAL, PHONEBOOK)),
    (("medio ambiente",), Route("Dirección de Medio Ambiente", ORIENTAL,
                              "+56 2 2486 8253", None, ENVIRONMENT, ENVIRONMENT, "orientales")),
    (("centro de atencion a la familia", "caf"),
     Route(PLACES["caf"].name, PLACES["caf"].address, "+56 2 2279 3009",
           None, PLACES["caf"].source_url, PLACES["caf"].source_url, "caf")),
    (("cultura",), Route("Corporación Cultural de Peñalolén", PLACES["chimkowe"].address,
                        "+56 2 2486 8338", "chimkowe@penalolen.cl", "https://chimkowe.cl/",
                        "https://www.penalolen.cl/edificios-municipales/", "chimkowe")),
    (("juzgado",), Route("Juzgado de Policía Local", ORIENTAL, "+56 2 2486 8240", None,
                         PLACES["juzgado"].source_url, PORTAL + "Sucursales/listar", "juzgado")),
    (("finanzas", "rentas"), Route("Rentas y Finanzas", GRECIA, MAIN_PHONE, None,
                                  PORTAL, DIRECTORY)),
    (("vivienda",), Route("Gerencia de Vivienda", "Av. Grecia 8299, Peñalolén",
                          "+56 2 2279 4997", None, PORTAL, PORTAL + "Sucursales/listar")),
    (("administracion municipal", "secretaria municipal"), OIRS),
)

TOPICS = (
    (("juzgado de policia local", "prescribir multas", "prescripcion de multa"), "juzgado"),
    (("licencia de conducir", "permiso de circulacion", "licencia clase"), "transito"),
    (("permiso de edificacion", "construccion irregular", "direccion de obras", "certificado de numero"), "obras"),
    (("registro social de hogares", "rsh"), "desarrollo comunitario"),
    (("subsidio habitacional", "vivienda social"), "vivienda"),
    (("chimkowe",), "cultura"),
    (("centro de atencion a la familia", "caf"), "centro de atencion a la familia"),
    (("reciclaje", "compostaje", "esterilizacion de mascotas", "zoonosis"), "medio ambiente"),
    (("patente comercial", "multas tag", "multa de tag"), "rentas"),
)

PLACE_TERMS = (
    ("juzgado", ("juzgado de policia local",)),
    ("orientales", ("complejo municipal orientales", "edificio municipal orientales", "arbolado comunal", "zoonosis")),
    ("cav", ("cav", "centro de atencion al vecino", "centro de atencion vecinal")),
    ("consistorial", ("edificio consistorial", "edificio municipal consistorial", "oficina oirs")),
    ("chimkowe", ("chimkowe", "grecia 8787")),
    ("piscina", ("piscina municipal", "piscina temperada", "grellet de los reyes 2101")),
    ("san-luis", ("centro civico san luis", "centro civico y cultural san luis", "biblioteca san luis")),
    ("chileatiende", ("chileatiende", "chile atiende")),
    ("caf", ("centro de atencion a la familia", "caf", "calle 17 a 931")),
    ("yunus", ("yunus",)),
    ("adulto-mayor", ("centro adulto mayor", "centro de adulto mayor", "centro del adulto mayor")),
    ("bodega", ("bodega municipal",)),
    ("mediacion", ("centro de mediacion", "mediacion vecinal", "ictinos 1626")),
    ("kintun", ("kintun",)),
    ("registro-civil", ("registro civil",)),
)


def contains(text: str, fragment: str) -> bool:
    return f" {fragment} " in f" {text} "


def routing(message: str, faq: FAQ | None = None) -> Route:
    query = normalize(message)
    topic = next((unit for terms, unit in TOPICS if any(contains(query, t) for t in terms)), "")
    unit = normalize(faq.unit if faq else "")
    # Topic rules can interpret FAQs published by a cross-cutting service desk.
    if not topic and unit not in {"", "secretaria municipal", "administracion municipal"}:
        topic = unit
    for terms, route in ROUTES:
        if any(contains(topic, t) for t in terms):
            return route
    places = place_ids(query)
    if len(places) == 1:
        place = PLACES[places[0]]
        return Route(place.name, place.address, None, None, place.source_url, place.source_url, place.id)
    if faq and faq.unit and unit not in {"secretaria municipal", "administracion municipal"}:
        return Route(faq.unit, None, None, None, PORTAL, PORTAL + "Direcciones/listar")
    return OIRS


def referral(route: Route) -> dict:
    data = asdict(route)
    data["central"] = asdict(OIRS) if route != OIRS and (not route.address or not route.phone) else None
    return data


def related_places(message: str, faq: FAQ | None, route: Route | None) -> list[dict]:
    query = normalize(message)
    context = " ".join((query, normalize(faq.question), normalize(faq.text))) if faq else query
    found = place_ids(context)
    if faq and not found:
        related = routing(message, faq)
        if related.building and related != OIRS:
            found.append(related.building)
    if route and route.building and route.building not in found:
        found.append(route.building)
    return [
        {**asdict(PLACES[key]), "service": faq.question if faq else None} for key in found
    ]


def place_ids(normalized: str) -> list[str]:
    return [key for key, terms in PLACE_TERMS if any(contains(normalized, term) for term in terms)]
