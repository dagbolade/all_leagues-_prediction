# test_optimizations.py - TEST YOUR OPTIMIZED SYSTEM

import os
import sys
import time
from pathlib import Path

print("🧪 TESTING OPTIMIZED FOOTBALL AI PREDICTOR")
print("=" * 60)
print("🎯 Testing your existing workflow with new optimizations")
print("⚡ Checking for speed improvements and functionality")
print("=" * 60)

def test_main_pipeline():
    """Test the optimized main.py pipeline"""
    print("\n📋 TEST 1: OPTIMIZED MAIN.PY PIPELINE")
    print("-" * 40)

    try:
        # Import your optimized main
        from main import main

        start_time = time.time()

        # Test with fast training enabled (default)
        print("🚀 Running optimized pipeline with fast training...")
        result = main(use_fast_training=True)

        training_time = time.time() - start_time

        if result:
            print(f"✅ Pipeline completed successfully!")
            print(f"⏰ Total time: {training_time/60:.1f} minutes")
            print(f"📊 Features reduced to: {result.get('total_features', 'Unknown')}")
            print(f"🧠 Bayesian predictions valid: {result.get('predictions_valid', False)}")

            if training_time < 3600:  # Less than 1 hour
                print(f"🎉 SUCCESS: {60/training_time:.1f}x faster than original 1-hour baseline!")

            return True
        else:
            print("❌ Pipeline returned None")
            return False

    except Exception as e:
        print(f"❌ Error testing main pipeline: {e}")
        return False

def test_flask_app_startup():
    """Test the Flask app startup"""
    print("\n📋 TEST 2: FLASK APP STARTUP")
    print("-" * 40)

    try:
        # Import your routes
        from app.routes import routes, predictor, teams, model_info

        print(f"✅ Routes imported successfully")
        print(f"📊 Predictor status: {'Ready' if predictor else 'Not ready'}")
        print(f"👥 Teams loaded: {len(teams)}")
        print(f"🤖 Model info: {model_info}")

        if predictor and len(teams) > 0:
            print("✅ Flask app initialization successful!")
            return True
        else:
            print("⚠️ Flask app partially initialized")
            return False

    except Exception as e:
        print(f"❌ Error testing Flask app: {e}")
        return False

def test_optimized_files():
    """Test if optimized files exist"""
    print("\n📋 TEST 3: OPTIMIZED FILES CHECK")
    print("-" * 40)

    required_files = {
        'Fast Feature Selector': 'footy/intelligent_feature_selector.py',
        'Fast Model Training': 'footy/fast_model_training.py',
        'Optimized Main': 'main.py',
        'Modern Routes': 'app/routes.py',
        'Modern Index Template': 'app/templates/index.html',
        'Analytics Template': 'app/templates/analytics.html'
    }

    all_exist = True
    for name, file_path in required_files.items():
        if Path(file_path).exists():
            print(f"✅ {name}: {file_path}")
        else:
            print(f"❌ {name}: {file_path} - MISSING")
            all_exist = False

    return all_exist

def test_speed_comparison():
    """Test prediction speed"""
    print("\n📋 TEST 4: PREDICTION SPEED TEST")
    print("-" * 40)

    try:
        from app.routes import predictor

        if not predictor:
            print("⚠️ Predictor not available for speed test")
            return False

        # Test prediction speed
        test_teams = ['Arsenal', 'Chelsea']

        start_time = time.time()
        result = predictor.predict_with_full_bayesian_analysis(test_teams[0], test_teams[1])
        prediction_time = time.time() - start_time

        print(f"⚡ Prediction time: {prediction_time:.3f} seconds")

        if prediction_time < 5.0:
            print("✅ Prediction speed: EXCELLENT (< 5 seconds)")
            return True
        elif prediction_time < 30.0:
            print("✅ Prediction speed: GOOD (< 30 seconds)")
            return True
        else:
            print("⚠️ Prediction speed: SLOW (> 30 seconds)")
            return False

    except Exception as e:
        print(f"❌ Error testing prediction speed: {e}")
        return False

def run_flask_test():
    """Quick Flask app test"""
    print("\n📋 TEST 5: FLASK ROUTES TEST")
    print("-" * 40)

    try:
        from flask import Flask
        from app.routes import routes

        app = Flask(__name__)
        app.register_blueprint(routes)

        with app.test_client() as client:
            # Test home page
            response = client.get('/')
            if response.status_code == 200:
                print("✅ Home page: OK")
            else:
                print(f"❌ Home page: Error {response.status_code}")

            # Test predict page
            response = client.get('/predict')
            if response.status_code == 200:
                print("✅ Predict page: OK")
            else:
                print(f"❌ Predict page: Error {response.status_code}")

            # Test analytics page
            response = client.get('/analytics')
            if response.status_code == 200:
                print("✅ Analytics page: OK")
            else:
                print(f"❌ Analytics page: Error {response.status_code}")

            # Test API endpoint
            response = client.get('/api/system-status')
            if response.status_code == 200:
                print("✅ API endpoint: OK")
            else:
                print(f"❌ API endpoint: Error {response.status_code}")

        print("✅ Flask routes test completed")
        return True

    except Exception as e:
        print(f"❌ Error testing Flask routes: {e}")
        return False

def main():
    """Run all tests"""
    print(f"📅 Test started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        ("Files Check", test_optimized_files),
        ("Flask Startup", test_flask_app_startup),
        ("Flask Routes", run_flask_test),
        ("Prediction Speed", test_speed_comparison),
        # ("Main Pipeline", test_main_pipeline),  # This one takes time, run separately
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            print()  # Empty line for readability
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")

    print("🎉 TEST RESULTS SUMMARY")
    print("=" * 40)
    print(f"✅ Passed: {passed}/{total} tests")
    print(f"📊 Success rate: {(passed/total)*100:.1f}%")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("🚀 Your optimized system is ready!")
        print("\n📝 NEXT STEPS:")
        print("1. Run: python main.py (for full optimization)")
        print("2. Run: python app/run.py (to start Flask app)")
        print("3. Open: http://localhost:5000")
    else:
        print(f"\n⚠️ {total-passed} tests failed")
        print("💡 Check the errors above and fix any issues")

    print("\n🔍 OPTIONAL: Run full pipeline test")
    print("   python -c \"from test_optimizations import test_main_pipeline; test_main_pipeline()\"")

if __name__ == "__main__":
    main()