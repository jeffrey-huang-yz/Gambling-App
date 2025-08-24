from turtle import title
from flask import Flask, jsonify, request, make_response, g
import requests
import os
from datetime import datetime, timedelta, timezone
import jwt
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId
from pymongo.errors import BulkWriteError
from werkzeug.security import generate_password_hash, check_password_hash
import time, math 
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['Gambling-App']

JWT_SECRET       = os.getenv("JWT_SECRET")
JWT_ALG          = "HS256"
JWT_ISSUER       = os.getenv("JWT_ISSUER")
JWT_AUDIENCE     = os.getenv("JWT_AUDIENCE")
JWT_EXP_SECONDS  = int(os.getenv("JWT_EXP_SECONDS")) 
COOKIE_SECURE    = os.getenv("COOKIE_SECURE", "0") == "1"     
COOKIE_NAME      = "auth_token"


# Initial daily credit for users
DAILY_CREDIT = 1000

tiers = [
            {"name": "king",  "threshold": 95},
            {"name": "diamond",  "threshold": 95},  
            {"name": "platinum", "threshold": 90},  
            {"name": "gold",     "threshold": 80},  
            {"name": "silver",   "threshold": 50},  
            {"name": "bronze",   "threshold": 0},  
        ]
        
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

def generate_jwt(claims: dict) -> str:
    # Encode signed JWT, must include username in claims
    now = int(time.time())
    payload = {
        "iss": JWT_ISSUER,      # Issuer of JWT
        "aud": JWT_AUDIENCE,    # Audience of JWT   
        "iat": now,             # Issued at
        "nbf": now,             # Not before
        "exp": now + JWT_EXP_SECONDS,  # Expiration time
        **claims,               # Put the username in type shi 
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def verify_jwt(token: str):
    # Decode and verify JWT 
    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALG],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["exp", "iat", "iss", "aud"]},
            leeway=10, # incase of clock skew 
        )
    except jwt.PyJWTError:
        return None


def get_token_from_request():
    # Get token from cookies
    return request.cookies.get(COOKIE_NAME)

def auth_required(fn):
    # Decorator to protect routes by verifying JWT 
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = get_token_from_request()
        claims = verify_jwt(token) if token else None
        if not claims:
            return jsonify({"status": "error", "message": "unauthorized"}), 401
        
        # ensure user still exists
        uname = claims.get("sub")
        if not uname or not db.Users.find_one({"username": uname}):
            return jsonify({"status": "error", "message": "unauthorized"}), 401
        from flask import g
        g.user_claims = claims
        return fn(*args, **kwargs)
    return wrapper

def set_auth_cookie(resp, token: str):
    resp.set_cookie(
        COOKIE_NAME,
        token,
        max_age=JWT_EXP_SECONDS,
        httponly=True,           
        samesite="Lax",         
        secure=COOKIE_SECURE,    # True in prod
        path="/",
    )
    return resp

def clear_auth_cookie(resp):
    resp.set_cookie(COOKIE_NAME, "", max_age=0, httponly=True, samesite="Lax", secure=COOKIE_SECURE, path="/")
    return resp

def to_iso(v):
    from datetime import datetime as dt
    return v.isoformat() if isinstance(v, dt) else v

def parse_iso_z(s: str) -> datetime:
    # The Odds API returns ISO with trailing 'Z'. Make it tz-aware.
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    return datetime.fromisoformat(s)

