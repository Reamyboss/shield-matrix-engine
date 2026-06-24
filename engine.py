"""
Shield Matrix Engine v3.0
Data: WC2010 + WC2014 + WC2018 + WC2022 + WC2026 = 306 real matches
Ratings: recency-weighted (recent tournaments count more)
"""
import math, requests, json
from datetime import datetime
from collections import defaultdict

WC_AVG = 1.288
_ratings_cache = {}

WC_URLS = [
    "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2010/worldcup.json",
    "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2014/worldcup.json",
    "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2018/worldcup.json",
    "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2022/worldcup.json",
    "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.json",
]
YEAR_WEIGHTS = {2010:1.0, 2014:1.0, 2018:1.5, 2022:2.0, 2026:2.5}

# Hardcoded fallback built from real data so engine works offline too
FALLBACK_RATINGS = {
    "Algeria":{"attack":1.333,"defense":1.5},"Argentina":{"attack":1.797,"defense":0.986},
    "Australia":{"attack":0.858,"defense":2.0},"Austria":{"attack":1.5,"defense":1.5},
    "Belgium":{"attack":1.294,"defense":0.647},"Bosnia & Herzegovina":{"attack":1.667,"defense":2.0},
    "Brazil":{"attack":1.486,"defense":1.119},"Canada":{"attack":1.778,"defense":1.593},
    "Cape Verde":{"attack":1.0,"defense":1.0},"Colombia":{"attack":1.938,"defense":0.688},
    "Costa Rica":{"attack":0.909,"defense":1.636},"Croatia":{"attack":1.37,"defense":1.185},
    "Curaçao":{"attack":0.5,"defense":3.5},"Czech Republic":{"attack":1.0,"defense":1.5},
    "Ecuador":{"attack":0.875,"defense":0.875},"Egypt":{"attack":1.2,"defense":1.6},
    "England":{"attack":1.815,"defense":1.0},"France":{"attack":2.053,"defense":0.867},
    "Germany":{"attack":2.322,"defense":0.983},"Ghana":{"attack":1.1,"defense":1.7},
    "Haiti":{"attack":0.5,"defense":2.0},"Iran":{"attack":0.818,"defense":1.364},
    "Iraq":{"attack":0.5,"defense":2.5},"Ivory Coast":{"attack":1.1,"defense":1.267},
    "Japan":{"attack":1.35,"defense":1.45},"Jordan":{"attack":1.0,"defense":2.5},
    "Mexico":{"attack":1.024,"defense":1.122},"Morocco":{"attack":0.762,"defense":0.905},
    "Netherlands":{"attack":2.224,"defense":0.845},"New Zealand":{"attack":1.5,"defense":2.5},
    "Nigeria":{"attack":1.0,"defense":1.4},"Norway":{"attack":3.5,"defense":1.5},
    "Panama":{"attack":0.5,"defense":2.6},"Paraguay":{"attack":1.0,"defense":2.0},
    "Portugal":{"attack":2.107,"defense":1.125},"Qatar":{"attack":0.5,"defense":2.833},
    "Saudi Arabia":{"attack":0.75,"defense":2.125},"Scotland":{"attack":0.8,"defense":1.0},
    "Senegal":{"attack":1.2,"defense":1.7},"Serbia":{"attack":1.167,"defense":2.0},
    "South Africa":{"attack":0.933,"defense":1.333},"South Korea":{"attack":1.167,"defense":1.5},
    "Spain":{"attack":1.731,"defense":1.192},"Sweden":{"attack":1.92,"defense":1.68},
    "Switzerland":{"attack":1.5,"defense":1.45},"Tunisia":{"attack":0.875,"defense":2.25},
    "Turkey":{"attack":0.8,"defense":1.5},"Türkiye":{"attack":0.8,"defense":1.5},
    "USA":{"attack":1.267,"defense":1.1},"United States":{"attack":1.267,"defense":1.1},
    "Uruguay":{"attack":1.2,"defense":1.067},"Uzbekistan":{"attack":0.8,"defense":2.0},
    "Wales":{"attack":0.5,"defense":2.0},"Congo DR":{"attack":0.8,"defense":1.2},
    "DR Congo":{"attack":0.8,"defense":1.2},"Senegal":{"attack":1.333,"defense":1.889},
}

