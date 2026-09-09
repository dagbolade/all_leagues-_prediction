import re
import unicodedata

DOMESTIC = {
    'E0':'Premier League','E1':'Championship','E2':'League One','E3':'League Two','EC':'National League',
    'SC0':'Scottish Premiership','SC1':'Scottish Championship','SC2':'Scottish League One','SC3':'Scottish League Two',
    'D1':'Bundesliga','D2':'2. Bundesliga','I1':'Serie A','I2':'Serie B','SP1':'La Liga','SP2':'Segunda Division',
    'F1':'Ligue 1','F2':'Ligue 2','N1':'Eredivisie','B1':'Belgian Pro League','P1':'Primeira Liga','T1':'Super Lig','G1':'Greek Super League'}
GLOBAL = {'ARG':'ARG1','AUT':'AUT1','BRA':'BRA1','CHN':'CHN1','DNK':'DNK1','FIN':'FIN1','IRL':'IRL1','JPN':'JPN1','MEX':'MEX1','NOR':'NOR1','POL':'POL1','ROU':'ROU1','RUS':'RUS1','SWE':'SWE1','SWZ':'SWZ1','USA':'USA1'}
NAMES = {**DOMESTIC,'CL':'Champions League','NBA':'NBA','EuroLeague':'EuroLeague','ATP':'ATP Tour','WTA':'WTA Tour',
         'ARG1':'Argentina','AUT1':'Austria','BRA1':'Brazil','CHN1':'China','DNK1':'Denmark','FIN1':'Finland','IRL1':'Ireland','JPN1':'Japan','MEX1':'Mexico','NOR1':'Norway','POL1':'Poland','ROU1':'Romania','RUS1':'Russia','SWE1':'Sweden','SWZ1':'Switzerland','USA1':'MLS'}

def canonical(name):
    """Explicit aliases only; never choose a team using substring similarity."""
    from app.services.team_aliases import ALIASES
    name=str(name).strip()
    from .aliases import FOOTBALL_ALIASES
    alias=FOOTBALL_ALIASES.get(name.lower(),ALIASES.get(name.lower()))
    return alias if alias else name

def team_id(sport,name):
    name=unicodedata.normalize('NFKD',canonical(name)).encode('ascii','ignore').decode().lower()
    return sport+':'+re.sub(r'[^a-z0-9]+','-',name).strip('-')