def fetch_events_for_sport(sport_key: str, event_ids: list[str]) -> dict:
    # Calls /v4/sports/{sport}/events?apiKey=...&dateFormat=iso&eventIds=...
    # Returns dict[id] -> event_json. Raises on HTTP error.
    base_url = "https://api.the-odds-api.com/v4"
    params = {
        'apiKey': os.getenv('ODDS_API'),
        'dateFormat': 'iso',
        'eventIds': ','.join(map(str, event_ids))
    }
    url = f"{base_url}/sports/{sport_key}/events"
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Events API error {resp.status_code} for sport={sport_key}")
    events = resp.json() or []
    return {e.get('id'): e for e in events}


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
            
            # Compute and update user's rank after bet settles
            try:
                total_users = max(db.Users.count_documents({"profit": {"$exists": True}}), 1)
                updated_profit = float(updated_user.get('profit', 0) or 0)
                user_rank = db.Users.count_documents({"profit": {"$gt": updated_profit}}) + 1

                # Percentile without div by 0
                percentile_from_top = 100.0 * (1 - (user_rank - 1) / total_users)

                # Determine tier based on percentile
                rank = tiers[-1]["name"] if tiers else "bronze"
                for t in tiers:
                    if percentile_from_top >= t.get("threshold", 0):
                        rank = t.get("name", rank)
                        break

                # Update Rank
                db.Users.update_one(
                    {"username": user_id},
                    {"$set": {
                        "rank": user_rank,
                    }}
                )
            except Exception as rank_e:
                print(f"⚠️ Failed to compute/update rank for user {user_id}: {rank_e}")
            
            users_affected.append({
                'user_id': user_id,
                'bets_settled': updates['bets_count'],
                'wins': updates['wins'],
                'losses': updates['losses'],
                'profit_change': updates['profit_change'],
                'old_profit': existing_user.get('profit', 0),
                'new_profit': updated_user.get('profit', 0),
                'new_balance': updated_user.get('balance', 0),
                'rank': db.Users.find_one({"username": user_id}).get('rank') if db else None,
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
    
@app.route('/api/users/<user_id>/bets', methods=['GET'])
@auth_required
def get_user_bets(user_id):
    try:
        # Verify user exists
        user = db.Users.find_one({"username": user_id})
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        # Build query and validate active parameter if provided
        query = {"user_id": user_id}
        active = request.args.get('active')
        if active is not None:
            val = active.strip().lower()
            if val == "true":
                query["status"] = "active"
            elif val == "false":
                query["status"] = "settled"
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'active must be true or false'
                }), 400
        
        print(f" Query parameters: {query}")
        
        # Retrieve bets in the same way we access them in settle_bets
        bets = list(db.Bets.find(query).sort([("created_at", -1)]))
        
        # converte date object to ISO format
        def to_iso(v):
            from datetime import datetime as dt
            return v.isoformat() if isinstance(v, dt) else v
    
        data = []
        for bet in bets:
            # Use 'legs' field if exists, otherwise fallback to legacy 'leg'
            legs = bet.get('legs', [])
            data.append({
            'bet_id': str(bet.get('_id')),
            'user_id': bet.get('user_id'),
            'title': bet.get('title', ''),
            'status': bet.get('status'),
            'wagered_amount': bet.get('wagered_amount'),
            'outcome': bet.get('outcome'),
            'payout': bet.get('payout'),
            'profit': bet.get('profit'),
            'created_at': to_iso(bet.get('created_at')),
            'settled_at': to_iso(bet.get('settled_at')),
            'legs': [
                {
                'game_id': leg.get('game_id'),
                'selection': leg.get('selection'),
                'odds': leg.get('odds'),
                'status': leg.get('status')
                } for leg in legs
            ]
            })

        return jsonify({
            'status': 'success',
            'data': data,
            'total_bets': len(data)
        }), 200

    except Exception as e:
        print(f"Error in get_user_bets: {e}")
        return jsonify({    
            'status': 'error',
            'message': 'Failed to retrieve user bets',
            'error': str(e)
        }), 500
    
