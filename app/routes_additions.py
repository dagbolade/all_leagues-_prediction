# Add these routes to app/routes.py at the end before the initialization

@routes.route('/statistics', methods=['GET', 'POST'])
def statistics():
    """Match statistics dashboard"""
    if request.method == 'POST':
        home_team = request.form.get('homeTeam')
        away_team = request.form.get('awayTeam')
        
        if not home_team or not away_team:
            return render_template('statistics.html', teams=teams, error="Please select both teams")
        
        if not predictor:
            return render_template('statistics.html', teams=teams, error="System not available")
        
        try:
            # Import statistics generator
            from app.match_statistics import get_statistics_generator
            
            stats_gen = get_statistics_generator(predictor.df)
            stats = stats_gen.generate_full_statistics(home_team, away_team)
            
            return render_template('statistics.html',
                                 teams=teams,
                                 stats=stats,
                                 home_team=home_team,
                                 away_team=away_team)
        
        except Exception as e:
            print(f"[Error] Statistics error: {str(e)}")
            import traceback
            traceback.print_exc()
            return render_template('statistics.html', teams=teams,
                                 error=f"Statistics generation failed: {str(e)}")
    
    return render_template('statistics.html', teams=teams)


@routes.route('/api/betting-tips', methods=['POST'])
def get_betting_tips():
    """API endpoint for betting tips"""
    try:
        data = request.get_json()
        home_team = data.get('home_team')
        away_team = data.get('away_team')
        
        if not home_team or not away_team or not predictor:
            return jsonify({'status': 'error', 'message': 'Invalid request'}), 400
        
        # Get prediction
        result = predictor.predict_with_full_bayesian_analysis(home_team, away_team)
        
        # Generate betting tips
        tips_gen = get_betting_tips_generator()
        tips = tips_gen.generate_tips(
            result.get('predictions', {}),
            result.get('probabilities', {}),
            home_team,
            away_team
        )
        
        formatted_tips = tips_gen.format_tips_for_display(tips)
        
        return jsonify({
            'status': 'success',
            'tips': formatted_tips,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
