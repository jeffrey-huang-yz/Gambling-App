from flask import Flask, jsonify, request
import requests
import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId
from pymongo.errors import BulkWriteError

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['Gambling-App']

# Sport mapping for tags
SPORT_MAPPING = {
    'americanfootball_nfl': {'sport': 'football', 'league': 'NFL'},
    'basketball_nba': {'sport': 'basketball', 'league': 'NBA'},
    'baseball_mlb': {'sport': 'baseball', 'league': 'MLB'},
    'icehockey_nhl': {'sport': 'hockey', 'league': 'NHL'},
    'americanfootball_ncaaf': {'sport': 'football', 'league': 'NCAA'},
    'basketball_ncaab': {'sport': 'basketball', 'league': 'NCAA'},
    'soccer_usa_mls': {'sport': 'soccer', 'league': 'MLS'}
}

@app.route('/api/games/upcoming', methods=['GET'])
def get_upcoming_games():
    """
    Get upcoming games using The Odds API (optimized for minimal costs)
    
    Query Parameters:
    - sport: Required - specific sport (e.g., "baseball_mlb", "basketball_nba")
    """
    try:
        print("🚀 Fetching upcoming games from The Odds API...")
        
        # Get required sport parameter
        sport = request.args.get('sport', '').strip().lower()
        
        if not sport:
            return jsonify({
                'status': 'error',
                'message': 'sport parameter is required',
                'available_sports': list(SPORT_MAPPING.keys()),
                'example': '/api/games/upcoming?sport=baseball_mlb'
            }), 400
        
        if sport not in SPORT_MAPPING:
            return jsonify({
                'status': 'error',
                'message': f'Invalid sport: {sport}',
                'available_sports': list(SPORT_MAPPING.keys())
            }), 400
        
        api_key = os.getenv('ODDS_API')
        base_url = "https://api.the-odds-api.com/v4"
        
        print(f"🔍 Fetching {sport} games...")
        
        # Optimized request - single sport, single region, all markets
        params = {
            'apiKey': api_key,
            'regions': 'us',  # Single region to minimize cost
            'markets': 'h2h,spreads,totals',  # 3 markets
            'oddsFormat': 'american'
        }
        
        # Make API request
        url = f"{base_url}/sports/{sport}/odds"
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return jsonify({
                'status': 'error',
                'message': f'The Odds API error: {response.status_code}',
                'sport': sport
            }), 500
        
        games_data = response.json()
        
        # Get credit usage from headers
        credits_used = response.headers.get('x-requests-last', '3')  # Default to 3 (3 markets × 1 region)
        credits_remaining = response.headers.get('x-requests-remaining', 'unknown')
        
        formatted_games = []
        sport_info = SPORT_MAPPING[sport]
        
        # Process each game
        for game in games_data:
            # Organize odds by market type for easy access
            organized_odds = {
                'moneyline': {},
                'spread': {},
                'total': {}
            }
            
            # Process all bookmakers for this game
            for bookmaker in game.get('bookmakers', []):
                book_name = bookmaker['key']
                
                for market in bookmaker.get('markets', []):
                    market_key = market['key']
                    
                    if market_key == 'h2h':  # Moneyline
                        for outcome in market['outcomes']:
                            organized_odds['moneyline'][outcome['name']] = {
                                'odds': outcome['price'],
                                'bookmaker': book_name
                            }
                    
                    elif market_key == 'spreads':
                        for outcome in market['outcomes']:
                            organized_odds['spread'][outcome['name']] = {
                                'odds': outcome['price'],
                                'line': outcome.get('point'),
                                'bookmaker': book_name
                            }
                    
                    elif market_key == 'totals':
                        for outcome in market['outcomes']:
                            key = 'over' if 'over' in outcome['name'].lower() else 'under'
                            organized_odds['total'][key] = {
                                'odds': outcome['price'],
                                'line': outcome.get('point'),
                                'bookmaker': book_name
                            }
            
            # Create game response
            game_response = {
                'game_id': game['id'],
                'sport': sport_info['sport'],
                'league': sport_info['league'],
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'game_time': game['commence_time'],
                'odds': organized_odds,
                'total_bookmakers': len(game.get('bookmakers', []))
            }
            
            formatted_games.append(game_response)
        
        print(f" Retrieved {len(formatted_games)} upcoming games")
        
        return jsonify({
            'status': 'success',
            'data': {
                'games': formatted_games,
                'total_games': len(formatted_games),
                'sport': sport,
                'league': sport_info['league'],
                'fetch_timestamp': datetime.now().isoformat(),
                'source': 'The Odds API'
            },
            'api_usage': {
                'credits_used': credits_used,
                'credits_remaining': credits_remaining,
                'cost_breakdown': '3 markets × 1 region = 3 credits'
            }
        }), 200
        
    except requests.exceptions.Timeout:
        return jsonify({
            'status': 'error',
            'message': 'Request to The Odds API timed out'
        }), 500
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'status': 'error',
            'message': 'Failed to connect to The Odds API',
            'error': str(e)
        }), 500
        
    except Exception as e:
        print(f" Error in get_upcoming_games: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e)
        }), 500