@app.route('/api/users/<user_id>/history', methods=['GET'])
@auth_required
def get_user_history(user_id):
    try:
        start = request.args.get("start")
        end = request.args.get("end")

        if not (start and end):
            return jsonify({
                'status': 'error',
                'message': 'start and end params required'
            }), 400
        
        try:
            start_date = datetime.fromisoformat(start)

            # Add 1 day to end date to include the entire end day
            end_date = datetime.fromisoformat(end) + timedelta(days=1)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': 'start and end must be ISO',
                'error': str(e)
            }), 400
        
        # Verify user exists
        user = db.Users.find_one({"username": user_id})
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        # Date filter
        date_filter = {"$gte": start_date, "$lt": end_date}
        query = {
            "user_id": user_id,
            "$or": [
                {"created_at": date_filter},
                {"settled_at": date_filter},
                {"date": date_filter}
            ]
        }
        
        # Retrieve bets sort by created_at then settled_at
        bets = list(db.Bets.find(query).sort([("created_at", -1), ("settled_at", -1)]))
        
        def to_iso(v):
            from datetime import datetime as dt
            return v.isoformat() if isinstance(v, dt) else v
        
        data = []
        for bet in bets:
            legs = bet.get('leg', [])
            data.append({
                'bet_id': str(bet.get('_id')),
                'user_id': bet.get('user_id'),
                'bet_type': bet.get('bet_type'),
                'leg': [
                    {
                        'game_id': leg.get('game_id'),
                        'selection': leg.get('selection'),
                        'odds': leg.get('odds'),
                        'status': leg.get('status')
                    } for leg in legs
                ],
                'wagered_amount': bet.get('wagered_amount'),
                'status': bet.get('status'),
                'outcome': bet.get('outcome'),
                'payout': bet.get('payout'),
                'profit': bet.get('profit'),
                'created_at': to_iso(bet.get('created_at')),
                'settled_at': to_iso(bet.get('settled_at')),

            })
        
        return jsonify({
            'status': 'success',
            'bets': data,
            'total_bets': len(data),
            'start': start,
            'end': end
        }), 200
    except Exception as e:
        print(f"Error in get_user_history: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve user history',
            'error': str(e)
        }), 500
    
@app.route('/api/users/<user_id>/balance', methods=['GET'])
@auth_required
def get_user_balance(user_id):
    try:
        # Verify user exists by username to match other routes
        user = db.Users.find_one({"username": user_id})
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404

        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'balance': user.get('balance', 0)
        }), 200
    except Exception as e:
        print(f"Error in get_user_balance: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve user balance',
            'error': str(e)
        }), 500

@app.route('/api/users/<user_id>/rank', methods=['GET'])
@auth_required
def get_user_rank(user_id):
    try:
        # Verify user exists by username
        user = db.Users.find_one({"username": user_id})
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404

        # Get user's current profit (default to 0 if not set)
        user_profit = user.get('profit', 0)

        # Build leaderboard: all users with a profit field, sorted by descending profit
        leaderboard = list(db.Users.find({"profit": {"$exists": True}}).sort("profit", -1))
        
        # Determine user's rank efficiently by counting how many users have a higher profit
        user_profit = user.get('profit', 0)
        user_rank = db.Users.count_documents({"profit": {"$gt": user_profit}}) + 1

        if user_rank is None:
            return jsonify({
                'status': 'error',
                'message': 'User not found in leaderboard'
            }), 404

        # Tier-based ranking by profit percentile and profit needed for next tier

        total_users = max(len(leaderboard), 1)  
        percentile_from_top = 100.0 * (1 - (user_rank - 1) / total_users)

        # Determine current tier
        current_tier_idx = next((i for i, t in enumerate(tiers) if percentile_from_top >= t["threshold"]), len(tiers) - 1)

        # Profit needed to reach next higher tier
        if current_tier_idx == 0 or total_users == 0:
            profit_to_next_rank = 0
            spots_to_next_rank = 0
        else:
            next_tier = tiers[current_tier_idx - 1]
            users_in_next_tier = max(1, math.ceil(((100 - next_tier["threshold"]) / 100.0) * total_users))
            cutoff_index = min(users_in_next_tier, total_users) - 1  # zero-based
            cutoff_user = leaderboard[cutoff_index] if leaderboard else None
            cutoff_profit = cutoff_user.get("profit", 0) if cutoff_user else 0
            profit_to_next_rank = max(cutoff_profit - user_profit, 0)


            current_index = user_rank - 1  
            spots_to_next_rank = max(current_index - cutoff_index, 0)

    

        # Spots to next rank is the count of users ahead of the current user.
        spots_to_next_rank = user_rank - 1

        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'rank': user_rank,
            'profit_to_next_rank': profit_to_next_rank,
            'spots_to_next_rank': spots_to_next_rank
        }), 200
    except Exception as e:
        print(f"Error in get_user_rank: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve user rank',
            'error': str(e)
        }), 500

