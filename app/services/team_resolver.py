"""
Shared team-name resolver: maps football-data.org API names to local DB names.

Usage:
    from app.services.team_resolver import resolve_team

    local_name = resolve_team(api_name, local_teams)
    # Returns the matched local DB name, or None if no safe match found.
"""

from app.services.team_aliases import ALIASES


def resolve_team(api_name: str, local_teams) -> str | None:
    """
    Attempt to match an API team name to a name in the local dataset.

    Resolution order:
      1. Exact match against local_teams
      2. ALIASES lookup (explicit override; None sentinel = block fuzzy)
      3. Case-insensitive exact match
      4. Suffix / prefix stripping ( fc, cd, cf, ud, afc … )
      5. Longest-substring inclusion (DB name inside cleaned API name)
      6. First-word fallback (if word >= 5 chars)

    Args:
        api_name:    Team name as returned by football-data.org API.
        local_teams: Iterable of team name strings from the local dataset.

    Returns:
        Matched local DB team name, or None.
    """
    api_name = api_name.strip()
    local_teams = list(local_teams)
    local_lower = {t.lower(): t for t in local_teams}

    # 1. Exact match
    if api_name in local_teams:
        return api_name

    lc = api_name.lower()

    # 2. Explicit alias map
    if lc in ALIASES:
        target = ALIASES[lc]
        if target is None:
            return None  # blocked — no fuzzy fallback
        if target.lower() in local_lower:
            return local_lower[target.lower()]
        # alias defined but target not in current dataset — fall through
        return None

    # 3. Case-insensitive exact
    if lc in local_lower:
        return local_lower[lc]

    # 4. Strip common suffixes / prefixes
    clean = lc
    for suffix in (' fc', ' cd', ' cf', ' ud', ' afc', ' sc', ' ac'):
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)]
            break
    for prefix in ('cd ', 'fc ', 'rc ', 'sc ', 'ac '):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
            break

    if clean in local_lower:
        return local_lower[clean]

    # 5. Longest-substring inclusion
    #    Sort descending by length to prefer longer (more specific) matches
    sorted_local = sorted(local_lower.items(), key=lambda x: len(x[0]), reverse=True)
    for lt_lower, lt in sorted_local:
        if len(lt_lower) >= 5 and lt_lower in clean:
            return lt

    # 6. First-word fallback
    first_word = clean.split()[0] if clean.split() else ''
    if len(first_word) >= 6:
        for lt_lower, lt in local_lower.items():
            if first_word in lt_lower:
                return lt

    return None