@app.route('/api/games/completed', methods=['GET'])
def get_completed_games():
    """
    Get completed games with scores using The Odds API (optimized for minimal costs)
    
    Query Parameters:
    - sport: Required - specific sport (e.g., "baseball_mlb", "basketball_nba")
    - days_back: Optional - days back to search (1-3, default: 1)
    """
    try:
        print(" Fetching completed games from The Odds API...")
        
        # Get required sport parameter
        sport = request.args.get('sport', '').strip().lower()
        days_back = int(request.args.get('days_back', 1))
        
        if not sport:
            return jsonify({
                'status': 'error',
                'message': 'sport parameter is required',
                'available_sports': list(SPORT_MAPPING.keys()),
                'example': '/api/games/completed?sport=baseball_mlb&days_back=1'
            }), 400
        
        if sport not in SPORT_MAPPING:
            return jsonify({
                'status': 'error',
                'message': f'Invalid sport: {sport}',
                'available_sports': list(SPORT_MAPPING.keys())
            }), 400
        
        if days_back < 1 or days_back > 3:
            return jsonify({
                'status': 'error',
                'message': 'days_back must be between 1 and 3',
                'provided': days_back
            }), 400
        
        api_key = os.getenv('ODDS_API')
        base_url = "https://api.the-odds-api.com/v4"
        
        print(f"🔍 Fetching completed {sport} games from last {days_back} days...")
        
        # Optimized scores request - single sport, costs 2 credits
        params = {
            'apiKey': api_key,
            'daysFrom': days_back,
            'dateFormat': 'iso'
        }
        
        url = f"{base_url}/sports/{sport}/scores"
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return jsonify({
                'status': 'error',
                'message': f'The Odds API error: {response.status_code}',
                'sport': sport
            }), 500
        
        games_data = response.json()
        
        # Get credit usage from headers
        credits_used = response.headers.get('x-requests-last', '2')  # Should be 2 for scores with daysFrom
        credits_remaining = response.headers.get('x-requests-remaining', 'unknown')
        
        completed_games = []
        sport_info = SPORT_MAPPING[sport]
        
        # Process only completed games
        for game in games_data:
            if not game.get('completed', False):
                continue  # Skip non-completed games
            
            # Extract scores
            scores = {}
            home_score = None
            away_score = None
            
            for score in game.get('scores', []):
                team_name = score['name']
                team_score = int(score['score'])
                scores[team_name] = team_score
                
                if team_name == game['home_team']:
                    home_score = team_score
                elif team_name == game['away_team']:
                    away_score = team_score
            
            # Calculate betting outcomes
            if home_score is not None and away_score is not None:
                total_score = home_score + away_score
                home_won = home_score > away_score
                
                # Create settlement-ready response
                completed_game = {
                    'game_id': game['id'],
                    'sport': sport_info['sport'],
                    'league': sport_info['league'],
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'game_time': game['commence_time'],
                    'completed': True,
                    'scores': {
                        'home_score': home_score,
                        'away_score': away_score,
                        'total_score': total_score
                    },
                    'settlement_data': {
                        'needs_settlement': True,
                        'winner': 'home' if home_won else 'away',
                        'betting_outcomes': {
                            'moneyline': {
                                'home_result': 'win' if home_won else 'loss',
                                'away_result': 'loss' if home_won else 'win'
                            },
                            'total_score': total_score
                        }
                    },
                    'last_update': game.get('last_update')
                }
                
                completed_games.append(completed_game)
        
        print(f"✅ Found {len(completed_games)} completed games")
        
        return jsonify({
            'status': 'success',
            'data': {
                'completed_games': completed_games,
                'total_games': len(completed_games),
                'sport': sport,
                'league': sport_info['league'],
                'days_searched': days_back,
                'fetch_timestamp': datetime.now().isoformat(),
                'source': 'The Odds API'
            },
            'api_usage': {
                'credits_used': credits_used,
                'credits_remaining': credits_remaining,
                'cost_breakdown': f'1 sport scores with daysFrom = 2 credits'
            }
        }), 200
        
    except requests.exceptions.Timeout:
        return jsonify({
            'status': 'error',
            'message': 'Request to The Odds API timed out'
        }), 500
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'status': 'error',
            'message': 'Failed to connect to The Odds API',
            'error': str(e)
        }), 500
        
    except Exception as e:
        print(f" Error in get_completed_games: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'message': 'Gambling API using The Odds API (optimized)',
        'api_provider': 'The Odds API',
        'available_sports': list(SPORT_MAPPING.keys())
    })