# get total profit of each day within range 
@app.route('/api/users/<user_id>/profit_history', methods=['GET'])
@auth_required
def get_user_daily_profits(user_id):

    try:
        # Verify user exists by username
        user = db.Users.find_one({"username": user_id})
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        start = request.args.get('start')
        end = request.args.get('end')

        if start or end:
            # If one is provided, require both to avoid ambiguity
            if not (start and end):
                return jsonify({'status': 'error', 'message': 'Provide both start and end or neither'}), 400
            try:
                start_date = datetime.fromisoformat(start)
                # include whole end day
                end_date = datetime.fromisoformat(end) + timedelta(days=1)
            except Exception as e:
                return jsonify({'status': 'error', 'message': 'start and end must be ISO', 'error': str(e)}), 400
            days_window = None
        else:
            # Use days window if start/end omitted
            days_param = request.args.get('days', '30').strip()
            try:
                days_window = int(days_param)
                if days_window <= 0:
                    raise ValueError('days must be positive')
            except Exception:
                return jsonify({'status': 'error', 'message': 'days must be a positive integer'}), 400
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_window)
            # Make end exclusive by adding 1 day when we present back to client later
            end = end_date.date().isoformat()
            start = start_date.date().isoformat()

        # Build pipeline for aggregation
        pipeline = [
            {'$match': {
                'user_id': user_id,
                'status': 'settled'
            }},

            # add ts field that converts settled_at/created_at to date objects
            {'$addFields': {
                '_ts': {
                    '$ifNull': [
                        {'$convert': {'input': '$settled_at', 'to': 'date', 'onError': None, 'onNull': None}},
                        {'$convert': {'input': '$created_at', 'to': 'date', 'onError': None, 'onNull': None}}
                    ]
                }
            }},
            # match for bets created after start_date and before end_date
            {'$match': {'_ts': {'$gte': start_date, '$lt': end_date}}},

            # group by day and sum profits from each bet 
            {'$group': {
                '_id': {
                    '$dateTrunc': { 'date': "$_ts", 'unit': "day", 'timezone': "America/Toronto" }
                },
                'profit': {'$sum': {'$ifNull': ['$profit', 0]}},
                'wagered_amount': {'$sum': {'$ifNull': ['$wagered_amount', 0]}}
            }},
            {'$sort': {'_id': 1}}
        ]

        results = list(db.Bets.aggregate(pipeline))
        daily_profits = [ { 'date': r.get('_id'), 'wagered_amount': r.get('wagered_amount', 0), 'profit': r.get('profit', 0) } for r in results ]

        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'start': start,
            'end': end,
            'days': days_window,
            'daily_profits': daily_profits,
            'points': len(daily_profits)
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to retrieve daily profits', 'error': str(e)}), 500

#user login routes

