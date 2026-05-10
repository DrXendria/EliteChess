"""
Swiss, Round-Robin, and Team Swiss pairing engines.
"""
import random
from models import Tournament, Match, Round, MatchResult, Player, TournamentType


def generate_pairings(tournament: Tournament) -> Round | None:
    """Generate pairings for the next round based on tournament type."""
    if tournament.tournament_type == TournamentType.SWISS:
        return _generate_swiss_pairings(tournament)
    elif tournament.tournament_type == TournamentType.ROUND_ROBIN:
        return _generate_round_robin_pairings(tournament)
    elif tournament.tournament_type == TournamentType.TEAM_SWISS:
        return _generate_team_swiss_pairings(tournament)
    return None


# ─── SWISS SYSTEM ────────────────────────────────────────────────────────────

def _generate_swiss_pairings(tournament: Tournament) -> Round | None:
    next_round = tournament.current_round + 1
    if next_round > tournament.num_rounds:
        return None

    active = tournament.get_active_players()
    if len(active) < 2:
        return None

    return _swiss_subsequent_round(tournament, active, next_round)


def _swiss_subsequent_round(tournament: Tournament, players: list[Player], round_num: int) -> Round:
    """Subsequent rounds: pair players with similar scores."""
    player_scores = {}
    for p in players:
        player_scores[p.id] = tournament.get_player_score(p.id)

    sorted_players = sorted(
        players,
        key=lambda p: (-player_scores[p.id], -p.rating)
    )

    bye_player = None
    working_players = list(sorted_players)

    if len(working_players) % 2 == 1:
        bye_player = _select_bye_player(tournament, working_players, player_scores)
        working_players.remove(bye_player)

    matches = _pair_score_groups(tournament, working_players, player_scores)

    if bye_player:
        matches.append(Match(
            board=len(matches) + 1,
            white_id=bye_player.id,
            black_id="BYE",
            result=MatchResult.BYE
        ))

    return Round(round_number=round_num, matches=matches)


def _select_bye_player(tournament: Tournament, players: list[Player], scores: dict) -> Player:
    """Select bye player: lowest-scoring player who hasn't had a bye yet."""
    candidates = sorted(players, key=lambda p: (scores[p.id], p.rating))
    for c in candidates:
        if not tournament.player_had_bye(c.id):
            return c
    return candidates[0]


