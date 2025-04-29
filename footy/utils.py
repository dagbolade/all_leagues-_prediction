def smart_team_match(live_team_name, known_teams):
    """Smart matcher with manual overrides first."""

    # Manual overrides (check before cleaning)
    if 'paris saint-germain' in live_team_name.lower():
        return 'Paris SG'
    if 'manchester united' in live_team_name.lower():
        return 'Man United'
    if 'manchester city' in live_team_name.lower():
        return 'Man City'

    # Then clean and fuzzy match
    live_team_name = live_team_name.lower()
    live_team_name = live_team_name.replace('fc', '').replace('cf', '').replace('afc', '').replace('sc', '')
    live_team_name = live_team_name.replace('tilburg', '').replace('united', '').replace('city', '').strip()

    best_match = None
    best_score = 0

    for team in known_teams:
        team_name_clean = team.lower().replace('fc', '').replace('cf', '').replace('afc', '').replace('sc', '')
        team_name_clean = team_name_clean.replace('tilburg', '').replace('united', '').replace('city', '').strip()

        # Exact match
        if live_team_name == team_name_clean:
            print(f"[MATCH-EXACT] {live_team_name} -> {team}")
            return team

        # Partial match
        if team_name_clean in live_team_name or live_team_name in team_name_clean:
            print(f"[MATCH-PARTIAL] {live_team_name} -> {team}")
            return team

        # Word overlap score
        live_words = set(live_team_name.split())
        team_words = set(team_name_clean.split())
        common = live_words.intersection(team_words)

        score = len(common)
        if score > best_score:
            best_score = score
            best_match = team

    if best_score > 0:
        print(f"[MATCH-WORDS] {live_team_name} -> {best_match} (score={best_score})")
        return best_match

    print(f"[NO MATCH] {live_team_name}")
    return None