@app.route('/api/users', methods=['POST'])
def register_user():
    try:
        data = request.get_json(force=True) or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''

        if not username:
            return jsonify({'status': 'error', 'message': 'username is required'}), 400
        if len(password) < 6:
            return jsonify({'status': 'error', 'message': 'password must be at least 6 characters'}), 400

        if db.Users.find_one({'username': username}):
            return jsonify({'status': 'error', 'message': 'Username already exists'}), 409

        pwd_hash = generate_password_hash(password)

        user_doc = {
            'username': username,
            'password': pwd_hash,
            'balance': DAILY_CREDIT,
            'rank': 'Bronze',
            'profit': 0,
            'wagered_amount': 0,
            'losses': 0,
            'history_visible': True,
            'created_at': datetime.now()
        }
        db.Users.insert_one(user_doc)

        # Auto-login after register
        token = generate_jwt({'sub': username})
        resp = make_response(jsonify({
            'status': 'success',
            'user': {
                'user_id': username,
                'balance': user_doc['balance'],
                'rank': user_doc['rank']
            },
            'token': token
        }), 201)
        return set_auth_cookie(resp, token)
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to register user', 'error': str(e)}), 500

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    # if g.user_claims.get('sub') != user_id:
    #     return jsonify({'status': 'error', 'message': 'forbidden'}), 403

    user = db.Users.find_one({'username': user_id}, {'password': 0})
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    data = {
        'user_id': user.get('username'),
        'balance': user.get('balance', 0),
        'profit': user.get('profit', 0),
        'losses': user.get('losses', 0),
        'rank': user.get('rank', 'Bronze'),
        'wagered_amount': user.get('wagered_amount', 0),
        'history_visible': user.get('history_visible', True),
        'created_at': to_iso(user.get('created_at')),
        'password_updated_at': to_iso(user.get('password_updated_at')),
    }
    return jsonify({'status': 'success', 'data': data}), 200