def _pair_score_groups(tournament: Tournament, players: list[Player], scores: dict) -> list[Match]:
    """Pair players within score groups using FIDE Dutch (Torba) system.
    
    For each score group:
    1. Sort by rating descending
    2. Split into S1 (top half) and S2 (bottom half)
    3. Pair S1[0] vs S2[0], S1[1] vs S2[1], etc.
    4. If a pair already played each other, transpose within S2
    5. Unpaired players float down to the next score group
    """
    score_groups: dict[float, list[Player]] = {}
    for p in players:
        s = scores[p.id]
        if s not in score_groups:
            score_groups[s] = []
        score_groups[s].append(p)

    sorted_scores = sorted(score_groups.keys(), reverse=True)
    matches = []
    floaters: list[Player] = []
    board_num = 1

    for score in sorted_scores:
        current_players = score_groups[score]
        
        # Sort current_players by rating descending, tiebreak alphabetically
        current_players.sort(key=lambda p: (-p.rating, (p.surname or "").lower(), (p.name or "").lower(), p.id))
        
        # 1. Pair down-floaters with the highest available players in current_players
        unpaired_floaters = []
        for floater in floaters:
            paired = False
            candidates = []
            for idx, cand in enumerate(current_players):
                if tournament.have_played(floater.id, cand.id):
                    continue
                if _have_absolute_color_conflict(tournament, floater, cand):
                    continue
                
                c1 = tournament.get_player_colors(floater.id)
                c2 = tournament.get_player_colors(cand.id)
                c1_last = c1[-1] if c1 else None
                c2_last = c2[-1] if c2 else None
                color_compat = 1 if c1_last and c2_last and c1_last != c2_last else 0
                
                candidates.append((color_compat, idx, cand))
                
            # Sort candidates: Prioritize HIGHEST RATING (lowest idx) first for floaters!
            candidates.sort(key=lambda x: (x[1], -x[0]))
            
            for _, idx, cand in candidates:
                w, b = _assign_colors(tournament, floater, cand)
                matches.append(Match(board=board_num, white_id=w, black_id=b))
                board_num += 1
                
                current_players.remove(cand)
                paired = True
                break
                
            if not paired:
                unpaired_floaters.append(floater)
                
        floaters = unpaired_floaters
        
        # 2. Pair the remaining players in this score group using Torba (S1 vs S2)
        group = current_players
        half = len(group) // 2
        s1 = group[:half]
        s2 = group[half:]

        pairings_found = []
        
        def solve_bracket(s1_idx, used_s2_idx):
            if s1_idx == len(s1):
                return True
            
            p1 = s1[s1_idx]
            p1_colors = tournament.get_player_colors(p1.id)
            p1_last = p1_colors[-1] if p1_colors else None
            
            # Try all candidates in S2
            candidates = []
            for s2_idx in range(len(s2)):
                if s2_idx in used_s2_idx:
                    continue
                p2 = s2[s2_idx]
                if tournament.have_played(p1.id, p2.id):
                    continue
                if _have_absolute_color_conflict(tournament, p1, p2):
                    continue
                
                p2_colors = tournament.get_player_colors(p2.id)
                p2_last = p2_colors[-1] if p2_colors else None
                color_compat = 1 if p1_last and p2_last and p1_last != p2_last else 0
                candidates.append((color_compat, s2_idx, p2))
            
            # Sort by color compatibility, then original S2 order
            candidates.sort(key=lambda x: (-x[0], x[1]))
            
            for _, s2_idx, p2 in candidates:
                used_s2_idx.add(s2_idx)
                pairings_found.append((p1, p2, s2_idx))
                if solve_bracket(s1_idx + 1, used_s2_idx):
                    return True
                # Backtrack
                pairings_found.pop()
                used_s2_idx.remove(s2_idx)
            
            return False

        current_used_s2 = set()
        if solve_bracket(0, current_used_s2):
            # Perfect! Everyone in S1 is paired.
            for p1, p2, s2_idx in pairings_found:
                white_id, black_id = _assign_colors(tournament, p1, p2)
                matches.append(Match(board=board_num, white_id=white_id, black_id=black_id))
                board_num += 1
            
            # Leftover in S2 (if odd) floats down
            for s2_idx in range(len(s2)):
                if s2_idx not in current_used_s2:
                    floaters.append(s2[s2_idx])
        else:
            # Fallback: If no perfect pairing exists, use greedy and float the unpaired
            paired_s1 = set()
            paired_s2 = set()
            for s1_idx, p1 in enumerate(s1):
                found = False
                for s2_idx, p2 in enumerate(s2):
                    if s2_idx in paired_s2: continue
                    if not tournament.have_played(p1.id, p2.id) and not _have_absolute_color_conflict(tournament, p1, p2):
                        w, b = _assign_colors(tournament, p1, p2)
                        matches.append(Match(board=board_num, white_id=w, black_id=b))
                        board_num += 1
                        paired_s1.add(s1_idx)
                        paired_s2.add(s2_idx)
                        found = True
                        break
                if not found:
                    floaters.append(p1)
            
            for s2_idx in range(len(s2)):
                if s2_idx not in paired_s2:
                    floaters.append(s2[s2_idx])

    # Final cleanup for remaining floaters
    if len(floaters) >= 2:
        floaters.sort(key=lambda p: (-scores.get(p.id, 0), -p.rating))
        remaining = list(floaters)
        floaters = []
        
        while len(remaining) >= 2:
            p1 = remaining.pop(0)
            found = False
            for i, cand in enumerate(remaining):
                if not tournament.have_played(p1.id, cand.id):
                    p2 = remaining.pop(i)
                    w, b = _assign_colors(tournament, p1, p2)
                    matches.append(Match(board=board_num, white_id=w, black_id=b))
                    board_num += 1
                    found = True
                    break
            
            if not found:
                # Last resort: pair even if they played before
                if remaining:
                    p2 = remaining.pop(0)
                    w, b = _assign_colors(tournament, p1, p2)
                    matches.append(Match(board=board_num, white_id=w, black_id=b))
                    board_num += 1

    return matches


