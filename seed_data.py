"""
Seed-script: laadt de voorbeelddata uit toolregister_v3.html in de database.
Veilig om meerdere keren te draaien (checkt op bestaande namen).
"""
from datetime import datetime
from models import init_db, get_session, Tool, Project, Probleem, User

TOOLS = [
    dict(
        naam="Power BI",
        eigenaar="Data Team",
        beschrijving="Dashboard- en rapportagetool voor business intelligence en datavisualisatie op basis van live databronnen.",
        status="actief",
        ingebracht_door="Jan de Vries",
        ingebracht_datum=datetime(2024, 1, 12),
        gewijzigd_door="Sara Bakker",
        gewijzigd_datum=datetime(2024, 3, 5),
    ),
    dict(
        naam="Monday.com",
        eigenaar="PMO",
        beschrijving="Werkbeheersplatform voor projectplanning, taakverdeling en voortgangsmonitoring across teams.",
        status="actief",
        ingebracht_door="Roos Smit",
        ingebracht_datum=datetime(2024, 2, 3),
        gewijzigd_door="Roos Smit",
        gewijzigd_datum=datetime(2024, 3, 1),
    ),
    dict(
        naam="ChatGPT",
        eigenaar="Innovatieteam",
        beschrijving="AI-assistent voor tekstgeneratie, samenvatten en kennisondersteuning binnen teams.",
        status="evaluatie",
        ingebracht_door="Tom Hendriks",
        ingebracht_datum=datetime(2024, 2, 20),
        gewijzigd_door="Tom Hendriks",
        gewijzigd_datum=datetime(2024, 2, 20),
    ),
    dict(
        naam="Miro",
        eigenaar="Design Team",
        beschrijving="Digitaal whiteboard voor visuele samenwerking, workshops en mapping-sessies met meerdere deelnemers.",
        status="actief",
        ingebracht_door="Lisa van Dam",
        ingebracht_datum=datetime(2024, 1, 8),
        gewijzigd_door="Jan de Vries",
        gewijzigd_datum=datetime(2024, 2, 14),
    ),
    dict(
        naam="Zapier",
        eigenaar="IT Afdeling",
        beschrijving="No-code automatiseringsplatform dat apps en werkstromen aan elkaar koppelt zonder programmeerkennis.",
        status="actief",
        ingebracht_door="Mark Visser",
        ingebracht_datum=datetime(2024, 3, 15),
        gewijzigd_door="Mark Visser",
        gewijzigd_datum=datetime(2024, 3, 15),
    ),
]

PROJECTEN = [
    dict(naam="Digitale Transformatie 2024", projectleider="Jan de Vries",  opdrachtgever="Directie",  status="lopend",   opmerkingen="Strategisch meerjarig programma gericht op digitalisering van kernprocessen.", ingebracht_door="Sara Bakker", ingebracht_datum=datetime(2024, 1, 2),  gewijzigd_door="Jan de Vries", gewijzigd_datum=datetime(2024, 3, 10)),
    dict(naam="Klantportaal Redesign",        projectleider="Roos Smit",     opdrachtgever="Marketing", status="lopend",   opmerkingen="Redesign van het klantportaal voor betere gebruikerservaring.",               ingebracht_door="Roos Smit",   ingebracht_datum=datetime(2024, 1, 15), gewijzigd_door="Lisa van Dam",  gewijzigd_datum=datetime(2024, 3, 5)),
    dict(naam="HR Automatisering",            projectleider="Mark Visser",   opdrachtgever="HR",        status="on hold",  opmerkingen="Automatisering van HR-processen zoals onboarding en verlofbeheer.",           ingebracht_door="Mark Visser", ingebracht_datum=datetime(2024, 2, 20), gewijzigd_door="Mark Visser",  gewijzigd_datum=datetime(2024, 3, 1)),
    dict(naam="Data Centralisatie",           projectleider="Sara Bakker",   opdrachtgever="CFO",       status="lopend",   opmerkingen="Centralisering van alle databronnen naar één datawarehouse.",                  ingebracht_door="Jan de Vries",ingebracht_datum=datetime(2024, 1, 10), gewijzigd_door="Sara Bakker",  gewijzigd_datum=datetime(2024, 3, 12)),
]