@app.route('/api/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json(force=True) or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''

        if not username or not password:
            return jsonify({'status': 'error', 'message': 'username and password are required'}), 400

        user = db.Users.find_one({'username': username})
        if not user or not user.get('password'):
            return jsonify({'status': 'error', 'message': 'invalid credentials'}), 401

        if not check_password_hash(user['password'], password):
            return jsonify({'status': 'error', 'message': 'invalid credentials'}), 401

        token = generate_jwt({'sub': user['username']})
        resp = make_response(jsonify({
            'status': 'success',
            'token': token,
            'user': {
                'user_id': user['username'],
                'balance': user.get('balance', 0),      
                'rank': user.get('rank', 'Bronze'),
            }
        }), 200)
        return set_auth_cookie(resp, token)
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to login', 'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json(force=True) or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''

        if not username or not password:
            return jsonify({'status': 'error', 'message': 'username and password are required'}), 400

        user = db.Users.find_one({'username': username})
        if not user or not user.get('password'):
            return jsonify({'status': 'error', 'message': 'invalid credentials'}), 401

        if not check_password_hash(user['password'], password):
            return jsonify({'status': 'error', 'message': 'invalid credentials'}), 401

        token = generate_jwt({'sub': user['username']})
        resp = make_response(jsonify({
            'status': 'success',
            'token': token,
            'user': {
                'user_id': user['username'],
                'balance': user.get('balance', 0),
                'rank': user.get('rank', 'Bronze'),
            }
        }), 200)
        return set_auth_cookie(resp, token)
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to login', 'error': str(e)}), 500
    
@app.route('/api/logout', methods=['POST'])
def logout_user():
    resp = make_response(jsonify({'status': 'success', 'message': 'logged out'}), 200)
    return clear_auth_cookie(resp)

@app.route('/api/users/<user_id>/password', methods=['PUT'])
@auth_required
def change_password(user_id):
    # Caller must be the same user
    if g.user_claims.get('sub') != user_id:
        return jsonify({'status': 'error', 'message': 'forbidden'}), 403

    # Get current pw and new pw
    data = request.get_json(force=True) or {}
    current_password = str(data.get('current_password') or '')
    new_password     = str(data.get('new_password') or '')

    if len(new_password) < 6:
        return jsonify({'status': 'error', 'message': 'new_password must be at least 6 characters'}), 400
    
    user = db.Users.find_one({'username': user_id}, {'password': 1})

    if not user or not user.get('password'):
        return jsonify({'status': 'error', 'message': 'user not found'}), 404

    if not check_password_hash(user['password'], current_password):
        return jsonify({'status': 'error', 'message': 'invalid current password'}), 401

    # Disallow reusing the same password
    if check_password_hash(user['password'], new_password):
        return jsonify({'status': 'error', 'message': 'new password must differ from current password'}), 400

    # Update user's pw 
    db.Users.update_one(
        {'username': user_id},
        {'$set': {'password': generate_password_hash(new_password)}}
    )

    # Rotate JWT + refresh cookie
    new_token = generate_jwt({'sub': user_id})
    resp = make_response(jsonify({'status': 'success', 'message': 'password updated', 'token': new_token}), 200)
    return set_auth_cookie(resp, new_token)

@app.route('/api/bets', methods=['POST'])
@auth_required
def create_bet():
    try:
        data = request.get_json(force=True) or {}

        # Validate required fields
        user_id = data.get('user_id')
        wager_raw = data.get('wager') or data.get('wagered_amount')
        legs = data.get('legs')

        if not user_id:
            return jsonify({'status': 'error', 'message': 'user_id is required'}), 400
        if wager_raw is None:
            return jsonify({'status': 'error', 'message': 'wager is required'}), 400
        try:
            wager = float(wager_raw)
            if wager <= 0:
                raise ValueError('wager must be > 0')
        except Exception:
            return jsonify({'status': 'error', 'message': 'wager must be a positive number'}), 400
        if not isinstance(legs, list) or len(legs) == 0:
            return jsonify({'status': 'error', 'message': 'legs must be a non-empty array'}), 400

        # Verify user exists by username and has sufficient balance
        user = db.Users.find_one({'username': user_id})
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        balance = float(user.get('balance', 0))
        if balance < wager:
            return jsonify({'status': 'error', 'message': 'Insufficient balance'}), 409

        # Determine bet type from leg count
        bet_type = 'parlay' if len(legs) > 1 else 'single'

    
        bet = {
            'user_id': user_id,
            'bet_type': bet_type,
            'wagered_amount': wager,
            'legs': legs,            
            'status': 'active',
            'outcome': None,
            'payout': 0,
            'profit': 0,
            'created_at': datetime.now(),
            'settled_at': None,
        }

        # Maintain legacy 'leg' field for compatibility
        bet['leg'] = legs[0] if len(legs) == 1 else legs

        res = db.Bets.insert_one(bet)

        # Decrement user balance
        db.Users.update_one({'username': user_id}, {'$inc': {'balance': -wager}})
        new_user = db.Users.find_one({'username': user_id})
        new_balance = float(new_user.get('balance', 0)) if new_user else balance - wager

        return jsonify({
            'status': 'success',
            'bet_id': str(res.inserted_id),
            'new_balance': new_balance
        }), 201
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to create bet', 'error': str(e)}), 500

@app.route('/api/bets/<bet_id>/cancel', methods=['PATCH'])
@auth_required
def cancel_bet(bet_id):
    try:
        # Validate ObjectId
        try:
            _id = ObjectId(bet_id)
        except Exception:
            return jsonify({'status': 'error', 'message': 'Invalid bet_id'}), 400

        bet = db.Bets.find_one({'_id': _id})
        if not bet:
            return jsonify({'status': 'error', 'message': 'Bet not found'}), 404

        # Owner check
        if bet.get('user_id') != g.user_claims.get('sub'):
            return jsonify({'status': 'error', 'message': 'forbidden'}), 403

        if bet.get('status') != 'active':
            return jsonify({'status': 'error', 'message': 'Only active bets can be cancelled'}), 409

        legs = bet.get('legs')
        if not isinstance(legs, list) or not legs:
            return jsonify({'status': 'error', 'message': 'Bet has no legs; cannot verify pre-game'}), 409

        # Group legs by sport key; ensure game_id + sport exist
        legs_by_sport = {}
        for idx, leg in enumerate(legs):
            gid = leg.get('game_id')
            sport_key = (leg.get('sport') or '').strip().lower()
            if not gid or not sport_key:
                return jsonify({
                    'status': 'error',
                    'message': f'leg {idx} missing game_id or sport'
                }), 409
            legs_by_sport.setdefault(sport_key, []).append(gid)

        # Query The Odds API events endpoint per sport
        now = datetime.now(timezone.utc)
        for sport_key, ids in legs_by_sport.items():
            try:
                events_map = fetch_events_for_sport(sport_key, ids)
            except Exception as api_err:
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to fetch events for sport={sport_key}',
                    'error': str(api_err)
                }), 502  # upstream failure

            # If any requested id is not in the response -> return false immediately
            for gid in ids:
                if str(gid) not in events_map:
                    return jsonify({
                        'status': 'error',
                        'allowed': False,
                        'message': f'Event not found for game_id={gid} (sport={sport_key})'
                    }), 409

            # Check commence_time for each event; deny if any started
            for gid in ids:
                evt = events_map[str(gid)]
                ct_raw = evt.get('commence_time')  
                try:
                    ct = parse_iso_z(ct_raw).astimezone(timezone.utc)
                except Exception:
                    return jsonify({
                        'status': 'error',
                        'allowed': False,
                        'message': f'Invalid commence_time for game_id={gid}'
                    }), 409

                if now >= ct:
                    return jsonify({
                        'status': 'error',
                        'allowed': False,
                        'message': f'Cannot cancel: game {gid} (sport={sport_key}) already started',
                        'game_id': gid,
                        'commence_time': ct.isoformat()
                    }), 409

        # If we get here: all legs exist and none have started -> cancel + refund
        wager = float(bet.get('wagered_amount', 0) or 0.0)
        user_id = bet.get('user_id')

        upd = db.Bets.update_one(
            {'_id': _id, 'status': 'active'},
            {'$set': {
                'status': 'cancelled',
                'outcome': 'cancelled',
                'payout': 0,
                'profit': 0,
                'settled_at': datetime.now(timezone.utc)
            }}
        )
        if upd.modified_count != 1:
            return jsonify({'status': 'error', 'message': 'Cancellation failed'}), 500

        db.Users.update_one({'username': user_id}, {'$inc': {'balance': wager}})
        new_user = db.Users.find_one({'username': user_id}, {'balance': 1})
        new_balance = float(new_user.get('balance', 0)) if new_user else None

        return jsonify({
            'status': 'success',
            'allowed': True,
            'message': 'bet cancelled and refunded',
            'bet_id': bet_id,
            'refund': wager,
            'new_balance': new_balance
        }), 200

    except requests.exceptions.Timeout:
        return jsonify({'status': 'error', 'message': 'Events API timeout'}), 502
    except requests.exceptions.RequestException as e:
        return jsonify({'status': 'error', 'message': 'Events API request failed', 'error': str(e)}), 502
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to cancel bet', 'error': str(e)}), 500
    

