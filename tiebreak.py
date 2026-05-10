"""
FIDE C.07 Tie-Break calculations (effective 1 March 2026).
Supports full unplayed rounds management (Art.16) and all major tie-break types.
"""
from models import Tournament, TieBreakType, MatchResult, UnplayedCategory


def calculate_tiebreaks(tournament: Tournament, player_id: str) -> dict[TieBreakType, float]:
    results = {}
    for tb in tournament.tiebreak_order:
        results[tb] = _calc_single(tournament, player_id, tb)
    return results


def calculate_all_standings(tournament: Tournament) -> list[dict]:
    # Include all players so withdrawn players still appear in standings and cross table
    all_players = tournament.players
    standings = []
    for player in all_players:
        score = tournament.get_player_score(player.id)
        tiebreaks = calculate_tiebreaks(tournament, player.id)
        standings.append({"player": player, "score": score, "tiebreaks": tiebreaks})
    standings.sort(key=lambda x: _sort_key(x, tournament.tiebreak_order), reverse=True)
    for i, entry in enumerate(standings):
        entry["rank"] = i + 1
    return standings


def _sort_key(entry: dict, tiebreak_order: list[TieBreakType]) -> tuple:
    key = [entry["score"]]
    for tb in tiebreak_order:
        key.append(entry["tiebreaks"].get(tb, 0.0))
    return tuple(key)


_DISPATCH = {}  # filled after function definitions


def _calc_single(tournament: Tournament, player_id: str, tb_type: TieBreakType) -> float:
    fn = _DISPATCH.get(tb_type)
    return fn(tournament, player_id) if fn else 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS — Unplayed Rounds (Art.16)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_opponent_scores_art16(tournament: Tournament, player_id: str) -> list[dict]:
    """Get opponent contribution list for Buchholz family, respecting Art.16.
    Returns list of dicts: {score, is_dummy, is_vur, round_number}.
    """
    round_info = tournament.get_player_round_info(player_id)
    unplayed = dict(tournament.classify_unplayed_rounds(player_id))
    player_score = tournament.get_player_score(player_id)
    entries = []

    for entry in round_info:
        rnd_num = entry["round_number"]

        if rnd_num in unplayed:
            # Art.16.4: dummy opponent
            cat = unplayed[rnd_num]
            dummy = player_score
            if cat in (UnplayedCategory.FORFEIT_WIN, UnplayedCategory.FORFEIT_LOSS):
                opp_id = tournament.get_forfeit_scheduled_opponent(player_id, rnd_num)
                if opp_id:
                    adj = tournament.get_adjusted_score(opp_id)
                    dummy = min(dummy, adj)
            else:
                dummy = min(dummy, 0.5 * tournament.num_rounds)

            is_vur = cat in (UnplayedCategory.REQUESTED_BYE_ACTIVE,
                             UnplayedCategory.REQUESTED_BYE_TERMINAL,
                             UnplayedCategory.FORFEIT_LOSS)
            entries.append({"score": dummy, "is_dummy": True, "is_vur": is_vur, "round_number": rnd_num})
        elif entry["opponent_id"]:
            opp_score = tournament.get_adjusted_score(entry["opponent_id"])
            entries.append({"score": opp_score, "is_dummy": False, "is_vur": False, "round_number": rnd_num})

    return entries


# ═══════════════════════════════════════════════════════════════════════════════
# BUCHHOLZ FAMILY (Art.8, Type C)
# ═══════════════════════════════════════════════════════════════════════════════

def _buchholz(t: Tournament, pid: str) -> float:
    return sum(e["score"] for e in _get_opponent_scores_art16(t, pid))


def _buchholz_cut1(t: Tournament, pid: str) -> float:
    entries = _get_opponent_scores_art16(t, pid)
    if not entries:
        return 0.0
    return _apply_cut(entries, 1, cut_high=False)


def _buchholz_cut2(t: Tournament, pid: str) -> float:
    entries = _get_opponent_scores_art16(t, pid)
    if not entries:
        return 0.0
    return _apply_cut(entries, 2, cut_high=False)


def _buchholz_median1(t: Tournament, pid: str) -> float:
    entries = _get_opponent_scores_art16(t, pid)
    if len(entries) <= 2:
        return sum(e["score"] for e in entries)
    total = sum(e["score"] for e in entries)
    scores = sorted(entries, key=lambda e: e["score"])
    return total - scores[0]["score"] - scores[-1]["score"]


