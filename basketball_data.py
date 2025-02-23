import requests
import csv
import json
import statistics
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
import logging
import urllib.parse
import time
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('basketball_data.log', mode='w'),
        logging.StreamHandler()
    ]
)

class TeamCountDialog:
    def __init__(self, parent=None):
        self.dialog = tk.Toplevel(parent) if parent else tk.Tk()
        self.dialog.title("Team Count Selection")
        self.dialog.geometry("300x150")
        self.dialog.resizable(False, False)
        
        # Make dialog modal
        self.dialog.transient(parent) if parent else None
        self.dialog.grab_set()
        
        # Center on screen
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'+{x}+{y}')
        
        # Configure grid
        self.dialog.grid_columnconfigure(0, weight=1)
        
        # Add explanation label
        explanation = tk.Label(
            self.dialog,
            text="Enter the number of teams to analyze.\nLeave blank or enter 0 for all teams.",
            wraplength=250
        )
        explanation.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Add entry field
        self.entry = ttk.Entry(self.dialog, width=10, justify='center')
        self.entry.grid(row=1, column=0, padx=20, pady=5)
        self.entry.insert(0, "0")
        
        # Add OK button
        ok_button = ttk.Button(self.dialog, text="OK", command=self._on_ok)
        ok_button.grid(row=2, column=0, pady=(10, 20))
        
        # Initialize result
        self.result = None
        
        # Bind Enter key to OK button
        self.dialog.bind('<Return>', lambda e: self._on_ok())
        
        # Focus entry field
        self.entry.focus_set()
        self.entry.selection_range(0, tk.END)
    
    def _on_ok(self):
        try:
            value = self.entry.get().strip()
            if not value:  # Empty input
                self.result = 0
            else:
                self.result = int(value)
                if self.result < 0:
                    raise ValueError("Number must be positive")
            self.dialog.destroy()
        except ValueError as e:
            messagebox.showerror(
                "Invalid Input",
                "Please enter a valid positive number or leave blank for all teams."
            )
    
    def show(self):
        self.dialog.mainloop()
        return self.result

class ProgressWindow:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ProgressWindow()
        return cls._instance
    
    def __init__(self, title="Basketball Data Collection Progress"):
        if ProgressWindow._instance is not None:
            raise Exception("This class is a singleton!")
            
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("400x150")
        self.root.resizable(False, False)
        
        # Keep window on top
        self.root.attributes('-topmost', True)
        
        # Configure grid
        self.root.grid_columnconfigure(0, weight=1)
        
        # Status label
        self.status_var = tk.StringVar(value="Initializing...")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, wraplength=380)
        self.status_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        # Main progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self.root, 
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # Sub-task progress bar
        self.subtask_var = tk.DoubleVar(value=0)
        self.subtask_bar = ttk.Progressbar(
            self.root, 
            variable=self.subtask_var,
            maximum=100,
            mode='determinate'
        )
        self.subtask_bar.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        # Detail label
        self.detail_var = tk.StringVar(value="")
        self.detail_label = tk.Label(self.root, textvariable=self.detail_var, wraplength=380)
        self.detail_label.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        
        # Animation variables
        self.target_progress = 0
        self.target_subtask = 0
        self.current_progress = 0
        self.current_subtask = 0
        self.animation_speed = 0.3  # Animation speed factor (0-1)
        
        self.queue = queue.Queue()
        self.running = True
        self.update_gui()
        
        ProgressWindow._instance = self
    
    def _animate_progress(self):
        """Smoothly animate progress bars"""
        if self.current_progress != self.target_progress:
            diff = self.target_progress - self.current_progress
            self.current_progress += diff * self.animation_speed
            if abs(diff) < 0.1:
                self.current_progress = self.target_progress
            self.progress_var.set(self.current_progress)
            
        if self.current_subtask != self.target_subtask:
            diff = self.target_subtask - self.current_subtask
            self.current_subtask += diff * self.animation_speed
            if abs(diff) < 0.1:
                self.current_subtask = self.target_subtask
            self.subtask_var.set(self.current_subtask)
    
    def update_gui(self):
        """Process all pending GUI updates"""
        if not self.running:
            return
            
        try:
            while True:
                update = self.queue.get_nowait()
                if isinstance(update, tuple):
                    attr, value = update
                    if attr == 'progress_var':
                        self.target_progress = float(value)
                    elif attr == 'subtask_var':
                        self.target_subtask = float(value)
                    elif hasattr(self, attr):
                        getattr(self, attr).set(value)
        except queue.Empty:
            pass
        
        # Animate progress bars
        self._animate_progress()
        
        # Update more frequently for smoother animation
        self.root.after(16, self.update_gui)  # ~60 FPS
    
    def update(self, status=None, progress=None, subtask=None, detail=None):
        """Queue updates to GUI elements"""
        if not self.running:
            return
            
        if status is not None:
            self.queue.put(('status_var', status))
        if progress is not None:
            self.queue.put(('progress_var', progress))
        if subtask is not None:
            self.queue.put(('subtask_var', subtask))
        if detail is not None:
            self.queue.put(('detail_var', detail))
    
    def close(self):
        """Close the progress window"""
        self.running = False
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None
        ProgressWindow._instance = None

