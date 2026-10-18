"""Comprehensive test suite for Elite Chess:
1. Player import (.nat, .csv) and column auto-mapping (verifying No != fide_id)
2. Live performance calculations (TPR, Live Rating, Delta, BYE/forfeit handling)
3. Web server API (/api/data) and HTML dashboard (/) endpoints
"""
import unittest
import json
import urllib.request
import threading
import time
import socket
from models import Tournament, Player, Match, MatchResult, Round
from tiebreak import TieBreakType
from web_server import LiveServerThread, _percentage_to_rd
from dialogs import PlayerListImportDialog


class TestPlayerImport(unittest.TestCase):
    def test_nat_file_reading_and_mapping(self):
        """Verify .nat parsing and ensure 'No' does NOT map to FIDE ID."""
        dlg = PlayerListImportDialog.__new__(PlayerListImportDialog)
        raw = dlg._read_nat("ornek_oyuncular.nat")
        self.assertEqual(len(raw), 10, "Should read 10 players from ornek_oyuncular.nat")
        
        # Verify first row
        first = raw[0]
        self.assertEqual(first.get("No"), "1")
        self.assertEqual(first.get("Soyad"), "Carlsen")
        self.assertEqual(first.get("Ad"), "Magnus")
        self.assertEqual(first.get("ELO"), "2830")
        self.assertEqual(first.get("Kulüp"), "Offerspill")
        
        # Test column mapping logic without Qt widgets
        file_cols = list(first.keys())
        mapping = {}
        for key, aliases in PlayerListImportDialog._ALIASES.items():
            matched_col = None
            # Exact
            for col in file_cols:
                col_lower = col.replace("İ", "i").replace("I", "ı").lower().strip()
                if col_lower in aliases:
                    matched_col = col
                    break
            # Fallback
            if not matched_col:
                for col in file_cols:
                    col_lower = col.replace("İ", "i").replace("I", "ı").lower().strip()
                    if key == "name" and "soy" in col_lower:
                        continue
                    if key == "fide_id" and "fide" not in col_lower:
                        continue
                    if col_lower in ["no", "sno", "sira", "sıra", "sn", "#", "nr", "numara"]:
                        continue
                    for alias in aliases:
                        if alias in col_lower or (len(col_lower) >= 3 and col_lower in alias):
                            matched_col = col
                            break
                    if matched_col:
                        break
            if matched_col:
                mapping[key] = matched_col
        
        print("\n[TEST] Auto-detected column mapping for NAT:")
        for k, v in mapping.items():
            print(f"  {k} -> {v}")
            
        self.assertEqual(mapping.get("name"), "Ad")
        self.assertEqual(mapping.get("surname"), "Soyad")
        self.assertEqual(mapping.get("elo"), "ELO")
        self.assertEqual(mapping.get("ukd"), "UKD")
        self.assertEqual(mapping.get("club"), "Kulüp")
        self.assertIsNone(mapping.get("fide_id"), "FIDE ID must NOT map to 'No' column!")