def _buchholz_median2(t: Tournament, pid: str) -> float:
    entries = _get_opponent_scores_art16(t, pid)
    if len(entries) <= 4:
        return sum(e["score"] for e in entries)
    total = sum(e["score"] for e in entries)
    scores = sorted(entries, key=lambda e: e["score"])
    return total - scores[0]["score"] - scores[1]["score"] - scores[-1]["score"] - scores[-2]["score"]


def _avg_opp_buchholz(t: Tournament, pid: str) -> float:
    """AOB: Average of opponents' Buchholz (Art.8.2). Only over-the-board opponents."""
    opponents = t.get_player_opponents(pid)
    if not opponents:
        return 0.0
    bh_scores = [_buchholz(t, opp_id) for opp_id, _, _ in opponents]
    return round(sum(bh_scores) / len(bh_scores), 1) if bh_scores else 0.0


def _fore_buchholz(t: Tournament, pid: str) -> float:
    """FB: Buchholz as if all final round games ended in draws (Art.8.3).
    Simplified: use regular Buchholz (exact implementation needs hypothetical scoring).
    """
    return _buchholz(t, pid)


def _apply_cut(entries: list[dict], n_cut: int, cut_high: bool = False) -> float:
    """Apply Cut modifier with VUR exception (Art.16.5).
    When cutting lowest: prefer VUR entries per Art.16.5.1.
    """
    total = sum(e["score"] for e in entries)
    sorted_entries = sorted(entries, key=lambda e: e["score"])

    if cut_high:
        sorted_entries = list(reversed(sorted_entries))

    cut_count = 0
    cut_sum = 0.0
    # Art.16.5.1: VUR entries should be cut first
    vur_entries = [e for e in sorted_entries if e["is_vur"]]
    non_vur_entries = [e for e in sorted_entries if not e["is_vur"]]

    # Cut VUR entries first (lowest among them)
    vur_sorted = sorted(vur_entries, key=lambda e: e["score"])
    for e in vur_sorted:
        if cut_count >= n_cut:
            break
        cut_sum += e["score"]
        cut_count += 1

    # If still need to cut more, cut from non-VUR
    if cut_count < n_cut:
        non_vur_sorted = sorted(non_vur_entries, key=lambda e: e["score"])
        for e in non_vur_sorted:
            if cut_count >= n_cut:
                break
            cut_sum += e["score"]
            cut_count += 1

    return total - cut_sum


# ═══════════════════════════════════════════════════════════════════════════════
# SONNEBORN-BERGER (Art.9.1, Type BC)
# ═══════════════════════════════════════════════════════════════════════════════

def _sonneborn_berger(t: Tournament, pid: str) -> float:
    """SB: Sum of (adjusted_opp_score × points_scored_vs_opponent)."""
    opponents = t.get_player_opponents(pid)
    sb = 0.0
    for opp_id, score_vs, color in opponents:
        opp_adj = t.get_adjusted_score(opp_id)
        sb += opp_adj * score_vs

    # Add dummy contributions for unplayed rounds
    unplayed = dict(t.classify_unplayed_rounds(pid))
    player_score = t.get_player_score(pid)
    round_info = t.get_player_round_info(pid)

    for entry in round_info:
        rnd_num = entry["round_number"]
        if rnd_num not in unplayed:
            continue
        cat = unplayed[rnd_num]
        dummy = player_score
        if cat in (UnplayedCategory.FORFEIT_WIN, UnplayedCategory.FORFEIT_LOSS):
            opp_id = t.get_forfeit_scheduled_opponent(pid, rnd_num)
            if opp_id:
                dummy = min(dummy, t.get_adjusted_score(opp_id))
        else:
            dummy = min(dummy, 0.5 * t.num_rounds)
        sb += dummy * entry["points_scored"]

    return sb