def calculate_payout(wager, odds):
    """Calculate payout from wager and odds"""
    if odds < 0:
        return wager + (wager * 100 / abs(odds))
    else:
        return wager + (wager * odds / 100)

def determine_bet_outcome(leg, winner, final_score):
    """Determine if a bet leg won or lost"""
    selection = leg.get('selection', '').strip()
    
    # Simple moneyline matching
    if selection.lower() == winner.lower():
        return True
    else:
        return False
@app.route('/api/bets/settle', methods=['POST'])
def settle_bets():
    """
    Settle bets for a completed game
    
    Body:
    {
        "game_id": "32569687",
        "winner": "Lakers",
        "final_score": {"home": 108, "away": 95}
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        game_id = data.get('game_id', '').strip()
        winner = data.get('winner', '').strip()
        final_score = data.get('final_score', {})
        
        if not game_id or not winner:
            return jsonify({
                'status': 'error',
                'message': 'game_id and winner are required'
            }), 400
        
        print(f" Settling bets for game {game_id}, winner: {winner}")
        print(f" Game ID type: {type(game_id)}, value: '{game_id}'")
        
        # Debug: Check all bets first
        all_bets = list(db.Bets.find({}))
        print(f" Total bets in collection: {len(all_bets)}")
        
        for i, bet in enumerate(all_bets):
            print(f" Bet {i+1}: game_id='{bet['leg']['game_id']}' (type: {type(bet['leg']['game_id'])}), status='{bet['status']}'")
        
        # Find all active bets for this game with multiple query attempts
        print(f" Attempting query 1: exact match")
        active_bets = list(db.Bets.find({
            "leg.game_id": game_id,
            "status": "active"
        }))
        print(f" Query 1 results: {len(active_bets)} bets found")
        
        # If no results, try string conversion
        if len(active_bets) == 0:
            print(f" Attempting query 2: with string conversion")
            active_bets = list(db.Bets.find({
                "leg.game_id": str(game_id),
                "status": "active"
            }))
            print(f" Query 2 results: {len(active_bets)} bets found")
        
        # If still no results, try just game_id
        if len(active_bets) == 0:
            print(f" Attempting query 3: game_id only")
            game_id_bets = list(db.Bets.find({"leg.game_id": game_id}))
            print(f" Query 3 results: {len(game_id_bets)} bets with matching game_id")
            
            active_bets = [bet for bet in game_id_bets if bet.get('status') == 'active']
            print(f" Active bets from manual filter: {len(active_bets)}")
        
        if not active_bets:
            return jsonify({
                'status': 'success',
                'message': 'No active bets found for this game',
                'settlement_summary': {
                    'game_id': game_id,
                    'bets_settled': 0,
                    'users_affected': 0
                },
                'debug_info': {
                    'total_bets_in_db': len(all_bets),
                    'searched_game_id': game_id,
                    'searched_game_id_type': str(type(game_id))
                }
            }), 200
        
        print(f" Found {len(active_bets)} active bets to settle")
        
        # Process settlements
        settlement_results = []
        user_updates = {}
        
        for bet in active_bets:
            print(f" Processing bet ID: {bet['_id']}")
            
            leg = bet['leg']
            user_id = bet['user_id']
            wagered_amount = bet['wagered_amount']
            odds = leg['odds']
            
            print(f" User: {user_id}, Wager: ${wagered_amount}, Odds: {odds}")
            print(f" Selection: '{leg.get('selection')}', Winner: '{winner}'")
            
            # Determine outcome
            won = determine_bet_outcome(leg, winner, final_score)
            print(f"🎲 Bet won: {won}")
            
            # Calculate profit change
            if won:
                payout = calculate_payout(wagered_amount, odds)
                profit_change = payout - wagered_amount
                bet_outcome = "win"
            else:
                payout = 0
                profit_change = -wagered_amount
                bet_outcome = "loss"
            
            print(f" Outcome: {bet_outcome}, Payout: ${payout}, Profit: ${profit_change}")
            
            # Update bet document
            print(f" Updating bet {bet['_id']} to settled status")
            update_result = db.Bets.update_one(
                {"_id": bet["_id"]},
                {
                    "$set": {
                        "status": "settled",
                        "outcome": bet_outcome,
                        "payout": payout,
                        "profit": profit_change,
                        "settled_at": datetime.now().isoformat(),
                        "leg.status": "settled",
                        "leg.outcome": won
                    }
                }
            )
            print(f" Bet update result: matched={update_result.matched_count}, modified={update_result.modified_count}")
            
            # Verify bet was updated
            updated_bet = db.Bets.find_one({"_id": bet["_id"]})
            print(f" Bet after update: status='{updated_bet.get('status')}', leg.status='{updated_bet['leg'].get('status')}'")
            
            # Track user updates
            if user_id not in user_updates:
                user_updates[user_id] = {
                    'profit_change': 0,
                    'losses_change': 0,
                    'bets_count': 0,
                    'wins': 0,
                    'losses': 0
                }
            
            user_updates[user_id]['profit_change'] += profit_change
            user_updates[user_id]['bets_count'] += 1
            
            if won:
                user_updates[user_id]['wins'] += 1
            else:
                user_updates[user_id]['losses'] += 1
                user_updates[user_id]['losses_change'] += wagered_amount
            
            settlement_results.append({
                'bet_id': str(bet['_id']),
                'user_id': user_id,
                'bet_outcome': bet_outcome,
                'wager': wagered_amount,
                'payout': payout,
                'profit_change': profit_change
            })
        
        # Update user stats
        users_affected = []
        for user_id, updates in user_updates.items():
            print(f" Looking for user with username: '{user_id}'")
            
            # Check if user exists
            existing_user = db.Users.find_one({"username": user_id})
            if not existing_user:
                print(f" User '{user_id}' not found in Users collection")
                # Try to find all users to debug
                all_users = list(db.Users.find({}))
                print(f"🔍 Available users: {[u.get('username') for u in all_users]}")
                continue
            
            print(f" Found user: {existing_user['username']}")
            print(f" Current user stats: profit={existing_user.get('profit')}, losses={existing_user.get('losses')}")
            print(f" Applying changes: profit_change={updates['profit_change']}, losses_change={updates['losses_change']}")
            
            # Update user document
            user_result = db.Users.update_one(
                {"username": user_id},
                {
                    "$inc": {
                        "profit": updates['profit_change'],
                        "losses": updates['losses_change']
                    }
                }
            )
            print(f"📈 User update result: matched={user_result.matched_count}, modified={user_result.modified_count}")
            
            # Get updated user info
            updated_user = db.Users.find_one({"username": user_id})
            print(f"📊 Updated user stats: profit={updated_user.get('profit')}, losses={updated_user.get('losses')}")
            
            users_affected.append({
                'user_id': user_id,
                'bets_settled': updates['bets_count'],
                'wins': updates['wins'],
                'losses': updates['losses'],
                'profit_change': updates['profit_change'],
                'old_profit': existing_user.get('profit', 0),
                'new_profit': updated_user.get('profit', 0),
                'new_balance': updated_user.get('balance', 0)
            })
        
        print(f" Successfully settled {len(active_bets)} bets for {len(user_updates)} users")
        
        return jsonify({
            'status': 'success',
            'settlement_summary': {
                'game_id': game_id,
                'winner': winner,
                'final_score': final_score,
                'bets_settled': len(active_bets),
                'users_affected': len(user_updates),
                'settled_at': datetime.now().isoformat()
            },
            'user_updates': users_affected,
            'settlement_details': settlement_results
        }), 200
        
    except Exception as e:
        print(f" Error in settle_bets: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': 'Failed to settle bets',
            'error': str(e)
        }), 500
    
#user login routes

if __name__ == '__main__':
    print("🎰 Starting Gambling App API with optimized The Odds API usage...")
    app.run(debug=True, host='0.0.0.0', port=5000)