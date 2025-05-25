"""
EuroMillions number analysis module.

This module provides analysis of hot and cold numbers in EuroMillions draws,
visualization of number frequency patterns, and prediction models.
"""
import os
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from pathlib import Path

from app.database import SessionLocal
from app.models.base import Draw

logger = logging.getLogger(__name__)

# Constants for EuroMillions
NUM_MAIN_NUMBERS = 5
NUM_LUCKY_STARS = 2
MAX_MAIN_NUMBER = 50
MAX_LUCKY_STAR = 12

# Directory for saving generated charts
CHARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'charts')
os.makedirs(CHARTS_DIR, exist_ok=True)

class NumberAnalyzer:
    """Analyze EuroMillions numbers for patterns and predictions."""
    
    def __init__(self):
        """Initialize the analyzer with database connection."""
        self.db = SessionLocal()
        self.draws_df = None
        self._load_data()
        
    def __del__(self):
        """Close database connection when object is destroyed."""
        if hasattr(self, 'db') and self.db:
            self.db.close()
    
    def _load_data(self):
        """Load draw data from database into pandas DataFrame."""
        try:
            # Query all draws from the database
            draws = self.db.query(Draw).order_by(Draw.draw_date.asc()).all()
            
            if not draws:
                logger.error("No draws found in database")
                return
                
            # Convert to pandas DataFrame for easier analysis
            data = []
            for draw in draws:
                data.append({
                    'draw_date': draw.draw_date,
                    'ball1': draw.ball1,
                    'ball2': draw.ball2,
                    'ball3': draw.ball3,
                    'ball4': draw.ball4,
                    'ball5': draw.ball5,
                    'lucky_star1': draw.lucky_star1,
                    'lucky_star2': draw.lucky_star2,
                    'jackpot': draw.jackpot
                })
            
            self.draws_df = pd.DataFrame(data)
            logger.info(f"Loaded {len(self.draws_df)} draws from database")
            
            # Create arrays for all numbers
            self.draws_df['main_numbers'] = self.draws_df.apply(
                lambda x: [x['ball1'], x['ball2'], x['ball3'], x['ball4'], x['ball5']], axis=1
            )
            self.draws_df['lucky_stars'] = self.draws_df.apply(
                lambda x: [x['lucky_star1'], x['lucky_star2']], axis=1
            )
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def analyze_number_frequency(self, time_period: str = 'all') -> Tuple[Dict, Dict]:
        """Analyze frequency of numbers and identify hot and cold numbers.
        
        Args:
            time_period: Time period for analysis ('all', 'year', '6months', '3months')
            
        Returns:
            Tuple of (main_numbers_frequency, lucky_stars_frequency)
        """
        if self.draws_df is None or len(self.draws_df) == 0:
            logger.error("No data available for analysis")
            return {}, {}
            
        # Filter data based on time period
        filtered_df = self._filter_by_time_period(time_period)
        
        # Analyze main numbers frequency
        main_numbers_freq = self._count_number_frequency(filtered_df, 'main', MAX_MAIN_NUMBER)
        
        # Analyze lucky stars frequency
        lucky_stars_freq = self._count_number_frequency(filtered_df, 'lucky_stars', MAX_LUCKY_STAR)
        
        return main_numbers_freq, lucky_stars_freq
    
    def _filter_by_time_period(self, time_period: str) -> pd.DataFrame:
        """Filter draws DataFrame by time period.
        
        Args:
            time_period: Time period ('all', 'year', '10years', '6months', '3months')
            
        Returns:
            Filtered DataFrame
        """
        today = date.today()
        
        if time_period == 'all':
            return self.draws_df
        elif time_period == '10years':
            cutoff_date = today - timedelta(days=3650)  # 10 years × 365 days
        elif time_period == 'year':
            cutoff_date = today - timedelta(days=365)
        elif time_period == '6months':
            cutoff_date = today - timedelta(days=182)
        elif time_period == '3months':
            cutoff_date = today - timedelta(days=91)
        else:
            logger.warning(f"Unknown time period: {time_period}, using all data")
            return self.draws_df
            
        filtered_df = self.draws_df[self.draws_df['draw_date'] >= cutoff_date]
        logger.info(f"Filtered to {len(filtered_df)} draws for time period: {time_period}")
        return filtered_df
    
    def _count_number_frequency(self, df: pd.DataFrame, number_type: str, max_value: int) -> Dict:
        """Count frequency of numbers in draws.
        
        Args:
            df: DataFrame with draw data
            number_type: Type of numbers ('main' or 'lucky_stars')
            max_value: Maximum possible value for the number type
            
        Returns:
            Dictionary with number frequencies and classifications
        """
        # Initialize frequency count
        frequency = {i: 0 for i in range(1, max_value + 1)}
        
        # Count occurrences
        if number_type == 'main':
            for _, row in df.iterrows():
                for num in row['main_numbers']:
                    frequency[num] += 1
            draws_count = len(df) * NUM_MAIN_NUMBERS
        else:  # lucky_stars
            for _, row in df.iterrows():
                for num in row['lucky_stars']:
                    frequency[num] += 1
            draws_count = len(df) * NUM_LUCKY_STARS
        
        # Calculate frequency percentage
        for num in frequency:
            frequency[num] = {
                'count': frequency[num],
                'percentage': (frequency[num] / draws_count) * 100
            }
        
        # Classify numbers as hot, warm, cool, cold
        sorted_numbers = sorted(frequency.items(), key=lambda x: x[1]['count'], reverse=True)
        
        # Top 20% are hot, next 30% are warm, next 30% are cool, bottom 20% are cold
        hot_count = int(max_value * 0.2)
        warm_count = int(max_value * 0.3)
        cool_count = int(max_value * 0.3)
        
        for i, (num, data) in enumerate(sorted_numbers):
            if i < hot_count:
                frequency[num]['status'] = 'hot'
            elif i < hot_count + warm_count:
                frequency[num]['status'] = 'warm'
            elif i < hot_count + warm_count + cool_count:
                frequency[num]['status'] = 'cool'
            else:
                frequency[num]['status'] = 'cold'
        
        return frequency
    
    def visualize_number_frequency(self, time_period: str = 'all', save_path: Optional[str] = None) -> str:
        """Create and save visualizations of number frequency.
        
        Args:
            time_period: Time period for analysis ('all', 'year', '6months', '3months')
            save_path: Optional path to save the visualization
            
        Returns:
            Path to the saved visualization file
        """
        main_numbers_freq, lucky_stars_freq = self.analyze_number_frequency(time_period)
        
        if not main_numbers_freq or not lucky_stars_freq:
            logger.error("No frequency data to visualize")
            return ""
        
        # Create a figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
        
        # Prepare data for main numbers
        main_numbers = list(range(1, MAX_MAIN_NUMBER + 1))
        main_counts = [main_numbers_freq[num]['count'] for num in main_numbers]
        main_status = [main_numbers_freq[num]['status'] for num in main_numbers]
        
        # Prepare data for lucky stars
        lucky_stars = list(range(1, MAX_LUCKY_STAR + 1))
        lucky_counts = [lucky_stars_freq[num]['count'] for num in lucky_stars]
        lucky_status = [lucky_stars_freq[num]['status'] for num in lucky_stars]
        
        # Set color palette based on status
        color_map = {'hot': 'red', 'warm': 'orange', 'cool': 'lightblue', 'cold': 'blue'}
        main_colors = [color_map[status] for status in main_status]
        lucky_colors = [color_map[status] for status in lucky_status]
        
        # Plot main numbers
        ax1.bar(main_numbers, main_counts, color=main_colors)
        ax1.set_title(f'EuroMillions Main Number Frequency ({time_period})', fontsize=14)
        ax1.set_xlabel('Number', fontsize=12)
        ax1.set_ylabel('Frequency', fontsize=12)
        ax1.set_xticks(main_numbers)
        ax1.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Add labels to main number bars with status
        for i, count in enumerate(main_counts):
            status = main_status[i]
            ax1.text(main_numbers[i], count + 1, status.upper(), 
                    rotation=90, ha='center', fontsize=8, color=color_map[status])
        
        # Plot lucky stars
        ax2.bar(lucky_stars, lucky_counts, color=lucky_colors)
        ax2.set_title(f'EuroMillions Lucky Star Frequency ({time_period})', fontsize=14)
        ax2.set_xlabel('Number', fontsize=12)
        ax2.set_ylabel('Frequency', fontsize=12)
        ax2.set_xticks(lucky_stars)
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Add labels to lucky star bars with status
        for i, count in enumerate(lucky_counts):
            status = lucky_status[i]
            ax2.text(lucky_stars[i], count + 1, status.upper(), 
                    rotation=90, ha='center', fontsize=8, color=color_map[status])
        
        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='red', label='Hot (top 20%)'),
            Patch(facecolor='orange', label='Warm (21-50%)'),
            Patch(facecolor='lightblue', label='Cool (51-80%)'),
            Patch(facecolor='blue', label='Cold (bottom 20%)')
        ]
        ax1.legend(handles=legend_elements, loc='upper right')
        
        plt.tight_layout()
        
        # Save the plot
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            save_path = os.path.join(CHARTS_DIR, f'frequency_analysis_{time_period}_{timestamp}.png')
        
        plt.savefig(save_path)
        logger.info(f"Visualization saved to {save_path}")
        plt.close()
        
        return save_path
    
    def get_hot_cold_recommendations(self, time_period: str = '3months', strategy: str = 'balanced') -> Dict[str, Any]:
        """Get recommended numbers based on hot/cold analysis.
        
        Args:
            time_period: Time period for analysis ('all', 'year', '6months', '3months')
            strategy: Number selection strategy:
                     'hot': Pick mostly hot numbers
                     'cold': Pick mostly cold numbers
                     'balanced': Mix of hot, warm, cool, and cold
                     'mixed': Opposite strategy (hot and cold, no warm/cool)
            
        Returns:
            Dictionary with recommended numbers
        """
        main_numbers_freq, lucky_stars_freq = self.analyze_number_frequency(time_period)
        
        if not main_numbers_freq or not lucky_stars_freq:
            logger.error("No frequency data for recommendations")
            return {'main_numbers': [], 'lucky_stars': []}
            
        # Group numbers by status
        main_by_status = {
            'hot': [],
            'warm': [],
            'cool': [],
            'cold': []
        }
        
        lucky_by_status = {
            'hot': [],
            'warm': [],
            'cool': [],
            'cold': []
        }
        
        for num, data in main_numbers_freq.items():
            main_by_status[data['status']].append((num, data['count']))
            
        for num, data in lucky_stars_freq.items():
            lucky_by_status[data['status']].append((num, data['count']))
            
        # Sort each group by frequency (highest first)
        for status in main_by_status:
            main_by_status[status].sort(key=lambda x: x[1], reverse=True)
            
        for status in lucky_by_status:
            lucky_by_status[status].sort(key=lambda x: x[1], reverse=True)
            
        # Apply strategy to select numbers
        if strategy == 'hot':
            # 4 hot, 1 warm for main; 2 hot for lucky stars
            main_picks = self._select_numbers(main_by_status, [('hot', 4), ('warm', 1)])
            lucky_picks = self._select_numbers(lucky_by_status, [('hot', 2)])
        elif strategy == 'cold':
            # 4 cold, 1 cool for main; 2 cold for lucky stars
            main_picks = self._select_numbers(main_by_status, [('cold', 4), ('cool', 1)])
            lucky_picks = self._select_numbers(lucky_by_status, [('cold', 2)])
        elif strategy == 'mixed':
            # 2 hot, 3 cold for main; 1 hot, 1 cold for lucky stars
            main_picks = self._select_numbers(main_by_status, [('hot', 2), ('cold', 3)])
            lucky_picks = self._select_numbers(lucky_by_status, [('hot', 1), ('cold', 1)])
        else:  # balanced
            # 2 hot, 1 warm, 1 cool, 1 cold for main; 1 hot, 1 cold for lucky stars
            main_picks = self._select_numbers(main_by_status, [('hot', 2), ('warm', 1), ('cool', 1), ('cold', 1)])
            lucky_picks = self._select_numbers(lucky_by_status, [('hot', 1), ('cold', 1)])
            
        return {
            'main_numbers': sorted(main_picks),
            'lucky_stars': sorted(lucky_picks),
            'time_period': time_period,
            'strategy': strategy
        }
        
    def _select_numbers(self, numbers_by_status: Dict, selection_counts: List[Tuple[str, int]]) -> List[int]:
        """Select numbers from different status groups according to specified counts.
        
        Args:
            numbers_by_status: Dictionary of numbers grouped by status
            selection_counts: List of tuples (status, count) specifying how many to select from each group
            
        Returns:
            List of selected numbers
        """
        selected = []
        
        for status, count in selection_counts:
            # Get available numbers for this status
            available = [n[0] for n in numbers_by_status[status]]
            
            # Determine how many to select (limited by availability)
            to_select = min(count, len(available))
            
            # If not enough available, log a warning
            if to_select < count:
                logger.warning(f"Not enough {status} numbers available. Requested {count}, found {to_select}")
                
            # Select top numbers (already sorted by frequency)
            selected.extend(available[:to_select])
            
        return selected
        
    def generate_prediction_model(self, lookback_periods: int = 10, train_size: float = 0.8) -> Dict[str, Any]:
        """Generate a prediction model based on historical patterns.
        
        Args:
            lookback_periods: Number of previous draws to use as features
            train_size: Fraction of data to use for training (0.0-1.0)
            
        Returns:
            Dictionary with model performance metrics and predictions
        """
        if self.draws_df is None or len(self.draws_df) < lookback_periods + 10:
            logger.error("Insufficient data for prediction model")
            return {'success': False, 'error': 'Insufficient data'}
            
        try:
            # Prepare features and targets
            X, y_main, y_stars = self._prepare_prediction_data(lookback_periods)
            
            if len(X) < 10:
                logger.error("Insufficient data for prediction model after preparation")
                return {'success': False, 'error': 'Insufficient data after preparation'}
                
            # Split data into training and test sets
            X_train, X_test, y_main_train, y_main_test, y_stars_train, y_stars_test = self._split_data(
                X, y_main, y_stars, train_size
            )
            
            # Train models for main numbers
            main_models = []
            main_accuracies = []
            
            for i in range(NUM_MAIN_NUMBERS):
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                model.fit(X_train, y_main_train[:, i])
                y_pred = model.predict(X_test)
                accuracy = accuracy_score(y_main_test[:, i], y_pred)
                main_models.append(model)
                main_accuracies.append(accuracy)
                
            # Train models for lucky stars
            star_models = []
            star_accuracies = []
            
            for i in range(NUM_LUCKY_STARS):
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                model.fit(X_train, y_stars_train[:, i])
                y_pred = model.predict(X_test)
                accuracy = accuracy_score(y_stars_test[:, i], y_pred)
                star_models.append(model)
                star_accuracies.append(accuracy)
                
            # Make prediction for next draw
            latest_features = self._get_latest_features(lookback_periods)
            
            predicted_main = []
            for model in main_models:
                pred = model.predict([latest_features])[0]
                predicted_main.append(int(pred))
                
            predicted_stars = []
            for model in star_models:
                pred = model.predict([latest_features])[0]
                predicted_stars.append(int(pred))
                
            # Remove duplicates and ensure we have the right number of predictions
            predicted_main = self._ensure_unique_predictions(predicted_main, MAX_MAIN_NUMBER, NUM_MAIN_NUMBERS)
            predicted_stars = self._ensure_unique_predictions(predicted_stars, MAX_LUCKY_STAR, NUM_LUCKY_STARS)
            
            return {
                'success': True,
                'main_numbers': sorted(predicted_main),
                'lucky_stars': sorted(predicted_stars),
                'main_accuracy': sum(main_accuracies) / len(main_accuracies),
                'star_accuracy': sum(star_accuracies) / len(star_accuracies),
                'lookback_periods': lookback_periods
            }
            
        except Exception as e:
            logger.error(f"Error generating prediction model: {e}")
            return {'success': False, 'error': str(e)}
            
    def _prepare_prediction_data(self, lookback_periods: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for prediction model.
        
        Args:
            lookback_periods: Number of previous draws to use as features
            
        Returns:
            Tuple of (features, main_number_targets, lucky_star_targets)
        """
        # Convert draw data to numeric features
        features = []
        main_targets = []
        star_targets = []
        
        for i in range(lookback_periods, len(self.draws_df)):
            # Create feature vector from previous draws
            feature_vector = []
            for j in range(i - lookback_periods, i):
                main_nums = self.draws_df.iloc[j]['main_numbers']
                lucky_stars = self.draws_df.iloc[j]['lucky_stars']
                feature_vector.extend(main_nums)
                feature_vector.extend(lucky_stars)
                
            # Add target values (current draw)
            target_main = self.draws_df.iloc[i]['main_numbers']
            target_stars = self.draws_df.iloc[i]['lucky_stars']
            
            features.append(feature_vector)
            main_targets.append(target_main)
            star_targets.append(target_stars)
            
        return np.array(features), np.array(main_targets), np.array(star_targets)
        
    def _split_data(self, X, y_main, y_stars, train_size: float):
        """Split data into training and test sets.
        
        Args:
            X: Features
            y_main: Main number targets
            y_stars: Lucky star targets
            train_size: Fraction of data to use for training
            
        Returns:
            Tuple of (X_train, X_test, y_main_train, y_main_test, y_stars_train, y_stars_test)
        """
        # Use same random split for all targets
        X_train, X_test, y_main_train, y_main_test = train_test_split(
            X, y_main, train_size=train_size, random_state=42
        )
        
        # Split star targets using same indices
        _, _, y_stars_train, y_stars_test = train_test_split(
            X, y_stars, train_size=train_size, random_state=42
        )
        
        return X_train, X_test, y_main_train, y_main_test, y_stars_train, y_stars_test
        
    def _get_latest_features(self, lookback_periods: int) -> List[int]:
        """Get feature vector from latest draws for prediction.
        
        Args:
            lookback_periods: Number of previous draws to use
            
        Returns:
            Feature vector for latest draws
        """
        feature_vector = []
        for i in range(len(self.draws_df) - lookback_periods, len(self.draws_df)):
            main_nums = self.draws_df.iloc[i]['main_numbers']
            lucky_stars = self.draws_df.iloc[i]['lucky_stars']
            feature_vector.extend(main_nums)
            feature_vector.extend(lucky_stars)
            
        return feature_vector
        
    def _ensure_unique_predictions(self, predictions: List[int], max_value: int, required_count: int) -> List[int]:
        """Ensure predictions contain the required number of unique values.
        
        Args:
            predictions: List of predicted numbers
            max_value: Maximum possible value
            required_count: Required number of unique predictions
            
        Returns:
            List of unique predictions with required length
        """
        # Remove duplicates
        unique_predictions = list(set(predictions))
        
        # If we have too few predictions, add random ones that aren't already included
        while len(unique_predictions) < required_count:
            candidate = np.random.randint(1, max_value + 1)
            if candidate not in unique_predictions:
                unique_predictions.append(candidate)
                
        # If we have too many predictions, keep only the required number
        if len(unique_predictions) > required_count:
            unique_predictions = unique_predictions[:required_count]
            
        return unique_predictions
        
    def visualize_prediction_performance(self, save_path: Optional[str] = None) -> str:
        """Visualize prediction model performance with different lookback periods.
        
        Args:
            save_path: Optional path to save the visualization
            
        Returns:
            Path to the saved visualization file
        """
        lookback_periods = [5, 10, 15, 20, 25]
        main_accuracies = []
        star_accuracies = []
        
        for lookback in lookback_periods:
            result = self.generate_prediction_model(lookback_periods=lookback)
            if result['success']:
                main_accuracies.append(result['main_accuracy'])
                star_accuracies.append(result['star_accuracy'])
            else:
                main_accuracies.append(0)
                star_accuracies.append(0)
                
        # Create the figure
        plt.figure(figsize=(10, 6))
        
        # Plot accuracy for main numbers and lucky stars
        plt.plot(lookback_periods, main_accuracies, 'o-', label='Main Numbers')
        plt.plot(lookback_periods, star_accuracies, 'o-', label='Lucky Stars')
        
        plt.title('Prediction Model Accuracy with Different Lookback Periods', fontsize=14)
        plt.xlabel('Lookback Periods (Number of Previous Draws)', fontsize=12)
        plt.ylabel('Accuracy', fontsize=12)
        plt.legend()
        plt.grid(linestyle='--', alpha=0.7)
        
        # Save the plot
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            save_path = os.path.join(CHARTS_DIR, f'prediction_performance_{timestamp}.png')
        
        plt.savefig(save_path)
        logger.info(f"Prediction performance visualization saved to {save_path}")
        plt.close()
        
        return save_path
        
    def combine_strategies(self, recommendations_count: int = 3) -> List[Dict[str, Any]]:
        """Generate multiple number recommendations using different strategies.
        
        Args:
            recommendations_count: Number of different recommendations to generate
            
        Returns:
            List of recommendation dictionaries
        """
        strategies = ['hot', 'cold', 'balanced', 'mixed']
        time_periods = ['3months', '6months', 'year', 'all']
        
        recommendations = []
        
        # Generate ML-based prediction
        ml_prediction = self.generate_prediction_model()
        if ml_prediction['success']:
            recommendations.append({
                'main_numbers': ml_prediction['main_numbers'],
                'lucky_stars': ml_prediction['lucky_stars'],
                'strategy': 'Machine Learning',
                'time_period': f"Lookback: {ml_prediction['lookback_periods']} draws",
                'type': 'prediction'
            })
        
        # Add recommendations from different frequency analysis strategies
        for i in range(min(recommendations_count - 1, len(strategies) * len(time_periods))):
            strategy = strategies[i % len(strategies)]
            time_period = time_periods[i // len(strategies)]
            
            recommendation = self.get_hot_cold_recommendations(time_period, strategy)
            recommendation['type'] = 'frequency'
            recommendations.append(recommendation)
            
        return recommendations

    def generate_complete_analysis(self) -> Dict[str, Any]:
        """Generate a complete analysis report with visualizations and recommendations.
        
        Returns:
            Dictionary with analysis results and file paths
        """
        result = {
            'charts': {},
            'recommendations': [],
            'summary': {}
        }
        
        # Generate frequency visualizations for different time periods
        time_periods = ['3months', '6months', 'year', 'all']
        for period in time_periods:
            chart_path = self.visualize_number_frequency(period)
            result['charts'][f'frequency_{period}'] = chart_path
            
        # Generate prediction performance visualization
        perf_chart = self.visualize_prediction_performance()
        result['charts']['prediction_performance'] = perf_chart
        
        # Generate recommendations
        result['recommendations'] = self.combine_strategies(5)
        
        # Analyze overall frequency
        main_freq, star_freq = self.analyze_number_frequency('all')
        
        # Get hottest and coldest numbers
        hottest_main = sorted([n for n, data in main_freq.items() if data['status'] == 'hot'], 
                           key=lambda x: main_freq[x]['count'], reverse=True)
        coldest_main = sorted([n for n, data in main_freq.items() if data['status'] == 'cold'], 
                            key=lambda x: main_freq[x]['count'])
                            
        hottest_stars = sorted([n for n, data in star_freq.items() if data['status'] == 'hot'], 
                             key=lambda x: star_freq[x]['count'], reverse=True)
        coldest_stars = sorted([n for n, data in star_freq.items() if data['status'] == 'cold'], 
                              key=lambda x: star_freq[x]['count'])
        
        result['summary'] = {
            'hottest_main_numbers': hottest_main,
            'coldest_main_numbers': coldest_main,
            'hottest_lucky_stars': hottest_stars,
            'coldest_lucky_stars': coldest_stars,
            'total_draws_analyzed': len(self.draws_df),
            'date_range': {
                'first_draw': self.draws_df['draw_date'].min().strftime('%Y-%m-%d'),
                'last_draw': self.draws_df['draw_date'].max().strftime('%Y-%m-%d')
            }
        }
        
        return result
