import math
import time
import json
import random

class ShieldMatrixCore:
    def __init__(self):
        print("[⚡ SYSTEM] Shield Matrix Algorithmic Engine Booting Up...")
        print("[⚙️ MODE] Automated Analysis & Pipeline Logging Active.\n---")

    def calculate_poisson_probability(self, average_goals, exact_k):
        """Runs the foundational Poisson math: P(k; λ) = (λ^k * e^-λ) / k!"""
        if average_goals <= 0:
            return 0.0
        numerator = (math.pow(average_goals, exact_k)) * (math.exp(-average_goals))
        denominator = math.factorial(exact_k)
        return numerator / denominator

    def analyze_fixture(self, home_team, away_team, home_xg_form, away_xg_form, defensive_volatility):
        """
        Processes deep telemetry data to generate accurate win/draw/loss matrices
        and gauges risk parameters based on statistical variance.
        """
        # Step 1: Establish baseline algorithmic projections
        home_projected_goals = home_xg_form * (1.1 + (defensive_volatility * 0.05))
        away_projected_goals = away_xg_form * (0.9 + (defensive_volatility * 0.05))
        
        home_win_prob = 0.0
        away_win_prob = 0.0
        draw_prob = 0.0
        
        # Step 2: Compute a 6x6 score matrix loop (up to 5 goals per team) for precise probability mapping
        for h in range(6):
            for a in range(6):
                p_h = self.calculate_poisson_probability(home_projected_goals, h)
                p_a = self.calculate_poisson_probability(away_projected_goals, a)
                matrix_cell_prob = p_h * p_a
                
                if h > a:
                    home_win_prob += matrix_cell_prob
                elif a > h:
                    away_win_prob += matrix_cell_prob
                else:
                    draw_prob += matrix_cell_prob

        # Step 3: Normalize to 100% distribution scale
        total_distribution = home_win_prob + away_win_prob + draw_prob
        home_pct = round((home_win_prob / total_distribution) * 100)
        away_pct = round((away_win_prob / total_distribution) * 100)
        draw_pct = round((draw_prob / total_distribution) * 100)
        
        # Step 4: Quantify algorithmic risk tracking
        risk_factor = "LOW"
        if defensive_volatility > 1.5 or abs(home_pct - away_pct) < 15:
            risk_factor = "HIGH"
        elif 1.0 <= defensive_volatility <= 1.5:
            risk_factor = "MEDIUM"
            
        # Step 5: Draft the tactical data logging breakdown
        trend_analysis = f"Computed True xG: {home_projected_goals:.2f} vs {away_projected_goals:.2f}. "
        if home_pct > 55:
            trend_analysis += f"Heavy alpha variance favoring {home_team} home momentum."
        elif away_pct > 55:
            trend_analysis += f"Away tactical setup matches structural vulnerabilities in home backline."
        else:
            trend_analysis += "High tactical gridlock detected in central channels. Value on under markets."

        return {
            "match": f"{home_team} vs {away_team}",
            "homeWin": f"{home_pct}%",
            "draw": f"{draw_pct}%",
            "awayWin": f"{away_pct}%",
            "risk": risk_factor,
            "trend": trend_analysis,
            "mathTelemetry": {
                "homeExpectedValue": round(home_projected_goals, 2),
                "awayExpectedValue": round(away_projected_goals, 2),
                "volatilityIdx": defensive_volatility
            }
        }

    def run_pipeline_stream(self):
        """Simulates continuous live scraping and pipeline log transmission"""
        # Mocking incoming raw data streams from your sports targets
        raw_scraped_fixtures = [
            ("Arsenal", "Chelsea", 2.10, 1.05, 0.8),
            ("Real Madrid", "Barcelona", 1.95, 1.80, 1.6),
            ("Manchester City", "Liverpool", 2.45, 2.10, 1.2),
        ]
        
        processed_pipeline_batch = []
        
        for home, away, h_xg, a_xg, volatility in raw_scraped_fixtures:
            print(f"[🔍 SCRAPING] Analyzing real-time metrics for {home} vs {away}...")
            analysis_output = self.analyze_fixture(home, away, h_xg, a_xg, volatility)
            processed_pipeline_batch.append(analysis_output)
            time.sleep(0.4) # Simulating fast asynchronous thread execution
            
        print("\n[📤 PIPELINE LOGGING] Transmitting processed structural payload to database...")
        # In production, this JSON payload writes straight to your live collection node
        print(json.dumps(processed_pipeline_batch, indent=2))
        print("\n[✅ SUCCESS] Data sync cycle complete. Waiting for next network fixture update block...")

if __name__ == "__main__":
    engine = ShieldMatrixCore()
    engine.run_pipeline_stream()