def _have_absolute_color_conflict(tournament: Tournament, p1: Player, p2: Player) -> bool:
    """Check if two players have an absolute color conflict (both MUST have the same color)."""
    colors1 = tournament.get_player_colors(p1.id)
    colors2 = tournament.get_player_colors(p2.id)
    
    limit1 = _get_absolute_color_need(colors1)
    limit2 = _get_absolute_color_need(colors2)
    
    # Conflict only if both absolutely need the same color
    return limit1 is not None and limit1 == limit2


def _get_absolute_color_need(colors: list[str]) -> str | None:
    """Returns 'W' or 'B' if the player MUST have that color, None otherwise."""
    if not colors:
        return None
    
    # Rule: two same colors in a row -> must alternate
    if len(colors) >= 2 and colors[-1] == colors[-2]:
        return "B" if colors[-1] == "W" else "W"
    
    # Rule: two more of one color than the other
    w_count = colors.count("W")
    b_count = colors.count("B")
    if w_count - b_count >= 2:
        return "B"
    if b_count - w_count >= 2:
        return "W"
    
    return None


def _assign_colors(tournament: Tournament, p1: Player, p2: Player) -> tuple[str, str]:
    """Assign white/black colors based on strict alternation rules.
    
    Priority:
    1. Absolute need (2 same colors in a row, or 2+ color difference)
    2. Strong preference (last color played -> alternate)
    3. Color balance (equalize W/B count)
    4. Higher-rated player gets white (tiebreaker)
    """
    colors1 = tournament.get_player_colors(p1.id)
    colors2 = tournament.get_player_colors(p2.id)

    need1 = _get_absolute_color_need(colors1)
    need2 = _get_absolute_color_need(colors2)

    # If one has absolute need, satisfy it
    if need1 == "W" and need2 != "W":
        return p1.id, p2.id  # p1 white
    if need1 == "B" and need2 != "B":
        return p2.id, p1.id  # p1 black
    if need2 == "W" and need1 != "W":
        return p2.id, p1.id  # p2 white
    if need2 == "B" and need1 != "B":
        return p1.id, p2.id  # p2 black

    # Both have same absolute need (shouldn't happen if conflict check passed)
    # or neither has absolute need -> use preferences
    
    pref1 = _get_color_preference(colors1)
    pref2 = _get_color_preference(colors2)

    # Opposite preferences -> easy
    if pref1 > 0 and pref2 < 0:
        return p1.id, p2.id  # p1 wants white, p2 wants black
    if pref1 < 0 and pref2 > 0:
        return p2.id, p1.id  # p2 wants white, p1 wants black

    # One has preference, other is neutral
    if pref1 > 0 and pref2 == 0:
        return p1.id, p2.id
    if pref1 < 0 and pref2 == 0:
        return p2.id, p1.id
    if pref2 > 0 and pref1 == 0:
        return p2.id, p1.id
    if pref2 < 0 and pref1 == 0:
        return p1.id, p2.id

    # Both same preference or both neutral -> use last color to decide
    # Give white to the player who last played black (for alternation)
    if colors1 and colors2:
        if colors1[-1] == "B" and colors2[-1] == "W":
            return p1.id, p2.id  # p1 last played B, give W
        if colors1[-1] == "W" and colors2[-1] == "B":
            return p2.id, p1.id  # p2 last played B, give W
    
    # If both have the SAME preference, higher-rated player gets their preference
    if pref1 > 0 and pref2 > 0:
        if p1.rating >= p2.rating:
            return p1.id, p2.id  # p1 wants White and gets White
        return p2.id, p1.id
        
    if pref1 < 0 and pref2 < 0:
        if p1.rating >= p2.rating:
            return p2.id, p1.id  # p1 wants Black and gets Black
        return p1.id, p2.id

    # If both are neutral (Round 1), randomize to avoid all S1 players getting same color
    if not colors1 and not colors2:
        if random.random() < 0.5:
            return p1.id, p2.id
        return p2.id, p1.id

    # If still tied (both neutral/same pref in later rounds), higher-rated gets white
    if p1.rating >= p2.rating:
        return p1.id, p2.id  # higher-rated p1 gets white
    return p2.id, p1.id  # higher-rated p2 gets white


def _get_color_preference(colors: list[str]) -> int:
    """Returns color preference score.
    Positive = wants White, Negative = wants Black, 0 = neutral.
    """
    if not colors:
        return 0
    
    # Simple alternation: want the opposite of last color played
    last = colors[-1]
    if last == "W":
        return -1  # Want black
    else:
        return 1   # Want white