def _sonneborn_berger_cut1(t: Tournament, pid: str) -> float:
    """SB-C1: SB minus the contribution from the opponent with the lowest score."""
    opponents = t.get_player_opponents(pid)
    contributions = []
    for opp_id, score_vs, _ in opponents:
        opp_adj = t.get_adjusted_score(opp_id)
        contributions.append({"value": opp_adj * score_vs, "opp_score": opp_adj, "is_vur": False})

    unplayed = dict(t.classify_unplayed_rounds(pid))
    player_score = t.get_player_score(pid)
    round_info = t.get_player_round_info(pid)
    for entry in round_info:
        rnd_num = entry["round_number"]
        if rnd_num not in unplayed:
            continue
        cat = unplayed[rnd_num]
        dummy = player_score
        if cat in (UnplayedCategory.FORFEIT_WIN, UnplayedCategory.FORFEIT_LOSS):
            opp_id = t.get_forfeit_scheduled_opponent(pid, rnd_num)
            if opp_id:
                dummy = min(dummy, t.get_adjusted_score(opp_id))
        else:
            dummy = min(dummy, 0.5 * t.num_rounds)
        is_vur = cat in (UnplayedCategory.REQUESTED_BYE_ACTIVE,
                         UnplayedCategory.REQUESTED_BYE_TERMINAL,
                         UnplayedCategory.FORFEIT_LOSS)
        contributions.append({"value": dummy * entry["points_scored"], "opp_score": dummy, "is_vur": is_vur})

    if not contributions:
        return 0.0

    total = sum(c["value"] for c in contributions)
    # Art.16.5.1 for SB: cut higher of (lowest VUR contribution, lowest overall contribution)
    vur_contribs = [c for c in contributions if c["is_vur"]]
    min_overall = min(contributions, key=lambda c: c["opp_score"])

    if vur_contribs:
        min_vur = min(vur_contribs, key=lambda c: c["value"])
        cut_val = max(min_vur["value"], min_overall["value"])
    else:
        cut_val = min_overall["value"]

    return total - cut_val


# ═══════════════════════════════════════════════════════════════════════════════
# KOYA SYSTEM (Art.9.2, Type BC) — Round Robin only
# ═══════════════════════════════════════════════════════════════════════════════

def _koya(t: Tournament, pid: str) -> float:
    """KS: Points against opponents who scored ≥50% of max possible."""
    max_score = t.num_rounds  # in standard scoring: 1pt per round
    threshold = max_score * 0.5
    total = 0.0
    opponents = t.get_player_opponents(pid)
    for opp_id, score_vs, _ in opponents:
        opp_score = t.get_player_score(opp_id)
        if opp_score >= threshold:
            total += score_vs
    return total


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECT ENCOUNTER (Art.6, Type A)
# ═══════════════════════════════════════════════════════════════════════════════

def _direct_encounter(t: Tournament, pid: str) -> float:
    """DE: Score against players with the same total score.
    Art.6.1.1: forfeit results excluded unless tournament rules say otherwise.
    Art.6.1.2: if played more than once, use average.
    """
    player_score = t.get_player_score(pid)
    # Find all players with the same score
    same_score_ids = set()
    for p in t.get_active_players():
        if p.id != pid and abs(t.get_player_score(p.id) - player_score) < 0.001:
            same_score_ids.add(p.id)

    if not same_score_ids:
        return 0.0

    # Collect per-opponent results
    opp_results: dict[str, list[float]] = {}
    for rnd in t.rounds:
        if not rnd.is_completed:
            continue
        for match in rnd.matches:
            if match.is_bye or match.result.is_forfeit:  # Art.6.1.1: exclude forfeits
                continue
            if match.white_id == pid and match.black_id in same_score_ids:
                opp_results.setdefault(match.black_id, []).append(match.result.white_score)
            elif match.black_id == pid and match.white_id in same_score_ids:
                opp_results.setdefault(match.white_id, []).append(match.result.black_score)

    de = 0.0
    for opp_id, scores in opp_results.items():
        if len(scores) > 1:
            de += sum(scores) / len(scores)  # Art.6.1.2: average
        else:
            de += scores[0]
    return de


# ═══════════════════════════════════════════════════════════════════════════════
# TYPE B TIE-BREAKS (Art.7 — Participant's Own Record)
# ═══════════════════════════════════════════════════════════════════════════════

def _num_wins(t: Tournament, pid: str) -> float:
    """WIN (Art.7.1): Rounds where player obtains as many points as awarded for a win."""
    wins = 0.0
    for rnd in t.rounds:
        if not rnd.is_completed:
            continue
        for match in rnd.matches:
            if match.white_id == pid and match.result.white_score >= 1.0:
                wins += 1
            elif match.black_id == pid and match.result.black_score >= 1.0:
                wins += 1
    return wins


def _games_won(t: Tournament, pid: str) -> float:
    """WON (Art.7.2): Games won over the board."""
    wins = 0.0
    for rnd in t.rounds:
        if not rnd.is_completed:
            continue
        for match in rnd.matches:
            if not match.result.is_played:
                continue
            if match.white_id == pid and match.result == MatchResult.WHITE_WIN:
                wins += 1
            elif match.black_id == pid and match.result == MatchResult.BLACK_WIN:
                wins += 1
    return wins


def _black_played_games(t: Tournament, pid: str) -> float:
    """BPG (Art.7.3): Number of games played over the board with black pieces."""
    count = 0.0
    for rnd in t.rounds:
        if not rnd.is_completed:
            continue
        for match in rnd.matches:
            if not match.result.is_played:
                continue
            if match.black_id == pid:
                count += 1
    return count