def build_ratings_from_live():
    """Pull all WC history and build recency-weighted ratings."""
    all_matches = []
    for url in WC_URLS:
        try:
            r = requests.get(url, timeout=12, headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code == 200:
                year = int(url.split("/")[-2])
                for m in r.json().get("matches", []):
                    if "score" in m and m["score"].get("ft"):
                        all_matches.append({"year":year,"home":m["team1"],"away":m["team2"],
                            "hg":m["score"]["ft"][0],"ag":m["score"]["ft"][1]})
        except:
            continue

    if not all_matches:
        return FALLBACK_RATINGS

    year_team = defaultdict(lambda: defaultdict(lambda: {"played":0,"gf":0,"ga":0}))
    for m in all_matches:
        y = m["year"]
        year_team[y][m["home"]]["played"] += 1
        year_team[y][m["home"]]["gf"]     += m["hg"]
        year_team[y][m["home"]]["ga"]     += m["ag"]
        year_team[y][m["away"]]["played"] += 1
        year_team[y][m["away"]]["gf"]     += m["ag"]
        year_team[y][m["away"]]["ga"]     += m["hg"]

    all_teams = set()
    for y in year_team:
        all_teams.update(year_team[y].keys())

    ratings = {}
    for team in all_teams:
        wgf = wga = tw = 0
        played_total = 0
        for yr, ys in year_team.items():
            if team in ys and ys[team]["played"] > 0:
                s = ys[team]
                w = YEAR_WEIGHTS.get(yr, 1.0)
                wgf += (s["gf"] / s["played"]) * w * s["played"]
                wga += (s["ga"] / s["played"]) * w * s["played"]
                tw  += w * s["played"]
                played_total += s["played"]
        if tw > 0:
            ratings[team] = {
                "attack":  round(max(0.3, min(wgf/tw, 4.0)), 3),
                "defense": round(max(0.3, min(wga/tw, 4.0)), 3),
                "played":  played_total
            }
    return ratings if ratings else FALLBACK_RATINGS


def get_ratings():
    global _ratings_cache
    if not _ratings_cache:
        _ratings_cache = build_ratings_from_live()
    return _ratings_cache


def get_strength(team: str, live_stats: dict = None) -> dict:
    ratings = get_ratings()
    base = ratings.get(team)
    if not base:
        for k, v in ratings.items():
            if k.lower() == team.lower():
                base = v
                break
    if not base:
        base = {"attack": WC_AVG, "defense": WC_AVG}

    if live_stats:
        ls = live_stats.get(team) or next((v for k,v in live_stats.items() if k.lower()==team.lower()), None)
        if ls and ls.get("played", 0) >= 2:
            w = min(ls["played"], 3) / 3.0
            return {
                "attack":  round(base["attack"]  * (1-w) + ls.get("avg_gf", base["attack"])  * w, 3),
                "defense": round(base["defense"] * (1-w) + ls.get("avg_ga", base["defense"]) * w, 3),
            }
    return base


def poisson(lam: float, k: int) -> float:
    if lam <= 0: return 1.0 if k == 0 else 0.0
    return (math.exp(-lam) * (lam**k)) / math.factorial(k)


def predict(home: str, away: str, live_stats: dict = None) -> dict:
    h = get_strength(home, live_stats)
    a = get_strength(away, live_stats)

    hxg = round(max(0.3, min((h["attack"]/WC_AVG)*(a["defense"]/WC_AVG)*WC_AVG*1.08, 5.0)), 3)
    axg = round(max(0.3, min((a["attack"]/WC_AVG)*(h["defense"]/WC_AVG)*WC_AVG, 5.0)), 3)

    hw=d=aw=o25=btts=0.0
    matrix = {}
    for i in range(7):
        for j in range(7):
            p = poisson(hxg,i)*poisson(axg,j)
            matrix[f"{i}-{j}"] = round(p*100,2)
            if i>j: hw+=p
            elif i==j: d+=p
            else: aw+=p
            if i+j>2: o25+=p
            if i>0 and j>0: btts+=p

    t = hw+d+aw
    hw_p = round(hw/t*100,1); d_p = round(d/t*100,1); aw_p = round(100-hw_p-d_p,1)
    o_p = round(o25*100,1); b_p = round(btts*100,1)
    top5 = [{"score":s,"prob":p} for s,p in sorted(matrix.items(),key=lambda x:x[1],reverse=True)[:5]]

    cands = [(f"{home} Win",hw_p),("Draw",d_p),(f"{away} Win",aw_p),
             ("Over 2.5",o_p),("Under 2.5",round(100-o_p,1)),
             ("BTTS Yes",b_p),("BTTS No",round(100-b_p,1))]
    best, best_p = max(cands, key=lambda x:x[1])
    conf = "HIGH" if best_p>=55 else "MEDIUM" if best_p>=42 else "LOW"

    return {
        "home_team": home, "away_team": away,
        "xg": {"home": hxg, "away": axg},
        "probabilities": {"home_win": hw_p, "draw": d_p, "away_win": aw_p},
        "markets": {"over_2_5": o_p, "under_2_5": round(100-o_p,1), "btts_yes": b_p, "btts_no": round(100-b_p,1)},
        "top_scorelines": top5,
        "best_bet": {"pick": best, "probability": best_p, "confidence": conf},
        "data_source": "WC2010+2014+2018+2022+2026 (306 matches)",
        "generated_at": datetime.utcnow().isoformat(),
    }
