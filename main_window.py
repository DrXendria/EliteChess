"""

Main window for Swiss Chess Tournament Manager.

"""

import os

import sys

import socket

import subprocess

import shutil

import urllib.request

import re

import json

from PyQt6.QtWidgets import (

    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,

    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,

    QPushButton, QLabel, QComboBox, QStatusBar, QMenuBar, QMenu,

    QFileDialog, QMessageBox, QToolBar, QLineEdit, QGroupBox,

    QFormLayout, QApplication, QSpinBox, QCheckBox, QTextEdit

)

from PyQt6.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal

from PyQt6.QtGui import QAction, QIcon, QFont, QKeySequence, QColor



class TunnelReader(QThread):

    """Background thread to read tunnel process output and detect public URLs."""

    url_found = pyqtSignal(str)

    log_received = pyqtSignal(str)

    

    def __init__(self, process):

        super().__init__()

        self.process = process

        self._url_emitted = False

        

    def run(self):

        import time

        try:

            while True:

                line = self.process.stdout.readline()

                if not line:

                    break

                

                # Clean ANSI escape codes

                clean_line = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', line).strip()

                if not clean_line:

                    continue

                    

                self.log_received.emit(clean_line)

                

                # Skip if we already found a URL

                if self._url_emitted:

                    continue

                

                if "https://" in clean_line:

                    # Look for tunnel URLs (trycloudflare.com, localhost.run, serveo.net)

                    match = re.search(r'(https://[a-zA-Z0-9._-]+\.trycloudflare\.com)', clean_line)

                    if not match:

                        # Generic https URL but filter out non-tunnel links

                        match = re.search(r'(https://[^\s"\x1b]+)', clean_line)

                        if match:

                            url = match.group(1).rstrip('.,)')

                            # Filter out documentation/settings links

                            skip_words = ["developers", "github", "console", "settings", 

                                         "cloudflare.com", "one.dash", "support"]

                            if any(w in url for w in skip_words) and "trycloudflare" not in url:

                                match = None

                    

                    if match:

                        url = match.group(1).rstrip('.,')

                        self.log_received.emit(f"<b>✓ Link Tespit Edildi.</b> Tünel hazırlanıyor...")

                        time.sleep(3)  # Brief wait for tunnel stabilization

                        self._url_emitted = True

                        self.url_found.emit(url)

        except Exception:

            pass



class CloudflareDownloader(QThread):

    finished = pyqtSignal(str)

    error = pyqtSignal(str)



    def run(self):

        try:

            # Standalone binary for Windows 64-bit

            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

            target = os.path.join(os.getcwd(), "cloudflared.exe")

            

            # Simple download

            with urllib.request.urlopen(url) as response, open(target, 'wb') as out_file:

                shutil.copyfileobj(response, out_file)

            

            self.finished.emit(target)

        except Exception as e:

            self.error.emit(str(e))



from models import (

    Tournament, Player, Team, Match, Round, MatchResult,

    TournamentType, TieBreakType, Title

)

from pairing import generate_pairings, swap_match_colors

from tiebreak import calculate_all_standings

from tournament_io import save_tournament, load_tournament, export_html, export_excel

from dialogs import TournamentDialog, PlayerDialog, TeamDialog, FideSearchDialog, PlayerListImportDialog, PlayerDetailsDialog, DashboardDialog, UnpairedPlayersDialog

# --- MERGED FROM widgets.py ---

class StandingsTable(QTableWidget):

    """Sortable standings table with tie-break columns."""



    def __init__(self, parent=None):

        super().__init__(parent)

        self.setAlternatingRowColors(True)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.setSortingEnabled(False)

        self.verticalHeader().setVisible(False)

        self.horizontalHeader().setStretchLastSection(True)



    def update_standings(self, standings: list[dict], tournament: Tournament):

        """Populate the table with standings data."""

        tb_types = tournament.tiebreak_order

        base_cols = ["Sıra", "No", "Ünvan", "İsim", "Rating", "Kulüp", "Puan"]

        tb_cols = [tb.value for tb in tb_types]

        all_cols = base_cols + tb_cols



        self.setColumnCount(len(all_cols))

        self.setHorizontalHeaderLabels(all_cols)

        self.setRowCount(len(standings))



        for row, entry in enumerate(standings):

            p = entry["player"]

            col = 0



            # Rank

            item = QTableWidgetItem(str(entry["rank"]))

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.setItem(row, col, item)

            col += 1



            # Player number

            idx = tournament.players.index(p) + 1 if p in tournament.players else 0

            item = QTableWidgetItem(str(idx))

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.setItem(row, col, item)

            col += 1



            # Title

            item = QTableWidgetItem(p.display_title)

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if p.display_title in ("GM", "WGM"):

                item.setForeground(QColor("#f59e0b"))

            elif p.display_title in ("IM", "WIM"):

                item.setForeground(QColor("#8b5cf6"))

            elif p.display_title in ("FM", "WFM"):

                item.setForeground(QColor("#10b981"))

            self.setItem(row, col, item)

            col += 1



            # Name

            item = QTableWidgetItem(p.full_name)

            font = item.font()

            if entry["rank"] <= 3:

                font.setBold(True)

                item.setFont(font)

            self.setItem(row, col, item)

            col += 1



            # Rating

            item = QTableWidgetItem(str(p.rating) if p.rating > 0 else "—")

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.setItem(row, col, item)

            col += 1



            # Club

            self.setItem(row, col, QTableWidgetItem(p.club))

            col += 1



            # Score

            score_item = QTableWidgetItem(f"{entry['score']:.1f}")

            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            score_font = score_item.font()

            score_font.setBold(True)

            score_item.setFont(score_font)

            self.setItem(row, col, score_item)

            col += 1



            # Tiebreaks

            for tb in tb_types:

                val = entry["tiebreaks"].get(tb, 0)

                tb_item = QTableWidgetItem(f"{val:.1f}" if isinstance(val, float) else str(val))

                tb_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.setItem(row, col, tb_item)

                col += 1



        # Resize columns

        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        for i in range(len(all_cols)):

            if i != 3:

                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)