class BasketballDataCollector:
    def __init__(self, progress_window=None):
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv('API_KEY')
        if not self.api_key:
            raise ValueError("API key not found. Please set API_KEY in your .env file")
        
        self.base_url = "https://api.collegebasketballdata.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
        # Create output directory if it doesn't exist
        self.output_dir = "data_output"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Store progress window reference
        self.progress_window = progress_window
        self.max_teams = 0

    def _format_season(self, season: str) -> str:
        """Format season string correctly for API"""
        # The API expects just the year number (e.g., "2024")
        try:
            year = int(season)
            return str(year)  # Just return the year as is
        except ValueError:
            return season

    def _format_team_name(self, team_name: str) -> str:
        """Format team name correctly for API"""
        if not team_name:
            return None
        
        # Remove special characters and normalize spaces
        formatted = team_name.strip()        
        
        # Do not URL encode - the requests library will handle that
        return formatted

    def _increment_progress(self, amount=1):
        """Increment progress by the smallest operation unit"""
        self.completed_operations += amount
        if self.total_operations > 0:
            progress = (self.completed_operations / self.total_operations) * 100
            self.progress_window.update(progress=progress)

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make an API request with error handling and progress tracking"""
        try:
            url = f"{self.base_url}/{endpoint}"
            
            # Format parameters
            if params:
                formatted_params = {}
                for key, value in params.items():
                    if value is None:
                        continue
                    if key == 'season':
                        formatted_params[key] = self._format_season(value)
                    elif key == 'team':
                        formatted_params[key] = value  # Already formatted, let requests handle URL encoding
                    elif key == 'status':
                        valid_statuses = ['scheduled', 'in_progress', 'final', 'postponed', 'cancelled']
                        status_val = value.lower()
                        if status_val not in valid_statuses:
                            logging.error(f"Invalid status value: {value}. Must be one of {valid_statuses}")
                            return None
                        formatted_params[key] = status_val
                    else:
                        formatted_params[key] = value
                
                params = formatted_params
            
            # Log request details before URL encoding
            logging.info(f"Making request to {url}")
            logging.info(f"Request parameters: {params}")
            
            # Update progress for request preparation
            self._increment_progress(0.2)
            
            # Let requests handle URL encoding of parameters
            response = requests.get(url, headers=self.headers, params=params)
            
            # Log the actual URL that was requested (after encoding)
            logging.info(f"Full URL after encoding: {response.url}")
            
            # Log response details
            logging.info(f"Response status code: {response.status_code}")
            if response.status_code != 200:
                logging.error(f"Response content: {response.text}")
            
            # Update progress for request completion
            self._increment_progress(0.3)
            
            if response.status_code == 400:
                logging.error(f"Bad request to {endpoint}. Full URL: {response.url}")
                logging.error(f"Response: {response.text}")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            # Log data summary
            if isinstance(data, list):
                logging.info(f"Retrieved {len(data)} items from API")
            else:
                logging.info("Retrieved data from API")
            
            # Update progress for data parsing
            self._increment_progress(0.5)
            
            return data
        except requests.exceptions.RequestException as e:
            logging.error(f"Error making request to {endpoint}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response content: {e.response.text}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error in request to {endpoint}: {str(e)}")
            return None

    def get_teams(self, season: Optional[str] = None) -> List[Dict]:
        """Get list of teams with optional season filter"""
        try:
            # First try without season to get all teams
            params = {}
            teams = self._make_request("teams", params) or []
            if teams:
                logging.info(f"Retrieved {len(teams)} teams")
                return teams
            
            # If that fails, try with season
            if season:
                params = {"season": season}
                teams = self._make_request("teams", params) or []
                if teams:
                    logging.info(f"Retrieved {len(teams)} teams for season {season}")
                return teams
            
            return []
        except Exception as e:
            logging.error(f"Error getting teams: {str(e)}")
            return []

    def get_team_stats(self, season: str, team: Optional[str] = None) -> List[Dict]:
        """Get team season statistics"""
        try:
            formatted_team = self._format_team_name(team) if team else None
            logging.info(f"Getting stats for team: {team} (formatted: {formatted_team})")
            
            params = {
                "season": season,
                "team": formatted_team,
                "seasonType": "regular"
            }
            
            stats = self._make_request("stats/team/season", params) or []
            
            if stats:
                logging.info(f"Retrieved {len(stats)} season stats entries for {'team ' + team if team else 'all teams'}")
                # Log first entry as sample if available
                if len(stats) > 0:
                    sample = stats[0]
                    logging.info(f"Sample stats - Team: {sample.get('team')}, Games: {sample.get('games')}, Points: {sample.get('offense', {}).get('points', {}).get('total')}")
            else:
                logging.warning(f"No stats retrieved for {'team ' + team if team else 'all teams'}")
            
            return stats
        except Exception as e:
            logging.error(f"Error getting team stats: {str(e)}")
            return []

    def get_games(self, season: str, team: Optional[str] = None, status: str = "final") -> List[Dict]:
        """Get basic games data with filters"""
        params = {
            "season": season,
            "seasonType": "regular",
            "team": team
        }
        games = self._make_request("games", params) or []
        
        if games:
            # Count games with valid scores
            games_with_scores = sum(1 for g in games 
                                  if g.get('homePoints') is not None 
                                  and g.get('awayPoints') is not None)
            
            logging.info(f"Retrieved {len(games)} games ({games_with_scores} with scores) for {'team ' + team if team else 'all teams'}")
            
            if games_with_scores < len(games):
                logging.warning(f"Only {games_with_scores} out of {len(games)} games have scores.")
                if len(games) > 0:
                    logging.debug(f"Sample game data: {json.dumps(games[0], indent=2)}")
        
        return games

    def get_games_teams(self, season: str, team: Optional[str] = None) -> List[Dict]:
        """Get detailed team statistics for games"""
        params = {
            "season": season,
            "seasonType": "regular",
            "team": team
        }
        detailed_games = self._make_request("games/teams", params) or []
        if detailed_games:
            logging.info(f"Retrieved detailed stats for {len(detailed_games)} game entries")
            # Log a sample entry to help with debugging
            if len(detailed_games) > 0:
                sample = detailed_games[0]
                points = sample.get('offense', {}).get('points', {}).get('total')
                logging.debug(f"Sample game points: {points}")
                logging.debug(f"Sample game structure: {json.dumps({
                    'gameId': sample.get('gameId'),
                    'team': sample.get('team'),
                    'opponent': sample.get('opponent'),
                    'offensePoints': sample.get('offense', {}).get('points', {}).get('total'),
                    'defensePoints': sample.get('defense', {}).get('points', {}).get('total'),
                    'neutralSite': sample.get('neutralSite')
                }, indent=2)}")
        return detailed_games

    def get_betting_lines(self, season: str, team: Optional[str] = None) -> List[Dict]:
        """Get betting lines data"""
        params = {
            "season": season,
            "team": team
        }
        lines = self._make_request("lines", params) or []
        if lines:
            logging.info(f"Retrieved {len(lines)} betting lines")
        return lines

    def get_team_ratings(self, season: str, team: Optional[str] = None) -> Dict:
        """Get both adjusted and SRS ratings"""
        params = {"season": season, "team": team}
        adj_ratings = self._make_request("ratings/adjusted", params) or []
        srs_ratings = self._make_request("ratings/srs", params) or []
        return {
            "adjusted": adj_ratings,
            "srs": srs_ratings
        }

    def collect_comprehensive_data(self, season: str):
        """Collect comprehensive data for analysis"""
        logging.info(f"Starting comprehensive data collection for season {season}")
        
        try:
            # Reset progress tracking
            self.total_operations = 0
            self.completed_operations = 0
            
            # Get all teams first
            self.progress_window.update(
                status="Fetching teams list...",
                progress=0,
                subtask=0,
                detail="Connecting to API"
            )
            
            teams = self.get_teams(season)
            if not teams:
                logging.error("Failed to retrieve teams data")
                return
            
            # Limit teams if max_teams is set
            total_teams = len(teams)
            if self.max_teams > 0:
                teams = teams[:self.max_teams]
                logging.info(f"Limited analysis to {len(teams)} teams out of {total_teams} total teams")
            else:
                logging.info(f"Analyzing all {total_teams} teams")
            
            # Each team represents an equal portion of the total progress
            progress_per_team = 100.0 / len(teams)
            current_progress = 0.0
            
            # Update progress window with team count info
            self.progress_window.update(
                status=f"Processing {len(teams)} teams...",
                detail=f"Starting data collection for {len(teams)} teams",
                progress=current_progress
            )
            
            # Prepare data structures and tracking sets
            games_data = []
            team_stats = []
            betting_lines = []
            ratings_data = []
            analyzed_teams = set()  # Track teams we've analyzed
            seen_game_ids = set()  # Track game IDs we've seen
            seen_betting_lines = set()  # Track betting lines we've seen
            
            # Process teams
            for idx, team in enumerate(teams, 1):
                team_name = team.get('school')
                if not team_name:
                    logging.warning(f"Skipping team with no name at index {idx}")
                    continue
                
                # Add to analyzed teams set
                analyzed_teams.add(team_name)
                
                # Add delay between requests to avoid rate limiting
                if idx > 1:
                    time.sleep(1)
                
                self.progress_window.update(
                    status=f"Processing team {idx}/{len(teams)}",
                    detail=f"Current team: {team_name}",
                    progress=current_progress
                )
                
                # Initialize empty data for this team
                team_data = {
                    'season': season,
                    'seasonLabel': f"{int(season)-1}{season}",  # e.g., "20232024" for season "2024"
                    'teamId': team.get('id'),
                    'team': team_name,
                    'conference': team.get('conference'),
                    'games': 0,
                    'wins': 0,
                    'losses': 0,
                    'totalMinutes': 0,
                    'pace': 0,
                    'offense': {
                        'assists': 0,
                        'blocks': 0,
                        'steals': 0,
                        'possessions': 0,
                        'trueShooting': 0,
                        'rating': 0,
                        'fieldGoals': {'made': 0, 'attempted': 0, 'pct': 0},
                        'twoPointFieldGoals': {'made': 0, 'attempted': 0, 'pct': 0},
                        'threePointFieldGoals': {'made': 0, 'attempted': 0, 'pct': 0},
                        'freeThrows': {'made': 0, 'attempted': 0, 'pct': 0},
                        'rebounds': {'offensive': 0, 'defensive': 0, 'total': 0},
                        'turnovers': {'total': 0, 'teamTotal': 0},
                        'fouls': {'total': 0, 'technical': 0, 'flagrant': 0},
                        'points': {'total': 0, 'inPaint': 0, 'offTurnovers': 0, 'fastBreak': 0},
                        'fourFactors': {
                            'effectiveFieldGoalPct': 0,
                            'turnoverRatio': 0,
                            'offensiveReboundPct': 0,
                            'freeThrowRate': 0
                        }
                    },
                    'defense': {
                        'assists': 0,
                        'blocks': 0,
                        'steals': 0,
                        'possessions': 0,
                        'trueShooting': 0,
                        'rating': 0,
                        'fieldGoals': {'made': 0, 'attempted': 0, 'pct': 0},
                        'twoPointFieldGoals': {'made': 0, 'attempted': 0, 'pct': 0},
                        'threePointFieldGoals': {'made': 0, 'attempted': 0, 'pct': 0},
                        'freeThrows': {'made': 0, 'attempted': 0, 'pct': 0},
                        'rebounds': {'offensive': 0, 'defensive': 0, 'total': 0},
                        'turnovers': {'total': 0, 'teamTotal': 0},
                        'fouls': {'total': 0, 'technical': 0, 'flagrant': 0},
                        'points': {'total': 0, 'inPaint': 0, 'offTurnovers': 0, 'fastBreak': 0},
                        'fourFactors': {
                            'effectiveFieldGoalPct': 0,
                            'turnoverRatio': 0,
                            'offensiveReboundPct': 0,
                            'freeThrowRate': 0
                        }
                    }
                }
                
                # Get games
                self.progress_window.update(subtask=0, detail=f"Fetching games for {team_name}")
                team_games = self.get_games(season, team_name)
                if team_games:
                    # Only add games we haven't seen before
                    for game in team_games:
                        game_id = game.get('id')
                        if game_id and game_id not in seen_game_ids:
                            seen_game_ids.add(game_id)
                            games_data.append(game)
                            
                            # Update team's win/loss record
                            if game.get('homeTeam') == team_name:
                                if game.get('homePoints', 0) > game.get('awayPoints', 0):
                                    team_data['wins'] += 1
                                else:
                                    team_data['losses'] += 1
                            elif game.get('awayTeam') == team_name:
                                if game.get('awayPoints', 0) > game.get('homePoints', 0):
                                    team_data['wins'] += 1
                                else:
                                    team_data['losses'] += 1
                            team_data['games'] += 1
                self.progress_window.update(subtask=25)
                
                # Get team stats
                self.progress_window.update(detail=f"Fetching stats for {team_name}")
                team_season_stats = self.get_team_stats(season, team_name)
                if team_season_stats:
                    # Update team_data with any available stats
                    for stat in team_season_stats:
                        if stat.get('team') == team_name:
                            # Use the API response data directly instead of our initialized structure
                            team_data = stat
                            team_stats.append(team_data)
                            logging.info(f"Added complete stats for {team_name}")
                            break
                    else:
                        logging.warning(f"No matching stats found for {team_name} in API response")
                        team_stats.append(team_data)  # Add initialized data as fallback
                else:
                    logging.warning(f"Failed to get stats for {team_name}")
                    team_stats.append(team_data)  # Add initialized data as fallback
                self.progress_window.update(subtask=50)
                
                # Get betting lines
                self.progress_window.update(detail=f"Fetching betting lines for {team_name}")
                team_lines = self.get_betting_lines(season, team_name)
                if team_lines:
                    # Create unique identifier for each betting line using available fields
                    for line in team_lines:
                        line_key = (
                            str(line.get('gameId', '')),
                            str(line.get('openDate', '')),
                            str(line.get('homeTeam', '')),
                            str(line.get('awayTeam', '')),
                            str(line.get('provider', ''))
                        )
                        if line_key not in seen_betting_lines:
                            seen_betting_lines.add(line_key)
                            betting_lines.append(line)
                self.progress_window.update(subtask=75)
                
                # Get ratings
                self.progress_window.update(detail=f"Fetching ratings for {team_name}")
                team_ratings = self.get_team_ratings(season, team_name)
                if team_ratings:
                    ratings_data.append({
                        "team": team_name,
                        "ratings": team_ratings
                    })
                else:
                    # Include empty ratings for teams without data
                    ratings_data.append({
                        "team": team_name,
                        "ratings": {"adjusted": [], "srs": []}
                    })
                self.progress_window.update(subtask=100)
                
                # Update main progress after completing each team
                current_progress = min(100.0, (idx * progress_per_team))
                self.progress_window.update(progress=current_progress)
            
            # Save all collected data
            self.progress_window.update(
                status="Saving collected data...",
                detail="Processing and saving all data files",
                subtask=0
            )
            
            # Pass the analyzed teams set to summary generation
            self._save_data_with_progress(games_data, "games", season)
            self._save_data_with_progress(team_stats, "team_stats", season)
            self._save_data_with_progress(betting_lines, "betting_lines", season)
            self._save_data_with_progress(ratings_data, "ratings", season)
            
            # Generate summary
            self.progress_window.update(
                status="Generating summary...",
                detail="Finalizing data collection",
                progress=100,
                subtask=100
            )
            self._generate_summary_stats(games_data, team_stats, betting_lines, ratings_data, season, analyzed_teams)
            
            # Show completion
            self.progress_window.update(
                status="Data collection complete!",
                progress=100,
                subtask=100,
                detail=f"All operations finished successfully. Processed {len(analyzed_teams)} teams. Window will close automatically..."
            )
            
        except Exception as e:
            logging.error(f"Error in data collection: {str(e)}", exc_info=True)
            self.progress_window.update(
                status="Error occurred during data collection",
                detail=f"Error: {str(e)}. Window will close automatically..."
            )

    def _save_data_with_progress(self, data: List[Dict], data_type: str, season: str):
        """Save data to both JSON and CSV formats with progress tracking"""
        if not data:
            logging.warning(f"No {data_type} data to save")
            return
        
        # Save as JSON
        self.progress_window.update(
            detail=f"Saving {data_type} (JSON)",
            subtask=25
        )
        json_file = os.path.join(self.output_dir, f"{season}_{data_type}.json")
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Process for CSV - properly flatten nested structures
        self.progress_window.update(
            detail=f"Processing {data_type} for CSV",
            subtask=50
        )
        flattened_data = []
        for item in data:
            flat_item = {}
            for key, value in item.items():
                if isinstance(value, dict):
                    # Handle nested dictionaries
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, dict):
                            # Handle doubly nested dictionaries (e.g., offense.fieldGoals)
                            for sub_sub_key, sub_sub_value in sub_value.items():
                                flat_item[f"{key}_{sub_key}_{sub_sub_key}"] = sub_sub_value
                        else:
                            flat_item[f"{key}_{sub_key}"] = sub_value
                else:
                    flat_item[key] = value
            flattened_data.append(flat_item)
        
        # Save as CSV
        self.progress_window.update(
            detail=f"Saving {data_type} (CSV)",
            subtask=75
        )
        csv_file = os.path.join(self.output_dir, f"{season}_{data_type}.csv")
        with open(csv_file, 'w', newline='') as f:
            if flattened_data:  # Only proceed if we have data
                writer = csv.DictWriter(f, fieldnames=flattened_data[0].keys())
                writer.writeheader()
                writer.writerows(flattened_data)
        
        self.progress_window.update(subtask=100)
        logging.info(f"Saved {data_type} data to {json_file} and {csv_file}")

    def _generate_summary_stats(self, games: List[Dict], team_stats: List[Dict], 
                              betting_lines: List[Dict], ratings: List[Dict], 
                              season: str, analyzed_teams: set):
        """Generate summary statistics from collected data"""
        try:
            # Get valid games with scores
            valid_games = [
                game for game in games 
                if (game.get('homePoints') is not None and 
                    game.get('awayPoints') is not None)
            ]
            
            # Calculate average score only if we have valid games
            avg_score = 0
            if valid_games:
                scores = [
                    game['homePoints'] + game['awayPoints']
                    for game in valid_games
                ]
                avg_score = statistics.mean(scores) if scores else 0
            
            summary = {
                "season": season,
                "total_games": len(games),
                "valid_games_with_scores": len(valid_games),
                "analyzed_teams": len(analyzed_teams),
                "teams_list": sorted(list(analyzed_teams)),  # Add list of team names for verification
                "average_total_score": round(avg_score, 2) if avg_score else 0,
                "total_betting_lines": len(betting_lines),
                "data_collection_date": datetime.now().isoformat(),
                "data_completeness": {
                    "games": bool(games),
                    "games_with_scores": bool(valid_games),
                    "team_stats": bool(team_stats),
                    "betting_lines": bool(betting_lines),
                    "ratings": bool(ratings)
                },
                "data_counts": {
                    "games": len(games),
                    "team_stats": len(team_stats),
                    "betting_lines": len(betting_lines),
                    "ratings": len(ratings)
                }
            }
            
            # Save summary
            summary_file = os.path.join(self.output_dir, f"{season}_summary.json")
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            # Log detailed summary
            logging.info(f"Summary Statistics for season {season}:")
            logging.info(f"- Total Games: {summary['total_games']}")
            logging.info(f"- Games with Scores: {summary['valid_games_with_scores']}")
            logging.info(f"- Teams Analyzed: {summary['analyzed_teams']}")
            logging.info(f"- Teams List: {', '.join(summary['teams_list'])}")
            logging.info(f"- Average Score: {summary['average_total_score']}")
            logging.info(f"- Total Betting Lines: {summary['total_betting_lines']}")
            logging.info(f"Generated summary statistics saved to {summary_file}")
            
        except Exception as e:
            logging.error(f"Error generating summary stats: {str(e)}", exc_info=True)
            self.progress_window.update(
                status="Warning: Error in summary generation",
                detail="Summary stats may be incomplete"
            )

def run_data_collection(progress_window, season: str, max_teams: int):
    """Run data collection in a separate thread"""
    try:
        collector = BasketballDataCollector(progress_window)
        collector.max_teams = max_teams
        collector.collect_comprehensive_data(season)
    finally:
        # Schedule the window to close after a short delay
        # This ensures the completion message is visible briefly
        if progress_window and progress_window.root:
            progress_window.root.after(1500, progress_window.close)

def main():
    try:
        # First show the team count dialog
        dialog = TeamCountDialog()
        max_teams = dialog.show()
        
        if max_teams is None:  # Dialog was closed without selecting
            return
            
        # Create progress window
        progress_window = ProgressWindow.get_instance()
        
        # Start data collection in a separate thread
        current_season = "2025"
        collection_thread = threading.Thread(
            target=run_data_collection,
            args=(progress_window, current_season, max_teams)
        )
        collection_thread.daemon = True
        collection_thread.start()
        
        # Run the GUI main loop
        progress_window.root.mainloop()
        
    except Exception as e:
        logging.error(f"Error in main: {str(e)}", exc_info=True)
    finally:
        # Close progress window
        if ProgressWindow._instance:
            ProgressWindow._instance.close()

if __name__ == "__main__":
    main() 