"""
Team name aliases: maps football-data.org API names (lowercase) to local DB names.

Rules:
- Value is a string  -> use that local DB name directly (skip all fuzzy logic)
- Value is None      -> team is NOT in local dataset; return None immediately
                        (prevents wrong fuzzy matches, e.g. 'Athletic Club' -> 'Annan Athletic')
"""

ALIASES = {
    # ── Bundesliga ─────────────────────────────────────────────────────────
    '1. fc köln':             'FC Koln',
    '1. fsv mainz 05':        'Mainz',
    'bayer 04 leverkusen':    'Leverkusen',
    'borussia mönchengladbach': "M'gladbach",
    'eintracht frankfurt':    'Ein Frankfurt',
    'fc st. pauli 1910':      'St Pauli',

    # ── La Liga ────────────────────────────────────────────────────────────
    'athletic club':                  None,   # Bilbao not in dataset — blocks 'Annan Athletic' false match
    'club atlético de madrid':        'Ath Madrid',
    'deportivo alavés':               'Alaves',
    'rayo vallecano de madrid':       'Vallecano',
    'rcd espanyol de barcelona':      'Espanol',
    'real betis balompié':            'Betis',
    'real sociedad de fútbol':        'Sociedad',

    # ── Ligue 1 ────────────────────────────────────────────────────────────
    'paris saint-germain fc':         'Paris SG',
    'stade rennais fc 1901':          'Rennes',
    'ogc nice':                       'Nice',
    'olympique lyonnais':             'Lyon',
    'olympique de marseille':         'Marseille',

    # ── Champions League / other European ─────────────────────────────────
    'afc ajax':                       'Ajax',

    # ── Serie A ────────────────────────────────────────────────────────────
    'acf fiorentina':                 'Fiorentina',
    'ac pisa 1909':                   'Pisa',
    'as roma':                        'Roma',
    'fc internazionale milano':       'Inter',

    # ── Eredivisie / Dutch ─────────────────────────────────────────────────
    'az':                             'AZ Alkmaar',
    'psv':                            'PSV Eindhoven',
    'nec':                            'Nijmegen',

    # ── Primeira Liga / Portugal ───────────────────────────────────────────
    'fc famalicão':                   'Famalicao',
    'sporting clube de braga':        'Sp Braga',  # blocks wrong 'Sporting Kansas City' match

    # ── Brasileirão ────────────────────────────────────────────────────────
    'são paulo fc':                   'Sao Paulo',
    'ca mineiro':                     'Atletico-MG',
    'cr flamengo':                    'Flamengo RJ',
    'grêmio fbpa':                    'Gremio',
    'ec vitória':                     'Vitoria',
    'ca paranaense':                  None,   # Not in local dataset
    'clube do remo':                  None,   # Not in local dataset

    # ── Other ──────────────────────────────────────────────────────────────
    'cd santa clara':                 'Santa Clara',
    'racing club de lens':            'Lens',
    'fortuna sittard':                'For Sittard',
}