class PairingTable(QTableWidget):

    """Pairing/results table for a single round."""



    result_changed = pyqtSignal()



    def __init__(self, parent=None):

        super().__init__(parent)

        self.setAlternatingRowColors(True)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.verticalHeader().setVisible(False)

        self.horizontalHeader().setStretchLastSection(False)

        self._tournament = None

        self._round = None



    def load_round(self, tournament: Tournament, rnd):

        """Load round data into the table."""

        self._tournament = tournament

        self._round = rnd



        # Calculate scores before this round

        scores = {p.id: 0.0 for p in tournament.players}

        for r in tournament.rounds:

            if r.round_number >= rnd.round_number:

                break

            for m in r.matches:

                if m.is_bye:

                    if m.result == MatchResult.HALF_POINT_BYE:

                        scores[m.white_id] = scores.get(m.white_id, 0.0) + 0.5

                    elif m.result != MatchResult.ZERO_POINT_BYE and m.result != MatchResult.NONE:

                        scores[m.white_id] = scores.get(m.white_id, 0.0) + 1.0

                else:

                    if m.result == MatchResult.WHITE_WIN or m.result == MatchResult.BLACK_FORFEIT:

                        scores[m.white_id] = scores.get(m.white_id, 0.0) + 1.0

                    elif m.result == MatchResult.BLACK_WIN or m.result == MatchResult.WHITE_FORFEIT:

                        scores[m.black_id] = scores.get(m.black_id, 0.0) + 1.0

                    elif m.result == MatchResult.DRAW:

                        scores[m.white_id] = scores.get(m.white_id, 0.0) + 0.5

                        scores[m.black_id] = scores.get(m.black_id, 0.0) + 0.5



        columns = ["Masa", "No", "Beyaz", "Rtg", "Puan", "Sonuç", "Puan", "Rtg", "Siyah", "No"]

        self.setColumnCount(len(columns))

        self.setHorizontalHeaderLabels(columns)

        self.setRowCount(len(rnd.matches))



        for row, match in enumerate(rnd.matches):

            col = 0



            # Board

            item = QTableWidgetItem(str(match.board))

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.setItem(row, col, item)

            col += 1



            # White number

            wp = tournament.get_player_by_id(match.white_id)

            w_idx = tournament.players.index(wp) + 1 if wp and wp in tournament.players else 0

            item = QTableWidgetItem(str(w_idx))

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.setItem(row, col, item)

            col += 1



            # White name

            w_name = wp.full_name if wp else match.white_id

            item = QTableWidgetItem(w_name)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.setItem(row, col, item)

            col += 1



            # White rating

            w_rtg = str(wp.rating) if wp and wp.rating > 0 else "—"

            item = QTableWidgetItem(w_rtg)

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.setItem(row, col, item)

            col += 1



            # White score

            w_score = f"{scores.get(wp.id, 0.0):g}" if wp else "0"

            item = QTableWidgetItem(w_score)

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.setItem(row, col, item)

            col += 1



            # Result combo

            if match.is_bye:

                match.result = MatchResult.BYE # Ensure it's set

                item = QTableWidgetItem("1 - 0 (Bye) ✅")

                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                item.setBackground(QColor("#dcfce7")) # Light green

                item.setForeground(QColor("#166534")) # Dark green

                self.setItem(row, col, item)

            else:

                combo = QComboBox()

                combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)

                combo.addItem("—", MatchResult.NONE)

                combo.addItem("1 - 0", MatchResult.WHITE_WIN)

                combo.addItem("½ - ½", MatchResult.DRAW)

                combo.addItem("0 - 1", MatchResult.BLACK_WIN)

                combo.addItem("1 - 0 (f)", MatchResult.BLACK_FORFEIT)

                combo.addItem("0 - 1 (f)", MatchResult.WHITE_FORFEIT)

                combo.addItem("0 - 0 (f)", MatchResult.DOUBLE_FORFEIT)

                combo.addItem("½ bye", MatchResult.HALF_POINT_BYE)

                combo.addItem("0 bye", MatchResult.ZERO_POINT_BYE)



                idx = combo.findData(match.result)

                if idx >= 0:

                    combo.setCurrentIndex(idx)



                combo.currentIndexChanged.connect(

                    lambda _, r=row: self._on_result_changed(r)

                )

                self.setCellWidget(row, col, combo)

            col += 1



            # Black prep

            bp = tournament.get_player_by_id(match.black_id) if match.black_id != "BYE" else None



            # Black score

            b_score = f"{scores.get(bp.id, 0.0):g}" if bp else "0"

            item = QTableWidgetItem(b_score if match.black_id != "BYE" else "—")

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.setItem(row, col, item)

            col += 1



            # Black rating

            b_rtg = str(bp.rating) if bp and bp.rating > 0 else "—"

            item = QTableWidgetItem(b_rtg if match.black_id != "BYE" else "—")

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.setItem(row, col, item)

            col += 1



            # Black name

            b_name = bp.full_name if bp else ("BYE" if match.black_id == "BYE" else match.black_id)

            item = QTableWidgetItem(b_name)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.setItem(row, col, item)

            col += 1



            # Black number

            b_idx = tournament.players.index(bp) + 1 if bp and bp in tournament.players else 0

            item = QTableWidgetItem(str(b_idx) if b_idx > 0 else "—")

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.setItem(row, col, item)



        # ─── Unpaired Players Section ───

        paired_ids = set()

        for m in rnd.matches:

            paired_ids.add(m.white_id)

            if m.black_id != "BYE":

                paired_ids.add(m.black_id)

        

        unpaired = [p for p in tournament.players if p.id not in paired_ids]

        

        if unpaired:

            start_row = len(rnd.matches)

            self.setRowCount(start_row + 1 + len(unpaired))

            

            # Separator Row

            sep_row = start_row

            sep_item = QTableWidgetItem("─── Eşleşmeyen / Çekilen Sporcular ───")

            sep_item.setFlags(Qt.ItemFlag.ItemIsEnabled)

            sep_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            

            # Theme-aware styling (Using more neutral colors)

            sep_item.setBackground(QColor(128, 128, 128, 40)) # Translucent gray

            font = QFont()

            font.setBold(True)

            font.setPointSize(9)

            sep_item.setFont(font)

            

            self.setSpan(sep_row, 0, 1, self.columnCount())

            self.setItem(sep_row, 0, sep_item)

            

            for i, p in enumerate(unpaired):

                row = start_row + 1 + i

                

                # Apply background that matches the theme better

                bg_color = self.palette().alternateBase().color() if i % 2 == 0 else self.palette().base().color()

                

                # Helper to set items correctly

                def set_ui_item(c, text, flags=Qt.ItemFlag.ItemIsEnabled, align=Qt.AlignmentFlag.AlignCenter):

                    it = QTableWidgetItem(text)

                    it.setFlags(flags)

                    it.setTextAlignment(align)

                    it.setBackground(bg_color)

                    self.setItem(row, c, it)

                    return it



                set_ui_item(1, str(tournament.players.index(p) + 1))

                name_it = set_ui_item(2, p.full_name if p.is_active else f"{p.full_name} (Ayrıldı)", align=Qt.AlignmentFlag.AlignLeft)

                if not p.is_active: name_it.setForeground(QColor("gray"))

                set_ui_item(3, str(p.rating))

                set_ui_item(4, f"{scores.get(p.id, 0.0):g}")

                

                # Result Combo

                combo = QComboBox()

                combo.p_id = p.id

                combo.addItem("— (0 Puan)", MatchResult.ZERO_POINT_BYE)

                combo.addItem("½ Bye", MatchResult.HALF_POINT_BYE)

                combo.addItem("1 Bye (Manuel)", MatchResult.BYE)

                combo.currentIndexChanged.connect(lambda _, p_id=p.id: self._on_unpaired_result_changed(p_id))

                self.setCellWidget(row, 5, combo)

                

                # Fill empty cells for BG consistency

                for c in [0, 6, 7, 8, 9]:

                    it = QTableWidgetItem("")

                    it.setFlags(Qt.ItemFlag.ItemIsEnabled)

                    it.setBackground(bg_color)

                    self.setItem(row, c, it)



        # Resize

        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)

        for i in [0, 1, 3, 4, 5, 6, 7, 9]:

            self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)



    def _on_result_changed(self, row: int):

        if not self._round or row >= len(self._round.matches):

            return

        combo = self.cellWidget(row, 5)

        if combo:

            self._round.matches[row].result = combo.currentData()

            self.result_changed.emit()



    def _on_unpaired_result_changed(self, player_id: str):

        if not self._round or not self._tournament:

            return

            

        # Find which row this player is in

        for row in range(self.rowCount()):

            combo = self.cellWidget(row, 5)

            if combo and self.item(row, 2) and player_id in [p.id for p in self._tournament.players if p.full_name in self.item(row, 2).text()]:

                res = combo.currentData()

                

                # Update or create a bye match for this player

                existing = None

                for m in self._round.matches:

                    if m.white_id == player_id and m.black_id == "BYE":

                        existing = m

                        break

                

                if existing:

                    existing.result = res

                else:

                    new_match = Match(

                        board=len(self._round.matches) + 1,

                        white_id=player_id,

                        black_id="BYE",

                        result=res

                    )

                    self._round.matches.append(new_match)

                

                self.result_changed.emit()

                break



    def get_updated_matches(self) -> list[Match]:

        if not self._round:

            return []

        return self._round.matches



    def keyPressEvent(self, event):

        row = self.currentRow()

        if row >= 0:

            text = event.text().strip()

            combo = self.cellWidget(row, 5)

            

            # If the row has no combo (e.g. BYE), but we press a valid number, skip to next row

            if not combo and text in ("1", "2", "3", "4", "5", "6"):

                next_row = row + 1

                if next_row < self.rowCount():

                    self.setCurrentCell(next_row, self.currentColumn())

                return

                

            if combo:

                moved = False

                result_map = {

                    "1": MatchResult.WHITE_WIN,

                    "2": MatchResult.DRAW,

                    "3": MatchResult.BLACK_WIN,

                    "4": MatchResult.BLACK_FORFEIT, # White win by forfeit

                    "5": MatchResult.WHITE_FORFEIT, # Black win by forfeit

                    "6": MatchResult.DOUBLE_FORFEIT,

                }

                

                if text in result_map:

                    idx = combo.findData(result_map[text])

                    if idx >= 0:

                        combo.setCurrentIndex(idx)

                        moved = True

                

                if moved:

                    next_row = row + 1

                    if next_row < self.rowCount():

                        self.setCurrentCell(next_row, self.currentColumn())

                    return

        super().keyPressEvent(event)





