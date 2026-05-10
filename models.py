"""
Data models for Swiss Chess Tournament Manager.
Updated for FIDE C.07 (effective 1 March 2026).
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
import uuid


class TournamentType(Enum):
    SWISS = "swiss"
    ROUND_ROBIN = "round_robin"
    TEAM_SWISS = "team_swiss"


class MatchResult(Enum):
    NONE = "none"
    WHITE_WIN = "1-0"
    BLACK_WIN = "0-1"
    DRAW = "1/2-1/2"
    WHITE_FORFEIT = "0-1f"       # White loses by forfeit
    BLACK_FORFEIT = "1-0f"       # Black loses by forfeit (White wins by forfeit)
    DOUBLE_FORFEIT = "0-0f"
    BYE = "bye"                  # Pairing-allocated bye (full point)
    HALF_POINT_BYE = "bye_half"  # Requested half-point bye
    ZERO_POINT_BYE = "bye_zero"  # Requested zero-point bye / withdrawal round

    @property
    def white_score(self) -> float:
        scores = {
            MatchResult.NONE: 0.0,
            MatchResult.WHITE_WIN: 1.0,
            MatchResult.BLACK_WIN: 0.0,
            MatchResult.DRAW: 0.5,
            MatchResult.WHITE_FORFEIT: 0.0,
            MatchResult.BLACK_FORFEIT: 1.0,
            MatchResult.DOUBLE_FORFEIT: 0.0,
            MatchResult.BYE: 1.0,
            MatchResult.HALF_POINT_BYE: 0.5,
            MatchResult.ZERO_POINT_BYE: 0.0,
        }
        return scores[self]

    @property
    def black_score(self) -> float:
        scores = {
            MatchResult.NONE: 0.0,
            MatchResult.WHITE_WIN: 0.0,
            MatchResult.BLACK_WIN: 1.0,
            MatchResult.DRAW: 0.5,
            MatchResult.WHITE_FORFEIT: 1.0,
            MatchResult.BLACK_FORFEIT: 0.0,
            MatchResult.DOUBLE_FORFEIT: 0.0,
            MatchResult.BYE: 0.0,
            MatchResult.HALF_POINT_BYE: 0.0,
            MatchResult.ZERO_POINT_BYE: 0.0,
        }
        return scores[self]

    @property
    def is_played(self) -> bool:
        """Game was actually played over the board."""
        return self in (MatchResult.WHITE_WIN, MatchResult.BLACK_WIN, MatchResult.DRAW)

    @property
    def is_forfeit(self) -> bool:
        return self in (MatchResult.WHITE_FORFEIT, MatchResult.BLACK_FORFEIT, MatchResult.DOUBLE_FORFEIT)

    @property
    def is_forfeit_win(self) -> bool:
        """One side won by forfeit (FIDE Art.16.2.2)."""
        return self in (MatchResult.BLACK_FORFEIT, MatchResult.WHITE_FORFEIT)

    @property
    def is_forfeit_loss(self) -> bool:
        """One side lost by forfeit (FIDE Art.16.2.4)."""
        return self in (MatchResult.WHITE_FORFEIT, MatchResult.BLACK_FORFEIT, MatchResult.DOUBLE_FORFEIT)

    @property
    def is_bye(self) -> bool:
        return self in (MatchResult.BYE, MatchResult.HALF_POINT_BYE, MatchResult.ZERO_POINT_BYE)

    @property
    def is_requested_bye(self) -> bool:
        """Half-point or zero-point bye requested by player (FIDE Art.16.1.1)."""
        return self in (MatchResult.HALF_POINT_BYE, MatchResult.ZERO_POINT_BYE)

    @property
    def is_decided(self) -> bool:
        return self != MatchResult.NONE

    @property
    def is_unplayed(self) -> bool:
        """Round where no game was played (FIDE Art.15.1)."""
        return self in (
            MatchResult.WHITE_FORFEIT, MatchResult.BLACK_FORFEIT,
            MatchResult.DOUBLE_FORFEIT,
            MatchResult.BYE, MatchResult.HALF_POINT_BYE, MatchResult.ZERO_POINT_BYE,
        )


class Title(Enum):
    NONE = ""
    GM = "GM"
    IM = "IM"
    FM = "FM"
    CM = "CM"
    WGM = "WGM"
    WIM = "WIM"
    WFM = "WFM"
    WCM = "WCM"
    NM = "NM"


class TieBreakType(Enum):
    # ── Buchholz family (Type C) ──
    BUCHHOLZ = "BH"
    BUCHHOLZ_CUT1 = "BH-C1"
    BUCHHOLZ_CUT2 = "BH-C2"
    BUCHHOLZ_MEDIAN1 = "BH-M1"
    BUCHHOLZ_MEDIAN2 = "BH-M2"
    AVG_OPP_BUCHHOLZ = "AOB"
    FORE_BUCHHOLZ = "FB"

    # ── Participant + Opponent based (Type BC) ──
    SONNEBORN_BERGER = "SB"
    SONNEBORN_BERGER_CUT1 = "SB-C1"
    KOYA = "KS"

    # ── Direct Encounter (Type A) ──
    DIRECT_ENCOUNTER = "DE"

    # ── Participant's own record (Type B) ──
    NUM_WINS = "WIN"
    GAMES_WON = "WON"
    BLACK_PLAYED_GAMES = "BPG"
    BLACK_WINS = "BWG"
    PROGRESSIVE_SCORE = "PS"
    ROUNDS_ELECTED_PLAY = "REP"
    STANDARD_POINTS = "STD"
    TOURNAMENT_PAIRING_NUM = "TPN"

    # ── Rating-based (Type D/DB) ──
    AVG_RATING_OPP = "ARO"
    AVG_RATING_OPP_CUT1 = "ARO-C1"
    TOURNAMENT_PERFORMANCE = "TPR"
    RATING = "RTNG"

    @property
    def display_name(self) -> str:
        names = {
            TieBreakType.BUCHHOLZ: "Buchholz",
            TieBreakType.BUCHHOLZ_CUT1: "Buchholz Cut-1",
            TieBreakType.BUCHHOLZ_CUT2: "Buchholz Cut-2",
            TieBreakType.BUCHHOLZ_MEDIAN1: "Buchholz Median-1",
            TieBreakType.BUCHHOLZ_MEDIAN2: "Buchholz Median-2",
            TieBreakType.AVG_OPP_BUCHHOLZ: "Ort. Rakip Buchholz",
            TieBreakType.FORE_BUCHHOLZ: "Fore Buchholz",
            TieBreakType.SONNEBORN_BERGER: "Sonneborn-Berger",
            TieBreakType.SONNEBORN_BERGER_CUT1: "Sonneborn-Berger Cut-1",
            TieBreakType.KOYA: "Koya Sistemi",
            TieBreakType.DIRECT_ENCOUNTER: "Kişisel Karşılaşma",
            TieBreakType.NUM_WINS: "Galibiyet Sayısı",
            TieBreakType.GAMES_WON: "Masa Başı Galibiyet",
            TieBreakType.BLACK_PLAYED_GAMES: "Siyah Oynanan Maç",
            TieBreakType.BLACK_WINS: "Siyah Galibiyet",
            TieBreakType.PROGRESSIVE_SCORE: "Kümülatif Puan",
            TieBreakType.ROUNDS_ELECTED_PLAY: "Oynamayı Seçilen Turlar",
            TieBreakType.STANDARD_POINTS: "Standart Puan",
            TieBreakType.TOURNAMENT_PAIRING_NUM: "Eşleştirme Numarası",
            TieBreakType.AVG_RATING_OPP: "Ort. Rakip Rating",
            TieBreakType.AVG_RATING_OPP_CUT1: "Ort. Rakip Rating Cut-1",
            TieBreakType.TOURNAMENT_PERFORMANCE: "Performans Rating",
            TieBreakType.RATING: "Rating",
        }
        return names.get(self, self.value)


TSF_2025_DEFAULT_TIEBREAKS = [
    TieBreakType.BUCHHOLZ_CUT1,
    TieBreakType.BUCHHOLZ,
    TieBreakType.SONNEBORN_BERGER,
    TieBreakType.DIRECT_ENCOUNTER,
    TieBreakType.NUM_WINS,
    TieBreakType.BLACK_WINS,
]


@dataclass
class Player:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    surname: str = ""
    rating: int = 0
    ukd: int = 0
    elo: int = 0
    title: Title = Title.NONE
    club: str = ""
    birth_year: int = 0
    fide_id: str = ""
    team_id: str = ""
    is_active: bool = True
    is_registered: bool = False
    withdrawn_after_round: int = 0  # 0 = not withdrawn; >0 = last round played

    def update_rating(self):
        max_val = max(self.ukd, self.elo)
        if max_val > 0:
            self.rating = max_val


    @property
    def full_name(self) -> str:
        return f"{self.surname}, {self.name}".strip(", ")

    @property
    def display_title(self) -> str:
        return self.title.value if self.title != Title.NONE else ""


@dataclass
class Team:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    player_ids: list[str] = field(default_factory=list)


@dataclass
class Match:
    board: int = 0
    white_id: str = ""
    black_id: str = ""
    result: MatchResult = MatchResult.NONE

    @property
    def is_bye(self) -> bool:
        return self.result.is_bye or self.black_id == "BYE"


@dataclass
class Round:
    round_number: int = 0
    matches: list[Match] = field(default_factory=list)
    is_completed: bool = False


# ─── Unplayed Round Category (FIDE C.07 Art.16.2) ───────────────────────────

class UnplayedCategory(Enum):
    """FIDE Art.16.2 categories for unplayed rounds."""
    PAIRING_BYE = "16.2.1"       # Pairing-allocated bye or full-point bye
    FORFEIT_WIN = "16.2.2"       # Forfeit win
    REQUESTED_BYE_ACTIVE = "16.2.3"  # Requested bye followed by ≥1 non-VUR
    FORFEIT_LOSS = "16.2.4"      # Forfeit loss
    REQUESTED_BYE_TERMINAL = "16.2.5"  # Requested bye followed only by VURs or last round


@dataclass
class Tournament:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Yeni Turnuva"
    tournament_type: TournamentType = TournamentType.SWISS
    date: str = ""
    location: str = ""
    arbiter: str = ""
    num_rounds: int = 7
    players: list[Player] = field(default_factory=list)
    teams: list[Team] = field(default_factory=list)
    rounds: list[Round] = field(default_factory=list)
    current_round: int = 0
    tiebreak_order: list[TieBreakType] = field(default_factory=lambda: list(TSF_2025_DEFAULT_TIEBREAKS))
    is_double_round_robin: bool = False

    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def get_team_by_id(self, team_id: str) -> Optional[Team]:
        for t in self.teams:
            if t.id == team_id:
                return t
        return None

    def get_player_score(self, player_id: str) -> float:
        score = 0.0
        for rnd in self.rounds:
            if not rnd.is_completed:
                continue
            for match in rnd.matches:
                if match.white_id == player_id:
                    score += match.result.white_score
                elif match.black_id == player_id:
                    score += match.result.black_score
        return score

    def get_player_opponents(self, player_id: str) -> list[tuple[str, float, str]]:
        """Returns list of (opponent_id, score_vs_opponent, color) for all rounds."""
        opponents = []
        for rnd in self.rounds:
            if not rnd.is_completed:
                continue
            for match in rnd.matches:
                if match.is_bye and match.white_id == player_id:
                    continue
                if match.white_id == player_id and match.black_id != "BYE":
                    opponents.append((match.black_id, match.result.white_score, "W"))
                elif match.black_id == player_id:
                    opponents.append((match.white_id, match.result.black_score, "B"))
        return opponents

    def have_played(self, player1_id: str, player2_id: str) -> bool:
        for rnd in self.rounds:
            for match in rnd.matches:
                if (match.white_id == player1_id and match.black_id == player2_id) or \
                   (match.white_id == player2_id and match.black_id == player1_id):
                    # FIDE Rule: Only games actually played over the board prevent a rematch.
                    # If the previous encounter was a forfeit (hükmen), they CAN play again.
                    if match.result.is_played:
                        return True
        return False

    def get_player_colors(self, player_id: str) -> list[str]:
        """Returns list of colors ('W' or 'B') for each completed round."""
        colors = []
        for rnd in self.rounds:
            if not rnd.is_completed:
                continue
            for match in rnd.matches:
                if match.is_bye:
                    continue
                if match.white_id == player_id:
                    colors.append("W")
                elif match.black_id == player_id:
                    colors.append("B")
        return colors

    def player_had_bye(self, player_id: str) -> bool:
        for rnd in self.rounds:
            for match in rnd.matches:
                if match.is_bye and match.white_id == player_id:
                    return True
        return False

    def get_active_players(self) -> list['Player']:
        return [p for p in self.players if p.is_active and p.is_registered]

    def get_player_score_after_round(self, player_id: str, round_num: int) -> float:
        score = 0.0
        for rnd in self.rounds:
            if rnd.round_number > round_num or not rnd.is_completed:
                continue
            for match in rnd.matches:
                if match.white_id == player_id:
                    score += match.result.white_score
                elif match.black_id == player_id:
                    score += match.result.black_score
        return score

    # ─── FIDE C.07 Art.16: Unplayed Rounds Management ────────────────────

    def get_player_round_info(self, player_id: str) -> list[dict]:
        """Get detailed per-round info for a player.
        Returns list of dicts with keys: round_number, match, result, is_unplayed,
        opponent_id, points_scored, category (UnplayedCategory or None).
        """
        info = []
        completed_rounds = [r for r in self.rounds if r.is_completed]
        completed_rounds.sort(key=lambda r: r.round_number)

        for rnd in completed_rounds:
            entry = {
                "round_number": rnd.round_number,
                "match": None,
                "result": MatchResult.NONE,
                "is_unplayed": False,
                "opponent_id": None,
                "points_scored": 0.0,
                "category": None,
            }
            found = False
            for match in rnd.matches:
                if match.white_id == player_id:
                    entry["match"] = match
                    entry["result"] = match.result
                    entry["points_scored"] = match.result.white_score
                    entry["opponent_id"] = match.black_id if match.black_id != "BYE" else None
                    entry["is_unplayed"] = match.result.is_unplayed
                    found = True
                    break
                elif match.black_id == player_id:
                    entry["match"] = match
                    entry["result"] = match.result
                    entry["points_scored"] = match.result.black_score
                    entry["opponent_id"] = match.white_id
                    entry["is_unplayed"] = match.result.is_unplayed
                    found = True
                    break

            if not found:
                # Player was not paired this round (possibly withdrawn)
                entry["is_unplayed"] = True
                entry["result"] = MatchResult.ZERO_POINT_BYE
                entry["points_scored"] = 0.0

            info.append(entry)

        return info

    def classify_unplayed_rounds(self, player_id: str) -> list[tuple[int, 'UnplayedCategory']]:
        """Classify each unplayed round per FIDE Art.16.2.
        Returns list of (round_number, UnplayedCategory).
        """
        round_info = self.get_player_round_info(player_id)
        results = []

        for i, entry in enumerate(round_info):
            if not entry["is_unplayed"]:
                continue

            result = entry["result"]
            rnd_num = entry["round_number"]

            # 16.2.1: Pairing-allocated bye (full-point bye)
            if result == MatchResult.BYE:
                results.append((rnd_num, UnplayedCategory.PAIRING_BYE))

            # 16.2.2: Forfeit win
            elif result == MatchResult.BLACK_FORFEIT and entry.get("match") and entry["match"].white_id == player_id:
                results.append((rnd_num, UnplayedCategory.FORFEIT_WIN))
            elif result == MatchResult.WHITE_FORFEIT and entry.get("match") and entry["match"].black_id == player_id:
                results.append((rnd_num, UnplayedCategory.FORFEIT_WIN))

            # 16.2.4: Forfeit loss
            elif result == MatchResult.WHITE_FORFEIT and entry.get("match") and entry["match"].white_id == player_id:
                results.append((rnd_num, UnplayedCategory.FORFEIT_LOSS))
            elif result == MatchResult.BLACK_FORFEIT and entry.get("match") and entry["match"].black_id == player_id:
                results.append((rnd_num, UnplayedCategory.FORFEIT_LOSS))
            elif result == MatchResult.DOUBLE_FORFEIT:
                results.append((rnd_num, UnplayedCategory.FORFEIT_LOSS))

            # 16.2.3 vs 16.2.5: Requested byes
            elif result.is_requested_bye or result == MatchResult.ZERO_POINT_BYE:
                # Check if followed by at least one non-VUR round
                has_future_played = False
                for j in range(i + 1, len(round_info)):
                    future = round_info[j]
                    if not future["is_unplayed"]:
                        has_future_played = True
                        break
                    # Also check if future unplayed is not a VUR
                    # VUR = requested bye or forfeit loss
                    fr = future["result"]
                    if not (fr.is_requested_bye or fr == MatchResult.ZERO_POINT_BYE or
                            fr == MatchResult.DOUBLE_FORFEIT or
                            (fr == MatchResult.WHITE_FORFEIT and future.get("match") and
                             future["match"].white_id == player_id) or
                            (fr == MatchResult.BLACK_FORFEIT and future.get("match") and
                             future["match"].black_id == player_id)):
                        has_future_played = True
                        break

                if has_future_played:
                    results.append((rnd_num, UnplayedCategory.REQUESTED_BYE_ACTIVE))
                else:
                    results.append((rnd_num, UnplayedCategory.REQUESTED_BYE_TERMINAL))

        return results

    def get_adjusted_score(self, player_id: str) -> float:
        """Calculate adjusted score for tie-break of opponents (FIDE Art.16.3).

        Unplayed rounds of categories 16.2.1-16.2.4: evaluated with the result
        corresponding to the awarded number of points.
        Category 16.2.5 (terminal requested bye): evaluated as draws.
        """
        round_info = self.get_player_round_info(player_id)
        unplayed = dict(self.classify_unplayed_rounds(player_id))

        adjusted = 0.0
        for entry in round_info:
            rnd_num = entry["round_number"]
            if rnd_num in unplayed:
                cat = unplayed[rnd_num]
                if cat == UnplayedCategory.REQUESTED_BYE_TERMINAL:
                    # Art.16.3.2: Evaluated as draws
                    adjusted += 0.5
                else:
                    # Art.16.3.1: Evaluated with the awarded points
                    adjusted += entry["points_scored"]
            else:
                adjusted += entry["points_scored"]

        return adjusted

    def get_forfeit_scheduled_opponent(self, player_id: str, round_num: int) -> Optional[str]:
        """Get the scheduled opponent in a forfeit round."""
        for rnd in self.rounds:
            if rnd.round_number != round_num:
                continue
            for match in rnd.matches:
                if match.white_id == player_id:
                    return match.black_id if match.black_id != "BYE" else None
                elif match.black_id == player_id:
                    return match.white_id
        return None

    def get_player_pairing_number(self, player_id: str) -> int:
        """Get 1-based pairing number (position in players list)."""
        for i, p in enumerate(self.players):
            if p.id == player_id:
                return i + 1
        return 0

    def is_vur(self, player_id: str, round_num: int) -> bool:
        """Check if a round is a Voluntary Unplayed Round for a player (Art.16.1.2)."""
        unplayed = dict(self.classify_unplayed_rounds(player_id))
        if round_num not in unplayed:
            return False
        cat = unplayed[round_num]
        return cat in (
            UnplayedCategory.REQUESTED_BYE_ACTIVE,
            UnplayedCategory.REQUESTED_BYE_TERMINAL,
            UnplayedCategory.FORFEIT_LOSS,
        )
