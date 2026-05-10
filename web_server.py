import http.server
import json
import threading
import os
import sys
from PyQt6.QtCore import pyqtSignal, QObject
from tiebreak import calculate_all_standings

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    bases = []
    if hasattr(sys, '_MEIPASS'):
        bases.append(sys._MEIPASS)
    bases.append(os.path.dirname(os.path.abspath(__file__)))
    bases.append(os.path.abspath("."))
    
    for base in bases:
        full_path = os.path.normpath(os.path.join(base, relative_path))
        if os.path.exists(full_path):
            return full_path
    return os.path.join(bases[0] if bases else os.path.abspath("."), relative_path)

class TournamentHandler(http.server.BaseHTTPRequestHandler):
    server_instance = None 

    def log_message(self, format, *args):
        if self.server_instance:
            self.server_instance.log_signal.emit(format % args)

    def do_GET(self):
        if self.server_instance:
            self.server_instance.log_signal.emit(f"İstek geldi: {self.path}")

        path = self.path.split('?')[0].strip('/')
        
        if path in ('', 'index.html', 'index', 'dashboard', 'live'):
            self.serve_embedded_html()
        elif path == 'api/data':
            self.serve_json()
        else:
            self.serve_file(os.path.join('resources', path), 'text/plain')

    def serve_embedded_html(self):
        try:
            content = self.get_dashboard_html().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            if self.server_instance:
                self.server_instance.log_signal.emit(f"Gömülü HTML hatası: {e}")
            self.send_error(500)

    def get_dashboard_html(self):
        # Fallback to external file if exists
        full_path = resource_path(os.path.join('resources', 'live_dashboard.html'))
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except: pass
        
        return """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Elite Chess Canlı Turnuva Takibi</title>
    <style>
        :root {
            --bg-color: #f0f2f5; --card-bg: #ffffff; --text-color: #1f2937;
            --primary: #2563eb; --secondary: #64748b; --accent: #f59e0b;
            --border: #e5e7eb; --header-bg: #1e3a5f; --header-text: #ffffff;
        }
        [data-theme="dark"] {
            --bg-color: #0f172a; --card-bg: #1e293b; --text-color: #f1f5f9;
            --primary: #3b82f6; --secondary: #94a3b8; --accent: #fbbf24;
            --border: #334155; --header-bg: #0f172a; --header-text: #ffffff;
        }
        * { box-sizing: border-box; transition: background-color 0.2s, color 0.2s; }
        body { font-family: 'Inter', system-ui, sans-serif; margin: 0; background: var(--bg-color); color: var(--text-color); }
        .header { background: var(--header-bg); color: var(--header-text); padding: 1rem; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .container { max-width: 1000px; margin: 1rem auto; padding: 0 1rem; }
        .tabs { display: flex; background: var(--card-bg); border-radius: 12px; padding: 0.25rem; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .tab { flex: 1; padding: 0.75rem; text-align: center; cursor: pointer; border-radius: 10px; font-weight: 600; color: var(--secondary); }
        .tab.active { background: var(--primary); color: white; }
        .card { background: var(--card-bg); border-radius: 12px; padding: 1rem; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); margin-bottom: 1rem; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 0.75rem; color: var(--secondary); font-size: 0.8rem; border-bottom: 2px solid var(--border); }
        td { padding: 0.75rem; border-bottom: 1px solid var(--border); }
        .rank { font-weight: bold; width: 40px; }
        .score { font-weight: 800; color: var(--primary); text-align: center; }
        .clickable-row { cursor: pointer; }
        .clickable-row:hover { background: rgba(0,0,0,0.02); }
        [data-theme="dark"] .clickable-row:hover { background: rgba(255,255,255,0.03); }
        
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); backdrop-filter: blur(4px); }
        .modal-content { background: var(--card-bg); margin: 5% auto; padding: 1.5rem; border-radius: 16px; width: 95%; max-width: 600px; max-height: 85vh; overflow-y: auto; position: relative; }
        .close { float: right; font-size: 1.5rem; cursor: pointer; font-weight: bold; }
        
        .round-nav { display: flex; gap: 0.5rem; overflow-x: auto; padding-bottom: 0.5rem; margin-bottom: 1rem; }
        .round-btn { padding: 0.5rem 1rem; border: 1px solid var(--border); border-radius: 20px; cursor: pointer; background: var(--card-bg); white-space: nowrap; font-weight: 600; color: var(--secondary); }
        .round-btn.active { background: var(--primary); color: white; border-color: var(--primary); }
        
        .badge { padding: 2px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; }
        .badge-w { background: #e2e8f0; color: #475569; border: 1px solid #cbd5e1; }
        .badge-b { background: #1e293b; color: #f8fafc; border: 1px solid #334155; }
        .res-win { color: #16a34a; }
        .res-loss { color: #dc2626; }
        .footer { text-align: center; color: var(--secondary); font-size: 0.75rem; margin: 2rem 0; }
    </style>
</head>
<body data-theme="dark">
    <div class="header">
        <h1 id="tournament-name">Yükleniyor...</h1>
        <button onclick="toggleTheme()" style="background:none; border:1px solid white; color:white; border-radius:50%; width:36px; height:36px; cursor:pointer; display:flex; align-items:center; justify-content:center;">🌓</button>
    </div>
    <div class="container">
        <div class="tabs">
            <div class="tab active" onclick="switchTab('standings')" id="tab-standings">Sıralama</div>
            <div class="tab" onclick="switchTab('pairings')" id="tab-pairings">Eşlendirmeler</div>
        </div>
        <div id="content-standings">
            <div class="card">
                <table>
                    <thead><tr><th>#</th><th>Sporcu</th><th style="text-align:center">Puan</th></tr></thead>
                    <tbody id="standings-body"></tbody>
                </table>
            </div>
        </div>
        <div id="content-pairings" style="display:none">
            <div class="round-nav" id="round-nav"></div>
            <div id="pairings-list"></div>
        </div>
        <div class="footer">Elite Chess Tournament Manager | Designed & Developed by Emir Cica</div>
    </div>

    <div id="playerModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <div id="player-detail-content"></div>
        </div>
    </div>

    <script>
        let tournamentData = null;
        let selectedRound = 0;

        function toggleTheme() {
            const theme = document.body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            document.body.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
        }
        if (localStorage.getItem('theme') === 'light') document.body.setAttribute('data-theme', 'light');

        function switchTab(tab) {
            document.getElementById('tab-standings').className = 'tab' + (tab === 'standings' ? ' active' : '');
            document.getElementById('tab-pairings').className = 'tab' + (tab === 'pairings' ? ' active' : '');
            document.getElementById('content-standings').style.display = tab === 'standings' ? 'block' : 'none';
            document.getElementById('content-pairings').style.display = tab === 'pairings' ? 'block' : 'none';
        }

        async function update() {
            try {
                const res = await fetch('/api/data?t=' + Date.now());
                tournamentData = await res.json();
                if (selectedRound === 0) selectedRound = tournamentData.current_round;
                render();
            } catch(e) { document.getElementById('tournament-name').innerText = "Bağlantı Bekleniyor..."; }
        }

        function render() {
            if (!tournamentData) return;
            document.getElementById('tournament-name').innerText = tournamentData.name;
            
            document.getElementById('standings-body').innerHTML = tournamentData.standings.map(p => `
                <tr class="clickable-row" onclick="showPlayer('${p.id}')">
                    <td class="rank">${p.rank}</td>
                    <td><small style="color:var(--accent)">${p.title || ''}</small> <b>${p.name}</b><br><small>${p.rating} | ${p.club || ''}</small></td>
                    <td class="score">${p.score.toFixed(1)}</td>
                </tr>
            `).join('');

            // Round Nav - Only show rounds that have data
            let navHtml = "";
            tournamentData.rounds.forEach(r => {
                navHtml += `<button class="round-btn ${selectedRound===r.round_number?'active':''}" onclick="setRound(${r.round_number})">Tur ${r.round_number}</button>`;
            });
            document.getElementById('round-nav').innerHTML = navHtml;

            const rnd = tournamentData.rounds.find(r => r.round_number === selectedRound);
            if (rnd) {
                let unpairedHtml = "";
                const hasUnpaired = tournamentData.unpaired && tournamentData.unpaired.length > 0;
                const hasWithdrawn = tournamentData.withdrawn && tournamentData.withdrawn.length > 0;

                if ((hasUnpaired || hasWithdrawn) && selectedRound === tournamentData.current_round) {
                    let items = "";
                    if (hasUnpaired) {
                        items += `<h3 style="font-size:0.75rem; color:var(--secondary); margin: 0.5rem 0; text-transform:uppercase;">Eşleşmeyenler</h3>`;
                        items += `<div style="display:flex; flex-wrap:wrap; gap:0.5rem; margin-bottom:1rem">`;
                        items += tournamentData.unpaired.map(name => `<span class="badge badge-w" style="background:rgba(37, 99, 235, 0.1); color:var(--primary); border-color:var(--primary)">${name}</span>`).join('');
                        items += `</div>`;
                    }
                    if (hasWithdrawn) {
                        items += `<h3 style="font-size:0.75rem; color:var(--secondary); margin: 0.5rem 0; text-transform:uppercase;">Çekilen / Ayrılanlar</h3>`;
                        items += `<div style="display:flex; flex-wrap:wrap; gap:0.5rem">`;
                        items += tournamentData.withdrawn.map(name => `<span class="badge badge-w" style="opacity:0.6; text-decoration:line-through">${name}</span>`).join('');
                        items += `</div>`;
                    }

                    unpairedHtml = `
                        <div style="margin-top:1.5rem; border-top:1px solid var(--border); padding-top:1rem">
                            ${items}
                        </div>
                    `;
                }

                document.getElementById('pairings-list').innerHTML = `
                    <div class="card">
                        <table>
                            ${rnd.matches.map(m => `
                                <tr>
                                    <td style="width:30px"><small>${m.board}</small></td>
                                    <td style="width:40%; cursor:pointer; color:var(--primary)" onclick="showPlayer('${m.white_id}')">
                                        <b>${m.white}</b><br><small style="color:var(--secondary)">${m.white_rating}</small>
                                    </td>
                                    <td style="text-align:center; font-weight:bold; width:60px">${m.result}</td>
                                    <td style="text-align:right; width:40%; cursor:pointer; color:var(--primary)" onclick="${m.black_id !== 'BYE' ? `showPlayer('${m.black_id}')` : ''}">
                                        <b>${m.black}</b><br><small style="color:var(--secondary)">${m.black_rating}</small>
                                    </td>
                                </tr>
                            `).join('')}
                        </table>
                        ${unpairedHtml}
                    </div>
                `;
            } else {
                document.getElementById('pairings-list').innerHTML = '<div class="card">Bu tur için eşlendirme bulunamadı.</div>';
            }
        }

        function setRound(r) { selectedRound = r; render(); }

        function showPlayer(id) {
            const p = tournamentData.standings.find(x => x.id == id);
            if (!p) return;
            const content = `
                <h2 style="margin-top:0">${p.name}</h2>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:1.5rem; background:rgba(0,0,0,0.05); padding:1rem; border-radius:12px; font-size:0.9rem">
                    <div><b>UKD:</b> ${p.ukd || '-'}</div>
                    <div><b>ELO:</b> ${p.elo || '-'}</div>
                    <div><b>Rating:</b> ${p.rating}</div>
                    <div><b>Perf. Rating:</b> <span style="color:var(--primary); font-weight:800">${p.perf || '-'}</span></div>
                </div>
                <h3 style="font-size:1rem; margin-bottom:0.5rem">Maç Geçmişi</h3>
                <table style="font-size:0.85rem">
                    <thead><tr><th>Tur</th><th>Rakip</th><th>Renk</th><th>Sonuç</th></tr></thead>
                    <tbody>
                        ${p.matches.map(m => `
                            <tr>
                                <td>${m.round}</td>
                                <td>${m.opponent} <small>(${m.opp_rating})</small></td>
                                <td><span class="badge badge-${m.color.toLowerCase()}">${m.color === 'W' ? 'B' : 'S'}</span></td>
                                <td class="${m.result === '1'?'res-win':m.result === '0'?'res-loss':''}" style="font-size:1.1rem"><b>${m.result}</b></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            document.getElementById('player-detail-content').innerHTML = content;
            document.getElementById('playerModal').style.display = "block";
        }

        function closeModal() { document.getElementById('playerModal').style.display = "none"; }
        window.onclick = e => { if(e.target == document.getElementById('playerModal')) closeModal(); }

        update();
        setInterval(update, 5000);
    </script>
</body>
</html>"""

    def serve_file(self, filepath, content_type):
        try:
            full_path = resource_path(filepath)
            if not os.path.exists(full_path):
                self.send_error(404)
                return
            with open(full_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(content)
        except:
            self.send_error(404)

    def serve_json(self):
        tournament = self.server_instance.tournament if self.server_instance else None
        if not tournament:
            self.send_error(500)
            return
        try:
            data = self._prepare_data(tournament)
            content = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            if self.server_instance:
                self.server_instance.log_signal.emit(f"JSON Hatası: {e}")
            self.send_error(500)

    def _prepare_data(self, t):
        standings = calculate_all_standings(t)
        standings_json = []
        for s in standings:
            p = s["player"]
            opp_ratings = []
            player_matches = []
            for rnd in t.rounds:
                for m in rnd.matches:
                    opp = None
                    res = ""
                    color = ""
                    if m.white_id == p.id:
                        opp = t.get_player_by_id(m.black_id)
                        # Points for White
                        if not m.result.is_decided:
                            pts = "-"
                        else:
                            res_val = m.result.value
                            if res_val == "1-0": pts = "1"
                            elif res_val == "0-1": pts = "0"
                            elif res_val == "1/2-1/2": pts = "½"
                            else: pts = "0"
                        color = "W"
                    elif m.black_id == p.id:
                        opp = t.get_player_by_id(m.white_id)
                        # Points for Black (Inverted)
                        if not m.result.is_decided:
                            pts = "-"
                        else:
                            res_val = m.result.value
                            if res_val == "1-0": pts = "0"
                            elif res_val == "0-1": pts = "1"
                            elif res_val == "1/2-1/2": pts = "½"
                            else: pts = "0"
                        color = "B"
                    
                    if opp or (m.white_id == p.id and m.black_id == "BYE"):
                        if opp: opp_ratings.append(opp.rating)
                        player_matches.append({
                            "round": rnd.round_number,
                            "opponent": opp.full_name if opp else "BYE",
                            "opp_rating": opp.rating if opp else 0,
                            "result": pts if opp else "1",
                            "color": color
                        })

            avg_opp_rating = sum(opp_ratings) / len(opp_ratings) if opp_ratings else 0
            score_pct = s["score"] / t.current_round if t.current_round > 0 else 0
            dp = 800 * (score_pct - 0.5) 
            perf_rating = int(avg_opp_rating + dp) if opp_ratings else 0

            standings_json.append({
                "id": p.id,
                "rank": s["rank"],
                "name": p.full_name,
                "title": p.display_title,
                "rating": p.rating,
                "ukd": p.ukd,
                "elo": p.elo,
                "club": p.club,
                "score": s["score"],
                "perf": perf_rating,
                "matches": player_matches,
                "tiebreaks": {tb.value: s["tiebreaks"].get(tb, 0.0) for tb in t.tiebreak_order}
            })

        rounds_json = []
        for r in t.rounds:
            matches_json = []
            for m in r.matches:
                wp = t.get_player_by_id(m.white_id)
                bp = t.get_player_by_id(m.black_id) if m.black_id != "BYE" else None
                matches_json.append({
                    "board": m.board,
                    "white_id": m.white_id,
                    "white": wp.full_name if wp else m.white_id,
                    "white_rating": wp.rating if wp else 0,
                    "black_id": m.black_id,
                    "black": bp.full_name if bp else "BYE",
                    "black_rating": bp.rating if bp else 0,
                    "result": m.result.value,
                    "is_completed": m.result.is_decided
                })
            rounds_json.append({
                "round_number": r.round_number,
                "is_completed": r.is_completed,
                "matches": matches_json
            })

        return {
            "name": t.name,
            "type": t.tournament_type.value,
            "current_round": t.current_round,
            "num_rounds": t.num_rounds,
            "standings": standings_json,
            "rounds": rounds_json,
            "player_count": len(t.players),
            "unpaired": [p.full_name for p in t.players if p.is_active and p.is_registered and p.id not in [m.white_id for rnd in t.rounds if rnd.round_number == t.current_round for m in rnd.matches] and p.id not in [m.black_id for rnd in t.rounds if rnd.round_number == t.current_round for m in rnd.matches]],
            "withdrawn": [p.full_name for p in t.players if not p.is_active]
        }

class LiveServerThread(threading.Thread):
    class Signaler(QObject):
        log_signal = pyqtSignal(str)

    def __init__(self, tournament, port=8000):
        super().__init__(daemon=True)
        self.tournament = tournament
        self.port = port
        self.httpd = None
        self.signaler = self.Signaler()
        self.log_signal = self.signaler.log_signal

    def run(self):
        handler = TournamentHandler
        handler.server_instance = self
        try:
            self.httpd = http.server.ThreadingHTTPServer(('0.0.0.0', self.port), handler)
            self.log_signal.emit(f"Sunucu başlatıldı: port {self.port}")
            self.httpd.serve_forever()
        except Exception as e:
            self.log_signal.emit(f"Sunucu hatası: {e}")

    def update_tournament(self, new_tournament):
        self.tournament = new_tournament

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