@app.route('/api/reset', methods=['POST'])
def reset_balances():
    try:
        result = db.Users.update_many({}, {"$set": {"balance": DAILY_CREDIT}})
        return jsonify({
            'status': 'success',
            'users_reset': result.modified_count,
            'new_balance': DAILY_CREDIT
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to reset balances', 'error': str(e)}), 500

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    try:
        try:
            limit = int((request.args.get('limit') or '50').strip())
            offset = int((request.args.get('offset') or '0').strip())
        except Exception:
            return jsonify({'status': 'error', 'message': 'limit and offset must be integers'}), 400
        if limit < 1 or limit > 100:
            limit = 50
        if offset < 0:
            offset = 0

        total_users = db.Users.count_documents({"profit": {"$exists": True}})
        cursor = (
            db.Users
            .find({"profit": {"$exists": True}})
            .sort("profit", -1)
            .skip(offset)
            .limit(limit)
        )
        users_page = list(cursor)

        results = []
        rank_base = offset + 1
        for idx, u in enumerate(users_page):
            results.append({
                'rank': rank_base + idx,
                'user_id': u.get('username'),
                'profit': u.get('profit', 0),
                'balance': u.get('balance', 0)
            })

        return jsonify({
            'status': 'success',
            'total_users': total_users,
            'limit': limit,
            'offset': offset,
            'results': results
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to get leaderboard', 'error': str(e)}), 500


@app.route('/api/bets/<bet_id>', methods=['GET'])
def get_bet_by_id(bet_id):
    try:
        try:
            _id = ObjectId(bet_id)
        except Exception:
            return jsonify({'status': 'error', 'message': 'Invalid bet_id'}), 400

        bet = db.Bets.find_one({'_id': _id})
        if not bet:
            return jsonify({'status': 'error', 'message': 'Bet not found'}), 404

        def to_iso(v):
            from datetime import datetime as dt
            return v.isoformat() if isinstance(v, dt) else v

        # Normalize legs for consistent output
        legs = bet.get('legs')
        if not isinstance(legs, list):
            legacy_leg = bet.get('leg')
            if isinstance(legacy_leg, list):
                legs = legacy_leg
            elif isinstance(legacy_leg, dict):
                legs = [legacy_leg]
            else:
                legs = []

        bet_json = {
            'bet_id': str(bet.get('_id')),
            'user_id': bet.get('user_id'),
            'bet_type': bet.get('bet_type'),
            'wagered_amount': bet.get('wagered_amount'),
            'leg': [
                {
                    'game_id': leg.get('game_id'),
                    'selection': leg.get('selection'),
                    'odds': leg.get('odds'),
                    'status': leg.get('status')
                } for leg in legs
            ],
            'status': bet.get('status'),
            'outcome': bet.get('outcome'),
            'payout': bet.get('payout'),
            'profit': bet.get('profit'),
            'created_at': to_iso(bet.get('created_at')),
            'settled_at': to_iso(bet.get('settled_at')),
        
        }

        return jsonify({'status': 'success', 'data': bet_json}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to fetch bet', 'error': str(e)}), 500

@app.route('/api/users/<user_id>/stats', methods=['GET'])
@auth_required
def get_user_stats(user_id):
    if g.user_claims.get('sub') != user_id:
        return jsonify({'status': 'error', 'message': 'forbidden'}), 403

    active_count  = db.Bets.count_documents({'user_id': user_id, 'status': 'active'})
    settled_count = db.Bets.count_documents({'user_id': user_id, 'status': 'settled'})

    # wins/losses + totals from settled bets
    pipeline = [
        {'$match': {'user_id': user_id, 'status': 'settled'}},
        {'$group': {
            '_id': None,
            'wins':   {'$sum': {'$cond': [{'$eq': ['$outcome', 'win']}, 1, 0]}},
            'losses': {'$sum': {'$cond': [{'$eq': ['$outcome', 'loss']}, 1, 0]}},
            'wagered_total': {'$sum': {'$ifNull': ['$wagered_amount', 0]}},
            'profit_total':  {'$sum': {'$ifNull': ['$profit', 0]}},
        }}
    ]
    agg = list(db.Bets.aggregate(pipeline))
    wins = int(agg[0]['wins']) if agg else 0
    losses = int(agg[0]['losses']) if agg else 0
    wagered_total = float(agg[0]['wagered_total']) if agg else 0.0
    profit_total  = float(agg[0]['profit_total']) if agg else 0.0

    win_pct = (wins / (wins + losses)) if (wins + losses) > 0 else 0.0
    roi = (profit_total / wagered_total) if wagered_total > 0 else 0.0

    # average odds over settled bets' single leg
    settled_bets = db.Bets.find(
        {'user_id': user_id, 'status': 'settled'},
        {'leg.odds': 1}
    )
    odds_sum = 0.0
    odds_n = 0
    for b in settled_bets:
        legs = b.get('leg') or []
        for leg in legs:
            try:
                odds_sum += float(leg['odds'])
                odds_n += 1
            except Exception:
                pass
    avg_odds = (odds_sum / odds_n) if odds_n else 0.0

    return jsonify({
        'status': 'success',
        'user_id': user_id,
        'stats': {
            'wins': wins,
            'losses': losses,
            'win_pct': round(win_pct, 4),
            'roi': round(roi, 4),
            'avg_odds': round(avg_odds, 2),
            'active_count': int(active_count),
            'settled_count': int(settled_count),
            'wagered_total': wagered_total,
            'profit_total': profit_total,
        }
    }), 200

if __name__ == '__main__':
    print("🎰 Starting Gambling App API with optimized The Odds API usage...")
    app.run(debug=True, host='0.0.0.0', port=5000)

