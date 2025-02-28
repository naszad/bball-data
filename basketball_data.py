import requests
import csv
import json
import statistics
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        
        # Initialize progress tracking
        self.completed_operations = 0
        self.total_operations = 100  # Default value, can be updated based on actual operations
        
        # Cache for loaded data
        self.cache = {}
        
        # Create session with retries
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a session with retry strategy to handle rate limits and transient errors."""
        session = requests.Session()
        retry_strategy = Retry(
            total=5,  # increased number of retries
            backoff_factor=1.0,  # increased backoff factor
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=25, pool_maxsize=25)
        session.mount("https://", adapter)
        session.headers.update(self.headers)
        return session

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

    def _increment_progress(self, increment: float):
        """Increment the progress by the specified amount"""
        if self.progress_window:
            self.completed_operations += increment
            progress = min(100, (self.completed_operations / self.total_operations) * 100)
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
            response = self.session.get(url, params=params)
            
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

    def _load_cached_data(self, data_type: str, season: str) -> List[Dict]:
        """Load data from cache or file if available"""
        cache_key = f"{season}_{data_type}"
        
        # Check memory cache first
        if cache_key in self.cache:
            logging.info(f"Using memory cache for {cache_key}")
            return self.cache[cache_key]
        
        # Try loading from file
        json_file = os.path.join(self.output_dir, f"{cache_key}.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    self.cache[cache_key] = data  # Store in memory cache
                    logging.info(f"Loaded cached data from {json_file}")
                    return data
            except Exception as e:
                logging.error(f"Error loading cached data from {json_file}: {str(e)}")
        
        return None
    
    def _save_to_cache(self, data: List[Dict], data_type: str, season: str):
        """Save data to both memory cache and file"""
        cache_key = f"{season}_{data_type}"
        self.cache[cache_key] = data
        
        # Also save to file
        json_file = os.path.join(self.output_dir, f"{cache_key}.json")
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)
        logging.info(f"Saved data to cache: {cache_key}")

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
        """Get team season statistics with caching"""
        # Try to get from cache first
        cached_data = self._load_cached_data("team_stats", season)
        if cached_data is not None and team:
            # Filter cached data for specific team
            team_stats = [s for s in cached_data if s.get('team') == team]
            if team_stats:
                logging.info(f"Using cached team stats for {team}")
                return team_stats
        
        # If no cache or team not found, fetch from API
        formatted_team = self._format_team_name(team) if team else None
        params = {
            "season": season,
            "team": formatted_team,
            "seasonType": "regular"
        }
        
        stats = self._make_request("stats/team/season", params) or []
        
        if stats:
            # Update cache if fetching all teams
            if not team:
                self._save_to_cache(stats, "team_stats", season)
            
            logging.info(f"Retrieved {len(stats)} season stats entries")
        
        return stats

    def get_games(self, season: str, team: Optional[str] = None, status: str = "final") -> List[Dict]:
        """Get basic games data with caching"""
        # Try to get from cache first
        cached_data = self._load_cached_data("games", season)
        if cached_data is not None and team:
            # Filter cached data for specific team
            team_games = [g for g in cached_data if team in (g.get('homeTeam'), g.get('awayTeam'))]
            if team_games:
                logging.info(f"Using cached games data for team {team}")
                return team_games
        
        # If no cache or team not found, fetch from API
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
            
            # Update cache if fetching all games
            if not team:
                self._save_to_cache(games, "games", season)
        
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
                # Create a dictionary for the JSON structure
                sample_structure = {
                    'gameId': sample.get('gameId'),
                    'team': sample.get('team'),
                    'opponent': sample.get('opponent'),
                    'offensePoints': sample.get('offense', {}).get('points', {}).get('total'),
                    'defensePoints': sample.get('defense', {}).get('points', {}).get('total'),
                    'neutralSite': sample.get('neutralSite')
                }
                # Log the structure
                logging.debug(f"Sample game structure: {json.dumps(sample_structure, indent=2)}")
        return detailed_games

    def get_betting_lines(self, season: str, team: Optional[str] = None) -> List[Dict]:
        """Get betting lines data with caching"""
        # Try to get from cache first
        cached_data = self._load_cached_data("betting_lines", season)
        if cached_data is not None and team:
            # Filter cached data for specific team
            team_lines = [l for l in cached_data 
                         if team in (l.get('homeTeam'), l.get('awayTeam'))]
            if team_lines:
                logging.info(f"Using cached betting lines for {team}")
                return team_lines
        
        # If no cache or team not found, fetch from API
        params = {
            "season": season,
            "team": team
        }
        lines = self._make_request("lines", params) or []
        
        if lines:
            # Update cache if fetching all lines
            if not team:
                self._save_to_cache(lines, "betting_lines", season)
            
            logging.info(f"Retrieved {len(lines)} betting lines")
        
        return lines

    def get_team_ratings(self, season: str, team: Optional[str] = None) -> Dict:
        """Get both adjusted and SRS ratings with caching"""
        # Try to get from cache first
        cached_data = self._load_cached_data("ratings", season)
        if cached_data is not None and team:
            # Filter cached data for specific team
            team_ratings = [r for r in cached_data if r.get('team') == team]
            if team_ratings:
                logging.info(f"Using cached ratings for {team}")
                return team_ratings[0].get('ratings', {})
        
        # If no cache or team not found, fetch from API
        params = {"season": season, "team": team}
        adj_ratings = self._make_request("ratings/adjusted", params) or []
        srs_ratings = self._make_request("ratings/srs", params) or []
        
        ratings_data = {
            "adjusted": adj_ratings,
            "srs": srs_ratings
        }
        
        # Update cache if fetching all ratings
        if not team:
            self._save_to_cache([{
                "team": team,
                "ratings": ratings_data
            }], "ratings", season)
        
        return ratings_data

    def _parallel_fetch(self, teams: List[Dict], season: str, fetch_type: str) -> Dict:
        """Fetch data for multiple teams in parallel"""
        results = {}
        max_workers = min(10, len(teams))  # Limit concurrent requests
        
        def fetch_team_data(team: Dict) -> Tuple[str, Optional[List[Dict]]]:
            team_name = team.get('school')
            if not team_name:
                return team_name, None
            
            try:
                if fetch_type == 'stats':
                    data = self.get_team_stats(season, team_name)
                elif fetch_type == 'games':
                    data = self.get_games(season, team_name)
                elif fetch_type == 'betting_lines':
                    data = self.get_betting_lines(season, team_name)
                elif fetch_type == 'ratings':
                    data = self.get_team_ratings(season, team_name)
                else:
                    return team_name, None
                
                return team_name, data
            except Exception as e:
                logging.error(f"Error fetching {fetch_type} for {team_name}: {str(e)}")
                return team_name, None
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_team = {
                executor.submit(fetch_team_data, team): team 
                for team in teams
            }
            
            completed = 0
            total = len(teams)
            
            for future in as_completed(future_to_team):
                completed += 1
                progress = (completed / total) * 100
                self.progress_window.update(
                    subtask=progress,
                    detail=f"Fetching {fetch_type} ({completed}/{total} teams)"
                )
                
                try:
                    team_name, data = future.result()
                    if team_name and data:
                        results[team_name] = data
                except Exception as e:
                    team = future_to_team[future]
                    logging.error(f"Error processing {team.get('school')}: {str(e)}")
        
        return results

    def collect_comprehensive_data(self, season: str):
        """Collect comprehensive data for analysis"""
        logging.info(f"Starting comprehensive data collection for season {season}")
        
        try:
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
            
            # Update progress window
            self.progress_window.update(
                status=f"Processing {len(teams)} teams...",
                detail=f"Starting parallel data collection for {len(teams)} teams",
                progress=0
            )
            
            # Parallel fetch all data types
            progress_increment = 25  # 25% per data type
            
            # 1. Fetch games (0-25%)
            self.progress_window.update(status="Fetching games data...")
            games_results = self._parallel_fetch(teams, season, 'games')
            self.progress_window.update(progress=25)
            
            # Save individual team's games data into separate JSON files
            self._save_games_by_team(games_results, season)
            
            # 2. Fetch team stats (25-50%)
            self.progress_window.update(status="Fetching team statistics...")
            stats_results = self._parallel_fetch(teams, season, 'stats')
            self.progress_window.update(progress=50)
            
            # 3. Fetch betting lines (50-75%)
            self.progress_window.update(status="Fetching betting lines...")
            betting_results = self._parallel_fetch(teams, season, 'betting_lines')
            self.progress_window.update(progress=75)
            
            # 4. Fetch ratings (75-100%)
            self.progress_window.update(status="Fetching team ratings...")
            ratings_results = self._parallel_fetch(teams, season, 'ratings')
            self.progress_window.update(progress=100)
            
            # Process and save results
            self.progress_window.update(
                status="Processing and saving data...",
                detail="Combining and saving collected data",
                subtask=0
            )
            
            # Combine and deduplicate data
            all_games = []
            all_stats = []
            all_betting_lines = []
            all_ratings = []
            seen_game_ids = set()
            seen_betting_line_ids = set()
            
            for team_games in games_results.values():
                if team_games:
                    for game in team_games:
                        game_id = game.get('id')
                        if game_id and game_id not in seen_game_ids:
                            seen_game_ids.add(game_id)
                            all_games.append(game)
            
            for team_stats in stats_results.values():
                if team_stats:
                    all_stats.extend(team_stats)
            
            for team_lines in betting_results.values():
                if team_lines:
                    for line in team_lines:
                        line_id = (
                            str(line.get('gameId', '')),
                            str(line.get('provider', ''))
                        )
                        if line_id not in seen_betting_line_ids:
                            seen_betting_line_ids.add(line_id)
                            all_betting_lines.append(line)
            
            for team_rating in ratings_results.values():
                if team_rating:
                    all_ratings.append(team_rating)
            
            # Save all collected data
            self._save_data_with_progress(all_games, "games", season)
            self._save_data_with_progress(all_stats, "team_stats", season)
            self._save_data_with_progress(all_betting_lines, "betting_lines", season)
            self._save_data_with_progress(all_ratings, "ratings", season)
            
            # Generate summary
            self.progress_window.update(
                status="Generating summary...",
                detail="Finalizing data collection",
                progress=100,
                subtask=100
            )
            
            analyzed_teams = set(team.get('school') for team in teams if team.get('school'))
            self._generate_summary_stats(all_games, all_stats, all_betting_lines, all_ratings, season, analyzed_teams)
            
            # Show completion
            self.progress_window.update(
                status="Data collection complete!",
                progress=100,
                subtask=100,
                detail=f"All operations finished successfully. Processed {len(analyzed_teams)} teams."
            )
            
        except Exception as e:
            logging.error(f"Error in data collection: {str(e)}", exc_info=True)
            self.progress_window.update(
                status="Error occurred during data collection",
                detail=f"Error: {str(e)}. Window will close automatically..."
            )
        finally:
            # Clean up session
            self.session.close()

    def _save_data_with_progress(self, data: List[Dict], data_type: str, season: str):
        """Save data to both JSON and CSV formats with progress tracking"""
        if not data:
            logging.warning(f"No {data_type} data to save")
            return
        
        # Create a season-specific folder inside the output directory
        season_folder = os.path.join(self.output_dir, season)
        os.makedirs(season_folder, exist_ok=True)

        json_file = os.path.join(season_folder, f"{data_type}.json")
        self.progress_window.update(
            detail=f"Saving {data_type} (JSON)",
            subtask=25
        )
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Process data for CSV using a comprehensive flattening function
        self.progress_window.update(
            detail=f"Processing {data_type} for CSV",
            subtask=50
        )
        def flatten_data(d, parent_key='', sep='_'):
            items = {}
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if v is None:
                    items[new_key] = ""
                elif isinstance(v, dict):
                    items.update(flatten_data(v, new_key, sep=sep))
                elif isinstance(v, list):
                    if all(isinstance(elem, (int, float, str, bool)) for elem in v):
                        items[new_key] = ','.join(map(str, v))
                    else:
                        items[new_key] = json.dumps(v)
                else:
                    items[new_key] = v
            return items
        
        # Flatten each data item
        flattened_data = [flatten_data(item) for item in data]
        
        # Collect all headers (union of keys across all items)
        header_set = set()
        for item in flattened_data:
            header_set.update(item.keys())
        
        # Define priority headers that should appear first if available
        priority_headers = ['team', 'season', 'conference']
        remaining_headers = sorted(list(header_set - set(priority_headers)))
        csv_headers = [h for h in priority_headers if h in header_set] + remaining_headers
        
        # Ensure each flattened item has all headers
        for item in flattened_data:
            for header in csv_headers:
                if header not in item:
                    item[header] = None
        
        self.progress_window.update(
            detail=f"Saving {data_type} (CSV)",
            subtask=75
        )
        csv_file = os.path.join(season_folder, f"{data_type}.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=csv_headers)
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

    def _save_games_by_team(self, games_results: Dict[str, List[Dict]], season: str):
        """Save each team's games data into individual JSON and CSV files in a subdirectory."""
        team_folder = os.path.join(self.output_dir, season, "teams")
        os.makedirs(team_folder, exist_ok=True)

        def flatten_data(d, parent_key='', sep='_'):
            items = {}
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if v is None:
                    items[new_key] = ""
                elif isinstance(v, dict):
                    items.update(flatten_data(v, new_key, sep=sep))
                elif isinstance(v, list):
                    if all(isinstance(elem, (int, float, str, bool)) for elem in v):
                        items[new_key] = ','.join(map(str, v))
                    else:
                        items[new_key] = json.dumps(v)
                else:
                    items[new_key] = v
            return items

        for team, games in games_results.items():
            # Create a safe filename by removing unwanted characters and replacing spaces
            safe_team = ''.join(c for c in team if c.isalnum() or c in (' ', '_', '-')).rstrip().replace(' ', '_')

            # Save JSON file
            json_file_path = os.path.join(team_folder, f"{safe_team}.json")
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(games, f, indent=2)
            logging.info(f"Saved games for team {team} to {json_file_path}")

            # Prepare and save CSV file
            flattened_games = [flatten_data(game) for game in games]
            header_set = set()
            for item in flattened_games:
                header_set.update(item.keys())
            csv_headers = sorted(list(header_set))

            # Ensure each flattened game has all headers, fill missing with empty string
            for game in flattened_games:
                for header in csv_headers:
                    if header not in game:
                        game[header] = ""

            csv_file_path = os.path.join(team_folder, f"{safe_team}.csv")
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=csv_headers)
                writer.writeheader()
                writer.writerows(flattened_games)
            logging.info(f"Saved CSV games for team {team} to {csv_file_path}")

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