import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import json
from typing import Dict, Optional

class DataVisualizationGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Sports Betting Data Visualization")
        self.master.geometry("1100x750")
        
        # Load data first
        self.data = self.load_data()
        if not self.data:
            messagebox.showerror("Error", "No data found in data_output directory. Please run data collection first.")
            self.master.destroy()
            return

        # Notebook (tabbed interface)
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(expand=True, fill='both')

        # Create tabs
        self.create_summary_tab(self.data)
        self.create_games_tab(self.data)
        self.create_team_stats_tab(self.data)
        self.create_betting_lines_tab(self.data)
        self.create_win_loss_tab(self.data)
        self.create_correlation_heatmap_tab(self.data)

    def load_data(self) -> Optional[Dict]:
        """Load all data files from the data_output directory"""
        try:
            data_dir = "data_output"
            if not os.path.exists(data_dir):
                return None

            # Find the most recent season's files
            seasons = set()
            for file in os.listdir(data_dir):
                if file.endswith('.json'):
                    season = file.split('_')[0]
                    seasons.add(season)

            if not seasons:
                return None

            latest_season = max(seasons)
            data = {}

            # Load each data type
            data_types = ['games', 'team_stats', 'betting_lines', 'ratings', 'summary']
            for data_type in data_types:
                json_file = os.path.join(data_dir, f"{latest_season}_{data_type}.json")
                if os.path.exists(json_file):
                    with open(json_file, 'r') as f:
                        data[data_type] = json.load(f)
                        # Convert to DataFrame if it's a list
                        if isinstance(data[data_type], list):
                            data[data_type] = pd.DataFrame(data[data_type])

            return data
        except Exception as e:
            messagebox.showerror("Error", f"Error loading data: {str(e)}")
            return None

    def create_summary_tab(self, data):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Summary")

        if not data or 'summary' not in data:
            tk.Label(tab, text="No summary data available").pack()
            return

        # Create a frame for summary statistics
        stats_frame = ttk.LabelFrame(tab, text="Season Overview")
        stats_frame.pack(fill='x', padx=10, pady=5)

        # Display summary statistics
        summary = data['summary']
        stats_text = f"""
        Season: {summary.get('season', 'N/A')}
        Total Games: {summary.get('total_games', 0)}
        Games with Scores: {summary.get('valid_games_with_scores', 0)}
        Teams Analyzed: {summary.get('analyzed_teams', 0)}
        Average Total Score: {summary.get('average_total_score', 0):.2f}
        Total Betting Lines: {summary.get('total_betting_lines', 0)}
        """
        tk.Label(stats_frame, text=stats_text, justify='left').pack(padx=10, pady=5)

        # Create graphs frame
        graphs_frame = ttk.Frame(tab)
        graphs_frame.pack(fill='both', expand=True, padx=10, pady=5)
        graphs_frame.grid_columnconfigure(0, weight=1)
        graphs_frame.grid_columnconfigure(1, weight=1)

        # Top teams by wins (if team_stats available)
        if 'team_stats' in data and isinstance(data['team_stats'], pd.DataFrame):
            team_stats = data['team_stats']
            
            # Left plot: Top 10 teams by wins
            fig1, ax1 = plt.subplots(figsize=(6, 4))
            top_teams = team_stats.nlargest(10, 'wins')
            ax1.barh(top_teams['team'], top_teams['wins'], color='skyblue')
            ax1.set_title("Top 10 Teams by Wins")
            ax1.set_xlabel("Wins")
            plt.tight_layout()
            
            canvas1 = FigureCanvasTkAgg(fig1, master=graphs_frame)
            canvas1.draw()
            canvas1.get_tk_widget().grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

            # Right plot: Win percentage distribution
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            team_stats['win_pct'] = team_stats['wins'] / (team_stats['wins'] + team_stats['losses']) * 100
            ax2.hist(team_stats['win_pct'], bins=20, color='lightgreen', edgecolor='black')
            ax2.set_title("Win Percentage Distribution")
            ax2.set_xlabel("Win Percentage")
            ax2.set_ylabel("Number of Teams")
            plt.tight_layout()
            
            canvas2 = FigureCanvasTkAgg(fig2, master=graphs_frame)
            canvas2.draw()
            canvas2.get_tk_widget().grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

            # Bottom plot: Average points per game distribution
            fig3, ax3 = plt.subplots(figsize=(12, 4))
            if 'offense' in team_stats.columns and 'points' in team_stats['offense'].iloc[0]:
                points_per_game = team_stats.apply(
                    lambda x: x['offense']['points']['total'] / x['games'] 
                    if isinstance(x['offense'], dict) else 0, 
                    axis=1
                )
                ax3.hist(points_per_game, bins=30, color='salmon', edgecolor='black')
                ax3.set_title("Points per Game Distribution")
                ax3.set_xlabel("Points per Game")
                ax3.set_ylabel("Number of Teams")
                plt.tight_layout()
                
                canvas3 = FigureCanvasTkAgg(fig3, master=graphs_frame)
                canvas3.draw()
                canvas3.get_tk_widget().grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        else:
            tk.Label(graphs_frame, text="No team statistics available for visualization").pack()

    def create_games_tab(self, data):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Games Data")

        if not data or 'games' not in data or not isinstance(data['games'], pd.DataFrame):
            tk.Label(tab, text="No games data available").pack()
            return

        # Create control frame
        control_frame = ttk.Frame(tab)
        control_frame.pack(fill='x', padx=10, pady=5)

        # Add team filter
        team_label = ttk.Label(control_frame, text="Select Team:")
        team_label.pack(side='left', padx=5)
        
        teams = sorted(data['games']['homeTeam'].unique())
        team_var = tk.StringVar(value='All Teams')
        team_combo = ttk.Combobox(control_frame, textvariable=team_var, values=['All Teams'] + list(teams))
        team_combo.pack(side='left', padx=5)

        # Create graphs frame
        graphs_frame = ttk.Frame(tab)
        graphs_frame.pack(fill='both', expand=True, padx=10, pady=5)
        graphs_frame.grid_columnconfigure(0, weight=1)
        graphs_frame.grid_columnconfigure(1, weight=1)

        def update_plots(*args):
            # Clear previous plots
            for widget in graphs_frame.winfo_children():
                widget.destroy()

            games_df = data['games']
            selected_team = team_var.get()
            
            if selected_team != 'All Teams':
                team_games = games_df[
                    (games_df['homeTeam'] == selected_team) | 
                    (games_df['awayTeam'] == selected_team)
                ]
            else:
                team_games = games_df

            # Ensure we have numeric points
            team_games['homePoints'] = pd.to_numeric(team_games['homePoints'], errors='coerce')
            team_games['awayPoints'] = pd.to_numeric(team_games['awayPoints'], errors='coerce')
            team_games = team_games.dropna(subset=['homePoints', 'awayPoints'])

            if team_games.empty:
                tk.Label(graphs_frame, text="No valid game data available").pack()
                return

            # Plot 1: Total points distribution
            fig1, ax1 = plt.subplots(figsize=(6, 4))
            total_points = team_games['homePoints'] + team_games['awayPoints']
            ax1.hist(total_points, bins=20, color='skyblue', edgecolor='black')
            ax1.set_title(f"Total Points Distribution\n{'(All Teams)' if selected_team == 'All Teams' else f'({selected_team})'}")
            ax1.set_xlabel("Total Points")
            ax1.set_ylabel("Number of Games")
            plt.tight_layout()
            
            canvas1 = FigureCanvasTkAgg(fig1, master=graphs_frame)
            canvas1.draw()
            canvas1.get_tk_widget().grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

            # Plot 2: Point differential distribution
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            point_diff = team_games['homePoints'] - team_games['awayPoints']
            ax2.hist(point_diff, bins=20, color='lightgreen', edgecolor='black')
            ax2.set_title(f"Point Differential Distribution\n{'(Home - Away)'}")
            ax2.set_xlabel("Point Differential")
            ax2.set_ylabel("Number of Games")
            plt.tight_layout()
            
            canvas2 = FigureCanvasTkAgg(fig2, master=graphs_frame)
            canvas2.draw()
            canvas2.get_tk_widget().grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

            # Plot 3: Points timeline
            fig3, ax3 = plt.subplots(figsize=(12, 4))
            if selected_team != 'All Teams':
                team_points = []
                game_numbers = []
                for idx, game in team_games.iterrows():
                    if game['homeTeam'] == selected_team:
                        team_points.append(game['homePoints'])
                    else:
                        team_points.append(game['awayPoints'])
                    game_numbers.append(len(game_numbers) + 1)
                
                ax3.plot(game_numbers, team_points, marker='o', linestyle='-', color='blue', label=f'{selected_team} Points')
                ax3.set_title(f"Points Timeline for {selected_team}")
                ax3.set_xlabel("Game Number")
                ax3.set_ylabel("Points Scored")
                
                # Add moving average
                window = min(5, len(team_points))  # Use 5-game moving average or less if fewer games
                if window > 1:
                    moving_avg = pd.Series(team_points).rolling(window=window).mean()
                    ax3.plot(game_numbers, moving_avg, color='red', linestyle='--', 
                            label=f'{window}-Game Moving Average')
                
                ax3.legend()
            else:
                ax3.text(0.5, 0.5, "Select a specific team to see points timeline", 
                        ha='center', va='center', transform=ax3.transAxes)
            plt.tight_layout()
            
            canvas3 = FigureCanvasTkAgg(fig3, master=graphs_frame)
            canvas3.draw()
            canvas3.get_tk_widget().grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

        # Bind the update function to team selection
        team_combo.bind('<<ComboboxSelected>>', update_plots)
        
        # Initial plot
        update_plots()

    def create_team_stats_tab(self, data):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Team Stats")

        if not data or 'team_stats' not in data or not isinstance(data['team_stats'], pd.DataFrame):
            tk.Label(tab, text="No team stats data available").pack()
            return

        # Create control frame
        control_frame = ttk.Frame(tab)
        control_frame.pack(fill='x', padx=10, pady=5)

        # Add team filter
        team_label = ttk.Label(control_frame, text="Select Team:")
        team_label.pack(side='left', padx=5)
        
        teams = sorted(data['team_stats']['team'].unique())
        team_var = tk.StringVar(value=teams[0] if teams else '')
        team_combo = ttk.Combobox(control_frame, textvariable=team_var, values=teams)
        team_combo.pack(side='left', padx=5)

        # Create content frame
        content_frame = ttk.Frame(tab)
        content_frame.pack(fill='both', expand=True, padx=10, pady=5)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        def update_stats(*args):
            # Clear previous content
            for widget in content_frame.winfo_children():
                widget.destroy()

            team_stats = data['team_stats']
            selected_team = team_var.get()
            team_data = team_stats[team_stats['team'] == selected_team].iloc[0]

            # Create stats panel
            stats_frame = ttk.LabelFrame(content_frame, text="Team Overview")
            stats_frame.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

            # Basic stats
            stats_text = f"""
            Conference: {team_data.get('conference', 'N/A')}
            Games Played: {team_data.get('games', 0)}
            Wins: {team_data.get('wins', 0)}
            Losses: {team_data.get('losses', 0)}
            Win Rate: {(team_data.get('wins', 0) / team_data.get('games', 1) * 100):.1f}%
            """
            tk.Label(stats_frame, text=stats_text, justify='left').pack(padx=10, pady=5)

            # Create offensive stats frame
            off_frame = ttk.LabelFrame(content_frame, text="Offensive Stats")
            off_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

            if isinstance(team_data.get('offense'), dict):
                offense = team_data['offense']
                off_stats = f"""
                Points per Game: {offense['points']['total'] / team_data['games']:.1f}
                Field Goal %: {offense['fieldGoals']['pct']:.1f}%
                3-Point %: {offense['threePointFieldGoals']['pct']:.1f}%
                Free Throw %: {offense['freeThrows']['pct']:.1f}%
                Assists per Game: {offense['assists'] / team_data['games']:.1f}
                Turnovers per Game: {offense['turnovers']['total'] / team_data['games']:.1f}
                """
                tk.Label(off_frame, text=off_stats, justify='left').pack(padx=10, pady=5)

            # Create plots frame
            plots_frame = ttk.Frame(content_frame)
            plots_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

            if isinstance(team_data.get('offense'), dict):
                offense = team_data['offense']
                
                # Plot 1: Shooting percentages
                fig1, ax1 = plt.subplots(figsize=(6, 4))
                shot_types = ['Field Goals', '2-Point', '3-Point', 'Free Throws']
                percentages = [
                    offense['fieldGoals']['pct'],
                    offense['twoPointFieldGoals']['pct'],
                    offense['threePointFieldGoals']['pct'],
                    offense['freeThrows']['pct']
                ]
                ax1.bar(shot_types, percentages, color=['skyblue', 'lightgreen', 'salmon', 'purple'])
                ax1.set_title(f"Shooting Percentages - {selected_team}")
                ax1.set_ylabel("Percentage")
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                canvas1 = FigureCanvasTkAgg(fig1, master=plots_frame)
                canvas1.draw()
                canvas1.get_tk_widget().grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

                # Plot 2: Four Factors
                fig2, ax2 = plt.subplots(figsize=(6, 4))
                factors = list(offense['fourFactors'].keys())
                values = list(offense['fourFactors'].values())
                ax2.bar(factors, values, color='lightblue')
                ax2.set_title(f"Four Factors - {selected_team}")
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                canvas2 = FigureCanvasTkAgg(fig2, master=plots_frame)
                canvas2.draw()
                canvas2.get_tk_widget().grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

        # Bind the update function to team selection
        team_combo.bind('<<ComboboxSelected>>', update_stats)
        
        # Initial stats display
        if teams:
            update_stats()

    def create_betting_lines_tab(self, data):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Betting Lines")

        if not data or 'betting_lines' not in data or not isinstance(data['betting_lines'], pd.DataFrame):
            tk.Label(tab, text="No betting lines data available").pack()
            return

        # Create control frame
        control_frame = ttk.Frame(tab)
        control_frame.pack(fill='x', padx=10, pady=5)

        # Create content frame
        content_frame = ttk.Frame(tab)
        content_frame.pack(fill='both', expand=True, padx=10, pady=5)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        def update_analysis(*args):
            # Clear previous content
            for widget in content_frame.winfo_children():
                widget.destroy()

            lines_df = data['betting_lines'].copy()

            if lines_df.empty:
                tk.Label(content_frame, text="No betting data available").pack()
                return

            # Create summary stats frame
            stats_frame = ttk.LabelFrame(content_frame, text="Betting Summary")
            stats_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

            # Calculate basic stats
            total_games = len(lines_df)
            avg_line = lines_df['line'].mean() if 'line' in lines_df.columns else None
            avg_line_text = f"{avg_line:.1f}" if avg_line is not None else "N/A"
            
            stats_text = f"""
            Total Games: {total_games}
            Average Line: {avg_line_text}
            """
            tk.Label(stats_frame, text=stats_text, justify='left').pack(padx=10, pady=5)

            if 'line' in lines_df.columns:
                # Plot 1: Line distribution
                fig1, ax1 = plt.subplots(figsize=(6, 4))
                ax1.hist(lines_df['line'].dropna(), bins=20, color='skyblue', edgecolor='black')
                ax1.set_title("Line Distribution")
                ax1.set_xlabel("Line")
                ax1.set_ylabel("Frequency")
                plt.tight_layout()
                
                canvas1 = FigureCanvasTkAgg(fig1, master=content_frame)
                canvas1.draw()
                canvas1.get_tk_widget().grid(row=1, column=0, padx=5, pady=5, sticky='nsew')

                # Plot 2: Results vs Lines
                if 'result' in lines_df.columns:
                    fig2, ax2 = plt.subplots(figsize=(6, 4))
                    ax2.scatter(lines_df['line'], lines_df['result'], color='lightgreen', alpha=0.6)
                    ax2.set_title("Results vs Lines")
                    ax2.set_xlabel("Line")
                    ax2.set_ylabel("Result")
                    plt.tight_layout()
                    
                    canvas2 = FigureCanvasTkAgg(fig2, master=content_frame)
                    canvas2.draw()
                    canvas2.get_tk_widget().grid(row=1, column=1, padx=5, pady=5, sticky='nsew')

        # Initial analysis display
        update_analysis()

    def create_win_loss_tab(self, data):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Win/Loss Distribution")

        if not data or 'games' not in data or not isinstance(data['games'], pd.DataFrame):
            tk.Label(tab, text="No games data available").pack()
            return

        # Create control frame
        control_frame = ttk.Frame(tab)
        control_frame.pack(fill='x', padx=10, pady=5)

        # Add team filter
        team_label = ttk.Label(control_frame, text="Select Team:")
        team_label.pack(side='left', padx=5)
        
        teams = sorted(pd.concat([
            data['games']['homeTeam'],
            data['games']['awayTeam']
        ]).unique())
        team_var = tk.StringVar(value='All Teams')
        team_combo = ttk.Combobox(control_frame, textvariable=team_var, values=['All Teams'] + list(teams))
        team_combo.pack(side='left', padx=5)

        # Create content frame
        content_frame = ttk.Frame(tab)
        content_frame.pack(fill='both', expand=True, padx=10, pady=5)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        def update_analysis(*args):
            # Clear previous content
            for widget in content_frame.winfo_children():
                widget.destroy()

            games_df = data['games'].copy()
            selected_team = team_var.get()
            
            # Ensure numeric points
            games_df['homePoints'] = pd.to_numeric(games_df['homePoints'], errors='coerce')
            games_df['awayPoints'] = pd.to_numeric(games_df['awayPoints'], errors='coerce')
            games_df = games_df.dropna(subset=['homePoints', 'awayPoints'])

            if selected_team != 'All Teams':
                team_games = games_df[
                    (games_df['homeTeam'] == selected_team) | 
                    (games_df['awayTeam'] == selected_team)
                ]
            else:
                team_games = games_df

            if team_games.empty:
                tk.Label(content_frame, text="No game data available for selected team").pack()
                return

            # Create summary stats frame
            stats_frame = ttk.LabelFrame(content_frame, text="Win/Loss Summary")
            stats_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

            if selected_team != 'All Teams':
                # Calculate team-specific stats
                home_games = team_games[team_games['homeTeam'] == selected_team]
                away_games = team_games[team_games['awayTeam'] == selected_team]
                
                home_wins = sum(home_games['homePoints'] > home_games['awayPoints'])
                home_losses = sum(home_games['homePoints'] < home_games['awayPoints'])
                away_wins = sum(away_games['awayPoints'] > away_games['homePoints'])
                away_losses = sum(away_games['awayPoints'] < away_games['homePoints'])
                
                total_wins = home_wins + away_wins
                total_losses = home_losses + away_losses
                win_pct = (total_wins / (total_wins + total_losses)) * 100 if (total_wins + total_losses) > 0 else 0
                
                stats_text = f"""
                Total Games: {len(team_games)}
                Total Wins: {total_wins}
                Total Losses: {total_losses}
                Win Percentage: {win_pct:.1f}%
                
                Home Record: {home_wins}-{home_losses}
                Away Record: {away_wins}-{away_losses}
                Home Win %: {(home_wins / len(home_games) * 100):.1f}% if len(home_games) > 0 else 'N/A'
                Away Win %: {(away_wins / len(away_games) * 100):.1f}% if len(away_games) > 0 else 'N/A'
                """
            else:
                # Calculate overall league stats
                home_wins = sum(games_df['homePoints'] > games_df['awayPoints'])
                away_wins = sum(games_df['awayPoints'] > games_df['homePoints'])
                total_games = len(games_df)
                
                stats_text = f"""
                Total Games: {total_games}
                Home Team Wins: {home_wins}
                Away Team Wins: {away_wins}
                Home Win %: {(home_wins / total_games * 100):.1f}%
                Away Win %: {(away_wins / total_games * 100):.1f}%
                """

            tk.Label(stats_frame, text=stats_text, justify='left').pack(padx=10, pady=5)

            # Plot 1: Win/Loss Pie Chart
            fig1, ax1 = plt.subplots(figsize=(6, 6))
            if selected_team != 'All Teams':
                values = [total_wins, total_losses]
                labels = ['Wins', 'Losses']
                colors = ['lightgreen', 'salmon']
                title = f"Win/Loss Distribution - {selected_team}"
            else:
                values = [home_wins, away_wins]
                labels = ['Home Wins', 'Away Wins']
                colors = ['lightblue', 'lightgreen']
                title = "Home vs Away Wins Distribution"
                
            ax1.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.set_title(title)
            plt.tight_layout()
            
            canvas1 = FigureCanvasTkAgg(fig1, master=content_frame)
            canvas1.draw()
            canvas1.get_tk_widget().grid(row=1, column=0, padx=5, pady=5, sticky='nsew')

            # Plot 2: Point Differential Distribution
            fig2, ax2 = plt.subplots(figsize=(6, 6))
            if selected_team != 'All Teams':
                point_diffs = []
                for _, game in team_games.iterrows():
                    if game['homeTeam'] == selected_team:
                        point_diffs.append(game['homePoints'] - game['awayPoints'])
                    else:
                        point_diffs.append(game['awayPoints'] - game['homePoints'])
                
                ax2.hist(point_diffs, bins=20, color='skyblue', edgecolor='black')
                ax2.set_title(f"Point Differential Distribution\n{selected_team}")
                ax2.set_xlabel("Point Differential (Positive = Win)")
            else:
                point_diffs = games_df['homePoints'] - games_df['awayPoints']
                ax2.hist(point_diffs, bins=20, color='skyblue', edgecolor='black')
                ax2.set_title("Home Team Point Differential Distribution")
                ax2.set_xlabel("Point Differential (Positive = Home Win)")
            
            ax2.set_ylabel("Number of Games")
            plt.tight_layout()
            
            canvas2 = FigureCanvasTkAgg(fig2, master=content_frame)
            canvas2.draw()
            canvas2.get_tk_widget().grid(row=1, column=1, padx=5, pady=5, sticky='nsew')

            # Plot 3: Win/Loss Timeline
            if selected_team != 'All Teams':
                fig3, ax3 = plt.subplots(figsize=(12, 4))
                
                results = []
                dates = []
                for _, game in team_games.iterrows():
                    if game['homeTeam'] == selected_team:
                        results.append(1 if game['homePoints'] > game['awayPoints'] else 0)
                    else:
                        results.append(1 if game['awayPoints'] > game['homePoints'] else 0)
                    dates.append(len(results))
                
                # Calculate running win percentage
                running_pct = [sum(results[:i+1])/(i+1) * 100 for i in range(len(results))]
                
                ax3.plot(dates, running_pct, marker='o', linestyle='-', color='blue')
                ax3.set_title(f"Running Win Percentage - {selected_team}")
                ax3.set_xlabel("Games Played")
                ax3.set_ylabel("Win Percentage")
                ax3.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                
                canvas3 = FigureCanvasTkAgg(fig3, master=content_frame)
                canvas3.draw()
                canvas3.get_tk_widget().grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

        # Bind the update function to team selection
        team_combo.bind('<<ComboboxSelected>>', update_analysis)
        
        # Initial analysis display
        update_analysis()

    def create_correlation_heatmap_tab(self, data):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Correlation Heatmap")

        if not data or 'team_stats' not in data or not isinstance(data['team_stats'], pd.DataFrame):
            tk.Label(tab, text="No team stats data available for correlation analysis").pack()
            return

        # Create control frame
        control_frame = ttk.Frame(tab)
        control_frame.pack(fill='x', padx=10, pady=5)

        # Add metric type selector
        metric_label = ttk.Label(control_frame, text="Select Metrics:")
        metric_label.pack(side='left', padx=5)
        
        metric_var = tk.StringVar(value='Basic Stats')
        metric_combo = ttk.Combobox(control_frame, textvariable=metric_var, 
                                  values=['Basic Stats', 'Offensive Stats', 'Shooting Stats', 'Advanced Stats'])
        metric_combo.pack(side='left', padx=5)

        # Create content frame
        content_frame = ttk.Frame(tab)
        content_frame.pack(fill='both', expand=True, padx=10, pady=5)

        def update_correlation(*args):
            # Clear previous content
            for widget in content_frame.winfo_children():
                widget.destroy()

            team_stats = data['team_stats'].copy()
            selected_metrics = metric_var.get()

            # Extract and prepare data based on selected metrics
            if selected_metrics == 'Basic Stats':
                # Basic team statistics
                metrics_df = pd.DataFrame({
                    'Wins': team_stats['wins'],
                    'Losses': team_stats['losses'],
                    'Win Rate': team_stats['wins'] / (team_stats['wins'] + team_stats['losses']),
                    'Games': team_stats['games'],
                    'Pace': team_stats['pace']
                })
                
                if 'offense' in team_stats.columns:
                    metrics_df['Points/Game'] = team_stats.apply(
                        lambda x: x['offense']['points']['total'] / x['games'] 
                        if isinstance(x['offense'], dict) else None,
                        axis=1
                    )

            elif selected_metrics == 'Offensive Stats':
                # Create offensive metrics dataframe
                metrics_df = pd.DataFrame()
                
                def safe_get(row, *keys):
                    value = row
                    for key in keys:
                        if isinstance(value, dict) and key in value:
                            value = value[key]
                        else:
                            return None
                    return value

                metrics_df['Points/Game'] = team_stats.apply(
                    lambda x: safe_get(x, 'offense', 'points', 'total') / x['games'], axis=1)
                metrics_df['Assists/Game'] = team_stats.apply(
                    lambda x: safe_get(x, 'offense', 'assists') / x['games'], axis=1)
                metrics_df['Turnovers/Game'] = team_stats.apply(
                    lambda x: safe_get(x, 'offense', 'turnovers', 'total') / x['games'], axis=1)
                metrics_df['Off Rebounds/Game'] = team_stats.apply(
                    lambda x: safe_get(x, 'offense', 'rebounds', 'offensive') / x['games'], axis=1)
                metrics_df['Def Rebounds/Game'] = team_stats.apply(
                    lambda x: safe_get(x, 'offense', 'rebounds', 'defensive') / x['games'], axis=1)

            elif selected_metrics == 'Shooting Stats':
                # Create shooting metrics dataframe
                metrics_df = pd.DataFrame()
                
                metrics_df['FG%'] = team_stats.apply(
                    lambda x: x['offense']['fieldGoals']['pct'] 
                    if isinstance(x['offense'], dict) else None, 
                    axis=1
                )
                metrics_df['3P%'] = team_stats.apply(
                    lambda x: x['offense']['threePointFieldGoals']['pct']
                    if isinstance(x['offense'], dict) else None,
                    axis=1
                )
                metrics_df['2P%'] = team_stats.apply(
                    lambda x: x['offense']['twoPointFieldGoals']['pct']
                    if isinstance(x['offense'], dict) else None,
                    axis=1
                )
                metrics_df['FT%'] = team_stats.apply(
                    lambda x: x['offense']['freeThrows']['pct']
                    if isinstance(x['offense'], dict) else None,
                    axis=1
                )
                metrics_df['True Shooting%'] = team_stats.apply(
                    lambda x: x['offense']['trueShooting']
                    if isinstance(x['offense'], dict) else None,
                    axis=1
                )

            else:  # Advanced Stats
                # Create advanced metrics dataframe
                metrics_df = pd.DataFrame()
                
                metrics_df['Pace'] = team_stats['pace']
                metrics_df['Off Rating'] = team_stats.apply(
                    lambda x: x['offense']['rating']
                    if isinstance(x['offense'], dict) else None,
                    axis=1
                )
                metrics_df['eFG%'] = team_stats.apply(
                    lambda x: x['offense']['fourFactors']['effectiveFieldGoalPct']
                    if isinstance(x['offense'], dict) else None,
                    axis=1
                )
                metrics_df['TO Ratio'] = team_stats.apply(
                    lambda x: x['offense']['fourFactors']['turnoverRatio']
                    if isinstance(x['offense'], dict) else None,
                    axis=1
                )
                metrics_df['Off Reb%'] = team_stats.apply(
                    lambda x: x['offense']['fourFactors']['offensiveReboundPct']
                    if isinstance(x['offense'], dict) else None,
                    axis=1
                )

            # Drop any rows with NaN values
            metrics_df = metrics_df.dropna()

            if metrics_df.empty:
                tk.Label(content_frame, text="No valid data available for selected metrics").pack()
                return

            # Calculate correlation matrix
            corr_matrix = metrics_df.corr()

            # Create correlation heatmap
            fig, ax = plt.subplots(figsize=(10, 8))
            im = ax.imshow(corr_matrix, cmap='coolwarm', aspect='auto')

            # Add colorbar
            plt.colorbar(im)

            # Add labels
            ax.set_xticks(np.arange(len(corr_matrix.columns)))
            ax.set_yticks(np.arange(len(corr_matrix.columns)))
            ax.set_xticklabels(corr_matrix.columns, rotation=45, ha='right')
            ax.set_yticklabels(corr_matrix.columns)

            # Add correlation values in cells
            for i in range(len(corr_matrix.columns)):
                for j in range(len(corr_matrix.columns)):
                    text = ax.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                                 ha='center', va='center',
                                 color='white' if abs(corr_matrix.iloc[i, j]) > 0.5 else 'black')

            ax.set_title(f"Correlation Heatmap - {selected_metrics}")
            plt.tight_layout()

            # Create canvas and pack
            canvas = FigureCanvasTkAgg(fig, master=content_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)

            # Add explanation text
            explanation = """
            Correlation Coefficient Guide:
            1.0 = Perfect positive correlation
            0.0 = No correlation
            -1.0 = Perfect negative correlation
            
            Strong correlations (>0.5 or <-0.5) are shown in white text
            """
            tk.Label(content_frame, text=explanation, justify='left').pack(padx=10, pady=5)

        # Bind the update function to metric selection
        metric_combo.bind('<<ComboboxSelected>>', update_correlation)
        
        # Initial correlation display
        update_correlation()

if __name__ == "__main__":
    root = tk.Tk()

    # Sample data simulation – replace these with your actual API-collected data
    sample_data = {
        "avg_score": {"Team A": 75, "Team B": 68, "Team C": 80},
        "games": pd.DataFrame({
            "homePoints": [75, 68, 80, 70, 85, 90, 65, 78, 82, 77],
            "awayPoints": [70, 75, 78, 72, 80, 85, 68, 80, 76, 80]
        }),
        "team_stats": pd.DataFrame({
            "team": ["Team A"] * 5 + ["Team B"] * 5,
            "game_id": list(range(1, 6)) + list(range(1, 6)),
            "score": [75, 80, 72, 78, 74, 68, 70, 69, 72, 71],
            "margin": [5, 10, 3, 7, 4, -2, 1, 0, 2, -1]  # example extra metric
        }),
        "betting_lines": pd.DataFrame({
            "line": [5, -3, 7, -2, 4, 2, -1, 6, -4, 3],
            "result": [6, -2, 8, -1, 5, 3, 0, 7, -3, 4]
        })
    }

    app = DataVisualizationGUI(root)
    root.mainloop()
