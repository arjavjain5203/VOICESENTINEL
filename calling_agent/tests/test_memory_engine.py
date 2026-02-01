
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Adjust path to import src
sys.path.append(os.path.join(os.getcwd(), '../calling_agent'))

from src.memory_engine import calculate_name_stability, calculate_dob_stability, calculate_trust_trend
from src.risk_engine import calculate_risk

class TestMemoryEngine(unittest.TestCase):
    
    def test_name_stability_exact(self):
        history = {'last_verified_name': 'John Doe'}
        score, changed = calculate_name_stability('John Doe', history)
        self.assertEqual(score, 1.0)
        self.assertFalse(changed)

    def test_name_stability_case_insensitive(self):
        history = {'last_verified_name': 'John Doe'}
        score, changed = calculate_name_stability('john doe', history)
        self.assertEqual(score, 1.0)
        self.assertFalse(changed)

    def test_name_stability_fuzzy(self):
        history = {'last_verified_name': 'Jonathan Doe'}
        score, changed = calculate_name_stability('John Doe', history)
        # SequenceMatcher ratio for "Jonathan Doe" vs "John Doe" is around 0.7-0.8
        # Let's just check it's not 1.0 and changed might be true depending on threshold
        # Threshold is 0.8. 
        # ratio("Jonathan Doe", "John Doe") -> 0.8
        # "Johnathan" vs "John" -> 0.61
        self.assertTrue(score < 1.0)
        
    def test_name_stability_mismatch(self):
        history = {'last_verified_name': 'Alice Smith'}
        score, changed = calculate_name_stability('Bob Jones', history)
        self.assertTrue(score < 0.4)
        self.assertTrue(changed)

    def test_dob_stability_match(self):
        history = {'last_verified_dob': '1990-01-01'}
        score, mismatch = calculate_dob_stability('1990-01-01', history)
        self.assertEqual(score, 1.0)
        self.assertEqual(mismatch, 0)
        
    def test_dob_stability_mismatch(self):
        history = {'last_verified_dob': '1990-01-01'}
        score, mismatch = calculate_dob_stability('1992-05-05', history)
        self.assertEqual(score, 0.0)
        self.assertEqual(mismatch, 1)

    def test_trust_trend_increasing(self):
        history = {'trust_score_history': [50, 50, 60]} # Avg 53.3
        # Current 70 > 53.3 + 5
        trend = calculate_trust_trend(70, history)
        self.assertEqual(trend, "increasing")
        
    def test_trust_trend_decreasing(self):
        history = {'trust_score_history': [80, 80, 80]} # Avg 80
        # Current 60 < 80 - 5
        trend = calculate_trust_trend(60, history)
        self.assertEqual(trend, "decreasing")
        
    def test_risk_integration_name_change(self):
        # Scenario: Name changed, DOB matches.
        # Name stability 0.0 -> Risk += 2.0
        details = calculate_risk(
            otp_success=True,
            identity_fails=0,
            voice_risk="LOW",
            intent="REFUND",
            name_stability=0.0,
            dob_stability=1.0,
            trust_trend="stable"
        )
        # Base breakdown check
        self.assertEqual(details['breakdown']['name_stability_risk'], 2.0)
        self.assertEqual(details['breakdown']['dob_stability_risk'], 0.0)
        
    def test_risk_integration_dob_mismatch(self):
        # Scenario: DOB mismatch -> Risk += 3.0
        details = calculate_risk(
            otp_success=True,
            identity_fails=0,
            voice_risk="LOW",
            intent="REFUND",
            name_stability=1.0,
            dob_stability=0.0,
            trust_trend="stable"
        )
        self.assertEqual(details['breakdown']['dob_stability_risk'], 3.0)

if __name__ == '__main__':
    unittest.main()