class TestLivePerformanceAndWebServer(unittest.TestCase):
    def setUp(self):
        # Create a tournament with 4 players
        self.t = Tournament(
            name="Live Performance Championship",
            num_rounds=3,
            tiebreak_order=[TieBreakType.DIRECT_ENCOUNTER, TieBreakType.BUCHHOLZ]
        )
        self.p1 = Player(name="Magnus", surname="Carlsen", rating=2800)
        self.p2 = Player(name="Hikaru", surname="Nakamura", rating=2780)
        self.p3 = Player(name="Fabiano", surname="Caruana", rating=2790)
        self.p4 = Player(name="Alireza", surname="Firouzja", rating=2750)
        for p in [self.p1, self.p2, self.p3, self.p4]:
            self.t.players.append(p)
            p.is_registered = True

        # Round 1:
        # Board 1: p1 (2800) vs p2 (2780) -> 1-0
        # Board 2: p3 (2790) vs p4 (2750) -> 1/2-1/2
        r1 = Round(round_number=1, is_completed=True)
        m1 = Match(board=1, white_id=self.p1.id, black_id=self.p2.id)
        m1.result = MatchResult.WHITE_WIN
        m2 = Match(board=2, white_id=self.p3.id, black_id=self.p4.id)
        m2.result = MatchResult.DRAW
        r1.matches = [m1, m2]
        self.t.rounds.append(r1)

        # Round 2:
        # Board 1: p1 (2800) vs p3 (2790) -> 1/2-1/2
        # Board 2: p4 (2750) vs BYE -> 1-0 (BYE)
        r2 = Round(round_number=2, is_completed=True)
        m3 = Match(board=1, white_id=self.p1.id, black_id=self.p3.id)
        m3.result = MatchResult.DRAW
        m4 = Match(board=2, white_id=self.p4.id, black_id="BYE")
        m4.result = MatchResult.BYE
        r2.matches = [m3, m4]
        self.t.rounds.append(r2)

    def test_tpr_lookup(self):
        """Verify FIDE Art. 10.2 dp lookup."""
        self.assertEqual(_percentage_to_rd(0.50), 0)
        self.assertEqual(_percentage_to_rd(1.00), 800)
        self.assertEqual(_percentage_to_rd(0.00), -800)
        self.assertGreater(_percentage_to_rd(0.75), 180)
        self.assertLess(_percentage_to_rd(0.25), -180)

    def test_web_server_endpoints(self):
        """Start web server on an ephemeral port and test / and /api/data."""
        # Find an available port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        sock.close()

        server_thread = LiveServerThread(self.t, port=port)
        server_thread.start()
        time.sleep(0.5)

        try:
            # 1. Test HTML Dashboard
            url_html = f"http://127.0.0.1:{port}/"
            with urllib.request.urlopen(url_html, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                html = resp.read().decode("utf-8")
                self.assertIn("Elite Chess Canlı Turnuva Takibi", html)
                self.assertIn("Canlı Rating", html)
                self.assertIn("Perf. (TPR)", html)
                self.assertIn("playerModal", html)
                self.assertIn("modal-content", html)

            # 2. Test JSON API
            url_api = f"http://127.0.0.1:{port}/api/data"
            with urllib.request.urlopen(url_api, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data["name"], "Live Performance Championship")
                self.assertEqual(len(data["standings"]), 4)

                # Check Magnus (p1):
                # Opponents: Nakamura (2780) -> Won (1.0)
                #            Caruana (2790) -> Draw (0.5)
                # Total score: 1.5 / 2 = 75%
                # ARO = (2780 + 2790) / 2 = 2785
                # dp(75%) = 193 (from FIDE table)
                # TPR = 2785 + 193 = 2978
                magnus = next(s for s in data["standings"] if s["id"] == self.p1.id)
                self.assertEqual(magnus["score"], 1.5)
                self.assertIsNotNone(magnus["perf"])
                self.assertTrue(2970 <= magnus["perf"] <= 2990, f"Expected TPR ~2978, got {magnus['perf']}")
                self.assertIsNotNone(magnus["delta"])
                self.assertGreater(magnus["delta"], 0, "Winning against 2780 and drawing 2790 must yield positive delta")
                self.assertEqual(magnus["live_rating"], round(2800 + magnus["delta"], 1))

                # Check matches breakdown for Magnus
                self.assertEqual(len(magnus["matches"]), 2)
                m1_info = magnus["matches"][0]
                self.assertEqual(m1_info["opponent"], "Nakamura, Hikaru")
                self.assertEqual(m1_info["color"], "W")
                self.assertEqual(m1_info["result"], "1")
                self.assertTrue(m1_info["delta_r"].startswith("+"))

                # Check Firouzja (p4) who had a BYE in Round 2:
                # BYE must NOT be counted as a rated opponent!
                firouzja = next(s for s in data["standings"] if s["id"] == self.p4.id)
                self.assertEqual(len(firouzja["matches"]), 2)
                bye_match = firouzja["matches"][1]
                self.assertEqual(bye_match["opponent"], "BYE")
                self.assertEqual(bye_match["delta_r"], "—")
                self.assertIsNone(bye_match["delta_val"])
                # Rated games = 1 (against Caruana 2790, draw)
                # Score = 0.5 / 1 = 50%
                # TPR = 2790 + 0 = 2790
                self.assertEqual(firouzja["perf"], 2790)

                print("\n[TEST] Verified Live Performance API response:")
                print(f"  Magnus: Score={magnus['score']}, ARO~2785, TPR={magnus['perf']}, ΔR={magnus['delta']}, Live={magnus['live_rating']}")
                print(f"  Firouzja (with BYE): Score={firouzja['score']}, TPR={firouzja['perf']}, ΔR={firouzja['delta']}, Live={firouzja['live_rating']}")

        finally:
            server_thread.stop()
            server_thread.join(2.0)


if __name__ == "__main__":
    unittest.main()
