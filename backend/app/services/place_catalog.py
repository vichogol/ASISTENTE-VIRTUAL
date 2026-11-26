
"""Addresses, service locations and photo credits for the municipal directory."""

from dataclasses import dataclass

DIRECTORY_PAGE = "https://www.penalolen.cl/edificios-municipales/"
BRANCHES = "https://tramites.penalolen.cl/Sucursales/listar"
GRECIA = "Av. Grecia 8735, Peñalolén"
ORIENTAL = "Av. Oriental 6958, Peñalolén"
GRELLET = "Ricardo Grellet de los Reyes 2001, Peñalolén"
LAS_TORRES = "Av. Las Torres 5555, Peñalolén"

SAN_LUIS_OSM = "https://www.openstreetmap.org/way/745408470"
KINTUN_OSM = "https://www.openstreetmap.org/way/678461092"
CULTURE_PHOTO = "/recintos/chimkowe.jpg"
CULTURE_PHOTO_SOURCE = "https://commons.wikimedia.org/wiki/File:Centro_Cultural_Chimkowe,_Pe%C3%B1alol%C3%A9n,_Santiago_20260916_03.jpg"
SAN_LUIS_PHOTO_SOURCE = "https://chimkowe.cl/wp-content/uploads/2021/10/Ficha-Tecnica-CCCSL.pdf#page=4"
KINTUN_PHOTO_SOURCE = "https://www.flickr.com/photos/penalolen/10192400613/in/album-72157636399494125/"
CIVIC_SURVEY = ("https://participa.penalolen.cl/uploads/archivos/"
                "a-PSCC_CATASTRO_URBANO_CENTRO_CIVICO_PENALOLEN_Art%2072_230623.pdf")


@dataclass(frozen=True)
class Building:
    id: str
    name: str
    short_name: str
    address: str
    latitude: float | None
    longitude: float | None
    style: str
    services: tuple[str, ...]
    source_url: str
    map_source: str | None
    photo_url: str | None = None
    photo_source: str | None = None
    photo_caption: str | None = None


