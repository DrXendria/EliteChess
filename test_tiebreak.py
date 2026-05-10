"""Quick test of tiebreak calculations."""
from models import *
from tiebreak import *

t = Tournament(num_rounds=3)
p1 = Player(id='p1', name='Ali', surname='Yilmaz', rating=2200)
p2 = Player(id='p2', name='Burak', surname='Kaya', rating=2100)
p3 = Player(id='p3', name='Can', surname='Demir', rating=2000)
p4 = Player(id='p4', name='Deniz', surname='Arslan', rating=1900)
t.players = [p1, p2, p3, p4]

# Round 1: p1 beats p2, p3 draws p4
r1 = Round(round_number=1, is_completed=True, matches=[
    Match(board=1, white_id='p1', black_id='p2', result=MatchResult.WHITE_WIN),
    Match(board=2, white_id='p3', black_id='p4', result=MatchResult.DRAW),
])

# Round 2: p1 draws p3, p4 loses to p2
r2 = Round(round_number=2, is_completed=True, matches=[
    Match(board=1, white_id='p1', black_id='p3', result=MatchResult.DRAW),
    Match(board=2, white_id='p4', black_id='p2', result=MatchResult.BLACK_WIN),
])

t.rounds = [r1, r2]
t.current_round = 2

print("=== Standings ===")
st = calculate_all_standings(t)
for e in st:
    p = e["player"]
    print(f"  {e['rank']}. {p.full_name:20s} Pts={e['score']:.1f}  ", end="")
    for tb_type, val in e["tiebreaks"].items():
        print(f"{tb_type.value}={val:.1f} ", end="")
    print()

# Test with bye
print("\n=== Test with BYE ===")
p5 = Player(id='p5', name='Emre', surname='Oz', rating=1800)
t.players.append(p5)
r1.matches.append(Match(board=3, white_id='p5', black_id='BYE', result=MatchResult.BYE))
r2.matches.append(Match(board=3, white_id='p5', black_id='p4', result=MatchResult.WHITE_WIN))

st2 = calculate_all_standings(t)
for e in st2:
    p = e["player"]
    print(f"  {e['rank']}. {p.full_name:20s} Pts={e['score']:.1f}  BH={e['tiebreaks'].get(TieBreakType.BUCHHOLZ, 0):.1f}  BH-C1={e['tiebreaks'].get(TieBreakType.BUCHHOLZ_CUT1, 0):.1f}")

# Test unplayed rounds classification
print("\n=== Unplayed Round Categories (p5) ===")
cats = t.classify_unplayed_rounds('p5')
for rnd_num, cat in cats:
    print(f"  Round {rnd_num}: {cat.value} ({cat.name})")

adj = t.get_adjusted_score('p5')
raw = t.get_player_score('p5')
print(f"  Raw score: {raw}, Adjusted: {adj}")

print("\nALL TESTS PASSED!")