# ─── ROUND-ROBIN (BERGER TABLE) ─────────────────────────────────────────────

def _generate_round_robin_pairings(tournament: Tournament) -> Round | None:
    next_round = tournament.current_round + 1
    active = tournament.get_active_players()
    n = len(active)

    total_rounds = n - 1 if n % 2 == 0 else n
    if tournament.is_double_round_robin:
        total_rounds *= 2

    if next_round > total_rounds:
        return None

    players = list(active)
    if n % 2 == 1:
        bye_player_obj = Player(id="BYE", name="BYE", surname="")
        players.append(bye_player_obj)
        n += 1

    sorted_players = sorted(players, key=lambda p: (-p.rating, p.surname))
    player_ids = [p.id for p in sorted_players]

    effective_round = next_round
    swap_colors = False
    if tournament.is_double_round_robin and next_round > (n - 1):
        effective_round = next_round - (n - 1)
        swap_colors = True

    pairings = _berger_round(player_ids, effective_round)

    matches = []
    board = 1
    for w_id, b_id in pairings:
        if w_id == "BYE" or b_id == "BYE":
            real_id = w_id if b_id == "BYE" else b_id
            matches.append(Match(board=board, white_id=real_id, black_id="BYE", result=MatchResult.BYE))
        else:
            if swap_colors:
                w_id, b_id = b_id, w_id
            matches.append(Match(board=board, white_id=w_id, black_id=b_id))
        board += 1

    return Round(round_number=next_round, matches=matches)


def _berger_round(player_ids: list[str], round_num: int) -> list[tuple[str, str]]:
    """Generate Berger table pairings for a specific round."""
    n = len(player_ids)
    fixed = player_ids[0]
    rotating = list(player_ids[1:])

    for _ in range(round_num - 1):
        rotating = [rotating[-1]] + rotating[:-1]

    current = [fixed] + rotating
    pairs = []
    half = n // 2

    for i in range(half):
        p1 = current[i]
        p2 = current[n - 1 - i]
        if i == 0:
            if round_num % 2 == 0:
                pairs.append((p2, p1))
            else:
                pairs.append((p1, p2))
        else:
            if i % 2 == 0:
                pairs.append((p1, p2))
            else:
                pairs.append((p2, p1))

    return pairs


# ─── TEAM SWISS ──────────────────────────────────────────────────────────────

def _generate_team_swiss_pairings(tournament: Tournament) -> Round | None:
    """Team Swiss: pair teams by match points, then generate board pairings."""
    next_round = tournament.current_round + 1
    if next_round > tournament.num_rounds:
        return None

    teams = tournament.teams
    if len(teams) < 2:
        return None

    team_scores = {}
    for team in teams:
        team_scores[team.id] = _get_team_score(tournament, team.id)

    sorted_teams = sorted(teams, key=lambda t: (-team_scores[t.id], t.name))

    bye_team = None
    working_teams = list(sorted_teams)

    if len(working_teams) % 2 == 1:
        bye_team = working_teams.pop()

    matches = []
    board = 1

    for i in range(0, len(working_teams) - 1, 2):
        team_a = working_teams[i]
        team_b = working_teams[i + 1]

        max_boards = min(len(team_a.player_ids), len(team_b.player_ids))
        for b in range(max_boards):
            w_id = team_a.player_ids[b]
            b_id = team_b.player_ids[b]
            if i % 2 == 1:
                w_id, b_id = b_id, w_id
            matches.append(Match(board=board, white_id=w_id, black_id=b_id))
            board += 1

    if bye_team:
        for pid in bye_team.player_ids:
            matches.append(Match(board=board, white_id=pid, black_id="BYE", result=MatchResult.BYE))
            board += 1

    return Round(round_number=next_round, matches=matches)


def _get_team_score(tournament: Tournament, team_id: str) -> float:
    team = tournament.get_team_by_id(team_id)
    if not team:
        return 0.0
    total = 0.0
    for pid in team.player_ids:
        total += tournament.get_player_score(pid)
    return total


def swap_match_colors(match: Match) -> Match:
    """Swap white and black in a match (for manual adjustment)."""
    return Match(
        board=match.board,
        white_id=match.black_id,
        black_id=match.white_id,
        result=match.result
    )