PLACES = {
    building.id: building for building in (
        Building("cav", "Centro de Atención al Vecino", "CAV", GRECIA,
                 -33.47678, -70.54261, "civic",
                 ("Licencia de conducir", "Permiso de circulación", "Obras municipales"),
                 DIRECTORY_PAGE, "https://www.openstreetmap.org/way/622839473",
                 "/recintos/cav.jpg",
                 "https://gubbinsarquitectos.cl/galeria-cav", "Fachada del Centro de Atención al Vecino"),
        Building("san-luis", "Centro Cívico y Cultural San Luis", "San Luis", LAS_TORRES,
                 -33.502405, -70.577900, "culture", ("Delegación municipal", "Biblioteca San Luis", "Actividades culturales"),
                 "https://chimkowe.cl/san-luis/", SAN_LUIS_OSM,
                 "/recintos/san-luis.jpg", SAN_LUIS_PHOTO_SOURCE, "Salón del Centro Cívico y Cultural San Luis"),
        Building("consistorial", "Edificio Municipal Consistorial", "Consistorial", GRECIA,
                 -33.47686, -70.54172, "civic", ("Orientación municipal y OIRS", "Secretaría Municipal"),
                 DIRECTORY_PAGE, "https://www.openstreetmap.org/way/622839469",
                 "/recintos/consistorial.png", None, "Fachada del Edificio Municipal Consistorial"),
        Building("chimkowe", "Centro Cultural Chimkowe", "Chimkowe", "Av. Grecia 8787, Peñalolén",
                 -33.47712, -70.54118, "culture", ("Talleres y actividades culturales",),
                 "https://chimkowe.cl/chimkowe/", "https://www.openstreetmap.org/way/622839470",
                 CULTURE_PHOTO, CULTURE_PHOTO_SOURCE, "Centro Cultural Chimkowe, fachada acristalada"),
        Building("piscina", "Piscina Municipal", "Piscina Municipal", "Ricardo Grellet de los Reyes 2101, Peñalolén",
                 -33.47812, -70.54212, "pool", ("Cursos y talleres de piscina",),
                 DIRECTORY_PAGE, "https://www.openstreetmap.org/way/678461082",
                 "/recintos/piscina.jpg",
                 "https://deportespenalolen.cl/blog/2020/11/26/piscina-temperada-reabre-sus-puertas-la-primera-semana-de-diciembre/",
                 "Interior de la Piscina Temperada Municipal"),
        Building("chileatiende", "Oficina ChileAtiende", "ChileAtiende", LAS_TORRES,
                 -33.502405, -70.577900, "civic", ("Orientación sobre servicios del Estado",),
                 DIRECTORY_PAGE, SAN_LUIS_OSM, "/recintos/san-luis.jpg", SAN_LUIS_PHOTO_SOURCE,
                 "Interior del Centro Cívico San Luis, que alberga la oficina ChileAtiende"),
        Building("caf", "Centro de Atención a la Familia", "CAF", "Calle 17-A 931, La Faena, Peñalolén",
                 None, None, "civic", ("Orientación familiar",),
                 "https://www.penalolen.cl/centro-de-atencion-a-la-familia/", None),
        Building("yunus", "Edificio Yunus", "Yunus", GRELLET,
                 -33.47758, -70.54165, "civic", ("Empleo", "Capacitación", "Asesoría para emprendimientos"),
                 DIRECTORY_PAGE, "https://www.openstreetmap.org/way/678461085",
                 "/recintos/yunus.jpg", CIVIC_SURVEY + "#page=17",
                 "Vista aérea municipal con el Edificio Yunus identificado"),
        Building("adulto-mayor", "Centro de Adulto Mayor", "Centro de Adulto Mayor", GRELLET,
                 -33.47781, -70.54134, "green", ("Actividades para personas mayores",), DIRECTORY_PAGE, KINTUN_OSM,
                 "/recintos/kintun.jpg", KINTUN_PHOTO_SOURCE, "Acceso al Centro de Adulto Mayor y KINTUN"),
        Building("orientales", "Edificio Municipal Orientales", "Orientales", ORIENTAL,
                 -33.46700, -70.55855, "green", ("Áreas verdes", "Arbolado comunal", "Zoonosis"),
                 DIRECTORY_PAGE, "https://www.openstreetmap.org/way/1485888085"),
        Building("bodega", "Bodega Municipal", "Bodega Municipal", "Maravedies 1076, Peñalolén",
                 None, None, "civic", (), BRANCHES, None),
        Building("mediacion", "Centro de Mediación Vecinal", "Mediación Vecinal", "Ictinos 1626, Peñalolén",
                 None, None, "civic", ("Orientación para mediación vecinal",), BRANCHES, None,
                 "/recintos/mediacion.jpg", "https://www.penalolen.cl/wp-content/uploads/2024/05/Revista-Nosotras-Nov-2024.pdf#page=8",
                 "Fachada del inmueble municipal de Ictinos 1626"),
        Building("juzgado", "Juzgado de Policía Local", "Juzgado", ORIENTAL,
                 -33.46720, -70.55881, "court", ("Causas y exhortos", "Prescripción de multas"),
                 "https://www.penalolen.cl/juzgado-de-policia-local-jpl/",
                 "https://www.openstreetmap.org/node/6637579556"),
        Building("kintun", "Centro Diurno KINTUN", "KINTUN", GRELLET,
                 -33.47781, -70.54134, "green", ("Orientación sobre el Centro Diurno",), DIRECTORY_PAGE, KINTUN_OSM,
                 "/recintos/kintun.jpg", KINTUN_PHOTO_SOURCE, "Acceso durante la inauguración del Centro KINTUN"),
        Building("registro-civil", "Registro Civil de Peñalolén", "Registro Civil", GRECIA,
                 -33.47669, -70.54148, "civic", ("Documentos de identidad", "Certificados del Registro Civil"),
                 DIRECTORY_PAGE, "https://www.openstreetmap.org/node/7070202755",
                 "/recintos/registro-civil.jpg", CIVIC_SURVEY + "#page=20",
                 "Vista aérea municipal con el edificio del Registro Civil identificado"),
    )
}
