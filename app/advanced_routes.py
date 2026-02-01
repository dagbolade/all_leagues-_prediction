"""
Routes for Priority 4 Advanced Features

AI Chat Assistant, Accumulator Builder, Live Tracker, League Predictor
"""

from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import logging

# Import Priority 4 modules
from app.ai_assistant import get_ai_assistant, get_fallback_response
from app.accumulator_builder import get_accumulator_builder
from app.live_tracker import get_live_tracker
from app.league_predictor import get_league_predictor

logger = logging.getLogger(__name__)

# Create blueprint
advanced_routes = Blueprint('advanced', __name__)


# ============================================================================
# AI CHAT ASSISTANT ROUTES
# ============================================================================

@advanced_routes.route('/chat', methods=['GET'])
def chat_page():
    """AI chat assistant page"""
    return render_template('chat.html')


@advanced_routes.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    """AI chat endpoint"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        context = data.get('context', None)
        
        logger.info(f"AI chat request: {message[:50]}...")
        
        if not message:
            return jsonify({'status': 'error', 'message': 'No message provided'}), 400
        
        # Get AI assistant
        assistant = get_ai_assistant()
        logger.info(f"AI assistant initialized with model: {assistant.model_name}")
        
        # Generate response
        logger.info("Generating AI response...")
        response = assistant.generate_response(message, context)
        logger.info(f"AI response status: {response.get('status')}")
        
        # If AI not available, use fallback
        if response.get('fallback') or response.get('status') == 'error':
            logger.warning(f"AI fallback triggered: {response.get('message')}")
            response['message'] = get_fallback_response(message)
            response['status'] = 'success'
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"AI chat error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Sorry, I encountered an error. Please try again.',
            'error': str(e)
        }), 500


@advanced_routes.route('/api/ai-chat/clear', methods=['POST'])
def clear_chat_history():
    """Clear chat history"""
    try:
        assistant = get_ai_assistant()
        assistant.clear_history()
        
        return jsonify({
            'status': 'success',
            'message': 'Chat history cleared'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============================================================================
# ACCUMULATOR BUILDER ROUTES
# ============================================================================

@advanced_routes.route('/accumulator', methods=['GET'])
def accumulator_page():
    """Accumulator builder page"""
    return render_template('accumulator.html')


@advanced_routes.route('/api/accumulator/add', methods=['POST'])
def add_to_accumulator():
    """Add selection to accumulator"""
    try:
        data = request.get_json()
        
        builder = get_accumulator_builder()
        result = builder.add_selection(
            home_team=data.get('home_team'),
            away_team=data.get('away_team'),
            market=data.get('market'),
            selection=data.get('selection'),
            odds=float(data.get('odds', 1.0)),
            confidence=float(data.get('confidence', 0.5))
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Accumulator add error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@advanced_routes.route('/api/accumulator/remove/<int:selection_id>', methods=['DELETE'])
def remove_from_accumulator(selection_id):
    """Remove selection from accumulator"""
    try:
        builder = get_accumulator_builder()
        result = builder.remove_selection(selection_id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@advanced_routes.route('/api/accumulator/details', methods=['GET'])
def get_accumulator_details():
    """Get accumulator details"""
    try:
        builder = get_accumulator_builder()
        details = builder.get_accumulator_details()
        
        return jsonify({
            'status': 'success',
            'accumulator': details
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@advanced_routes.route('/api/accumulator/stake-suggestion', methods=['POST'])
def get_stake_suggestion():
    """Get suggested stake"""
    try:
        data = request.get_json()
        bankroll = float(data.get('bankroll', 100))
        
        builder = get_accumulator_builder()
        suggestion = builder.get_suggested_stake(bankroll)
        
        return jsonify({
            'status': 'success',
            'suggestion': suggestion
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@advanced_routes.route('/api/accumulator/clear', methods=['POST'])
def clear_accumulator():
    """Clear accumulator"""
    try:
        builder = get_accumulator_builder()
        builder.clear_selections()
        
        return jsonify({
            'status': 'success',
            'message': 'Accumulator cleared'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============================================================================
# LIVE MATCH TRACKER ROUTES
# ============================================================================

@advanced_routes.route('/live-tracker', methods=['GET'])
def live_tracker_page():
    """Live match tracker page"""
    return render_template('live_tracker.html')


@advanced_routes.route('/api/live-tracker/matches', methods=['GET'])
def get_live_matches():
    """Get live matches with predictions"""
    try:
        tracker = get_live_tracker()
        matches = tracker.get_live_matches_with_predictions()
        
        return jsonify({
            'status': 'success',
            'matches': matches,
            'count': len(matches),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Live tracker error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============================================================================
# LEAGUE TABLE PREDICTOR ROUTES
# ============================================================================

@advanced_routes.route('/league-predictor', methods=['GET'])
def league_predictor_page():
    """League table predictor page"""
    return render_template('league_predictor.html')


@advanced_routes.route('/api/league-predictor/predict', methods=['POST'])
def predict_league_table():
    """Predict league table"""
    try:
        data = request.get_json()
        
        league = data.get('league')
        current_standings = data.get('current_standings', [])
        remaining_fixtures = data.get('remaining_fixtures', [])
        
        # Get predictor (would need to pass main predictor instance)
        predictor = get_league_predictor()
        
        result = predictor.predict_league_table(
            league,
            current_standings,
            remaining_fixtures
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"League prediction error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
