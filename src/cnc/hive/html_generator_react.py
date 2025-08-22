"""Main HTML generation for hive games - React version"""

from pathlib import Path
import structlog
import json

from cnc.hive.config import get_config
from cnc.hive.fetch_hive_games import GameCache
from cnc.hive.games_data import create_games_list
from cnc.hive.table_generator_react import generate_game_counts_data
from cnc.hive.database import HiveDatabase

# Get logger for this module
logger = structlog.get_logger()


def generate_hive_html_react() -> str:
    """Generate the main hive HTML page with React"""
    # Get all players
    root = Path(__file__).parent.parent.parent.parent
    config = get_config(root / "data" / "hive.toml")
    known_players = config.players

    # Load cached game data
    cache_file = root / "data" / "hive_games_cache.json"
    all_games_raw = GameCache.model_validate_json(cache_file.read_text()).players

    raw_games = create_games_list(
        [game for player_cache in all_games_raw.values() for game in player_cache.games]
    )

    # Create database instance and load data
    db = HiveDatabase()
    db.load_data(config, raw_games)  # Use raw_games, not merged games

    # Generate structured data for React instead of HTML table
    table_data = generate_game_counts_data(db, config)

    # Close database connection
    db.close()

    logger.info(f"Generated table data with {len(table_data['players'])} players")

    # Generate the HTML content directly
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hive Games - React Version</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .stats {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            border-bottom: 1px solid #e9ecef;
        }}
        .stats span {{
            display: inline-block;
            margin: 0 20px;
            font-size: 1.1em;
        }}
        .stats .number {{
            font-weight: bold;
            color: #667eea;
            font-size: 1.3em;
        }}
        #hive-table-root {{
            padding: 20px;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #666;
        }}
        .error {{
            background: #fee;
            color: #c33;
            padding: 20px;
            border-radius: 4px;
            margin: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐝 Hive Games</h1>
            <p>Game statistics and match history</p>
        </div>
        
        <div class="stats">
            <span>Players: <span class="number">{len(table_data["players"])}</span></span>
            <span>Total Games: <span class="number">{sum(p["total_games"] for p in table_data["players"])}</span></span>
            <span>Matchups: <span class="number">{len(table_data["game_stats"])}</span></span>
        </div>
        
        <div id="hive-table-root">
            <div class="loading">Loading React table...</div>
        </div>
    </div>

    <!-- React and dependencies -->
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    
    <!-- Data -->
    <script>
        window.tableData = {json.dumps(table_data, indent=2)};
    </script>
    
    <!-- React Component -->
    <script type="text/babel">
        const {{ useState, useEffect }} = React;
        
        function HiveTable() {{
            const [sortConfig, setSortConfig] = useState({{ field: 'total_games', direction: 'desc' }});
            const data = window.tableData;
            
            if (!data) {{
                return <div className="error">Error: No data available</div>;
            }}
            
            const {{ players, game_stats, config }} = data;
            
            // Sort players
            const sortedPlayers = [...players].sort((a, b) => {{
                if (sortConfig.field === 'total_games') {{
                    return sortConfig.direction === 'asc' ? a.total_games - b.total_games : b.total_games - a.total_games;
                }}
                return 0;
            }});
            
            const getGroupColor = (groups) => {{
                if (groups.includes('emily')) return '#ff6b6b';
                if (groups.includes('crc')) return '#4ecdc4';
                if (groups.includes('csc')) return '#45b7d1';
                if (groups.includes('bot')) return '#96ceb4';
                if (groups.includes('World Champion')) return '#feca57';
                if (groups.includes('(outsider)')) return '#ddd';
                return '#f8f9fa';
            }};
            
            const getCellClass = (rowPlayer, colPlayer, stats) => {{
                if (rowPlayer.id === colPlayer.id) return 'self-match';
                if (!stats || (stats.rated_stats.total === 0 && stats.unrated_stats.total === 0)) return 'no-matches';
                if (stats.rated_stats.total > 0 || stats.unrated_stats.total > 0) return 'has-matches';
                return '';
            }};
            
            const formatStats = (stats) => {{
                if (!stats || stats.total === 0) return '';
                return `${{stats.wins}}W ${{stats.losses}}L ${{stats.draws}}D`;
            }};
            
            const getStats = (player1, player2) => {{
                return game_stats.find(stat => 
                    (stat.player1 === player1.id && stat.player2 === player2.id) ||
                    (stat.player1 === player2.id && stat.player2 === player1.id)
                );
            }};
            
            return (
                <div className="hive-table">
                    <div className="table-container">
                        <table className="game-table">
                            <thead>
                                <tr>
                                    <th className="header-cell">Player</th>
                                    <th className="header-cell">Total Games</th>
                                    {{sortedPlayers.map(player => (
                                        <th key={{{{player.id}}}} className="header-cell player-header">
                                            <div className="player-name">{{{{player.display_name}}}}</div>
                                            <div className="player-group" style={{{{backgroundColor: getGroupColor(player.groups)}}}}>
                                                {{{{player.groups[0]}}}}
                                            </div>
                                        </th>
                                    ))}}
                                </tr>
                            </thead>
                            <tbody>
                                {{sortedPlayers.map(rowPlayer => {{
                                    const stats = getStats(rowPlayer, rowPlayer);
                                    return (
                                                                            <tr key={{{{rowPlayer.id}}}} className="player-row">
                                        <td className="player-cell">
                                            <div className="player-name">{{{{rowPlayer.display_name}}}}</div>
                                            <div className="player-group" style={{{{backgroundColor: getGroupColor(rowPlayer.groups)}}}}>
                                                {{{{rowPlayer.groups[0]}}}}
                                            </div>
                                        </td>
                                        <td className="total-games">{{{{rowPlayer.total_games}}}}</td>
                                            {{{{sortedPlayers.map(colPlayer => {{
                                                const stats = getStats(rowPlayer, colPlayer);
                                                const cellClass = getCellClass(rowPlayer, colPlayer, stats);
                                                const ratedStats = stats ? stats.rated_stats : null;
                                                const unratedStats = stats ? stats.unrated_stats : null;
                                                
                                                return (
                                                    <td key={{{{`${{{{rowPlayer.id}}}}-${{{{colPlayer.id}}}}`}}}} className={{{{`game-cell ${{{{cellClass}}}}`}}}}>
                                                        {{{{ratedStats && ratedStats.total > 0 && (
                                                            <span dangerouslySetInnerHTML={{{{__html: formatStats(ratedStats)}}}}></span>
                                                        )}}}}
                                                        {{{{unratedStats && unratedStats.total > 0 && (
                                                            <>
                                                                <br />
                                                                <span className="unrated-text" dangerouslySetInnerHTML={{{{__html: formatStats(unratedStats)}}}}></span>
                                                            </>
                                                        )}}}}
                                                    </td>
                                                );
                                            }})}}}}
                                        </tr>
                                    );
                                }})}}
                            </tbody>
                        </table>
                    </div>
                </div>
            );
        }}
        
        // Render the component
        const root = ReactDOM.createRoot(document.getElementById('hive-table-root'));
        root.render(<HiveTable />);
    </script>
    
    <style>
        .hive-table {{
            overflow-x: auto;
        }}
        .table-container {{
            min-width: 800px;
        }}
        .game-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}
        .header-cell {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 8px;
            text-align: center;
            font-weight: bold;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .player-header {{
            min-width: 80px;
        }}
        .player-cell {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 8px;
            text-align: left;
            font-weight: bold;
            position: sticky;
            left: 0;
            z-index: 5;
        }}
        .total-games {{
            background: #e9ecef;
            border: 1px solid #dee2e6;
            padding: 8px;
            text-align: center;
            font-weight: bold;
            position: sticky;
            left: 120px;
            z-index: 5;
        }}
        .game-cell {{
            border: 1px solid #dee2e6;
            padding: 4px;
            text-align: center;
            min-width: 60px;
            height: 40px;
            vertical-align: middle;
        }}
        .player-row:nth-child(even) .game-cell {{
            background-color: #f8f9fa;
        }}
        .self-match {{
            background-color: #e9ecef !important;
            color: #6c757d;
        }}
        .no-matches {{
            background-color: #f8f9fa;
            color: #adb5bd;
        }}
        .has-matches {{
            background-color: #d4edda;
        }}
        .player-name {{
            font-weight: bold;
            margin-bottom: 4px;
        }}
        .player-group {{
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 10px;
            color: white;
            text-align: center;
            white-space: nowrap;
        }}
        .unrated-text {{
            color: #6c757d;
            font-size: 10px;
        }}
    </style>
</body>
</html>"""

    logger.info(f"Successfully generated HTML, result length: {len(html_content)}")
    return html_content
