import sys
import os

# Ensure project root is in python path to load the strategy package
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from strategy import StrategyOptimizer, UndercutAnalyzer

def test_strategy_modules():
    print("FormulaMind Strategy Engine Verification")
    
    try:
        # 1. Initialize Optimizer
        print("\n[Testing Strategy Optimizer]")
        optimizer = StrategyOptimizer()
        print("StrategyOptimizer initialized successfully.")
        
        # Optimize Silverstone race (52 laps)
        print("Running full race strategy optimization (52 Laps)...")
        results = optimizer.find_best_strategies(total_laps=52, pit_loss=20.0)
        
        print("\nRanked Race Strategy Recommendations:")
        for idx, res in enumerate(results):
            strat_name = res['strategy_name']
            opt_pit = res['optimal_pit_lap']
            total_time_m = res['total_time_secs'] / 60.0
            print(f" {idx+1}. {strat_name:30} | Optimal Pit Lap: {str(opt_pit):10} | Total Duration: {total_time_m:.3f} mins")
            
        # 2. Initialize Undercut Analyzer
        print("\n[Testing Undercut Analyzer]")
        analyzer = UndercutAnalyzer(optimizer)
        print("UndercutAnalyzer initialized successfully.")
        
        # Test a scenario: Chaser is 1.2 seconds behind on Lap 18.
        # Leader is on Mediums with age 14. Chaser wants to pit for fresh Hards.
        gap = 1.2
        lap = 18
        age = 14
        print(f"Evaluating Undercut Scenario:")
        print(f" - Current Gap: {gap}s | Current Lap: {lap} | Leader Tyre Age: {age} (MEDIUM)")
        print(f" - Chaser pits for fresh HARD tires...")
        
        analysis = analyzer.analyze_undercut_potential(
            gap_seconds=gap,
            lap_number=lap,
            tyre_age_leader=age,
            compound_leader='MEDIUM',
            compound_chaser_fresh='HARD'
        )
        
        print("\nUndercut Analysis Output:")
        print(f" - Leader Out-lap Time (worn): {analysis['leader_lap_time_worn']:.3f}s")
        print(f" - Chaser Out-lap Time (fresh): {analysis['chaser_lap_time_fresh']:.3f}s")
        print(f" - Undercut Gain: {analysis['undercut_gain_secs']:.3f}s")
        print(f" - New Gap Post-Pit: {analysis['predicted_gap_secs']:.3f}s")
        print(f" - Threat Level: {analysis['threat_level']}")
        print(f" - Recommendation: {analysis['recommendation']}")
        
        print("\n=== Strategy Check PASSED ===")
        return True
    except Exception as e:
        import traceback
        err_msg = str(e).encode('ascii', 'replace').decode('ascii')
        print(f"Failed strategy testing: {err_msg}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_strategy_modules()