def _black_wins(t: Tournament, pid: str) -> float:
    """BWG (Art.7.4): Games won over the board with black pieces."""
    wins = 0.0
    for rnd in t.rounds:
        if not rnd.is_completed:
            continue
        for match in rnd.matches:
            if not match.result.is_played:
                continue
            if match.black_id == pid and match.result == MatchResult.BLACK_WIN:
                wins += 1
    return wins


def _progressive_score(t: Tournament, pid: str) -> float:
    """PS (Art.7.5): Sum of cumulative scores after each round."""
    completed = sorted([r for r in t.rounds if r.is_completed], key=lambda r: r.round_number)
    ps = 0.0
    for rnd in completed:
        ps += t.get_player_score_after_round(pid, rnd.round_number)
    return ps


def _rounds_elected_play(t: Tournament, pid: str) -> float:
    """REP (Art.7.6): Rounds minus half-point-byes, zero-point-byes, and forfeit losses."""
    completed = [r for r in t.rounds if r.is_completed]
    total = len(completed)
    unplayed = dict(t.classify_unplayed_rounds(pid))
    deductions = 0
    for rnd_num, cat in unplayed.items():
        if cat in (UnplayedCategory.REQUESTED_BYE_ACTIVE, UnplayedCategory.REQUESTED_BYE_TERMINAL,
                   UnplayedCategory.FORFEIT_LOSS):
            deductions += 1
    return float(total - deductions)


def _standard_points(t: Tournament, pid: str) -> float:
    """STD (Art.7.7): Simplified — rounds scoring more than opponent + 0.5×draws."""
    std = 0.0
    for rnd in t.rounds:
        if not rnd.is_completed:
            continue
        for match in rnd.matches:
            if match.is_bye and match.white_id == pid:
                std += 1.0  # Bye = win equivalent
                break
            if match.white_id == pid:
                if match.result.is_played:
                    if match.result == MatchResult.WHITE_WIN:
                        std += 1.0
                    elif match.result == MatchResult.DRAW:
                        std += 0.5
                break
            elif match.black_id == pid:
                if match.result.is_played:
                    if match.result == MatchResult.BLACK_WIN:
                        std += 1.0
                    elif match.result == MatchResult.DRAW:
                        std += 0.5
                break
    return std


def _tournament_pairing_num(t: Tournament, pid: str) -> float:
    """TPN (Art.7.8): Negative pairing number (lower = better, sorted descending)."""
    return float(-t.get_player_pairing_number(pid))


# ═══════════════════════════════════════════════════════════════════════════════
# RATING-BASED (Art.10)
# ═══════════════════════════════════════════════════════════════════════════════

def _avg_rating_opp(t: Tournament, pid: str) -> float:
    """ARO (Art.10.1): Average rating of opponents played over the board."""
    opponents = t.get_player_opponents(pid)
    ratings = []
    for opp_id, _, _ in opponents:
        p = t.get_player_by_id(opp_id)
        if p and p.rating > 0:
            ratings.append(p.rating)
    if not ratings:
        return 0.0
    avg = sum(ratings) / len(ratings)
    return round(avg + 0.5 - (0.5 if avg == int(avg) else 0.0))  # 0.5 rounds up


def _avg_rating_opp_cut1(t: Tournament, pid: str) -> float:
    """ARO-C1: ARO excluding the lowest-rated opponent."""
    opponents = t.get_player_opponents(pid)
    ratings = []
    for opp_id, _, _ in opponents:
        p = t.get_player_by_id(opp_id)
        if p and p.rating > 0:
            ratings.append(p.rating)
    if len(ratings) <= 1:
        return sum(ratings) if ratings else 0.0
    ratings.sort()
    ratings = ratings[1:]  # cut lowest
    return round(sum(ratings) / len(ratings))


def _tournament_performance(t: Tournament, pid: str) -> float:
    """TPR (Art.10.2): ARO + RD(fractional score)."""
    opponents = t.get_player_opponents(pid)
    if not opponents:
        return 0.0
    ratings, total_score, games = [], 0.0, 0
    for opp_id, score_vs, _ in opponents:
        p = t.get_player_by_id(opp_id)
        if p and p.rating > 0:
            ratings.append(p.rating)
            total_score += score_vs
            games += 1
    if not ratings or games == 0:
        return 0.0
    aro = sum(ratings) / len(ratings)
    percentage = total_score / games
    return round(aro + _percentage_to_rd(percentage))