class CrossTableWidget(QTableWidget):

    """Cross-table (Çapraz Tablo) view for the tournament."""



    def __init__(self, parent=None):

        super().__init__(parent)

        self.setAlternatingRowColors(True)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.setSortingEnabled(False)

        self.verticalHeader().setVisible(False)

        self.horizontalHeader().setStretchLastSection(True)



    def update_table(self, standings: list[dict], tournament: Tournament):

        if not standings or not tournament.players:

            self.setRowCount(0)

            self.setColumnCount(0)

            return



        rounds_count = tournament.num_rounds

        base_cols = ["Sıra", "No", "İsim", "Rtg"]

        round_cols = [f"R{i+1}" for i in range(rounds_count)]

        end_cols = ["Puan"]

        tb_cols = [tb.value for tb in tournament.tiebreak_order]

        

        all_cols = base_cols + round_cols + end_cols + tb_cols

        

        self.setColumnCount(len(all_cols))

        self.setHorizontalHeaderLabels(all_cols)

        self.setRowCount(len(standings))

        

        # O(N) lookup for player starting number (No)

        player_to_no = {

            p.id: idx + 1 for idx, p in enumerate(tournament.players)

        }

        

        # O(N) lookup for player rank (Sıralama)

        player_to_rank = {

            entry["player"].id: entry["rank"] for entry in standings

        }

        

        for row, entry in enumerate(standings):

            p = entry["player"]

            col = 0

            

            # Sıra

            item = QTableWidgetItem(str(entry["rank"]))

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.setItem(row, col, item)

            col += 1

            

            # No

            p_no = player_to_no.get(p.id, 0)

            item = QTableWidgetItem(str(p_no))

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.setItem(row, col, item)

            col += 1

            

            # İsim

            item = QTableWidgetItem(p.full_name)

            if entry["rank"] <= 3:

                font = item.font()

                font.setBold(True)

                item.setFont(font)

            self.setItem(row, col, item)

            col += 1

            

            # Rtg

            item = QTableWidgetItem(str(p.rating) if p.rating > 0 else "—")

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.setItem(row, col, item)

            col += 1

            

            # Turlar

            for r in range(1, rounds_count + 1):

                match_text = "—"

                if r <= len(tournament.rounds):

                    rnd = tournament.rounds[r-1]

                    for m in rnd.matches:

                        if m.white_id == p.id:

                            if m.is_bye:

                                if m.result == MatchResult.HALF_POINT_BYE:

                                    match_text = "½ BYE"

                                elif m.result == MatchResult.ZERO_POINT_BYE:

                                    match_text = "-0"

                                else:

                                    match_text = "+1 BYE"

                            else:

                                opp_no = player_to_rank.get(m.black_id, "?")

                                res = ""

                                if m.result == MatchResult.WHITE_WIN: res = "1"

                                elif m.result == MatchResult.DRAW: res = "½"

                                elif m.result == MatchResult.BLACK_WIN: res = "0"

                                elif m.result == MatchResult.BLACK_FORFEIT: res = "+ (f)"

                                elif m.result == MatchResult.WHITE_FORFEIT: res = "- (f)"

                                elif m.result == MatchResult.DOUBLE_FORFEIT: res = "- (f)"

                                match_text = f"{opp_no}w{res}"

                            break

                        elif m.black_id == p.id:

                            opp_no = player_to_rank.get(m.white_id, "?")

                            res = ""

                            if m.result == MatchResult.BLACK_WIN: res = "1"

                            elif m.result == MatchResult.DRAW: res = "½"

                            elif m.result == MatchResult.WHITE_WIN: res = "0"

                            elif m.result == MatchResult.WHITE_FORFEIT: res = "+ (f)"

                            elif m.result == MatchResult.BLACK_FORFEIT: res = "- (f)"

                            elif m.result == MatchResult.DOUBLE_FORFEIT: res = "- (f)"

                            match_text = f"{opp_no}b{res}"

                            break

                item = QTableWidgetItem(match_text)

                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.setItem(row, col, item)

                col += 1

                

            # Puan

            score_item = QTableWidgetItem(f"{entry['score']:.1f}")

            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            score_font = score_item.font()

            score_font.setBold(True)

            score_item.setFont(score_font)

            self.setItem(row, col, score_item)

            col += 1

            

            # Eşitlik Bozmalar

            for tb in tournament.tiebreak_order:

                val = entry["tiebreaks"].get(tb, 0)

                tb_item = QTableWidgetItem(f"{val:.1f}" if isinstance(val, float) else str(val))

                tb_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.setItem(row, col, tb_item)

                col += 1



        # Resize columns

        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        for i in range(len(all_cols)):

            if i != 2:

                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

# --- END MERGED ---



from ui_theme import AppTheme, get_stylesheet

from database import init_db, save_tournament_to_db, load_tournament_from_db

from web_server import LiveServerThread





def resource_path(relative_path):

    """ Get absolute path to resource, works for dev and for PyInstaller """

    try:

        # PyInstaller creates a temp folder and stores path in _MEIPASS

        base_path = sys._MEIPASS

    except Exception:

        base_path = os.path.abspath(".")



    return os.path.join(base_path, relative_path)