PROBLEMEN = [
    dict(titel="Trage en foutgevoelige rapportage",    beschrijving="Maandrapportages kosten veel tijd en bevatten regelmatig fouten door handmatig samenvoegen van data.",                                           status="actief",    opmerkingen="Gevoeld door finance en management.", ingebracht_door="Sara Bakker", ingebracht_datum=datetime(2024, 1, 5),  gewijzigd_door="Sara Bakker", gewijzigd_datum=datetime(2024, 1, 5)),
    dict(titel="Gebrek aan projectoverzicht",          beschrijving="Teams hebben geen centraal overzicht van lopende projecten, waardoor dubbel werk en miscommunicatie ontstaat.",                                   status="actief",    opmerkingen="",                                    ingebracht_door="Roos Smit",   ingebracht_datum=datetime(2024, 1, 10), gewijzigd_door="Jan de Vries", gewijzigd_datum=datetime(2024, 2, 20)),
    dict(titel="Kennissilos binnen teams",             beschrijving="Kennis en expertise worden niet gedeeld tussen teams, waardoor het wiel steeds opnieuw uitgevonden wordt.",                                       status="actief",    opmerkingen="Hoog prioriteit na recente audit.",   ingebracht_door="Tom Hendriks",ingebracht_datum=datetime(2024, 2, 18), gewijzigd_door="Tom Hendriks", gewijzigd_datum=datetime(2024, 2, 18)),
    dict(titel="Handmatige dataverwerking",            beschrijving="Veel processen vereisen handmatige data-invoer en -export, wat foutgevoelig en tijdrovend is.",                                                   status="actief",    opmerkingen="",                                    ingebracht_door="Mark Visser", ingebracht_datum=datetime(2024, 1, 22), gewijzigd_door="Mark Visser", gewijzigd_datum=datetime(2024, 1, 22)),
    dict(titel="Inefficiënte interne communicatie",    beschrijving="Communicatie verloopt via te veel kanalen waardoor informatie verloren gaat en reactietijden hoog zijn.",                                          status="evaluatie", opmerkingen="",                                    ingebracht_door="Lisa van Dam",ingebracht_datum=datetime(2024, 3, 1),  gewijzigd_door="Lisa van Dam", gewijzigd_datum=datetime(2024, 3, 1)),
]

# tool_naam → (project_namen, probleem_titels)
KOPPELINGEN = {
    "Power BI":    (["Digitale Transformatie 2024", "Data Centralisatie"],
                    ["Trage en foutgevoelige rapportage", "Handmatige dataverwerking"]),
    "Monday.com":  (["Digitale Transformatie 2024", "Klantportaal Redesign", "HR Automatisering"],
                    ["Gebrek aan projectoverzicht", "Inefficiënte interne communicatie"]),
    "ChatGPT":     (["Klantportaal Redesign", "HR Automatisering"],
                    ["Kennissilos binnen teams", "Inefficiënte interne communicatie"]),
    "Miro":        (["Digitale Transformatie 2024", "Klantportaal Redesign"],
                    ["Kennissilos binnen teams", "Gebrek aan projectoverzicht"]),
    "Zapier":      (["HR Automatisering", "Data Centralisatie"],
                    ["Handmatige dataverwerking", "Trage en foutgevoelige rapportage"]),
}


def seed():
    init_db()
    session = get_session()

    if session.query(Tool).count() > 0:
        print("Database bevat al data – seed overgeslagen.")
        session.close()
        return

    # Voeg toe
    tool_map    = {}
    project_map = {}
    probleem_map = {}

    for t in TOOLS:
        obj = Tool(**t)
        session.add(obj)
        session.flush()
        tool_map[obj.naam] = obj

    for p in PROJECTEN:
        obj = Project(**p)
        session.add(obj)
        session.flush()
        project_map[obj.naam] = obj

    for p in PROBLEMEN:
        obj = Probleem(**p)
        session.add(obj)
        session.flush()
        probleem_map[obj.titel] = obj

    # Koppel
    for tool_naam, (proj_namen, prob_titels) in KOPPELINGEN.items():
        tool = tool_map[tool_naam]
        for naam in proj_namen:
            tool.projecten.append(project_map[naam])
        for titel in prob_titels:
            tool.problemen.append(probleem_map[titel])

    session.commit()
    print(f"Seed klaar: {len(tool_map)} tools, {len(project_map)} projecten, {len(probleem_map)} problemen.")
    session.close()


TIJDBALK_DEFAULTS = {
    "Power BI":   (25, 95),
    "Monday.com": (5,  85),
    "ChatGPT":    (40, 75),
    "Miro":       (5,  40),
    "Zapier":     (55, 95),
}


def update_tijdbalk():
    """Voeg tijdbalk-posities toe aan bestaande tools die er nog geen hebben."""
    session = get_session()
    from models import Tool as ToolModel
    for naam, (start, eind) in TIJDBALK_DEFAULTS.items():
        t = session.query(ToolModel).filter_by(naam=naam).first()
        if t and t.tijdbalk_start is None:
            t.tijdbalk_start = start
            t.tijdbalk_eind  = eind
    session.commit()
    session.close()


def ensure_admin():
    """Zorg dat er minimaal één admin-gebruiker is. Aangemaakt als geen users bestaan."""
    session = get_session()
    try:
        if session.query(User).count() > 0:
            print("Gebruikers al aanwezig – ensure_admin overgeslagen.")
            return

        # Admin aanmaken
        admin = User(
            naam="Beheerder",
            email="admin@toolregister.nl",
            rol="admin",
            aangemaakt_datum=datetime.utcnow(),
            actief=True,
        )
        admin.set_password("admin123")
        session.add(admin)

        # Voorbeeldgebruiker aanmaken
        gebruiker = User(
            naam="Jan de Vries",
            email="jan@toolregister.nl",
            rol="gebruiker",
            aangemaakt_datum=datetime.utcnow(),
            actief=True,
        )
        gebruiker.set_password("gebruiker123")
        session.add(gebruiker)

        session.commit()
        print("Admin aangemaakt: admin@toolregister.nl / admin123")
        print("Gebruiker aangemaakt: jan@toolregister.nl / gebruiker123")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
    update_tijdbalk()
    ensure_admin()