def _rating_tiebreak(t: Tournament, pid: str) -> float:
    """RTNG (Art.10.6): Player's own rating."""
    p = t.get_player_by_id(pid)
    return float(p.rating) if p else 0.0


def _percentage_to_rd(percentage: float) -> float:
    """Convert scoring percentage to rating difference (FIDE conversion table)."""
    _TABLE = [
        (1.00, 800), (0.99, 677), (0.98, 589), (0.97, 538), (0.96, 501),
        (0.95, 470), (0.94, 444), (0.93, 422), (0.92, 401), (0.91, 383),
        (0.90, 366), (0.89, 351), (0.88, 336), (0.87, 322), (0.86, 309),
        (0.85, 296), (0.84, 284), (0.83, 273), (0.82, 262), (0.81, 251),
        (0.80, 240), (0.79, 230), (0.78, 220), (0.77, 211), (0.76, 202),
        (0.75, 193), (0.74, 184), (0.73, 175), (0.72, 166), (0.71, 158),
        (0.70, 149), (0.69, 141), (0.68, 133), (0.67, 125), (0.66, 117),
        (0.65, 110), (0.64, 102), (0.63, 95), (0.62, 87), (0.61, 80),
        (0.60, 72), (0.59, 65), (0.58, 57), (0.57, 50), (0.56, 43),
        (0.55, 36), (0.54, 29), (0.53, 21), (0.52, 14), (0.51, 7),
        (0.50, 0),
        (0.49, -7), (0.48, -14), (0.47, -21), (0.46, -29), (0.45, -36),
        (0.44, -43), (0.43, -50), (0.42, -57), (0.41, -65), (0.40, -72),
        (0.39, -80), (0.38, -87), (0.37, -95), (0.36, -102), (0.35, -110),
        (0.34, -117), (0.33, -125), (0.32, -133), (0.31, -141), (0.30, -149),
        (0.29, -158), (0.28, -166), (0.27, -175), (0.26, -184), (0.25, -193),
        (0.24, -202), (0.23, -211), (0.22, -220), (0.21, -230), (0.20, -240),
        (0.19, -251), (0.18, -262), (0.17, -273), (0.16, -284), (0.15, -296),
        (0.14, -309), (0.13, -322), (0.12, -336), (0.11, -351), (0.10, -366),
        (0.09, -383), (0.08, -401), (0.07, -422), (0.06, -444), (0.05, -470),
        (0.04, -501), (0.03, -538), (0.02, -589), (0.01, -677), (0.00, -800),
    ]
    closest = min(_TABLE, key=lambda x: abs(x[0] - percentage))
    return closest[1]


# ═══════════════════════════════════════════════════════════════════════════════
# DISPATCH TABLE
# ═══════════════════════════════════════════════════════════════════════════════

_DISPATCH = {
    TieBreakType.BUCHHOLZ: _buchholz,
    TieBreakType.BUCHHOLZ_CUT1: _buchholz_cut1,
    TieBreakType.BUCHHOLZ_CUT2: _buchholz_cut2,
    TieBreakType.BUCHHOLZ_MEDIAN1: _buchholz_median1,
    TieBreakType.BUCHHOLZ_MEDIAN2: _buchholz_median2,
    TieBreakType.AVG_OPP_BUCHHOLZ: _avg_opp_buchholz,
    TieBreakType.FORE_BUCHHOLZ: _fore_buchholz,
    TieBreakType.SONNEBORN_BERGER: _sonneborn_berger,
    TieBreakType.SONNEBORN_BERGER_CUT1: _sonneborn_berger_cut1,
    TieBreakType.KOYA: _koya,
    TieBreakType.DIRECT_ENCOUNTER: _direct_encounter,
    TieBreakType.NUM_WINS: _num_wins,
    TieBreakType.GAMES_WON: _games_won,
    TieBreakType.BLACK_PLAYED_GAMES: _black_played_games,
    TieBreakType.BLACK_WINS: _black_wins,
    TieBreakType.PROGRESSIVE_SCORE: _progressive_score,
    TieBreakType.ROUNDS_ELECTED_PLAY: _rounds_elected_play,
    TieBreakType.STANDARD_POINTS: _standard_points,
    TieBreakType.TOURNAMENT_PAIRING_NUM: _tournament_pairing_num,
    TieBreakType.AVG_RATING_OPP: _avg_rating_opp,
    TieBreakType.AVG_RATING_OPP_CUT1: _avg_rating_opp_cut1,
    TieBreakType.TOURNAMENT_PERFORMANCE: _tournament_performance,
    TieBreakType.RATING: _rating_tiebreak,
}