class MainWindow(QMainWindow):



    def __init__(self):

        super().__init__()

        

        # Initialize database

        init_db()

        

        self.current_theme = AppTheme.SYSTEM

        self.current_filepath = ""



        self.setWindowTitle("Elite Chess Tournament Manager")

        self.setWindowIcon(QIcon(resource_path("resources/logo.png")))

        self.setMinimumSize(1100, 700)

        self.resize(1280, 800)



        self.server_thread = None

        self.ngrok_process = None

        self.ssh_process = None

        self.cf_process = None  # Cloudflare process

        self.ngrok_timer = QTimer(self)

        self.ngrok_timer.timeout.connect(self._update_ngrok_status)



        self._create_menu()

        self._create_toolbar()

        self._create_tabs()

        self._create_statusbar()

        self._apply_theme(self.current_theme)

        

        self.tournament = Tournament() # Fallback

        QTimer.singleShot(0, self._show_dashboard)



    # ─── MENU ────────────────────────────────────────────────────────────



    def _create_menu(self):

        menubar = self.menuBar()



        # File

        file_menu = menubar.addMenu("Dosya")



        dash_act = QAction("Ana Ekran (Dashboard)", self)

        dash_act.triggered.connect(self._show_dashboard)

        file_menu.addAction(dash_act)



        file_menu.addSeparator()



        new_act = QAction("Yeni Turnuva", self)

        new_act.setShortcut(QKeySequence.StandardKey.New)

        new_act.triggered.connect(self._new_tournament)

        file_menu.addAction(new_act)



        open_act = QAction("Turnuva Aç...", self)

        open_act.setShortcut(QKeySequence.StandardKey.Open)

        open_act.triggered.connect(self._open_tournament)

        file_menu.addAction(open_act)



        save_act = QAction("Kaydet", self)

        save_act.setShortcut(QKeySequence.StandardKey.Save)

        save_act.triggered.connect(self._save_tournament)

        file_menu.addAction(save_act)



        save_as_act = QAction("Farklı Kaydet...", self)

        save_as_act.setShortcut(QKeySequence.StandardKey.SaveAs)

        save_as_act.triggered.connect(self._save_tournament_as)

        file_menu.addAction(save_as_act)



        file_menu.addSeparator()



        html_act = QAction("HTML Dışa Aktar...", self)

        html_act.triggered.connect(self._export_html)

        file_menu.addAction(html_act)



        excel_act = QAction("Excel Dışa Aktar...", self)

        excel_act.triggered.connect(self._export_excel)

        file_menu.addAction(excel_act)



        file_menu.addSeparator()



        exit_act = QAction("Çıkış", self)

        exit_act.setShortcut(QKeySequence("Alt+F4"))

        exit_act.triggered.connect(self.close)

        file_menu.addAction(exit_act)



        # Edit

        edit_menu = menubar.addMenu("Düzenle")



        settings_act = QAction("Turnuva Ayarları...", self)

        settings_act.triggered.connect(self._edit_tournament_settings)

        edit_menu.addAction(settings_act)



        edit_menu.addSeparator()



        add_player_act = QAction("Oyuncu Ekle...", self)

        add_player_act.setShortcut(QKeySequence("Ctrl+N"))

        add_player_act.triggered.connect(self._add_player)

        edit_menu.addAction(add_player_act)



        fide_act = QAction("FIDE Listesinden Ekle...", self)

        fide_act.triggered.connect(self._fide_import)

        edit_menu.addAction(fide_act)



        import_list_act = QAction("Listeden İçe Aktar...", self)

        import_list_act.setShortcut(QKeySequence("Ctrl+I"))

        import_list_act.triggered.connect(self._import_player_list)

        edit_menu.addAction(import_list_act)



        edit_menu.addSeparator()



        add_team_act = QAction("Takım Ekle...", self)

        add_team_act.triggered.connect(self._add_team)

        edit_menu.addAction(add_team_act)



        # Pairings

        pair_menu = menubar.addMenu("Eşleştirme")



        auto_pair_act = QAction("Otomatik Eşleştir", self)

        auto_pair_act.setShortcut(QKeySequence("F9"))

        auto_pair_act.triggered.connect(self._generate_pairings)

        pair_menu.addAction(auto_pair_act)



        delete_round_act = QAction("Turu Sil", self)

        delete_round_act.triggered.connect(self._delete_current_round)

        pair_menu.addAction(delete_round_act)



        # Rounds

        round_menu = menubar.addMenu("Turlar")



        complete_act = QAction("Turu Tamamla", self)

        complete_act.setShortcut(QKeySequence("F10"))

        complete_act.triggered.connect(self._complete_round)

        round_menu.addAction(complete_act)





        # View

        view_menu = menubar.addMenu("Görünüm")



        theme_menu = view_menu.addMenu("Tema")

        for theme in AppTheme:

            act = QAction(theme.display_name, self)

            act.triggered.connect(lambda checked, t=theme: self._apply_theme(t))

            theme_menu.addAction(act)

        # Help
        help_menu = menubar.addMenu("Yardım")
        about_act = QAction("Hakkında...", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)



    # ─── TOOLBAR ─────────────────────────────────────────────────────────



    def _create_toolbar(self):

        toolbar = QToolBar("Ana Araç Çubuğu")

        toolbar.setMovable(False)

        toolbar.setIconSize(QSize(20, 20))

        self.addToolBar(toolbar)



        btn_new = QPushButton("📄 Yeni")

        btn_new.clicked.connect(self._new_tournament)

        toolbar.addWidget(btn_new)



        btn_open = QPushButton("📂 Aç")

        btn_open.clicked.connect(self._open_tournament)

        toolbar.addWidget(btn_open)



        btn_save = QPushButton("💾 Kaydet")

        btn_save.clicked.connect(self._save_tournament)

        toolbar.addWidget(btn_save)



        btn_save_as = QPushButton("💾 Farklı Kaydet")

        btn_save_as.clicked.connect(self._save_tournament_as)

        toolbar.addWidget(btn_save_as)



        toolbar.addSeparator()



        btn_add = QPushButton("➕ Oyuncu Ekle")

        btn_add.clicked.connect(self._add_player)

        toolbar.addWidget(btn_add)



        btn_import = QPushButton("📋 Liste İçe Aktar")

        btn_import.clicked.connect(self._import_player_list)

        toolbar.addWidget(btn_import)



        toolbar.addSeparator()



        btn_pair = QPushButton("🔀 Eşleştir")

        btn_pair.clicked.connect(self._generate_pairings)

        toolbar.addWidget(btn_pair)



        btn_complete = QPushButton("✅ Turu Tamamla")

        btn_complete.clicked.connect(self._complete_round)

        toolbar.addWidget(btn_complete)



    # ─── TABS ────────────────────────────────────────────────────────────



    def _create_tabs(self):

        self.tab_widget = QTabWidget()

        self.setCentralWidget(self.tab_widget)



        self._create_tournament_tab()

        self._create_players_tab()

        self._create_rounds_tab()

        self._create_standings_tab()

        self._create_crosstable_tab()

        self._create_broadcast_tab()



    def _create_tournament_tab(self):

        widget = QWidget()

        layout = QVBoxLayout(widget)



        info_group = QGroupBox("Turnuva Bilgileri")

        form = QFormLayout(info_group)



        self.info_name = QLabel()

        self.info_name.setStyleSheet("font-size: 18px; font-weight: bold;")

        form.addRow("Turnuva:", self.info_name)



        self.info_type = QLabel()

        form.addRow("Tür:", self.info_type)



        self.info_date = QLabel()

        form.addRow("Tarih:", self.info_date)



        self.info_location = QLabel()

        form.addRow("Konum:", self.info_location)



        self.info_arbiter = QLabel()

        form.addRow("Hakem:", self.info_arbiter)



        self.info_rounds = QLabel()

        form.addRow("Turlar:", self.info_rounds)



        self.info_players = QLabel()

        form.addRow("Oyuncular:", self.info_players)



        layout.addWidget(info_group)



        tb_group = QGroupBox("Eşitlik Bozma Sıralaması")

        tb_layout = QVBoxLayout(tb_group)

        self.info_tiebreaks = QLabel()

        self.info_tiebreaks.setWordWrap(True)

        tb_layout.addWidget(self.info_tiebreaks)

        layout.addWidget(tb_group)



        btn = QPushButton("⚙ Turnuva Ayarlarını Düzenle")

        btn.clicked.connect(self._edit_tournament_settings)

        layout.addWidget(btn)



        layout.addStretch()

        self.tab_widget.addTab(widget, "🏆 Turnuva")



    def _create_players_tab(self):

        widget = QWidget()

        layout = QVBoxLayout(widget)



        # Search

        search_layout = QHBoxLayout()

        self.player_search = QLineEdit()

        self.player_search.setPlaceholderText("🔍 Oyuncu ara...")

        self.player_search.textChanged.connect(self._filter_players)

        search_layout.addWidget(self.player_search)

        layout.addLayout(search_layout)



        # Player table

        self.player_table = QTableWidget()

        self.player_table.setAlternatingRowColors(True)

        self.player_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.player_table.verticalHeader().setVisible(False)

        self.player_table.setColumnCount(12)

        self.player_table.setHorizontalHeaderLabels(

            ["Kayıt", "No", "Ünvan", "Soyad", "Ad", "UKD", "ELO", "Rating", "Kulüp", "FIDE ID", "Takım", "Oynamadığı Turlar"]

        )

        self.player_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.player_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self.player_table.horizontalHeader().setSectionResizeMode(11, QHeaderView.ResizeMode.Stretch)

        self.player_table.doubleClicked.connect(self._edit_player)

        self.player_table.itemChanged.connect(self._on_player_item_changed)

        

        # Context menu setup

        self.player_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.player_table.customContextMenuRequested.connect(self._show_player_context_menu)

        

        layout.addWidget(self.player_table)



        # Buttons

        btn_layout = QHBoxLayout()



        btn_select_all = QPushButton("☑ Kayıt: Hepsini Seç")

        btn_select_all.clicked.connect(self._select_all_players)

        btn_layout.addWidget(btn_select_all)



        btn_deselect_all = QPushButton("☐ Kayıt: Hepsini Temizle")

        btn_deselect_all.setProperty("secondary", True)

        btn_deselect_all.clicked.connect(self._deselect_all_players)

        btn_layout.addWidget(btn_deselect_all)



        btn_start_rank = QPushButton("🏆 Başlangıç Sıralaması")

        btn_start_rank.clicked.connect(self._generate_starting_rank)

        btn_layout.addWidget(btn_start_rank)



        btn_add = QPushButton("➕ Ekle")

        btn_add.clicked.connect(self._add_player)

        btn_layout.addWidget(btn_add)



        btn_edit = QPushButton("✏️ Düzenle")

        btn_edit.clicked.connect(self._edit_player)

        btn_layout.addWidget(btn_edit)



        btn_del = QPushButton("🗑️ Sil")

        btn_del.setProperty("danger", True)

        btn_del.clicked.connect(self._delete_player)

        btn_layout.addWidget(btn_del)



        btn_fide = QPushButton("🌐 FIDE Import")

        btn_fide.setProperty("secondary", True)

        btn_fide.clicked.connect(self._fide_import)

        btn_layout.addWidget(btn_fide)



        btn_team = QPushButton("👥 Takım Ekle")

        btn_team.setProperty("secondary", True)

        btn_team.clicked.connect(self._add_team)

        btn_layout.addWidget(btn_team)



        btn_layout.addStretch()

        layout.addLayout(btn_layout)



        self.tab_widget.addTab(widget, "👤 Oyuncular")



    def _create_rounds_tab(self):

        widget = QWidget()

        layout = QVBoxLayout(widget)



        # Round selector

        round_layout = QHBoxLayout()

        round_layout.addWidget(QLabel("Tur:"))

        self.round_combo = QComboBox()

        self.round_combo.currentIndexChanged.connect(self._load_round)

        round_layout.addWidget(self.round_combo, 1)

        layout.addLayout(round_layout)



        # Pairing table

        self.pairing_table = PairingTable()

        self.pairing_table.result_changed.connect(self._on_result_changed)

        self.pairing_table.cellDoubleClicked.connect(self._on_pairing_double_click)

        layout.addWidget(self.pairing_table)



        # Buttons

        btn_layout = QHBoxLayout()



        btn_pair = QPushButton("🔀 Eşleştir")

        btn_pair.clicked.connect(self._generate_pairings)

        btn_layout.addWidget(btn_pair)



        btn_complete = QPushButton("✅ Turu Tamamla")

        btn_complete.clicked.connect(self._complete_round)

        btn_layout.addWidget(btn_complete)



        btn_delete = QPushButton("🗑️ Turu Sil")

        btn_delete.setProperty("danger", True)

        btn_delete.clicked.connect(self._delete_current_round)

        btn_layout.addWidget(btn_delete)



        btn_layout.addStretch()

        layout.addLayout(btn_layout)



        self.tab_widget.addTab(widget, "🎯 Turlar")



    def _create_standings_tab(self):

        widget = QWidget()

        layout = QVBoxLayout(widget)



        self.standings_table = StandingsTable()

        self.standings_table.cellDoubleClicked.connect(self._on_standings_double_click)

        layout.addWidget(self.standings_table)



        btn_layout = QHBoxLayout()



        btn_refresh = QPushButton("🔄 Yenile")

        btn_refresh.clicked.connect(self._refresh_standings)

        btn_layout.addWidget(btn_refresh)



        btn_html = QPushButton("📄 HTML Export")

        btn_html.setProperty("secondary", True)

        btn_html.clicked.connect(self._export_html)

        btn_layout.addWidget(btn_html)



        btn_excel = QPushButton("📊 Excel Export")

        btn_excel.setProperty("secondary", True)

        btn_excel.clicked.connect(self._export_excel)

        btn_layout.addWidget(btn_excel)



        btn_layout.addStretch()

        layout.addLayout(btn_layout)



        self.tab_widget.addTab(widget, "📊 Sıralama")



    def _create_crosstable_tab(self):

        widget = QWidget()

        layout = QVBoxLayout(widget)

        

        self.crosstable_widget = CrossTableWidget()

        self.crosstable_widget.cellDoubleClicked.connect(self._on_crosstable_double_click)

        layout.addWidget(self.crosstable_widget)

        

        self.tab_widget.addTab(widget, "📈 Çapraz Tablo")



    def _create_statusbar(self):

        self.status_bar = QStatusBar()

        self.setStatusBar(self.status_bar)

        self.status_label = QLabel()

        self.status_bar.addPermanentWidget(self.status_label)



    # ─── UI UPDATE ───────────────────────────────────────────────────────



    def _update_ui(self):

        t = self.tournament



        # Title

        title = f"{t.name} — PAU Swiss Chess Tournament Manager"

        if self.current_filepath:

            title = f"{t.name} [{os.path.basename(self.current_filepath)}] — PAU Swiss Chess Tournament Manager"

        self.setWindowTitle(title)



        # Tournament tab

        self.info_name.setText(t.name or "—")

        type_names = {

            TournamentType.SWISS: "İsviçre Sistemi",

            TournamentType.ROUND_ROBIN: "Round-Robin (Berger)",

            TournamentType.TEAM_SWISS: "Takım İsviçre",

        }

        self.info_type.setText(type_names.get(t.tournament_type, "—"))

        self.info_date.setText(t.date or "—")

        self.info_location.setText(t.location or "—")

        self.info_arbiter.setText(t.arbiter or "—")

        self.info_rounds.setText(f"{t.current_round} / {t.num_rounds}")

        self.info_players.setText(str(len(t.get_active_players())))

        tb_text = " → ".join(f"{tb.value} ({tb.display_name})" for tb in t.tiebreak_order)

        self.info_tiebreaks.setText(tb_text or "—")



        self._refresh_player_table()



        # Rounds tab

        self._update_round_combo()



        # Standings tab

        self._refresh_standings()

        

        # Auto-save

        if hasattr(self, 'tournament') and self.tournament:

            try:

                save_tournament_to_db(self.tournament)

            except Exception as e:

                print(f"Auto-save error: {e}")



        # Status bar

        self._update_tournament_info()



        # Sync Web Server

        if self.server_thread:

            self.server_thread.update_tournament(self.tournament)



    def _update_tournament_info(self):

        t = self.tournament

        type_names = {

            TournamentType.SWISS: "İsviçre Sistemi",

            TournamentType.ROUND_ROBIN: "Round-Robin (Berger)",

            TournamentType.TEAM_SWISS: "Takım İsviçre",

        }

        self.status_label.setText(

            f"Oyuncular: {len(t.get_active_players())} | "

            f"Tur: {t.current_round}/{t.num_rounds} | "

            f"Sistem: {type_names.get(t.tournament_type, '—')}"

        )



    def _refresh_player_table(self):

        self.player_table.blockSignals(True)

        players = self.tournament.players

        self.player_table.setRowCount(len(players))

        

        # Calculate missed rounds

        missed_rounds_map = {p.id: [] for p in players}

        for rnd in self.tournament.rounds:

            paired_players = set()

            for m in rnd.matches:

                if m.white_id != "BYE": paired_players.add(m.white_id)

                if m.black_id != "BYE": paired_players.add(m.black_id)

            for p in players:

                if p.id not in paired_players:

                    missed_rounds_map[p.id].append(str(rnd.round_number))



        for row, p in enumerate(players):

            # Kayıt checkbox

            check_item = QTableWidgetItem()

            check_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

            check_item.setCheckState(Qt.CheckState.Checked if p.is_registered else Qt.CheckState.Unchecked)

            self.player_table.setItem(row, 0, check_item)

            

            # Non-editable cells

            no_item = QTableWidgetItem(str(row + 1))

            no_item.setFlags(no_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.player_table.setItem(row, 1, no_item)

            

            title_item = QTableWidgetItem(p.display_title)

            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.player_table.setItem(row, 2, title_item)

            

            surname_item = QTableWidgetItem(p.surname)

            surname_item.setFlags(surname_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.player_table.setItem(row, 3, surname_item)

            

            name_item = QTableWidgetItem(p.name)

            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.player_table.setItem(row, 4, name_item)

            

            # Editable UKD/ELO

            ukd_item = QTableWidgetItem(str(p.ukd) if p.ukd > 0 else "")

            self.player_table.setItem(row, 5, ukd_item)

            

            elo_item = QTableWidgetItem(str(p.elo) if p.elo > 0 else "")

            self.player_table.setItem(row, 6, elo_item)

            

            # Non-editable Rating

            rating_item = QTableWidgetItem(str(p.rating) if p.rating > 0 else "—")

            rating_item.setFlags(rating_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.player_table.setItem(row, 7, rating_item)

            

            club_item = QTableWidgetItem(p.club)

            club_item.setFlags(club_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.player_table.setItem(row, 8, club_item)

            

            fide_item = QTableWidgetItem(p.fide_id)

            fide_item.setFlags(fide_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.player_table.setItem(row, 9, fide_item)



            team = self.tournament.get_team_by_id(p.team_id) if p.team_id else None

            team_item = QTableWidgetItem(team.name if team else "—")

            team_item.setFlags(team_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.player_table.setItem(row, 10, team_item)

            

            missed = missed_rounds_map.get(p.id, [])

            missed_item = QTableWidgetItem(", ".join(missed) if missed else "—")

            missed_item.setFlags(missed_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            missed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.player_table.setItem(row, 11, missed_item)



            if not p.is_active:

                for col in range(12):

                    item = self.player_table.item(row, col)

                    if item:

                        item.setForeground(Qt.GlobalColor.gray)

                        if col == 0:

                            # Disable checkbox if inactive

                            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)

                            

        self.player_table.blockSignals(False)



    def _select_all_players(self):

        for p in self.tournament.players:

            if p.is_active:

                p.is_registered = True

        self._update_ui()

        

    def _deselect_all_players(self):

        for p in self.tournament.players:

            if p.is_active:

                p.is_registered = False

        self._update_ui()



    def _on_player_item_changed(self, item):

        row = item.row()

        col = item.column()

        if row < 0 or row >= len(self.tournament.players):

            return

            

        p = self.tournament.players[row]

        changed = False

        

        if col == 0:  # Kayıt Checkbox

            checked = item.checkState() == Qt.CheckState.Checked

            if p.is_registered != checked:

                p.is_registered = checked

                changed = True

        elif col == 5:  # UKD

            text = item.text().strip()

            try:

                new_ukd = int(text) if text else 0

                if p.ukd != new_ukd:

                    p.ukd = new_ukd

                    changed = True

            except ValueError:

                pass # Revert if invalid on next refresh

        elif col == 6:  # ELO

            text = item.text().strip()

            try:

                new_elo = int(text) if text else 0

                if p.elo != new_elo:

                    p.elo = new_elo

                    changed = True

            except ValueError:

                pass

                

        if changed:

            if col in (5, 6):

                p.update_rating()

            self._update_ui()



    def _filter_players(self, text: str):

        text = text.lower()

        for row in range(self.player_table.rowCount()):

            match = False

            for col in range(self.player_table.columnCount()):

                item = self.player_table.item(row, col)

                if item and text in item.text().lower():

                    match = True

                    break

            self.player_table.setRowHidden(row, not match)



    def _update_round_combo(self):

        self.round_combo.blockSignals(True)

        self.round_combo.clear()

        for rnd in self.tournament.rounds:

            status = "✅" if rnd.is_completed else "⏳"

            self.round_combo.addItem(f"{status} Tur {rnd.round_number}", rnd.round_number)

        self.round_combo.blockSignals(False)



        if self.tournament.rounds:

            self.round_combo.setCurrentIndex(len(self.tournament.rounds) - 1)

            self._load_round()



    def _load_round(self):

        idx = self.round_combo.currentIndex()

        if idx < 0 or idx >= len(self.tournament.rounds):

            return

        rnd = self.tournament.rounds[idx]

        self.pairing_table.load_round(self.tournament, rnd)



    def _refresh_standings(self):

        if not self.tournament.players:

            self.standings_table.setRowCount(0)

            if hasattr(self, 'crosstable_widget'):

                self.crosstable_widget.setRowCount(0)

                self.crosstable_widget.setColumnCount(0)

            return

        standings = calculate_all_standings(self.tournament)

        self.standings_table.update_standings(standings, self.tournament)

        if hasattr(self, 'crosstable_widget'):

            self.crosstable_widget.update_table(standings, self.tournament)



    # ─── ACTIONS ─────────────────────────────────────────────────────────



    def _show_about(self):
        QMessageBox.about(self, "Elite Chess Hakkında",
            "<h3>Elite Chess Tournament Manager</h3>"
            "<p>Version 1.0.0</p>"
            "<p>Profesyonel satranç turnuva yönetimi ve canlı yayın sistemi.</p>"
            "<hr>"
            "<p><b>Designed & Developed by Emir Cica</b></p>")

    def _show_dashboard(self):

        dlg = DashboardDialog(self)

        if dlg.exec():

            if dlg.selected_tournament_id:

                t = load_tournament_from_db(dlg.selected_tournament_id)

                if t:

                    self.tournament = t

                    self.current_filepath = ""

                    self._update_ui()

                else:

                    QMessageBox.critical(self, "Hata", "Turnuva veritabanından yüklenemedi!")

            else:

                self._new_tournament()



    def _new_tournament(self):

        if self.tournament.players:

            reply = QMessageBox.question(

                self, "Yeni Turnuva",

                "Mevcut turnuva kaydedilsin mi?",

                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No |

                QMessageBox.StandardButton.Cancel

            )

            if reply == QMessageBox.StandardButton.Yes:

                self._save_tournament()

            elif reply == QMessageBox.StandardButton.Cancel:

                return



        dlg = TournamentDialog(parent=self)

        if dlg.exec():

            self.tournament = dlg.get_tournament()

            self.current_filepath = ""

            self._update_ui()



    def _open_tournament(self):

        filepath, _ = QFileDialog.getOpenFileName(

            self, "Turnuva Aç", "",

            "Swiss Tournament Files (*.swt);;JSON Files (*.json);;All Files (*)"

        )

        if filepath:

            t = load_tournament(filepath)

            if t:

                self.tournament = t

                self.current_filepath = filepath

                self._update_ui()

            else:

                QMessageBox.critical(self, "Hata", "Dosya yüklenemedi!")



    def _save_tournament(self):

        if not self.current_filepath:

            self._save_tournament_as()

            return

        if save_tournament(self.tournament, self.current_filepath):

            self.status_bar.showMessage("Kaydedildi!", 3000)

        else:

            QMessageBox.critical(self, "Hata", "Kaydetme başarısız!")



    def _save_tournament_as(self):

        filepath, _ = QFileDialog.getSaveFileName(

            self, "Turnuva Kaydet", f"{self.tournament.name}.swt",

            "Swiss Tournament Files (*.swt);;JSON Files (*.json)"

        )

        if filepath:

            self.current_filepath = filepath

            self._save_tournament()

            self._update_ui()



    def _export_html(self):

        filepath, _ = QFileDialog.getSaveFileName(

            self, "HTML Dışa Aktar", f"{self.tournament.name}.html",

            "HTML Files (*.html)"

        )

        if filepath:

            if export_html(self.tournament, filepath):

                QMessageBox.information(self, "Başarılı", "HTML dosyası oluşturuldu!")

            else:

                QMessageBox.critical(self, "Hata", "HTML export başarısız!")



    def _export_excel(self):

        filepath, _ = QFileDialog.getSaveFileName(

            self, "Excel Dışa Aktar", f"{self.tournament.name}.xlsx",

            "Excel Files (*.xlsx)"

        )

        if filepath:

            if export_excel(self.tournament, filepath):

                QMessageBox.information(self, "Başarılı", "Excel dosyası oluşturuldu!")

            else:

                QMessageBox.critical(self, "Hata", "Excel export başarısız!")



    def _edit_tournament_settings(self):

        dlg = TournamentDialog(self.tournament, self)

        if dlg.exec():

            self.tournament = dlg.get_tournament()

            self._update_ui()



    def _add_player(self):

        dlg = PlayerDialog(teams=self.tournament.teams, parent=self)

        if dlg.exec():

            player = dlg.get_player()

            self.tournament.players.append(player)

            if player.team_id:

                team = self.tournament.get_team_by_id(player.team_id)

                if team and player.id not in team.player_ids:

                    team.player_ids.append(player.id)

            self._update_ui()



    def _edit_player(self):

        row = self.player_table.currentRow()

        if row < 0 or row >= len(self.tournament.players):

            return

        player = self.tournament.players[row]

        dlg = PlayerDialog(player, self.tournament.teams, self)

        if dlg.exec():

            self._update_ui()



    def _delete_player(self):

        row = self.player_table.currentRow()

        if row < 0 or row >= len(self.tournament.players):

            return

        player = self.tournament.players[row]



        if self.tournament.current_round > 0:

            player.is_active = not player.is_active

            status = "deaktif" if not player.is_active else "aktif"

            self.status_bar.showMessage(f"{player.full_name} {status} edildi", 3000)

        else:

            reply = QMessageBox.question(

                self, "Oyuncu Sil",

                f"{player.full_name} silinsin mi?",

                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No

            )

            if reply == QMessageBox.StandardButton.Yes:

                self.tournament.players.remove(player)

        self._update_ui()



    def _add_team(self):

        dlg = TeamDialog(parent=self)

        if dlg.exec():

            team = dlg.get_team()

            self.tournament.teams.append(team)

            self.status_bar.showMessage(f"Takım eklendi: {team.name}", 3000)



    def _fide_import(self):

        dlg = FideSearchDialog(self)

        if dlg.exec():

            players = dlg.get_selected_players()

            for p in players:

                self.tournament.players.append(p)

            if players:

                self.status_bar.showMessage(f"{len(players)} oyuncu eklendi!", 3000)

                self._update_ui()



    def _import_player_list(self):

        dlg = PlayerListImportDialog(self)

        if dlg.exec():

            players = dlg.get_players()

            for p in players:

                self.tournament.players.append(p)

            if players:

                self.status_bar.showMessage(f"{len(players)} oyuncu listeden içe aktarıldı!", 5000)

                self._update_ui()



    def _generate_starting_rank(self):

        """Sort players by FIDE rules: Rating -> Title -> Alphabetical."""

        if not self.tournament.players:

            return

            

        def get_title_value(title):

            # Sort order for titles: GM > IM > FM > CM > WGM > WIM > WFM > WCM > NM > NONE

            order = {

                Title.GM: 10, Title.IM: 9, Title.FM: 8, Title.CM: 7,

                Title.WGM: 6, Title.WIM: 5, Title.WFM: 4, Title.WCM: 3,

                Title.NM: 2, Title.NONE: 1

            }

            return order.get(title, 0)

            

        self.tournament.players.sort(

            key=lambda p: (

                -p.rating,

                -get_title_value(p.title),

                p.surname.lower(),

                p.name.lower()

            )

        )

        self._update_ui()

        self.status_bar.showMessage("Başlangıç sıralaması oluşturuldu.", 3000)



    def _show_player_context_menu(self, position):

        row = self.player_table.rowAt(position.y())

        if row < 0 or row >= len(self.tournament.players):

            return

            

        player = self.tournament.players[row]

        menu = QMenu()

        

        # Withdraw action

        if player.is_active:

            withdraw_act = QAction("🚫 Turnuvadan Çek (Withdraw)", self)

            withdraw_act.triggered.connect(lambda: self._set_player_withdrawn(player, True))

            menu.addAction(withdraw_act)

        else:

            restore_act = QAction("✅ Turnuvaya Geri Al", self)

            restore_act.triggered.connect(lambda: self._set_player_withdrawn(player, False))

            menu.addAction(restore_act)

            

        menu.exec(self.player_table.viewport().mapToGlobal(position))

        

    def _set_player_withdrawn(self, player, withdrawn: bool):

        player.is_active = not withdrawn

        if withdrawn:

            player.withdrawn_after_round = self.tournament.current_round

        else:

            player.withdrawn_after_round = 0

        self._update_ui()

        status = "turnuvadan çekildi" if withdrawn else "turnuvaya geri alındı"

        self.status_bar.showMessage(f"{player.full_name} {status}.", 3000)



    def _generate_pairings(self):

        if not self.tournament.get_active_players():

            QMessageBox.warning(self, "Uyarıı", "Oyuncu eklenmemiş!")

            return



        if len(self.tournament.get_active_players()) < 2:

            QMessageBox.warning(self, "Uyarıı", "En az 2 oyuncu gerekli!")

            return



        # Check if current round is incomplete

        if self.tournament.rounds:

            last_round = self.tournament.rounds[-1]

            if not last_round.is_completed:

                QMessageBox.warning(self, "Uyarıı", "Mevcut tur henüz tamamlanmadı!")

                return



        if self.tournament.current_round >= self.tournament.num_rounds:

            QMessageBox.information(self, "Bilgi", "Tüm turlar tamamlandı!")

            return



        # Check for unpaired players and ask for confirmation

        unpaired_players = [p for p in self.tournament.players if not p.is_active or not p.is_registered]

        if unpaired_players:

            # Calculate missed rounds

            missed_rounds_map = {p.id: [] for p in self.tournament.players}

            for round_obj in self.tournament.rounds:

                paired_players = set()

                for m in round_obj.matches:

                    if m.white_id != "BYE": paired_players.add(m.white_id)

                    if m.black_id != "BYE": paired_players.add(m.black_id)

                for p in self.tournament.players:

                    if p.id not in paired_players:

                        missed_rounds_map[p.id].append(str(round_obj.round_number))

            

            dlg = UnpairedPlayersDialog(unpaired_players, missed_rounds_map, self)

            if not dlg.exec():

                return



        rnd = generate_pairings(self.tournament)

        if rnd:

            self.tournament.rounds.append(rnd)

            self._update_ui()

            self.tab_widget.setCurrentIndex(2)  # Switch to rounds tab

            self.status_bar.showMessage(f"Tur {rnd.round_number} eşleştirildi!", 3000)

        else:

            QMessageBox.warning(self, "Hata", "Eşleştirme oluşturulamadı!")



    def _complete_round(self):

        if not self.tournament.rounds:

            QMessageBox.warning(self, "Uyarıı", "Henüz eşleştirme yapılmamış!")

            return



        current_idx = self.round_combo.currentIndex()

        if current_idx < 0:

            return



        rnd = self.tournament.rounds[current_idx]

        if rnd.is_completed:

            QMessageBox.information(self, "Bilgi", "Bu tur zaten tamamlanmış!")

            return



        # Check all results

        for match in rnd.matches:

            if not match.result.is_decided and not match.is_bye:

                QMessageBox.warning(

                    self, "Uyarıı",

                    "Tüm maç sonuçları girilmeden tur tamamlanamaz!"

                )

                return



        rnd.is_completed = True

        self.tournament.current_round = rnd.round_number

        self._update_ui()

        self.status_bar.showMessage(f"Tur {rnd.round_number} tamamlandı!", 3000)



    def _delete_current_round(self):

        if not self.tournament.rounds:

            return



        current_idx = self.round_combo.currentIndex()

        if current_idx < 0:

            return



        rnd = self.tournament.rounds[current_idx]



        reply = QMessageBox.question(

            self, "Turu Sil",

            f"Tur {rnd.round_number} silinsin mi?",

            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No

        )

        if reply == QMessageBox.StandardButton.Yes:

            self.tournament.rounds.pop(current_idx)

            if self.tournament.rounds:

                self.tournament.current_round = max(

                    r.round_number for r in self.tournament.rounds if r.is_completed

                ) if any(r.is_completed for r in self.tournament.rounds) else 0

            else:

                self.tournament.current_round = 0

            self._update_ui()



    def _on_result_changed(self):

        self._refresh_standings()



    def _get_player_by_name(self, name: str) -> Player:

        for p in self.tournament.players:

            if p.full_name == name:

                return p

        return None



    def _on_standings_double_click(self, row, col):

        if not self.tournament.players: return

        if col == 3: # İsim sütunu

            item = self.standings_table.item(row, col)

            if item:

                p = self._get_player_by_name(item.text())

                if p:

                    dlg = PlayerDetailsDialog(p, self.tournament, self)

                    dlg.exec()



    def _on_crosstable_double_click(self, row, col):

        if not self.tournament.players: return

        if col == 2: # İsim sütunu

            item = self.crosstable_widget.item(row, col)

            if item:

                p = self._get_player_by_name(item.text())

                if p:

                    dlg = PlayerDetailsDialog(p, self.tournament, self)

                    dlg.exec()



    def _on_pairing_double_click(self, row, col):

        if not self.tournament.players: return

        if col in (2, 6): # Beyaz veya Siyah isim sütunu

            item = self.pairing_table.item(row, col)

            if item and item.text() != "BYE":

                p = self._get_player_by_name(item.text())

                if p:

                    dlg = PlayerDetailsDialog(p, self.tournament, self)

                    dlg.exec()



    def _apply_theme(self, theme: AppTheme):

        self.current_theme = theme

        stylesheet = get_stylesheet(theme)

        QApplication.instance().setStyleSheet(stylesheet)



    def closeEvent(self, event):

        if self.tournament.players:

            reply = QMessageBox.question(

                self, "Çıkış",

                "Kaydetmeden çıkmak istediğinize emin misiniz?",

                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No

            )

            if reply == QMessageBox.StandardButton.No:

                event.ignore()

                return



        # Clean up server and tunnels on exit

        if self.server_thread:

            self.server_thread.stop()

        if self.ngrok_process:

            try:

                subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe", "/T"], shell=True, capture_output=True)

            except: pass

        if self.ssh_process:

            self.ssh_process.terminate()

        if self.cf_process:

            # Kill process tree for npx/cloudflared

            if os.name == 'nt':

                try:

                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.cf_process.pid)], shell=True, capture_output=True)

                except: pass

            else:

                self.cf_process.terminate()

        

        event.accept()

    def _create_broadcast_tab(self):

        self.broadcast_tab = QWidget()

        layout = QVBoxLayout(self.broadcast_tab)



        # Server Status Group

        status_group = QGroupBox("Yayın Sunucusu Durumu")

        status_layout = QFormLayout(status_group)



        self.lbl_server_status = QLabel("Kapalı 🔴")

        self.lbl_server_status.setStyleSheet("color: red; font-weight: bold;")

        status_layout.addRow("Sunucu Durumu:", self.lbl_server_status)



        self.lbl_local_url = QLabel("-")
        self.lbl_local_url.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_local_url.setOpenExternalLinks(True)
        status_layout.addRow("Yerel Ağ Linki:", self.lbl_local_url)

        self.lbl_ngrok_url = QLabel("-")
        self.lbl_ngrok_url.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_ngrok_url.setOpenExternalLinks(True)
        self.lbl_ngrok_url.setStyleSheet("color: #2563eb; font-weight: bold;")
        status_layout.addRow("İnternet Linki:", self.lbl_ngrok_url)



        layout.addWidget(status_group)



        # Controls Group

        ctrl_group = QGroupBox("Kontrol Paneli")

        ctrl_layout = QVBoxLayout(ctrl_group)



        self.btn_toggle_server = QPushButton("🌐 Web Sunucusunu Başlat")

        self.btn_toggle_server.setFixedHeight(40)

        self.btn_toggle_server.clicked.connect(self._toggle_server)

        ctrl_layout.addWidget(self.btn_toggle_server)



        self.btn_copy_link = QPushButton("🔗 Linki Kopyala")

        self.btn_copy_link.setEnabled(False)

        self.btn_copy_link.clicked.connect(self._copy_broadcast_link)

        ctrl_layout.addWidget(self.btn_copy_link)



        layout.addWidget(ctrl_group)



        # ngrok Settings Group

        ngrok_group = QGroupBox("ngrok İnternet Yayını Ayarları")

        ngrok_layout = QFormLayout(ngrok_group)



        self.txt_ngrok_token = QLineEdit()

        self.txt_ngrok_token.setPlaceholderText("ngrok authtoken buraya yapıştırın...")

        self.txt_ngrok_token.setEchoMode(QLineEdit.EchoMode.Password)

        ngrok_layout.addRow("Auth Token:", self.txt_ngrok_token)



        self.btn_start_ngrok = QPushButton("🚀 Dünyaya Aç (ngrok Başlat)")

        self.btn_start_ngrok.clicked.connect(self._start_ngrok)

        ngrok_layout.addRow("", self.btn_start_ngrok)



        layout.addWidget(ngrok_group)



        # SSH Tunnel Group (Zero Login)

        ssh_group = QGroupBox("Hızlı İnternet Yayını (Üyelik Gerektirmez)")

        ssh_layout = QVBoxLayout(ssh_group)

        

        # Cloudflare Button

        self.btn_start_cf = QPushButton("☁️ Cloudflare Tunnel ile Başlat (Önerilen)")

        self.btn_start_cf.setFixedHeight(35)

        self.btn_start_cf.setStyleSheet("background-color: #f38020; color: white; font-weight: bold;")

        self.btn_start_cf.clicked.connect(self._toggle_cloudflare_tunnel)
        ssh_layout.addWidget(self.btn_start_cf)

        # SSH Button (Old)
        self.btn_start_ssh = QPushButton("⚡ localhost.run ile Başlat (Alternatif)")
        self.btn_start_ssh.clicked.connect(self._toggle_ssh_tunnel)

        ssh_layout.addWidget(self.btn_start_ssh)

        

        layout.addWidget(ssh_group)

        

        # Connection Log

        log_group = QGroupBox("Bağlantı Günlüğü")

        log_layout = QVBoxLayout(log_group)

        self.txt_broadcast_log = QTextEdit()

        self.txt_broadcast_log.setReadOnly(True)

        self.txt_broadcast_log.setFixedHeight(100)

        self.txt_broadcast_log.setStyleSheet("font-family: Consolas; font-size: 10px; background: #000; color: #0f0;")

        log_layout.addWidget(self.txt_broadcast_log)

        layout.addWidget(log_group)

        

        info_lbl = QLabel("Not: ngrok veya SSH kullanarak internetten yayın yapmak için önce 'Web Sunucusunu Başlat' butonuna basmalısınız.")

        info_lbl.setWordWrap(True)

        info_lbl.setStyleSheet("color: #666; font-style: italic;")

        layout.addWidget(info_lbl)



        layout.addStretch()

        self.tab_widget.addTab(self.broadcast_tab, "📡 Canlı Yayın")



    def _toggle_server(self):

        if not self.server_thread:

            try:

                self.server_thread = LiveServerThread(self.tournament, port=8080)

                self.server_thread.log_signal.connect(self._on_ssh_log)

                self.server_thread.start()

                

                # Get local IP

                hostname = socket.gethostname()

                local_ip = socket.gethostbyname(hostname)

                self.lbl_local_url.setText(f'<a href="http://{local_ip}:8080" style="color: #2563eb;">http://{local_ip}:8080</a>')

                

                self.lbl_server_status.setText("Açık 🟢")

                self.lbl_server_status.setStyleSheet("color: green; font-weight: bold;")

                self.btn_toggle_server.setText("🛑 Web Sunucusunu Durdur")

                self.btn_copy_link.setEnabled(True)

                self.status_bar.showMessage("Web sunucusu başlatıldı.", 3000)

            except Exception as e:

                QMessageBox.critical(self, "Hata", f"Sunucu başlatılamadı: {e}")

        else:

            self.server_thread.stop()

            self.server_thread = None

            self.lbl_server_status.setText("Kapalı 🔴")

            self.lbl_server_status.setStyleSheet("color: red; font-weight: bold;")

            self.lbl_local_url.setText("-")

            self.btn_toggle_server.setText("🌐 Web Sunucusunu Başlat")

            self.btn_copy_link.setEnabled(False)

            self.status_bar.showMessage("Web sunucusu durduruldu.", 3000)



    def _start_ngrok(self):

        token = self.txt_ngrok_token.text().strip()

        if token:

            subprocess.run(["ngrok", "config", "add-authtoken", token], shell=True)

        

        try:

            # Start ngrok process

            self.ngrok_process = subprocess.Popen(

                ["ngrok", "http", "8080"], 

                shell=True, 

                stdout=subprocess.PIPE, 

                stderr=subprocess.PIPE

            )

            self.ngrok_timer.start(2000) # Poll every 2 seconds for URL

            self.btn_start_ngrok.setEnabled(False)

            self.btn_start_ngrok.setText("⏳ ngrok Başlatılıyor...")

        except Exception as e:

            QMessageBox.warning(self, "ngrok Hatasıı", f"ngrok başlatılamadı. Dosyanın mevcut ve PATH'de olduğundan emin olun.\nHata: {e}")



    def _update_ngrok_status(self):

        url = self._get_ngrok_url()

        if url:

            self.lbl_ngrok_url.setText(url)

            self.btn_start_ngrok.setText("✅ ngrok Çalışıyor")

            self.ngrok_timer.stop()

            self.status_bar.showMessage(f"İnternet yayını aktif: {url}", 5000)



    def _get_ngrok_url(self):

        try:

            with urllib.request.urlopen("http://localhost:4040/api/tunnels") as response:

                data = json.loads(response.read().decode())

                for tunnel in data['tunnels']:

                    if tunnel['proto'] == 'https':

                        return tunnel['public_url']

        except:

            pass

        return None



    def _copy_broadcast_link(self):

        url = self.lbl_ngrok_url.text()

        if url == "-":

            url = self.lbl_local_url.text()

        

        if url != "-":

            QApplication.clipboard().setText(url)

            self.status_bar.showMessage("Link kopyalandı!", 2000)



    def _toggle_ssh_tunnel(self):
        if self.ssh_process and self.ssh_process.poll() is None:
            try:
                self.ssh_process.terminate()
                self.ssh_process.wait(1000)
            except:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.ssh_process.pid)], shell=True, capture_output=True)
            self.ssh_process = None
            self.lbl_ngrok_url.setText("-")
            self.btn_start_ssh.setText("⚡ localhost.run ile Başlat (Alternatif)")
            self.btn_start_cf.setEnabled(True)
            self.txt_broadcast_log.append("SSH tüneli durduruldu.")
            return

        if not self.server_thread:
            QMessageBox.warning(self, "Uyarı", "Önce web sunucusunu başlatmalısınız!")
            return

        try:
            self.txt_broadcast_log.append("SSH bağlantısı başlatılıyor (localhost.run)...")
            self.ssh_process = subprocess.Popen(
                ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-R", "80:127.0.0.1:8080", "nokey@localhost.run"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.btn_start_ssh.setText("🛑 SSH Durdur")
            self.btn_start_cf.setEnabled(False)
            
            self.ssh_reader = TunnelReader(self.ssh_process)
            self.ssh_reader.url_found.connect(self._on_ssh_url_found)
            self.ssh_reader.log_received.connect(self._on_ssh_log)
            self.ssh_reader.start()
        except Exception as e:
            self.txt_broadcast_log.append(f"HATA: {e}")
            QMessageBox.warning(self, "SSH Hatası", f"SSH başlatılamadı: {e}")



    def _on_ssh_log(self, text):

        self.txt_broadcast_log.append(text.strip())



    def _on_ssh_url_found(self, url):

        self.txt_broadcast_log.append(f"<b>✓ Link Tespit Edildi:</b> <a href='{url}'>{url}</a>")

        self.lbl_ngrok_url.setText(f'<a href="{url}" style="color: #2563eb;">{url}</a>')

        self.lbl_ngrok_url.setOpenExternalLinks(True)

        self.btn_start_ssh.setText("✅ Hızlı Yayın Aktif")

        self.btn_start_cf.setText("✅ Cloudflare Aktif")

        self.status_bar.showMessage(f"Hızlı yayın aktif: {url}", 5000)

        self.btn_copy_link.setEnabled(True)

        

        # Add a tip for Cloudflare 1033 error

        if "trycloudflare.com" in url:

            self.txt_broadcast_log.append("<br><span style='color: #fbbf24;'>💡 İpucu: Eğer 'Error 1033' devam ederse:<br>"

                                         "1. Güvenlik duvarınızın (Firewall) bağlantıyı engellemediğinden emin olun.<br>"

                                         "2. Web sunucusunu durdurup tekrar başlatmayı deneyin.<br>"

                                         "3. Tünelin tam oturması için 10-15 saniye bekleyin.</span>")



    def _toggle_cloudflare_tunnel(self):
        if self.cf_process and self.cf_process.poll() is None:
            try:
                self.cf_process.terminate()
                self.cf_process.wait(1000)
            except:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.cf_process.pid)], shell=True, capture_output=True)
            self.cf_process = None
            self.lbl_ngrok_url.setText("-")
            self.btn_start_cf.setText("☁️ Cloudflare Tunnel ile Başlat (Önerilen)")
            self.btn_start_ssh.setEnabled(True)
            self.txt_broadcast_log.append("Cloudflare tüneli durduruldu.")
            return

        if not self.server_thread:
            QMessageBox.warning(self, "Uyarı", "Önce web sunucusunu başlatmalısınız!")
            return

        if os.name == 'nt':
            try:
                subprocess.run(['taskkill', '/F', '/IM', 'cloudflared.exe', '/T'], shell=True, capture_output=True)
            except: pass

        npx_path = shutil.which("npx")
        cf_path = shutil.which("cloudflared")
        
        if npx_path:
            self._run_cloudflare_process(["npx", "-y", "cloudflared", "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8080"], is_npx=True)
            return

        if cf_path:
            self._run_cloudflare_process([cf_path, "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8080"])
            return

        possible_paths = [
            os.path.join(os.getcwd(), "cloudflared.exe"),
            os.path.join(os.getcwd(), "dist", "cloudflared.exe"),
            "cloudflared.exe"
        ]
        
        for local_exe in possible_paths:
            if os.path.exists(local_exe):
                self._run_cloudflare_process([local_exe, "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8080"])
                return

        reply = QMessageBox.question(self, "Araç Eksik", "Cloudflare Tunnel bulunamadı. İndirmek ister misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.btn_start_cf.setText("⏳ İndiriliyor...")
            self.cf_dl = CloudflareDownloader()
            self.cf_dl.finished.connect(lambda path: self._run_cloudflare_process([path, "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8080"]))
            self.cf_dl.start()



    def _on_download_error(self, err):
        self.btn_start_cf.setEnabled(True)
        self.btn_start_cf.setText("☁️ Cloudflare Tunnel ile Başlat")
        self.txt_broadcast_log.append(f"İndirme Hatasııı: {err}")
        QMessageBox.warning(self, "Hata", f"Araç indirilemedi: {err}")

    def _run_cloudflare_process(self, cmd_list, is_npx=False):
        try:
            self.txt_broadcast_log.append(f"Cloudflare komutu çalıştırılıyor: {' '.join(cmd_list)}")
            
            # Use shell=True for consistent environment on Windows
            cmd_str = " ".join(f'"{ c}"' if " " in c else c for c in cmd_list)
            self.cf_process = subprocess.Popen(
                cmd_str,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.btn_start_ssh.setEnabled(False)
            self.btn_start_cf.setText("🛑 CF Durdur")
            
            self.cf_reader = TunnelReader(self.cf_process)
            self.cf_reader.url_found.connect(self._on_ssh_url_found)
            self.cf_reader.log_received.connect(self._on_ssh_log)
            self.cf_reader.start()
            
        except Exception as e:
            self.txt_broadcast_log.append(f"HATA: {e}")
            self.btn_start_cf.setEnabled(True)
            self.btn_start_cf.setText("☁️ Cloudflare Tunnel ile Başlat")
            QMessageBox.warning(self, "Cloudflare Hatasıı", f"Tünel başlatılamadı: {e}")

